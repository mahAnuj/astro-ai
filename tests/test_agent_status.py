"""The "Agents right now" cards (agent_status.py): one state per agent, from
running runs, open PR labels and agents.json, on /admin/ops and in JSON."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from astro_ai import agent_status

NOW = datetime(2026, 11, 13, 6, 0, tzinfo=timezone.utc)


def _run(name: str, title: str, status: str = "in_progress", minutes_ago: int = 12) -> dict:
    ts = datetime.fromtimestamp(NOW.timestamp() - minutes_ago * 60, timezone.utc).isoformat().replace("+00:00", "Z")
    return {"name": name, "display_title": title, "status": status, "run_started_at": ts,
            "html_url": f"https://github.com/x/runs/{abs(hash(title)) % 1000}"}


def _pr(number: int, ref: str, labels: tuple[str, ...] = (), title: str = "a change", draft: bool = False) -> dict:
    return {"number": number, "title": title, "draft": draft, "head": {"ref": ref},
            "labels": [{"name": n} for n in labels], "html_url": f"https://github.com/x/pull/{number}",
            "updated_at": "2026-11-13T05:00:00Z"}


LOOPS = [
    {"workflow": "agent-work.yml", "last_run": "2026-11-13T03:00:00Z", "last_conclusion": "success"},
    {"workflow": "agent-merge.yml", "last_run": "2026-11-13T05:30:00Z", "last_conclusion": "success"},
    {"workflow": "agent-steward.yml", "last_run": "2026-11-13T01:00:00Z", "last_conclusion": "failure"},
    {"workflow": "agent-measure.yml", "last_run": "2026-11-13T05:50:00Z", "last_conclusion": "success"},
]


def _cards(active=(), prs=(), loops=LOOPS) -> dict[str, dict]:
    doc = agent_status.build(list(active), list(prs), list(loops), now=NOW)
    return {a["id"]: a for a in doc["agents"]}


def test_every_agent_has_a_card_in_order_with_a_known_state():
    doc = agent_status.build([], [], LOOPS, now=NOW)
    assert [a["id"] for a in doc["agents"]] == [a[0] for a in agent_status.AGENTS]
    assert all(a["state"] in agent_status.STATES for a in doc["agents"])
    assert sum(doc["counts"].values()) == len(agent_status.AGENTS)


def test_a_running_build_cycle_is_building_and_names_its_pr():
    c = _cards([_run("Agent work", "Agent work")], [_pr(951, "issue/835-sun-career", title="answer-first lede")])
    assert c["developer"]["state"] == "building"
    assert c["developer"]["detail"].startswith("working on PR #951 · answer-first lede · started 12m ago")


def test_a_qa_round_is_qa_running_not_developer_building():
    c = _cards([_run("Agent work", "QA round: PR #940")])
    assert c["qa"]["state"] == "running" and "reviewing PR #940" in c["qa"]["detail"]
    assert c["developer"]["state"] == "done"  # from agents.json, not from the QA run


def test_labels_decide_qa_merge_and_chief():
    prs = [
        _pr(1, "issue/1-a", ("qa-fail",)),
        _pr(2, "issue/2-b", ("qa-pass", "qa:independent")),
        _pr(3, "fix/3-c", ("qa-pass", "needs-human-review")),
        _pr(4, "issue/4-d", ("needs-human-review", "chief-cleared")),
    ]
    c = _cards(prs=prs)
    assert c["qa"]["state"] == "blocked" and "PR #1" in c["qa"]["detail"]
    assert c["merge"]["state"] == "waiting" and "PR #2" in c["merge"]["detail"]  # #3 is held, not mergeable
    assert c["chief"]["state"] == "blocked" and "PR #3" in c["chief"]["detail"]  # #4 already cleared


def test_measurement_prs_are_not_work_waiting_for_anyone():
    c = _cards(prs=[_pr(946, "measurements/43346338332-1")])
    assert c["qa"]["state"] == "idle" and c["merge"]["state"] == "done"


def test_unreviewed_pr_waits_for_qa_but_a_draft_does_not():
    assert _cards(prs=[_pr(5, "issue/5-e")])["qa"]["state"] == "waiting"
    assert _cards(prs=[_pr(6, "issue/6-f", draft=True)])["qa"]["state"] == "idle"


def test_history_gives_done_failed_or_idle():
    c = _cards()
    assert c["steward"]["state"] == "failed" and "failed 5h ago" in c["steward"]["detail"]
    assert c["analyst"]["state"] == "done" and "10m ago" in c["analyst"]["detail"]
    assert c["discover"]["state"] == "idle"  # no row in agents.json


def test_a_queued_run_says_queued():
    c = _cards([_run("Agent steward", "Agent steward", status="queued", minutes_ago=2)])
    assert c["steward"]["state"] == "queued" and "queued 2m ago" in c["steward"]["detail"]


def test_snapshot_never_raises_and_says_it_is_not_live(monkeypatch: pytest.MonkeyPatch):
    def boom(*_a, **_k):
        raise OSError("network down")

    monkeypatch.setattr(agent_status, "_get", boom)
    monkeypatch.setattr(agent_status, "_loops", lambda: LOOPS)
    monkeypatch.setattr(agent_status, "_cache", None)
    doc = agent_status.snapshot()
    assert doc["live"] is False and len(doc["agents"]) == len(agent_status.AGENTS)


def test_snapshot_reads_three_endpoints_once_per_ttl(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def fake(path: str):
        calls.append(path)
        return [] if path.startswith("pulls") else {"workflow_runs": []}

    monkeypatch.setattr(agent_status, "_get", fake)
    monkeypatch.setattr(agent_status, "_loops", lambda: LOOPS)
    monkeypatch.setattr(agent_status, "_cache", None)
    agent_status.snapshot()
    agent_status.snapshot()
    assert len(calls) == 3
    assert {c.split("?")[0] for c in calls} == {"actions/runs", "pulls"}


def test_the_json_route_is_public_cached_and_cors_scoped(monkeypatch: pytest.MonkeyPatch):
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    monkeypatch.setattr(agent_status, "snapshot", lambda: agent_status.build([], [], LOOPS, now=NOW))
    res = TestClient(app).get("/api/agents/status")
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "https://anujmahajan.com"
    assert "max-age=60" in res.headers["cache-control"]
    assert len(res.json()["agents"]) == len(agent_status.AGENTS)
