"""Growth goals, their meters and the 60/40 split (owner, 2026-11-19).

scripts/growth_split.py against an in-memory GitHub, the agent-sync / agent-measure wiring,
and the "Goals and agent decisions" panel on /admin/ops rendered through the real route.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from astro_ai import llm_stats, ops_data

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("growth_split", ROOT / "scripts" / "growth_split.py")
gs = importlib.util.module_from_spec(_spec)
sys.modules["growth_split"] = gs
_spec.loader.exec_module(gs)

REPO = "o/r"
# Thursday 2026-11-19 12:00 UTC = 17:30 IST, ISO week 2026-W47, month 2026-11, quarter 2026-Q4.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def _issue(n, labels=(), title="t", state="open"):
    return {"number": n, "title": title, "state": state, "labels": list(labels)}


def goals_comment(level="weekly", period="2026-W47", goals=None, login="github-actions[bot]", **extra):
    key = gs.LEVELS[level][0]
    doc = {key: period, "goals": goals or [{"id": "g1", "goal": "clicks", "metric_key": "gsc_clicks_28d",
                                            "baseline": 300, "target": 400, "issues": [7]}], **extra}
    return {"login": login, "at": "2026-11-16T10:00:00Z",
            "body": f"<!-- {level}-goals {key}={period} -->\nprose\n```json\n{json.dumps(doc)}\n```\n"}


def score_comment(level="weekly", period="2026-W46", status="met", login="claude[bot]"):
    key = gs.LEVELS[level][0]
    doc = {key: period, "results": [{"id": "g1", "status": status, "actual": 1}], "lacking": "supply",
           "direction": "file band pages"}
    return {"login": login, "at": "2026-11-15T10:00:00Z",
            "body": f"<!-- {level}-goals-score {key}={period} -->\n```json\n{json.dumps(doc)}\n```"}


class Gh:
    def __init__(self, comments=(), issues=(), goals_issue=50, singles=None):
        self.comments, self.issues = list(comments), list(issues)
        self.goals_issue, self.singles, self.calls = goals_issue, singles or {}, []

    def __call__(self, args):
        self.calls.append(args)
        path = next(a for a in args if a.startswith("repos/"))
        if "labels=weekly-goals" in path:
            return json.dumps([{"number": self.goals_issue}] if self.goals_issue else [])
        if path.endswith("/comments?per_page=100"):
            return "\n".join(json.dumps(c) for c in self.comments)
        if "/comments?since=" in path:            # the outbox's dedupe read
            return ""
        if "-X" in args and path.endswith("/issues"):
            self.goals_issue = 99
            return json.dumps({"number": 99})
        if "-X" in args and path.endswith("/comments"):
            return "{}"
        if "issues?state=all" in path:
            return "\n".join(json.dumps(i) for i in self.issues)
        n = int(path.rsplit("/", 1)[1])
        return json.dumps(self.singles[n])


def _row(run, started, issue, kind="ranked", **kw):
    return {"run": run, "started": started, "issue": issue, "kind": kind, "outcome": "shipped", **kw}


# --------------------------------------------------------------- classification and the rule

@pytest.mark.parametrize("issue,expected", [
    (_issue(1, ["growth"]), "growth"),
    (_issue(1, ["seo"]), "growth"),
    (_issue(1, ["funnel:ask"]), "growth"),
    (_issue(1, ["bug", "severity:blocker", "growth"]), "exempt"),
    (_issue(1, ["priority:high"], title="[OPS] loop stalled"), "exempt"),
    (_issue(1, ["priority:medium"], title="[OPS] amber thing"), "other"),
    (_issue(1, ["bug"]), "other"),
    (None, "other"),
])
def test_every_issue_is_classed(issue, expected):
    assert gs.classify(issue, set()) == expected


def test_an_issue_a_current_goal_names_counts_as_growth():
    assert gs.classify(_issue(7, ["bug"]), {7}) == "growth"


def test_the_pick_rule_holds_the_running_share_at_or_just_above_60_percent():
    g = o = 0
    for _ in range(20):
        if gs.must_pick_growth(g, o):
            g += 1
        else:
            o += 1
    assert gs.must_pick_growth(0, 0) is True, "a day's first pick is growth"
    assert g / (g + o) >= 0.6 and g / (g + o) < 0.7


# --------------------------------------------------------------- goals

def test_only_trusted_this_period_goals_count_and_the_newest_wins():
    late = goals_comment(goals=[{"id": "g9", "goal": "newer", "issues": []}])
    late["at"] = "2026-11-17T00:00:00Z"
    gh = Gh([goals_comment(login="random-person"), goals_comment(period="2026-W46"),
             goals_comment(), late, score_comment()])
    g = gs.read_goals(gh, REPO, NOW)
    assert [x["id"] for x in g["current"]["goals"]] == ["g9"]
    assert g["previous_score"]["direction"] == "file band pages"


def test_an_outsiders_goals_are_ignored_entirely():
    g = gs.read_goals(Gh([goals_comment(login="random-person")]), REPO, NOW)
    assert g["current"] is None


def test_last_months_goals_are_not_this_months():
    gh = Gh([goals_comment("monthly", "2026-10"), goals_comment("quarterly", "2026-Q4")])
    lv = gs.read_goals(gh, REPO, NOW)["levels"]
    assert lv["monthly"]["current"] is None and lv["monthly"]["period"] == "2026-11"
    assert lv["quarterly"]["current"]["quarter"] == "2026-Q4"


def test_a_marker_whose_json_names_another_period_is_rejected():
    c = goals_comment()
    c["body"] = c["body"].replace('"week": "2026-W47"', '"week": "2026-W40"')
    assert gs.read_goals(Gh([c]), REPO, NOW)["current"] is None


def test_weeks_are_monday_to_sunday_in_ist():
    # Sunday 23:00 IST is still W47; Monday 00:10 IST is W48.
    assert gs.iso_week(datetime(2026, 11, 22, 17, 30, tzinfo=timezone.utc)) == "2026-W47"
    assert gs.iso_week(datetime(2026, 11, 22, 18, 40, tzinfo=timezone.utc)) == "2026-W48"


# --------------------------------------------------------------- progress and meters

def test_progress_is_measured_clamped_and_works_for_a_falling_target():
    m = {"gsc_clicks_28d": 350, "objective_top5": 3}
    assert gs.progress({"metric_key": "gsc_clicks_28d", "baseline": 300, "target": 400}, m, {})["progress"] == 0.5
    assert gs.progress({"metric_key": "gsc_clicks_28d", "baseline": 300, "target": 320}, m, {})["progress"] == 1.0
    assert gs.progress({"metric_key": "gsc_clicks_28d", "baseline": 400, "target": 500}, m, {})["progress"] == 0.0
    # a position: 8 -> 5, now 6.5
    assert gs.progress({"metric_key": "pos", "baseline": 8, "target": 5}, {"pos": 6.5}, {})["progress"] == 0.5


def test_progress_falls_back_to_closed_issues_then_to_nothing():
    issues = {7: _issue(7, state="closed"), 8: _issue(8)}
    p = gs.progress({"metric_key": "unknown", "issues": [7, 8]}, {}, issues)
    assert p["progress"] == 0.5 and p["basis"] == "issues"
    assert gs.progress({"goal": "x"}, {}, issues)["progress"] is None


def _mdir(tmp_path, top_positions=(3, 4, 8, 9, 10, 11, 12, 13, 14, 15)):
    d = tmp_path / "m"
    d.mkdir()
    rows = [{"query": f"q{i}", "impressions": 1000 - i, "position": p} for i, p in enumerate(top_positions)]
    rows.append({"query": "small", "impressions": 1, "position": 1.0})
    (d / "gsc-trend-query.json").write_text(json.dumps({"window": ["a", "b"], "rows": rows}))
    (d / "gsc-daily.json").write_text(json.dumps({"total_clicks": 350, "total_impressions": 9000}))
    (d / "ga4-daily.json").write_text(json.dumps({"rows": [{"active_users": 5, "new_users": 4, "sessions": 6}]}))
    return d


def test_the_overall_meter_is_the_objective_top10_queries_in_the_top_5(tmp_path):
    top = gs.objective_top5(_mdir(tmp_path))
    assert (top["value"], top["of"]) == (2, 10), "the low-impression query at #1 is outside the top 10"


def test_build_counts_ist_days_and_kinds_and_fills_all_five_meters(tmp_path):
    rows = [
        _row(1, "2026-11-19T10:00:00Z", 7),                    # today, growth (goal issue)
        _row(2, "2026-11-19T09:00:00Z", 8),                    # today, other
        _row(3, "2026-11-18T19:00:00Z", 9),                    # 00:30 IST on the 19th: today, growth
        _row(4, "2026-11-19T08:00:00Z", 8, kind="qa-round"),   # not a choice of work
        _row(5, "2026-11-19T07:00:00Z", None),                 # no issue
        _row(6, "2026-11-16T07:00:00Z", 8),                    # Monday, this week
    ]
    issues = {7: _issue(7, ["bug"]), 8: _issue(8, ["bug"]), 9: _issue(9, ["growth"])}
    goals = gs.read_goals(Gh([goals_comment()]), REPO, NOW)
    doc = gs.build(rows, issues, goals, NOW, _mdir(tmp_path))
    assert doc["today"] == {"growth": 2, "other": 1, "exempt": 0, "share": 0.667}
    assert doc["this_week"]["growth"] == 2 and doc["this_week"]["other"] == 2
    assert doc["must_pick_growth"] is True, "an other pick now would drop today to 2 of 4 = 50%"
    m = doc["meters"]
    assert m["daily"]["progress"] == 1.0
    assert m["weekly"]["progress"] == 0.5 and m["weekly"]["goals"][0]["current"] == 350
    assert m["monthly"]["progress"] is None and "no goals" in m["monthly"]["detail"]
    assert m["overall"]["progress"] == 0.2
    assert gs.validate(doc) == []


def test_main_writes_nothing_when_github_cannot_be_read(tmp_path):
    loop = tmp_path / "loop.json"
    loop.write_text(json.dumps({"rows": []}))
    out = tmp_path / "g.json"

    def down(args):
        raise RuntimeError("HTTP 502")
    assert gs.main(["--loop", str(loop), "--out", str(out), "--repo", REPO], gh=down, now=NOW) == 1
    assert not out.exists()


# --------------------------------------------------------------- posting

def _file(tmp_path, name, comment):
    f = tmp_path / name
    f.write_text(comment["body"])
    return str(f)


def test_valid_goals_and_scores_are_posted_scores_first(tmp_path):
    gh = Gh()
    a = _file(tmp_path, "weekly-goals.md", goals_comment(period="2026-W48"))
    b = _file(tmp_path, "weekly-score.md", score_comment(period="2026-W47"))
    assert gs.main(["--repo", REPO, "--post", a, b, str(tmp_path / "monthly-goals.md")], gh=gh, now=NOW) == 0
    bodies = [a for c in gh.calls if "-X" in c for a in c if a.startswith("body=")]
    assert "weekly-goals-score" in bodies[0] and "weekly-goals week=2026-W48" in bodies[1]
    assert all("<!-- outbox: kind=growth-goals " in b for b in bodies), "posted through the outbox (#1188)"


def test_the_standing_issue_is_created_when_missing(tmp_path):
    gh = Gh(goals_issue=None)
    assert gs.main(["--repo", REPO, "--post", _file(tmp_path, "w.md", goals_comment())], gh=gh, now=NOW) == 0
    assert any("labels[]=weekly-goals" in c for c in gh.calls)
    assert any(a.startswith("repos/o/r/issues/99/comments") for c in gh.calls for a in c)


def test_an_invalid_file_is_refused_and_nothing_is_posted(tmp_path):
    f = tmp_path / "weekly-goals.md"
    f.write_text("<!-- weekly-goals week=2026-W48 -->\nno json here")
    gh = Gh()
    assert gs.main(["--repo", REPO, "--post", str(f)], gh=gh, now=NOW) == 1
    assert not any("-X" in c for c in gh.calls)


# --------------------------------------------------------------- wiring

def _wf(name):
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())


def test_the_goals_review_is_on_sunday_before_sundays_ranking():
    on = _wf("agent-sync.yml").get(True) or _wf("agent-sync.yml")["on"]
    crons = [c["cron"] for c in on["schedule"]]
    assert "23 15 * * 0" in crons
    prio = _wf("agent-prioritise.yml").get(True)["schedule"][0]["cron"]
    assert prio == "0 17 * * 0", "the goals must land before Sunday's ranking"


def test_goals_are_posted_only_on_sunday_or_by_hand_and_the_sync_skips_sunday():
    steps = {s.get("name"): s for s in _wf("agent-sync.yml")["jobs"]["sync"]["steps"]}
    post = steps["Post the weekly growth goals"]
    assert "'23 15 * * 0'" in post["if"] and "workflow_dispatch" in post["if"]
    assert "growth_split.py" in post["run"] and "--post" in post["run"]
    assert post["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert "'23 15 * * 0'" in steps["Sync"]["if"]


def test_agent_measure_collects_the_split_after_the_loop():
    steps = [s.get("name") for s in _wf("agent-measure.yml")["jobs"]["commit"]["steps"]]
    assert steps.index("Collect the growth split") > steps.index("Collect loop measurements")


# --------------------------------------------------------------- the panel

@pytest.fixture
def mdir(monkeypatch, tmp_path):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    d = tmp_path / "ops"
    d.mkdir()
    monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(d))
    ops_data._cache.clear()
    yield d
    ops_data._cache.clear()


def test_the_panel_says_not_collected_without_the_file(mdir):
    assert ops_data._growth_view(None, None, "2026-11-19", NOW) is None


def test_the_panel_renders_meters_split_and_decisions(client, mdir, monkeypatch, tmp_path):
    issues = {7: _issue(7, ["growth"], title="band page"), 8: _issue(8, ["bug"], title="a bug")}
    rows = [_row(1, "2026-11-19T10:00:00Z", 7, agents_called={"architect": 1, "backend-engineer": 2}),
            _row(2, "2026-11-19T09:00:00Z", 8)]
    doc = gs.build(rows, issues, gs.read_goals(Gh([goals_comment()]), REPO, NOW), NOW, _mdir(tmp_path))
    (mdir / "growth.json").write_text(json.dumps(doc))
    (mdir / "loop.json").write_text(json.dumps({"generated_at": "2026-11-19T11:00:00Z", "rows": rows}))
    monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
    r = client.get("/admin/ops", auth=("admin", "bhagya-dev"))
    assert r.status_code == 200
    i = r.text.index('id="goals"')
    html = r.text[i: r.text.index("</section>", i)]
    for label in ("Today: growth share", "Weekly goals", "Monthly goals", "Quarterly goals", "Objective: top-10"):
        assert label in html
    assert 'aria-valuenow="50"' in html, "the weekly meter shows the goal's measured progress"
    assert "#7" in html and "band page" in html and "architect, backend-engineer×2" in html
    assert "g-target" in html and "Show the split as a table" in html
