"""documents — PDF upload + extraction of EXPLICITLY documented recommendations (quote + page verified)."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.contracts.documents import DocumentAnalysis, DocumentSummary, DocumentType
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.db import now_iso, store
from app.services.documents import goldens, storage
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


@router.post("", response_model=DocumentSummary, summary="Upload a PDF for the current subject")
async def upload(file: UploadFile = File(...), ctx: Context = Depends(require(Scope.read_documents))):
    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "Bitte laden Sie eine PDF-Datei hoch.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Die Datei ist zu groß (max. 20 MB).")
    filename = file.filename or "upload.pdf"
    pages = page_texts(data)
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    storage.save_pdf(doc_id, data)
    summary = DocumentSummary(document_id=doc_id, filename=filename, doc_type=detect_doc_type(pages, filename),
                              uploaded_at=now_iso(), owner_id=ctx.subject.id)
    store.put(storage.DOCS, doc_id, {**summary.model_dump(), "sha256": sha256(data), "pages": len(pages)},
              subject_id=ctx.subject.id)
    return summary


@router.get("", response_model=list[DocumentSummary], summary="Documents of the current subject")
def list_docs(ctx: Context = Depends(require(Scope.read_documents))):
    return store.list(storage.DOCS, subject_id=ctx.subject.id)


@router.post("/{document_id}/analyze", response_model=DocumentAnalysis, summary="Extract explicitly documented recommendations")
def analyze(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    meta = _owned_meta(document_id, ctx)
    data = storage.load_pdf(document_id) if meta else None
    if meta and data:
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


@router.get("/{document_id}/file", summary="Download the uploaded PDF", response_class=FileResponse,
            responses={200: {"content": {"application/pdf": {}}}})
def get_file(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    meta = _owned_meta(document_id, ctx)
    path = storage.pdf_path(document_id)
    if not meta or not path.exists():
        raise HTTPException(404, "Dokument nicht gefunden")
    return FileResponse(path, media_type="application/pdf", filename=meta["filename"])
