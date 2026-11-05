"""Deterministic facts from documents (regex, no LLM). Each fact keeps a verbatim quote + page.

Administrative facts (dates, department) and – for forms that explicitly ask for them (PAL 080 "Krankheiten bzw.
gesundheitliche Beeinträchtigungen") – the diagnoses AS WRITTEN in the document. They are copied verbatim, never
summarised, explained or interpreted, and always prefilled unconfirmed for the person to check.
"""

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
    if doc_type == DocumentType.discharge_letter:
        facts += _diagnoses(pages)
    return facts


_MAIN = re.compile(r"Hauptdiagnose[ \t]*:[ \t]*(.+?\.)[ \t]*(?:\n|$)", re.DOTALL)
_SECONDARY_START = re.compile(r"Nebendiagnosen[ \t]*:[ \t]*\n")
_SECONDARY_END = re.compile(r"\n(?:Relevante Vorerkrankungen|\d+\.\s+[A-ZÄÖÜ])")


def _clean(text: str) -> str:
    return " ".join(re.sub(r"-\n(?=[a-zäöüß])", "", text).split())


def _diagnoses(pages: list[str]) -> list[DocumentFact]:
    """Main and secondary diagnoses exactly as written (verbatim), for forms that ask for them."""
    out: list[DocumentFact] = []
    for i, text in enumerate(pages, start=1):
        m = _MAIN.search(text)
        if m and len(m.group(1)) < 300:
            out.append(DocumentFact(key="main_diagnosis", value=_clean(m.group(1)).rstrip("."),
                                    quote=_clean(m.group(0)), page=i))
            break
    joined = "\n".join(pages)
    m = _SECONDARY_START.search(joined)
    if m:
        end = _SECONDARY_END.search(joined, m.end())
        block = joined[m.end(): end.start() if end else m.end() + 1500]
        items = [_clean(x) for x in re.split(r"\n\s*•\s*", "\n" + block) if _clean(x)]
        if items:
            page = _page_of(pages, m.start())
            out.append(DocumentFact(key="secondary_diagnoses", value="; ".join(x.rstrip(".") for x in items),
                                    quote="Nebendiagnosen: " + " • ".join(items), page=page))
    return out


def _page_of(pages: list[str], offset: int) -> int:
    pos = 0
    for i, t in enumerate(pages, start=1):
        pos += len(t) + 1
        if offset < pos:
            return i
    return len(pages)
