"""scripts/cycle_queue.py -- a dispatch made while a cycle runs is QUEUED, not lost.

The defect this guards, measured: `agent-work` runs one cycle at a time and
GitHub keeps one pending run per concurrency group, cancelling the older when a
third arrives. So `dispatch_cycle.sh` refused to dispatch behind a running cycle
and printed "waits for the next run" -- and nothing ever came back for it. PR
#649 had two green heads deferred that way in one day and was reviewed on
neither (#560: qa-on-green's one-per-commit marker was already spent).

Every test drives the real functions through a fake `gh` that keeps comments in
memory, so enqueue -> pending -> drain -> mark runs end to end.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cycle_queue", ROOT / "scripts" / "cycle_queue.py")
cq = importlib.util.module_from_spec(_spec)
sys.modules["cycle_queue"] = cq
_spec.loader.exec_module(cq)

REPO = "owner/repo"


class FakeGh:
    """Answers exactly the calls cycle_queue.py makes, and records them."""

    def __init__(self, *, busy="0", labels=None):
        self.comments: list[dict] = []
        self.busy = busy
        self.labels = labels or {}          # target -> "a,b"
        self.calls: list[list[str]] = []
        self._id = 100

    def add(self, body, login=cq.WRITER, on=1):
        self._id += 1
        self.comments.append({"id": self._id, "body": body, "login": login, "on": on,
                              "created_at": f"2026-11-02T10:{self._id - 100:02d}:00Z"})
        return self._id

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["api", "--paginate"]:
            return "\n".join(json.dumps({k: c[k] for k in ("id", "body", "created_at", "login")})
                             for c in self.comments)
        if args[:3] == ["api", "-X", "POST"]:
            on = int(args[3].split("/issues/")[1].split("/")[0])
            self.add(args[5][len("body="):], on=on)
            return "{}"
        if args[:3] == ["api", "-X", "PATCH"]:
            cid = int(args[3].rsplit("/", 1)[1])
            next(c for c in self.comments if c["id"] == cid)["body"] = args[5][len("body="):]
            return "{}"
        if args[:2] == ["run", "list"]:
            if self.busy == "error":
                raise RuntimeError("gh run list failed")
            return self.busy + "\n"
        if args[0] == "api" and "/issues/" in args[1]:
            return self.labels.get(int(args[1].rsplit("/", 1)[1]), "") + "\n"
        raise AssertionError(f"unexpected gh call: {args}")


class FakeCarrier:
    def __init__(self, results):
        self.results = list(results)        # each: (rc, run_id or None)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, ruling, who):
        self.calls.append((ruling, who))
        rc, run = self.results.pop(0)
        return rc, ({"DISPATCHED_RUN": run} if run else {}), f"carrier rc={rc}"


def entry(kind, target, by="qa-on-green"):
    return f"<!-- {cq.MARK}: kind={kind} target={target} by={by} -->\nQueued."


# --------------------------------------------------------------- enqueue

def test_enqueue_writes_a_marker_where_it_is_told_to(capsys):
    gh = FakeGh()
    assert cq.enqueue(gh, REPO, "issue", 616, "qa-on-green", on=642) == 0
    [c] = gh.comments
    assert c["on"] == 642, "qa-on-green may comment on its PR, not on the issue"
    assert f"<!-- {cq.MARK}: kind=issue target=616 by=qa-on-green -->" in c["body"]
    assert [e.target for e in cq.pending(gh, REPO)] == [616]


def test_the_same_ruling_is_never_queued_twice(capsys):
    gh = FakeGh()
    cq.enqueue(gh, REPO, "pr", 649, "steward", on=649)
    cq.enqueue(gh, REPO, "pr", 649, "chief", on=649)
    assert len(gh.comments) == 1
    assert "already queued" in capsys.readouterr().out


def test_an_issue_and_a_pr_with_the_same_number_are_different_rulings():
    """The number spaces overlap; `issue=642` and `pr=642` aim at different things."""
    gh = FakeGh()
    cq.enqueue(gh, REPO, "pr", 642, "steward", on=642)
    cq.enqueue(gh, REPO, "issue", 642, "steward", on=642)
    assert {(e.kind, e.target) for e in cq.pending(gh, REPO)} == {("pr", 642), ("issue", 642)}


def test_a_role_name_with_spaces_or_brackets_still_round_trips():
    gh = FakeGh()
    cq.enqueue(gh, REPO, "pr", 5, "queue (qa-on-green)", on=5)
    [e] = cq.pending(gh, REPO)
    assert e.by == "queue-qa-on-green"


def test_a_failed_write_is_exit_1_not_a_silent_success(capsys):
    def broken(args):
        if args[:3] == ["api", "-X", "POST"]:
            raise RuntimeError("403")
        return ""
    assert cq.enqueue(broken, REPO, "pr", 5, "x", on=5) == 1
    assert "could not queue" in capsys.readouterr().out


# --------------------------------------------------------------- pending

def test_only_entries_written_by_github_actions_count():
    """Every writer uses `github.token`. A marker pasted by anyone else would aim
    a ~50-minute cycle at a target nobody ruled on."""
    gh = FakeGh()
    gh.add(entry("pr", 1), login="drive-by-contributor")
    gh.add(entry("pr", 2), login="claude[bot]")
    gh.add(entry("pr", 3))
    assert [e.target for e in cq.pending(gh, REPO)] == [3]


def test_taken_and_dropped_entries_are_not_pending():
    gh = FakeGh()
    gh.add(entry("pr", 1).replace(f"{cq.MARK}: ", f"{cq.MARK}-taken: "))
    gh.add(entry("pr", 2).replace(f"{cq.MARK}: ", f"{cq.MARK}-dropped: "))
    gh.add(entry("pr", 3))
    assert [e.target for e in cq.pending(gh, REPO)] == [3]


def test_pending_asks_only_for_the_last_week():
    gh = FakeGh()
    cq.pending(gh, REPO, now=datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc))
    assert "since=2026-11-02T12:00:00Z" in gh.calls[0][2]


def test_pending_is_oldest_first_whatever_order_the_api_returns():
    gh = FakeGh()
    gh.add(entry("pr", 1))
    gh.add(entry("pr", 2))
    gh.comments.reverse()
    assert [e.target for e in cq.pending(gh, REPO)] == [1, 2]


# --------------------------------------------------------------- drain

def test_drain_does_nothing_while_a_cycle_runs():
    gh = FakeGh(busy="1")
    gh.add(entry("pr", 1))
    car = FakeCarrier([])
    assert cq.drain(gh, REPO, car) == 0
    assert car.calls == []
    assert len(cq.pending(gh, REPO)) == 1


def test_an_unreadable_busy_check_counts_as_busy():
    gh = FakeGh(busy="error")
    gh.add(entry("pr", 1))
    car = FakeCarrier([])
    cq.drain(gh, REPO, car)
    assert car.calls == []


def test_drain_starts_the_OLDEST_entry_and_only_one():
    gh = FakeGh()
    gh.add(entry("pr", 649, by="steward"))
    gh.add(entry("pr", 636, by="chief"))
    car = FakeCarrier([(0, "777")])
    assert cq.drain(gh, REPO, car) == 0
    assert car.calls == [("pr=649", "queue(steward)")]
    assert [e.target for e in cq.pending(gh, REPO)] == [636], "one cycle at a time"
    taken = gh.comments[0]["body"]
    assert f"{cq.MARK}-taken: " in taken and "777" in taken


def test_a_refused_entry_is_dropped_and_the_next_one_is_tried():
    gh = FakeGh()
    gh.add(entry("issue", 610))         # closed issue: the carrier refuses
    gh.add(entry("pr", 636))
    car = FakeCarrier([(1, None), (0, "888")])
    cq.drain(gh, REPO, car)
    assert [r for r, _ in car.calls] == ["issue=610", "pr=636"]
    assert f"{cq.MARK}-dropped: " in gh.comments[0]["body"]
    assert f"{cq.MARK}-taken: " in gh.comments[1]["body"]


def test_a_race_with_another_dispatcher_leaves_the_entry_queued():
    """rc 0 with no run means the carrier found a cycle in flight after all."""
    gh = FakeGh()
    gh.add(entry("pr", 1))
    car = FakeCarrier([(0, None)])
    cq.drain(gh, REPO, car)
    assert [e.target for e in cq.pending(gh, REPO)] == [1]


def test_a_pr_that_already_carries_qa_pass_is_dropped_without_a_cycle():
    gh = FakeGh(labels={649: "qa-pass,qa:in-cycle"})
    gh.add(entry("pr", 649))
    car = FakeCarrier([])
    cq.drain(gh, REPO, car)
    assert car.calls == []
    assert "already carries `qa-pass`" in gh.comments[0]["body"]


def test_a_qa_fail_pr_IS_started():
    """qa-fail is exactly the state a manual round exists for (#649, #636)."""
    gh = FakeGh(labels={649: "qa-fail,qa:in-cycle"})
    gh.add(entry("pr", 649))
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls == [("pr=649", "queue(qa-on-green)")]


def test_main_refuses_a_missing_or_malformed_repo(monkeypatch):
    monkeypatch.delenv("GH_REPO", raising=False)
    assert cq.main(["cycle_queue.py", "drain"], gh=FakeGh()) == 2
    monkeypatch.setenv("GH_REPO", "not a repo")
    assert cq.main(["cycle_queue.py", "drain"], gh=FakeGh()) == 2


# ----------------------------------------- the carrier queues instead of dropping

def _bin(tmp_path: Path) -> Path:
    b = tmp_path / "bin"
    b.mkdir()
    (b / "gh").write_text(f"""#!/usr/bin/env bash
echo "$*" >> "{tmp_path}/gh.log"
case "$*" in
  *"issue view"*"--json url"*) echo 'https://github.com/owner/repo/issues/1' ;;
  *"pr view"*|*"issue view"*) echo 'OPEN' ;;
  *"run list"*) echo '1' ;;
  *"api --paginate"*) : ;;
  *"api -X POST"*) echo '{{}}' ;;
  *) echo "UNEXPECTED gh $*" >&2; exit 9 ;;
esac
""")
    (b / "gh").chmod(0o755)
    return b


@pytest.mark.parametrize("ruling,queue_on,where", [
    ("pr=649", None, "issues/649/comments"),
    ("issue=616", "642", "issues/642/comments"),
])
def test_the_carrier_QUEUES_a_ruling_when_a_cycle_is_running(ruling, queue_on, where, tmp_path):
    f = tmp_path / "ruling.txt"
    f.write_text(ruling + "\n")
    env = dict(os.environ, PATH=f"{_bin(tmp_path)}:{os.environ['PATH']}", GH_REPO="owner/repo")
    env.pop("GITHUB_ENV", None)
    if queue_on:
        env["QUEUE_ON"] = queue_on
    r = subprocess.run(["bash", str(ROOT / "scripts" / "dispatch_cycle.sh"), str(f), "qa-on-green"],
                       capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "QUEUED, not dropped" in r.stdout
    log = (tmp_path / "gh.log").read_text()
    posts = [l for l in log.splitlines() if l.startswith("api -X POST")]
    assert len(posts) == 1 and where in posts[0], log
    assert "workflow run" not in log, "a busy carrier must never dispatch"


# --------------------------------------------------------------- wiring

def _wf(name):
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())


def test_agent_queue_drains_on_COMPLETION_of_agent_work_and_the_steward():
    """Not from a step inside agent-work: that run is still in progress, so the
    dispatch would land in the cancellable pending slot."""
    doc = _wf("agent-queue.yml")
    on = doc.get("on") or doc.get(True)
    assert on["workflow_run"]["workflows"] == ["Agent work", "Agent steward"]
    assert on["workflow_run"]["types"] == ["completed"]
    assert "schedule" not in on, "a cron here costs ~1,400 Actions minutes a month"
    run = doc["jobs"]["drain"]["steps"][-1]["run"]
    assert "cycle_queue.py drain" in run and "${{" not in run


def test_qa_on_green_queues_on_its_own_PR():
    steps = _wf("qa-on-green.yml")["jobs"]["consider"]["steps"]
    carry = next(s for s in steps if s.get("name") == "Carry out the dispatch")
    assert carry["env"]["QUEUE_ON"] == "${{ steps.pick.outputs.pr }}"


def test_the_queue_needs_no_label_writes():
    """qa-on-green is barred from labels so it can never hand itself qa-pass."""
    src = (ROOT / "scripts" / "cycle_queue.py").read_text()
    assert "--add-label" not in src and "--remove-label" not in src
    assert "/labels" not in src, "the label endpoints are where a write would go"
