"""PDF text per page (pypdf), content hash and deterministic document-type detection."""

from __future__ import annotations

import hashlib
import io
import re

from pypdf import PdfReader

from app.contracts.documents import DocumentType


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def page_texts(data: bytes) -> list[str]:
    """Text of every page, index 0 = page 1. Page numbers are preserved by position."""
    reader = PdfReader(io.BytesIO(data))
    return [(p.extract_text() or "") for p in reader.pages]


# Ordered: first match wins. Vaccination records and discharge letters are checked before imaging,
# because a discharge letter may mention imaging ("Röntgen") but an imaging report never says "Entlassungsbefund".
_TYPE_KEYWORDS: list[tuple[DocumentType, tuple[str, ...]]] = [
    (DocumentType.vaccination_record, ("elektronischer impfpass", "e-impfpass", "impfstoff:", "impfdatum:")),
    (DocumentType.discharge_letter, ("entlassungsbefund", "entlassungsbrief", "entlassungsdatum", "entlassungsmanagement")),
    (DocumentType.imaging_report, ("bildgebende diagnostik", "us-befund", "röntgen", "sonographie", "sonografie",
                                   "mrt-befund", "ct-befund", "magnetresonanz", "computertomographie")),
]


def detect_doc_type(pages: list[str], filename: str = "") -> DocumentType:
    """Keyword-based type detection on the first two pages (+ filename). Deterministic, no LLM."""
    hay = (filename + "\n" + "\n".join(pages[:2])).lower()
    for doc_type, words in _TYPE_KEYWORDS:
        if any(w in hay for w in words):
            return doc_type
    return DocumentType.other


_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Whitespace-normalised text for quote matching (collapse runs, unify soft hyphen / nbsp)."""
    text = text.replace("­", "").replace(" ", " ")
    return _WS.sub(" ", text).strip()
