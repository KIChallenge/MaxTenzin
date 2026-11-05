"""Copy blank official form templates into knowledge/forms/templates and dump their fields/text.

For AcroForm PDFs (FSW) the named fields are dumped (name, type, options) -> basis for form schemas + real PDF fill.
For flat PDFs (SV forms) the page text is dumped -> basis for the hand-written field schema + Antragsentwurf rendering.
"""

from __future__ import annotations

import shutil

from pypdf import PdfReader

from common import RAW_DIR, REPO_ROOT, record, write_json

TEMPLATES_DIR = REPO_ROOT / "knowledge" / "forms" / "templates"

FORMS = {
    "fsw_foerderung": "Anträge und Formulare/fsw-antrag-auf-foerderung-von-leistungen.1779095804.pdf",
    "fsw_einrichtungswunsch": "Anträge und Formulare/FSW-Antrag-Beilage-Einrichtungswunsch.1779345450.pdf",
    "fsw_senioren_wg": "Anträge und Formulare/Bedarfsmeldung-Senior_innen-Wohngemeinschaft_Basispaket.1736522017.pdf",
    "pva_pflegegeld_pal080": "Anträge und Formulare/PAL080_0125_Mpfl_052026.pdf",
    "sv_kur_reha": "Anträge und Formulare/Antrag Kur und Reha.pdf",
    "sv_reha_nach_unfall": "Anträge und Formulare/Reha_n_Unfall_052026.pdf",
    "oegk_fahrtkosten_wien": "Anträge und Formulare/Antrag-auf-Zuschuss-zu-Fahrtkosten_Wien.pdf",
}

FIELD_TYPES = {"/Tx": "text", "/Btn": "checkbox_or_radio", "/Ch": "choice", "/Sig": "signature"}


def dump_fields(reader: PdfReader) -> list[dict]:
    fields = reader.get_fields() or {}
    out = []
    for name, f in fields.items():
        ft = f.get("/FT")
        states = f.get("/_States_", [])
        out.append(
            {
                "name": name,
                "type": FIELD_TYPES.get(ft, str(ft)),
                "states": [str(s) for s in states] if states else None,
                "tooltip": str(f.get("/TU")) if f.get("/TU") else None,
            }
        )
    return sorted(out, key=lambda x: x["name"])


def main() -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    sources, outputs, total = [], [], 0
    for form_id, rel in FORMS.items():
        src = RAW_DIR / rel
        reader = PdfReader(str(src))
        pdf_out = TEMPLATES_DIR / f"{form_id}.pdf"
        shutil.copyfile(src, pdf_out)
        fields = dump_fields(reader)
        meta = {
            "form_id": form_id,
            "source_file": rel,
            "pages": len(reader.pages),
            "fillable": bool(fields),
            "fields": fields,
            "page_text": [p.extract_text() or "" for p in reader.pages],
        }
        meta_out = TEMPLATES_DIR / f"{form_id}.fields.json"
        write_json(meta_out, meta)
        sources.append(src)
        outputs += [pdf_out, meta_out]
        total += len(fields)
        print(f"forms: {form_id}: {len(reader.pages)} pages, {len(fields)} fields")
    record("form_templates", sources=sources, outputs=outputs, rows=total, notes="blank official templates")


if __name__ == "__main__":
    main()
