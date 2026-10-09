#!/usr/bin/env python3
"""Weekly loop-outcome report: did each autonomous loop have an EFFECT?

WHY THIS EXISTS (#316, part 2 of #313)
--------------------------------------
Four defects found on 2026-10-08/09 were each invisible because workflow STATUS
was fine -- green, or absent, rather than red:

  1. agent-merge's `workflow_run` leg returned HTTP 422 on every run; the
     `pull_request_target` leg worked, so merges happened and nobody looked.
  2. close-on-evidence lacked `pull-requests: read`; its close step 403'd, but
     the job's `if` had never passed, so the step had never run.
  3. agent-work / agent-discover lacked `actions: read`; the measurement fetch
     403'd inside a `continue-on-error` step and the run went green. The delivery
     cycle had never once received the analyst's measurement.
  4. close-on-evidence's first successful run closed nothing (PR #312 mentioned
     its issue without a closing keyword). It concluded `success`.

A static gate (#315) sees two of those. This reads HISTORY: for each loop it
asks "what should have happened, derived from something UPSTREAM", then "what
is actually there, observed DOWNSTREAM". A conclusion is never the evidence.

THE VERDICTS
------------
  OK       expected work existed and its effect is there
  IDLE     the expected set is EMPTY -- nothing to do, which is not a fault
  BROKEN   expected work existed and the effect is short, or every run failed
  UNKNOWN  the evidence could not be read (403, 404, expired log, 5xx)

UNKNOWN is never green. Exit 0 only if everything is OK/IDLE; 2 if anything is
UNKNOWN; 1 if anything is BROKEN (1 wins). "Produced nothing because there was
nothing to do" versus "produced nothing because it is broken" is the whole point
-- conflating them is what hid defect 3 for its entire life.

ENDPOINTS READ, AND THE GITHUB_TOKEN SCOPE EACH NEEDS
-----------------------------------------------------
The static workflow gate (#315) cannot see `gh` calls made inside this script,
so this table is the only place the requirement is written down. A test asserts
`.github/workflows/loop-outcomes.yml` grants every scope named here -- a missing
one reads as a 403, which this script (correctly) reports as UNKNOWN, i.e. it
would degrade into the very blind spot it exists to remove.

  actions/workflows/{wf}/runs, actions/runs/{id}/jobs,
  actions/jobs/{id}/logs ........................ actions: read
  pulls, pulls/{n} .............................. pull-requests: read
  issues/{n}/events, issues/comments,
  issues/events, issues ......................... issues: read
  commits?path= ................................. contents: read
  commits/{sha}/check-runs ...................... checks: read

STDLIB ONLY, deliberately: the workflow runs it with no `uv sync`.

    python3 scripts/report_loop_outcomes.py --since 2026-10-02 --until 2026-10-09
    python3 scripts/report_loop_outcomes.py --fixtures tests/fixtures/loop_outcomes/healthy
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

OK, IDLE, BROKEN, UNKNOWN = "OK", "IDLE", "BROKEN", "UNKNOWN"
RECEIVED, NONE_YET, DENIED = "RECEIVED", "NONE_YET", "DENIED"

# Something that began less than this long before the window closed is IN
# FLIGHT, not broken: a PR opened 20 minutes ago has not failed to merge.
GRACE = timedelta(hours=2)
# agent-work opens its PR near the end of the run; allow a little slack after it.
RUN_PAD = timedelta(minutes=15)

BOT = "github-actions[bot]"
FAILED = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}

# Runs per WEEK a schedule must produce. Hard-coded rather than parsed from the
# workflows (that needs PyYAML, which is not stdlib); instead a test regex-checks
# this table against the `cron:` lines so the two cannot drift apart.
MIN_RUNS = {"agent-work": 5, "agent-measure": 5, "agent-discover": 1, "agent-design": 1}

# The loop's own report file; a commit touching it is the loop's effect.
REPORT_PATH = {
    "agent-measure": "measurements/latest.md",
    "agent-discover": "measurements/discover/latest.md",
    "agent-design": "measurements/design/latest.md",
}
WORKFLOW = {name: f"{name}.yml" for name in
            ("agent-merge", "agent-work", "agent-measure", "agent-discover", "agent-design",
             "close-on-evidence", "verify-production", "pr-gates")}

# The echoed first line of the measurement-fetch step, used to find its slice of
# a job log. The raw log carries the script's first line, not the step's name.
MEASURE_ANCHOR = "agent-measure.yml"
LEGIT_STOP = re.compile(r"cannot[- ]reproduce|needs[- ]evidence", re.I)


# --------------------------------------------------------------------------- #
# time
# --------------------------------------------------------------------------- #

def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Window:
    since: datetime
    until: datetime

    @property
    def days(self) -> float:
        return (self.until - self.since).total_seconds() / 86400

    def contains(self, t: str) -> bool:
        return self.since <= ts(t) <= self.until

    def settled(self, t: str) -> bool:
        """Old enough to demand an effect from. In flight is not broken.
        Inclusive: something exactly GRACE old is judged; one second younger is not."""
        return ts(t) <= self.until - GRACE

    def merged_in(self, t: str) -> bool:
        """Merged inside the window AND settled. `agent_prs` selects by updated_at, so
        a PR merged weeks ago and merely touched this week arrives here too; its
        verification run and its issue's close belong to a window this report is
        not looking at, and judging it reads as a false BROKEN."""
        return self.since <= ts(t) and self.settled(t)


def parse_when(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# findings
# --------------------------------------------------------------------------- #

@dataclass
class Finding:
    loop: str
    verdict: str
    sentence: str          # one plain sentence naming WHAT produced nothing, and WHY
    evidence: list[str] = field(default_factory=list)


def exit_code(findings: list[Finding]) -> int:
    if any(f.verdict == BROKEN for f in findings):
        return 1
    if any(f.verdict == UNKNOWN for f in findings):
        return 2
    return 0


def _refs(items: list[dict], n: int = 6) -> list[str]:
    out = [f"run {r['id']} {r.get('conclusion') or r.get('status')} {r.get('html_url', '')}".strip()
           for r in items[:n]]
    if len(items) > n:
        out.append(f"... and {len(items) - n} more")
    return out


def _done(runs: list[dict]) -> list[dict]:
    return [r for r in runs if r.get("status") == "completed"]


# --------------------------------------------------------------------------- #
# sources: the seam between pure classifiers and the network
# --------------------------------------------------------------------------- #

class ApiError(Exception):
    def __init__(self, status: int | None, path: str, message: str):
        super().__init__(f"HTTP {status or '?'} on {path}: {message}")
        self.status, self.path, self.message = status, path, message


class Source:
    def get(self, path: str, paginate: bool = False):
        raise NotImplementedError

    def text(self, path: str) -> str:
        raise NotImplementedError


def _parse_stream(s: str) -> list:
    """Every JSON value in `s`. `gh api --paginate` prints one per page, with no
    separator guarantee and (depending on version) no `--slurp`; raw_decode needs
    neither."""
    dec, i, out = json.JSONDecoder(), 0, []
    s = s.strip()
    while i < len(s):
        obj, i = dec.raw_decode(s, i)
        out.append(obj)
        while i < len(s) and s[i].isspace():
            i += 1
    return out


def _merge_pages(pages: list):
    if not pages:
        return []
    if len(pages) == 1:
        return pages[0]
    if all(isinstance(p, list) for p in pages):
        return [x for p in pages for x in p]
    merged = dict(pages[0])
    for p in pages[1:]:
        for k, v in p.items():
            if isinstance(v, list) and isinstance(merged.get(k), list):
                merged[k] = merged[k] + v
    return merged


class GhSource(Source):
    def __init__(self, repo: str):
        self.repo = repo

    def _run(self, path: str, extra: list[str]) -> str:
        cmd = ["gh", "api", *extra, f"repos/{self.repo}/{path}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ApiError(None, path, f"could not run gh: {e}") from e
        if r.returncode != 0:
            m = re.search(r"HTTP (\d+)", r.stderr)
            raise ApiError(int(m.group(1)) if m else None, path,
                           (r.stderr.strip() or r.stdout.strip())[:200])
        return r.stdout

    def get(self, path: str, paginate: bool = False):
        out = self._run(path, ["--paginate"] if paginate else [])
        return _merge_pages(_parse_stream(out))

    def text(self, path: str) -> str:
        return self._run(path, [])


# Query parameters that select DIFFERENT DATA (as opposed to paging/windowing)
# and so must be part of a fixture's name.
_KEYED_PARAMS = ("path", "state")


def fixture_key(path: str) -> str:
    base, _, query = path.partition("?")
    key = re.sub(r"[^A-Za-z0-9.-]+", "_", base).strip("_")
    for part in query.split("&"):
        k, _, v = part.partition("=")
        if k in _KEYED_PARAMS:
            key += f"__{k}-" + re.sub(r"[^A-Za-z0-9.-]+", "_", v).strip("_")
    return key


class FixtureSource(Source):
    """A directory chain keyed by `fixture_key`. Earlier dirs override later ones,
    so a defect scenario holds only the files that differ from the healthy base.
    `<key>.error` ("403 message") raises ApiError; a missing file is a 404."""

    def __init__(self, dirs: list[Path]):
        self.dirs = [Path(d) for d in dirs]

    def _find(self, path: str, suffix: str):
        key = fixture_key(path)
        for d in self.dirs:
            err = d / f"{key}.error"
            if err.exists():
                status, _, msg = err.read_text().strip().partition(" ")
                raise ApiError(int(status), path, msg)
            if (d / f"{key}{suffix}").exists():
                return d / f"{key}{suffix}"
        raise ApiError(404, path, f"no fixture {key}{suffix}")

    def get(self, path: str, paginate: bool = False):
        return json.loads(self._find(path, ".json").read_text())

    def text(self, path: str) -> str:
        return self._find(path, ".log").read_text()


class MemoSource(Source):
    """Several loops read the same endpoint (agent PRs, verify runs). Fetch once."""

    def __init__(self, inner: Source):
        self.inner, self._memo = inner, {}

    def _cached(self, key, fn):
        if key not in self._memo:
            try:
                self._memo[key] = (fn(), None)
            except ApiError as e:
                self._memo[key] = (None, e)
        value, err = self._memo[key]
        if err:
            raise err
        return value

    def get(self, path: str, paginate: bool = False):
        return self._cached(("get", path), lambda: self.inner.get(path, paginate))

    def text(self, path: str) -> str:
        return self._cached(("text", path), lambda: self.inner.text(path))


# --------------------------------------------------------------------------- #
# pure helpers: log reading
# --------------------------------------------------------------------------- #

def step_output(log: str, anchor: str) -> list[str] | None:
    """Output lines of the `Run` step whose FIRST line mentions `anchor`.

    The raw job log wraps each `run:` step as `##[group]Run <script>` ...
    `##[endgroup]` followed by the output. The group CONTAINS THE SCRIPT SOURCE,
    which for the measurement fetch includes `echo "no prior measurement"` -- so a
    naive substring search finds the words in the echoed source even when the real
    output was a 403. Only what follows `##[endgroup]` is evidence.
    """
    state, out = 0, []
    for line in log.splitlines():
        is_group = "##[group]" in line
        if state == 0:
            if is_group and anchor in line and "##[group]Run " in line:
                state = 1
        elif state == 1:
            if "##[endgroup]" in line:
                state = 2
        elif is_group:
            break
        else:
            out.append(line)
    return out if state == 2 else None


def measurement_receipt(log: str) -> str:
    lines = step_output(log, MEASURE_ANCHOR)
    if not lines:
        return UNKNOWN
    text = "\n".join(lines)
    if re.search(r"HTTP 403|Resource not accessible", text):
        return DENIED
    if re.search(r"measurement from run \d+", text):
        return RECEIVED
    if "no prior measurement" in text:
        return NONE_YET
    return UNKNOWN


def _outside_script(log: str) -> list[str]:
    """Log lines that are not inside a `##[group]Run` block (i.e. not echoed source)."""
    out, inside = [], False
    for line in log.splitlines():
        if "##[group]Run " in line:
            inside = True
        elif "##[endgroup]" in line:
            inside = False
        elif not inside:
            out.append(line)
    return out


def close_reason(log: str, pr: int) -> tuple[str, str] | None:
    """Why did close-on-evidence not close for PR `pr`? (code, the log line.)"""
    rules = [
        ("denied", r"HTTP 403|Resource not accessible"),
        ("claims-no-issue", rf"PR #{pr} claims no issue(?! in its body)"),
        ("refs-declined", rf"PR #{pr} explicitly REFS|branch names #\d+ but the body refs it"),
        ("newer-deploy", r"live commit [0-9a-f]{7,} is not this run's"),
        ("no-build-sha", r"/health reports no build_sha"),
    ]
    lines = _outside_script(log)
    for code, pat in rules:
        for line in lines:
            if re.search(pat, line):
                return code, re.sub(r"^\S+Z\s+", "", line).strip()
    return None


# --------------------------------------------------------------------------- #
# pure helpers: agent PRs
# --------------------------------------------------------------------------- #

_CLOSING = re.compile(r"(?i)(?:clos(?:e|es|ed)|fix(?:e[sd])?|resolv(?:e|es|ed))\s+#(\d+)")
_REFS = re.compile(r"(?i)refs?\s+#(\d+)")


def claimed_issues(pr: dict) -> dict:
    """What close-on-evidence would do with this PR, mirrored from its shell.

    The patterns are copied from close-on-evidence.yml (closing keywords; `Refs #N`
    suppresses the branch-name fallback for N), and a test pins the workflow's
    literal grep so the two cannot drift apart silently.
    """
    text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
    closing = {int(n) for n in _CLOSING.findall(text)}
    refs = {int(n) for n in _REFS.findall(text)}
    m = re.match(r"issue/(\d+)", pr["head"]["ref"])
    branch = {int(m.group(1))} if m else set()
    refs_lines = [ln.strip() for ln in text.splitlines() if _REFS.search(ln)]
    return {"expected": sorted(closing | (branch - refs)),
            "declined": sorted((branch & refs) - closing),
            "refs_lines": refs_lines}


def blocker(pr: dict) -> tuple[str, str]:
    """(why this PR is not merged, kind). kind: definite | uncertain | pending."""
    names = {lbl["name"] for lbl in pr.get("labels", [])}
    if pr.get("draft"):
        return "it is still a draft", "definite"
    if "qa-fail" in names:
        return "QA failed it (qa-fail)", "definite"
    if "too-large-to-automerge" in names:
        return "it is labelled too-large-to-automerge", "definite"
    if "qa-pass" not in names:
        return "it has no qa-pass label", "definite"
    checks = pr.get("checks")
    if checks is None:
        return "its checks could not be read", "uncertain"
    if any(c.get("status") != "completed" for c in checks):
        return "its checks are still running", "pending"
    bad = sorted({c["name"] for c in checks if c.get("conclusion") in FAILED})
    if bad:
        return "check(s) failing: " + ", ".join(bad), "definite"
    if not checks:
        return "no checks reported", "definite"
    return "checks are green and qa-pass is present, so agent-merge did not act", "definite"


# --------------------------------------------------------------------------- #
# classifiers (pure: dicts in, Findings out)
# --------------------------------------------------------------------------- #

def classify_merge_legs(runs, gate_runs, label_events, window: Window) -> list[Finding]:
    """agent-merge fires on two signals and either can be the last to arrive. A leg
    that never succeeds is broken, not idle -- a working leg must not excuse it."""
    real = [r for r in _done(runs) if r.get("conclusion") != "skipped"]
    gates = [g for g in _done(gate_runs) if window.settled(g["updated_at"])]
    labels = [e for e in label_events if window.contains(e["created_at"]) and window.settled(e["created_at"])]
    legs = [("workflow_run", "pr-gates completion", len(gates)),
            ("pull_request_target", "qa-pass label", len(labels))]
    stat = {}
    for ev, _, _ in legs:
        rs = [r for r in real if r.get("event") == ev]
        stat[ev] = (rs, sum(1 for r in rs if r.get("conclusion") == "success"))
    out = []
    for ev, what, expected in legs:
        rs, ok = stat[ev]
        other = next(e for e in stat if e != ev)
        ors, ook = stat[other]
        loop = f"agent-merge {ev} leg"
        if rs and ok == 0:
            concl = ", ".join(sorted({r.get("conclusion") or "?" for r in rs}))
            tail = (f"; the {other} leg alone has been succeeding ({ook} of {len(ors)})"
                    if ook else "")
            out.append(Finding(loop, BROKEN,
                f"{loop}: {len(rs)} of {len(rs)} runs failed (conclusion: {concl}), 0 succeeded, "
                f"for {expected} {what}(s){tail}.", _refs(rs)))
        elif expected and not rs:
            out.append(Finding(loop, BROKEN,
                f"{loop}: {expected} {what}(s) in the window and 0 runs of this leg -- it never fired.", []))
        elif not expected and not rs:
            out.append(Finding(loop, IDLE, f"{loop}: no {what}s in the window, so nothing for it to do.", []))
        else:
            out.append(Finding(loop, OK,
                f"{loop}: {ok} of {len(rs)} runs succeeded for {expected} {what}(s).", []))
    return out


def classify_merge_outcome(prs, label_events, window: Window) -> Finding:
    """A PR carrying qa-pass, open, and old enough: agent-merge owed it a merge."""
    qa_at = {}
    for e in label_events:
        qa_at[e["pr"]] = max(qa_at.get(e["pr"], e["created_at"]), e["created_at"])
    stranded, uncertain, pending, merged, passed = [], [], 0, 0, 0
    for pr in prs:
        names = {lbl["name"] for lbl in pr.get("labels", [])}
        if pr.get("merged_at"):
            merged += window.contains(pr["merged_at"])
            passed += "qa-pass" in names and window.contains(pr["merged_at"])
            continue
        if pr["state"] != "open" or "qa-pass" not in names or "qa-fail" in names:
            continue
        passed += 1
        if not window.settled(qa_at.get(pr["number"], pr["updated_at"])):
            pending += 1
            continue
        why, kind = blocker(pr)
        if kind == "pending":
            pending += 1
        elif kind == "uncertain":
            uncertain.append(f"PR #{pr['number']}: {why}")
        else:
            stranded.append(f"PR #{pr['number']} ({pr['head']['ref']}): {why}")
    loop = "agent-merge outcome"
    if stranded:
        return Finding(loop, BROKEN,
            f"{loop}: {len(stranded)} PR(s) carry qa-pass and are still open -- " + "; ".join(stranded) + ".",
            stranded)
    if uncertain:
        return Finding(loop, UNKNOWN, f"{loop}: could not tell why " + "; ".join(uncertain) + ".", uncertain)
    if not passed:
        return Finding(loop, IDLE, f"{loop}: no agent PR carried qa-pass in the window.", [])
    note = f" ({pending} in flight, excluded)" if pending else ""
    return Finding(loop, OK, f"{loop}: {merged} agent PR(s) merged, none stranded{note}.", [])


def eligible_prs(prs, verify_runs, window: Window):
    """Merged agent PRs whose merge commit has a GREEN verify-production run: the
    exact condition close-on-evidence demands. Returns (eligible, no_run, red)."""
    eligible, no_run, red = [], [], []
    for pr in prs:
        if not pr.get("merged_at") or not window.merged_in(pr["merged_at"]):
            continue
        sha = pr["merge_commit_sha"]
        vr = [v for v in verify_runs if v["head_sha"] == sha and v.get("event") in ("push", "workflow_dispatch")]
        if any(v.get("conclusion") == "success" for v in vr):
            eligible.append(pr)
        elif not vr:
            no_run.append(pr)
        elif all(v.get("status") == "completed" for v in vr):
            red.append(pr)
    return eligible, no_run, red


def classify_last_mile(prs, verify_runs, window: Window) -> Finding:
    """agent-merge merges with GITHUB_TOKEN, and GitHub starts no push-triggered run
    for such a merge. agent-merge therefore dispatches verify-production itself;
    a merged PR with NO run on its commit means that hop failed, and
    close-on-evidence could never have fired for it."""
    loop = "agent-merge post-merge verification"
    by_bot = [p for p in prs if (p.get("merged_by") or {}).get("login") == BOT]
    _, no_run, red = eligible_prs(by_bot, verify_runs, window)
    total = len([p for p in by_bot if p.get("merged_at") and window.merged_in(p["merged_at"])])
    if not total:
        return Finding(loop, IDLE, f"{loop}: agent-merge merged nothing in the window.", [])
    if no_run:
        nums = ", ".join(f"#{p['number']}" for p in no_run)
        return Finding(loop, BROKEN,
            f"{loop}: {len(no_run)} of {total} PR(s) merged by agent-merge ({nums}) have no "
            f"verify-production run on their merge commit, so close-on-evidence could not fire for them.",
            [f"PR #{p['number']} merge commit {p['merge_commit_sha'][:7]}" for p in no_run])
    note = f" ({len(red)} verified RED, which closes nothing by design)" if red else ""
    return Finding(loop, OK, f"{loop}: all {total} agent merge(s) were followed by a verification run{note}.", [])


def classify_close(prs, verify_runs, close_runs, issue_events, window: Window,
                   logs_for: Callable[[], tuple[list[str], int]] = lambda: ([], 0)) -> Finding:
    """close-on-evidence: a green-verified merged PR claiming issue N should leave a
    `closed` event on N whose actor is the bot. Anything else is effect zero."""
    loop = "close-on-evidence"
    eligible, _, _ = eligible_prs(prs, verify_runs, window)
    owed, declined_ok, shortfalls = 0, [], []
    for pr in eligible:
        claim = claimed_issues(pr)
        for n in claim["expected"] + claim["declined"]:
            closer = next((e["actor"]["login"] for e in reversed(issue_events.get(n, []))
                           if e["event"] == "closed"), None)
            if n in claim["declined"]:
                if closer is None:
                    declined_ok.append(f"#{n} (PR #{pr['number']}: {' / '.join(claim['refs_lines'])})")
                    continue
                if closer == BOT:
                    continue
            elif closer == BOT:
                owed += 1
                continue
            owed += 1
            who = f"closed by {closer}, not by the loop" if closer else "still open"
            shortfalls.append((pr, n, who, claim))
    if not eligible:
        return Finding(loop, IDLE, f"{loop}: no merged agent PR had a green verification to act on.", [])
    if not shortfalls:
        note = f"; {len(declined_ok)} deliberately declined via Refs" if declined_ok else ""
        return Finding(loop, OK, f"{loop}: {owed} issue(s) owed a close, all closed by the loop{note}.", declined_ok)
    texts, unreadable = logs_for()
    done_runs = _done(close_runs)
    evidence, bits = [], []
    for pr, n, who, claim in shortfalls:
        reason = next((r for r in (close_reason(t, pr["number"]) for t in texts) if r), None)
        if reason:
            why = f"log says: {reason[0]} ({reason[1]})"
        elif not any(r.get("conclusion") == "success" for r in done_runs):
            why = "close-on-evidence has no successful run (" + ", ".join(
                sorted({r.get("conclusion") or "?" for r in done_runs}) or ["no runs"]) + ")"
        else:
            why = "reason unknown (log unreadable or silent)" if unreadable or not texts else "reason not in its log"
        refs = f" PR body says {' / '.join(claim['refs_lines'])!r}" if claim["refs_lines"] else ""
        bits.append(f"#{n} (PR #{pr['number']} merged, verification green, issue {who}; {why})")
        evidence.append(f"#{n}: PR #{pr['number']} branch {pr['head']['ref']} -- {who};{refs}")
    return Finding(loop, BROKEN,
        f"{loop}: {len(shortfalls)} of {owed} issue(s) were not closed by the loop -- " + "; ".join(bits) + ".",
        evidence)


def classify_receipts(loop: str, receipts: list[tuple[int, str]], measure_successes: int) -> Finding:
    """Did the run actually RECEIVE the analyst's measurement? The fetch step is
    continue-on-error, so a 403 there leaves the run green. Only the log knows."""
    name = f"{loop} measurement receipt"
    n = len(receipts)
    if not n:
        return Finding(name, IDLE, f"{name}: no completed runs to receive one.", [])
    count = lambda k: [r for r, v in receipts if v == k]  # noqa: E731
    denied, none_yet, unknown, got = count(DENIED), count(NONE_YET), count(UNKNOWN), count(RECEIVED)
    ev = [f"run {r}: {v}" for r, v in receipts][:8]
    if denied:
        return Finding(name, BROKEN,
            f"{name}: delivery received no measurement in {n - len(got)} of {n} runs -- "
            f"{len(denied)} fetch(es) were refused (HTTP 403), yet the runs concluded success.", ev)
    if none_yet and measure_successes:
        return Finding(name, BROKEN,
            f"{name}: delivery received no measurement in {n - len(got)} of {n} runs -- "
            f"{len(none_yet)} said 'no prior measurement' while agent-measure had "
            f"{measure_successes} successful run(s).", ev)
    if unknown:
        return Finding(name, UNKNOWN,
            f"{name}: could not read the fetch step's log for {len(unknown)} of {n} runs.", ev)
    if none_yet == [r for r, _ in receipts]:
        return Finding(name, IDLE, f"{name}: agent-measure has no successful run yet, so there was nothing to receive.", ev)
    return Finding(name, OK, f"{name}: {len(got)} of {n} runs received a measurement.", ev)


def classify_work(runs, prs, traces, window: Window) -> Finding:
    """agent-work: each nightly run should end in a merged PR -- or leave a trace
    that it stopped at step 0 on purpose. A green run with neither is the defect."""
    loop = "agent-work"
    attempts = [r for r in _done(runs) if r.get("event") in ("schedule", "workflow_dispatch")
                and window.settled(r["updated_at"])]
    if not attempts:
        return Finding(loop, IDLE, f"{loop}: no completed runs in the window.", [])
    merged, idle, bad = [], [], []
    for r in attempts:
        start = ts(r.get("run_started_at") or r["created_at"])
        end = ts(r["updated_at"]) + RUN_PAD
        if r.get("conclusion") != "success":
            bad.append(f"run {r['id']} concluded {r.get('conclusion')}")
            continue
        mine = [p for p in prs if start <= ts(p["created_at"]) <= end]
        mine = [p for p in mine if window.settled(p["created_at"])]
        if any(p.get("merged_at") for p in mine):
            merged.append(r)
        elif mine:
            p = mine[0]
            why = "closed without merging" if p["state"] == "closed" else "not merged: " + blocker(p)[0]
            if p["state"] == "open" and blocker(p)[1] == "pending":
                merged.append(r)       # checks still running: in flight, not failed
            else:
                bad.append(f"run {r['id']} opened PR #{p['number']} but it is {why}")
        elif any(start <= ts(t["at"]) <= end for t in traces):
            idle.append(r)
        else:
            bad.append(f"run {r['id']} concluded success with no PR and no cannot-reproduce/needs-evidence trace")
    parts = [f"{len(merged)} merged a PR", f"{len(idle)} stopped on purpose at step 0"]
    if bad:
        return Finding(loop, BROKEN,
            f"{loop}: {len(bad)} of {len(attempts)} runs produced no merged PR -- " + "; ".join(bad) + ".", bad)
    verdict = OK if merged else IDLE
    return Finding(loop, verdict, f"{loop}: {len(attempts)} runs: " + ", ".join(parts) + ".", [])


def classify_report_loop(loop: str, runs, commits, window: Window, issues_created=None) -> Finding:
    """A report IS the contract for measure/discover/design, so a run that
    concludes success without committing one is never 'idle'. Caveat, accepted:
    the persist step skips an UNCHANGED report, which reads as no commit."""
    attempts = [r for r in _done(runs) if window.settled(r["updated_at"])]
    if not attempts:
        return Finding(loop, IDLE, f"{loop}: no completed runs in the window.", [])
    nothing, failed = [], []
    for r in attempts:
        start = ts(r.get("run_started_at") or r["created_at"])
        end = ts(r["updated_at"]) + RUN_PAD
        if r.get("conclusion") != "success":
            failed.append(f"run {r['id']} concluded {r.get('conclusion')}")
        elif not any(start <= ts(c["commit"]["committer"]["date"]) <= end for c in commits):
            nothing.append(f"run {r['id']}")
    if failed or nothing:
        bits = failed + [f"{x} concluded success but produced nothing (no commit touching "
                         f"{REPORT_PATH[loop]}; or the report was unchanged)" for x in nothing]
        return Finding(loop, BROKEN, f"{loop}: {len(failed) + len(nothing)} of {len(attempts)} runs produced "
                       "no report -- " + "; ".join(bits) + ".", bits)
    if issues_created == 0:
        return Finding(loop, IDLE, f"{loop}: {len(attempts)} report(s) committed, 0 issues filed (no findings).", [])
    return Finding(loop, OK, f"{loop}: {len(attempts)} report(s) committed.", [])


def classify_schedule(loop: str, runs, window: Window) -> Finding:
    need = int(MIN_RUNS[loop] * window.days / 7)
    name = f"{loop} schedule"
    if len(runs) < need:
        return Finding(name, BROKEN,
            f"{name}: schedule not firing -- {len(runs)} run(s) in {window.days:.1f} days, expected at least {need}.", [])
    return Finding(name, OK, f"{name}: {len(runs)} run(s), at least {need} expected.", [])


# --------------------------------------------------------------------------- #
# fetching: Source -> the dicts the classifiers take
# --------------------------------------------------------------------------- #

def list_runs(src: Source, loop: str, window: Window) -> list[dict]:
    d = src.get(f"actions/workflows/{WORKFLOW[loop]}/runs?per_page=100"
                f"&created={iso(window.since)}..{iso(window.until)}", paginate=True)
    return d["workflow_runs"] if isinstance(d, dict) else d


def agent_prs(src: Source, window: Window) -> list[dict]:
    """Agent PRs touched in the window, in full (the list payload lacks merged_by).
    First 100 by recent update only: a week of agent work is a handful."""
    listing = src.get("pulls?state=all&sort=updated&direction=desc&per_page=100")
    return [src.get(f"pulls/{p['number']}") for p in listing
            if p["head"]["ref"].startswith("issue/") and ts(p["updated_at"]) >= window.since]


def with_checks(src: Source, prs: list[dict]) -> list[dict]:
    for pr in prs:
        if pr["state"] == "open" and "checks" not in pr:
            try:
                pr["checks"] = src.get(f"commits/{pr['head']['sha']}/check-runs?per_page=100")["check_runs"]
            except ApiError:
                pr["checks"] = None
    return prs


def qa_pass_events(src: Source, prs: list[dict]) -> list[dict]:
    out = []
    for pr in prs:
        for e in src.get(f"issues/{pr['number']}/events?per_page=100", paginate=True):
            if e["event"] == "labeled" and e["label"]["name"] == "qa-pass":
                out.append({"pr": pr["number"], "created_at": e["created_at"]})
    return out


def run_receipt(src: Source, run_id: int) -> tuple[str, str]:
    """(receipt, note). A log that cannot be read is UNKNOWN, never RECEIVED."""
    try:
        for job in src.get(f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]:
            if job.get("conclusion") == "skipped":
                continue
            receipt = measurement_receipt(src.text(f"actions/jobs/{job['id']}/logs"))
            if receipt != UNKNOWN:
                return receipt, ""
        return UNKNOWN, "no job log contained the measurement-fetch step"
    except ApiError as e:
        return UNKNOWN, str(e)


def receipts_for(src: Source, runs: list[dict], window: Window) -> list[tuple[int, str]]:
    return [(r["id"], run_receipt(src, r["id"])[0]) for r in _done(runs)
            if window.settled(r["updated_at"])][:14]


def check_merge(src, window):
    runs = list_runs(src, "agent-merge", window)
    gates = [g for g in list_runs(src, "pr-gates", window)
             if g.get("event") == "pull_request" and g["head_branch"].startswith("issue/")]
    prs = with_checks(src, agent_prs(src, window))
    labels = qa_pass_events(src, prs)
    verify = list_runs(src, "verify-production", window)
    return [*classify_merge_legs(runs, gates, labels, window),
            classify_merge_outcome(prs, labels, window),
            classify_last_mile(prs, verify, window)]


def check_close(src, window):
    prs = agent_prs(src, window)
    verify = list_runs(src, "verify-production", window)
    close_runs = list_runs(src, "close-on-evidence", window)
    eligible, _, _ = eligible_prs(prs, verify, window)
    events = {}
    for pr in eligible:
        claim = claimed_issues(pr)
        for n in claim["expected"] + claim["declined"]:
            events[n] = src.get(f"issues/{n}/events?per_page=100", paginate=True)

    def logs_for():
        texts, unreadable = [], 0
        for r in sorted(_done(close_runs), key=lambda r: r["created_at"], reverse=True)[:8]:
            try:
                for job in src.get(f"actions/runs/{r['id']}/jobs?per_page=100")["jobs"]:
                    if job.get("conclusion") != "skipped":
                        texts.append(src.text(f"actions/jobs/{job['id']}/logs"))
            except ApiError:
                unreadable += 1
        return texts, unreadable

    return [classify_close(prs, verify, close_runs, events, window, logs_for)]


def traces_in(src: Source, window: Window) -> list[dict]:
    """Evidence that agent-work stopped at step 0 ON PURPOSE: a bot comment or a
    label saying cannot-reproduce / needs-evidence. First 100 of each only."""
    out = []
    for c in src.get(f"issues/comments?since={iso(window.since)}&per_page=100"):
        if c["user"]["type"] == "Bot" and LEGIT_STOP.search(c.get("body") or ""):
            out.append({"at": c["created_at"], "what": "comment"})
    for e in src.get("issues/events?per_page=100"):
        if e["event"] == "labeled" and LEGIT_STOP.search(e["label"]["name"]):
            out.append({"at": e["created_at"], "what": "label"})
    return out


def check_work(src, window):
    runs = list_runs(src, "agent-work", window)
    prs = with_checks(src, agent_prs(src, window))
    measures = sum(1 for r in list_runs(src, "agent-measure", window) if r.get("conclusion") == "success")
    return [classify_schedule("agent-work", runs, window),
            classify_work(runs, prs, traces_in(src, window), window),
            classify_receipts("agent-work", receipts_for(src, runs, window), measures)]


def check_report(loop: str):
    def check(src, window):
        runs = list_runs(src, loop, window)
        commits = src.get(f"commits?path={REPORT_PATH[loop]}&since={iso(window.since)}"
                          f"&until={iso(window.until)}&per_page=100")
        out = [classify_schedule(loop, runs, window)]
        issues = None
        if loop == "agent-discover":
            issues = sum(1 for i in src.get(f"issues?state=all&since={iso(window.since)}&per_page=100")
                         if "pull_request" not in i and i["user"]["type"] == "Bot"
                         and window.contains(i["created_at"]))
        out.append(classify_report_loop(loop, runs, commits, window, issues))
        if loop == "agent-discover":
            measures = sum(1 for r in list_runs(src, "agent-measure", window) if r.get("conclusion") == "success")
            out.append(classify_receipts(loop, receipts_for(src, runs, window), measures))
        return out
    return check


# A loop cannot silently drop out of the report: this table is pinned by a test.
LOOPS: dict[str, Callable] = {
    "agent-merge": check_merge,
    "close-on-evidence": check_close,
    "agent-work": check_work,
    "agent-measure": check_report("agent-measure"),
    "agent-discover": check_report("agent-discover"),
    "agent-design": check_report("agent-design"),
}


def run_all(src: Source, window: Window) -> list[Finding]:
    src = MemoSource(src)
    out = []
    for name, check in LOOPS.items():
        try:
            out.extend(check(src, window))
        except ApiError as e:
            out.append(Finding(name, UNKNOWN, f"{name}: could not read the evidence -- {e}.", []))
        except Exception as e:  # noqa: BLE001 -- a report bug must not look like a green loop
            out.append(Finding(name, UNKNOWN,
                f"{name}: the report itself failed ({type(e).__name__}: {e}).", []))
    return out


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #

def render_md(findings: list[Finding], window: Window) -> str:
    n = {v: sum(f.verdict == v for f in findings) for v in (BROKEN, UNKNOWN, OK, IDLE)}
    lines = [f"# Loop outcome report {iso(window.since)} .. {iso(window.until)}", "",
             f"**{n[BROKEN]} BROKEN, {n[UNKNOWN]} UNKNOWN, {n[OK]} OK, {n[IDLE]} IDLE.** "
             "UNKNOWN means the evidence could not be read; it is not a pass.", ""]
    for title, verdicts in (("Produced nothing, or broke", (BROKEN,)),
                            ("Could not be read", (UNKNOWN,)),
                            ("Fine", (OK, IDLE))):
        rows = [f for f in findings if f.verdict in verdicts]
        if not rows:
            continue
        lines += [f"## {title}", ""]
        for f in rows:
            lines.append(f"- **{f.verdict}** {f.sentence}")
            lines += [f"    - {e}" for e in f.evidence]
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since", help="ISO date/time; default 7 days before --until")
    ap.add_argument("--until", help="ISO date/time; default now. A date-only value means midnight at the "
                                    "START of that day: use --until 2026-10-10 to include 2026-10-09")
    ap.add_argument("--out", help="directory for report.md and findings.json")
    ap.add_argument("--fixtures", nargs="+", help="read fixture dirs instead of the network (earlier overrides later)")
    ap.add_argument("--repo", default=os.environ.get("GH_REPO", "mahAnuj/astro-ai"))
    a = ap.parse_args(argv)
    until = parse_when(a.until) if a.until else datetime.now(timezone.utc)
    since = parse_when(a.since) if a.since else until - timedelta(days=7)
    window = Window(since, until)
    src = FixtureSource([Path(d) for d in a.fixtures]) if a.fixtures else GhSource(a.repo)

    findings = run_all(src, window)
    md = render_md(findings, window)
    print(md)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.md").write_text(md)
        (out / "findings.json").write_text(json.dumps([asdict(f) for f in findings], indent=2))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write(md + "\n")
    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(main())
