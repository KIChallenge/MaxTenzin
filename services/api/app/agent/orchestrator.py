"""Agent orchestrator: input guard -> (live tool loop | scripted planner) -> output guard -> persist.

The model only understands, routes and explains. Deterministic services decide; deterministic guards bracket the model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.agent import guard, state
from app.agent.scripted import Scripted, forbidden_text
from app.agent.tools import SCOPE_DE, TOOL_SPECS, ToolClient, ToolOutcome, llm_payload
from app.contracts.agent import ChatAction, ChatRequest, ChatResponse, ToolTrace
from app.core.auth import Context
from app.core.db import now_iso
from app.core.llm import get_llm
from app.seed.loader import delegations_for

log = logging.getLogger("agent")

MAX_TOOL_ROUNDS = 6
MAX_TOKENS = 3000
REASONING = "low"
PROMPT = Path(__file__).parent / "prompts" / "system_de.md"
LANG_NAMES = {"de": "Deutsch", "en": "Englisch (English)", "tr": "Türkisch (Türkçe)"}


@lru_cache
def _prompt_template() -> str:
    return PROMPT.read_text(encoding="utf-8")


def _full_name(p) -> str:
    return f"{p.first_name} {p.last_name}"


DETAIL_DE = {"short": "DETAILTIEFE KURZ: höchstens 4 Sätze oder 4 Aufzählungspunkte, nur das Nötigste.",
             "normal": "Detailtiefe normal.",
             "detailed": "DETAILTIEFE AUSFÜHRLICH: erkläre Hintergründe, Voraussetzungen und Schritte ausführlicher."}


def _prefs_text(prefs: dict) -> str:
    if not prefs:
        return "keine gespeichert"
    daypart = {"morning": "vormittags", "afternoon": "nachmittags"}.get(prefs.get("daypart"), "keine Tageszeit-Präferenz")
    return (f"Sprache {prefs.get('language', 'de')}, Detailtiefe {prefs.get('detail', 'normal')}, Termine {daypart}, "
            f"{'möglichst in der Nähe' if prefs.get('near_home', True) else 'Entfernung egal'}"
            f"{', barrierefrei' if prefs.get('accessible') else ''}")


def system_prompt(ctx: Context, memo: dict, plain: bool, lang: str = "de", prefs: dict | None = None) -> str:
    s = ctx.subject
    relation = ""
    if ctx.actor.id != s.id:
        rel = next((d.relation for d in delegations_for(s.id) if d.grantee_id == ctx.actor.id), "")
        relation = f" – {_full_name(ctx.actor)} handelt als Vertretung" + (f" ({rel})" if rel else "")
    docs = state.DEMO_DOCUMENTS.get(s.id, [])
    doc_txt = ", ".join(f"{d['document_id']} ({d['filename']}, {d['doc_type']})" for d in docs) or \
        "unbekannt – bei Bedarf list_documents aufrufen"
    scopes = ", ".join(f"{SCOPE_DE.get(x, x)}" for x in sorted(ctx.scopes)) if ctx.actor.id != s.id else \
        "alle (handelt für sich selbst)"
    plain_txt = ("EINFACHE SPRACHE: kurze Sätze, keine Fachwörter ohne Erklärung, eine Information pro Satz."
                 if plain else "Klare Alltagssprache; Fachbegriffe kurz erklären.")
    return _prompt_template().format(
        plain_language=plain_txt, reply_language=LANG_NAMES.get(lang, "Deutsch"), today=date.today().isoformat(), actor_name=_full_name(ctx.actor),
        subject_name=_full_name(s), subject_birth=s.birth_date, subject_zip=s.address.zip, subject_insurer=s.insurer,
        relation=relation, scopes=scopes, documents=doc_txt, memo=state.memo_text(memo),
        preferences=_prefs_text(prefs or {}), detail=DETAIL_DE.get((prefs or {}).get("detail", "normal"), ""))


def _trace(o: ToolOutcome) -> ToolTrace:
    return ToolTrace(tool=o.tool, arguments=o.arguments, status=o.status, summary_de=o.summary_de, sources=o.sources)


def _suggestions(memo: dict, outcomes: list[ToolOutcome]) -> list[str]:
    if memo.get("form_rendered"):
        return ["Wohin schicke ich den Antrag?", "Fall mit allen Schritten anlegen"]
    if memo.get("form_session_id") and memo.get("open_questions") == []:
        return ["PDF-Entwurf erstellen", "Angaben noch einmal zeigen"]
    if memo.get("form_session_id"):
        return ["PDF-Entwurf jetzt erstellen", "Wer ist zuständig?"]
    if memo.get("benefits") and not memo.get("form_session_id"):
        names = [b["name_de"] for b in memo["benefits"] if b["recommended_in_document"] and b["form_ids"]][:2]
        return [f"Antrag vorbereiten: {n}" for n in names] + ["Wer ist zuständig?"]
    if memo.get("prevention_checked"):
        return ["Wo kann ich mich impfen lassen?", "Was kostet die Vorsorgeuntersuchung?"]
    return ["Entlassungsbrief prüfen", "Welche Vorsorge ist fällig?", "Antrag vorbereiten"]


# --------------------------------------------------------------------------------------------- live loop
async def _llm(messages: list[dict], tools: list[dict] | None):
    llm = get_llm()
    return await asyncio.to_thread(llm.chat, messages, tools, max_tokens=MAX_TOKENS, reasoning_effort=REASONING)


def _assistant_msg(msg) -> dict:
    out: dict = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        out["tool_calls"] = [{"id": tc.id, "type": "function",
                              "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                             for tc in msg.tool_calls]
    return out


async def run_live(client: ToolClient, ctx: Context, conv: dict, message: str, plain: bool, lang: str,
                   outcomes: list[ToolOutcome]) -> str:
    memo = conv["memo"]
    r = await client.fetch("/api/identity/preferences", "context:preferences")
    prefs = r.json() if r.status_code == 200 else {}
    plain = plain or bool(prefs.get("plain_language"))
    if lang == "de" and prefs.get("language") and prefs["language"] != "de":
        lang = prefs["language"]
    messages = [{"role": "system", "content": system_prompt(ctx, memo, plain, lang, prefs)}, *state.history_messages(conv),
                {"role": "user", "content": message}]
    reply = await _tool_loop(client, memo, messages, outcomes, MAX_TOOL_ROUNDS)

    allowed = guard.numbers_in([o.data for o in outcomes]) | guard.numbers_in([o.arguments for o in outcomes]) | \
        guard.numbers_in(message)
    wrote = any(o.tool == "set_form_fields" and o.ok for o in outcomes)
    problems = (guard.output_violations(reply, allowed) + guard.write_claim_violations(reply, wrote)
                + guard.question_violations(reply)) if reply else ["leere Antwort"]
    if problems and any(p.startswith("Behauptung, etwas in den Antrag") for p in problems):
        # Claimed a form entry without writing it: give the model tools again to actually do it (max 3 rounds).
        log.warning("output guard (write claim): %s", problems)
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "SYSTEMPRÜFUNG (nicht von der Person): " + "; ".join(problems)}]
        reply = await _tool_loop(client, memo, messages, outcomes, 3)
        wrote = any(o.tool == "set_form_fields" and o.ok for o in outcomes)
        problems = (guard.output_violations(reply, allowed) + guard.write_claim_violations(reply, wrote)) \
            if reply else ["leere Antwort"]
    if problems:
        log.warning("output guard: %s", problems)
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "SYSTEMPRÜFUNG (nicht von der Person): Deine Antwort verletzt Regeln: "
                      + "; ".join(problems) + ". Formuliere die Antwort neu – nur Beträge, die wörtlich in den "
                      "Tool-Ergebnissen stehen, keine Einreichung behaupten, Vorsorge-Wording beachten, höchstens 2 Rückfragen."}]
        reply = (await _llm(messages, None)).content or ""
        problems = (guard.output_violations(reply, allowed) + guard.write_claim_violations(reply, wrote)) \
            if reply else ["leere Antwort"]
        if problems:
            log.warning("output guard fallback: %s", problems)
            reply = fallback_reply(outcomes)
    return reply


async def _tool_loop(client: ToolClient, memo: dict, messages: list[dict], outcomes: list[ToolOutcome],
                     rounds: int) -> str:
    for _ in range(rounds):
        msg = await _llm(messages, TOOL_SPECS)
        if not msg.tool_calls:
            return msg.content or ""
        messages.append(_assistant_msg(msg))
        calls = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append((tc.id, tc.function.name, args if isinstance(args, dict) else {}))
        results = await asyncio.gather(*(client.run(name, args) for _, name, args in calls))
        for (tc_id, _, _), o in zip(calls, results, strict=True):
            outcomes.append(o)
            state.update_memo(memo, o)
            messages.append({"role": "tool", "tool_call_id": tc_id, "content": llm_payload(o)})
    messages.append({"role": "user", "content": "SYSTEM: Keine weiteren Tools. Antworte jetzt mit dem bisherigen Stand."})
    return (await _llm(messages, None)).content or ""


def fallback_reply(outcomes: list[ToolOutcome]) -> str:
    ok = [o for o in outcomes if o.ok]
    if not ok:
        return ("Das konnte ich gerade nicht sicher beantworten. Bitte formulieren Sie Ihr Anliegen noch einmal oder "
                "nutzen Sie die Bereiche „Leistungen“, „Dokumente“ und „Anträge“ im Cockpit.")
    lines = ["Hier die Ergebnisse der geprüften Services:"] + [f"- {o.summary_de}" for o in ok]
    srcs: list[str] = []
    for o in ok:
        srcs += [s for s in o.sources if s not in srcs]
    if srcs:
        lines.append("\n**Quellen:** " + "; ".join(srcs[:6]))
    return "\n".join(lines)


CONTENT_FILTER_REPLY = (
    "Ihre Nachricht enthält Anweisungen, die ich aus Sicherheitsgründen nicht ausführe (z. B. Regeln zu ignorieren). "
    "Ich prüfe Ansprüche nur über die Services der Sozialversicherung, nenne keine erfundenen Beträge und reiche "
    "nichts ein. Beschreiben Sie mir gerne Ihr Anliegen in eigenen Worten – z. B. „Welche Leistungen kommen laut "
    "Entlassungsbrief in Frage?“"
)


def _is_content_filter(e: Exception) -> bool:
    text = str(e).lower()
    return "content management policy" in text or "content_filter" in text or "responsibleaipolicyviolation" in text


# --------------------------------------------------------------------------------------------- entry point
async def _llm_boundary_check(message: str) -> str | None:
    llm = get_llm()
    if not llm.live or not guard.HEALTH_TERMS.search(message.lower()):
        return None
    try:
        res = await asyncio.wait_for(asyncio.to_thread(llm.json, guard.LLM_BOUNDARY_SYSTEM, message, 400, "low"), 15)
    except Exception:  # noqa: BLE001 - the regex guard already ran; the LLM check is best-effort
        return None
    cat = (res or {}).get("category")
    return cat if cat in ("diagnosis", "findings", "prognosis", "medication", "emergency") else None


async def handle_turn(req: ChatRequest, ctx: Context, headers: dict[str, str]) -> ChatResponse:
    t0 = time.perf_counter()
    conv = state.load_or_create(req.conversation_id, ctx.actor.id, ctx.subject.id)
    memo = conv["memo"]
    prev_lang = conv["turns"][-1].get("language", "de") if conv["turns"] else "de"
    lang = req.language if req.language and req.language != "de" else guard.detect_language(req.message, prev_lang)
    subject_name = _full_name(ctx.subject)
    outcomes: list[ToolOutcome] = []
    mode = "live" if get_llm().live else "scripted"
    if req.document_ids:
        memo["last_document_id"] = req.document_ids[0]
    # Explicit consent in THIS message (deterministic): required to apply document-based situation suggestions.
    memo["_user_consented"] = bool(_CONSENT_YES.search(req.message or ""))

    hit = guard.check_boundary(req.message)
    category = hit.category if hit else await _llm_boundary_check(req.message)
    if category:
        reply, suggestions = guard.boundary_reply(category, lang)
        mode = f"boundary:{category}"
        resp = ChatResponse(conversation_id=conv["id"], reply=reply, tool_trace=[], boundary_triggered=True,
                            suggestions_de=suggestions)
    else:
        client = ToolClient(headers, ctx.subject.id, subject_name, memo)
        if req.form_session_id and req.form_session_id != memo.get("form_session_id"):
            # The wizard has this session open: the chat must edit exactly this one (never start a parallel draft).
            r = await client.fetch(f"/api/forms/sessions/{req.form_session_id}", "context:open_form")
            if r.status_code == 200:
                memo["form_session_id"], memo["form_id"] = req.form_session_id, r.json()["form_id"]
                memo["form_rendered"] = False
                memo.pop("open_questions", None)

        async def run(name: str, args: dict) -> ToolOutcome:
            o = await client.run(name, args)
            state.update_memo(memo, o)
            return o

        reply = ""
        if mode == "live":
            try:
                reply = await run_live(client, ctx, conv, req.message, req.plain_language, lang, outcomes)
            except Exception as e:
                if _is_content_filter(e):
                    # Provider-side safety filter (e.g. jailbreak / injection attempt): fixed safe reply, no fallback
                    # planner, so injected instructions can never steer the scripted path either.
                    log.warning("content filter triggered: %s", e)
                    mode = "content-filter"
                    reply = CONTENT_FILTER_REPLY
                else:
                    log.exception("live agent failed, falling back to scripted")
                    mode = "scripted-fallback"
            if reply and mode == "live" and _wants_pdf(req.message) and memo.get("form_session_id") \
                    and not any(o.tool == "render_form" for o in outcomes):
                # Explicit user command: render deterministically instead of depending on the model's choice.
                o = await run("render_form", {"session_id": memo["form_session_id"]})
                outcomes.append(o)
                if o.ok:
                    reply += ("\n\nIch habe den **PDF-Entwurf** erstellt. Bitte prüfen, unterschreiben und selbst "
                              "einreichen – es wurde nichts eingereicht.")
        if not reply:
            sp = Scripted(run, memo, ctx.subject.id, subject_name, ctx.actor.id == ctx.subject.id)
            reply = await sp.reply(req.message)
            outcomes += sp.outcomes
        rejected = [o for o in outcomes if o.tool == "set_form_fields" and o.status == 422]
        if rejected:
            # Relay the form's own validation message verbatim instead of letting the model guess why.
            reply = ("**Nicht übernommen:** " + (rejected[-1].error_de or "Die Angabe passt nicht zum Formular.")
                     + "\n\n" + reply)
        writes = [o for o in outcomes if o.tool == "set_form_fields" and o.ok]
        if writes:
            reply = await _form_write_reply(client, writes, reply)
        denied = [o for o in outcomes if o.status == 403]
        if denied and "berechtigung" not in reply.lower() and "permission" not in reply.lower():
            reply = forbidden_text(denied[0], subject_name) + "\n\n" + reply
        srcs = [s for o in outcomes if o.ok for s in o.sources]
        if srcs and not any(w in reply.lower() for w in ("quelle", "source", "kaynak")):
            reply += "\n\n**Quellen:** " + "; ".join(list(dict.fromkeys(srcs))[:6])
        resp = ChatResponse(conversation_id=conv["id"], reply=_sanitize(reply), tool_trace=[_trace(o) for o in outcomes],
                            boundary_triggered=False, suggestions_de=_suggestions(memo, outcomes),
                            actions=_actions(outcomes))

    conv["turns"].append({"ts": now_iso(), "user": req.message, "reply": resp.reply,
                          "tool_trace": [t.model_dump() for t in resp.tool_trace],
                          "boundary_triggered": resp.boundary_triggered, "suggestions_de": resp.suggestions_de,
                          "mode": mode, "language": lang, "latency_ms": int((time.perf_counter() - t0) * 1000)})
    state.save(conv)
    return resp


def _actions(outcomes) -> list[ChatAction]:
    """Deterministic UI buttons derived from successful tool calls (never from model text)."""
    acts: dict[str, ChatAction] = {}
    for o in outcomes:
        if not o.ok:
            continue
        sid = (o.arguments or {}).get("session_id")
        if not sid and o.tool == "start_form" and isinstance(o.data, dict):
            sid = o.data.get("id")
        if o.tool == "render_form" and sid:
            acts["download"] = ChatAction(kind="download_pdf", label_de="Entwurf als PDF herunterladen", method="POST",
                                          url=f"/api/forms/sessions/{sid}/render")
        elif o.tool in ("start_form", "set_form_fields", "get_next_questions") and sid:
            acts["form"] = ChatAction(kind="open_form", label_de="Antrag im Assistenten öffnen", url=f"/forms/{sid}")
        elif o.tool == "book_appointment" and isinstance(o.data, dict) and o.data.get("ics_url"):
            acts["ics"] = ChatAction(kind="download_ics", label_de="Termin in den Kalender (.ics)", url=o.data["ics_url"])
            acts["appointments"] = ChatAction(kind="open_appointments", label_de="Meine Termine", url="/termine")
        elif o.tool in ("create_case", "update_case_step"):
            acts["case"] = ChatAction(kind="open_case", label_de="Mein Fall öffnen", url="/fall")
    return list(acts.values())


_PDF_RE = re.compile(r"\b(pdf|entwurf\s+(erstellen|herunterladen|ausdrucken)|draft)\b", re.IGNORECASE)


def _wants_pdf(message: str) -> bool:
    return bool(_PDF_RE.search(message or ""))


_CONSENT = re.compile(r"zustimmung|einverst|einwillig", re.IGNORECASE)
# Model text that claims a consent was set/ticked (without negation in the same sentence) is never shown.
_CONSENT_CLAIM = re.compile(r"[^.!?\n]*(zustimmung|einverständnis|einwilligung)[^.!?\n]*\b(gesetzt|eingetragen|angekreuzt|"
                            r"bestätigt|erteilt|vermerkt|als ja)\b[^.!?\n]*", re.IGNORECASE)
_UUID = re.compile(r"\s*\(?\s*(Sitzung|session|Session-ID|ID)?:?\s*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
                   r"\s*\)?", re.IGNORECASE)


def _fmt(v) -> str:
    return "angekreuzt" if v is True else "nicht angekreuzt" if v is False else str(v)


async def _form_write_reply(client: ToolClient, writes: list[ToolOutcome], model_reply: str) -> str:
    """Deterministic statement of what was written (labels from the form definition) + what the person must do."""
    sid = writes[-1].arguments.get("session_id")
    defs = await client._field_defs(sid)
    written: dict = {}
    for o in writes:
        written.update(o.arguments.get("values") or {})
    parts = [f"{defs.get(f, {}).get('label') or f} = {_fmt(v)}" for f, v in written.items()]
    lines = ["**Eingetragen im Antrag:** " + "; ".join(parts)]
    r = await client.fetch(f"/api/forms/sessions/{sid}/next-questions", "context:after_write")
    if r.status_code == 200:
        qs = r.json().get("questions", [])
        consent = [q for q in qs if _CONSENT.search(q.get("label_de", ""))]
        if consent:
            lines.append("**Noch offen – bitte im Antrag selbst ankreuzen:** " +
                         "; ".join(f"„{q['label_de']}“" for q in consent) + " (Zustimmungen kreuze ich nie für Sie an).")
        others = [q for q in qs if q not in consent]
        if others:
            lines.append(f"**Noch offene Pflichtangaben:** {len(others)} – z. B. „{others[0]['label_de']}“.")
    rest = _CONSENT_CLAIM.sub("", model_reply).strip() if _CONSENT.search(model_reply) else model_reply.strip()
    # Drop the model's own restatement of the entry (the deterministic line above is authoritative).
    rest = re.sub(r"^[^\n]*\b(eingetragen|halte fest|vermerkt|gesetzt)\b[^\n]*\n?", "", rest, count=1,
                  flags=re.IGNORECASE).strip()
    return "\n".join(lines) + ("\n\n" + rest if rest else "")


_TOOL_DE = {"search_slots": "Terminsuche", "book_appointment": "Terminbuchung", "check_benefits": "Anspruchsprüfung",
            "analyze_document": "Dokumentanalyse", "get_next_questions": "Antragsentwurf", "set_form_fields": "Antragsentwurf",
            "start_form": "Antragsentwurf", "render_form": "PDF-Entwurf", "get_prevention": "Vorsorge-Hinweise",
            "match_bundle": "Lebenssituation", "get_situation": "Lebenslage", "find_office": "Zuständige Stellen",
            "search_law": "Rechtsgrundlagen", "get_value": "Werte-Tabelle", "get_benefit": "Leistungsbeschreibung",
            "list_appointments": "Termine", "preview_form": "Antragsentwurf", "list_documents": "Dokumente"}
_TOOL_RE = re.compile(r"`?\b(" + "|".join(_TOOL_DE) + r")\b`?")


def _sanitize(reply: str) -> str:
    """Never show internal ids (session UUIDs) or internal tool names to the person."""
    out = _TOOL_RE.sub(lambda m: _TOOL_DE[m.group(1)], _UUID.sub("", reply))
    out = re.sub(r"\n*\**Quellen:?\**:?\s*(keine|keine angegeben|keine Tool-Ergebnisse)[^\n]*", "", out, flags=re.IGNORECASE)
    return out.strip()


_CONSENT_YES = re.compile(r"\b(ja|jawohl|passt|stimmt|einverstanden|übernehmen|übernimm|bestätige|yes|evet)\b", re.IGNORECASE)
