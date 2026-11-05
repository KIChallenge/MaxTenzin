"""directory — 'Wer ist zuständig?'. STUB (owner: WS-B, data from WS-K offices.yaml)."""

from fastapi import APIRouter, Depends

from app.contracts.misc import Office
from app.core.auth import Context, require
from app.fixtures import OFFICES

router = APIRouter(prefix="/api/directory", tags=["directory"])


@router.get("/offices", response_model=list[Office], summary="Responsible offices by topic and postcode")
def offices(topic: str | None = None, zip: str | None = None, ctx: Context = Depends(require())):
    return [o for o in OFFICES if topic is None or topic in o.topics]  # STUB
