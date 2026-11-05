"""Deterministic e-Impfpass parser (pypdf text of an ELGA e-Impfpass PDF export). No LLM.

Layout (per entry, grouped under a disease heading that may continue across pages):
    COVID-19                          <- disease heading
    3. Nov. 2025                      <- entry start
     Impfstoff: COMIRNATY LP.8.1 ...
    Impfdatum: 3. November 2025 ...
    Auffrischung | Dosis 1            <- dose label
     Impfort: Heinestraße 11/12
    1020 Wien, Wien                   <- zip + city
"""

from __future__ import annotations

import re

from app.contracts.prevention import VaccinationEntry

MONTHS = {
    "jänner": 1, "januar": 1, "jän": 1, "jan": 1, "februar": 2, "feb": 2, "märz": 3, "mär": 3, "mrz": 3,
    "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "oktober": 10, "okt": 10, "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

# Canonical disease names. Keys are lower-case prefixes as they appear in e-Impfpass headings.
DISEASES = {
    "covid-19": "COVID-19", "influenza": "Influenza", "fsme": "FSME", "frühsommer-meningoenzephalitis": "FSME",
    "tetanus": "Tetanus", "diphtherie": "Diphtherie", "pertussis": "Pertussis", "poliomyelitis": "Polio",
    "polio": "Polio", "masern": "Masern", "mumps": "Mumps", "röteln": "Röteln", "hepatitis a": "Hepatitis A",
    "hepatitis b": "Hepatitis B", "hpv": "HPV", "humane papillomaviren": "HPV", "pneumokokken": "Pneumokokken",
    "herpes zoster": "Herpes zoster", "gürtelrose": "Herpes zoster", "varizellen": "Varizellen",
    "meningokokken": "Meningokokken", "rotavirus": "Rotavirus", "haemophilus influenzae": "Haemophilus influenzae b",
    "rsv": "RSV", "respiratorisches synzytial-virus": "RSV",
}

_DATE_LINE = re.compile(r"^(\d{1,2})\.\s*([A-Za-zÄÖÜäöü]+)\.?\s+(\d{4})$")
_IMPFDATUM = re.compile(r"Impfdatum:\s*(\d{1,2})\.\s*([A-Za-zÄÖÜäöü]+)\.?\s+(\d{4})")
_DOSE = re.compile(r"^(Auffrischung|Dosis \d+|Grundimmunisierung.*|Nachholimpfung.*|Einzeldosis)$")
_ZIP_CITY = re.compile(r"^(\d{4})\s+([^,]+)")


def _iso(day: str, month: str, year: str) -> str | None:
    m = MONTHS.get(month.lower().rstrip("."))
    return f"{int(year):04d}-{m:02d}-{int(day):02d}" if m else None


def _disease_heading(line: str) -> str | None:
    """'Influenza ('echte Grippe')' -> 'Influenza'; 'Diphtherie, Tetanus, ...' -> 'Diphtherie-Tetanus-...'."""
    if ":" in line or not line or line[0].isdigit():
        return None
    base = re.sub(r"\s*\(.*\)\s*$", "", line).strip()
    parts = [p.strip().lower() for p in re.split(r"[,/+]| und ", base) if p.strip()]
    names = []
    for p in parts:
        name = next((v for k, v in DISEASES.items() if p == k or p.startswith(k + " ")), None)
        if name is None:
            return None
        names.append(name)
    return "-".join(dict.fromkeys(names)) if names else None


def parse_impfpass(pages: list[str]) -> list[VaccinationEntry]:
    entries: list[VaccinationEntry] = []
    disease: str | None = None
    cur: dict | None = None
    expect_place = False

    def flush():
        nonlocal cur
        if cur and cur.get("date") and cur.get("disease"):
            entries.append(VaccinationEntry(**cur))
        cur = None

    for line in (ln.strip() for page in pages for ln in page.splitlines()):
        if not line:
            continue
        heading = _disease_heading(line)
        if heading:
            flush()
            disease = heading
            continue
        m = _DATE_LINE.match(line)
        if m and disease and _iso(*m.groups()):
            flush()
            cur = {"disease": disease, "date": _iso(*m.groups()), "vaccine": "", "dose_label": "", "place": ""}
            continue
        if cur is None:
            continue
        if line.startswith("Impfstoff:"):
            cur["vaccine"] = line.removeprefix("Impfstoff:").strip()
        elif (m := _IMPFDATUM.search(line)) and _iso(*m.groups()):
            cur["date"] = _iso(*m.groups())  # full date wins over the abbreviated heading date
        elif _DOSE.match(line):
            cur["dose_label"] = line
        elif line.startswith("Impfort:"):
            expect_place = True
        elif expect_place:
            expect_place = False
            if z := _ZIP_CITY.match(line):
                cur["place"] = f"{z.group(1)} {z.group(2).strip()}"
    flush()
    return entries
