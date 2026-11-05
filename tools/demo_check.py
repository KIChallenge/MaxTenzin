"""Preflight for the live demo: runs the demo-script chat lines against the RUNNING API (make api-demo).

Read-only for the demo state: new conversation + new draft session, no permission changes.
Usage: make demo-check   (API must run on http://localhost:8000)
"""

from __future__ import annotations

import sys
import time

import httpx

API = "http://localhost:8000"
MARIA_ANNA = {"Authorization": "Bearer demo-maria", "X-Subject-Id": "anna"}
STEFAN = {"Authorization": "Bearer demo-stefan"}
results: list[tuple[bool, str, float]] = []


def check(ok: bool, label: str, t0: float) -> None:
    results.append((ok, label, time.perf_counter() - t0))
    print(f"{'✅' if ok else '❌'} {label} ({time.perf_counter() - t0:.1f}s)", flush=True)


def chat(c: httpx.Client, h: dict, msg: str, cid: str | None = None, **extra) -> dict:
    r = c.post("/api/agent/chat", headers=h, json={"message": msg, "conversation_id": cid, **extra})
    r.raise_for_status()
    return r.json()


def tools(r: dict) -> list[str]:
    return [t["tool"] for t in r["tool_trace"]]


def main() -> int:
    with httpx.Client(base_url=API, timeout=90) as c:
        t0 = time.perf_counter()
        try:
            health = c.get("/api/health").json()
        except httpx.HTTPError as e:
            print(f"❌ API not reachable at {API}: {e}")
            return 1
        check(health.get("llm") == "live", f"API up, LLM mode = {health.get('llm')}", t0)

        t0 = time.perf_counter()
        scopes = c.get("/api/identity/me", headers=MARIA_ANNA).json()["scopes"]
        check("prepare_applications" in scopes, "Maria may prepare applications for Anna (no leftover revoke)", t0)

        t0 = time.perf_counter()
        r1 = chat(c, MARIA_ANNA, "Meine Mutter Anna wurde letzte Woche aus dem Spital entlassen. Bitte schau dir ihren "
                                 "Entlassungsbrief an – welche Leistungen kommen für sie in Frage?")
        check({"analyze_document", "check_benefits"} <= set(tools(r1)) and "Pflegegeld" in r1["reply"],
              "Akt 1: Brief → Leistungen", t0)
        cid = r1["conversation_id"]

        t0 = time.perf_counter()
        r2 = chat(c, MARIA_ANNA, "Sie braucht ungefähr 90 Stunden Hilfe im Monat, und das sicher länger als ein halbes "
                                 "Jahr.", cid)
        check("check_benefits" in tools(r2) and "Pflegegeld" in r2["reply"], "Akt 1: Fakten → Pflegegeld", t0)

        t0 = time.perf_counter()
        r3 = chat(c, MARIA_ANNA, "Bitte bereite den Pflegegeld-Antrag als Entwurf vor.", cid)
        form = next((a["url"].removeprefix("/forms/") for a in r3["actions"] if a["kind"] == "open_form"), None)
        check(form is not None, "Akt 1: Antrag gestartet, Button 'Assistent öffnen'", t0)

        if form:
            t0 = time.perf_counter()
            r4 = chat(c, MARIA_ANNA, "Trag beim Pflegegeld-Antrag ein, dass wir die kostenlose Pflegeberatung möchten. "
                                     "Meine Mutter hat zugestimmt.", form_session_id=form)
            v = c.get(f"/api/forms/sessions/{form}", headers=MARIA_ANNA).json()["values"]
            check(v["Pflegeberatung"]["value"] == "Ja" and not v["Antragstellung andere Person"]["value"]
                  and "start_form" not in tools(r4), "Akt 1: Chat → Assistent (Pflegeberatung = Ja, Zustimmung offen)", t0)
            t0 = time.perf_counter()
            pdf = c.post(f"/api/forms/sessions/{form}/render", headers=MARIA_ANNA)
            check(pdf.status_code == 200 and pdf.content[:4] == b"%PDF", "Akt 1: PDF-Entwurf", t0)

        t0 = time.perf_counter()
        rb = chat(c, MARIA_ANNA, "Ist ihr Tumor jetzt weg?")
        check(rb["boundary_triggered"] and not rb["tool_trace"], "Akt 2: Grenze (keine Befundinterpretation)", t0)

        t0 = time.perf_counter()
        prev = c.get("/api/prevention/overview", headers=STEFAN).json()
        flu = next((i for i in prev["items"] if i["id"] == "influenza"), {})
        check(flu.get("status") == "due", "Akt 4: Stefan – Grippeimpfung fällig (Impfpass importiert)", t0)

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} ok" + ("" if not failed else " – siehe Fallbacks im Drehbuch"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
