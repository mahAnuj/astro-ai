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

CLAUDE TOKENS PER RUN (2026-11-17, owner: "Measure tokens per cycle")
--------------------------------------------------------------------
Read from the SAME job logs the receipt comes from -- no extra request per run.
`parse_usage` states the rule; in short, the session total is the
`model_usage_since_last_result` of claude-code-action's final `"type": "result"`
object, summed over every result object in the run. Rows carry `turns`,
`tokens_input`, `tokens_output`, `tokens_cache_read`, `tokens_cache_write`,
`cost_list_usd` and `model`, each ABSENT (never 0) when the log has no readable
result. `cost_list_usd` is list price: the Max subscription pays a flat fee, so it
is a weight for comparing runs, not money spent; the weekly quota is what binds.
The top-level `tokens` block (`token_summary`) holds the window totals, medians
per outcome and tokens per merged PR. Rows settled before this existed are
backfilled ONCE, on the first collection whose input has no `tokens` block.

ENDPOINTS READ, AND THE GITHUB_TOKEN SCOPE EACH NEEDS
-----------------------------------------------------
`verify_workflows.py` cannot see `gh` calls made inside a script, so this table
is the only place the requirement is written down; a test asserts the `commit`
job in agent-measure.yml grants exactly these.

  actions/workflows/agent-work.yml/runs, actions/runs/{id}/jobs,
  actions/jobs/{id}/logs ........................ actions: read
  pulls, pulls/{n}, pulls/{n}/commits ........... pull-requests: read

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

OUTCOMES = ("shipped", "pr open", "judged", "nothing", "failed", "unknown")
ATTRIBUTIONS = ("receipt", "log", "unattributed")
# WHAT THE RUN WAS ASKED TO DO, read from the cycle's own prompt (2026-11-03).
# Until then a QA round that ruled on a PR -- which by design ships nothing --
# was filed as `nothing`, indistinguishable from a cycle that produced nothing:
# measured that day, 13 of the 47 `nothing` runs (158 of 1,303 minutes) were
# rounds that had done their job. `judged` is the outcome of a successful round.
#   qa-round   `/agent-cycle --qa-pr <n>`   judge one PR
#   fix-pr     `/agent-cycle --fix-pr <n>`  fix one PR's QA FAIL / red gates (2026-11-13)
#   issue      `/agent-cycle <n>`           work one named issue
#   ranked     `/agent-cycle`               project-manager picks the issue
#   unknown    no prompt line in the log (expired, or older than this field)
KINDS = ("qa-round", "fix-pr", "issue", "ranked", "unknown")
LOOP_FIELDS = ("run", "workflow", "date", "started", "trigger", "conclusion", "minutes",
               "issue", "pr", "pr_merged", "outcome", "attribution", "kind", "owner_helped")
# `owner_helped` (2026-11-09, owner: "at many times, I am also pushing things moving the
# PRs opened by loop to completion"). On a SHIPPED row: True when the PR was merged by,
# or carries a commit authored by, anyone outside LOOP_IDENTITIES -- the owner directly
# (`mahAnuj`) or a top-level session pushing for them (commits authored `claude`); False
# when the loop did all of it; None when it could not be read, or the row did not ship.
# Without it the "shipped" count credited the loop with PRs a human finished.
LOOP_IDENTITIES = frozenset({"github-actions[bot]", "claude[bot]", "shubhagya-publisher[bot]"})
# OPTIONAL per-row fields (2026-11-17): present only when the run's log held a
# readable result object. `parse_usage` writes them; an old row without them is valid.
USAGE_FIELDS = ("turns", "tokens_input", "tokens_output", "tokens_cache_read",
                "tokens_cache_write", "cost_list_usd", "model")
# OPTIONAL per-row field (2026-11-19): `agents_called`, {subagent: times called} for
# one run, read from the same job log (agent-work runs with `show_full_output`, so
# every Agent tool call is printed). `{}` means the log was read and the run called
# no subagent (a QA round does its own work); ABSENT means it could not be read.
# Owner, 2026-11-19: "we should track when was architect agent used in the flow" --
# measured that day over 14 working cycles: architect 1, product-manager 0.
AGENTS_FIELD = "agents_called"
TOKEN_FIELDS = ("tokens_input", "tokens_output", "tokens_cache_read", "tokens_cache_write")
# The action step's env listing prints the RESOLVED prompt (`PROMPT: /agent-cycle
# --qa-pr 679`), never the template, so this cannot match a step's echoed source.
PROMPT = re.compile(r"\bPROMPT: /agent-cycle(?: (--qa-pr |--fix-pr )?(\d+))?[ \t]*$", re.M)
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
        # `kind` arrived 2026-11-03; a snapshot written before then is still a
        # valid snapshot -- its rows read as kind `unknown` until re-collected.
        if "kind" not in r:
            r = {**r, "kind": "unknown"}
        # `owner_helped` arrived 2026-11-09; older rows read as not-yet-known.
        if "owner_helped" not in r:
            r = {**r, "owner_helped": None}
        usage = {k: r[k] for k in USAGE_FIELDS if k in r}
        if AGENTS_FIELD in r:
            ac = r[AGENTS_FIELD]
            if not isinstance(ac, dict) or any(
                    not isinstance(k, str) or not AGENT_NAME.fullmatch(k) or not _is_int(v) or v < 1
                    for k, v in ac.items()):
                errs.append(f"{where} {AGENTS_FIELD} is not {{agent-name: count >= 1}}")
        r = {k: v for k, v in r.items() if k not in USAGE_FIELDS and k != AGENTS_FIELD}
        if usage:
            # All of a reading or none of it: a row with output tokens but no
            # cache reads would read as a cheap run rather than a half-parsed one.
            missing = [k for k in USAGE_FIELDS if k != "turns" and k not in usage]
            if missing:
                errs.append(f"{where} usage is partial, missing {missing}")
            if any(not _is_int(usage[k]) or usage[k] < 0 for k in (*TOKEN_FIELDS, "turns") if k in usage):
                errs.append(f"{where} a token count is not an int >= 0")
            c = usage.get("cost_list_usd")
            if c is not None and (isinstance(c, bool) or not isinstance(c, (int, float)) or c < 0):
                errs.append(f"{where} cost_list_usd is not a number >= 0")
            if "model" in usage and (not isinstance(usage["model"], str) or not usage["model"]):
                errs.append(f"{where} model is not a non-empty string")
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
        if r["owner_helped"] not in (True, False, None):
            errs.append(f"{where} owner_helped is not true/false/null")
        elif r["owner_helped"] is not None and r["outcome"] != "shipped":
            errs.append(f"{where} owner_helped is set on a row that did not ship")
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
        if r["kind"] not in KINDS:
            errs.append(f"{where} kind {r['kind']!r} not in {KINDS}")
        if r["outcome"] == "judged" and r["kind"] != "qa-round":
            errs.append(f"{where} 'judged' but the run was not a QA round")
    w = doc.get("waste")
    if w is not None:
        if not isinstance(w, dict) or set(w.get("minutes_by_outcome", {})) != set(OUTCOMES):
            errs.append("waste.minutes_by_outcome does not cover every outcome")
        elif not (0 <= w.get("build_idle_share", -1) <= 1):
            errs.append("waste.build_idle_share out of range")
    t = doc.get("tokens")
    if t is not None and (not isinstance(t, dict) or not _is_int(t.get("measured"))
                          or t["measured"] > (t.get("runs") or 0)):
        errs.append("tokens block is malformed or measures more runs than it has")
    ag = doc.get("agents")
    if ag is not None:
        rr = ag.get("runs_read") if isinstance(ag, dict) else None
        ba = ag.get("by_agent") if isinstance(ag, dict) else None
        if not isinstance(rr, dict) or not isinstance(ba, dict) or set(rr) != set(AGENT_WINDOWS):
            errs.append("agents block is malformed")
        else:
            for name, a in ba.items():
                if not isinstance(a, dict) or any(not _is_int(a.get(k)) or a[k] > rr[k] for k in AGENT_WINDOWS):
                    errs.append(f"agents.by_agent.{name} counts more runs than were read")
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


def kind_of(logs: list[str]) -> str:
    for log in logs:
        m = PROMPT.search(log)
        if m:
            if m.group(1):
                return "fix-pr" if m.group(1).startswith("--fix-pr") else "qa-round"
            return "issue" if m.group(2) else "ranked"
    return "unknown"


_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ")
_RESULT_TYPE = re.compile(r'^  "type": "result",?$')
_TURNS = re.compile(r'^  "num_turns": (\d+),?$')
_UUID = re.compile(r'^  "uuid": "([^"]+)",?$')
_SINCE_LAST = "model_usage_since_last_result"
_CUMULATIVE = "modelUsage"


def _result_objects(log: str) -> list[list[str]]:
    """Every top-level `"type": "result"` object, as timestamp-stripped lines.

    claude-code-action pretty-prints each stream message as its own object, `{`
    and `}` alone at column 0; nested braces are indented, so column 0 is a
    top-level boundary. The type is matched at exactly two spaces, so a nested
    `"type"` (a content block, an iteration) can never qualify an object."""
    out, start = [], None
    lines = [_TS.sub("", ln, count=1) for ln in log.splitlines()]
    for i, ln in enumerate(lines):
        if ln == "{":
            start = i
        elif ln == "}" and start is not None:
            obj, start = lines[start:i + 1], None
            if any(_RESULT_TYPE.match(x) for x in obj):
                out.append(obj)
    return out


def _sub_object(obj: list[str], key: str):
    """The top-level `key: {...}` of a pretty-printed object, cut out by indentation."""
    head = f'  "{key}": {{'
    if head not in obj:
        return None
    j = obj.index(head)
    k = next((n for n in range(j + 1, len(obj)) if obj[n] in ("  }", "  },")), None)
    if k is None:
        return None
    try:
        return json.loads("{" + "\n".join(obj[j + 1:k]) + "}")
    except ValueError:
        return None


def _read_result(obj: list[str]):
    """(uuid, num_turns, since_last, cumulative) for one result object; any may be None.

    The whole object is parsed when it can be. It cannot always: the runner rewrites
    the log after serialisation -- a masked secret (`***`) eats a closing quote, and
    a line the runner reads as a command (`##[endgroup]` inside a tool result)
    replaces the line it sat on. Measured 2026-11-17: 12 non-result objects across
    40 runs failed to parse for those two reasons. Free text in `result` or
    `permission_denials` can carry either, so on failure each usage sub-object
    alone is cut out by indentation -- it holds only model names and numbers."""
    try:
        o = json.loads("\n".join(obj))
    except ValueError:
        o = None
    if isinstance(o, dict):
        turns = o.get("num_turns")
        since, cum = o.get(_SINCE_LAST), o.get(_CUMULATIVE)
        return (o.get("uuid"), turns if _is_int(turns) else None,
                since if isinstance(since, dict) else None, cum if isinstance(cum, dict) else None)
    turns = next((int(m.group(1)) for m in map(_TURNS.match, obj) if m), None)
    uuid = next((m.group(1) for m in map(_UUID.match, obj) if m), None)
    return uuid, turns, _sub_object(obj, _SINCE_LAST), _sub_object(obj, _CUMULATIVE)


#: A subagent's start record, as claude-code-action prints it under
#: `show_full_output` (verified on agent-work run 44433226676, 2026-11-19):
#:   "tool_use_id": "toolu_018V…", "description": "Rank the eligible backlog",
#:   "subagent_type": "project-manager", … "spawn_depth": 1,
#: The same call also appears in the assistant message and in `wire_tool_inputs`;
#: keying on the tool_use_id counts it once. Timestamps are stripped first, since
#: each JSON line of the log carries one.
AGENT_NAME = re.compile(r"[a-z][a-z0-9-]{0,40}")
_AGENT_START = re.compile(
    r'"tool_use_id":\s*"(toolu_\w+)",\s*"description":\s*"(?:[^"\\]|\\.)*",\s*"subagent_type":\s*"([a-z][a-z0-9-]{0,40})"')
_LOG_TS = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?", re.M)


def parse_agent_calls(log: str) -> dict[str, int]:
    """{subagent: times called} for one run's log; {} when it called none."""
    calls: dict[str, str] = {}
    for m in _AGENT_START.finditer(_LOG_TS.sub("", log)):
        calls[m.group(1)] = m.group(2)
    out: dict[str, int] = {}
    for name in calls.values():
        out[name] = out.get(name, 0) + 1
    return dict(sorted(out.items()))


def parse_usage(log: str) -> dict | None:
    """The Claude session's token usage for one run, or None when it cannot be read.

    THE RULE, verified against agent-work run 44020807802 (job 133837665489) and
    39 more runs listed 2026-11-17:

      * Only top-level `"type": "result"` objects count. The same log carries a
        `usage` block on every `assistant` message (one API call each, main agent
        only) and `usage.total_tokens` on every subagent `task_progress` (a running
        count). Summing those double-counts; they are never read.
      * Within a result object, `model_usage_since_last_result` is the session
        total INCLUDING subagents. Measured on 44020807802: it reads 305 input /
        103,720 output / 13,174,859 cache-read / 542,749 cache-write and $3.8793,
        and that $3.8793 equals the object's `total_cost_usd`; the object's own
        top-level `usage` (2,293,717 cache-read) is the main agent alone and is
        NOT the total. In all 40 runs `modelUsage` equalled it and its costUSD
        summed to `total_cost_usd`.
      * A resumed session prints more than one result object, and the key's name
        says each holds the usage SINCE THE PREVIOUS ONE, so they are SUMMED, per
        model. Objects with the same `uuid` are one object printed twice and count
        once. (No multi-result log exists in the 40 runs read, so this half is
        built from the key's NAME, not observed. `num_turns` is
        summed the same way and carries the same caveat.)
      * An OLDER action printed only `modelUsage` (run 41574673500, 2026-11-03).
        With exactly ONE result object it is used: that is the case where the two
        keys were measured equal 40 times of 40. With several, `modelUsage` may be
        cumulative or per-segment and nothing here can tell which, so: None.
      * If ANY result object's usage is unreadable, the whole reading is None: a
        partial sum would understate the run and look like a cheap one.

    `cost_list_usd` is the action's own `costUSD` (`costBasis: "list"`)."""
    seen, results = set(), []
    for obj in _result_objects(log):
        uuid, t, since, cum = _read_result(obj)
        if uuid is not None:
            if uuid in seen:
                continue
            seen.add(uuid)
        results.append((t, since, cum))
    if not results:
        return None
    if all(since is not None for _, since, _ in results):
        parts = [(t, since) for t, since, _ in results]
    elif len(results) == 1 and results[0][2] is not None:
        parts = [(results[0][0], results[0][2])]
    else:
        return None
    turns, by_model = 0, {}
    for t, mu in parts:
        turns = None if (turns is None or t is None) else turns + t
        for model, u in mu.items():
            if not isinstance(u, dict):
                return None
            acc = by_model.setdefault(model, {"in": 0, "out": 0, "cr": 0, "cw": 0, "usd": 0.0})
            try:
                acc["in"] += int(u.get("inputTokens", 0))
                acc["out"] += int(u.get("outputTokens", 0))
                acc["cr"] += int(u.get("cacheReadInputTokens", 0))
                acc["cw"] += int(u.get("cacheCreationInputTokens", 0))
                acc["usd"] += float(u.get("costUSD", 0))
            except (TypeError, ValueError):
                return None
    if not by_model:
        return None
    out = {
        "tokens_input": sum(a["in"] for a in by_model.values()),
        "tokens_output": sum(a["out"] for a in by_model.values()),
        "tokens_cache_read": sum(a["cr"] for a in by_model.values()),
        "tokens_cache_write": sum(a["cw"] for a in by_model.values()),
        "cost_list_usd": round(sum(a["usd"] for a in by_model.values()), 4),
        "model": "+".join(sorted(by_model)),
    }
    if turns is not None:
        out["turns"] = turns
    return out


def row_tokens(row: dict) -> int | None:
    """Every token the run moved: input + output + cache read + cache write."""
    if not all(_is_int(row.get(k)) for k in TOKEN_FIELDS):
        return None
    return sum(row[k] for k in TOKEN_FIELDS)


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
    kind = kind_of(logs)
    usage = parse_usage("\n".join(logs))
    agents = parse_agent_calls("\n".join(logs)) if logs else None
    for log in logs:
        got = parse_receipt(log)
        if got:
            issue, branch, pr = got
            if issue is None and branch:
                m = BRANCH_ISSUE.match(branch)
                issue = int(m.group(1)) if m else None
            return {"issue": issue, "pr": pr, "attribution": "receipt", "no_pr_recorded": pr is None,
                    "kind": kind, "usage": usage, "agents": agents}
    for log in logs:
        got = parse_net_line(log)
        if got:
            branch, no_pr = got
            m = BRANCH_ISSUE.match(branch)
            issue = int(m.group(1)) if m else None     # "on 'main'": ended without a branch
            pr = None if (no_pr or not m) else pr_for_branch(src, owner, branch, ts(run["updated_at"]))
            return {"issue": issue, "pr": pr, "attribution": "log", "no_pr_recorded": no_pr, "kind": kind,
                    "usage": usage, "agents": agents}
    return {"issue": None, "pr": None, "attribution": "unattributed", "no_pr_recorded": False,
            "kind": kind, "usage": usage, "agents": agents}


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


def read_owner_helped(src: Source, pr: int):
    """True when anyone outside LOOP_IDENTITIES merged the PR or authored a commit on
    it, False when only the loop did, None when it cannot be read. A commit whose
    author GitHub cannot link to an account counts as outside: crediting the loop
    with work nobody can attribute to it is the claim this field exists to stop."""
    try:
        d = src.get(f"pulls/{pr}")
        merger = (d.get("merged_by") or {}).get("login")
        if merger and merger not in LOOP_IDENTITIES:
            return True
        commits = src.get(f"pulls/{pr}/commits?per_page=100")
    except ApiError:
        return None
    return any(((c.get("author") or {}).get("login")) not in LOOP_IDENTITIES for c in commits)


def _with_helped(src: Source, row: dict) -> dict:
    if row["outcome"] != "shipped" or row["pr"] is None:
        return {**row, "owner_helped": None}
    return {**row, "owner_helped": read_owner_helped(src, row["pr"])}


def _minutes(run: dict) -> float:
    start = ts(run.get("run_started_at") or run["created_at"])
    return round(max((ts(run["updated_at"]) - start).total_seconds(), 0) / 60, 1)


def judged(row: dict) -> dict:
    """A successful QA round's outcome is `judged`, whatever PR its receipt names:
    a round reviews a PR, it does not ship one, so crediting it with the PR's merge
    would count one PR as shipped twice and hide the round's real cost."""
    if row["kind"] == "qa-round" and row["conclusion"] == "success" and row["outcome"] != "unknown":
        return {**row, "outcome": "judged"}
    return row


def make_row(run: dict, a: dict, state, merged) -> dict:
    started = run.get("run_started_at") or run["created_at"]
    pr = a["pr"]
    unreadable_pr = pr is not None and state is None
    return judged({
        "run": run["id"], "workflow": WORKFLOW_NAME, "date": iso(ts(started))[:10], "started": iso(ts(started)),
        "trigger": run.get("event") or "unknown", "conclusion": run.get("conclusion") or "unknown",
        "minutes": _minutes(run), "issue": a["issue"], "pr": pr,
        "pr_merged": None if (pr is None or unreadable_pr) else merged,
        "outcome": "unknown" if unreadable_pr else outcome_of(
            run.get("conclusion") or "unknown", pr, merged, state, a["attribution"], a["no_pr_recorded"]),
        "attribution": a["attribution"],
        "kind": a.get("kind", "unknown"),
        "owner_helped": None,
        **(a.get("usage") or {}),
        **({AGENTS_FIELD: a["agents"]} if a.get("agents") is not None else {}),
    })


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
    stats = {"new": 0, "refreshed": 0, "frozen": 0, "deferred": 0, "pruned": 0, "pending": 0,
             "migrated": 0}
    merged_rows = dict(old)
    # Token fields arrived 2026-11-17. A snapshot without the `tokens` block was
    # written before them, so its listed rows get their logs read ONCE; after
    # this collection writes the block, a row with no usage stays without it
    # (its log had no readable result) instead of being re-read every run.
    backfill_usage = existing is not None and "tokens" not in existing
    # Same rule for `agents_called` (2026-11-19), keyed on the `agents` block.
    backfill_agents = existing is not None and "agents" not in existing
    for run in list_runs(src, WORKFLOW_NAME, Window(now - LOOKBACK, now)):
        if run.get("status") != "completed":
            stats["pending"] += 1
            continue
        prev = old.get(run["id"])
        try:
            need_kind = prev is not None and "kind" not in prev
            need_usage = (prev is not None and backfill_usage
                          and not any(k in prev for k in USAGE_FIELDS))
            need_agents = (prev is not None and backfill_agents and AGENTS_FIELD not in prev)
            if need_kind or need_usage or need_agents:
                # A row settled before `kind` (or the token fields) existed: read
                # its log ONCE, then it is frozen again like any other.
                try:
                    logs = job_logs(src, run["id"])
                except ApiError as e:
                    if e.status not in (404, 410):
                        raise
                    logs = []
                if need_kind:
                    prev = judged({**prev, "kind": kind_of(logs)})
                if need_usage:
                    prev = {**prev, **(parse_usage("\n".join(logs)) or {})}
                if need_agents and logs:
                    prev = {**prev, AGENTS_FIELD: parse_agent_calls("\n".join(logs))}
                merged_rows[run["id"]] = prev
                stats["migrated"] += 1
            if prev is not None and prev.get("outcome") == "shipped" and prev.get("owner_helped") is None:
                # Shipped before `owner_helped` existed, or unread last time: read
                # who finished it ONCE (two requests), then it is frozen again.
                prev = _with_helped(src, prev)
                merged_rows[run["id"]] = prev
                stats["migrated"] += 1
            if prev is not None and not reopen(prev):
                stats["frozen"] += 1
                continue
            if prev is not None:      # only the PR can have moved
                a = {"issue": prev["issue"], "pr": prev["pr"], "attribution": prev["attribution"],
                     "no_pr_recorded": False, "kind": prev.get("kind", "unknown"),
                     # The log is not re-read here, so the reading it gave is carried.
                     "usage": {k: prev[k] for k in USAGE_FIELDS if k in prev}}
                state, merged = read_pr(src, prev["pr"])
                merged_rows[run["id"]] = _with_helped(src, make_row(run, a, state, merged))
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
                    a = {"issue": None, "pr": None, "attribution": "unattributed", "no_pr_recorded": False,
                         "kind": "unknown"}
                else:
                    stats["deferred"] += 1
                    print(f"::warning::run {run['id']}: {e}", file=sys.stderr)
                    continue
            state, merged = (read_pr(src, a["pr"]) if a["pr"] is not None else (None, None))
            merged_rows[run["id"]] = _with_helped(src, make_row(run, a, state, merged))
            stats["new"] += 1
        except ApiError as e:
            stats["deferred"] += 1
            print(f"::warning::run {run['id']}: {e}", file=sys.stderr)
    floor = iso(now - RETAIN)
    # Rows older than the listing window that predate `kind` are not re-read
    # (their runs are no longer listed): they are honestly `unknown`.
    kept = {k: {"owner_helped": None, **(v if "kind" in v else {**v, "kind": "unknown"})}
            for k, v in merged_rows.items() if v["started"] >= floor}
    stats["pruned"] = len(merged_rows) - len(kept)
    rows = sorted(kept.values(), key=lambda r: r["started"], reverse=True)
    return {"generated_at": iso(now), "rows": rows, "waste": waste(rows, now),
            "tokens": token_summary(rows, now), "agents": agent_summary(rows, now)}, stats


#: The spans the agent summary covers.
AGENT_WINDOWS = {"7d": 7, "30d": 30}


def agent_summary(rows: list[dict], now: datetime) -> dict:
    """Per subagent: in how many runs it was called over each window, and the
    last run that called it. `runs_read` is the denominator -- runs whose log was
    read -- so "architect 1" reads as 1 of N, never as a bare count."""
    out: dict = {"runs_read": {}, "by_agent": {}}
    for label, days in AGENT_WINDOWS.items():
        floor = iso(now - timedelta(days=days))
        read = [r for r in rows if AGENTS_FIELD in r and r["started"] >= floor]
        out["runs_read"][label] = len(read)
        for r in read:
            for name in r[AGENTS_FIELD]:
                a = out["by_agent"].setdefault(name, {**{k: 0 for k in AGENT_WINDOWS}, "last_run": None,
                                                     "last_started": None, "last_issue": None})
                a[label] += 1
    for r in rows:                                 # rows are newest first
        for name in r.get(AGENTS_FIELD) or {}:
            a = out["by_agent"].get(name)
            if a is not None and a["last_run"] is None:
                a.update(last_run=r["run"], last_started=r["started"], last_issue=r["issue"])
    out["by_agent"] = dict(sorted(out["by_agent"].items()))
    return out


#: The span the waste figures cover. Short enough to show a change this week,
#: long enough that one bad day does not dominate.
WASTE_DAYS = 7
#: Outcomes that produced a RESULT: a merged PR, an open PR still on its way,
#: or a verdict. Everything else is time spent without one.
RESULT_OUTCOMES = ("shipped", "pr open", "judged")


def waste(rows: list[dict], now: datetime, days: int = WASTE_DAYS) -> dict:
    """Where the loop's time went over the last `days`: minutes by outcome, the
    share spent without a result, and how long the BUILD lane sat idle.

    Idle is wall-clock time in the window with no build-lane cycle running (QA
    rounds have their own lane and are excluded). With a backlog open, idle is
    capacity the schedule left unused -- not waste by itself, but the number to
    watch when the question is "would more cycles help"."""
    start = now - timedelta(days=days)
    win = [r for r in rows if ts(r["started"]) >= start]
    by = {o: 0.0 for o in OUTCOMES}
    for r in win:
        by[r["outcome"]] += float(r["minutes"])
    total = sum(by.values())
    no_result = sum(v for k, v in by.items() if k not in RESULT_OUTCOMES)
    spans = sorted((ts(r["started"]), ts(r["started"]) + timedelta(minutes=float(r["minutes"])))
                   for r in win if r["kind"] != "qa-round")
    busy, cur_s, cur_e = 0.0, None, None
    for s, e in spans:
        s, e = max(s, start), min(e, now)
        if e <= s:
            continue
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                busy += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        busy += (cur_e - cur_s).total_seconds()
    window_h = days * 24.0
    idle_h = max(window_h - busy / 3600, 0.0)
    return {
        "days": days,
        "cycles": len(win),
        "minutes_by_outcome": {k: round(v, 1) for k, v in by.items()},
        "minutes_total": round(total, 1),
        "minutes_without_result": round(no_result, 1),
        "share_without_result": round(no_result / total, 3) if total else None,
        "shipped_prs": len({r["pr"] for r in win if r["outcome"] == "shipped" and r["pr"]}),
        "build_idle_hours": round(idle_h, 1),
        "build_idle_share": round(idle_h / window_h, 3),
    }


def _median(xs: list) -> int | float | None:
    if not xs:
        return None
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _window_tokens(rows: list[dict], start: datetime, end: datetime) -> dict:
    win = [r for r in rows if start <= ts(r["started"]) < end]
    measured = [r for r in win if row_tokens(r) is not None]
    tokens = sum(row_tokens(r) for r in measured)
    usd = round(sum(float(r.get("cost_list_usd") or 0) for r in measured), 2)
    merged = len({r["pr"] for r in win if r["outcome"] == "shipped" and r["pr"]})
    return {"win": win, "measured": measured, "tokens": tokens, "usd": usd, "merged": merged,
            "per_pr": round(tokens / merged) if merged else None,
            "usd_per_pr": round(usd / merged, 2) if merged else None}


def token_summary(rows: list[dict], now: datetime, days: int = WASTE_DAYS) -> dict:
    """What the loop's Claude usage bought over the last `days` (the waste window).

    `per_merged_pr` is EVERY measured run's tokens in the window -- QA rounds,
    empty cycles and failures included -- divided by the distinct PRs that merged
    in it. That is the end-to-end cost of a shipped fix, which is the owner's
    question; dividing only the shipping rows' tokens would hide the waste that
    earned them. It is a floor when `measured < runs`, so both are carried.
    `previous` is the same figure for the window before, so a token-saving change
    can be read as a before/after and `cycle-tokens` can compare the two.
    Medians are over measured rows only and absent where no row was measured."""
    cur = _window_tokens(rows, now - timedelta(days=days), now + timedelta(seconds=1))
    prev = _window_tokens(rows, now - timedelta(days=2 * days), now - timedelta(days=days))
    m = cur["measured"]

    def med(rs):
        x = _median([row_tokens(r) for r in rs])
        return None if x is None else round(x)

    by_outcome = {}
    for o in OUTCOMES:
        rs = [r for r in m if r["outcome"] == o]
        if rs:
            by_outcome[o] = {"runs": len(rs), "tokens": med(rs),
                             "cost_list_usd": round(_median([float(r["cost_list_usd"]) for r in rs]), 2)}
    return {
        "days": days,
        "runs": len(cur["win"]),
        "measured": len(m),
        "total": {"tokens": cur["tokens"],
                  **{k.replace("tokens_", ""): sum(r[k] for r in m) for k in TOKEN_FIELDS},
                  "cost_list_usd": cur["usd"]},
        "median_by_outcome": by_outcome,
        "median_cycle": med([r for r in m if r["kind"] != "qa-round"]),
        "median_qa_round": med([r for r in m if r["kind"] == "qa-round"]),
        "merged_prs": cur["merged"],
        "per_merged_pr": cur["per_pr"],
        "cost_list_usd_per_merged_pr": cur["usd_per_pr"],
        "previous": {"runs": len(prev["win"]), "measured": len(prev["measured"]),
                     "merged_prs": prev["merged"], "per_merged_pr": prev["per_pr"]},
    }


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
