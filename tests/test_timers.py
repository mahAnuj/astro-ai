"""#1187: timers -- agent-set follow-ups and schedules, fired into the inbox.

Until this, the analyst wrote "pending — scoreable from <date>" as prose and
nothing ever fired it. These drive scripts/timers.py end to end against an
in-memory `gh` that also holds the queue, so `fire` -> `cycle_queue.enqueue`
-> the entry is one real path.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("timers", ROOT / "scripts" / "timers.py")
tm = importlib.util.module_from_spec(_spec)
sys.modules["timers"] = tm
_spec.loader.exec_module(tm)
cq = tm.cycle_queue

REPO = "owner/repo"
NOW = datetime(2026, 12, 18, 3, 17, tzinfo=timezone.utc)


class Gh:
    """Search, the repo comment feed, one item's comments, POST and PATCH."""

    def __init__(self, *, search_fails=False, patch_fails=0):
        self.comments: list[dict] = []
        self.search_fails = search_fails
        self.patch_fails = patch_fails
        self._id = 900

    def add(self, body, *, on, login=tm.WRITER):
        self._id += 1
        self.comments.append({"id": self._id, "body": body, "on": on, "login": login,
                              "created_at": "2026-11-17T10:00:00Z"})
        return self._id

    def entries(self):
        return [c for c in self.comments if cq.ANY_ENTRY.search(c["body"])]

    def __call__(self, args):
        if args[:4] == ["api", "-X", "GET", "search/issues"]:
            if self.search_fails:
                raise RuntimeError("search 403")
            want_pr = "is:pull-request" in args[5]
            # The index sees hidden markers in comments, from any author.
            nums = sorted({c["on"] for c in self.comments if "agent-timer" in c["body"]
                           and (c["on"] >= 1000) == want_pr})
            return "\n".join(map(str, nums))
        if args[:2] == ["api", "--paginate"] and "/issues/comments?" in args[2]:
            if "contains" in args[-1]:          # timers.candidates' recent feed
                return "\n".join(f"https://api.github.com/repos/{REPO}/issues/{c['on']}"
                                 for c in self.comments
                                 if c["login"] == tm.WRITER and "<!-- agent-timer" in c["body"])
            return "\n".join(json.dumps({     # cycle_queue.entries
                "id": c["id"], "body": c["body"], "created_at": c["created_at"],
                "updated_at": c["created_at"], "login": c["login"],
                "issue_url": f"https://api.github.com/repos/{REPO}/issues/{c['on']}"})
                for c in self.comments)
        if args[:2] == ["api", "--paginate"]:   # one item's comments
            n = int(args[2].split("/issues/")[1].split("/")[0])
            return "\n".join(json.dumps({"id": c["id"], "body": c["body"], "login": c["login"]})
                             for c in self.comments if c["on"] == n)
        if args[:3] == ["api", "-X", "POST"]:
            self.add(args[5][len("body="):], on=int(args[3].split("/issues/")[1].split("/")[0]))
            return "{}"
        if args[:3] == ["api", "-X", "PATCH"]:
            if self.patch_fails:
                self.patch_fails -= 1
                raise RuntimeError("PATCH 502")
            cid = int(args[3].rsplit("/", 1)[1])
            next(c for c in self.comments if c["id"] == cid)["body"] = args[5][len("body="):]
            return "{}"
        raise AssertionError(f"unexpected gh call: {args}")


def _timer(gh, *, key="score-1150", due="2026-12-18T00:00:00Z", kind="followup", every="-",
           target=1150, action="measure:1150", login=tm.WRITER):
    ak, at = action.split(":")
    body = tm.marker(key, tm.parse_due(due), kind, every, "issue", target, ak, int(at)) + "\nTimer."
    return gh.add(body, on=target, login=login)


# ------------------------------------------------------------------ fire

def test_a_due_timer_gives_ONE_entry_and_a_double_fire_still_gives_one():
    gh = Gh()
    _timer(gh)
    assert tm.fire(gh, REPO, NOW) == 0
    assert tm.fire(gh, REPO, NOW + timedelta(hours=1)) == 0
    [e] = gh.entries()
    assert "kind=measure target=1150 by=timer" in e["body"]
    assert "key=timer.score-1150.20261218T0000Z" in e["body"]


def test_a_double_fire_after_a_FAILED_mark_is_still_one_entry():
    """The entry was written, the done-edit failed: the next fire re-appends
    the same key, which the queue drops, and then marks the timer done."""
    gh = Gh(patch_fails=1)
    cid = _timer(gh)
    assert tm.fire(gh, REPO, NOW) == 1, "a failed mark is red"
    assert tm.fire(gh, REPO, NOW + timedelta(hours=1)) == 0
    assert len(gh.entries()) == 1
    assert "<!-- agent-timer-done:" in next(c for c in gh.comments if c["id"] == cid)["body"]


def test_a_followup_completes():
    gh = Gh()
    cid = _timer(gh)
    tm.fire(gh, REPO, NOW)
    body = next(c for c in gh.comments if c["id"] == cid)["body"]
    assert body.startswith("<!-- agent-timer-done: key=score-1150 ")
    [t] = tm.timers_on(gh, REPO, 1150)
    assert t.done


def test_a_timer_not_yet_due_does_nothing():
    gh = Gh()
    _timer(gh, due="2026-12-19T00:00:00Z")
    tm.fire(gh, REPO, NOW)
    assert gh.entries() == []


def test_a_schedule_ADVANCES_past_now_and_fires_once_not_a_burst():
    gh = Gh()
    cid = _timer(gh, key="gochar-14d", kind="schedule", every="24h",
                 due="2026-12-15T02:00:00Z", action="issue:1150")
    tm.fire(gh, REPO, NOW)
    assert len(gh.entries()) == 1, "three missed occurrences are one firing, not three"
    [t] = tm.timers_on(gh, REPO, 1150)
    assert not t.done and t.due == datetime(2026, 12, 19, 2, 0, tzinfo=timezone.utc)
    assert t.due > NOW
    tm.fire(gh, REPO, NOW + timedelta(hours=1))
    assert len(gh.entries()) == 1, "not due again until the next occurrence"
    tm.fire(gh, REPO, datetime(2026, 12, 19, 2, 17, tzinfo=timezone.utc))
    assert len(gh.entries()) == 2, "the next occurrence is a new key, so a new entry"
    assert "20261219T0200Z" in gh.entries()[1]["body"]
    assert next(c for c in gh.comments if c["id"] == cid)["body"].count("Last fired") == 1, (
        "the body is regenerated, never appended to")


def test_an_UNTRUSTED_authors_marker_is_ignored():
    """An agent's own `gh` is claude[bot]; a stranger can paste anything."""
    gh = Gh()
    _timer(gh, login="claude[bot]")
    _timer(gh, key="evil", login="drive-by", action="issue:1")
    assert tm.fire(gh, REPO, NOW) == 0
    assert gh.entries() == []


def test_a_failed_search_is_red_but_recent_timers_still_fire():
    gh = Gh(search_fails=True)
    _timer(gh)
    assert tm.fire(gh, REPO, NOW) == 1
    assert len(gh.entries()) == 1, "the recent-comments feed still found it"


def test_a_failed_enqueue_leaves_the_timer_due():
    gh = Gh()
    cid = _timer(gh)
    assert tm.fire(gh, REPO, NOW, enqueue=lambda *a, **k: 1) == 1
    assert "<!-- agent-timer: " in next(c for c in gh.comments if c["id"] == cid)["body"]


# ------------------------------------------------------------------- set

def test_set_writes_the_marker_and_is_idempotent_per_key():
    gh = Gh()
    args = (REPO, "issue", 1150, "score-1150", "2026-12-18", "followup", "-", "measure:1150", NOW)
    assert tm.set_timer(gh, *args) == 0
    assert tm.set_timer(gh, *args) == 0
    [c] = gh.comments
    assert c["body"].startswith("<!-- agent-timer: key=score-1150 due=2026-12-18T00:00:00Z "
                                "kind=followup every=- target=issue:1150 action=measure:1150 -->")


def test_set_refuses_what_fire_could_not_find_or_parse():
    gh = Gh()
    bad = [("issue", 1, "k", "2027-03-01", "followup", "-", "measure:1"),    # past the search window
           ("issue", 1, "k", "2026-12-20", "schedule", "-", "issue:1"),      # schedule with no cadence
           ("issue", 1, "k", "2026-12-20", "followup", "1d", "issue:1"),     # follow-up with a cadence
           ("issue", 1, "k", "2026-12-20", "schedule", "45d", "issue:1"),    # longer than the window
           ("issue", 1, "k k", "2026-12-20", "followup", "-", "issue:1"),    # key with a space
           ("issue", 1, "k", "tomorrow", "followup", "-", "issue:1"),
           ("issue", 1, "k", "2026-12-20", "followup", "-", "deploy:1")]
    for b in bad:
        assert tm.set_timer(gh, REPO, *b, NOW) == 2, b
    assert gh.comments == []


def test_from_file_carries_only_the_allowed_kinds(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("target=issue:1150 key=score-1150 due=2026-12-18 action=measure:1150\n"
                 "target=issue:7 key=sneaky due=2026-12-18 action=issue:7\n"
                 "free text the agent wrote\n")
    gh = Gh()
    assert tm.set_from_file(gh, REPO, str(f), ("measure",), NOW) == 2
    assert [c["on"] for c in gh.comments] == [1150], "only the measure timer was set"


def test_from_file_with_no_file_is_no_timers(tmp_path):
    assert tm.set_from_file(Gh(), REPO, str(tmp_path / "absent.txt"), ("measure",), NOW) == 0


def test_from_file_refuses_a_runaway(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("".join(f"target=issue:{i} key=score-{i} due=2026-12-18 action=measure:{i}\n"
                         for i in range(tm.MAX_FILE_LINES + 1)))
    gh = Gh()
    assert tm.set_from_file(gh, REPO, str(f), ("measure",), NOW) == 2 and gh.comments == []


def test_main_from_file_needs_an_explicit_scope(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_REPO", REPO)
    assert tm.main(["timers.py", "set", "--from-file", str(tmp_path / "x")], gh=Gh(), now=NOW) == 2


# ------------------------------------------------------- the wiring

def test_the_analyst_records_timers_and_agent_measure_sets_them_with_github_token():
    md = (ROOT / ".claude" / "agents" / "analyst.md").read_text()
    flat = " ".join(md.split())
    assert "set a timer for that date" in flat
    assert "target=issue:<n> key=score-<n> due=<deploy + 31 days, YYYY-MM-DD> action=measure:<n>" in flat
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-measure.yml").read_text())
    steps = doc["jobs"]["measure"]["steps"]
    i_agent = next(i for i, s in enumerate(steps) if "claude-code-action" in (s.get("uses") or ""))
    agent = steps[i_agent]
    assert agent["with"]["allowed_bots"] == "github-actions", (
        "a timer-dispatched analyst run is a Bot actor (#421)")
    assert "/tmp/analyst-timers.txt" in agent["with"]["prompt"]
    i_set = next(i for i, s in enumerate(steps) if s.get("name") == "Set the analyst's scoring timers")
    assert i_set > i_agent
    s = steps[i_set]
    assert s["run"] == ("python3 scripts/timers.py set --from-file /tmp/analyst-timers.txt "
                        "--allow-kinds measure")
    assert s["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert doc["jobs"]["measure"]["permissions"]["issues"] == "write", "no new scope needed"


def test_a_timer_entry_key_carries_the_due_time_the_drain_covers_from():
    e = cq.Entry(1, "measure", 1150, "timer", "2026-12-18T03:17:00Z", "",
                 key="timer.score-1150.20261218T0000Z")
    assert cq._cover_since(e) == datetime(2026, 12, 18, tzinfo=timezone.utc)
