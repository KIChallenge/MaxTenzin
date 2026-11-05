"""Extract the 'veränderliche Werte' (yearly value tables, veraendW) from the SozDok corpus.

Output: knowledge/extracted/values/veraendw.json
  values[]: {table, key, label_de, year, value, unit, legal_ref, bgbl}   (curated, column-mapped tables)
  tables{}: {nr: {title, rows: [[cell, ...], ...]}}                      (all tables, raw rows, for search/audit)
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from common import OUT_DIR, RAW_DIR, record, write_json

# table nr -> (legal_ref, {column index: (key, label_de, unit)})
MAPPINGS: dict[str, tuple[str, dict[int, tuple[str, str, str]]]] = {
    "54": (
        "§ 5 BPGG",
        {i: (f"pflegegeld_stufe_{i}", f"Pflegegeld Stufe {i} (monatlich)", "EUR") for i in range(1, 8)},
    ),
    "20": (
        "§ 136 ASVG; RRZ 2008",
        {
            1: ("rezeptgebuehr", "Rezeptgebühr pro Packung", "EUR"),
            2: ("rgb_befreiungsgrenze_alleinstehend", "Befreiungsgrenze Rezeptgebühr – alleinstehend (netto/Monat)", "EUR"),
            3: ("rgb_befreiungsgrenze_paar", "Befreiungsgrenze Rezeptgebühr – Ehepaare/Lebensgemeinschaften", "EUR"),
            6: ("rgb_erhoehung_pro_kind", "Erhöhung der Befreiungsgrenze pro Kind", "EUR"),
        },
    ),
    "25": (
        "§ 154a Abs. 7 ASVG",
        {
            1: ("reha_zuzahlung_frei_bis", "Reha: keine Zuzahlung bis mtl. Bruttoeinkommen", "EUR"),
            2: ("reha_stufe1_bis", "Reha: Zuzahlungsstufe 1 bis mtl. Bruttoeinkommen", "EUR"),
            3: ("reha_stufe1_pro_tag", "Reha: Zuzahlung Stufe 1 pro Verpflegstag", "EUR"),
            4: ("reha_stufe2_bis", "Reha: Zuzahlungsstufe 2 bis mtl. Bruttoeinkommen", "EUR"),
            5: ("reha_stufe2_pro_tag", "Reha: Zuzahlung Stufe 2 pro Verpflegstag", "EUR"),
            7: ("reha_stufe3_pro_tag", "Reha: Zuzahlung Stufe 3 pro Verpflegstag (darüber)", "EUR"),
        },
    ),
    "53": ("§§ 3, 8, 9 KBGG", {1: ("kbg_taeglich", "Kinderbetreuungsgeld pro Tag", "EUR")}),
    "46": (
        "§ 293 Abs. 1 ASVG",
        {
            1: ("az_richtsatz_paar", "Ausgleichszulage-Richtsatz – Ehepaar im gemeinsamen Haushalt", "EUR"),
            2: ("az_richtsatz_alleinstehend", "Ausgleichszulage-Richtsatz – alleinstehend", "EUR"),
            4: ("az_erhoehung_pro_kind", "Ausgleichszulage – Erhöhung pro Kind", "EUR"),
        },
    ),
}

YEAR = re.compile(r"^(19|20)\d{2}$")
NUM = re.compile(r"-?\d[\d\s\xa0.]*,\d+|-?\d[\d\s\xa0]*")


def cell_text(td: ET.Element) -> str:
    return re.sub(r"\s+", " ", html.unescape("".join(td.itertext()))).strip()


def to_number(s: str) -> float | None:
    m = NUM.search(s)
    if not m:
        return None
    raw = re.sub(r"[\s\xa0.]", "", m.group(0)).replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_table_file(path: Path) -> tuple[str, str, list[list[str]]]:
    root = ET.parse(path).getroot()
    nr = path.name.split("=")[2]
    nutz = root.find(".//nutzdaten")
    title = ""
    if nutz is not None:
        h = nutz.find(".//ueberschrift")
        title = cell_text(h) if h is not None else ""
    rows = []
    for t in root.iter("table"):
        for tr in t.iter("tr"):
            cells = [cell_text(td) for td in tr.iter("td")]
            if any(cells):
                rows.append(cells)
    return nr, title, rows


def main() -> None:
    files = sorted((RAW_DIR / "Rechtstexte").glob("veraendW=*.xml"))
    tables: dict[str, dict] = {}
    values: list[dict] = []
    for f in files:
        try:
            nr, title, rows = parse_table_file(f)
        except ET.ParseError:
            continue
        if not nr:
            continue
        tables[nr] = {"title": title, "rows": rows, "source_file": f.name}
        if nr not in MAPPINGS:
            continue
        legal_ref, cols = MAPPINGS[nr]
        for row in rows:
            if not row or not YEAR.match(row[0]):
                continue
            year = int(row[0])
            bgbl = next((c for c in reversed(row) if "BGBl" in c), "")
            for idx, (key, label, unit) in cols.items():
                if idx >= len(row):
                    continue
                v = to_number(row[idx])
                if v is None:
                    continue
                values.append(
                    {
                        "table": int(nr) if nr.isdigit() else nr,
                        "key": key,
                        "label_de": label,
                        "year": year,
                        "value": v,
                        "unit": unit,
                        "legal_ref": legal_ref,
                        "bgbl": bgbl,
                        "source": f"veraendW Tabelle {nr} ({f.name})",
                    }
                )
    values.sort(key=lambda r: (r["key"], -r["year"]))
    out = OUT_DIR / "values" / "veraendw.json"
    write_json(out, {"values": values, "tables": tables})
    record(
        "veraendw_values",
        sources=files,
        outputs=[out],
        rows=len(values),
        notes=f"mapped tables={sorted(MAPPINGS)}; raw tables={len(tables)}",
    )
    print(f"values: {len(values)} mapped values, {len(tables)} raw tables -> {out}")


if __name__ == "__main__":
    main()
