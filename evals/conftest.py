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

import eval_harness
from fastapi.testclient import TestClient

from app.main import app
from app.seed.loader import reset_delegations


@pytest.fixture
def client():
    reset_delegations()
    return TestClient(app)


def pytest_sessionfinish(session, exitstatus):
    if eval_harness.RESULTS:
        eval_harness.write_report(Path(__file__).parent / "REPORT.md")
