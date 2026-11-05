"""Eval harness setup: isolated temp DB, live LLM if a key is configured (else scripted fake mode), REPORT.md writer."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1] / "services" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))
os.environ["DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/eval.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed.loader import reset_delegations  # noqa: E402

import eval_harness  # noqa: E402


@pytest.fixture
def client():
    reset_delegations()
    return TestClient(app)


def pytest_sessionfinish(session, exitstatus):
    if eval_harness.RESULTS:
        eval_harness.write_report(Path(__file__).parent / "REPORT.md")
