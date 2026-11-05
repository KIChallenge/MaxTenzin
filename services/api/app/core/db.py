"""SQLite via SQLModel: one audit table + a tiny JSON document store used by all services."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.core.config import get_settings

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
    return _engine


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class AuditRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ts: str
    actor_id: str | None = None
    subject_id: str | None = None
    via: str = "ui"
    tool: str | None = None
    method: str
    path: str
    status: int
    scope_required: str | None = None
    allowed: bool = True
    sources_json: str = "[]"
    rule_ids_json: str = "[]"


class Doc(SQLModel, table=True):
    """Generic JSON store: (collection, id) -> data. Services own their collections."""
    collection: str = Field(primary_key=True)
    id: str = Field(primary_key=True)
    subject_id: str | None = Field(default=None, index=True)
    data: str
    updated_at: str


class Store:
    def put(self, collection: str, id: str, data: dict, subject_id: str | None = None) -> dict:
        with Session(engine()) as s:
            row = s.get(Doc, (collection, id)) or Doc(collection=collection, id=id, data="{}", updated_at="")
            row.data = json.dumps(data, ensure_ascii=False, default=str)
            row.subject_id = subject_id
            row.updated_at = now_iso()
            s.add(row)
            s.commit()
        return data

    def get(self, collection: str, id: str) -> dict | None:
        with Session(engine()) as s:
            row = s.get(Doc, (collection, id))
            return json.loads(row.data) if row else None

    def list(self, collection: str, subject_id: str | None = None) -> list[dict]:
        with Session(engine()) as s:
            q = select(Doc).where(Doc.collection == collection)
            if subject_id is not None:
                q = q.where(Doc.subject_id == subject_id)
            return [json.loads(r.data) for r in s.exec(q.order_by(Doc.updated_at)).all()]

    def delete(self, collection: str, id: str) -> None:
        with Session(engine()) as s:
            row = s.get(Doc, (collection, id))
            if row:
                s.delete(row)
                s.commit()


store = Store()


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine())
    SQLModel.metadata.create_all(engine())
