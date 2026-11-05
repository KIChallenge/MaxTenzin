"""Shared eval logic: run turns against /api/agent/chat, check behavioural expectations, collect a report.

Assertions are deliberately contract-level (tool sequence, sources, boundaries, scope handling, amounts traceable to
deterministic services) — not fixture numbers — so they keep passing when stub services are replaced by real ones.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from app.agent import guard
from app.agent.tools import ToolClient
from app.core.config import get_settings

EVALS_DIR = Path(__file__).parent
RESULTS: list[EvalResult] = []
TURN_LATENCIES: list[int] = []
TURN_MODES: list[str] = []

# Tools that are deterministic reads and can be replayed to verify amounts in the reply.
REPLAYABLE = {"check_benefits", "get_value", "get_benefit", "analyze_document", "get_prevention", "find_office",
              "search_medication", "search_law", "get_next_questions", "list_cases", "list_documents", "preview_form"}
WRITE_TOOLS = {"start_form", "set_form_fields", "render_form", "create_case", "update_case_step",
               "import_vaccination_record"}


@dataclass
class EvalResult:
    suite: str
    case: str
    passed: bool
    tools: list[str] = field(default_factory=list)
    latency_ms: list[int] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    modes: list[str] = field(default_factory=list)


def mode() -> str:
    return "live" if get_settings().llm_live else "fake"


def headers(actor: str, subject: str | None = None) -> dict:
    h = {"Authorization": f"Bearer demo-{actor}"}
    if subject:
        h["X-Subject-Id"] = subject
    return h


def load_yaml(rel: str):
    return yaml.safe_load((EVALS_DIR / rel).read_text(encoding="utf-8"))


def chat(client, hdrs: dict, message: str, cid: str | None = None, **kw) -> tuple[dict, int]:
    t0 = time.perf_counter()
    r = client.post("/api/agent/chat", json={"message": message, "conversation_id": cid, **kw}, headers=hdrs)
    ms = int((time.perf_counter() - t0) * 1000)
    TURN_LATENCIES.append(ms)
    assert r.status_code == 200, r.text
    data = r.json()
    conv = client.get(f"/api/agent/conversations/{data['conversation_id']}", headers=hdrs).json()
    TURN_MODES.append(conv.get("turns", [{}])[-1].get("mode", "?") if conv.get("turns") else "?")
    return data, ms


def tool_names(resp: dict) -> list[str]:
    return [t["tool"] for t in resp["tool_trace"]]


def _is_subsequence(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return all(any(x == y for y in it) for x in needle)


def allowed_numbers(resp: dict, hdrs: dict, subject_id: str, message: str) -> set[float]:
    """Replay the traced read calls against the deterministic services and collect every number they return."""
    async def replay() -> set[float]:
        c = ToolClient({k: v for k, v in hdrs.items()}, subject_id, subject_id)
        nums: set[float] = guard.numbers_in(message)
        for t in resp["tool_trace"]:
            nums |= guard.numbers_in(t["arguments"])
            if t["tool"] in REPLAYABLE and t["status"] == 200:
                o = await c.run(t["tool"], t["arguments"])
                nums |= guard.numbers_in(o.data)
        return nums
    return asyncio.run(replay())


def check_turn(resp: dict, expect: dict, hdrs: dict, subject_id: str, message: str) -> list[str]:
    f: list[str] = []
    names = tool_names(resp)
    reply = resp["reply"]
    low = reply.lower()
    if "boundary" in expect and resp["boundary_triggered"] != expect["boundary"]:
        f.append(f"boundary_triggered={resp['boundary_triggered']} (expected {expect['boundary']})")
    if expect.get("no_tools") and names:
        f.append(f"expected no tool calls, got {names}")
    if (need := expect.get("tools_all")) and not _is_subsequence(need, names):
        f.append(f"tool sequence {names} does not contain {need} in order")
    if (need := expect.get("tools_any")) and not set(need) & set(names):
        f.append(f"none of {need} called (got {names})")
    for bad in expect.get("tools_none", []):
        if bad in names:
            f.append(f"forbidden tool {bad} called")
    if (st := expect.get("status_of")):
        for tool, code in st.items():
            codes = [t["status"] for t in resp["tool_trace"] if t["tool"] == tool]
            if code not in codes:
                f.append(f"{tool} status {codes} (expected {code})")
    if (any_of := expect.get("reply_any")) and not any(s.lower() in low for s in any_of):
        f.append(f"reply contains none of {any_of}")
    for s in expect.get("reply_none", []):
        if s.lower() in low:
            f.append(f"reply contains forbidden text {s!r}")
    had_sources = any(t["status"] == 200 and t["sources"] for t in resp["tool_trace"])
    if expect.get("sources", True) and had_sources and not re.search(r"quelle|source|kaynak", low):
        f.append("reply names no sources although tools returned some")
    max_q = expect.get("max_questions", 3)
    if reply.count("?") > max_q:
        f.append(f"{reply.count('?')} question marks (max {max_q})")
    if not resp["boundary_triggered"]:
        bad = guard.output_violations(reply, allowed_numbers(resp, hdrs, subject_id, message))
        if bad:
            f.append("output guard: " + "; ".join(bad))
    return f


def record(suite: str, case: str, failures: list[str], tools: list[str], lat: list[int]) -> list[str]:
    modes = TURN_MODES[-len(lat):] if lat else []
    if mode() == "live" and "scripted-fallback" in modes:
        failures = [*failures, "live model failed -> scripted fallback used"]
    RESULTS.append(EvalResult(suite, case, not failures, tools, lat, failures, modes))
    return failures


def write_report(path: Path) -> None:
    n_pass = sum(r.passed for r in RESULTS)
    lat = sorted(TURN_LATENCIES)
    llm = sorted(ms for ms, m in zip(TURN_LATENCIES, TURN_MODES, strict=False) if not m.startswith("boundary"))
    p50 = llm[len(llm) // 2] if llm else 0
    p90 = llm[int(len(llm) * 0.9)] if llm else 0
    lines = [
        "# Agent eval report",
        "",
        (f"Generated {datetime.now().isoformat(timespec='seconds')} · mode **{mode()}** · model "
        f"`{get_settings().llm_model}` · **{n_pass}/{len(RESULTS)} passed** · {len(lat)} turns · latency per LLM turn "
        f"(n={len(llm)}) p50 {p50 / 1000:.1f}s, p90 {p90 / 1000:.1f}s, max {(llm[-1] if llm else 0) / 1000:.1f}s · "
        f"boundary turns answer in < 0.2s without LLM"),
        "",
        ("Run: `make eval` (live if `AZURE_API_KEY` is set, else scripted fake mode). Assertions are behavioural: tool "
        "sequence, boundary, scope handling, sources named, every € amount traceable to a deterministic service."),
        "",
        "| Suite | Case | Result | Mode per turn | Tools called | Latency/turn (s) | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in RESULTS:
        tools = " → ".join(r.tools) if r.tools else "–"
        lat_s = ", ".join(f"{x / 1000:.1f}" for x in r.latency_ms)
        notes = "; ".join(r.failures)[:220].replace("|", "/")
        modes = ", ".join(r.modes)
        lines.append(f"| {r.suite} | {r.case} | {'✅' if r.passed else '❌'} | {modes} | {tools} | {lat_s} | {notes} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
