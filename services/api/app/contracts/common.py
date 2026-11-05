"""Shared building blocks. Every fact shown to a user must carry a SourceRef."""

from enum import StrEnum

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    law = "law"                  # knowledge/extracted/legal (SozDok)
    value = "value"              # knowledge/extracted/values (veraendW)
    brochure = "brochure"        # ÖGK Serviceratgeber 2026
    form = "form"                # official form template
    document = "document"        # user-uploaded document (quote + page)
    eko = "eko"                  # Erstattungskodex
    external = "external"        # external official website (URL + retrieved date)


class SourceRef(BaseModel):
    kind: SourceKind
    label: str = Field(..., description="Human-readable citation, e.g. '§ 4 BPGG' or 'Serviceratgeber 2026, S. 63'")
    ref: str = Field("", description="Machine reference: doc_id, value key, page, URL")
    quote: str | None = Field(None, description="Verbatim quote when citing a document")
    in_force: str | None = Field(None, description="In-force date / Fassung for legal sources")


class Problem(BaseModel):
    code: str
    message_de: str
