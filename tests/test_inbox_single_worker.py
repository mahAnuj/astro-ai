"""#1185 / #1186: every trigger appends to the inbox first; agent-queue's drain
is the only worker; pending entries for one target fold into one run; an
hourly backstop drains whatever a cancelled wake left behind.

The defect, measured 2026-11-17: qa-on-green runs 44059296498 and 44059273106
were cancelled by GitHub (one pending run per concurrency group) and #1165,
then #1171, got no QA round -- the event lived inside the cancelled run,
because the carrier queued only when a lane was busy. Every test here drives
the real code: cycle_queue.py through an in-memory `gh`, dispatch_cycle.sh
through a fake `gh` on PATH, and the workflows as parsed YAML.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cycle_queue", ROOT / "scripts" / "cycle_queue.py")
cq = importlib.util.module_from_spec(_spec)
sys.modules["cycle_queue"] = cq
_spec.loader.exec_module(cq)

REPO = "owner/repo"
H1, H2 = "1" * 40, "2" * 40
T0 = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


class Gh:
    """The calls cycle_queue.py makes, answered from memory. Comments carry
    `issue_url` and `updated_at` like the real API, so entries know where they
    were written and when a claim was made."""

    def __init__(self, *, busy="0", busy_qa="0", runs=(), measure_runs=(), jobs=None):
        self.comments: list[dict] = []
        self.busy, self.busy_qa = busy, busy_qa
        self.runs = list(runs)                  # agent-work runs for claim recovery
        self.measure_runs = list(measure_runs)  # agent-measure workflow_runs
        self.jobs = jobs or {}                  # run id -> [jobs]
        self.clock = T0
        self._id = 500
        self.calls: list[list[str]] = []

    def add(self, body, *, login=cq.WRITER, on=1, at=None):
        self._id += 1
        when = _iso(at or (T0 + timedelta(minutes=self._id - 500)))
        self.comments.append({"id": self._id, "body": body, "login": login, "on": on,
                              "created_at": when, "updated_at": when})
        return self._id

    def by_id(self, cid):
        return next(c for c in self.comments if c["id"] == cid)

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["api", "--paginate"] and "/issues/comments?" in args[2]:
            return "\n".join(json.dumps({
                "id": c["id"], "body": c["body"], "created_at": c["created_at"],
                "updated_at": c["updated_at"], "login": c["login"],
                "issue_url": f"https://api.github.com/repos/{REPO}/issues/{c['on']}"})
                for c in self.comments)
        if args[:2] == ["api", "--paginate"]:     # one item's QA verdict lines: none here
            return ""
        if args[:3] == ["api", "-X", "POST"]:
            on = int(args[3].split("/issues/")[1].split("/")[0])
            self.add(args[5][len("body="):], on=on, at=self.clock)
            return "{}"
        if args[:3] == ["api", "-X", "PATCH"]:
            c = self.by_id(int(args[3].rsplit("/", 1)[1]))
            c["body"] = args[5][len("body="):]
            c["updated_at"] = _iso(self.clock)
            return "{}"
        if args[:2] == ["run", "list"]:
            if "--json" in args and "databaseId,createdAt,displayTitle" in args:
                return json.dumps(self.runs)
            lane = self.busy if "| not" in args[-1] else self.busy_qa
            if lane == "error":
                raise RuntimeError("gh run list failed")
            return lane + "\n"
        if args[0] == "api" and "agent-measure.yml/runs" in args[1]:
            return json.dumps({"workflow_runs": self.measure_runs})
        if args[0] == "api" and args[1].endswith("/jobs"):
            return json.dumps({"jobs": self.jobs.get(args[1].split("/runs/")[1].split("/")[0], [])})
        if args[0] == "api" and "/pulls/" in args[1]:
            return "\n"
        if args[0] == "api" and "/issues/" in args[1]:
            return "\n"                          # labels: none
        raise AssertionError(f"unexpected gh call: {args}")


class Carrier:
    def __init__(self, *results):
        self.results = list(results)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, ruling, who, entry=None):
        self.calls.append((ruling, who))
        rc, run = self.results.pop(0)
        return rc, ({"DISPATCHED_RUN": run} if run else {}), f"carrier rc={rc}"


def entry(kind, target, *, by="qa-on-green", head="", key="", state=""):
    fields = f"kind={kind} target={target} by={by}" + (f" head={head}" if head else "") \
        + (f" key={key}" if key else "")
    mark = f"{cq.MARK}-{state}" if state else cq.MARK
    return f"<!-- {mark}: {fields} -->\nQueued."


def states(gh):
    return [cq.ANY_ENTRY.search(c["body"]).group(1) or "pending"
            for c in gh.comments if cq.ANY_ENTRY.search(c["body"])]


# ------------------------------------------------- same key appended twice

def test_the_same_key_appended_twice_is_ONE_entry_and_one_dispatch():
    gh = Gh()
    assert cq.enqueue(gh, REPO, "pr", 649, "qa-on-green", 649, head=H1) == 0
    assert cq.enqueue(gh, REPO, "pr", 649, "steward", 649, head=H1) == 0
    assert len(gh.comments) == 1
    car = Carrier((0, "77"))
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert car.calls == [("pr=649", "queue(qa-on-green)")]


def test_two_handlers_racing_past_the_dedupe_still_give_one_run():
    """Both read the queue before either wrote: two identical entries. The
    fold takes the second into the first's run."""
    gh = Gh()
    gh.add(entry("pr", 649, head=H1), on=649)
    gh.add(entry("pr", 649, by="steward", head=H1), on=649)
    car = Carrier((0, "77"))
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert len(car.calls) == 1
    assert states(gh) == ["taken", "folded"]
    assert "folded into run `77`" in gh.comments[1]["body"]


def test_a_new_head_is_a_new_event_but_still_one_run_per_target():
    gh = Gh()
    cq.enqueue(gh, REPO, "pr", 649, "qa-on-green", 649, head=H1)
    cq.enqueue(gh, REPO, "pr", 649, "qa-on-green", 649, head=H2)
    assert len(gh.comments) == 2, "a new head is new information"
    car = Carrier((0, "77"))
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert len(car.calls) == 1 and states(gh) == ["taken", "folded"]


def test_a_timer_key_is_one_event_even_after_it_ran():
    """A double fire after the first entry was taken must add nothing."""
    gh = Gh()
    key = "timer.score-1150.20261218T0000Z"
    cq.enqueue(gh, REPO, "measure", 1150, "timer", 1150, key=key)
    gh.comments[0]["body"] = gh.comments[0]["body"].replace(f"{cq.MARK}: ", f"{cq.MARK}-taken: ")
    assert cq.enqueue(gh, REPO, "measure", 1150, "timer", 1150, key=key) == 0
    assert len(gh.comments) == 1


def test_a_head_and_a_key_round_trip_through_the_marker():
    gh = Gh()
    cq.enqueue(gh, REPO, "fix_pr", 951, "red-gates", 951, head=H1, key="k.1")
    [e] = cq.pending(gh, REPO)
    assert (e.kind, e.target, e.head, e.key, e.on) == ("fix_pr", 951, H1, "k.1", 951)


def test_an_old_marker_without_head_or_key_still_parses():
    gh = Gh()
    gh.add(f"<!-- {cq.MARK}: kind=issue target=5 by=steward -->", on=5)
    [e] = cq.pending(gh, REPO)
    assert (e.kind, e.target, e.head, e.key) == ("issue", 5, "", "")


# --------------------------------------------------------------- fold

def test_FOLD_three_entries_for_one_PR_give_ONE_dispatch_and_the_fix_wins():
    """A QA request, an `issue=` cycle qa-on-green queued ON the PR, and a
    red-gates fix: one target. The fix outranks the round (its push earns its
    own round), so a build-lane run starts and both others are folded."""
    gh = Gh()
    gh.add(entry("pr", 700, head=H1), on=700)                       # oldest
    gh.add(entry("issue", 55, head=H1), on=700)                     # written on PR 700
    gh.add(entry("fix_pr", 700, by="red-gates", head=H1), on=700)
    car = Carrier((0, "88"))
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert len(car.calls) == 1, car.calls
    assert car.calls[0][0] in ("issue=55", "fix_pr=700"), "the QA request must not win"
    assert states(gh).count("taken") == 1 and states(gh).count("folded") == 2
    for c in gh.comments:
        if "-folded:" in c["body"]:
            assert "folded into run `88`" in c["body"]


def test_a_target_whose_fix_lane_is_busy_waits_whole():
    """The QA lane is free, but the round is folded into a fix that cannot
    start yet: starting the round beside it would judge the pre-fix head."""
    gh = Gh(busy="1", busy_qa="0")
    gh.add(entry("pr", 700, head=H1), on=700)
    gh.add(entry("fix_pr", 700, head=H1), on=700)
    car = Carrier()
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert car.calls == [] and states(gh) == ["pending", "pending"]


def test_different_targets_are_not_folded():
    gh = Gh()
    gh.add(entry("pr", 700), on=700)
    gh.add(entry("pr", 701), on=701)
    car = Carrier((0, "1"))
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert states(gh) == ["taken", "pending"]


def test_an_issue_entry_on_its_own_issue_is_not_folded_into_a_PR_by_guessing():
    gh = Gh(busy_qa="1")
    gh.add(entry("issue", 55, by="steward"), on=55)
    gh.add(entry("fix_pr", 700), on=700)
    car = Carrier((0, "1"), (0, "2"))
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    assert car.calls[0][0] == "issue=55" and states(gh)[1] == "pending", (
        "one build lane: the second target waits, it is not folded")


def test_a_dropped_best_entry_hands_the_target_to_the_next():
    """fix_pr dropped as stale (PR passed at its head) -> the QA entry is next."""
    gh = Gh()
    gh.add(entry("pr", 700), on=700)
    gh.add(entry("fix_pr", 700), on=700)
    orig = cq.stale_reason
    try:
        cq.stale_reason = lambda g, r, e: "nothing to fix" if e.kind == "fix_pr" else None
        car = Carrier((0, "5"))
        cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=30))
    finally:
        cq.stale_reason = orig
    assert car.calls == [("pr=700", "queue(qa-on-green)")]
    assert states(gh) == ["taken", "dropped"]


# --------------------------------------------- a cancelled drain is harmless

def test_after_a_CANCELLED_drain_the_next_drain_still_processes_the_entry():
    """GitHub cancels the drain after its claim and before its dispatch. The
    entry is `claimed`, which no drain used to look at again. Past CLAIM_TTL
    with no matching run, the next drain returns it and starts it."""
    gh = Gh()
    gh.add(entry("pr", 649, head=H1), on=649)

    def cancelled(ruling, who, entry=None):
        raise KeyboardInterrupt("the runner received a shutdown signal")
    with pytest.raises(KeyboardInterrupt):
        cq.drain(gh, REPO, cancelled, now=T0 + timedelta(minutes=5))
    assert states(gh) == ["claimed"]
    gh.clock = T0 + timedelta(minutes=40)
    car = Carrier((0, "99"))
    assert cq.drain(gh, REPO, car, now=gh.clock) == 0
    assert car.calls == [("pr=649", "queue(qa-on-green)")]
    assert states(gh) == ["taken"]


def test_a_dead_drain_that_HAD_dispatched_is_recovered_as_taken_not_run_twice():
    gh = Gh()
    gh.add(entry("pr", 649), on=649)
    gh.clock = T0 + timedelta(minutes=5)
    claimed_at = gh.clock

    def dies_after_dispatch(ruling, who, entry=None):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        cq.drain(gh, REPO, dies_after_dispatch, now=gh.clock)
    gh.runs = [{"databaseId": 4242, "createdAt": _iso(claimed_at + timedelta(seconds=20)),
                "displayTitle": "QA round: PR #649"}]
    gh.clock = T0 + timedelta(minutes=40)
    car = Carrier()
    cq.drain(gh, REPO, car, now=gh.clock)
    assert car.calls == [], "the run already exists; a second would double the cycle"
    assert states(gh) == ["taken"] and "4242" in gh.comments[0]["body"]


def test_a_FRESH_claim_is_left_alone():
    """A claim younger than CLAIM_TTL may belong to a drain still running."""
    gh = Gh()
    gh.add(entry("pr", 649, state="claimed"), on=649, at=T0)
    car = Carrier()
    cq.drain(gh, REPO, car, now=T0 + timedelta(minutes=5))
    assert car.calls == [] and states(gh) == ["claimed"]


def test_unreadable_runs_leave_a_stale_claim_for_the_next_drain():
    gh = Gh()
    gh.add(entry("pr", 649, state="claimed"), on=649, at=T0)
    inner = gh.__call__

    def broken(args):
        if args[:2] == ["run", "list"] and "databaseId,createdAt,displayTitle" in args:
            raise RuntimeError("api down")
        return inner(args)
    car = Carrier()
    cq.drain(broken, REPO, car, now=T0 + timedelta(hours=1))
    assert car.calls == [] and states(gh) == ["claimed"]


def test_the_claim_ttl_outlives_the_drain_job_timeout():
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-queue.yml").read_text())
    assert cq.CLAIM_TTL > timedelta(minutes=doc["jobs"]["drain"]["timeout-minutes"])


# ------------------------------------------------------- measure entries

def _measure_gh(runs=(), jobs=None):
    gh = Gh(measure_runs=list(runs), jobs=jobs or {})
    return gh


DUE = datetime(2026, 12, 18, tzinfo=timezone.utc)
MKEY = "timer.score-1150.20261218T0000Z"


def test_a_measure_entry_covered_by_the_daily_analyst_run_costs_no_dispatch():
    gh = _measure_gh(runs=[{"id": 31, "status": "completed", "event": "schedule",
                            "created_at": "2026-12-18T00:20:00Z",
                            "run_started_at": "2026-12-18T00:21:00Z"}],
                     jobs={"31": [{"name": "measure", "conclusion": "success"}]})
    gh.add(entry("measure", 1150, by="timer", key=MKEY), on=1150)
    started = []
    cq.drain(gh, REPO, Carrier(), now=DUE + timedelta(hours=5), starter=lambda g, r: started.append(1))
    assert started == [] and states(gh) == ["taken"]
    assert "covered by analyst run `31`" in gh.comments[0]["body"]


def test_a_collectors_only_run_does_not_cover_a_score():
    gh = _measure_gh(runs=[{"id": 32, "status": "completed", "event": "schedule",
                            "created_at": "2026-12-18T09:30:00Z"}],
                     jobs={"32": [{"name": "measure", "conclusion": "skipped"}]})
    gh.add(entry("measure", 1150, by="timer", key=MKEY), on=1150)
    gh.add(entry("measure", 1151, by="timer", key="timer.score-1151.20261218T0000Z"), on=1151)
    started = []
    cq.drain(gh, REPO, Carrier(), now=DUE + timedelta(hours=10),
             starter=lambda g, r: started.append(1) or "555")
    assert started == [1], "two ripe scores, ONE analyst run"
    assert states(gh) == ["taken", "folded"]


def test_a_measure_entry_waits_out_the_grace_for_the_daily_slot():
    gh = _measure_gh()
    gh.add(entry("measure", 1150, by="timer", key=MKEY), on=1150)
    started = []
    cq.drain(gh, REPO, Carrier(), now=DUE + timedelta(hours=1), starter=lambda g, r: started.append(1))
    assert started == [] and states(gh) == ["pending"]


def test_a_measure_dispatch_that_never_appears_goes_back_and_the_drain_is_red():
    gh = _measure_gh()
    gh.add(entry("measure", 1150, by="timer", key=MKEY), on=1150)
    rc = cq.drain(gh, REPO, Carrier(), now=DUE + timedelta(hours=6), starter=lambda g, r: None)
    assert rc == 1 and states(gh) == ["pending"]


# ------------------------------------------- the carrier only appends now

def _fake_gh(tmp_path: Path, *, state="OPEN", head=H1, wake_ok=True) -> Path:
    """A Python `gh` on PATH that keeps comments in a JSON file, so the
    carrier's enqueue sees what an earlier run wrote."""
    store = tmp_path / "comments.json"
    store.write_text("[]")
    b = tmp_path / "bin"
    b.mkdir(exist_ok=True)
    (b / "gh").write_text(f"""#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
line = " ".join(args)
open({str(tmp_path / 'gh.log')!r}, "a").write(line + "\\n")
store = {str(store)!r}
cs = json.load(open(store))
if "issue view" in line and "--json url" in line:
    print("https://github.com/owner/repo/issues/1")
elif "pr view" in line and "headRefOid" in line:
    print({head!r})
elif "pr view" in line or "issue view" in line:
    print({state!r})
elif args[:2] == ["api", "--paginate"]:
    for i, c in enumerate(cs):
        print(json.dumps({{"id": i + 1, "body": c["body"], "created_at": "2026-11-17T10:00:00Z",
                          "updated_at": "2026-11-17T10:00:00Z", "login": "github-actions[bot]",
                          "issue_url": "https://api.github.com/repos/owner/repo/issues/" + c["on"]}}))
elif args[:3] == ["api", "-X", "POST"]:
    cs.append({{"on": args[3].split("/issues/")[1].split("/")[0], "body": args[5][5:]}})
    json.dump(cs, open(store, "w"))
    print("{{}}")
elif "workflow run agent-queue.yml" in line:
    sys.exit(0 if {wake_ok!r} else 1)
else:
    print("UNEXPECTED gh " + line, file=sys.stderr)
    sys.exit(9)
""")
    (b / "gh").chmod(0o755)
    return b


def _carry(tmp_path, ruling, who="qa-on-green", genv=None, **env_extra):
    f = tmp_path / "ruling.txt"
    f.write_text(ruling + "\n")
    env = dict(os.environ, PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}", GH_REPO=REPO)
    for k in ("GITHUB_ENV", "CYCLE_CARRIER", "QUEUE_HEAD", "QUEUE_ON", "QUEUE_KEY"):
        env.pop(k, None)
    if genv:
        env["GITHUB_ENV"] = str(genv)
    env.update(env_extra)
    return subprocess.run(["bash", str(ROOT / "scripts" / "dispatch_cycle.sh"), str(f), who],
                          capture_output=True, text=True, env=env, timeout=120)


def test_a_handler_QUEUES_and_wakes_and_never_starts_a_cycle_even_when_idle(tmp_path):
    """The idle path used to dispatch straight from the handler's own run."""
    _fake_gh(tmp_path)
    genv = tmp_path / "env"
    genv.write_text("")
    r = _carry(tmp_path, "pr=649", genv=genv)
    assert r.returncode == 0, r.stdout + r.stderr
    log = (tmp_path / "gh.log").read_text()
    assert "workflow run agent-work" not in log
    assert "run list" not in log, "queue mode does not even look at the lanes"
    assert "workflow run agent-queue.yml" in log
    [c] = json.loads((tmp_path / "comments.json").read_text())
    assert f"kind=pr target=649 by=qa-on-green head={H1}" in c["body"]
    assert "QUEUED=649" in genv.read_text() and "DISPATCHED" not in genv.read_text()


def test_a_handler_appending_the_same_head_twice_writes_once(tmp_path):
    _fake_gh(tmp_path)
    _carry(tmp_path, "pr=649")
    r = _carry(tmp_path, "pr=649", who="steward")
    assert r.returncode == 0 and "already queued" in r.stdout
    assert len(json.loads((tmp_path / "comments.json").read_text())) == 1


def test_qa_on_green_issue_ruling_is_keyed_on_the_head_it_was_given(tmp_path):
    _fake_gh(tmp_path, head="f" * 40)
    _carry(tmp_path, "issue=616", QUEUE_ON="642", QUEUE_HEAD=H2)
    [c] = json.loads((tmp_path / "comments.json").read_text())
    assert c["on"] == "642" and f"head={H2}" in c["body"]


def test_a_failed_wake_is_a_warning_not_a_lost_event(tmp_path):
    _fake_gh(tmp_path, wake_ok=False)
    r = _carry(tmp_path, "fix_pr=951")
    assert r.returncode == 0, r.stdout
    assert "hourly" in r.stdout or "backstop" in r.stdout
    assert len(json.loads((tmp_path / "comments.json").read_text())) == 1


def test_a_closed_target_is_still_refused_before_queueing(tmp_path):
    _fake_gh(tmp_path, state="CLOSED")
    r = _carry(tmp_path, "pr=640")
    assert r.returncode == 1 and json.loads((tmp_path / "comments.json").read_text()) == []


def test_a_malformed_head_is_not_used_as_a_key(tmp_path):
    _fake_gh(tmp_path)
    _carry(tmp_path, "pr=649", QUEUE_HEAD="not-a-sha; rm -rf /")
    [c] = json.loads((tmp_path / "comments.json").read_text())
    assert "head=not" not in c["body"]


# ---------------------------------------------- nothing else starts a cycle

_DISPATCH = re.compile(r"gh workflow run agent-work|\"workflow\",\s*\"run\",\s*\"agent-work\.yml\""
                       r"|agent-work\.yml/dispatches")
#: The worker and the files that only hold mutation anchors or a lint's own
#: examples. Everything else must not contain a dispatch outside a comment.
_ALLOWED = {"scripts/dispatch_cycle.sh", "scripts/chain_cycle.py"}
_ANCHOR_FILES = {"scripts/mutate_behaviour_suite.py", "scripts/mutate_verify_workflows.py",
                 "scripts/verify_workflows.py"}


def _code_lines(path: Path):
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.lstrip().startswith("#"):
            yield i, line


def test_NO_agent_work_dispatch_anywhere_except_the_drain():
    found = []
    for p in list((ROOT / "scripts").rglob("*")) + list((ROOT / ".github" / "workflows").glob("*.yml")):
        rel = p.relative_to(ROOT).as_posix()
        if not p.is_file() or p.suffix not in (".py", ".sh", ".yml") or rel in _ALLOWED \
                or rel in _ANCHOR_FILES or rel.startswith("scripts/mutations/"):
            continue
        found += [f"{rel}:{i}" for i, line in _code_lines(p) if _DISPATCH.search(line)]
    assert found == [], f"a path other than agent-queue's drain starts agent-work: {found}"


def test_the_carriers_dispatch_is_reachable_only_in_drain_mode():
    src = (ROOT / "scripts" / "dispatch_cycle.sh").read_text()
    gate = src.index('if [ "${CYCLE_CARRIER:-}" != "drain" ]; then')
    block_end = src.index("\n  exit 0\nfi\n", gate)
    dispatch = src.index('gh workflow run agent-work.yml --repo "$GH_REPO" -f "$kind=$target"')
    assert dispatch > block_end, "the dispatch must sit after the queue-mode block's exit"


def test_only_the_drain_sets_drain_mode():
    setters = []
    for p in list((ROOT / "scripts").glob("*")) + list((ROOT / ".github" / "workflows").glob("*.yml")):
        if p.is_file() and p.suffix in (".py", ".sh", ".yml") and p.name != "mutate_behaviour_suite.py":
            for i, line in _code_lines(p):
                # An assignment in any of its shapes; prose naming it (in
                # backticks) is not one.
                if re.search(r'CYCLE_CARRIER="drain"|CYCLE_CARRIER:\s*"?drain|export CYCLE_CARRIER'
                             r'|^\s*CYCLE_CARRIER=drain', line):
                    setters.append(f"{p.relative_to(ROOT).as_posix()}:{i}")
    assert setters == ["scripts/cycle_queue.py:" + str(next(
        i for i, l in _code_lines(ROOT / "scripts" / "cycle_queue.py") if 'CYCLE_CARRIER="drain"' in l))]


def test_the_drain_and_the_chain_run_only_in_agent_queue():
    users = {}
    for p in (ROOT / ".github" / "workflows").glob("*.yml"):
        doc = yaml.safe_load(p.read_text())
        for job in (doc.get("jobs") or {}).values():
            for s in job.get("steps") or []:
                run = s.get("run") or ""
                for tool in ("cycle_queue.py drain", "chain_cycle.py"):
                    if tool in run:
                        users.setdefault(tool, set()).add(p.name)
    assert users == {"cycle_queue.py drain": {"agent-queue.yml"}, "chain_cycle.py": {"agent-queue.yml"}}


@pytest.mark.parametrize("wf,step", [
    ("qa-on-green.yml", "Carry out the dispatch"),
    ("qa-on-green.yml", "Dispatch the fix cycle"),
    ("agent-steward.yml", "Carry out the steward's dispatch"),
    ("agent-steward.yml", "Carry out chief's dispatch ruling"),
    ("agent-work.yml", "Dispatch a fix when this QA round failed"),
])
def test_every_handler_goes_through_the_carrier_in_queue_mode(wf, step):
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / wf).read_text())
    s = next(s for j in doc["jobs"].values() for s in j.get("steps") or [] if s.get("name") == step)
    assert "dispatch_cycle.sh" in s["run"]
    assert "CYCLE_CARRIER" not in json.dumps(s), f"{wf}: {step} must not set drain mode"


def test_qa_on_green_keys_both_paths_on_the_head():
    steps = yaml.safe_load((ROOT / ".github/workflows/qa-on-green.yml").read_text())["jobs"]["consider"]["steps"]
    by = {s.get("name"): s for s in steps}
    assert by["Carry out the dispatch"]["env"]["QUEUE_HEAD"] == "${{ steps.pick.outputs.head }}"
    assert by["Dispatch the fix cycle"]["env"]["QUEUE_HEAD"] == "${{ github.event.workflow_run.head_sha }}"


def test_the_steward_counts_a_QUEUED_ruling_as_acting():
    """The carrier no longer starts the run, so `acted` would see cycles=0 on
    every steward dispatch and wake chief for nothing."""
    steps = yaml.safe_load((ROOT / ".github/workflows/agent-steward.yml").read_text())["jobs"]["steward"]["steps"]
    acted = next(s for s in steps if s.get("id") == "acted")["run"]
    assert '[ -n "${QUEUED:-}" ] && queued=1' in acted
    assert '[ "$queued" -gt 0 ]' in acted


# ------------------------------------------------------ the hourly backstop

def _queue_doc():
    return yaml.safe_load((ROOT / ".github/workflows/agent-queue.yml").read_text())


def test_the_hourly_backstop_cron_exists_and_runs_timers_drain_chain_liveness_in_order():
    doc = _queue_doc()
    on = doc.get("on") or doc.get(True)
    assert on["schedule"] == [{"cron": "17 * * * *"}]
    steps = doc["jobs"]["drain"]["steps"]
    names = [s.get("name") for s in steps]
    order = ["Fire due timers into the queue", "Start the oldest queued cycle",
             "Chain the next ranked cycle", "Liveness check, filed as ops findings"]
    assert [n for n in names if n in order] == order
    by = {s.get("name"): s for s in steps}
    assert "timers.py fire" in by[order[0]]["run"] and by[order[0]]["if"] == "github.event_name == 'schedule'"
    assert "github.event_name == 'schedule'" in by[order[2]]["if"]
    live = by[order[3]]
    assert "github.event_name == 'schedule'" in live["if"]
    assert "--scope liveness" in live["run"] and "liveness.py" in live["run"]
    assert by[order[1]]["if"] == "always()", "a failed timer step must not skip the drain"


def test_the_backstop_needs_no_new_permission():
    assert _queue_doc()["permissions"] == {"contents": "read", "actions": "write",
                                           "issues": "write", "pull-requests": "write"}


def test_the_no_cron_comment_is_gone_and_the_cost_is_stated():
    src = (ROOT / ".github/workflows/agent-queue.yml").read_text()
    assert "A `*/30` cron here would be ~1,400 Actions minutes a month" not in src
    assert "744 runs a month" in src and "#338" in src
