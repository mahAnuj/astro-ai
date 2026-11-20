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

    def __init__(self, *, busy="0", busy_qa=None, labels=None, heads=None, fail_patch_after=None,
                 open_prs=None, gates=None):
        self.comments: list[dict] = []
        self.busy = busy                    # build lane (and the QA lane unless busy_qa given)
        self.busy_qa = busy if busy_qa is None else busy_qa
        self.labels = labels or {}          # target -> "a,b"
        self.heads = heads or {}            # pr -> head sha
        self.open_prs = open_prs or {}      # pr -> (head ref, "a,b" labels, mergeable "true"/"false"/"null")
        self.gates = gates or {}            # head sha -> list of Actions runs, or "error" to raise
        self.fail_patch_after = fail_patch_after   # PATCH calls allowed before failing
        self.patches = 0
        self.calls: list[list[str]] = []
        self._id = 100

    def add(self, body, login=cq.WRITER, on=1):
        self._id += 1
        self.comments.append({"id": self._id, "body": body, "login": login, "on": on,
                              "created_at": f"2026-11-02T10:{self._id - 100:02d}:00Z"})
        return self._id

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["api", "--paginate"] and "/issues/comments?" in args[2]:
            return "\n".join(json.dumps({k: c[k] for k in ("id", "body", "created_at", "login")})
                             for c in self.comments)
        if args[:2] == ["api", "--paginate"] and "user.login" in args[-1]:   # PASS verdicts + author
            n = int(args[2].split("/issues/")[1].split("/")[0])
            return "\n".join(f"{c['login']}\t{c['body'].splitlines()[0]}"
                             for c in self.comments
                             if c["on"] == n and c["body"].startswith("QA: PASS"))
        if args[:2] == ["api", "--paginate"]:          # one PR's comments: QA verdicts
            n = int(args[2].split("/issues/")[1].split("/")[0])
            return "\n".join(f"{c['created_at']} {c['body'].splitlines()[0]}"
                             for c in self.comments
                             if c["on"] == n and c["body"].startswith("QA: "))
        if args[0] == "api" and "/actions/runs?head_sha=" in args[1]:
            sha = args[1].split("head_sha=")[1].split("&")[0]
            runs = self.gates.get(sha, [])
            if runs == "error":
                raise RuntimeError("gh api failed")
            # The REAL jq runs over the fake runs, so the name filter and the
            # newest-run pick are exercised, not reimplemented here.
            p = subprocess.run(["jq", "-r", args[args.index("--jq") + 1]], capture_output=True,
                               text=True, input=json.dumps({"workflow_runs": runs}), timeout=30)
            assert p.returncode == 0, p.stderr
            return p.stdout
        if args[0] == "api" and "/pulls?state=open" in args[1]:
            return "\n".join(json.dumps({"number": n, "ref": ref, "sha": self.heads.get(n, ""),
                                         "labels": [l for l in labs.split(",") if l]})
                             for n, (ref, labs, _m) in self.open_prs.items())
        if args[0] == "api" and "/pulls/" in args[1] and args[-1] == ".mergeable_state":
            m = self.open_prs[int(args[1].rsplit("/", 1)[1])][2]
            return {"true": "clean", "false": "dirty", "null": "unknown"}.get(m, m) + "\n"
        if args[0] == "api" and "/pulls/" in args[1]:
            return self.heads.get(int(args[1].rsplit("/", 1)[1]), "") + "\n"
        if args[:3] == ["api", "-X", "POST"]:
            on = int(args[3].split("/issues/")[1].split("/")[0])
            self.add(args[5][len("body="):], on=on)
            return "{}"
        if args[:3] == ["api", "-X", "PATCH"]:
            self.patches += 1
            if self.fail_patch_after is not None and self.patches > self.fail_patch_after:
                raise RuntimeError("PATCH failed")
            cid = int(args[3].rsplit("/", 1)[1])
            next(c for c in self.comments if c["id"] == cid)["body"] = args[5][len("body="):]
            return "{}"
        if args[:2] == ["run", "list"]:
            jq = args[-1]
            lane = self.busy if "| not" in jq else self.busy_qa
            if lane == "error":
                raise RuntimeError("gh run list failed")
            return lane + "\n"
        if args[0] == "api" and "/issues/" in args[1]:
            return self.labels.get(int(args[1].rsplit("/", 1)[1]), "") + "\n"
        raise AssertionError(f"unexpected gh call: {args}")


class FakeCarrier:
    def __init__(self, results):
        self.results = list(results)        # each: (rc, run_id or None[, output])
        self.calls: list[tuple[str, str]] = []

    def __call__(self, ruling, who, **kw):   # drain passes entry= (2026-11-17)
        self.calls.append((ruling, who))
        rc, run, *out = self.results.pop(0)
        return rc, ({"DISPATCHED_RUN": run} if run else {}), (out[0] if out else f"carrier rc={rc}")


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
    assert cq.drain(gh, REPO, car) == 0, "a closed target is a legitimate refusal, not a red drain"
    assert [r for r, _ in car.calls] == ["issue=610", "pr=636"]
    assert f"{cq.MARK}-dropped: " in gh.comments[0]["body"]
    assert f"{cq.MARK}-taken: " in gh.comments[1]["body"]


def test_a_race_with_another_dispatcher_leaves_EXACTLY_ONE_live_entry():
    """rc 0 with no run: the carrier found a cycle running after all and, unable
    to see the CLAIMED entry, wrote a fresh one. Restoring the claimed entry too
    left two for one target (#675 QA round 2, N2)."""
    gh = FakeGh()
    gh.add(entry("pr", 1))

    def carrier(ruling, who, **kw):     # what the real carrier does when busy
        cq.enqueue(gh, REPO, "pr", 1, who, on=1)
        return 0, {}, "QUEUED, not dropped"
    cq.drain(gh, REPO, carrier)
    assert [(e.kind, e.target) for e in cq.pending(gh, REPO)] == [("pr", 1)]
    assert f"{cq.MARK}-dropped: " in gh.comments[0]["body"]

def test_a_pr_that_already_carries_qa_pass_is_dropped_without_a_cycle():
    """`qa-pass` AND a `QA: PASS` verdict naming the head: really decided."""
    sha = "a" * 40
    gh = FakeGh(labels={649: "qa-pass,qa:in-cycle"}, heads={649: sha})
    gh.add(f"QA: PASS — verified at `{sha}`\nnotes", login="claude[bot]", on=649)
    gh.add(entry("pr", 649), on=649)
    car = FakeCarrier([])
    cq.drain(gh, REPO, car)
    assert car.calls == []
    assert "already carries `qa-pass`" in gh.comments[-1]["body"]


def _stale_pass(pass_login="claude[bot]", head="b" * 40, passed_at="a" * 40, labels="qa-pass,qa:in-cycle"):
    gh = FakeGh(labels={812: labels}, heads={812: head})
    gh.add(f"QA: PASS — verified at `{passed_at}`\nnotes", login=pass_login, on=812)
    gh.add(entry("pr", 812), on=812)
    return gh


def test_a_qa_pass_bound_to_an_EARLIER_commit_does_not_drop_the_round():
    """#823 / PR #812: `qa-pass` was given at d182529, two `Merge origin/main`
    commits followed, and the queue dropped the very round qa-on-green had
    queued for the new head ("already carries qa-pass"). agent-merge refused
    the PR, every dispatcher ignored it, and qa-on-green's one dispatch for
    that commit was spent."""
    gh = _stale_pass()
    assert cq.stale_reason(gh, REPO, cq.pending(gh, REPO)[0]) is None
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls == [("pr=812", "queue(qa-on-green)")]


def test_a_PASS_comment_from_a_stranger_does_not_count_as_binding():
    """agent-merge accepts only claude[bot] or the repo owner."""
    gh = _stale_pass(pass_login="someone-else", head="a" * 40, passed_at="a" * 40)
    assert cq.stale_reason(gh, REPO, cq.pending(gh, REPO)[0]) is None


def test_a_PASS_comment_from_the_repo_owner_binds_the_head():
    """A top-level session records its verdict as the owner."""
    gh = _stale_pass(pass_login="owner", head="a" * 40, passed_at="a" * 40)
    assert "for its head `aaaaaaa`" in cq.stale_reason(gh, REPO, cq.pending(gh, REPO)[0])


def test_qa_pass_with_NO_pass_comment_at_all_still_starts_a_round():
    gh = FakeGh(labels={812: "qa-pass"}, heads={812: "b" * 40})
    gh.add(entry("pr", 812), on=812)
    assert cq.stale_reason(gh, REPO, cq.pending(gh, REPO)[0]) is None


def test_an_unreadable_head_starts_the_round_rather_than_dropping_it():
    """A wasted round costs minutes; a wrongly dropped entry is permanent."""
    gh = _stale_pass()
    inner = gh.__call__
    def broken(args):
        if args[0] == "api" and "/pulls/" in args[1]:
            raise RuntimeError("gh api failed")
        return inner(args)
    assert cq.stale_reason(broken, REPO, cq.pending(gh, REPO)[0]) is None


HEAD_694 = "6" * 40


def _run(status, conclusion=None, at="2026-11-18T10:00:00Z", name="PR gates"):
    return {"name": name, "status": status, "conclusion": conclusion, "created_at": at}


def _issue_431(mergeable="true", ref="issue/431-prefix-row-known-shapes", pr_labels="qa-pass,qa:in-cycle",
               pass_at=HEAD_694, gates=None):
    gh = FakeGh(labels={431: "bug,qa-pass,qa:in-cycle"}, heads={694: HEAD_694},
                open_prs={694: (ref, pr_labels, mergeable), 650: ("issue/43-other", "qa-pass", "true")},
                gates={HEAD_694: gates} if gates is not None else None)
    gh.add(entry("issue", 431))
    if pass_at:
        gh.add(f"QA: PASS — verified at `{pass_at}`", login="claude[bot]", on=694)
    return gh


def test_an_ISSUE_entry_whose_PR_passed_an_OLDER_commit_is_still_started():
    """2026-11-15, PR #1058: `qa-pass` from 274e42f, head 98f14fb with gates red.
    red_gates queued the fix and this check dropped it twice as "waiting to
    merge"; agent-merge refuses a stale pass, so nothing was waiting."""
    gh = _issue_431(pass_at="2" * 40)
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


def test_an_ISSUE_entry_whose_PR_has_no_PASS_comment_at_all_is_still_started():
    gh = _issue_431(pass_at=None)
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


def test_an_ISSUE_entry_whose_PR_has_passed_and_is_mergeable_is_dropped():
    """2026-11-03 18:52Z: `issue=431` was drained twice while PR #694 held
    `qa-pass` and was mergeable. Each cycle stood down in ~35s and the carrier
    retried it as died-on-arrival, turning agent-queue red twice."""
    gh = _issue_431()
    car = FakeCarrier([])
    cq.drain(gh, REPO, car)
    assert car.calls == []
    assert "issue #431's PR #694 carries `qa-pass` and is mergeable" in gh.comments[0]["body"]


def test_an_ISSUE_entry_whose_qa_pass_PR_is_CONFLICTING_is_still_started():
    """QA round 1 on #704: the issue's own `qa-pass` label survives a PR going
    CONFLICTING (the #608 case). The steward queues `issue=<n>` to merge main
    in, and agent-merge skips a conflicting PR by design -- nothing is waiting
    to merge. Dropping on the label alone dropped that entry permanently."""
    gh = _issue_431(mergeable="false")
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


def test_an_ISSUE_entry_with_qa_pass_but_NO_open_PR_is_still_started():
    """A `partial/` PR merged with the issue still open: the label stays, no PR
    is waiting, and the remaining work needs a cycle. #43's PR must not count
    for #431 (prefix match on the number)."""
    gh = _issue_431()
    del gh.open_prs[694]
    # #43's PR carries everything a waiting PR needs -- `qa-pass` AND a PASS bound to its head
    # -- so only the issue-NUMBER comparison can tell it from #431's (2026-11-19). Without the
    # bound PASS, the head-binding check added 2026-11-15 dropped it first and the prefix row
    # was "caught" only by the anchor tripwires.
    gh.heads[650] = "5" * 40
    gh.add(f"QA: PASS — verified at `{'5' * 40}`", login="claude[bot]", on=650)
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


def test_an_ISSUE_entry_whose_PR_mergeability_is_UNKNOWN_is_still_started():
    """GitHub answers `mergeable: null` while it computes. A stand-down costs
    ~35s; a wrong drop is permanent, so unknown starts the cycle."""
    gh = _issue_431(mergeable="null")
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


def test_an_ISSUE_entry_without_qa_pass_is_started_without_reading_PRs():
    gh = FakeGh(labels={431: "bug,qa-fail"})
    gh.add(entry("issue", 431))
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"
    assert not any("/pulls?state=open" in " ".join(c) for c in gh.calls)

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
    # Drain mode: this is the race path, where the drain's own carrier finds a
    # cycle running after the drain checked. Queue mode always queues (#1185).
    env = dict(os.environ, PATH=f"{_bin(tmp_path)}:{os.environ['PATH']}", GH_REPO="owner/repo",
               CYCLE_CARRIER="drain")
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
    # INVERTED 2026-11-17 (#1186). This asserted no cron ("~1,400 Actions minutes a
    # month"); the repo is public, cost.json records Actions as unlimited (#338),
    # and the hourly backstop is now the rule. tests/test_inbox_single_worker.py
    # pins its shape; here only that it exists and is hourly.
    assert [c["cron"].split()[1:] for c in on["schedule"]] == [["*", "*", "*", "*"]]
    # By name, not position: since 2026-11-06 a chain step follows the drain.
    run = next(s["run"] for s in doc["jobs"]["drain"]["steps"]
               if s.get("name") == "Start the oldest queued cycle")
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


# ----------------------------------------- QA round 1 on #675: four findings

def test_a_run_that_died_on_arrival_goes_BACK_in_the_queue_and_the_drain_is_red():
    """The #421 shape: the carrier accepted the ruling and the RUN failed. That
    says nothing about the ruling, so dropping it lost work behind a green run."""
    gh = FakeGh()
    gh.add(entry("pr", 649))
    car = FakeCarrier([(1, None, "agent-work run 9 concluded 'failure' within 90s "
                                 "of dispatch at pr #649 -- it did not run a cycle. See #421.")])
    assert cq.drain(gh, REPO, car) == 1, "a failed run must not read as a green drain"
    assert [e.target for e in cq.pending(gh, REPO)] == [649]


def test_no_run_appearing_is_also_transient():
    gh = FakeGh()
    gh.add(entry("pr", 649))
    car = FakeCarrier([(1, None, "dispatch at pr #649 created no new agent-work run within 60s.")])
    assert cq.drain(gh, REPO, car) == 1
    assert [e.target for e in cq.pending(gh, REPO)] == [649]


def test_an_entry_is_CLAIMED_before_the_dispatch_so_a_failed_mark_cannot_repeat_it():
    """Dispatch succeeds, then the `taken` PATCH fails. Marking only afterwards
    left the entry pending, and the next drain started the same ~50-minute cycle
    again. Claimed first, it is no longer pending whatever happens next."""
    gh = FakeGh(fail_patch_after=1)            # the claim succeeds; `taken` fails
    gh.add(entry("pr", 649))
    with pytest.raises(RuntimeError):
        cq.drain(gh, REPO, FakeCarrier([(0, "777")]))
    assert cq.pending(gh, REPO) == [], "a claimed entry must never be started twice"
    assert f"{cq.MARK}-claimed: " in gh.comments[0]["body"]


def test_a_failed_CLAIM_dispatches_nothing():
    gh = FakeGh(fail_patch_after=0)
    gh.add(entry("pr", 649))
    car = FakeCarrier([])
    with pytest.raises(RuntimeError):
        cq.drain(gh, REPO, car)
    assert car.calls == []


def test_a_round_that_already_ruled_on_the_CURRENT_head_since_queueing_drops_the_entry():
    """The steward may now queue a round for the very PR the running cycle is
    reviewing. When that cycle posts its verdict for the same head, the queued
    round is a second round on one commit."""
    sha = "a" * 40
    gh = FakeGh(heads={649: sha})
    gh.add(entry("pr", 649), on=649)
    gh.add(f"QA: FAIL — verified at `{sha}`\nfindings", login="claude[bot]", on=649)
    car = FakeCarrier([])
    cq.drain(gh, REPO, car)
    assert car.calls == []
    assert "already ruled on PR #649" in gh.comments[0]["body"]


def test_a_verdict_on_an_OLDER_head_does_not_drop_the_entry():
    """#649 itself: round 3 failed `bab8e54`, the fix moved the head, and a round
    on the new head is exactly what is wanted."""
    gh = FakeGh(heads={649: "b" * 40})
    gh.add(f"QA: FAIL — verified at `{'a' * 40}`\nold", login="claude[bot]", on=649)
    gh.add(entry("pr", 649), on=649)
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls == [("pr=649", "queue(qa-on-green)")]


def test_enqueue_that_cannot_READ_the_queue_is_exit_1():
    def broken(args):
        raise RuntimeError("api down")
    assert cq.enqueue(broken, REPO, "pr", 5, "x", on=5) == 1


def test_the_steward_is_no_longer_told_to_stand_down_because_a_cycle_runs():
    """QA round 1 on #675's blocking finding. The steward obeys steward.md
    exactly; while guard 1 said "if anything is in_progress or queued, dispatch
    nothing", it could never feed the queue -- every copy of the rule has to
    change together (CLAUDE.md: "six places one coupling lived")."""
    md = (ROOT / ".claude" / "agents" / "steward.md").read_text()
    wf = (ROOT / ".github" / "workflows" / "agent-steward.yml").read_text()
    flat = " ".join(md.split())
    assert "If anything is `in_progress` or `queued`, dispatch nothing" not in flat.split(
        "Until that date this guard said")[0], "guard 1 tells the steward to stand down again"
    assert "Is this SAME target already queued?" in flat
    assert "agent-work-queue" in md
    assert "refuses rather than queueing a second" not in wf
    assert "guard 1 forbids a second dispatch" not in wf


# ----------------------------------------- QA round 2 on #675

def _dead(gh, n):
    return FakeCarrier([(1, None, "dispatch at pr #649 created no new agent-work run within 60s.")
                        for _ in range(n)])


def test_a_dead_run_is_retried_at_most_twice_then_dropped():
    """BLOCKING N1. A dead agent-work run COMPLETES, which fires agent-queue,
    which re-dispatched the same entry -- forever (#421 lasted three days)."""
    gh = FakeGh()
    gh.add(entry("pr", 649))
    car = _dead(gh, 3)
    assert cq.drain(gh, REPO, car) == 1
    assert [e.target for e in cq.pending(gh, REPO)] == [649], "retry 1"
    assert cq.drain(gh, REPO, car) == 1
    assert [e.target for e in cq.pending(gh, REPO)] == [649], "retry 2"
    assert cq.drain(gh, REPO, car) == 1, "retries ran out: the drain must be red, not quiet"
    assert cq.pending(gh, REPO) == [], "the third failure must drop it"
    assert f"{cq.MARK}-dropped: " in gh.comments[0]["body"]
    assert len(car.calls) == 3


def test_a_carrier_that_cannot_RUN_returns_the_entry_instead_of_stranding_it():
    """N3: an OSError or a timeout left the entry `claimed`, where no drain
    would ever look at it again."""
    gh = FakeGh()
    gh.add(entry("pr", 5))

    def broken(ruling, who, **kw):
        raise subprocess.TimeoutExpired("dispatch_cycle.sh", 600)
    assert cq.drain(gh, REPO, broken) == 1
    assert [e.target for e in cq.pending(gh, REPO)] == [5]
    assert "retry 1 of" in gh.comments[0]["body"]


def test_a_failed_RE_QUEUE_inside_the_carrier_is_retried_not_dropped():
    gh = FakeGh()
    gh.add(entry("pr", 5))
    car = FakeCarrier([(1, None, "::error::queue(x)'s ruling at pr #5 could NOT be queued.")])
    assert cq.drain(gh, REPO, car) == 1
    assert [e.target for e in cq.pending(gh, REPO)] == [5]


def test_chief_is_no_longer_told_it_cannot_dispatch_over_a_running_cycle():
    wf = (ROOT / ".github" / "workflows" / "agent-steward.yml").read_text()
    assert "dispatch over a cycle already in flight" not in wf


# ----------------------------------------- the QA lane (2026-11-03)

def test_a_QA_entry_starts_while_a_BUILD_cycle_runs():
    gh = FakeGh(busy="1", busy_qa="0")
    gh.add(entry("issue", 518))
    gh.add(entry("pr", 649))
    car = FakeCarrier([(0, "11")])
    cq.drain(gh, REPO, car)
    assert car.calls == [("pr=649", "queue(qa-on-green)")]
    assert [e.target for e in cq.pending(gh, REPO)] == [518], "the build entry waits"


def test_both_lanes_free_starts_ONE_entry_in_EACH():
    gh = FakeGh()
    gh.add(entry("issue", 518))
    gh.add(entry("pr", 649))
    gh.add(entry("pr", 636))
    car = FakeCarrier([(0, "11"), (0, "12")])
    cq.drain(gh, REPO, car)
    assert [r for r, _ in car.calls] == ["issue=518", "pr=649"]
    assert [e.target for e in cq.pending(gh, REPO)] == [636], "one QA round at a time"


def test_lanes_follow_the_kind():
    assert cq.lane_of("pr") == "qa" and cq.lane_of("issue") == "build"


def test_the_queue_and_the_carrier_tell_lanes_apart_the_SAME_way():
    """Two copies of one rule: if they drift, a lane looks free to one and busy
    to the other, and a round lands in a cancellable pending slot."""
    sh = (ROOT / "scripts" / "dispatch_cycle.sh").read_text()
    assert f'startswith("{cq.QA_TITLE}")' in cq.lane_jq("qa")
    assert f'select(.displayTitle | startswith("{cq.QA_TITLE}"))' in sh
    assert f'select(.displayTitle | startswith("{cq.QA_TITLE}") | not)' in sh


def test_agent_work_names_and_groups_QA_rounds_by_the_same_rule():
    src = (ROOT / ".github" / "workflows" / "agent-work.yml").read_text()
    doc = yaml.safe_load(src)
    assert doc["run-name"] == ("${{ inputs.pr && format('QA round: PR #{0}', inputs.pr) || "
                               "inputs.fix_pr && format('Agent work: fix PR #{0}', inputs.fix_pr) || 'Agent work' }}")
    # A fix run pushes, so it must count in the BUILD lane: its title may not
    # start with the QA prefix, and the concurrency group keys on `pr` alone.
    assert not "Agent work: fix PR #1".startswith(cq.QA_TITLE)
    assert cq.lane_of("fix_pr") == "build"
    assert doc["run-name"].split("format('")[1].startswith(cq.QA_TITLE)
    assert doc["concurrency"]["group"] == "${{ inputs.pr && 'agent-work-qa' || 'agent-work' }}"
    assert doc["concurrency"]["cancel-in-progress"] is False


def test_a_fix_pr_entry_is_parsed_and_runs_in_the_build_lane():
    m = cq.ENTRY.search("<!-- agent-work-queue: kind=fix_pr target=951 by=agent-work-qa-fix -->")
    assert m and m.group(1) == "fix_pr" and m.group(2) == "951"
    assert cq.lane_of("fix_pr") == "build"


def test_an_ISSUE_entry_whose_PR_passed_QA_but_went_RED_on_the_same_head_is_still_started():
    """2026-11-17: #1121, #1127, #1136, #1138 -- QA PASS bound to the head, gates
    then red on that head, GitHub `blocked`. The red-gates fix was dropped as
    'waiting to merge' each time and the PRs sat for a day."""
    gh = _issue_431(mergeable="blocked", gates=[_run("completed", "failure")])
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


# ----------------------------------------- #1207: blocked while gates run is waiting

def _blocked_dropped(gh):
    car = FakeCarrier([])
    cq.drain(gh, REPO, car)
    assert car.calls == []
    assert "waiting to merge" in gh.comments[0]["body"]
    assert f"{cq.MARK}-dropped: " in gh.comments[0]["body"]


def _blocked_started(gh):
    car = FakeCarrier([(0, "1")])
    cq.drain(gh, REPO, car)
    assert car.calls and car.calls[0][0] == "issue=431"


def test_a_BLOCKED_PR_whose_latest_gates_run_is_still_RUNNING_is_waiting_to_merge():
    """2026-11-18, PR #1227 (#1226): `qa-pass` bound to the head, `blocked` only
    because a second `gates` run was in progress. The drain started a cycle that
    stood down in under 90s, and the carrier read that as a dead run (#1207)."""
    _blocked_dropped(_issue_431(mergeable="blocked", gates=[_run("in_progress")]))
    _blocked_dropped(_issue_431(mergeable="blocked", gates=[_run("queued")]))


def test_a_BLOCKED_PR_whose_latest_gates_run_PASSED_is_waiting_to_merge():
    _blocked_dropped(_issue_431(mergeable="blocked", gates=[_run("completed", "success")]))


def test_only_the_NEWEST_gates_run_counts():
    """An older red run is the one the push superseded; the latest decides."""
    old = _run("completed", "failure", at="2026-11-18T09:00:00Z")
    _blocked_dropped(_issue_431(mergeable="blocked", gates=[old, _run("in_progress", at="2026-11-18T10:00:00Z")]))
    _blocked_dropped(_issue_431(mergeable="blocked", gates=[_run("completed", "success", at="2026-11-18T10:00:00Z"), old]))
    # and the reverse: an older green run does not excuse a newer red one
    green = _run("completed", "success", at="2026-11-18T09:00:00Z")
    _blocked_started(_issue_431(mergeable="blocked", gates=[green, _run("completed", "failure", at="2026-11-18T10:00:00Z")]))


@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "startup_failure", "cancelled"])
def test_a_BLOCKED_PR_whose_latest_gates_run_is_RED_is_still_started(conclusion):
    _blocked_started(_issue_431(mergeable="blocked", gates=[_run("completed", conclusion)]))


def test_a_BLOCKED_PR_with_NO_gates_run_is_still_started():
    """Nothing is running, so nothing is about to unblock it."""
    _blocked_started(_issue_431(mergeable="blocked", gates=[]))


def test_a_BLOCKED_PR_whose_gates_runs_are_UNREADABLE_is_still_started():
    _blocked_started(_issue_431(mergeable="blocked", gates="error"))


def test_a_BLOCKED_PR_with_a_SKIPPED_gates_run_is_still_started():
    """Neither running nor green: the PR is blocked by something else."""
    _blocked_started(_issue_431(mergeable="blocked", gates=[_run("completed", "skipped")]))


def test_a_running_run_of_ANOTHER_workflow_is_not_the_gates_run():
    """Only `PR gates` decides; an in-progress `Agent merge` run says nothing."""
    gates = [_run("completed", "failure", at="2026-11-18T09:00:00Z"),
             _run("in_progress", at="2026-11-18T10:00:00Z", name="verify-build")]
    _blocked_started(_issue_431(mergeable="blocked", gates=gates))


def test_a_failing_run_of_ANOTHER_workflow_is_ignored():
    gates = [_run("completed", "success", at="2026-11-18T09:00:00Z"),
             _run("completed", "failure", at="2026-11-18T10:00:00Z", name="verify-build")]
    _blocked_dropped(_issue_431(mergeable="blocked", gates=gates))


def test_a_BLOCKED_PR_whose_PASS_names_an_OLDER_commit_is_still_started_whatever_gates_say():
    _blocked_started(_issue_431(mergeable="blocked", pass_at="2" * 40, gates=[_run("in_progress")]))


@pytest.mark.parametrize("state", ["false", "null", "behind", "unstable"])
def test_only_BLOCKED_reads_the_gates_run(state):
    """dirty/unknown/behind/unstable have their own cause, a cycle is the step,
    and a green or running gates run does not make them wait."""
    gh = _issue_431(mergeable=state, gates=[_run("in_progress")])
    _blocked_started(gh)
    assert not any("/actions/runs" in " ".join(c) for c in gh.calls)


def test_a_CLEAN_PR_does_not_read_the_gates_run():
    gh = _issue_431(mergeable="true", gates=[_run("completed", "failure")])
    _blocked_dropped(gh)
    assert not any("/actions/runs" in " ".join(c) for c in gh.calls)


def test_gates_red_never_interpolates_a_sha_that_is_not_40_hex():
    gh = FakeGh()
    assert cq._gates_red(gh, REPO, "abc; rm -rf /") is None
    assert cq._gates_red(gh, REPO, "") is None
    assert gh.calls == []


def test_GATES_WORKFLOW_is_the_name_pr_gates_declares():
    """A rename would make every PR read as 'no gates run' and quietly restore
    the drain-into-a-stand-down loop, so the string is pinned to the file."""
    assert cq.GATES_WORKFLOW == _wf("pr-gates.yml")["name"]


# ----------------------------------------- #1207: a green run that wrote nothing

def test_a_run_that_SUCCEEDED_and_left_no_trace_is_dropped_not_retried():
    """2026-11-17, #1163: three cycles on one target, each standing down in under
    90s. A retry is the same cycle on the same state; it repeats itself."""
    gh = FakeGh()
    gh.add(entry("pr", 649))
    car = FakeCarrier([(1, None, "agent-work run 9 concluded 'success' within 90s of dispatch "
                                 "at pr #649 -- it did not run a cycle. See #421.")])
    assert cq.drain(gh, REPO, car) == 1, "red once, so the stand-down is seen"
    assert len(car.calls) == 1
    assert cq.pending(gh, REPO) == []
    assert f"{cq.MARK}-dropped: " in gh.comments[0]["body"]
    assert "repeats itself" in gh.comments[0]["body"]


def test_a_run_that_FAILED_still_keeps_its_retries():
    """Control for the test above: a dead run says nothing about the ruling."""
    gh = FakeGh()
    gh.add(entry("pr", 649))
    car = FakeCarrier([(1, None, "agent-work run 9 concluded 'failure' within 90s of dispatch "
                                 "at pr #649 -- it did not run a cycle. See #421.")])
    assert cq.drain(gh, REPO, car) == 1
    assert [e.target for e in cq.pending(gh, REPO)] == [649]
