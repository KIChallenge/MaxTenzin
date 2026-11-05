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
    from app.core.db import store

    reset_delegations()
    for subject in ("anna", "maria", "stefan", "lena"):  # answers stored by earlier tests must not leak
        store.delete("known_facts", subject)
    return TestClient(app)


def auth(actor: str, subject: str | None = None, via: str = "ui", tool: str | None = None) -> dict:
    h = {"Authorization": f"Bearer demo-{actor}", "X-Via": via}
    if subject:
        h["X-Subject-Id"] = subject
    if tool:
        h["X-Agent-Tool"] = tool
    return h
