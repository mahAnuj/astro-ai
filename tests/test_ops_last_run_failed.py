"""A weekly loop whose LAST RUN failed must not read as healthy between slots (#628).

Measured 2026-11-04: `agents.json` held `agent-research.yml` as
`verdict: not-due-yet`, `last_run_health: red` (`failure`, 2026-10-28) and
`alerts: []`. The verdict grades the schedule, so the Team panel header said
"every scheduled loop ran when due" and the alerts strip raised nothing, over a
loop that had failed and could not run again for days. Only a red chip in the
table showed it.

Every fixture here is built in the test. The committed `agents.json` changes
several times a day, so asserting against it would be a time bomb.
"""
from __future__ import annotations

import os
import re

import pytest

from astro_ai import ops_data


def _loop(workflow="agent-research.yml", verdict="not-due-yet", health="red",
          conclusion="failure"):
    return {"workflow": workflow, "display": workflow[:-4], "cadence": ["00 17 * * 0"],
            "cadence_error": None, "schedule_since": "2026-11-01T00:00:00Z",
            "slots_due": 0, "runs_scheduled": 4, "runs_total": 5,
            "last_run": "2026-10-28T23:00:00Z", "last_conclusion": conclusion,
            "last_run_health": health, "verdict": verdict}


def _alerts(*loops):
    agents = {"ok": True, "loops": list(loops)}
    loop = {"ok": True, "rows": [], "today_failed": []}
    return ops_data._alerts(loop, {"rows": []}, agents, {}, {})


def _titles(alerts):
    return [a["title"] for a in alerts]


def test_a_failed_last_run_between_slots_raises_an_amber_alert():
    hit = [a for a in _alerts(_loop()) if "last run failed" in a["title"]]
    assert len(hit) == 1, hit
    assert hit[0]["level"] == "amber"
    assert "agent-research.yml" in hit[0]["title"]
    assert "2026-10-28" in hit[0]["detail"] and "failure" in hit[0]["detail"]


@pytest.mark.parametrize("verdict,health", [
    ("not-due-yet", "green"),     # a healthy weekly loop
    ("not-due-yet", "amber"),     # loop-outcomes: exits non-zero by contract
    ("not-due-yet", "running"),
    ("not-due-yet", "unknown"),   # never ran: no health, no false red
    ("on-demand", "red"),         # event-driven: "failed today" covers it
    ("broken", "red"),            # already announced as "is broken"
    ("missing-slots", "red"),     # already announced as "missed scheduled runs"
])
def test_every_other_state_raises_no_last_run_alert(verdict, health):
    assert not [t for t in _titles(_alerts(_loop(verdict=verdict, health=health)))
                if "last run failed" in t]


def test_a_timed_out_last_run_under_an_ok_verdict_is_caught():
    """The collector only calls a `failure` conclusion `broken`; a `timed_out`
    last run keeps verdict `ok` and would otherwise stay silent."""
    hit = _alerts(_loop(verdict="ok", conclusion="timed_out"))
    assert any("last run failed" in t for t in _titles(hit))


def test_a_broken_loop_is_announced_once_not_twice():
    t = [x for x in _titles(_alerts(_loop(verdict="broken"))) if "agent-research" in x]
    assert t == ["agent-research.yml is broken"], t


def test_the_view_lists_the_failed_loops_and_only_them(monkeypatch):
    doc = {"generated_at": "2026-11-04T01:00:00Z", "window_days": 30, "alerts": [],
           "loops": [_loop(), _loop("agent-design.yml", health="green",
                                    conclusion="success")]}
    monkeypatch.setattr(ops_data, "_fetch", lambda n: doc if n == "agents.json" else None)
    view = ops_data._agents_view()
    assert [r["workflow"] for r in view["last_failed"]] == ["agent-research.yml"]


def _page(monkeypatch, loops):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps

    real = ops_data._fetch
    # The committed file supplies `delivery` and `agents`, which the template
    # reads whatever the loops say; only the loops are replaced.
    doc = {**(real("agents.json") or {}), "alerts": [], "loops": loops}
    # #883: the page also renders every open `[OPS] ...: last run failed` issue
    # from the committed issues.json, so asserting "last run failed" is absent
    # from the whole body went red on main the moment such an issue was open.
    # Keep the snapshot's shape (the page reads `objective`) and drop only rows.
    issues = {**(real("issues.json") or {}), "rows": [], "open": 0,
              "with_ask": 0, "blocked": 0, "by_area": {}, "by_type": {},
              "by_priority": {}}
    docs = {"agents.json": doc, "issues.json": issues}
    monkeypatch.setattr(ops_data, "_fetch",
                        lambda n: docs[n] if n in docs else real(n))
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    ops_data._cache.clear()
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200, r.status_code
    return r.text


def test_the_team_header_no_longer_claims_every_loop_ran_when_one_failed(monkeypatch):
    body = _page(monkeypatch, [_loop()])
    assert "every scheduled loop ran when due" not in body
    assert "1 loop last run failed" in body


def test_the_team_header_is_unchanged_when_nothing_failed(monkeypatch):
    body = _page(monkeypatch, [_loop(health="green", conclusion="success")])
    assert "every scheduled loop ran when due" in body
    # The header's own marker, not the bare phrase. The page also renders the
    # committed backlog, and on 2026-11-11 it held a real issue titled
    # "[OPS] agent-prioritise.yml: last run failed" (file_ops_findings.py), so
    # `"last run failed" not in body` went red on main and on every open PR --
    # the time bomb this file's header says it avoids.
    assert not re.search(r"\d+ loops? last run failed", body)


@pytest.mark.parametrize("verdict,says_not_due", [("not-due-yet", True), ("ok", False)])
def test_the_not_due_again_clause_appears_only_under_not_due_yet(verdict, says_not_due):
    """#738 item 2: under `ok` the schedule is on track, so "not due again yet"
    was false there."""
    hit = [a for a in _alerts(_loop(verdict=verdict)) if "last run failed" in a["title"]]
    assert len(hit) == 1, hit
    assert ("not due again yet" in hit[0]["detail"]) is says_not_due, hit[0]["detail"]
    assert "2026-10-28" in hit[0]["detail"]
