"""directory — 'Wer ist zuständig?'. (owner: WS-B, data: knowledge/offices.yaml)."""

from fastapi import APIRouter, Depends, Query

from app.contracts.misc import Office
from app.core.auth import Context, require
from app.services.directory import service

router = APIRouter(prefix="/api/directory", tags=["directory"])


@router.get("/offices", response_model=list[Office], summary="Responsible offices by topic and postcode")
def offices(topic: str | None = None, zip: str | None = None, provider: str | None = None,
            limit: int | None = Query(None, ge=1, le=100), ctx: Context = Depends(require())):
    res = service.search(topic, zip, provider, limit)
    ctx.cite(*{o.source.label for o in res})
    return res
