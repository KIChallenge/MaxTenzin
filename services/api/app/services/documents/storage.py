"""Uploaded PDF bytes under var/uploads/<doc_id>.pdf (gitignored) + document metadata in the doc store."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.db import store

DOCS = "documents"            # DocumentSummary (+ sha256, pages) per document id
ANALYSES = "document_analyses"  # DocumentAnalysis.model_dump() per document id (read by WS-B benefits, WS-F forms)


def uploads_dir() -> Path:
    d = get_settings().var_dir / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pdf_path(doc_id: str) -> Path:
    return uploads_dir() / f"{doc_id}.pdf"


def save_pdf(doc_id: str, data: bytes) -> Path:
    p = pdf_path(doc_id)
    p.write_bytes(data)
    return p


def load_pdf(doc_id: str) -> bytes | None:
    p = pdf_path(doc_id)
    return p.read_bytes() if p.exists() else None


def get_meta(doc_id: str) -> dict | None:
    return store.get(DOCS, doc_id)
