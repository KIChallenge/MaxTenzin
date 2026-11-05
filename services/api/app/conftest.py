import os
import tempfile

import pytest

os.environ.setdefault("LLM_MODE", "fake")
os.environ["DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient

from app.main import app
from app.seed.loader import reset_delegations


@pytest.fixture
def client():
    reset_delegations()
    return TestClient(app)


def auth(actor: str, subject: str | None = None, via: str = "ui", tool: str | None = None) -> dict:
    h = {"Authorization": f"Bearer demo-{actor}", "X-Via": via}
    if subject:
        h["X-Subject-Id"] = subject
    if tool:
        h["X-Agent-Tool"] = tool
    return h
