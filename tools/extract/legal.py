"""Extract allowlisted legal paragraphs from the SozDok XML corpus (docs/Rechtstexte) into JSONL.

One output row per paragraph file. Deterministic: no LLM, sorted output.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from common import OUT_DIR, RAW_DIR, record, write_jsonl

# Laws/guidelines relevant for the KI-Lotse benefit navigation (see documentation/sources.md).
ALLOWLIST = {
    "ASVG": "core social insurance law (Krankenversicherung, Reha, Rezeptgebühr, Ausgleichszulage)",
    "BPGG": "Pflegegeld",
    "RPGG_2012": "Pflegegeld application guidelines",
    "RRZ_2008": "Rezeptgebührenbefreiung",
    "RRK_2021": "Rehabilitation guidelines",
    "RBZRehab_2005": "Reha co-payment exemption",
    "RFG_2020": "ÖGK Festigung der Gesundheit",
    "RGFP": "Gesundheitsförderung und Prävention",
    "RVU": "Vorsorgeuntersuchung",
    "RJU_2016": "Jugendlichenuntersuchung",
    "RUF_2020": "ÖGK Unterstützungsfonds",
    "RBA": "Nachsicht Behandlungsbeitrag-Ambulanz",
    "RBS_2005": "Befreiung Service-Entgelt",
    "KrankenO_OEGK_2025": "ÖGK Krankenordnung (Transport, Hauskrankenpflege)",
    "Satzung_OEGK_2025": "ÖGK Satzung (Mehrleistungen, Zuschüsse)",
    "FLAG": "Familienbeihilfe",
    "KBGG": "Kinderbetreuungsgeld",
    "MuKiPassV_2002": "Mutter-Kind-Pass",
    "VO-EKO": "Erstattungskodex procedure",
}

BLOCK_TAGS = {"absatz", "schluss", "listelem", "ueberschrift", "tr", "zeile"}


def _text_of(elem: ET.Element) -> str:
    """Flatten an element to readable text, one line per block element."""
    parts: list[str] = []

    def walk(e: ET.Element) -> None:
        tag = e.tag.split("}")[-1]
        if e.text:
            parts.append(e.text)
        for c in e:
            walk(c)
            if c.tail:
                parts.append(c.tail)
        if tag in BLOCK_TAGS:
            parts.append("\n")
        elif tag == "td":
            parts.append(" | ")

    walk(elem)
    text = html.unescape("".join(parts))
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip(" |") for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln.strip())


def parse_file(path: Path) -> dict | None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    meta = root.find(".//metadaten")
    nutz = root.find(".//nutzdaten")
    if meta is None or nutz is None:
        return None
    a = meta.attrib
    headings = [_text_of(h).replace("\n", " ") for h in nutz.iter("ueberschrift")]
    text = _text_of(nutz)
    return {
        "doc_id": root.attrib.get("dokid", path.stem),
        "law_key": path.name.split("=")[0],
        "law": a.get("abkrvo", path.name.split("=")[0]),
        "law_title": a.get("titrvo", ""),
        "type": a.get("gldart", ""),
        "nr": a.get("gldnr", ""),
        "heading": " – ".join(h for h in headings if h)[:300],
        "text": text,
        "in_force": a.get("ikra", ""),
        "published": a.get("pubdat", ""),
        "amendment": a.get("titaen", ""),
        "topics": sorted(t.strip() for t in a.get("berkz", "").split(";") if t.strip()),
        "source_file": path.name,
    }


def main() -> None:
    src_dir = RAW_DIR / "Rechtstexte"
    files = sorted(p for p in src_dir.glob("*.xml") if p.name.split("=")[0] in ALLOWLIST)
    rows = [r for r in (parse_file(p) for p in files) if r and r["text"]]
    rows.sort(key=lambda r: (r["law_key"], r["doc_id"]))
    out = OUT_DIR / "legal" / "paragraphs.jsonl"
    write_jsonl(out, rows)
    laws = {r["law_key"] for r in rows}
    record(
        "legal_paragraphs",
        sources=files,
        outputs=[out],
        rows=len(rows),
        notes=f"allowlist={sorted(ALLOWLIST)}; laws_found={len(laws)}",
    )
    print(f"legal: {len(rows)} paragraphs from {len(laws)} laws -> {out}")


if __name__ == "__main__":
    main()
