"""#1186: liveness -- every event reaches an end, every ready PR merges.

Each finding is driven on fake API data until it fires, then the data is
moved to its resolved state and the finding must clear. The replay at the end
is the 2026-11-16/17 shape the owner found by hand: a QA PASS bound to the
head, gates red on that same head, the fix marked dispatched and its queue
entry dropped as "waiting to merge" (#1121, #1127, #1136, #1138).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("liveness", ROOT / "scripts" / "liveness.py")
lv = importlib.util.module_from_spec(_spec)
sys.modules["liveness"] = lv
_spec.loader.exec_module(lv)
cq = lv.cycle_queue
_fspec = importlib.util.spec_from_file_location("file_ops_findings", ROOT / "scripts" / "file_ops_findings.py")
fof = importlib.util.module_from_spec(_fspec)
_fspec.loader.exec_module(fof)

REPO = "owner/repo"
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
H, OLD = "a" * 40, "b" * 40
AUTHORS = {"claude[bot]", "github-actions[bot]", "shubhagya-publisher[bot]", "owner"}


def ago(hours: float) -> str:
    return (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Api:
    def __init__(self):
        self.queue: list[dict] = []          # repo comment feed (queue entries)
        self.comments: dict[int, list[dict]] = {}
        self.prs: list[dict] = []
        self.runs = {"agent-work.yml": [], "agent-measure.yml": [], "pr-gates.yml": [], "verify-build.yml": []}
        self._id = 0
        self.old_runs: list[dict] = []       # gate runs older than the shared page

    def entry(self, kind, target, *, state="", on, head="", age=8.0, note=""):
        self._id += 1
        mark = f"{cq.MARK}-{state}" if state else cq.MARK
        body = f"<!-- {mark}: kind={kind} target={target} by=qa-on-green" + (f" head={head}" if head else "") \
            + f" -->\nQueued.{note}"
        self.queue.append({"id": self._id, "body": body, "created_at": ago(age), "updated_at": ago(age),
                           "login": cq.WRITER, "issue_url": f"https://api.github.com/repos/{REPO}/issues/{on}"})

    def pr(self, num, *, head=H, ref="issue/55-x", labels=(), login="claude[bot]"):
        self.prs.append({"number": num, "head": {"sha": head, "ref": ref}, "user": {"login": login},
                         "labels": [{"name": l} for l in labels]})

    def say(self, num, body, *, login="claude[bot]", age=10.0):
        self.comments.setdefault(num, []).append({"body": body, "created_at": ago(age), "login": login})

    def gate(self, wf, head, conclusion, *, age=3.0, status="completed"):
        self.runs[wf].append({"id": len(self.runs[wf]) + 1, "head_sha": head, "status": status,
                              "conclusion": conclusion, "created_at": ago(age + 0.5),
                              "updated_at": ago(age), "name": lv.GATE_WORKFLOWS[wf]})

    def __call__(self, args):
        if args[:2] == ["api", "--paginate"] and "/issues/comments?" in args[2]:
            return "\n".join(json.dumps(c) for c in self.queue)
        if args[:2] == ["api", "--paginate"]:
            n = int(args[2].split("/issues/")[1].split("/")[0])
            return "\n".join(json.dumps(c) for c in self.comments.get(n, []))
        if args[0] == "api" and "/actions/runs?head_sha=" in args[1]:
            sha = args[1].split("head_sha=")[1].split("&")[0]
            return json.dumps({"workflow_runs": [r for wf in ("pr-gates.yml", "verify-build.yml")
                                                 for r in self.old_runs if r["head_sha"] == sha]})
        if args[0] == "api" and "/actions/workflows/" in args[1]:
            wf = args[1].split("/actions/workflows/")[1].split("/")[0]
            return json.dumps({"workflow_runs": self.runs[wf]})
        if args[0] == "api" and "/pulls?state=open" in args[1]:
            return json.dumps(self.prs)
        raise AssertionError(f"unexpected gh call: {args}")


def kinds(api):
    return {f["kind"]: f for f in lv.find(api, REPO, NOW, AUTHORS)}


# ------------------------------------------------------------ inbox-stale

def test_inbox_stale_fires_on_an_old_pending_entry_and_clears_once_taken_by_a_finished_run():
    api = Api()
    api.entry("pr", 649, on=649, age=7)
    f = kinds(api)["inbox-stale"]
    assert "`pr=649` on #649 (pending" in f["detail"] and "**Lever:**" in f["detail"]
    assert f["targets"] and f["level"] == "amber"
    api.queue[0]["body"] = api.queue[0]["body"].replace(f"{cq.MARK}: ", f"{cq.MARK}-taken: ") \
        + "\n\n**Taken:** agent-work run `777` started"
    api.runs["agent-work.yml"].append({"id": 777, "status": "completed"})
    assert "inbox-stale" not in kinds(api)


def test_a_taken_entry_whose_run_is_still_going_after_6h_is_stale():
    api = Api()
    api.entry("issue", 55, state="taken", on=55, age=7, note="\n\n**Taken:** agent-work run `778` started")
    api.runs["agent-work.yml"].append({"id": 778, "status": "in_progress"})
    assert "inbox-stale" in kinds(api)


def test_young_entries_and_dropped_ones_are_not_stale():
    api = Api()
    api.entry("pr", 1, on=1, age=5)
    api.entry("pr", 2, state="dropped", on=2, age=30)
    api.entry("pr", 3, state="claimed", on=3, age=2)
    assert "inbox-stale" not in kinds(api)


# --------------------------------------------------------- ready-unmerged

def _ready(api, num=1127, *, pass_age=8.0, labels=("qa-pass",)):
    api.pr(num, labels=labels)
    api.gate("pr-gates.yml", H, "success", age=9)
    api.say(num, f"QA: PASS — verified at `{H}`\nnotes", age=pass_age)


def test_ready_unmerged_fires_after_6h_and_clears_when_merged():
    api = Api()
    _ready(api)
    f = kinds(api)["ready-unmerged"]
    assert "PR #1127 at `aaaaaaa`" in f["detail"] and f["level"] == "red"
    assert "agent-merge" in f["detail"]
    api.prs.clear()                                 # merged: no longer open
    assert "ready-unmerged" not in kinds(api)


def test_ready_is_not_raised_before_6h_or_on_a_stale_pass_or_a_qa_fail():
    api = Api()
    _ready(api, pass_age=3)
    assert "ready-unmerged" not in kinds(api)
    api = Api()
    api.pr(1, labels=("qa-pass",))
    api.gate("pr-gates.yml", H, "success")
    api.say(1, f"QA: PASS — verified at `{OLD}`", age=20)       # an earlier commit
    assert "ready-unmerged" not in kinds(api)
    api = Api()
    _ready(api, labels=("qa-pass", "qa-fail"))
    assert "ready-unmerged" not in kinds(api)


def test_a_held_PR_is_ready_only_once_chief_cleared_ITS_head():
    api = Api()
    _ready(api, labels=("qa-pass", "needs-human-review"))
    assert "ready-unmerged" not in kinds(api), "a hold is chief's, not a stall"
    api.prs[0]["labels"].append({"name": "chief-cleared"})
    api.say(1127, f"chief-cleared at {OLD}")                      # a different head
    assert "ready-unmerged" not in kinds(api)
    api.say(1127, f"Ruling: chief-cleared at {H}")
    assert "chief-cleared" in kinds(api)["ready-unmerged"]["detail"]


def test_a_stranger_PASS_and_an_outside_author_do_not_count():
    api = Api()
    api.pr(1, labels=("qa-pass",))
    api.gate("pr-gates.yml", H, "success")
    api.say(1, f"QA: PASS — verified at `{H}`", login="someone", age=20)
    api.pr(2, head=OLD, labels=("qa-pass",), login="outsider")
    api.gate("pr-gates.yml", OLD, "success")
    api.say(2, f"QA: PASS — verified at `{OLD}`", age=20)
    assert "ready-unmerged" not in kinds(api)


# ---------------------------------------------------------- red-unhandled

def test_red_unhandled_fires_after_2h_and_clears_when_a_fix_is_queued():
    api = Api()
    api.pr(900, ref="feat/thing")
    api.gate("pr-gates.yml", H, "failure", age=3)
    f = kinds(api)["red-unhandled"]
    assert "PR #900 at `aaaaaaa`: PR gates red 3h ago; no fix dispatched" in f["detail"]
    api.entry("fix_pr", 900, on=900, head=H, age=0.2)
    assert "red-unhandled" not in kinds(api)


def test_red_under_2h_or_routed_to_a_session_is_not_raised():
    api = Api()
    api.pr(900, ref="feat/thing")
    api.gate("verify-build.yml", H, "failure", age=1)
    assert "red-unhandled" not in kinds(api)
    api = Api()
    api.pr(901, ref="feat/workflows")
    api.gate("pr-gates.yml", H, "failure", age=5)
    api.say(901, f"qa-on-green: red gates noted at {H}\n...", login=cq.WRITER)
    assert "red-unhandled" not in kinds(api), "red_gates.py routed this head to a session"


def test_a_fix_queued_for_an_OLD_head_does_not_cover_the_new_one():
    api = Api()
    api.pr(900, ref="feat/thing")
    api.gate("pr-gates.yml", H, "failure", age=3)
    api.entry("fix_pr", 900, on=900, head=OLD, age=0.5)
    assert "red-unhandled" in kinds(api)


def test_a_fix_run_that_finished_without_fixing_is_unhandled_again():
    api = Api()
    api.pr(900, ref="feat/thing")
    api.gate("pr-gates.yml", H, "failure", age=4)
    api.entry("fix_pr", 900, state="taken", on=900, head=H, age=3,
              note="\n\n**Taken:** agent-work run `55` started")
    api.runs["agent-work.yml"].append({"id": 55, "status": "completed"})
    assert "red-unhandled" in kinds(api)


def test_REPLAY_2026_11_17_pass_at_head_gates_red_fix_entry_dropped():
    """#1127's shape. Before #1185 the queue dropped the red-gates fix as
    'waiting to merge'; nothing raised anything and the PR sat ~24h."""
    api = Api()
    api.pr(1127, ref="issue/1120-ops-panel", labels=("qa-pass", "qa:in-cycle"))
    api.say(1127, f"QA: PASS — verified at `{H}`\nall green", age=26)
    api.gate("pr-gates.yml", H, "failure", age=22)
    api.say(1127, f"qa-on-green: fix dispatched at {H}\n...", login=cq.WRITER, age=22)
    api.entry("issue", 1120, state="dropped", on=1127, head=H, age=22,
              note="\n\n**Dropped:** issue #1120's PR #1127 carries `qa-pass` and is mergeable")
    found = kinds(api)
    assert "ready-unmerged" not in found, "gates are red on the head: not ready"
    f = found["red-unhandled"]
    assert "PR #1127" in f["detail"]
    assert "a fix was marked dispatched but no live queue entry carries it" in f["detail"]
    # ...and once the fix is queued again, it clears.
    api.entry("issue", 1120, on=1127, head=H, age=0.1)
    assert "red-unhandled" not in kinds(api)


def test_a_PR_whose_gates_ran_before_the_shared_page_is_still_seen():
    """Live on 2026-11-17 one page of PR-gates runs reached back ~16h. A ready
    PR stranded longer than that is the case this check exists for."""
    api = Api()
    api.pr(1136, labels=("qa-pass",))
    api.say(1136, f"QA: PASS — verified at `{H}`", age=30)
    api.old_runs.append({"id": 9, "head_sha": H, "status": "completed", "conclusion": "success",
                         "created_at": ago(31), "updated_at": ago(30), "name": "PR gates"})
    assert "PR #1136" in kinds(api)["ready-unmerged"]["detail"]


def test_measurement_PRs_are_never_findings():
    api = Api()
    api.pr(5, ref="measurements/123-1", login="shubhagya-publisher[bot]")
    api.gate("pr-gates.yml", H, "failure", age=10)
    assert kinds(api) == {}


# ----------------------------------------------------- filing and the CLI

def test_the_filer_owns_exactly_the_liveness_kinds():
    assert tuple(fof.LIVENESS_KINDS) == lv.KINDS


class Issues:
    """Enough of the issues API for file_ops_findings.carry."""

    def __init__(self, open_kinds):
        self.open = {k: 100 + i for i, k in enumerate(open_kinds)}
        self.posts: list[str] = []

    def __call__(self, args):
        if args[:2] == ["api", "--paginate"] and "/issues?state=open" in args[2]:
            return "\n".join(json.dumps({"number": n, "body": f"<!-- ops-finding: {k} -->\n<!-- ops-state: red|x -->"})
                             for k, n in self.open.items())
        if args[:2] == ["api", "--paginate"]:
            return ""
        if args[:3] == ["api", "-X", "POST"]:
            self.posts.append(args[3])
            return "{}"
        return "{}"


def test_a_liveness_run_never_clears_the_stewards_kinds_and_vice_versa():
    gh = Issues(["cache-low", "ready-unmerged"])
    fof.carry(gh, REPO, [], "now", scope="liveness")
    assert gh.posts == [f"repos/{REPO}/issues/101/comments"], "only ready-unmerged is cleared"
    gh = Issues(["cache-low", "ready-unmerged"])
    fof.carry(gh, REPO, [], "now", scope="ops")
    assert gh.posts == [f"repos/{REPO}/issues/100/comments"], "only cache-low is cleared"


def test_a_liveness_finding_is_filed_once_with_its_own_repro():
    gh = Issues([])
    f = {"kind": "red-unhandled", "level": "amber", "title": "1 red PR(s)", "detail": "d"}
    fof.carry(gh, REPO, [f, {"kind": "cache-low", "level": "red", "title": "t", "detail": "d"}],
              "now", scope="liveness")
    assert gh.posts == [f"repos/{REPO}/issues"], "the ops kind is not this run's to file"
    assert "python3 scripts/liveness.py" in fof.body_for(f, "now", "liveness")


def test_main_exit_codes(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_REPO", REPO)
    out = tmp_path / "l.json"
    assert lv.main(["liveness.py", "--out", str(out)], gh=Api(), now=NOW) == 0
    assert json.loads(out.read_text())["findings"] == []
    api = Api()
    api.entry("pr", 1, on=1, age=9)
    assert lv.main(["liveness.py", "--out", str(out)], gh=api, now=NOW) == 1

    def down(args):
        raise RuntimeError("api down")
    assert lv.main(["liveness.py", "--out", str(out)], gh=down, now=NOW) == 2
