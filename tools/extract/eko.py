"""Extract the Erstattungskodex (EKO) fixed-width export into JSONL (administrative lookup only).

Column offsets (0-based) were measured on the 195-char lines of medikament.txt; validated in tests.
Legend per 'Zeichenerklärungen und Abkürzungen.pdf' (EKO 1/2024, S. 20–24).
"""

from __future__ import annotations

import re
from pathlib import Path

from common import OUT_DIR, RAW_DIR, record, write_json, write_jsonl

LEGEND = {
    "box": {
        "G": "Grüner Bereich – frei verschreibbar (keine Bewilligung durch den chef-/kontrollärztlichen Dienst nötig)",
        "Y": "Gelber Bereich – nur mit Bewilligung bzw. nachfolgender Kontrolle (siehe RE1/RE2)",
    },
    "restriction": {
        "RE1": "Abgabe nur nach vorheriger Bewilligung durch den chef-/kontrollärztlichen Dienst",
        "RE2": "Bewilligung ersetzt durch nachfolgende Kontrolle, wenn die angegebene Verwendung vorliegt und dokumentiert ist",
        "IND": "Nur für die angeführten Indikationen; Ärztin/Arzt vermerkt 'IND' auf dem Rezept",
        "F14": "Grüner Bereich nur bis zum vollendeten 14. Lebensjahr",
        "F6J": "Grüner Bereich nur bis zum vollendeten 6. Lebensjahr",
        "F2J": "Grüner Bereich nur bis zum vollendeten 2. Lebensjahr",
        "SPECIALIST": "Grüner Bereich nur bei Erstverordnung durch die angeführte Fachrichtung (Folgeverordnung durch Allgemeinmedizin möglich)",
    },
    "divisibility": "T2/T3/T4: Tablette in 2/3/4 gleiche Teile teilbar",
    "max_packs": "Höchstanzahl der Originalpackungen pro Rezept",
    "source": "Zeichenerklärungen und Abkürzungen.pdf (EKO 1/2024, S. 20–24)",
}

LINE = re.compile(r"^\|(\d+)\|;\|(.*)\|\s*$")


def read_texts(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        m = LINE.match(line.strip())
        if m:
            out.setdefault(m.group(1), []).append(m.group(2).strip())
    return out


def parse_line(line: str) -> dict:
    restr = line[121:124].strip()
    return {
        "pharma_nr": line[0:7].strip(),
        "product_id": line[9:15].strip(),
        "name": line[18:118].strip(),
        "box": line[118].strip(),
        "restriction": restr,
        "pack": line[124:131].strip(),
        "price_eur": int(line[131:140]) / 100 if line[131:140].strip().isdigit() else None,
        "unit_price_raw": line[140:150].strip(),
        "divisible": line[158:160].strip() or None,
        "price_model_flag": line[161:162].strip() == "M",
        "max_packs": int(line[164]) if line[164:165].strip().isdigit() else None,
        "note": line[166:].strip() or None,
    }


def main() -> None:
    d = RAW_DIR / "Medikamenten Erstattungskodex"
    src = [d / "medikament.txt", d / "regeltext.txt", d / "indtext.txt", d / "Zeichenerklärungen und Abkürzungen.pdf"]
    regel = read_texts(d / "regeltext.txt")
    ind = read_texts(d / "indtext.txt")
    rows = []
    for raw in (d / "medikament.txt").read_text(encoding="latin-1").splitlines():
        raw = raw.rstrip("\r\n")
        if len(raw) < 160:
            continue
        r = parse_line(raw)
        r["rule_text"] = " ".join(regel.get(r["pharma_nr"], [])) or None
        r["indication_text"] = " ".join(ind.get(r["pharma_nr"], [])) or None
        rows.append(r)
    rows.sort(key=lambda r: r["pharma_nr"])
    out = OUT_DIR / "eko" / "medications.jsonl"
    legend_out = OUT_DIR / "eko" / "legend.json"
    write_jsonl(out, rows)
    write_json(legend_out, LEGEND)
    record("eko_medications", sources=src, outputs=[out, legend_out], rows=len(rows),
           notes="unit_price_raw semantics not documented in legend; kept raw")
    print(f"eko: {len(rows)} packs -> {out}")


if __name__ == "__main__":
    main()
