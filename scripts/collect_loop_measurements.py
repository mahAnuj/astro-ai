#!/usr/bin/env python3
"""Commit what the delivery loop produced, and what the team costs (#338, slice 1 of #335).

WHY THIS EXISTS
---------------
`report_loop_outcomes.py` judges per-LEG health and writes a 90-day Actions
artifact plus markdown on one issue -- neither is readable by a page, and the
artifact expires. #335's ops page needs per-CYCLE rows it can fetch. This writes
two files that `agent-measure`'s `commit` job commits under `measurements/`
(which the Cloud Build trigger ignores, so the push deploys nothing):

  measurements/loop.json   one row per completed `agent-work` run
  measurements/cost.json   one row per vendor, from the RATES table below

ZERO LLM CALLS on any path. Deterministic Python against the GitHub API.

HOW A RUN IS ATTRIBUTED -- from its own record, never from timestamps
---------------------------------------------------------------------
Three tiers, and every row says which one it came from (`attribution`):

  receipt        `agent-work.yml`'s last step prints
                   LOOP-RECEIPT issue=<n|none> branch=<name> pr=<n|none>
                 The run states what it worked and what PR it ended with.
  log            Runs from before the receipt. The net step ("Push the branch
                 and open the PR") already printed one of a few lines naming
                 the branch ("<branch> already on origin", "no commits on
                 <branch>", "on '<branch>', not an issue branch", "branch '<b>'
                 set up to track"). The branch gives the issue; the PR is then
                 looked up BY BRANCH NAME. Still the run's own output.
  unattributed   Neither is in the log (the run died before the net step, or the
                 log expired). issue/pr are null. NO time-window guess is made:
                 that heuristic is what this issue exists to replace, and a
                 wrong attribution looks exactly like a right one.

Only what follows `##[endgroup]` is read. The group header echoes the step's
SCRIPT SOURCE, so a naive search would find the words in the source (see
`report_loop_outcomes.step_output`, which burned this repo once). The receipt
is printed with `printf '...%s'` so the echoed source cannot match the reader's
regex either; a test pins both halves.

OUTCOME, in order (the first rule that applies wins)
----------------------------------------------------
  PR merged                                    shipped
  PR open                                      pr open
  PR closed, not merged                        failed
  no PR, run did not conclude success          failed
  no PR, success, the run's OWN record says so  nothing
  anything else                                unknown

"The run's own record says so" is a receipt with `pr=none`, or, for a legacy run,
the net step's "no commits on <branch>" / "not an issue branch". Those are
observations that nothing was pushed, not inferences. Looking a PR up by that
branch name instead would hand the run a PR a LATER run opened: runs 37734421636
and 37735035844 printed "no commits on issue/272-..." and PR #292 on that branch
shipped two hours afterwards.

`unknown` is deliberately an extra value beyond the brief's four. A green run
whose log could not be read, or a legacy run whose log named no branch, is not
`nothing` -- calling it that is a claim we cannot back, and it is the shape of
the silent-success defects #316 was written to find. It is never green.

A run whose conclusion is `failure` but whose rescue step still opened a merged
PR is `shipped`: the PR is the effect; the conclusion is kept in its own field.

KNOWN LIMIT: several runs can work one issue branch, so several rows can name
the same PR, and each reads `shipped` once it merges. Count distinct `pr` values,
not rows, when asking how many PRs landed.

ROWS ARE FROZEN once settled. Only a row whose PR is still `pr open` (or whose
PR lookup failed) is re-read, and then only the PR, never the log.

ENDPOINTS READ, AND THE GITHUB_TOKEN SCOPE EACH NEEDS
-----------------------------------------------------
`verify_workflows.py` cannot see `gh` calls made inside a script, so this table
is the only place the requirement is written down; a test asserts the `commit`
job in agent-measure.yml grants exactly these.

  actions/workflows/agent-work.yml/runs, actions/runs/{id}/jobs,
  actions/jobs/{id}/logs ........................ actions: read
  pulls, pulls/{n} .............................. pull-requests: read

(`contents: write` on that job is for the push, not for any read here.)

Job logs contain terminal escape sequences, and `gh api` REFUSES to print a
response containing them unless given `--allow-escape-sequences` (measured
2026-10-13, gh 2.102.0: all 22 logs failed without it). `report_loop_outcomes`'s
`GhSource.text` does not pass it; `LogSource` below does.

EXIT CODES: 0 wrote the files; 1 the document was invalid (NOTHING written, the
old files stand) or the run could not proceed.

    python3 scripts/collect_loop_measurements.py --out measurements
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_loop_outcomes import (  # noqa: E402
    ApiError, GhSource, MemoSource, Source, Window, _outside_script, iso, list_runs, ts,
)

WORKFLOW_NAME = "agent-work"
LOOKBACK = timedelta(days=14)     # runs listed per collection
RETAIN = timedelta(days=120)      # rows older than this are pruned

OUTCOMES = ("shipped", "pr open", "nothing", "failed", "unknown")
ATTRIBUTIONS = ("receipt", "log", "unattributed")
LOOP_FIELDS = ("run", "workflow", "date", "started", "trigger", "conclusion", "minutes",
               "issue", "pr", "pr_merged", "outcome", "attribution")
COST_FIELDS = ("item", "vendor", "monthly_usd", "basis", "status", "note")
FIGURE_STATUSES = ("known", "free-tier")

# The reader half of the receipt. The WRITER is `printf 'LOOP-RECEIPT issue=%s ...'`
# in agent-work.yml; `%s` can never satisfy `\d+|none`, so the echoed source of
# that step cannot match.
RECEIPT = re.compile(r"LOOP-RECEIPT issue=(\d+|none) branch=(\S+) pr=(\d+|none)")

# What the net step already printed before the receipt existed. Each captures a
# branch. Searched only OUTSIDE `##[group]Run` blocks.
NET_LINES = (
    (re.compile(r"(\S+) already on origin"), False),
    (re.compile(r"no commits on (\S+)"), True),
    (re.compile(r"on '([^']*)', not an issue branch"), True),
    # Only an issue/ branch: actions/checkout prints the same sentence for `main`,
    # and a search that took the first hit read every run as "ended on main".
    (re.compile(r"branch '(issue/\S+)' set up to track"), False),
)
BRANCH_ISSUE = re.compile(r"issue/(\d+)")


# --------------------------------------------------------------------------- #
# cost: the single source of truth
# --------------------------------------------------------------------------- #

# monthly_usd is None where NO figure can be read. Never 0 for an unknown: a
# zero here would make every total wrong and look deliberate. There is no
# `total` field and no timestamp, so an unchanged table produces no commit.
RATES = (
    {"item": "Claude Max 5x", "vendor": "Anthropic", "monthly_usd": 100, "basis": "flat monthly subscription",
     "status": "known",
     "note": "Owner-confirmed 2026-10-13. Funds every claude-code-action run; per-run cost is not separable."},
    {"item": "GitHub Actions", "vendor": "GitHub", "monthly_usd": 0, "basis": "public repository",
     "status": "known",
     "note": "Unlimited minutes for a public repo since 2026-10-12 (stated in #338)."},
    {"item": "Groq", "vendor": "Groq", "monthly_usd": 0, "basis": "free tier",
     "status": "free-tier",
     "note": "8,000 TPM per model. The paid fallthrough is OpenAI, below."},
    {"item": "Google Analytics 4", "vendor": "Google", "monthly_usd": 0, "basis": "free tier",
     "status": "free-tier", "note": ""},
    {"item": "Search Console", "vendor": "Google", "monthly_usd": 0, "basis": "free tier",
     "status": "free-tier", "note": ""},
    {"item": "Google Cloud (Cloud Run, GCS, Cloud Build)", "vendor": "Google", "monthly_usd": None,
     "basis": "no figure readable", "status": "awaiting billing export",
     "note": "No BigQuery billing export on bhagya-500701 and no gcloud command returns spend."},
    {"item": "OpenAI", "vendor": "OpenAI", "monthly_usd": None, "basis": "no figure readable",
     "status": "no usage source read",
     "note": "Paid safety net at the end of the LLM chain; its spend is not read by anything here."},
)


def build_cost() -> dict:
    return {"rows": [dict(r) for r in RATES]}


# --------------------------------------------------------------------------- #
# validation: nothing is written unless these return []
# --------------------------------------------------------------------------- #

def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate_loop(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["document is not an object"]
    errs = []
    if not isinstance(doc.get("generated_at"), str) or not doc["generated_at"]:
        errs.append("generated_at missing")
    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        return errs + ["rows is empty or not a list"]
    seen = set()
    for i, r in enumerate(rows):
        where = f"rows[{i}]"
        if not isinstance(r, dict):
            errs.append(f"{where} is not an object")
            continue
        if set(r) != set(LOOP_FIELDS):
            errs.append(f"{where} fields differ: missing {sorted(set(LOOP_FIELDS) - set(r))} "
                        f"extra {sorted(set(r) - set(LOOP_FIELDS))}")
            continue
        if not _is_int(r["run"]) or r["run"] in seen:
            errs.append(f"{where} run is not a unique int")
        seen.add(r["run"])
        for k in ("workflow", "trigger", "conclusion", "started"):
            if not isinstance(r[k], str) or not r[k]:
                errs.append(f"{where} {k} is not a non-empty string")
        if not (isinstance(r["date"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])):
            errs.append(f"{where} date is not YYYY-MM-DD")
        if isinstance(r["minutes"], bool) or not isinstance(r["minutes"], (int, float)) or r["minutes"] < 0:
            errs.append(f"{where} minutes is not a number >= 0")
        for k in ("issue", "pr"):
            if r[k] is not None and not _is_int(r[k]):
                errs.append(f"{where} {k} is neither null nor an int")
        if r["pr_merged"] not in (True, False, None):
            errs.append(f"{where} pr_merged is not true/false/null")
        if r["outcome"] not in OUTCOMES:
            errs.append(f"{where} outcome {r['outcome']!r} not in {OUTCOMES}")
        if r["attribution"] not in ATTRIBUTIONS:
            errs.append(f"{where} attribution {r['attribution']!r} not in {ATTRIBUTIONS}")
        # An outcome that its own fields contradict is the claim-without-evidence
        # this file exists to avoid.
        if r["outcome"] == "shipped" and not (r["pr"] and r["pr_merged"] is True):
            errs.append(f"{where} shipped without a merged PR")
        if r["outcome"] == "pr open" and not (r["pr"] and r["pr_merged"] is False):
            errs.append(f"{where} 'pr open' without an unmerged PR")
        if r["outcome"] == "nothing" and (r["pr"] is not None or r["attribution"] == "unattributed"):
            errs.append(f"{where} 'nothing' needs the run's own record of no PR")
        if r["attribution"] == "unattributed" and (r["issue"] is not None or r["pr"] is not None):
            errs.append(f"{where} unattributed but names an issue/pr")
        if r["attribution"] == "unattributed" and r["outcome"] not in ("failed", "unknown"):
            errs.append(f"{where} unattributed but outcome is {r['outcome']!r}")
    return errs


def validate_cost(doc) -> list[str]:
    if not isinstance(doc, dict) or not isinstance(doc.get("rows"), list) or not doc["rows"]:
        return ["cost document has no rows"]
    errs = []
    for i, r in enumerate(doc["rows"]):
        where = f"rows[{i}]"
        if not isinstance(r, dict) or set(r) != set(COST_FIELDS):
            errs.append(f"{where} fields are not exactly {COST_FIELDS}")
            continue
        for k in ("item", "vendor", "basis"):
            if not isinstance(r[k], str) or not r[k].strip():
                errs.append(f"{where} {k} is empty")
        if not isinstance(r["note"], str):
            errs.append(f"{where} note is not a string")
        usd, status = r["monthly_usd"], r["status"]
        if not isinstance(status, str) or not status.strip():
            errs.append(f"{where} {r.get('item')!r} has no status")
        elif usd is None:
            # A null must say WHY, and "known"/"free-tier" are claims of a figure.
            if status in FIGURE_STATUSES:
                errs.append(f"{where} {r['item']!r} is null but status {status!r} claims a figure")
        elif isinstance(usd, bool) or not isinstance(usd, (int, float)) or usd < 0:
            errs.append(f"{where} {r['item']!r} monthly_usd is not null or a number >= 0")
        elif status not in FIGURE_STATUSES:
            # The rule the issue states: a zero (or any figure) standing on an
            # explanation instead of a basis is an unknown dressed as a number.
            errs.append(f"{where} {r['item']!r} has a figure ({usd}) with status {status!r}; "
                        f"a figure needs one of {FIGURE_STATUSES}")
        elif status == "free-tier" and usd != 0:
            errs.append(f"{where} {r['item']!r} is free-tier but costs {usd}")
    return errs


# --------------------------------------------------------------------------- #
# reading: Source -> attribution
# --------------------------------------------------------------------------- #

class LogSource(GhSource):
    """GhSource whose `text()` can read job logs. See the module header: without
    --allow-escape-sequences gh refuses every one. An older gh that does not know
    the flag is retried without it, so the failure stays 'could not read'."""

    def text(self, path: str) -> str:
        try:
            return self._run(path, ["--allow-escape-sequences"])
        except ApiError as e:
            if "unknown flag" in e.message:
                return self._run(path, [])
            raise


def parse_receipt(log: str):
    """(issue|None, branch|None, pr|None) from the LAST receipt line, or None."""
    found = RECEIPT.findall(log)
    if not found:
        return None
    issue, branch, pr = found[-1]
    return (int(issue) if issue != "none" else None,
            None if branch == "none" else branch,
            int(pr) if pr != "none" else None)


def parse_net_line(log: str):
    """(branch, no_pr) from the net step's own output, or None. Echoed source is
    skipped. `no_pr` is True when the line itself says nothing was pushed."""
    lines = _outside_script(log)
    for pat, no_pr in NET_LINES:     # in priority order: the first pattern with a hit wins
        for line in lines:
            m = pat.search(line)
            if m:
                return m.group(1), no_pr
    return None


def job_logs(src: Source, run_id: int) -> list[str]:
    """Every non-skipped job's log. An unreadable one raises ApiError."""
    out = []
    for job in src.get(f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]:
        if job.get("conclusion") != "skipped":
            out.append(src.text(f"actions/jobs/{job['id']}/logs"))
    return out


def pr_for_branch(src: Source, owner: str, branch: str, run_end: datetime):
    """Newest PR on `branch` that existed when the run ended, or None.

    The branch name comes from the run's own log, so this is a lookup, not a
    guess. The cut-off matters because branches are REUSED: issue/255-... carries
    PR #328 (opened 10-11) and #330 (opened 10-13 by a later run), and the newest
    PR overall is the wrong answer for the runs in between."""
    prs = src.get(f"pulls?head={owner}:{branch}&state=all&per_page=100")
    seen = [p["number"] for p in prs if ts(p["created_at"]) <= run_end]
    return max(seen, default=None)


def attribute(src: Source, run: dict, owner: str) -> dict:
    """{'issue','pr','attribution','no_pr_recorded'} for one run. Raises ApiError
    for a transient read failure so the caller can defer rather than freeze a guess."""
    logs = job_logs(src, run["id"])
    for log in logs:
        got = parse_receipt(log)
        if got:
            issue, branch, pr = got
            if issue is None and branch:
                m = BRANCH_ISSUE.match(branch)
                issue = int(m.group(1)) if m else None
            return {"issue": issue, "pr": pr, "attribution": "receipt", "no_pr_recorded": pr is None}
    for log in logs:
        got = parse_net_line(log)
        if got:
            branch, no_pr = got
            m = BRANCH_ISSUE.match(branch)
            issue = int(m.group(1)) if m else None     # "on 'main'": ended without a branch
            pr = None if (no_pr or not m) else pr_for_branch(src, owner, branch, ts(run["updated_at"]))
            return {"issue": issue, "pr": pr, "attribution": "log", "no_pr_recorded": no_pr}
    return {"issue": None, "pr": None, "attribution": "unattributed", "no_pr_recorded": False}


def outcome_of(conclusion: str, pr: int | None, merged: bool | None, state: str | None,
               attribution: str, no_pr_recorded: bool) -> str:
    if pr is not None and merged is True:
        return "shipped"
    if pr is not None and state == "open":
        return "pr open"
    if pr is not None and state == "closed":
        return "failed"
    if pr is None and conclusion != "success":
        return "failed"
    if pr is None and attribution != "unattributed" and no_pr_recorded:
        return "nothing"
    return "unknown"


def read_pr(src: Source, pr: int):
    """(state, merged) or (None, None) when the PR cannot be read."""
    try:
        d = src.get(f"pulls/{pr}")
    except ApiError:
        return None, None
    return d.get("state"), bool(d.get("merged_at") or d.get("merged"))


def _minutes(run: dict) -> float:
    start = ts(run.get("run_started_at") or run["created_at"])
    return round(max((ts(run["updated_at"]) - start).total_seconds(), 0) / 60, 1)


def make_row(run: dict, a: dict, state, merged) -> dict:
    started = run.get("run_started_at") or run["created_at"]
    pr = a["pr"]
    unreadable_pr = pr is not None and state is None
    return {
        "run": run["id"], "workflow": WORKFLOW_NAME, "date": iso(ts(started))[:10], "started": iso(ts(started)),
        "trigger": run.get("event") or "unknown", "conclusion": run.get("conclusion") or "unknown",
        "minutes": _minutes(run), "issue": a["issue"], "pr": pr,
        "pr_merged": None if (pr is None or unreadable_pr) else merged,
        "outcome": "unknown" if unreadable_pr else outcome_of(
            run.get("conclusion") or "unknown", pr, merged, state, a["attribution"], a["no_pr_recorded"]),
        "attribution": a["attribution"],
    }


def reopen(row: dict) -> bool:
    """Frozen unless the PR can still change, or could not be read last time."""
    return row["pr"] is not None and (row["outcome"] == "pr open" or row["pr_merged"] is None)


# --------------------------------------------------------------------------- #
# the collection
# --------------------------------------------------------------------------- #

def collect(src: Source, existing: dict | None, now: datetime, owner: str):
    """(document, stats). Pure given `src`; the caller validates and writes."""
    src = MemoSource(src)
    old = {r["run"]: r for r in (existing or {}).get("rows", []) if isinstance(r, dict) and "run" in r}
    stats = {"new": 0, "refreshed": 0, "frozen": 0, "deferred": 0, "pruned": 0, "pending": 0}
    merged_rows = dict(old)
    for run in list_runs(src, WORKFLOW_NAME, Window(now - LOOKBACK, now)):
        if run.get("status") != "completed":
            stats["pending"] += 1
            continue
        prev = old.get(run["id"])
        try:
            if prev is not None and not reopen(prev):
                stats["frozen"] += 1
                continue
            if prev is not None:      # only the PR can have moved
                a = {"issue": prev["issue"], "pr": prev["pr"], "attribution": prev["attribution"],
                     "no_pr_recorded": False}
                state, merged = read_pr(src, prev["pr"])
                merged_rows[run["id"]] = make_row(run, a, state, merged)
                stats["refreshed"] += 1
                continue
            try:
                a = attribute(src, run, owner)
            except ApiError as e:
                # An expired or removed log never comes back: settle it. Anything
                # else (403, 5xx) may be transient, so write nothing and retry
                # tomorrow rather than freeze an `unattributed` that is really
                # "could not read".
                if e.status in (404, 410):
                    a = {"issue": None, "pr": None, "attribution": "unattributed", "no_pr_recorded": False}
                else:
                    stats["deferred"] += 1
                    print(f"::warning::run {run['id']}: {e}", file=sys.stderr)
                    continue
            state, merged = (read_pr(src, a["pr"]) if a["pr"] is not None else (None, None))
            merged_rows[run["id"]] = make_row(run, a, state, merged)
            stats["new"] += 1
        except ApiError as e:
            stats["deferred"] += 1
            print(f"::warning::run {run['id']}: {e}", file=sys.stderr)
    floor = iso(now - RETAIN)
    kept = {k: v for k, v in merged_rows.items() if v["started"] >= floor}
    stats["pruned"] = len(merged_rows) - len(kept)
    rows = sorted(kept.values(), key=lambda r: r["started"], reverse=True)
    return {"generated_at": iso(now), "rows": rows}, stats


def dump(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="measurements", help="directory holding loop.json and cost.json")
    ap.add_argument("--repo", default=os.environ.get("GH_REPO", "mahAnuj/astro-ai"))
    a = ap.parse_args(argv)
    out = Path(a.out)

    cost = build_cost()
    bad = validate_cost(cost)
    if bad:
        print("INVALID cost.json, nothing written:\n  " + "\n  ".join(bad), file=sys.stderr)
        return 1

    existing = None
    try:
        existing = json.loads((out / "loop.json").read_text())
    except (OSError, ValueError):
        pass        # first run, or an unreadable file we are about to replace

    now = datetime.now(timezone.utc)
    try:
        doc, stats = collect(LogSource(a.repo), existing, now, a.repo.split("/")[0])
    except ApiError as e:
        print(f"could not list runs, nothing written: {e}", file=sys.stderr)
        return 1
    bad = validate_loop(doc)
    if bad:
        print("INVALID loop.json, nothing written:\n  " + "\n  ".join(bad[:20]), file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    (out / "loop.json").write_text(dump(doc))
    (out / "cost.json").write_text(dump(cost))
    by = {}
    for r in doc["rows"]:
        by[r["outcome"]] = by.get(r["outcome"], 0) + 1
    print(f"loop.json: {len(doc['rows'])} rows {by}; {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
