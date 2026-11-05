"""documents — upload + explicit-recommendation extraction. STUB (owner: WS-D)."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.contracts.documents import DocumentAnalysis, DocumentSummary, DocumentType
from app.contracts.identity import Scope
from app.core.auth import Context, require
from app.core.db import now_iso, store
from app.fixtures import ANNA_ANALYSIS

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentSummary, summary="Upload a PDF for the current subject")
async def upload(file: UploadFile = File(...), ctx: Context = Depends(require(Scope.read_documents))):
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    summary = DocumentSummary(document_id=doc_id, filename=file.filename or "upload.pdf", doc_type=DocumentType.other,
                              uploaded_at=now_iso(), owner_id=ctx.subject.id)
    store.put("documents", doc_id, summary.model_dump(), subject_id=ctx.subject.id)
    return summary


@router.get("", response_model=list[DocumentSummary], summary="Documents of the current subject")
def list_docs(ctx: Context = Depends(require(Scope.read_documents))):
    return store.list("documents", subject_id=ctx.subject.id)


@router.post("/{document_id}/analyze", response_model=DocumentAnalysis, summary="Extract explicitly documented recommendations")
def analyze(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    if not store.get("documents", document_id) and document_id != ANNA_ANALYSIS.document_id:
        raise HTTPException(404, "Dokument nicht gefunden")
    ctx.cite(*(f"{ANNA_ANALYSIS.filename}, S. {r.page}" for r in ANNA_ANALYSIS.recommendations))
    return ANNA_ANALYSIS.model_copy(update={"document_id": document_id})  # STUB: fixture


@router.get("/{document_id}/analysis", response_model=DocumentAnalysis, summary="Last analysis result")
def get_analysis(document_id: str, ctx: Context = Depends(require(Scope.read_documents))):
    return ANNA_ANALYSIS.model_copy(update={"document_id": document_id})  # STUB
