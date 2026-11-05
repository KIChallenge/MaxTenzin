"""Preflight for the live demo: checks the demo-script scenes against the RUNNING API (make api-demo).

Does NOT change the demo state the jury will see: no booking, no Lebenslage confirmation, no permission changes.
(It creates a draft form session and conversations, which the demo never shows.)
Usage: make demo-check            (API on http://localhost:8000)
       DEMO_API=http://localhost:8001 make demo-check
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import httpx

API = os.environ.get("DEMO_API", "http://localhost:8000")
ROOT = Path(__file__).resolve().parents[1]
MARIA_ANNA = {"Authorization": "Bearer demo-maria", "X-Subject-Id": "anna"}
ANNA = {"Authorization": "Bearer demo-anna"}
STEFAN = {"Authorization": "Bearer demo-stefan"}
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, t0: float, hint: str = "") -> bool:
    results.append((ok, label))
    print(f"{'✅' if ok else '❌'} {label} ({time.perf_counter() - t0:.1f}s)" + (f"\n   → {hint}" if not ok and hint else ""),
          flush=True)
    return ok


def chat(c: httpx.Client, h: dict, msg: str, cid: str | None = None, **extra) -> dict:
    r = c.post("/api/agent/chat", headers=h, json={"message": msg, "conversation_id": cid, **extra})
    r.raise_for_status()
    return r.json()


def tools(r: dict) -> list[str]:
    return [t["tool"] for t in r["tool_trace"]]


def main() -> int:
    with httpx.Client(base_url=API, timeout=120) as c:
        t0 = time.perf_counter()
        try:
            health = c.get("/api/health").json()
        except httpx.HTTPError as e:
            print(f"❌ API not reachable at {API}: {e}")
            return 1
        check(health.get("llm") == "live", f"API up, LLM mode = {health.get('llm')}", t0, "AZURE_API_KEY in .env prüfen")

        # ---------------- state: fresh demo data, nothing left over from rehearsals
        t0 = time.perf_counter()
        photos = sorted((ROOT / "var" / "demo").glob("entlassungsbrief-foto-*.jpg"))
        check(len(photos) == 4, f"Demo-Fotos vorhanden ({len(photos)}/4)", t0, "make demo-assets")
        t0 = time.perf_counter()
        scopes = set(c.get("/api/identity/me", headers=MARIA_ANNA).json()["scopes"])
        need = {"prepare_applications", "manage_situation", "manage_appointments", "read_documents"}
        check(need <= scopes and "view_health_prevention" not in scopes,
              "Vollmacht Anna→Maria im Seed-Zustand (ohne Vorsorge)", t0, "make reset && make seed")
        t0 = time.perf_counter()
        sit = c.get("/api/situation", headers=MARIA_ANNA).json()
        check(not (sit["current"] or sit["upcoming"] or sit["past"]), "Lebenslage von Anna leer (Szene: Vorschläge übernehmen)",
              t0, "make reset && make seed")
        t0 = time.perf_counter()
        appts = [a for a in c.get("/api/appointments", headers=MARIA_ANNA).json() if a["status"] == "booked"]
        check(not appts, "keine gebuchten Termine von der Probe übrig", t0, "make reset && make seed")

        # ---------------- Akt 1
        t0 = time.perf_counter()
        team = c.get("/api/identity/care-team", headers=MARIA_ANNA).json()["members"]
        gp = next((m for m in team if m["role"] == "hausarzt"), None)
        check(gp is not None, f"Behandlungsteam: Hausärztin = {gp and gp['name']}", t0)
        t0 = time.perf_counter()
        analysis = c.get("/api/documents/doc-anna-entlassung/analysis", headers=MARIA_ANNA)
        facts = {f["key"] for f in analysis.json().get("facts", [])} if analysis.status_code == 200 else set()
        check({"discharge_date", "main_diagnosis"} <= facts, "Demo-Brief analysiert (Entlassungsdatum, Hauptdiagnose)", t0,
              "make seed (Analysen aktualisieren)")
        t0 = time.perf_counter()
        el = c.post("/api/benefits/eligibility", headers=MARIA_ANNA,
                    json={"subject_id": "anna", "document_ids": ["doc-anna-entlassung"], "benefit_ids": ["pflegegeld"]}).json()
        amount = (el[0].get("amounts") or [{}])[0].get("value") if el else None
        check(amount == 206.2, f"Leistungen: Pflegegeld Stufe 1 2026 = {amount} € (veraendW)", t0)

        t0 = time.perf_counter()
        r1 = chat(c, MARIA_ANNA, "Bitte bereite den Pflegegeld-Antrag als Entwurf vor.", document_ids=["doc-anna-entlassung"])
        form = next((a["url"].removeprefix("/forms/") for a in r1["actions"] if a["kind"] == "open_form"), None)
        check(form is not None, "Akt 1: Antrag per Chat gestartet, Button 'Assistent öffnen'", t0)
        if form:
            v = c.get(f"/api/forms/sessions/{form}", headers=MARIA_ANNA).json()["values"]
            t0 = time.perf_counter()
            check(bool((v.get("Leiden") or {}).get("value")), "Akt 1: 'Krankheiten' wörtlich aus dem Brief vorausgefüllt", t0)
            t0 = time.perf_counter()
            r2 = chat(c, MARIA_ANNA, "Trag beim Pflegegeld-Antrag ein, dass wir die kostenlose Pflegeberatung möchten. "
                                     "Meine Mutter hat zugestimmt.", form_session_id=form)
            v = c.get(f"/api/forms/sessions/{form}", headers=MARIA_ANNA).json()["values"]
            check(v["Pflegeberatung"]["value"] == "Ja" and not v["Antragstellung andere Person"]["value"]
                  and "start_form" not in tools(r2) and r2["reply"].startswith("**Eingetragen im Antrag:**"),
                  "Akt 1: Chat → Assistent (Pflegeberatung = Ja, Zustimmung offen)", t0)
            t0 = time.perf_counter()
            pdf = c.post(f"/api/forms/sessions/{form}/render", headers=MARIA_ANNA)
            check(pdf.status_code == 200 and pdf.content[:4] == b"%PDF", "Akt 1: PDF-Entwurf", t0)

        t0 = time.perf_counter()
        slots = c.post("/api/appointments/slots/search", headers=MARIA_ANNA,
                       json={"provider_id": gp["provider_id"] if gp else None, "daypart": "morning", "limit": 5}).json()
        check(len(slots) >= 3, f"Akt 1: freie Vormittagstermine bei der Hausärztin ({len(slots)})", t0)

        # ---------------- Akt 1: Rezeptgebühr (Aufgabe aus dem Brief) + Erstattungskodex
        t0 = time.perf_counter()
        rr = chat(c, MARIA_ANNA, "Muss meine Mutter für ihre Medikamente Rezeptgebühr zahlen?", document_ids=["doc-anna-entlassung"])
        check("check_benefits" in tools(rr) and "7,55" in rr["reply"],
              "Akt 1: Rezeptgebühr – Anspruchsprüfung, 7,55 € (veraendW), Brief S. 6", t0)
        t0 = time.perf_counter()
        rm = chat(c, MARIA_ANNA, "Was kostet Pantoprazol auf Rezept?", rr["conversation_id"])
        check("search_medication" in tools(rm) and not re.search(r"dosierung|einnehmen|nehmen sie", rm["reply"], re.IGNORECASE),
              "Akt 1: Erstattungskodex-Abfrage (nur administrativ)", t0)

        # ---------------- Akt 2
        t0 = time.perf_counter()
        rb = chat(c, MARIA_ANNA, "Ist ihr Tumor jetzt weg?")
        check(rb["boundary_triggered"] and not rb["tool_trace"], "Akt 2: Grenze (keine Befundinterpretation)", t0)

        # ---------------- Akt 4
        t0 = time.perf_counter()
        rg = chat(c, STEFAN, "Ich möchte etwas für meine Gesundheit tun.")
        check(bool({"match_bundle", "get_prevention"} & set(tools(rg))), "Akt 4: Stefan – Gesundheits-Bündel", t0)
        t0 = time.perf_counter()
        prev = c.get("/api/prevention/overview", headers=STEFAN).json()
        flu = next((i for i in prev["items"] if i["id"] == "influenza"), {})
        check(flu.get("status") == "due", "Akt 4: Stefan – Grippeimpfung fällig (Impfpass importiert)", t0, "make seed")

        # ---------------- Akt 4: Arzttermin-Dialog, Kind, Personalisierung
        t0 = time.perf_counter()
        ra = chat(c, STEFAN, "Ich möchte einen Arzttermin.")
        ra2 = chat(c, STEFAN, "Zur Kontrolle beim Hausarzt. Ja, gern in der Nähe, und vormittags.", ra["conversation_id"])
        check(not tools(ra) and "?" in ra["reply"] and "search_slots" in tools(ra2)
              and any(a["kind"] == "choose_slot" for a in ra2["actions"]),
              "Akt 4: Arzttermin – Rückfrage zum Anlass → Vormittagstermine angeboten (nicht gebucht)", t0)
        t0 = time.perf_counter()
        rk = chat(c, STEFAN, "Ich habe ein Kind und möchte wissen, welche Angebote es gibt.")
        check("match_bundle" in tools(rk) and "Eltern-Kind-Pass" in rk["reply"], "Akt 4: Kind-Bündel (Eltern-Kind-Pass …)", t0)
        t0 = time.perf_counter()
        ren = chat(c, MARIA_ANNA, "What is my mother entitled to after her hospital stay?", document_ids=["doc-anna-entlassung"])
        low = ren["reply"].lower()
        check("check_benefits" in tools(ren) and " the " in low and "in question" not in low and "into question" not in low,
              "Akt 4: englische Antwort (vollständig Englisch, keine Germanismen)", t0, "API nach git pull neu gestartet?")
        t0 = time.perf_counter()
        rp = chat(c, MARIA_ANNA, "Was ist Pflegegeld und wer entscheidet darüber?", plain_language=True)
        check(bool({"get_benefit", "check_benefits"} & set(tools(rp))), "Akt 4: Einfache Sprache", t0)

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} ok" + ("" if not failed else " – siehe Hinweise / Fallbacks im Drehbuch"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
