"""The "Agents right now" cards (agent_status.py): one state per agent, from
running runs, open PR labels and agents.json, on /admin/ops and in JSON."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from astro_ai import agent_status

NOW = datetime(2026, 11, 13, 6, 0, tzinfo=timezone.utc)


def _run(name: str, title: str, status: str = "in_progress", minutes_ago: int = 12,
         branch: str = "main", event: str = "workflow_dispatch") -> dict:
    ts = datetime.fromtimestamp(NOW.timestamp() - minutes_ago * 60, timezone.utc).isoformat().replace("+00:00", "Z")
    return {"name": name, "display_title": title, "status": status, "run_started_at": ts,
            "head_branch": branch, "event": event,
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


def test_a_dispatched_cycle_names_its_exact_issue_and_its_pr():
    # The other open cycle PR comes FIRST: a card that guessed "the newest
    # cycle PR" would name #952 instead of the issue the run was started on.
    prs = [_pr(952, "issue/900-other", title="something else"), _pr(951, "issue/835-sun-career")]
    doc = agent_status.build([_run("Agent work", "Agent work: issue #835")], prs, LOOPS,
                             issues={835: "Debilitated Sun and career"}, now=NOW)
    dev = {a["id"]: a for a in doc["agents"]}["dev-lead"]
    assert dev["state"] == "building"
    assert dev["detail"].startswith("working on issue #835 · Debilitated Sun and career · PR #951 · started 12m ago")
    assert dev["url"].endswith("/issues/835")


def test_every_agent_definition_has_a_card():
    from pathlib import Path

    defined = {f.stem for f in (Path(__file__).resolve().parents[1] / ".claude/agents").glob("*.md")}
    carded = {a[0] for a in agent_status.AGENTS}
    assert defined, "no agent definitions found"
    assert defined <= carded, f"agents with no card: {sorted(defined - carded)}"
    assert carded - defined == {"merge"}  # the one card that is a workflow, said so on the card
    assert {a[2] for a in agent_status.AGENTS} <= set(agent_status.GROUPS)


def test_helpers_are_on_standby_only_while_a_build_cycle_runs():
    c = _cards([_run("Agent work", "Agent work")])
    assert {c[k]["state"] for k in ("architect", "engineer", "frontend-engineer")} == {"standby"}
    c = _cards([_run("Agent work", "QA round: PR #940")])  # a QA round is not a build cycle
    assert {c[k]["state"] for k in ("architect", "engineer", "frontend-engineer")} == {"idle"}


def test_on_request_agents_say_they_have_no_schedule():
    c = _cards()
    assert c["conversion-lead"]["state"] == "idle" and "not on any schedule" in c["conversion-lead"]["detail"]
    assert "not on any schedule" in c["qa-lead"]["detail"]


def test_research_runs_light_both_auditors():
    c = _cards([_run("Agent research", "Agent research", event="schedule")])
    assert c["astro-auditor"]["state"] == "running" and c["numerologist"]["state"] == "running"


def test_a_ranked_cycle_says_it_is_picking_never_guesses_a_pr():
    c = _cards([_run("Agent work", "Agent work")], [_pr(951, "issue/835-sun-career", title="answer-first lede")])
    assert c["dev-lead"]["state"] == "building"
    assert c["dev-lead"]["detail"].startswith("picking the next issue from the ranked backlog")
    assert "951" not in c["dev-lead"]["detail"]


def test_a_qa_round_is_qa_running_not_developer_building():
    c = _cards([_run("Agent work", "QA round: PR #940")], [_pr(940, "partial/812-lede", title="lede rewrite")])
    assert c["qa"]["state"] == "running"
    assert "reviewing PR #940 · lede rewrite · issue #812" in c["qa"]["detail"]
    assert c["dev-lead"]["state"] == "done"  # from agents.json, not from the QA run


def test_every_running_workflow_is_listed_with_what_it_works_on():
    active = [
        _run("PR gates", "lede rewrite", branch="partial/812-lede", event="pull_request", minutes_ago=3),
        _run("Agent work", "Agent work: issue #835", minutes_ago=20),
        _run("Agent measure", "Agent measure", event="schedule", minutes_ago=1),
        _run("Agent merge", "Agent merge", status="queued", event="workflow_run", minutes_ago=30),
    ]
    doc = agent_status.build(active, [_pr(940, "partial/812-lede", title="lede rewrite")], LOOPS, now=NOW)
    wf = {w["name"]: w for w in doc["workflows"]}
    assert wf["PR gates"]["target"] == "PR #940 · lede rewrite" and wf["PR gates"]["target_url"].endswith("/pull/940")
    assert wf["Agent work"]["target"] == "issue #835" and wf["Agent work"]["target_kind"] == "issue"
    assert wf["Agent measure"]["target"] == "scheduled run"
    assert wf["Agent merge"]["state"] == "queued"
    assert [w["state"] for w in doc["workflows"]] == ["running", "running", "running", "queued"]  # running first
    assert doc["workflows"][0]["name"] == "Agent work"  # oldest RUNNING first, though the queued one is older


def test_a_still_running_history_row_does_not_say_finished():
    loops = [{"workflow": "agent-steward.yml", "last_run": "2026-11-13T05:00:00Z", "last_conclusion": None}]
    assert "started 1h ago" in _cards(loops=loops)["steward"]["detail"]


def test_labels_decide_qa_merge_and_chief():
    # Order matters: the cleared and the held PRs come FIRST, so a card that
    # stopped excluding them would name them instead of the right PR.
    prs = [
        _pr(4, "issue/4-d", ("needs-human-review", "chief-cleared")),
        _pr(3, "fix/3-c", ("qa-pass", "needs-human-review")),
        _pr(1, "issue/1-a", ("qa-fail",)),
        _pr(2, "issue/2-b", ("qa-pass", "qa:independent")),
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
    assert c["product-manager"]["state"] == "idle"  # no row in agents.json


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


def test_snapshot_fetches_the_title_of_the_issue_a_cycle_names(monkeypatch: pytest.MonkeyPatch):
    def fake(path: str):
        if path.startswith("pulls"):
            return []
        if path.startswith("issues/"):
            return {"title": "Debilitated Sun and career"}
        return {"workflow_runs": [_run("Agent work", "Agent work: issue #835")] if "in_progress" in path else []}

    monkeypatch.setattr(agent_status, "_get", fake)
    monkeypatch.setattr(agent_status, "_loops", lambda: LOOPS)
    monkeypatch.setattr(agent_status, "_cache", None)
    dev = {a["id"]: a for a in agent_status.snapshot()["agents"]}["dev-lead"]
    assert "issue #835 · Debilitated Sun and career" in dev["detail"]


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
