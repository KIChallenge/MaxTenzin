"""Uploaded bytes under var/uploads/ (gitignored): <doc_id>.pdf, or <doc_id>-p<N>.<jpg|png> per photo page.
Document metadata lives in the doc store."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.db import store

DOCS = "documents"            # DocumentSummary (+ sha256, pages, source, images) per document id
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


def image_name(doc_id: str, page: int, ext: str) -> str:
    return f"{doc_id}-p{page}.{ext}"


def save_image(name: str, data: bytes) -> Path:
    p = uploads_dir() / name
    p.write_bytes(data)
    return p


def image_path(name: str) -> Path:
    return uploads_dir() / name


def load_images(meta: dict) -> list[bytes] | None:
    """Photo pages of an image upload in page order, or None if any file is missing."""
    paths = [image_path(i["name"]) for i in meta.get("images") or []]
    if not paths or not all(p.exists() for p in paths):
        return None
    return [p.read_bytes() for p in paths]
