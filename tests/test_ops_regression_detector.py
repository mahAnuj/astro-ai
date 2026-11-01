"""`scripts/detect_ops_regressions.py`: the ops page's numbers, read by something.

WHY THIS MATTERS MORE THAN A USUAL DETECTOR TEST. Asked whether any workflow
reads the ops dashboard and acts on it, the answer measured 2026-11-01 was NO:
`/admin/ops` and `ops_today` appear in `.github/workflows/` only inside
comments. Every number on that page was computed for a human who had to open
it. This script is the first reader, so a finding it gets wrong is a finding
nobody else is checking.

THE TWO FAILURE DIRECTIONS ARE NOT SYMMETRIC, and the cases below are weighted
accordingly:

  a MISSED finding   is the dashboard's existing failure mode, continued
  a FALSE finding    is worse here than there, because this detector FILES
                     ISSUES. A watcher that cries weekly gets muted, and then
                     the real one is muted too -- which is exactly why #628's
                     `loop-outcomes` miscount had to be fixed before anything
                     started reading these numbers.

So every threshold has a case on both sides of it, and every trend finding has
a case proving a one-day blip does NOT fire it.

UNREADABLE IS A FINDING, NOT A PASS. `test_an_unreadable_source_exits_1_and_says_which`
is the load-bearing case. `ops_data._alerts()` states the rule this carries
across: "Silence means checked-and-clear, never not-checked." A detector that
returns 0 because it could not look is the defect this repo keeps finding one
layer up, and it is invisible precisely when it matters.

THE HISTORY CASES USE A REAL TEMPORARY GIT REPOSITORY, because the trend is
read with `git log` and `git show` over `measurements/issues.json`. A fixture of
loose files would exercise only the "too few revisions" branch.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "detect_ops_regressions.py"

_spec = importlib.util.spec_from_file_location("detect_ops_regressions", SCRIPT)
det = importlib.util.module_from_spec(_spec)
sys.modules["detect_ops_regressions"] = det
_spec.loader.exec_module(det)

NOW = datetime(2026, 11, 1, 3, 0, tzinfo=timezone.utc)


def _agents(*, generated=None, alerts=(), loops=(), yield_pct=51, cycles=96,
            shipped=49, ok=True) -> dict:
    return {
        "generated_at": (generated or NOW).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "alerts": list(alerts),
        "loops": list(loops),
        "delivery": {"ok": ok, "cycles": cycles, "yield_pct": yield_pct,
                     "outcomes": {"shipped": shipped}},
    }


def _issues(*, open_=128, unset=40, high=18, stamp=None) -> dict:
    """A snapshot. `stamp` differs per revision ON PURPOSE.

    The real collector rewrites `generated_at` every run, so the file changes
    on every measurement even when no count moved. The first version of this
    fixture reused one timestamp, which made two same-count snapshots
    byte-identical -- and `git log -- <path>` SKIPS a commit that did not touch
    the path, so the history came back one revision long and every
    unchanged-counts case reported "a trend needs two" instead of asserting.
    """
    return {"generated_at": (stamp or NOW).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "open": open_,
            "by_priority": {"unset": unset, "high": high, "medium": 20, "low": 1}}


def _repo(tmp_path: Path, agents: dict, snapshots: list[tuple[int, dict]]) -> Path:
    """A repo whose `measurements/issues.json` history is `snapshots`.

    `snapshots` is [(days_ago, doc), ...] applied oldest first, each committed
    with `--date` so `%cI` gives the age the trend logic reads. Identity is
    passed with `-c` so the fixture never depends on the machine's git config.
    """
    root = tmp_path / "repo"
    (root / "measurements").mkdir(parents=True)
    (root / "measurements" / "agents.json").write_text(json.dumps(agents))

    def run(*a, env_date=None):
        env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
        if env_date:
            env |= {"GIT_AUTHOR_DATE": env_date, "GIT_COMMITTER_DATE": env_date}
        subprocess.run(("git", "-C", str(root), "-c", "user.name=t",
                        "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a),
                       check=True, timeout=60, capture_output=True, env=env)

    subprocess.run(("git", "init", "-q", str(root)), check=True, timeout=60)
    for days_ago, doc in sorted(snapshots, key=lambda s: -s[0]):
        doc = {**doc,
               "generated_at": (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")}
        (root / "measurements" / "issues.json").write_text(json.dumps(doc))
        when = (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S+0000")
        run("add", "-A")
        # `--allow-empty`, because two snapshots with identical counts is a
        # REAL state -- a quiet day commits the same numbers -- and the trend
        # logic has to handle it. Without this the fixture died on
        # "nothing to commit" and every unchanged-counts case errored instead
        # of asserting.
        run("commit", "-q", "--allow-empty", "-m", f"snapshot -{days_ago}d",
            env_date=when)
    return root


def _find(tmp_path, monkeypatch, agents: dict, snapshots: list[tuple[int, dict]]):
    root = _repo(tmp_path, agents, snapshots)
    monkeypatch.setattr(det, "ROOT", root)
    monkeypatch.setattr(det, "MEASUREMENTS", root / "measurements")
    return det.find(now=NOW)


def _kinds(findings) -> set[str]:
    return {f["kind"] for f in findings}


# ----------------------------------------------------------- triage debt

@pytest.mark.parametrize("unset,total,fires", [
    (89, 128, True),    # live 2026-11-01: 70%
    (65, 128, True),    # 51%
    (64, 128, False),   # 50% — AT the threshold, not over it
    (10, 128, False),
])
def test_triage_debt_fires_only_ABOVE_the_threshold(unset, total, fires,
                                                    tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _agents(),
                 [(8, _issues(open_=total, unset=unset)),
                  (0, _issues(open_=total, unset=unset))])
    assert ("triage-debt" in _kinds(f)) is fires, f


def test_triage_debt_does_not_divide_by_zero_on_an_empty_backlog(tmp_path, monkeypatch):
    """An empty backlog is the goal, not a finding.

    `unset * 100 / total` with total 0 would raise, and an exception here exits
    2 — a detector reporting "could not run" on the best possible state.
    """
    f, u = _find(tmp_path, monkeypatch, _agents(),
                 [(8, _issues(open_=0, unset=0, high=0)),
                  (0, _issues(open_=0, unset=0, high=0))])
    assert "triage-debt" not in _kinds(f)


# ------------------------------------------------------- backlog trend

def test_a_rising_backlog_over_the_window_is_reported(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _agents(),
                 [(8, _issues(open_=123)), (0, _issues(open_=128))])
    hit = next(x for x in f if x["kind"] == "backlog-growing")
    assert "123 -> 128" in hit["title"]
    # Amber, not red, and the detail says why: discovery filing real work looks
    # identical to the loop falling behind.
    assert hit["level"] == "amber"
    assert "not automatically wrong" in hit["detail"]


def test_a_FALLING_backlog_reports_nothing(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _agents(),
                 [(8, _issues(open_=140)), (0, _issues(open_=128))])
    assert "backlog-growing" not in _kinds(f)


def test_a_ONE_DAY_rise_does_not_fire_the_trend(tmp_path, monkeypatch):
    """The comparison needs a revision at least TREND_DAYS old.

    Without that, a single measurement taken mid-triage -- issues filed in the
    morning, closed by evening -- files an issue every day, and the watcher is
    muted within a week.
    """
    f, u = _find(tmp_path, monkeypatch, _agents(),
                 [(1, _issues(open_=123)), (0, _issues(open_=128))])
    assert "backlog-growing" not in _kinds(f)
    assert any("needs" in x and "trend" in x for x in u), u


def test_a_history_with_one_revision_is_UNREADABLE_not_clean(tmp_path, monkeypatch):
    f, u = _find(tmp_path, monkeypatch, _agents(), [(0, _issues())])
    assert any("a trend needs two" in x for x in u), u


# -------------------------------------------------- high-priority stall

@pytest.mark.parametrize("before,after,fires,word", [
    (18, 22, True, "up from"),
    (18, 18, True, "unchanged at"),
    (22, 18, False, ""),
    (0, 0, False, ""),      # none at all is not a stall
])
def test_high_priority_is_reported_when_it_does_not_FALL(before, after, fires, word,
                                                         tmp_path, monkeypatch):
    """`issues.json` has carried `by_priority` all along and nothing read it.

    `ops_data._alerts()` touches `issues` only for a snapshot-staleness
    warning, so neither the high-priority COUNT nor its TREND raised anything
    anywhere before this script.
    """
    f, _ = _find(tmp_path, monkeypatch, _agents(),
                 [(8, _issues(high=before)), (0, _issues(high=after))])
    hits = [x for x in f if x["kind"] == "high-priority-stalled"]
    assert bool(hits) is fires, f
    if fires:
        assert word in hits[0]["title"]
        assert hits[0]["level"] == "red"


# ------------------------------------------------------- loop liveness

def test_a_flagged_loop_is_reported_with_the_COLLECTORS_verdict(tmp_path, monkeypatch):
    """The verdict is looked up, never re-derived.

    `collect_agent_performance.py` already decides `broken`/`dormant`/
    `missing-slots`. A second opinion computed here could disagree with the
    page, which is #628 exactly: one fact, two surfaces, two answers.
    """
    agents = _agents(alerts=["agent-research.yml"],
                     loops=[{"workflow": "agent-research.yml", "verdict": "broken"},
                            {"workflow": "agent-work.yml", "verdict": "green"}])
    f, _ = _find(tmp_path, monkeypatch, agents,
                 [(8, _issues()), (0, _issues())])
    hit = next(x for x in f if x["kind"] == "loop-broken")
    assert hit["title"] == "agent-research.yml is broken"
    assert hit["level"] == "red"


def test_no_flagged_loops_reports_no_loop_finding(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _agents(alerts=[]),
                 [(8, _issues()), (0, _issues())])
    assert "loop-broken" not in _kinds(f)


@pytest.mark.parametrize("pct,fires", [(51, False), (35, False), (34, True), (9, True)])
def test_delivery_yield_fires_only_BELOW_the_floor(pct, fires, tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _agents(yield_pct=pct),
                 [(8, _issues()), (0, _issues())])
    assert ("delivery-yield" in _kinds(f)) is fires, f


def test_yield_is_not_judged_when_the_collector_says_it_could_not_measure(
        tmp_path, monkeypatch):
    """`delivery.ok == False` means the number is absent, not zero.

    Reading it anyway would file a 0% yield alert every time `loop.json` was
    unreadable -- a false red on a missing input, which is the shape of defect
    this whole session has been cataloguing.
    """
    f, _ = _find(tmp_path, monkeypatch, _agents(yield_pct=0, ok=False),
                 [(8, _issues()), (0, _issues())])
    assert "delivery-yield" not in _kinds(f)


# ----------------------------------------------------------- staleness

def test_a_stale_snapshot_is_reported_before_anything_derived_from_it(tmp_path, monkeypatch):
    old = NOW - timedelta(hours=det.STALE_HOURS + 2)
    f, _ = _find(tmp_path, monkeypatch, _agents(generated=old),
                 [(8, _issues()), (0, _issues())])
    hit = next(x for x in f if x["kind"] == "measurement-stale")
    assert hit["level"] == "red"
    assert "not about now" in hit["detail"]


def test_a_NORMALLY_LATE_scheduled_run_does_not_read_as_stale(tmp_path, monkeypatch):
    """GitHub delivers a cron late, always. Measured over 30 `agent-work` fires
    2026-10-17..11-01: min +1h42m, median +3h19m, max +6h21m, and not one
    inside 100 minutes. A 24h threshold would fire on a normal day, and a
    watcher that is wrong daily is a watcher nobody reads.
    """
    # Asserted as a RELATIONSHIP, not a number: 24h for the missed day plus
    # the 6h21m worst skew is 30.35h, so a threshold of 30 was wrong and a
    # test pinned to `== 30` would have agreed with it.
    assert det.STALE_HOURS >= 24 + 7, (
        'a day plus the worst measured skew (6h21m) is 30.35h')
    f, _ = _find(tmp_path, monkeypatch, _agents(generated=NOW - timedelta(hours=29)),
                 [(8, _issues()), (0, _issues())])
    assert "measurement-stale" not in _kinds(f)


# -------------------------------------------- unreadable is not a pass

def test_an_unreadable_source_exits_1_and_says_which(tmp_path, monkeypatch, capsys):
    """THE LOAD-BEARING CASE. A detector that exits 0 because it could not look
    is invisible exactly when it matters."""
    root = _repo(tmp_path, _agents(), [(8, _issues()), (0, _issues())])
    (root / "measurements" / "agents.json").write_text("{ not json")
    monkeypatch.setattr(det, "ROOT", root)
    monkeypatch.setattr(det, "MEASUREMENTS", root / "measurements")
    monkeypatch.chdir(root)
    rc = det.main(["detect_ops_regressions.py"])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "UNREAD" in out and "agents.json" in out


def test_a_missing_issues_file_does_not_silently_drop_the_backlog_checks(
        tmp_path, monkeypatch):
    root = _repo(tmp_path, _agents(), [(0, _issues())])
    (root / "measurements" / "issues.json").unlink()
    monkeypatch.setattr(det, "ROOT", root)
    monkeypatch.setattr(det, "MEASUREMENTS", root / "measurements")
    f, u = det.find(now=NOW)
    assert any("issues.json" in x for x in u), u


def test_a_clean_state_exits_0_and_says_the_sources_were_READABLE(
        tmp_path, monkeypatch, capsys):
    """"No findings" has to be distinguishable from "did not look"."""
    root = _repo(tmp_path, _agents(),
                 [(8, _issues(open_=140, unset=10, high=22)),
                  (0, _issues(open_=128, unset=10, high=18))])
    monkeypatch.setattr(det, "ROOT", root)
    monkeypatch.setattr(det, "MEASUREMENTS", root / "measurements")
    monkeypatch.chdir(root)
    rc = det.main(["detect_ops_regressions.py"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "every source was readable" in out


# ------------------------------------------------- the declared blind spots

def test_coverage_names_the_product_checks_this_script_cannot_see():
    """Silence is not health, and the script has to say so itself.

    `ops_data._alerts()`'s own first rule: "Silence means checked-and-clear,
    never not-checked."
    """
    concerns = {c for c, _, _ in det.NOT_COVERED}
    assert "LLM error rate" in concerns
    assert "daily token ceiling" in concerns
    assert any("cache hit ratio" in c for c in concerns)


def test_the_cache_hit_ratio_is_declared_as_alerted_on_by_NOTHING():
    """Found while writing this, and it is a gap not a blind spot.

    `ops_data` computes `cache_hits` and `cache_misses` and raises no alert at
    any threshold. The number is rendered and never judged. Recording that in
    `NOT_COVERED` is what stops the next reader assuming the dashboard has it
    covered.
    """
    entry = next(e for e in det.NOT_COVERED if "cache hit ratio" in e[0])
    assert "NOTHING" in entry[1]


def test_coverage_is_printed_on_request_and_not_by_default(tmp_path, monkeypatch, capsys):
    """An issue filed by the carrier should carry the blind spots; a terminal
    run checking one thing should not reprint six lines of them."""
    root = _repo(tmp_path, _agents(), [(8, _issues()), (0, _issues())])
    monkeypatch.setattr(det, "ROOT", root)
    monkeypatch.setattr(det, "MEASUREMENTS", root / "measurements")
    monkeypatch.chdir(root)
    det.main(["detect_ops_regressions.py"])
    assert "NOT COVERED" not in capsys.readouterr().out
    det.main(["detect_ops_regressions.py", "--coverage"])
    assert "NOT COVERED" in capsys.readouterr().out


def test_json_output_carries_findings_unreadable_AND_the_blind_spots(
        tmp_path, monkeypatch, capsys):
    """The carrier reads this, so all three have to survive the serialisation.

    Dropping `not_covered` would make a filed issue imply the product checks
    were green.
    """
    root = _repo(tmp_path, _agents(),
                 [(8, _issues(open_=123, unset=89)), (0, _issues(open_=128, unset=89))])
    monkeypatch.setattr(det, "ROOT", root)
    monkeypatch.setattr(det, "MEASUREMENTS", root / "measurements")
    monkeypatch.chdir(root)
    det.main(["detect_ops_regressions.py", "--json"])
    doc = json.loads(capsys.readouterr().out)
    assert {"findings", "unreadable", "not_covered"} <= set(doc)
    assert {"triage-debt", "backlog-growing"} <= {f["kind"] for f in doc["findings"]}
    assert len(doc["not_covered"]) == len(det.NOT_COVERED)
