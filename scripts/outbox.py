#!/usr/bin/env python3
"""The one posting path for the loop's comments and issues (#1188, slice 4 of #1184).

WHY THIS EXISTS
---------------
Every script posted on its own, each with its own anti-noise rule, each rule added
after an incident: #311, #276 and #329 collected 20+ near-identical comments apiece.
There was no retry, no delivery record and no measure of how noisy the loop is.
Anthropic's always-on guide (2026-11-13) names the missing primitive the outbox:
pace messages, recover from errors, start quiet, build evals for the volume.

So a poster calls `Outbox.post()` / `Outbox.create_issue()` (or this file's CLI)
instead of `gh issue comment` / `gh api -X POST .../issues`, and gets:

  DEDUPE      key = (target, kind, sha256 of the body with its volatile parts
              normalised: SHAs, timestamps, run ids). Checked against this run's
              ledger and the target's recent comments by THIS identity, within a
              per-kind window (default 7 days). A duplicate is a logged no-op.
  DAILY CAP   per (target, kind), over a rolling 24h.
  QUIET START a kind not in KINDS gets QUIET_CAP (1 per target per day). Raising it
              is an explicit, reviewed edit to KINDS -- never a caller's argument.
  RETRY       backoff on 5xx, 429 and GitHub's secondary rate limit. Never on any
              other 4xx: a 422 resent is the same 422. Before each resend the target
              is re-read, because a 502 can still have created the comment.
  LEDGER      every attempt -- sent, deduped, capped, failed -- as one
              `OUTBOX-LEDGER` line on stderr, and as a JSON line in $OUTBOX_LEDGER
              when that is set. Counts, kinds, targets and keys ONLY: never the body.

WHERE THE LEDGER LANDS, AND WHY THIS SHAPE (docs/decisions/2026-11-17-always-on-outbox.md)
------------------------------------------------------------------------------------------
Posters run in many jobs with many tokens, and only agent-measure's commit job may
write `measurements/`. So the durable ledger is the posted text itself:

  * every message carries `<!-- outbox: kind=<kind> key=<16 hex> -->` on its last line;
  * a suppressed or failed attempt is TALLIED onto the newest comment of the same
    kind this identity already has on the target (`... deduped=2 capped=1 -->`) --
    an edit, which notifies nobody and needs only the write scope the poster holds;
  * `scripts/collect_outbox.py` reads the repo's recent comments and writes
    `measurements/outbox.json`, run from `collect_lessons.py` inside agent-measure.

No new permission, no new job, no workflow edit. What it cannot see: a failed post
with no earlier comment of its kind to tally onto (only the run's log has it), and
suppressed issue CREATIONS (an issue body is not edited). Both are stated in
outbox.json rather than reported as zero.

WHO COUNTS AS "ALREADY SAID"
----------------------------
Only comments this identity wrote (`viewerDidAuthor`) or, on REST reads, one of
LOOP_IDENTITIES. The marker is public text: an outsider who pastes it into their own
comment must not be able to silence the loop (the #361 / #367 rule).

A read that fails is FAIL-OPEN: the post goes out, checked against this run's ledger
only. A visible duplicate is better than a stop that announces nothing
(resolve_provenance.py's ruling, which this inherits rather than overrides).

TRANSPORT -- each migrated caller keeps the wire it already used
----------------------------------------------------------------
`transport="rest"` (the default, and file_ops_findings.py's): `gh api` on the
issue-comments endpoint, which serves PRs too and reports a clean `HTTP <code>`.
`transport="porcelain"` (triage and resolve_provenance): `gh issue|pr comment` and
`gh issue|pr view --json comments`, so #367's pinned write surface for triage (list,
comment, issue edit, label create) does not widen. Porcelain is GraphQL, which a
Claude Code web session's proxy refuses (measured 2026-11-17: HTTP 403); GitHub
Actions is not behind that proxy. Issues are created through `gh api -X POST
repos/<r>/issues`, which drops a missing label instead of failing the whole create --
file_ops_findings.py relies on that. Never a shell; argv lists only.

CLI
---
    outbox.py post --repo O/R (--issue N | --pr N) --kind K --body-file F
    outbox.py create-issue --repo O/R --kind K --title T --body-file F [--label L ...]
    outbox.py key --kind K --body-file F      # the dedupe key, for debugging
    outbox.py kinds                           # the KINDS config as JSON
EXIT: 0 sent, deduped or capped; 1 failed; 2 bad arguments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

#: This repository's own identities, as REST spells them. GraphQL drops the
#: `[bot]` suffix, which is why porcelain reads go by `viewerDidAuthor` instead.
LOOP_IDENTITIES = frozenset({"claude[bot]", "github-actions[bot]", "shubhagya-publisher[bot]"})

DEFAULT_WINDOW_DAYS = 7
#: A kind nobody has configured posts at most this often per target per day.
QUIET_CAP = 1

#: THE CONFIG. Small and explicit on purpose: a new kind starts quiet, and raising a
#: cap is a reviewed edit here, not an argument a caller can pass.
#:   cap          messages per target per rolling 24h
#:   window_days  how far back a duplicate is looked for
#:   dedupe       "window": any same-key message in the window is a duplicate.
#:                "last":   only the NEWEST message of this kind on the target counts.
#:                          For state carriers (A -> cleared -> A must be said again):
#:                          a window would swallow the second A.
KINDS: dict[str, dict] = {
    # file_ops_findings.py: "Now <LEVEL>" on a change and "cleared" when it goes, on
    # the one issue per finding kind. Two runs a day (agent-steward), so a finding
    # that flips each run is two comments; a third in a day is noise.
    "ops-finding": {"cap": 2, "window_days": 7, "dedupe": "last"},
    # file_ops_findings.py filing a new [OPS] issue. Target is the repository, so
    # the cap bounds how many new finding issues a day, across kinds.
    "ops-finding-issue": {"cap": 5, "window_days": 7, "dedupe": "window"},
    # triage_outsider_issues.py: one comment per issue per triage state.
    "triage-stage1": {"cap": 2, "window_days": 30, "dedupe": "window"},
    # resolve_provenance.py: the UNRESOLVED stop. Once is the announcement.
    "provenance-unresolved": {"cap": 1, "window_days": 7, "dedupe": "window"},
    # growth_split.py (2026-11-19): chief's Sunday goals and scores on the one
    # `weekly-goals` issue -- up to six files a Sunday (weekly, monthly, quarterly,
    # goals and score each). A re-posted identical file is a duplicate.
    "growth-goals": {"cap": 6, "window_days": 7, "dedupe": "window"},
    # growth_split.py creating that standing issue, once, when none is open.
    "growth-goals-issue": {"cap": 1, "window_days": 30, "dedupe": "window"},
}

#: Seconds before each resend. Secondary rate limits ask for "at least a minute".
RETRY_DELAYS = (10, 60)

_MARK = re.compile(r"<!-- outbox: kind=([a-z0-9-]+) key=([0-9a-f]{16})((?: [a-z]+=\d+)*) -->")
_KIND_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
TALLIED = ("deduped", "capped", "failed")

# Volatile parts. ORDER MATTERS: a timestamp is replaced before the run-id rule
# could eat its digits.
_TS = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?")
_RUN = re.compile(r"(actions/runs/|/job/|run[ _-]?(?:id)?[ =:#]*)\d+", re.I)
_LONG_INT = re.compile(r"\b\d{9,}\b")          # run and job ids are 10-11 digits
# A SHA needs a digit AND a letter: without the letter, "13174859 tokens" would read
# as a SHA and a moved count would be a duplicate; without the digit, "defaced" would.
# The cost: a short SHA that happens to be all digits (~4%) is not normalised.
_SHA = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")


def normalise(body: str) -> str:
    """The body as it is compared: marker gone, volatile parts replaced, whitespace
    collapsed. Two runs saying the same thing about a different head or at a
    different minute normalise equal; a changed NUMBER in the prose does not (a
    percentage moving is the caller's change rule, not this one's)."""
    t = _MARK.sub("", body or "")
    t = _TS.sub("<ts>", t)
    t = _RUN.sub(lambda m: m.group(1) + "<run>", t)
    t = _LONG_INT.sub("<id>", t)
    t = _SHA.sub("<sha>", t)
    return " ".join(t.split())


def key_for(kind: str, body: str) -> str:
    return hashlib.sha256(f"{kind}\n{normalise(body)}".encode()).hexdigest()[:16]


def policy(kind: str) -> dict:
    p = KINDS.get(kind)
    if p is None:
        return {"cap": QUIET_CAP, "window_days": DEFAULT_WINDOW_DAYS, "dedupe": "window", "quiet": True}
    return {"cap": int(p["cap"]), "window_days": int(p.get("window_days", DEFAULT_WINDOW_DAYS)),
            "dedupe": p.get("dedupe", "window"), "quiet": False}


def marker(kind: str, key: str, tallies: dict | None = None) -> str:
    extra = "".join(f" {k}={int(v)}" for k, v in sorted((tallies or {}).items()) if v)
    return f"<!-- outbox: kind={kind} key={key}{extra} -->"


def parse_marker(body: str) -> dict | None:
    """{kind, key, deduped, capped, failed} from the LAST marker in a body, or None."""
    found = list(_MARK.finditer(body or ""))
    if not found:
        return None
    m = found[-1]
    out = {"kind": m.group(1), "key": m.group(2), **{t: 0 for t in TALLIED}}
    for pair in m.group(3).split():
        k, _, v = pair.partition("=")
        if k in TALLIED:
            out[k] = int(v)
    return out


# --------------------------------------------------------------------------------------
# Errors: which ones are worth a resend
# --------------------------------------------------------------------------------------

class GhError(RuntimeError):
    def __init__(self, text: str, status: int | None = None):
        super().__init__(text)
        self.status = status


_STATUS = re.compile(r"\bHTTP (\d{3})\b")
_SECONDARY = re.compile(r"secondary rate limit|submitted too quickly|abuse detection", re.I)
_NETWORK = re.compile(r"timed? ?out|timeout|connection reset|connection refused|unexpected EOF|"
                      r"temporarily unavailable|TLS handshake", re.I)


def classify(exc: BaseException) -> tuple[int | None, bool]:
    """(HTTP status or None, worth a resend). A 4xx is final, except 429 and the
    secondary rate limit (a 403 whose text says so). No status at all is final
    unless the text is a network failure -- an unknown error resent blind is how
    a validation failure turns into three."""
    text = str(exc)
    status = getattr(exc, "status", None)
    if status is None:
        m = _STATUS.search(text)
        status = int(m.group(1)) if m else None
    if _SECONDARY.search(text):
        return status, True
    if status is not None:
        return status, status >= 500 or status == 429
    return None, bool(_NETWORK.search(text))


Runner = Callable[[list], str]


def run_gh(args: list) -> str:
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        raise GhError("gh timed out") from None
    if p.returncode != 0:
        raise GhError(f"gh {' '.join(args[:2])}: {p.stderr.strip()[:300]}")
    return p.stdout


def from_result_runner(gh: Callable) -> Runner:
    """Adapt a runner returning `Result(rc, out, err)` (triage, resolve_provenance)
    to this module's raise-on-failure shape, keeping its injected fakes usable."""
    def run(args: list) -> str:
        r = gh(args)
        if r.rc != 0:
            raise GhError(f"gh exit {r.rc}: {(r.err or '').strip()[:300]}")
        return r.out or ""
    return run


# --------------------------------------------------------------------------------------
# The outbox
# --------------------------------------------------------------------------------------

@dataclass
class Outcome:
    outcome: str            # sent | deduped | capped | failed
    kind: str
    target: str
    key: str
    attempts: int = 0
    status: int | None = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome != "failed"


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _login(c: dict) -> str:
    return str((c.get("user") or {}).get("login") or (c.get("author") or {}).get("login") or "")


def _comment_id(c: dict) -> int | None:
    if isinstance(c.get("id"), int):
        return c["id"]
    m = re.search(r"#issuecomment-(\d+)", str(c.get("url") or c.get("html_url") or ""))
    return int(m.group(1)) if m else None


class Outbox:
    """One per process run. Holds this run's ledger, so two posts in one run see
    each other even before GitHub's reads catch up."""

    def __init__(self, gh: Runner, repo: str, *, now: Callable[[], datetime] | None = None,
                 sleep: Callable[[float], None] = time.sleep, ledger_path: str | None = None,
                 log=None, tally: bool = True, transport: str = "rest"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo or ""):
            raise ValueError(f"bad repo {repo!r}")
        if transport not in ("rest", "porcelain"):
            raise ValueError(f"bad transport {transport!r}")
        self.transport = transport
        self.gh, self.repo, self.sleep = gh, repo, sleep
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.ledger_path = ledger_path if ledger_path is not None else os.environ.get("OUTBOX_LEDGER", "")
        self.log = log or sys.stderr
        self.tally = tally
        self.rows: list[dict] = []

    # ---- the ledger -----------------------------------------------------------------
    def _record(self, o: Outcome, comment_id: int | None = None, checked: bool = True) -> Outcome:
        row = {"at": self.now().strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": o.kind, "target": o.target,
               "key": o.key, "outcome": o.outcome, "attempts": o.attempts, "status": o.status,
               "checked": checked}
        if comment_id is not None:
            row["comment_id"] = comment_id
        self.rows.append(row)
        print("OUTBOX-LEDGER " + " ".join(f"{k}={row[k]}" for k in
                                          ("outcome", "kind", "target", "key", "attempts", "status")),
              file=self.log)
        if self.ledger_path:
            try:
                with open(self.ledger_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row, sort_keys=True) + "\n")
            except OSError as exc:
                print(f"OUTBOX-LEDGER could not append to {self.ledger_path}: {exc}", file=self.log)
        return o

    def _ledger_rows(self, target: str, kind: str) -> list[dict]:
        rows = list(self.rows)
        if self.ledger_path and os.path.isfile(self.ledger_path):
            try:
                with open(self.ledger_path, encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            r = json.loads(line)
                        except ValueError:
                            continue
                        if r not in rows:
                            rows.append(r)
            except OSError:
                pass
        return [r for r in rows if r.get("target") == target and r.get("kind") == kind]

    # ---- reading what is already there ----------------------------------------------
    def _read_comments(self, number: int, on: str) -> list[dict] | None:
        try:
            if self.transport == "porcelain":
                raw = self.gh([on, "view", str(number), "--repo", self.repo, "--json", "comments"])
                data = json.loads(raw or "{}")
                return list(data.get("comments") or []) if isinstance(data, dict) else None
            # REST: the issue-comments endpoint serves PRs too. `since` is the longest
            # window any kind uses, so a long thread is not read from its first page.
            since = self.now() - timedelta(days=max([DEFAULT_WINDOW_DAYS] + [
                int(k.get("window_days", DEFAULT_WINDOW_DAYS)) for k in KINDS.values()]))
            raw = self.gh(["api", "--paginate",
                           f"repos/{self.repo}/issues/{number}/comments?since="
                           f"{since.strftime('%Y-%m-%dT%H:%M:%SZ')}&per_page=100",
                           "--jq", ".[] | {id, created_at, user: {login: .user.login}, body}"])
            return _json_stream(raw)
        except (GhError, RuntimeError, ValueError, TypeError) as exc:
            print(f"OUTBOX-LEDGER read failed for {on}:{number} ({str(exc)[:120]}); "
                  "checking this run's ledger only", file=self.log)
            return None

    @staticmethod
    def _own(c: dict) -> bool:
        return c.get("viewerDidAuthor") is True or _login(c) in LOOP_IDENTITIES

    def _decide(self, kind: str, key: str, target: str, comments: Iterable[dict]) -> tuple[str | None, dict | None]:
        """(None | 'deduped' | 'capped', the newest own same-kind comment to tally onto)."""
        p = policy(kind)
        now = self.now()
        win, day = now - timedelta(days=p["window_days"]), now - timedelta(hours=24)
        # (when, key, comment-or-None, comment_id) for every message of this kind.
        seen: list[tuple[datetime, str, dict | None, int | None]] = []
        legacy_dup = False
        for c in comments:
            if not self._own(c):
                continue
            when = _ts(c.get("createdAt") or c.get("created_at")) or now
            m = parse_marker(c.get("body") or "")
            if m is None:
                # A message from before the outbox: no kind on it, so it can only be
                # a duplicate by its text -- and only in window mode.
                if when >= win and key_for(kind, c.get("body") or "") == key:
                    legacy_dup = True
                continue
            if m["kind"] == kind:
                seen.append((when, m["key"], c, _comment_id(c)))
        ids = {cid for _, _, _, cid in seen if cid is not None}
        for r in self._ledger_rows(target, kind):
            if r.get("outcome") != "sent" or (r.get("comment_id") in ids and r.get("comment_id") is not None):
                continue
            seen.append((_ts(r.get("at")) or now, r.get("key", ""), None, r.get("comment_id")))
        seen.sort(key=lambda s: s[0])
        newest_comment = next((s[2] for s in reversed(seen) if s[2] is not None), None)
        in_window = [s for s in seen if s[0] >= win]
        if p["dedupe"] == "last":
            dup = bool(seen) and seen[-1][1] == key
        else:
            dup = legacy_dup or any(s[1] == key for s in in_window)
        if dup:
            return "deduped", newest_comment
        if sum(1 for s in seen if s[0] >= day) >= p["cap"]:
            return "capped", newest_comment
        return None, newest_comment

    def _tally(self, comment: dict | None, what: str) -> None:
        """Count a suppressed or failed attempt on the comment that caused it. Best
        effort: an edit that fails is logged and the attempt stays in the run log."""
        if not self.tally or comment is None:
            return
        cid, body = _comment_id(comment), comment.get("body") or ""
        m = parse_marker(body)
        if cid is None or m is None:
            return
        counts = {t: m[t] for t in TALLIED}
        counts[what] += 1
        found = list(_MARK.finditer(body))[-1]
        new = body[:found.start()] + marker(m["kind"], m["key"], counts) + body[found.end():]
        try:
            self.gh(["api", "-X", "PATCH", f"repos/{self.repo}/issues/comments/{cid}", "-f", f"body={new}"])
            comment["body"] = new
        except (GhError, RuntimeError) as exc:
            print(f"OUTBOX-LEDGER tally edit failed on comment {cid} ({str(exc)[:120]})", file=self.log)

    # ---- posting ----------------------------------------------------------------------
    def post(self, number: int, kind: str, body: str, *, on: str = "issue",
             recent: list[dict] | None = None) -> Outcome:
        """Comment on issue or PR `number`. `recent`: the target's comments if the
        caller already read them (porcelain or REST shape); otherwise they are read."""
        if on not in ("issue", "pr") or not _KIND_OK.match(kind or "") or int(number) < 1:
            raise ValueError(f"bad post: on={on!r} kind={kind!r} number={number!r}")
        number = int(number)
        target, key = f"{on}:{number}", key_for(kind, body)
        comments, checked = recent, True
        if comments is None:
            comments = self._read_comments(number, on)
            if comments is None:
                comments, checked = [], False
        verdict, newest = self._decide(kind, key, target, comments)
        if verdict is not None:
            self._tally(newest, verdict)
            return self._record(Outcome(verdict, kind, target, key), checked=checked)
        text = (body or "").rstrip() + "\n\n" + marker(kind, key)
        if self.transport == "porcelain":
            args = [on, "comment", str(number), "--repo", self.repo, "--body", text]
        else:
            args = ["api", "-X", "POST", f"repos/{self.repo}/issues/{number}/comments",
                    "-f", f"body={text}", "--jq", ".id"]
        attempts, status, err = 0, None, ""
        for attempt in range(1, len(RETRY_DELAYS) + 2):
            attempts = attempt
            try:
                out = (self.gh(args) or "").strip()
                cid = int(out) if out.isdigit() else _comment_id({"url": out})
                return self._record(Outcome("sent", kind, target, key, attempts), cid, checked)
            except (GhError, RuntimeError) as exc:
                status, transient = classify(exc)
                err = str(exc)[:200]
                if not transient or attempt > len(RETRY_DELAYS):
                    break
                self.sleep(RETRY_DELAYS[attempt - 1])
                # A 5xx can still have created it. Look before resending.
                again = self._read_comments(number, on)
                if again is not None and any(self._own(c) and (parse_marker(c.get("body") or "") or {}).get("key") == key
                                             for c in again):
                    return self._record(Outcome("sent", kind, target, key, attempts, status), checked=checked)
        self._tally(newest, "failed")
        return self._record(Outcome("failed", kind, target, key, attempts, status, err), checked=checked)

    def _read_issues(self, since: datetime) -> list[dict] | None:
        try:
            raw = self.gh(["api", "--paginate",
                           f"repos/{self.repo}/issues?state=all&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}&per_page=100",
                           "--jq", ".[] | select(.pull_request == null) | "
                                   "{number, state, created_at, user: {login: .user.login}, body}"])
        except (GhError, RuntimeError) as exc:
            print(f"OUTBOX-LEDGER issue read failed ({str(exc)[:120]}); checking this run's ledger only",
                  file=self.log)
            return None
        return _json_stream(raw)

    def create_issue(self, kind: str, title: str, body: str, labels: Iterable[str] = ()) -> Outcome:
        """File an issue. A duplicate is an OPEN issue this repo's identities filed
        with the same key inside the window: a closed one was someone's decision,
        and re-filing after it is the caller's existing behaviour."""
        if not _KIND_OK.match(kind or ""):
            raise ValueError(f"bad kind {kind!r}")
        target, key = "repo", key_for(kind, f"{title}\n{body}")
        p = policy(kind)
        now = self.now()
        issues = self._read_issues(now - timedelta(days=p["window_days"]))
        checked = issues is not None
        # Issue bodies are not tallied (an edit there is an `issues: edited` event and
        # rewrites a document agents read); a suppressed create is in the run log only.
        pseudo = []
        for i in issues or []:
            if _login(i) not in LOOP_IDENTITIES:
                continue
            m = parse_marker(i.get("body") or "")
            if m is None or m["kind"] != kind:
                continue
            # An issue that is closed cannot be a duplicate, but it still counts to the cap.
            pseudo.append({"user": {"login": _login(i)}, "created_at": i.get("created_at"),
                           "body": i.get("body") if i.get("state") == "open" else
                           marker(kind, "0" * 16)})
        verdict, _ = self._decide(kind, key, target, pseudo)
        if verdict is not None:
            return self._record(Outcome(verdict, kind, target, key), checked=checked)
        args = ["api", "-X", "POST", f"repos/{self.repo}/issues",
                "-f", f"title={title}", "-f", f"body={(body or '').rstrip()}\n\n{marker(kind, key)}"]
        for lab in labels:
            args += ["-f", f"labels[]={lab}"]
        attempts, status, err = 0, None, ""
        for attempt in range(1, len(RETRY_DELAYS) + 2):
            attempts = attempt
            try:
                self.gh(args)
                return self._record(Outcome("sent", kind, target, key, attempts), checked=checked)
            except (GhError, RuntimeError) as exc:
                status, transient = classify(exc)
                err = str(exc)[:200]
                if not transient or attempt > len(RETRY_DELAYS):
                    break
                self.sleep(RETRY_DELAYS[attempt - 1])
                again = self._read_issues(now - timedelta(hours=1)) or []
                if any(_login(i) in LOOP_IDENTITIES and (parse_marker(i.get("body") or "") or {}).get("key") == key
                       for i in again):
                    return self._record(Outcome("sent", kind, target, key, attempts, status), checked=checked)
        return self._record(Outcome("failed", kind, target, key, attempts, status, err), checked=checked)


def _json_stream(raw: str) -> list[dict]:
    """Every JSON value in `raw`, whether gh printed one per line or pretty."""
    dec, i, out, raw = json.JSONDecoder(), 0, [], raw or ""
    while i < len(raw):
        while i < len(raw) and raw[i].isspace():
            i += 1
        if i >= len(raw):
            break
        val, i = dec.raw_decode(raw, i)
        if isinstance(val, list):
            out.extend(v for v in val if isinstance(v, dict))
        elif isinstance(val, dict):
            out.append(val)
    return out


def validate_kinds(kinds: dict = KINDS) -> list[str]:
    bad = []
    for k, p in kinds.items():
        if not _KIND_OK.match(k):
            bad.append(f"{k}: kind names are [a-z0-9-]")
        if not isinstance(p.get("cap"), int) or p["cap"] < 1:
            bad.append(f"{k}: cap must be an int >= 1 (0 would leave nothing to tally onto)")
        if not isinstance(p.get("window_days", DEFAULT_WINDOW_DAYS), int) or p.get("window_days", 1) < 1:
            bad.append(f"{k}: window_days must be an int >= 1")
        if p.get("dedupe", "window") not in ("window", "last"):
            bad.append(f"{k}: dedupe is 'window' or 'last'")
    return bad


def main(argv: list[str] | None = None, gh: Runner = run_gh) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post")
    p.add_argument("--repo", default=os.environ.get("GH_REPO", ""))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--issue", type=int)
    g.add_argument("--pr", type=int)
    p.add_argument("--kind", required=True)
    p.add_argument("--body-file", required=True)
    c = sub.add_parser("create-issue")
    c.add_argument("--repo", default=os.environ.get("GH_REPO", ""))
    c.add_argument("--kind", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--body-file", required=True)
    c.add_argument("--label", action="append", default=[])
    k = sub.add_parser("key")
    k.add_argument("--kind", required=True)
    k.add_argument("--body-file", required=True)
    sub.add_parser("kinds")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    if a.cmd == "kinds":
        print(json.dumps({"kinds": KINDS, "quiet_cap": QUIET_CAP,
                          "default_window_days": DEFAULT_WINDOW_DAYS}, indent=2))
        return 0
    try:
        body = sys.stdin.read() if a.body_file == "-" else open(a.body_file, encoding="utf-8").read()
    except OSError as exc:
        print(f"outbox: cannot read --body-file: {exc}", file=sys.stderr)
        return 2
    if a.cmd == "key":
        print(key_for(a.kind, body))
        return 0
    try:
        box = Outbox(gh, a.repo)
        if a.cmd == "post":
            o = box.post(a.issue or a.pr, a.kind, body, on="issue" if a.issue else "pr")
        else:
            o = box.create_issue(a.kind, a.title, body, a.label)
    except ValueError as exc:
        print(f"outbox: {exc}", file=sys.stderr)
        return 2
    print(f"outbox: {o.outcome} {o.kind} {o.target} key={o.key}")
    return 0 if o.ok else 1


if __name__ == "__main__":
    sys.exit(main())
