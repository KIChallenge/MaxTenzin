"""Deterministic scripted planner (LLM_MODE=fake, or fallback when the live model fails).

Same tools, same HTTP calls, same guards as the live orchestrator — only intent detection and wording are scripted.
Covers the three demo scenarios so the demo never dies offline: (1) Maria/Anna hero flow, (2) Stefan prevention,
(3) boundary (handled by the guard before this runs).
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from app.agent.state import DEMO_DOCUMENTS
from app.agent.tools import SCOPE_DE, STATUS_DE, ToolOutcome

Run = Callable[[str, dict], Awaitable[ToolOutcome]]

FACT_QUESTIONS_DE = {
    "care_hours_estimate": "Wie viele Stunden Hilfe im Monat braucht {name} ungefähr (z. B. beim Waschen, Anziehen, "
                           "Kochen, Einkaufen)? Eine grobe Schätzung reicht.",
    "care_need_months": "Wird die Unterstützung voraussichtlich mindestens sechs Monate nötig sein?",
    "net_income_monthly": "Wie hoch ist das monatliche Nettoeinkommen von {name} ungefähr (in Euro)?",
    "home_nursing_ordered": "Hat eine Ärztin bzw. ein Arzt Hauskrankenpflege verordnet?",
    "walking_unable_confirmed": "Hat eine Ärztin bzw. ein Arzt bestätigt, dass {name} nicht selbst gehen bzw. "
                                "öffentliche Verkehrsmittel nutzen kann?",
    "treatment_type": "Um welche Behandlung geht es bei den Fahrten (z. B. Strahlentherapie, Chemotherapie)?",
    "distance_km": "Wie weit ist der Behandlungsort ungefähr entfernt (in km, eine Strecke)?",
    "rgb_exempt": "Ist {name} bereits von der Rezeptgebühr befreit?",
    "gross_income_monthly": "Wie hoch ist das monatliche Bruttoeinkommen ungefähr?",
    "costs_eur": "Wie hoch sind die Kosten, um die es geht (in Euro)?",
}
BOOL_FACTS = {"care_need_months": 6}  # yes -> numeric value


def _n(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _yes_no(text: str) -> bool | None:
    t = _n(text)
    if re.search(r"\b(nein|nicht|no|hayır|keine?)\b", t):
        return False
    if re.search(r"\b(ja|jawohl|genau|yes|evet|bitte|gerne|ok)\b", t):
        return True
    return None


def _number(text: str) -> float | None:
    m = re.search(r"\d+(?:[.,]\d+)?", text)
    return float(m.group(0).replace(",", ".")) if m else None


def _eur(v) -> str:
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    except (TypeError, ValueError):
        return str(v)


def _sources_line(outcomes: list[ToolOutcome], n: int = 6) -> str:
    seen: list[str] = []
    for o in outcomes:
        for s in o.sources:
            if s not in seen:
                seen.append(s)
    return ("\n\n**Quellen:** " + "; ".join(seen[:n])) if seen else ""


def forbidden_text(o: ToolOutcome, subject_name: str) -> str:
    scope_de = SCOPE_DE.get(o.forbidden_scope or "", "diese Aktion")
    return (f"Dafür hat {subject_name} keine Berechtigung erteilt (fehlende Freigabe: „{scope_de}“). Ich umgehe das "
            f"nicht. {subject_name.split()[0]} kann die Berechtigung im Bereich „Vertretung“ selbst erteilen – danach "
            "mache ich gerne weiter.")


class Scripted:
    def __init__(self, run: Run, memo: dict, subject_id: str, subject_name: str, actor_is_subject: bool):
        self.run = run
        self.memo = memo
        self.subject_id = subject_id
        self.name = subject_name if not actor_is_subject else "Sie"
        self.subject_name = subject_name
        self.outcomes: list[ToolOutcome] = []

    async def call(self, tool: str, args: dict) -> ToolOutcome:
        o = await self.run(tool, args)
        self.outcomes.append(o)
        return o

    def _denied(self, o: ToolOutcome) -> str | None:
        return forbidden_text(o, self.subject_name) if o.status == 403 else None

    # ---------------------------------------------------------------- entry
    async def reply(self, message: str) -> str:
        t = _n(message)
        m = self.memo
        if re.search(r"impf|vorsorge|prevention|vaccin|aşı|check-?up|gesundenuntersuchung", t):
            return await self.prevention()
        if m.get("form_session_id") and re.search(r"\bpdf\b|entwurf (erstellen|erzeugen)|fertig|ausdruck|render", t):
            return await self.render()
        if re.search(r"zuständig|wohin|adresse|\bstelle\b|schicken|senden|office", t):
            return await self.office()
        if re.search(r"fall anlegen|mein fall|fall erstellen|aufgabenliste|create a case", t):
            return await self.case()
        if m.get("form_session_id") and re.search(r"\bpdf\b|entwurf (erstellen|erzeugen)|fertig|ausdruck|render", t):
            return await self.render()
        if re.search(r"antrag|formular|beantrag|ausfüllen|application|başvuru", t) and not m.get("open_questions"):
            return await self.start_form(t)
        if m.get("form_session_id") and m.get("open_questions") and not m.get("form_rendered"):
            return await self.answer_form(message)
        if m.get("pending_facts"):
            r = await self.answer_facts(message)
            if r:
                return r
        if re.search(r"entlass|dokument|brief|befund|zusteh|leistung|unterstützung|hilfe|spital|krankenhaus|"
                     r"what can|entitled|document|discharge|benefit|hak", t):
            return await self.documents_and_benefits()
        if (m2 := re.search(r"pflegegeld|reha|rezeptgebühr|fahrtkosten", t)):
            return await self.explain_benefit(m2.group(0))
        return ("Ich bin Ihr KI-Lotse für die Sozialversicherung. Ich kann zum Beispiel einen Entlassungsbrief auf "
                "ausdrücklich dokumentierte Empfehlungen prüfen, passende Leistungen ermitteln, einen Antrag als "
                "Entwurf vorbereiten oder fällige Vorsorge anzeigen. Womit soll ich beginnen?")

    # ---------------------------------------------------------------- flows
    async def documents_and_benefits(self) -> str:
        docs = await self.call("list_documents", {})
        if d := self._denied(docs):
            return d
        candidates = list(docs.data or []) + DEMO_DOCUMENTS.get(self.subject_id, [])
        doc = next((x for x in candidates if x.get("doc_type") == "discharge_letter"), None)
        if doc is None:
            return ("Ich habe kein Entlassungsdokument gefunden. Laden Sie den Entlassungsbrief bitte unter "
                    "„Dokumente“ hoch – dann prüfe ich ihn auf ausdrücklich dokumentierte Empfehlungen.")
        a = await self.call("analyze_document", {"document_id": doc["document_id"]})
        if d := self._denied(a):
            return d
        if not a.ok:
            return f"Das Dokument konnte ich nicht lesen ({a.error_de})."
        e = await self.call("check_benefits", {"document_ids": [doc["document_id"]], "facts": self.memo.get("facts", {})})
        if d := self._denied(e):
            return d
        recs = a.data["recommendations"]
        lines = [(f"Ich habe **{a.data['filename']}** gelesen. Darin werden ausdrücklich {len(recs)} Punkte empfohlen, "
                 "zum Beispiel:")]
        for r in recs[:3]:
            lines.append(f"- {r['text_de']} (S. {r['page']})")
        lines.append("\nDie Anspruchsprüfung der Sozialversicherungs-Services ergibt:")
        return self._eligibility_text(e, lines)

    def _eligibility_text(self, e: ToolOutcome, lines: list[str]) -> str:
        results = [r for r in e.data["results"] if r["recommended_in_document"] or r["status"] in ("likely", "possible")]
        results = [r for r in results if r["recommended_in_document"]] or results
        for r in results[:6]:
            amt = ""
            if r["amounts"]:
                a0 = r["amounts"][0]
                if a0.get("unit") in ("EUR", "€") and a0.get("value"):
                    amt = f" – z. B. {a0['label_de']}: {_eur(a0['value'])} ({a0['source']})"
            lines.append(f"- **{r['name_de']}** ({r['provider']}): {STATUS_DE[r['status']]}{amt}")
        lines.append("\nDie Entscheidung trifft jeweils der zuständige Träger – das ist eine unverbindliche Information.")
        focus = next((r for r in results if r["benefit_id"] == "pflegegeld"), results[0] if results else None)
        pending = (focus or {}).get("missing_fields", [])[:2]
        self.memo["pending_facts"] = pending
        self.memo["focus_benefit"] = (focus or {}).get("benefit_id")
        if pending:
            qs = [FACT_QUESTIONS_DE.get(k, f"Können Sie mir etwas zu „{k}“ sagen?").format(name=self.name)
                  for k in pending]
            lines.append(f"\nFür {focus['name_de']} fehlen noch Angaben: " + " ".join(qs))
        elif focus and focus.get("form_ids"):
            lines.append(f"\nSoll ich den Antrag für {focus['name_de']} als Entwurf vorbereiten?")
        return "\n".join(lines) + _sources_line(self.outcomes)

    async def answer_facts(self, message: str) -> str | None:
        facts: dict = {}
        num, yn = _number(message), _yes_no(message)
        for k in self.memo.get("pending_facts", []):
            if k in BOOL_FACTS and yn is not None:
                facts[k] = BOOL_FACTS[k] if yn else 1
            elif k in ("home_nursing_ordered", "walking_unable_confirmed", "rgb_exempt") and yn is not None:
                facts[k] = yn
            elif k == "treatment_type" and re.search(r"strahl|chemo|immun|dialyse", _n(message)):
                facts[k] = re.search(r"strahl|chemo|immun|dialyse", _n(message)).group(0).replace(
                    "strahl", "strahlentherapie").replace("chemo", "chemotherapie")
            elif num is not None and k not in BOOL_FACTS:
                facts[k] = num
                num = None
        if not facts:
            return None
        doc_ids = self.memo.get("eligibility_document_ids") or self.memo.get("analyzed_document_ids") or []
        e = await self.call("check_benefits", {"document_ids": doc_ids, "facts": {**self.memo.get("facts", {}), **facts}})
        if d := self._denied(e):
            return d
        return self._eligibility_text(e, ["Danke, ich habe das in der Anspruchsprüfung berücksichtigt:"])

    async def explain_benefit(self, word: str) -> str:
        bid = {"pflegegeld": "pflegegeld", "reha": "reha_onko", "rezeptgebühr": "rezeptgebuehrenbefreiung",
               "fahrtkosten": "fahrtkostenzuschuss"}[word]
        g = await self.call("get_benefit", {"benefit_id": bid})
        if not g.ok:
            return "Dazu habe ich gerade keine Informationen."
        b = g.data
        text = b.get("plain_de") or b.get("summary_de")
        return (f"**{b['name_de']}**: {text}\n\nZuständig für die Entscheidung ist {b['provider']}. Das ist eine "
                "unverbindliche Information, keine Rechtsberatung." + _sources_line(self.outcomes))

    async def start_form(self, t: str) -> str:
        if self.memo.get("form_session_id") and "neu" not in t:
            # A draft is already open (e.g. in the wizard): continue it, never start a parallel one.
            q = await self.call("get_next_questions", {"session_id": self.memo["form_session_id"]})
            if d := self._denied(q):
                return d
            return "Ich arbeite im bereits geöffneten Antrags-Entwurf weiter.\n\n" + self._ask(q)
        benefits = self.memo.get("benefits") or []
        target = next((b for b in benefits if b["form_ids"] and b["name_de"].lower().split()[0] in t), None)
        target = target or next((b for b in benefits if b["benefit_id"] == "pflegegeld"), None)
        if target is None:
            g = await self.call("get_benefit", {"benefit_id": "pflegegeld"})
            if not g.ok:
                return "Für welche Leistung soll ich den Antrag vorbereiten?"
            target = {"benefit_id": "pflegegeld", "name_de": g.data["name_de"], "form_ids": g.data["form_ids"]}
        if not target.get("form_ids"):
            return f"Für {target['name_de']} gibt es hier kein Antragsformular zum Vorausfüllen."
        args = {"form_id": target["form_ids"][0]}
        if self.memo.get("last_document_id") and self.memo.get("last_document_type") == "discharge_letter":
            args["document_id"] = self.memo["last_document_id"]
        s = await self.call("start_form", args)
        if d := self._denied(s):
            return d
        if not s.ok:
            return f"Der Antrag konnte nicht gestartet werden ({s.error_de})."
        prefilled = sum(1 for v in s.data["values"].values() if v.get("value") not in (None, ""))
        q = await self.call("get_next_questions", {"session_id": s.data["session_id"]})
        head = (f"Ich habe den Antrag **{target['name_de']}** als Entwurf gestartet und {prefilled} Felder aus "
                "Stammdaten bzw. Dokument vorausgefüllt (jeweils mit Quelle).")
        return head + "\n\n" + self._ask(q)

    def _ask(self, q: ToolOutcome) -> str:
        qs = q.data.get("questions", []) if q.ok else []
        if not qs:
            return "Alle Pflichtangaben sind ausgefüllt. Soll ich den PDF-Entwurf erstellen?"
        parts = []
        for f in qs[:1]:
            hint = f.get("ask_hint_de") or f"Bitte nennen Sie: {f['label_de']}."
            if f["field_id"].lower().startswith("leiden") or "krankheit" in f["label_de"].lower():
                hint += (" Ich fasse Diagnosen nicht selbst zusammen – Sie können sie eintragen oder z. B. "
                         "„siehe beiliegender Entlassungsbrief“ schreiben.")
            parts.append(f"**{f['label_de']}:** {hint}")
        rest = len(qs) - 1
        tail = f"\n\n(Danach {'ist noch 1 Angabe' if rest == 1 else f'sind noch {rest} Angaben'} offen.)" if rest else ""
        return "Eine Frage dazu:\n" + "\n".join(parts) + tail

    async def answer_form(self, message: str) -> str:
        sid = self.memo["form_session_id"]
        f = self.memo["open_questions"][0]
        value: str | bool = re.sub(r"^(bitte\s+)?(schreib\w*|trag\w*( ein)?|nimm|übernimm)\s*:?\s*", "",
                                   message.strip(), flags=re.IGNORECASE) or message.strip()
        if f.get("type") == "checkbox":
            yn = _yes_no(message)
            value = bool(yn)
        p = await self.call("set_form_fields", {"session_id": sid, "values": {f["field_id"]: value}})
        if d := self._denied(p):
            return d
        if not p.ok:
            return f"Diese Angabe passt so noch nicht: {p.error_de}. Können Sie sie bitte anders angeben?"
        q = await self.call("get_next_questions", {"session_id": sid})
        if q.ok and not q.data.get("questions"):
            return await self.render(prefix=f"Danke, „{f['label_de']}“ ist eingetragen. ")
        return f"Danke, „{f['label_de']}“ ist eingetragen.\n\n" + self._ask(q)

    async def render(self, prefix: str = "") -> str:
        sid = self.memo.get("form_session_id")
        if not sid:
            return "Es gibt noch keinen Antragsentwurf. Soll ich einen vorbereiten?"
        r = await self.call("render_form", {"session_id": sid})
        if d := self._denied(r):
            return d
        if not r.ok:
            return f"Der PDF-Entwurf konnte nicht erstellt werden ({r.error_de})."
        return (prefix + f"Der **PDF-Entwurf** ist fertig: [{r.data.get('filename') or 'Entwurf'}]"
                f"({r.data['draft_pdf_url']}).\n\nWichtig: Ich habe **nichts eingereicht**. Bitte prüfen Sie alle "
                "Angaben, unterschreiben Sie den Antrag und schicken Sie ihn selbst an die zuständige Stelle. "
                "Soll ich die Adresse heraussuchen oder einen Fall mit allen Schritten anlegen?")

    async def office(self) -> str:
        topic = self.memo.get("focus_benefit") or "pflegegeld"
        o = await self.call("find_office", {"topic": topic})
        if d := self._denied(o):
            return d
        if not o.ok or not o.data:
            return "Dazu habe ich keine zuständige Stelle gefunden."
        x = o.data[0]
        return (f"Zuständig ist: **{x['name']}**, {x['address']}, {x['zip']} {x['city']}"
                + (f", Tel. {x['phone']}" if x.get("phone") else "") + "." + _sources_line(self.outcomes))

    async def case(self) -> str:
        doc = self.memo.get("last_document_id")
        bids = [b["benefit_id"] for b in self.memo.get("benefits", []) if b["recommended_in_document"]]
        c = await self.call("create_case", {"title": "Versorgung nach dem Spitalsaufenthalt", "document_id": doc,
                                            "benefit_ids": bids})
        if d := self._denied(c):
            return d
        if not c.ok:
            return f"Der Fall konnte nicht angelegt werden ({c.error_de})."
        steps = "\n".join(f"- {s['title_de']} ({s['responsible_de']})" for s in c.data["steps"][:6])
        return f"Ich habe den Fall **{c.data['title_de']}** angelegt. Die ersten Schritte:\n{steps}"

    async def prevention(self) -> str:
        p = await self.call("get_prevention", {})
        if d := self._denied(p):
            return d
        if p.ok and not p.data.get("vaccinations_documented"):
            imp = next((x for x in DEMO_DOCUMENTS.get(self.subject_id, []) if x["doc_type"] == "vaccination_record"), None)
            if imp:
                p2 = await self.call("import_vaccination_record", {"document_id": imp["document_id"]})
                if p2.ok:
                    p = p2
        if not p.ok:
            return f"Die Vorsorge-Übersicht ist gerade nicht verfügbar ({p.error_de})."
        items = p.data["items"]
        due = [i for i in items if i["status"] == "due"]
        nd = [i for i in items if i["status"] == "not_documented"]
        lines = [(f"Laut e-Impfpass ({p.data['vaccinations_documented']} dokumentierte Impfungen) und Österreichischem "
                 "Impfplan bzw. ÖGK-Angebot:")]
        for i in due[:5]:
            cost = f" – {i['cost_de']}" if i.get("cost_de") else ""
            lines.append(f"- **{i['title_de']}**: laut Impfplan/ÖGK empfohlen und jetzt fällig{cost}")
        for i in nd[:3]:
            lines.append(f"- {i['title_de']}: nicht im e-Impfpass dokumentiert – bitte mit Ärztin/Arzt klären")
        lines.append("\n" + (p.data.get("disclaimer_de") or ""))
        return "\n".join(lines) + _sources_line(self.outcomes)
