"""documents — PDF / photo upload + extraction of EXPLICITLY documented recommendations (quote + page verified)."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.contracts.documents import DocumentAnalysis, DocumentSummary, DocumentType
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.db import now_iso, store
from app.services.documents import goldens, storage, vision
from app.services.documents.extract import analyze_pdf, enforce_boundary, from_golden
from app.services.documents.pdf import detect_doc_type, page_texts, sha256

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024


def _owned_meta(document_id: str, ctx: Context) -> dict | None:
    meta = storage.get_meta(document_id)
    if meta and meta.get("owner_id") != ctx.subject.id:
        raise HTTPException(404, "Dokument nicht gefunden")
    return meta


def _demo_golden(document_id: str, ctx: Context) -> dict | None:
    g = goldens.by_demo_id(document_id)
    return g if g and g.get("demo_subject_id") == ctx.subject.id else None


def _cite(ctx: Context, a: DocumentAnalysis) -> None:
    ctx.cite(*(f"{a.filename}, S. {r.page}" for r in a.recommendations))
    ctx.rule_ids.append("documents.quote_verification.v1")


@router.post("", response_model=DocumentSummary,
             summary="Upload a PDF or photos (JPG/PNG) of a document for the current subject")
async def upload(
    file: UploadFile | None = File(None, description="One PDF or one photo (JPG/PNG)"),
    files: list[UploadFile] | None = File(None, description="Several photos (JPG/PNG), one per page, in page order"),
    ctx: Context = Depends(require(Scope.read_documents)),
):
    uploads = ([file] if file else []) + list(files or [])
    if not uploads:
        raise HTTPException(422, "Bitte wählen Sie eine Datei aus.")
    blobs = [(u.filename, await u.read()) for u in uploads]
    kinds = [vision.media_type(d) for _, d in blobs]
    if kinds == [vision.PDF]:
        return _upload_pdf(blobs[0][0], blobs[0][1], ctx)
    if vision.PDF in kinds:
        raise HTTPException(415, "Mehrere Dateien gehen nur bei Fotos (JPG/PNG). Bitte laden Sie PDFs einzeln hoch.")
    if vision.HEIC in kinds:
        raise HTTPException(415, vision.HEIC_DE)
    if None in kinds:
        raise HTTPException(415, vision.UNSUPPORTED_DE)
    if len(blobs) > vision.MAX_IMAGES:
        raise HTTPException(413, f"Bitte laden Sie höchstens {vision.MAX_IMAGES} Fotos auf einmal hoch.")
    if sum(len(d) for _, d in blobs) > MAX_BYTES:
        raise HTTPException(413, "Die Datei ist zu groß (max. 20 MB)." if len(blobs) == 1
                            else "Die Fotos sind zusammen zu groß (max. 20 MB).")
    for name, data in blobs:
        try:
            vision.open_image(data)
        except ValueError:
            raise HTTPException(415, f"Das Foto „{name or 'Foto'}“ konnte nicht gelesen werden. "
                                     "Bitte nehmen Sie es erneut als JPG oder PNG auf.") from None
    return await run_in_threadpool(_upload_images, blobs, kinds, ctx)


def _upload_pdf(filename: str | None, data: bytes, ctx: Context) -> DocumentSummary:
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Die Datei ist zu groß (max. 20 MB).")
    filename = filename or "upload.pdf"
    pages = page_texts(data)
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    storage.save_pdf(doc_id, data)
    summary = DocumentSummary(document_id=doc_id, filename=filename, doc_type=detect_doc_type(pages, filename),
                              uploaded_at=now_iso(), owner_id=ctx.subject.id)
    store.put(storage.DOCS, doc_id, {**summary.model_dump(), "sha256": sha256(data), "pages": len(pages)},
              subject_id=ctx.subject.id)
    return summary


def _upload_images(blobs: list[tuple[str | None, bytes]], kinds: list[str], ctx: Context) -> DocumentSummary:
    """Photos become pages in upload order. They are transcribed right away so doc_type is known on upload."""
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    images = []
    for i, ((_, data), kind) in enumerate(zip(blobs, kinds, strict=True), 1):
        name = storage.image_name(doc_id, i, vision.IMAGE_TYPES[kind])
        storage.save_image(name, data)
        images.append({"name": name, "media_type": kind})
    filename = blobs[0][0] or "foto.jpg"
    if len(blobs) > 1:
        filename = f"{filename} (+{len(blobs) - 1} Fotos)"
    datas = [d for _, d in blobs]
    t = vision.transcribe(doc_id, datas)
    store.put(vision.TRANSCRIPTS, doc_id, t.model_dump(), subject_id=ctx.subject.id)
    summary = DocumentSummary(document_id=doc_id, filename=filename,
                              doc_type=detect_doc_type([p.text for p in t.pages], filename),
                              uploaded_at=now_iso(), owner_id=ctx.subject.id)
    store.put(storage.DOCS, doc_id, {**summary.model_dump(), "sha256": vision.image_sha(datas), "pages": len(datas),
                                     "source": "image", "images": images}, subject_id=ctx.subject.id)
    return summary


def _image_transcript(document_id: str, meta: dict) -> vision.DocumentTranscript | None:
    """Stored transcript of a photo upload; re-read if missing or if the last attempt failed."""
    stored = store.get(vision.TRANSCRIPTS, document_id)
    if stored and stored.get("mode") != "error":
        return vision.DocumentTranscript(**stored)
    images = storage.load_images(meta)
    if images is None:
        return None
    t = vision.transcribe(document_id, images)
    store.put(vision.TRANSCRIPTS, document_id, t.model_dump(), subject_id=meta.get("owner_id"))
    return t


@router.get("", response_model=list[DocumentSummary], summary="Documents of the current subject")
def list_docs(ctx: Context = Depends(require(Scope.read_documents))):
    return store.list(storage.DOCS, subject_id=ctx.subject.id)


@router.post("/{document_id}/analyze", response_model=DocumentAnalysis, summary="Extract explicitly documented recommendations")
def analyze(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    meta = _owned_meta(document_id, ctx)
    data = storage.load_pdf(document_id) if meta and meta.get("source") != "image" else None
    if meta and meta.get("source") == "image":
        a = _analyze_images(document_id, meta)
    elif meta and data:
        pages = page_texts(data)
        a = analyze_pdf(document_id, meta["filename"], meta.get("sha256") or sha256(data),
                        DocumentType(meta["doc_type"]), pages)
    elif (g := _demo_golden(document_id, ctx)) is not None:
        # Demo document known only by its golden (PDF not seeded): hand-verified golden, boundary still enforced.
        a = enforce_boundary(from_golden(g, document_id))
    else:
        raise HTTPException(404, "Dokument nicht gefunden")
    store.put(storage.ANALYSES, document_id, a.model_dump(mode="json"), subject_id=ctx.subject.id)
    _cite(ctx, a)
    return a


def _analyze_images(document_id: str, meta: dict) -> DocumentAnalysis:
    t = _image_transcript(document_id, meta)
    if t is None:
        raise HTTPException(404, "Dokument nicht gefunden")
    if t.mode == "error":
        raise HTTPException(502, "Das Foto konnte gerade nicht gelesen werden. Bitte versuchen Sie es später erneut.")
    pages = [p.text for p in t.pages]
    doc_type = detect_doc_type(pages, meta["filename"])
    if doc_type.value != meta["doc_type"]:
        store.put(storage.DOCS, document_id, {**meta, "doc_type": doc_type.value}, subject_id=meta.get("owner_id"))
    # Unchanged PDF pipeline on the transcript: extraction, quote verification, boundary, admin facts, cache.
    a = analyze_pdf(document_id, meta["filename"], meta["sha256"], doc_type, pages)
    return vision.mark_vision(a, t)


@router.get("/{document_id}/analysis", response_model=DocumentAnalysis, summary="Last analysis result")
def get_analysis(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    _owned_meta(document_id, ctx)
    stored = store.get(storage.ANALYSES, document_id)
    if stored:
        a = DocumentAnalysis(**stored)
    elif (g := _demo_golden(document_id, ctx)) is not None:
        a = enforce_boundary(from_golden(g, document_id))
    else:
        raise HTTPException(404, "Für dieses Dokument liegt noch keine Analyse vor.")
    _cite(ctx, a)
    return a


@router.get("/{document_id}/file", summary="Download the uploaded PDF (or photo page ?page=N)",
            response_class=FileResponse,
            responses={200: {"content": {"application/pdf": {}, "image/jpeg": {}, "image/png": {}}}})
def get_file(document_id: str, page: int = Query(1, ge=1, description="Photo uploads: page number"),
             ctx: Context = Depends(require(Scope.read_documents))):
    meta = _owned_meta(document_id, ctx)
    if meta and meta.get("source") == "image":
        images = meta.get("images") or []
        if page > len(images) or not storage.image_path(images[page - 1]["name"]).exists():
            raise HTTPException(404, "Dokument nicht gefunden")
        img = images[page - 1]
        return FileResponse(storage.image_path(img["name"]), media_type=img["media_type"], filename=img["name"])
    path = storage.pdf_path(document_id)
    if not meta or not path.exists():
        raise HTTPException(404, "Dokument nicht gefunden")
    return FileResponse(path, media_type="application/pdf", filename=meta["filename"])


@router.get("/{document_id}/transcript", response_model=vision.DocumentTranscript,
            summary="Text read from the document, per page (photo transcription or PDF text layer)")
def get_transcript(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    meta = _owned_meta(document_id, ctx)
    if meta and meta.get("source") == "image":
        t = _image_transcript(document_id, meta)
        if t is not None:
            return t
    elif meta and (data := storage.load_pdf(document_id)):
        pages = [vision.TranscriptPage(page=i, text=txt) for i, txt in enumerate(page_texts(data), 1)]
        return vision.DocumentTranscript(document_id=document_id, source="pdf", mode="pdf-text", pages=pages)
    raise HTTPException(404, "Für dieses Dokument liegt kein gelesener Text vor.")
