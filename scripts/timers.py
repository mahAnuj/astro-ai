#!/usr/bin/env python3
"""Timers: agent-set follow-ups and schedules, fired into the inbox (#1187).

WHY THIS EXISTS
---------------
The loop had fixed crons only, and GitHub throttles them: the `*/30` merge
sweep runs about every 6h, the analyst's 21:00 slot started 00:09-01:20Z over
2026-11-05..09. And an agent could not schedule its own follow-up at all: the
analyst wrote "pending — scoreable from <deploy + 31 days>" as prose and
nothing ever fired it. A timer is that sentence made executable.

WHERE A TIMER LIVES
-------------------
A hidden marker comment on the issue or PR it is about, written by
`github-actions[bot]` -- the queue's store and the queue's trust rule
(scripts/cycle_queue.py), so it needs no new store and no new permission:

    <!-- agent-timer: key=score-1150 due=2026-12-18T00:00:00Z kind=followup every=- target=issue:1150 action=measure:1150 -->

  key     [A-Za-z0-9_-]+, unique per target; `set` with an existing key is a no-op
  due     UTC, `YYYY-MM-DDTHH:MM:SSZ` (`set` accepts a bare date: 00:00Z)
  kind    followup (fires once, then its marker becomes `agent-timer-done`)
          schedule (fires, then `due` moves to the next occurrence after now)
  every   `-` for a follow-up; `<n>h` or `<n>d` for a schedule
  target  issue:<n> or pr:<n> -- where the marker is written
  action  <inbox kind>:<n>, the queue entry it appends: issue, pr, fix_pr
          (an agent-work cycle) or measure (an analyst scoring run)

ONLY `github-actions[bot]` MARKERS COUNT. An agent's own `gh` is the Claude App
token, so a marker an agent pastes is `claude[bot]`'s and is ignored, exactly as
in the queue. Agents set timers by handing a line to a workflow `run:` step that
calls `timers.py set` with `github.token` -- the analyst writes
`/tmp/analyst-timers.txt` and agent-measure carries it (`--from-file`), the same
record-then-carry shape as every dispatch ruling (#442).

HOW IT FIRES
------------
`fire` runs in agent-queue's hourly job, BEFORE the drain, so a due timer is
started the same hour. For each due timer it appends an inbox entry keyed
`timer.<key>.<due as YYYYMMDDTHHMMZ>` -- one key per occurrence -- and only then
marks the follow-up done or advances the schedule. A double fire (two hourly
runs, or a mark that failed) appends nothing the second time: the queue
dedupes a keyed entry in every state. API reads only, no model.

FINDING TIMERS WITHOUT LISTING EVERY COMMENT
--------------------------------------------
The repo writes ~200 comments a day (measured 2026-11-17: 1,448 since
2026-11-10), so reading every comment back to a 31-day follow-up's creation
would be ~60 pages an hour. Instead: the search API, which indexes hidden
markers in comments (checked 2026-11-17: `"agent-work-queue-taken"
in:comments` finds 5 issues and 30 PRs), limited to items updated within
HORIZON_DAYS, plus the last week's comments, which covers what the search
index has not caught up with yet. `set` refuses a due time further out than
MAX_LEAD_DAYS, so a live timer is always inside the search window.

EXIT CODES: 0 done   1 an API call failed (the run goes red; nothing is marked)   2 bad arguments
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_queue  # noqa: E402

Runner = Callable[[list[str]], str]

WRITER = "github-actions[bot]"
MARK = "agent-timer"
HORIZON_DAYS = 60
MAX_LEAD_DAYS = 55
MAX_EVERY = timedelta(days=30)
RECENT_DAYS = 8
#: Lines `--from-file` will carry from one agent run. The analyst scores a
#: handful of issues a night; more than this is a runaway, not a backlog.
MAX_FILE_LINES = 20

_ISO = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ"
TIMER = re.compile(
    r"<!-- agent-timer(-done)?: key=([A-Za-z0-9_-]+) due=(" + _ISO + r") "
    r"kind=(followup|schedule) every=(-|\d+[hd]) target=(issue|pr):(\d+) "
    r"action=(issue|pr|fix_pr|measure):(\d+) -->")
_KEY = re.compile(r"[A-Za-z0-9_-]{1,60}")


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}... failed: {p.stderr.strip()[:300]}")
    return p.stdout


@dataclass(frozen=True)
class Timer:
    comment_id: int
    key: str
    due: datetime
    kind: str
    every: str
    target_kind: str
    target: int
    action_kind: str
    action_target: int
    done: bool
    body: str


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_due(s: str) -> datetime:
    """`YYYY-MM-DD` (00:00Z) or `YYYY-MM-DDTHH:MM:SSZ`."""
    if re.fullmatch(r"\d{4}-\d\d-\d\d", s):
        s += "T00:00:00Z"
    if not re.fullmatch(_ISO, s):
        raise ValueError(f"due must be YYYY-MM-DD or {_ISO!r}-shaped UTC, got {s!r}")
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def parse_every(s: str) -> timedelta | None:
    if s == "-":
        return None
    m = re.fullmatch(r"(\d+)([hd])", s)
    if not m or int(m.group(1)) == 0:
        raise ValueError(f"every must be '-' or <n>h / <n>d, got {s!r}")
    n = int(m.group(1))
    return timedelta(hours=n) if m.group(2) == "h" else timedelta(days=n)


def marker(key: str, due: datetime, kind: str, every: str, target_kind: str, target: int,
           action_kind: str, action_target: int, done: bool = False) -> str:
    state = f"{MARK}-done" if done else MARK
    return (f"<!-- {state}: key={key} due={_iso(due)} kind={kind} every={every} "
            f"target={target_kind}:{target} action={action_kind}:{action_target} -->")


def body_for(t: Timer, due: datetime, done: bool, note: str) -> str:
    """The WHOLE comment, regenerated on every edit: a schedule that appended a
    line per firing would grow without bound."""
    what = ("fires once" if t.kind == "followup" else f"fires every {t.every}")
    return (marker(t.key, due, t.kind, t.every, t.target_kind, t.target,
                   t.action_kind, t.action_target, done) + "\n"
            f"**Timer `{t.key}`:** {what}; next due `{_iso(due)}`"
            + (" (done)" if done else "") +
            f" -> queues `{t.action_kind}={t.action_target}` for `agent-queue`.\n\n"
            f"{note}\n\nFired by agent-queue's hourly job (`scripts/timers.py fire`). "
            f"Only markers written by `{WRITER}` count.")


def _parse(c: dict) -> Timer | None:
    if c.get("login") != WRITER:
        return None
    m = TIMER.search(c.get("body") or "")
    if not m:
        return None
    return Timer(int(c["id"]), m.group(2), parse_due(m.group(3)), m.group(4), m.group(5),
                 m.group(6), int(m.group(7)), m.group(8), int(m.group(9)), bool(m.group(1)),
                 c.get("body") or "")


def timers_on(gh: Runner, repo: str, number: int) -> list[Timer]:
    raw = gh(["api", "--paginate", f"repos/{repo}/issues/{number}/comments?per_page=100",
              "--jq", '.[] | {id, body, login: .user.login}'])
    out = []
    for line in raw.splitlines():
        if line.strip():
            t = _parse(json.loads(line))
            if t:
                out.append(t)
    return out


def candidates(gh: Runner, repo: str, now: datetime) -> tuple[set[int], bool]:
    """(issue/PR numbers that may carry a timer, whether the search worked)."""
    found: set[int] = set()
    ok = True
    since = (now - timedelta(days=HORIZON_DAYS)).strftime("%Y-%m-%d")
    for kind in ("is:issue", "is:pull-request"):
        try:
            raw = gh(["api", "-X", "GET", "search/issues",
                      "-f", f'q=repo:{repo} {kind} "{MARK}" in:comments updated:>={since}',
                      "-f", "per_page=100", "--jq", ".items[].number"])
            found |= {int(n) for n in raw.split() if n.isdigit()}
        except RuntimeError as exc:
            ok = False
            print(f"::warning::timer search ({kind}) failed: {exc}")
    recent = (now - timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = gh(["api", "--paginate", f"repos/{repo}/issues/comments?since={recent}&per_page=100",
              "--jq", f'.[] | select(.user.login == "{WRITER}") '
                      f'| select(.body | contains("<!-- {MARK}")) | .issue_url'])
    for url in raw.split():
        m = re.search(r"/issues/(\d+)$", url)
        if m:
            found.add(int(m.group(1)))
    return found, ok


def list_timers(gh: Runner, repo: str, now: datetime) -> tuple[list[Timer], bool]:
    nums, ok = candidates(gh, repo, now)
    out: list[Timer] = []
    for n in sorted(nums):
        out += timers_on(gh, repo, n)
    return out, ok


def set_timer(gh: Runner, repo: str, target_kind: str, target: int, key: str, due: str,
              kind: str, every: str, action: str, now: datetime | None = None,
              allow_kinds: tuple[str, ...] | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    try:
        if target_kind not in ("issue", "pr"):
            raise ValueError(f"target must be issue:<n> or pr:<n>, got {target_kind}")
        if not _KEY.fullmatch(key):
            raise ValueError(f"key must match [A-Za-z0-9_-]{{1,60}}, got {key!r}")
        d = parse_due(due)
        step = parse_every(every)
        if kind not in ("followup", "schedule"):
            raise ValueError(f"kind must be followup or schedule, got {kind!r}")
        if (kind == "schedule") != (step is not None):
            raise ValueError("a schedule needs every=<n>h|<n>d; a follow-up needs every=-")
        if step and step > MAX_EVERY:
            raise ValueError(f"every may be at most {MAX_EVERY.days}d (the search window)")
        if d > now + timedelta(days=MAX_LEAD_DAYS):
            raise ValueError(f"due {_iso(d)} is more than {MAX_LEAD_DAYS} days out")
        m = re.fullmatch(r"(issue|pr|fix_pr|measure):(\d+)", action)
        if not m:
            raise ValueError(f"action must be <issue|pr|fix_pr|measure>:<n>, got {action!r}")
        if allow_kinds is not None and m.group(1) not in allow_kinds:
            raise ValueError(f"action kind {m.group(1)!r} is not allowed here ({', '.join(allow_kinds)})")
    except ValueError as exc:
        print(f"::error::timers.py set: {exc}")
        return 2
    try:
        existing = timers_on(gh, repo, target)
    except (RuntimeError, ValueError) as exc:
        print(f"::error::could not read #{target} before setting timer {key}: {exc}")
        return 1
    if any(t.key == key for t in existing):
        print(f"timer {key} already set on {target_kind}:{target}; not adding a second.")
        return 0
    t = Timer(0, key, d, kind, every, target_kind, target, m.group(1), int(m.group(2)), False, "")
    body = body_for(t, d, False, f"Set at `{_iso(now)}`.")
    try:
        gh(["api", "-X", "POST", f"repos/{repo}/issues/{target}/comments", "-f", f"body={body}"])
    except RuntimeError as exc:
        print(f"::error::could not set timer {key} on #{target}: {exc}")
        return 1
    print(f"::notice::timer {key} set on {target_kind}:{target}, due {_iso(d)} -> {action}")
    return 0


_LINE = re.compile(r"target=(issue|pr):(\d+) key=(\S+) due=(\S+) action=(\S+)"
                   r"(?: kind=(followup|schedule))?(?: every=(\S+))?")


def set_from_file(gh: Runner, repo: str, path: str, allow_kinds: tuple[str, ...],
                  now: datetime | None = None) -> int:
    """Carry an agent's recorded timers. Each line, exactly:
    `target=issue:<n> key=<key> due=<date|iso> action=<kind>:<n>` (a follow-up),
    optionally followed by ` kind=schedule every=<n>h|<n>d`. A missing file or
    an empty one is no timers -- a ruling, not a failure."""
    try:
        lines = [l.strip() for l in Path(path).read_text().splitlines() if l.strip()]
    except OSError:
        print(f"no timers recorded ({path} absent).")
        return 0
    if len(lines) > MAX_FILE_LINES:
        print(f"::error::{len(lines)} timer lines in {path}; at most {MAX_FILE_LINES}. Setting none.")
        return 2
    worst = 0
    for line in lines:
        m = _LINE.fullmatch(line)
        if not m:
            print(f"::error::unparseable timer line, skipped: {line[:120]!r}")
            worst = max(worst, 2)
            continue
        rc = set_timer(gh, repo, m.group(1), int(m.group(2)), m.group(3), m.group(4),
                       m.group(6) or "followup", m.group(7) or "-", m.group(5), now, allow_kinds)
        worst = max(worst, rc)
    return worst


def next_due(due: datetime, step: timedelta, now: datetime) -> datetime:
    """The first occurrence strictly after `now`. Missed occurrences are
    skipped, never fired in a burst: a schedule is a cadence, not a backlog."""
    k = int((now - due) / step) + 1
    return due + k * step


Enqueue = Callable[..., int]


def fire(gh: Runner, repo: str, now: datetime | None = None,
         enqueue: Enqueue = cycle_queue.enqueue) -> int:
    now = now or datetime.now(timezone.utc)
    try:
        timers, searched = list_timers(gh, repo, now)
    except (RuntimeError, ValueError) as exc:
        print(f"::error::could not read timers: {exc}")
        return 1
    due = [t for t in timers if not t.done and t.due <= now]
    print(f"{len(timers)} timer(s) found, {len(due)} due.")
    failed = not searched
    for t in due:
        key = f"timer.{t.key}.{t.due:%Y%m%dT%H%MZ}"
        rc = enqueue(gh, repo, t.action_kind, t.action_target, "timer", t.target, key=key)
        if rc != 0:
            print(f"::error::timer {t.key} on #{t.target}: could not queue {t.action_kind}="
                  f"{t.action_target}; it stays due and fires again next hour.")
            failed = True
            continue
        try:
            if t.kind == "followup":
                body = body_for(t, t.due, True, f"Fired at `{_iso(now)}`: queued "
                                                f"`{t.action_kind}={t.action_target}` (key `{key}`).")
            else:
                nd = next_due(t.due, parse_every(t.every), now)
                body = body_for(t, nd, False, f"Last fired at `{_iso(now)}` for `{_iso(t.due)}`: "
                                              f"queued `{t.action_kind}={t.action_target}`.")
            gh(["api", "-X", "PATCH", f"repos/{repo}/issues/comments/{t.comment_id}",
                "-f", f"body={body}"])
        except RuntimeError as exc:
            # The entry exists; the next fire re-appends the same key, which the
            # queue drops, and tries this edit again. Nothing doubles.
            print(f"::error::timer {t.key}: queued, but the marker edit failed ({exc}).")
            failed = True
            continue
        print(f"fired {t.key} on {t.target_kind}:{t.target} -> {t.action_kind}={t.action_target}")
    return 1 if failed else 0


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("--target", help="issue:<n> or pr:<n>")
    s.add_argument("--key")
    s.add_argument("--due", help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ (UTC)")
    s.add_argument("--kind", default="followup", choices=("followup", "schedule"))
    s.add_argument("--every", default="-")
    s.add_argument("--action", help="<issue|pr|fix_pr|measure>:<n>")
    s.add_argument("--from-file", help="one timer per line (see set_from_file)")
    s.add_argument("--allow-kinds", default="", help="comma list of action kinds a file may use")
    sub.add_parser("list")
    sub.add_parser("fire")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::timers.py needs GH_REPO=owner/name")
        return 2
    if a.cmd == "fire":
        return fire(gh, repo, now)
    if a.cmd == "list":
        try:
            timers, _ = list_timers(gh, repo, now or datetime.now(timezone.utc))
        except (RuntimeError, ValueError) as exc:
            print(f"::error::could not read timers: {exc}")
            return 1
        for t in timers:
            print(f"{'done' if t.done else 'live'}\t{t.target_kind}:{t.target}\t{t.key}\t"
                  f"{_iso(t.due)}\t{t.kind}\t{t.every}\t{t.action_kind}:{t.action_target}")
        return 0
    if a.from_file:
        allow = tuple(k for k in a.allow_kinds.split(",") if k)
        if not allow:
            print("::error::--from-file needs --allow-kinds: an agent's file never picks its own scope")
            return 2
        return set_from_file(gh, repo, a.from_file, allow, now)
    m = re.fullmatch(r"(issue|pr):(\d+)", a.target or "")
    if not (m and a.key and a.due and a.action):
        print("::error::set needs --target issue:<n>|pr:<n> --key --due --action (or --from-file)")
        return 2
    return set_timer(gh, repo, m.group(1), int(m.group(2)), a.key, a.due, a.kind, a.every,
                     a.action, now)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
