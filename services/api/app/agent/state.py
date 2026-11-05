"""Conversation state (store collection "conversations") + deterministic working memo."""

from __future__ import annotations

import uuid

from fastapi import HTTPException

from app.agent.tools import ToolOutcome
from app.core.db import now_iso, store

COLL = "conversations"
HISTORY_TURNS = 6

# Demo documents that exist as hand-verified goldens even when no PDF was uploaded (see documents/README.md).
# Only ids + labels — the agent still reads them exclusively through the documents API.
DEMO_DOCUMENTS: dict[str, list[dict]] = {
    "anna": [{"document_id": "doc-anna-entlassung", "filename": "Entlassungsbefund.pdf", "doc_type": "discharge_letter"}],
    "stefan": [
        {"document_id": "doc-stefan-impfpass", "filename": "Impfpass.pdf", "doc_type": "vaccination_record"},
        {"document_id": "doc-stefan-roentgen-1", "filename": "Röntgen Befund.pdf", "doc_type": "imaging_report"},
    ],
}


def load_or_create(conversation_id: str | None, actor_id: str, subject_id: str) -> dict:
    # Always touch the store first: core.db.engine() is lazily created and not thread-safe, and the tool loop may run
    # parallel in-process calls on a fresh DB ("table already exists" race).
    conv = store.get(COLL, conversation_id or "_")
    if conversation_id and conv:
        if conv["actor_id"] != actor_id or conv["subject_id"] != subject_id:
            raise HTTPException(404, "Gespräch nicht gefunden")
        return conv
    return {"id": conversation_id or f"conv-{uuid.uuid4().hex[:10]}", "actor_id": actor_id, "subject_id": subject_id,
            "created_at": now_iso(), "turns": [], "memo": {}}


def save(conv: dict) -> None:
    conv["updated_at"] = now_iso()
    store.put(COLL, conv["id"], conv, subject_id=conv["subject_id"])


def history_messages(conv: dict) -> list[dict]:
    out: list[dict] = []
    for t in conv["turns"][-HISTORY_TURNS:]:
        out.append({"role": "user", "content": t["user"]})
        out.append({"role": "assistant", "content": t["reply"]})
    return out


def update_memo(memo: dict, o: ToolOutcome) -> None:
    """Deterministically remember ids/state from tool results so later turns can continue (session id, case id …)."""
    if o.status == 403:
        memo.setdefault("denied_scopes", [])
        if o.forbidden_scope and o.forbidden_scope not in memo["denied_scopes"]:
            memo["denied_scopes"].append(o.forbidden_scope)
        return
    if not o.ok or o.data is None:
        return
    d = o.data
    if o.tool == "analyze_document":
        ids = memo.setdefault("analyzed_document_ids", [])
        if d.get("document_id") not in ids:
            ids.append(d.get("document_id"))
        memo["last_document_id"] = d.get("document_id")
        memo["last_document_type"] = d.get("doc_type")
    elif o.tool == "check_benefits":
        memo["facts"] = {**memo.get("facts", {}), **(o.arguments.get("facts") or {})}
        if o.arguments.get("document_ids"):
            memo["eligibility_document_ids"] = o.arguments["document_ids"]
        memo["benefits"] = [{"benefit_id": r["benefit_id"], "name_de": r["name_de"], "status": r["status"],
                             "recommended_in_document": r["recommended_in_document"],
                             "missing_fields": r["missing_fields"], "form_ids": r["form_ids"]}
                            for r in d.get("results", [])]
    elif o.tool in ("start_form", "set_form_fields"):
        memo["form_session_id"] = d.get("session_id")
        memo["form_id"] = d.get("form_id")
        if o.tool == "start_form" and not o.summary_de.startswith("Bestehender"):
            memo["form_rendered"] = False
            memo.pop("open_questions", None)
    elif o.tool == "get_next_questions":
        memo["open_questions"] = [{"field_id": q["field_id"], "label_de": q["label_de"], "type": q["type"],
                                   "ask_hint_de": q.get("ask_hint_de"), "options": q.get("options")}
                                  for q in d.get("questions", [])]
    elif o.tool == "render_form":
        memo["form_rendered"] = True
        memo["draft_pdf_url"] = d.get("draft_pdf_url")
    elif o.tool == "create_case":
        memo["case_id"] = d.get("case_id")
    elif o.tool in ("get_prevention", "import_vaccination_record"):
        memo["prevention_checked"] = True
        memo["vaccinations_documented"] = d.get("vaccinations_documented")


def memo_text(memo: dict) -> str:
    if not memo:
        return "noch nichts"
    keep = {k: v for k, v in memo.items() if k != "benefits"}
    if memo.get("benefits"):
        keep["benefits"] = [f"{b['benefit_id']}={b['status']}" + (f" fehlt:{','.join(b['missing_fields'])}"
                                                                   if b["missing_fields"] else "")
                            for b in memo["benefits"] if b["status"] != "not_applicable"]
    return str(keep)
