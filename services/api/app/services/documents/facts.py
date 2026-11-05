"""Deterministic administrative facts from documents (regex, no LLM, no medical content). Each fact keeps quote + page."""

from __future__ import annotations

import re

from app.contracts.documents import DocumentFact, DocumentType

# (key, pattern with one value group, doc types)
PATTERNS: list[tuple[str, re.Pattern, set[DocumentType]]] = [
    ("discharge_date", re.compile(r"Entlassungsdatum[ \t]*:?[ \t]*(\d{1,2}\.\d{1,2}\.\d{4})"), {DocumentType.discharge_letter}),
    ("admission_date", re.compile(r"Aufnahmedatum[ \t]*:?[ \t]*(\d{1,2}\.\d{1,2}\.\d{4})"), {DocumentType.discharge_letter}),
    ("department", re.compile(r"(Abteilung für [^\n–-]+?)\s*(?:[–-]|\n)"), {DocumentType.discharge_letter}),
    ("institution", re.compile(r"((?:Klinikum|Krankenhaus|Spital|Klinik)\s+[A-ZÄÖÜ][^\n,]{2,60})\n"), {DocumentType.discharge_letter}),
]


def admin_facts(doc_type: DocumentType, pages: list[str]) -> list[DocumentFact]:
    facts: list[DocumentFact] = []
    seen: set[str] = set()
    for key, pat, types in PATTERNS:
        if doc_type not in types:
            continue
        for i, text in enumerate(pages, start=1):
            m = pat.search(text)
            if m and key not in seen:
                value = " ".join(m.group(1).split())
                if key == "institution" and value.lower().startswith("krankenhaus-entlassungsbefund"):
                    continue
                facts.append(DocumentFact(key=key, value=value, quote=" ".join(m.group(0).split()), page=i))
                seen.add(key)
                break
    return facts
