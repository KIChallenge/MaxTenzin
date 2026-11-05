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


def system_prompt(ctx: Context, memo: dict, plain: bool, lang: str = "de") -> str:
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
        relation=relation, scopes=scopes, documents=doc_txt, memo=state.memo_text(memo))


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
    messages = [{"role": "system", "content": system_prompt(ctx, memo, plain, lang)}, *state.history_messages(conv),
                {"role": "user", "content": message}]
    reply = ""
    for _ in range(MAX_TOOL_ROUNDS):
        msg = await _llm(messages, TOOL_SPECS)
        if not msg.tool_calls:
            reply = msg.content or ""
            break
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
    else:
        messages.append({"role": "user", "content": "SYSTEM: Keine weiteren Tools. Antworte jetzt mit dem bisherigen "
                                                    "Stand."})
        reply = (await _llm(messages, None)).content or ""

    allowed = guard.numbers_in([o.data for o in outcomes]) | guard.numbers_in([o.arguments for o in outcomes]) | \
        guard.numbers_in(message)
    problems = (guard.output_violations(reply, allowed) + guard.question_violations(reply)) if reply else ["leere Antwort"]
    if problems:
        log.warning("output guard: %s", problems)
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "SYSTEMPRÜFUNG (nicht von der Person): Deine Antwort verletzt Regeln: "
                      + "; ".join(problems) + ". Formuliere die Antwort neu – nur Beträge, die wörtlich in den "
                      "Tool-Ergebnissen stehen, keine Einreichung behaupten, Vorsorge-Wording beachten, höchstens 2 Rückfragen."}]
        reply = (await _llm(messages, None)).content or ""
        problems = guard.output_violations(reply, allowed) if reply else ["leere Antwort"]
        if problems:
            log.warning("output guard fallback: %s", problems)
            reply = fallback_reply(outcomes)
    return reply


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

    hit = guard.check_boundary(req.message)
    category = hit.category if hit else await _llm_boundary_check(req.message)
    if category:
        reply, suggestions = guard.boundary_reply(category, lang)
        mode = f"boundary:{category}"
        resp = ChatResponse(conversation_id=conv["id"], reply=reply, tool_trace=[], boundary_triggered=True,
                            suggestions_de=suggestions)
    else:
        client = ToolClient(headers, ctx.subject.id, subject_name, memo)

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
        denied = [o for o in outcomes if o.status == 403]
        if denied and "berechtigung" not in reply.lower() and "permission" not in reply.lower():
            reply = forbidden_text(denied[0], subject_name) + "\n\n" + reply
        srcs = [s for o in outcomes if o.ok for s in o.sources]
        if srcs and not any(w in reply.lower() for w in ("quelle", "source", "kaynak")):
            reply += "\n\n**Quellen:** " + "; ".join(list(dict.fromkeys(srcs))[:6])
        resp = ChatResponse(conversation_id=conv["id"], reply=reply, tool_trace=[_trace(o) for o in outcomes],
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
        elif o.tool in ("create_case", "update_case_step"):
            acts["case"] = ChatAction(kind="open_case", label_de="Mein Fall öffnen", url="/case")
    return list(acts.values())


_PDF_RE = re.compile(r"\b(pdf|entwurf\s+(erstellen|herunterladen|ausdrucken)|draft)\b", re.IGNORECASE)


def _wants_pdf(message: str) -> bool:
    return bool(_PDF_RE.search(message or ""))
