#!/usr/bin/env python3
"""Is each loop alive, is it producing, and which agent is failing? (#345)

THE DOMINANT FAILURE IN THIS SYSTEM IS SILENCE, NOT BAD WORK
------------------------------------------------------------
Measured 2026-10-14 across the fourteen active workflows: two had a red most-
recent run and one had never executed at all, and none of that was visible
anywhere. So this reports in three layers, in this order:

  LIVENESS   did the loop run when it was due?
  YIELD      when it ran, did anything come out?
  AGENTS     when nothing came out, which agent stopped?

Liveness first because a loop that never runs cannot produce bad work to grade,
and a yield metric over zero runs reads as a flawless 0/0.

"NEVER RUN" IS TWO DIFFERENT FACTS
----------------------------------
`agent-research.yml` has never run. It is not broken: it landed on `main` on a
Thursday and its cron is Wednesday, so its first slot had not arrived. A naive
"0 runs = dead" check would have filed a bug against a healthy loop, and the
near-miss is the reason this script computes SLOTS DUE SINCE THE FILE LANDED
rather than counting runs. `0 of 0` is `not-due-yet`; `0 of 3` is `dormant`.

A RED RUN IS NOT AUTOMATICALLY A FAILING AGENT
-----------------------------------------------
`loop-outcomes.yml` is red because its script exits 1 when it finds something
broken -- the redness is the report working. `agent-design.yml` is red because
`claude-code-action` itself failed. Both are `conclusion: failure` and they
mean opposite things, so a loop may declare `red_means_finding: true` in
SELF_REPORTING below and is then classified `reporting` rather than `broken`.
Colouring both red teaches a reader to ignore red.

WHAT THIS DOES NOT CATCH, STATED PLAINLY
-----------------------------------------
Every per-agent figure here is parsed from the agents' OWN comments. That
catches an agent that stops, crashes or regresses. It cannot catch one that
writes a confident comment and does nothing -- the failure this repo has
actually suffered ("it wrote USER AUTHORISED PUSH, then cited its own line").
The defence against that is the gates, which judge the artifact rather than the
story about it, and no metric here substitutes for them.

Comments no pattern claims are COUNTED and reported as `unmatched`, never
dropped. A parser that silently matches 40% of its input looks identical to one
that matches all of it.

Stdlib plus the `gh` CLI. Zero LLM calls.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

#: Loops whose non-zero exit is a FINDING, not a fault. See the module header.
SELF_REPORTING = {"loop-outcomes.yml"}

#: Which agent a comment belongs to. Checked IN ORDER, first match wins, so a
#: narrow pattern must precede a broad one. Every pattern is anchored at the
#: start of the body (after optional markdown emphasis or heading marks),
#: because an agent NAMED in the middle of a sentence is being discussed, not
#: speaking -- "escalated to chief" is written by the cycle, not by chief.
_LEAD = r"^[\s>*#_]{0,8}"
AGENT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("qa",              _LEAD + r"QA[\s:(]|" + _LEAD + r"QA round \d"),
    ("chief",           _LEAD + r"chief ruling"),
    ("steward",         _LEAD + r"steward[\s,:(]"),
    ("analyst",         _LEAD + r"(Analyst score|Post-ship score)"),
    ("infra-lead",      _LEAD + r"infra-lead"),
    ("architect",       _LEAD + r"architect\b"),
    ("engineer",        _LEAD + r"engineer\b"),
    ("project-manager", _LEAD + r"project-manager\b"),
    ("product-manager", _LEAD + r"product-manager\b"),
    # Broadest, so it sits last: the cycle narrating its own steps.
    ("agent-cycle",     _LEAD + r"(agent-cycle|Autonomous cycle)"),
)
_COMPILED = tuple((name, re.compile(pat, re.I)) for name, pat in AGENT_PATTERNS)

#: A QA verdict line. `qa.md` says "PASS is a report, not an action", and the
#: wording has drifted across runs ("QA: PASS", "QA round 1: FAIL",
#: "QA: PASS — independent"), so the verdict is read as the first PASS/FAIL
#: token after a leading `QA`, not from a fixed sentence.
QA_VERDICT = re.compile(r"^[\s>*#_]{0,8}QA\b[^\n]{0,80}?\b(PASS|FAIL)\b", re.I)

#: `- cron: "0 23 * * *"` inside a workflow. Deliberately a line regex and not
#: a YAML parse: this script runs in the `commit` job, which has no `uv sync`
#: and therefore no PyYAML. Every schedule in this repo is a flat list of
#: quoted crons directly under `on: schedule:`, and a file whose cron this
#: cannot read is reported as `cadence: null` rather than assumed daily.
CRON_LINE = re.compile(r"^\s*-\s*cron:\s*['\"]?([^'\"#\n]+?)['\"]?\s*(?:#.*)?$", re.M)


def gh(*args: str) -> str:
    """`gh` with its stderr surfaced. A 403 here must not read as empty data."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def gh_json(*args: str):
    return json.loads(gh(*args) or "null")


def gh_json_pages(*args: str) -> list:
    """`gh api --paginate --jq` emits ONE JSON VALUE PER PAGE, concatenated.

    `json.loads` on that raises "Extra data: line 2 column 1" the moment a
    result spills past the first page -- which is to say, as soon as there is
    enough data to be worth reading. Decoded incrementally instead, so this
    does not depend on a `gh` new enough for `--slurp`.
    """
    text = gh(*args)
    dec, out, i, n = json.JSONDecoder(), [], 0, len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        val, i = dec.raw_decode(text, i)
        out.extend(val if isinstance(val, list) else [val])
    return out


# ── liveness ────────────────────────────────────────────────────────────────

def parse_crons(text: str) -> list[tuple[int, int, set[int] | None]]:
    """Every cron in a workflow as (minute, hour, weekdays-or-None-for-daily).

    Supports the shapes this repo uses: numeric minute and hour, `*` for day of
    month and month, and `*` or a comma list for day of week. Anything else
    raises, because a cron silently misread as daily would report a weekly loop
    as missing six slots a week -- a false alarm is as corrosive here as a miss.
    """
    out = []
    for raw in CRON_LINE.findall(text):
        parts = raw.split()
        if len(parts) != 5:
            raise ValueError(f"not a 5-field cron: {raw!r}")
        minute, hour, dom, month, dow = parts
        if dom != "*" or month != "*":
            raise ValueError(f"day-of-month/month crons are not supported: {raw!r}")
        if not minute.isdigit() or not hour.isdigit():
            raise ValueError(f"only a fixed minute and hour are supported: {raw!r}")
        days = None if dow == "*" else {int(d) % 7 for d in dow.split(",")}
        out.append((int(minute), int(hour), days))
    return out


def slots_due(crons, since: datetime, until: datetime) -> int:
    """How many times these crons came due in (since, until].

    Walks days rather than solving it in closed form: the windows here are
    weeks, the loop is a few hundred iterations, and a closed form would need a
    test this does not have.
    """
    n = 0
    day = since.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= until:
        for minute, hour, days in crons:
            # cron day-of-week is 0=Sunday; Python's weekday() is 0=Monday.
            if days is not None and ((day.weekday() + 1) % 7) not in days:
                continue
            at = day.replace(hour=hour, minute=minute)
            if since < at <= until:
                n += 1
        day += timedelta(days=1)
    return n


def schedule_since(path: Path, repo: str) -> str | None:
    """When this workflow was LAST edited on `main`, ISO-8601, or None.

    Last edited, not first created, and the difference is a false alarm this
    script produced on its first run. `agent-work.yml` has carried a 23:00 cron
    since 2026-10-08 and gained a second at 11:00 on 2026-10-13 (#337). Counting
    the CURRENT crons from the file's CREATION credits six days of 11:00 slots
    that no schedule ever declared, and the loop was reported as missing eight
    slots it was never due for.

    A schedule is only knowable from the moment it was last written, so that is
    where the window starts. The cost is honest and worth naming: a workflow
    edited every few days never accumulates enough slots to be judged, and
    reports `not-due-yet` rather than a verdict built on a cadence that was not
    in force.

    `git log` first: free and exact. The `commit` job checks out shallow, so
    this normally returns nothing and the API answers instead -- one request per
    workflow, twice a day.
    """
    rel = path.relative_to(ROOT).as_posix()
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", rel],
            capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
        if out:
            return out.splitlines()[0]
    except (subprocess.CalledProcessError, OSError):
        pass
    try:
        commits = gh_json("api", f"repos/{repo}/commits?path={rel}&per_page=1")
        if commits:
            return commits[0]["commit"]["author"]["date"]
    except (RuntimeError, ValueError, KeyError, IndexError):
        pass
    return None


def liveness(repo: str, now: datetime, days: int) -> list[dict]:
    """One row per active workflow: due, observed, and a verdict."""
    runs = gh_json("api", f"repos/{repo}/actions/workflows", "--jq",
                   '[.workflows[] | select(.state=="active") | {name,path,id}]') or []
    window_start = now - timedelta(days=days)
    rows = []
    for wf in runs:
        name = wf["path"].split("/")[-1]
        path = WORKFLOWS / name
        cadence, err, crons = None, None, []
        if path.is_file():
            try:
                crons = parse_crons(path.read_text())
                cadence = [f"{m:02d} {h:02d} * * {'*' if d is None else ','.join(map(str, sorted(d)))}"
                           for m, h, d in crons]
            except ValueError as exc:
                err = str(exc)

        recent = gh_json("api", f"repos/{repo}/actions/workflows/{wf['id']}/runs"
                                f"?per_page=100&created=>{window_start:%Y-%m-%d}",
                         "--jq", '[.workflow_runs[] | {created_at, conclusion, status, event}]') or []
        scheduled = [r for r in recent if r["event"] == "schedule"]
        last = gh_json("api", f"repos/{repo}/actions/workflows/{wf['id']}/runs?per_page=1",
                       "--jq", '.workflow_runs[0] | {created_at, conclusion, status} // null')

        born = schedule_since(path, repo) if crons else None
        start = window_start
        if born:
            born_dt = datetime.fromisoformat(born.replace("Z", "+00:00")).astimezone(timezone.utc)
            start = max(start, born_dt)
        due = slots_due(crons, start, now) if crons else None

        if not crons:
            verdict = "on-demand"            # no schedule: triggered by an event
        elif due == 0:
            verdict = "not-due-yet"          # the agent-research case
        elif not scheduled:
            verdict = "dormant"              # due and never came
        elif last and last.get("conclusion") == "failure":
            verdict = "reporting" if name in SELF_REPORTING else "broken"
        elif len(scheduled) < due:
            verdict = "missing-slots"
        else:
            verdict = "ok"

        rows.append({
            "workflow": name, "display": wf["name"],
            "cadence": cadence, "cadence_error": err,
            "schedule_since": born,
            "slots_due": due,
            "runs_scheduled": len(scheduled),
            "runs_total": len(recent),
            "last_run": (last or {}).get("created_at"),
            "last_conclusion": (last or {}).get("conclusion") or (last or {}).get("status"),
            # Is the LAST RUN red, amber or green, independent of the verdict?
            #
            # The two answer different questions and /admin/ops needs both. The
            # verdict grades the SCHEDULE -- a loop between slots is
            # `not-due-yet` whether its last run was green or red -- and for six
            # days `agent-measure` read healthy on that page while every run was
            # failing to push (#393). `agent-design` sits at `not-due-yet` right
            # now with a `failure` as its most recent run.
            #
            # Computed here rather than in the template because SELF_REPORTING
            # lives here: `loop-outcomes` exits non-zero when it FINDS
            # something, so painting its red the same red as a crash is the
            # thing this file's own header warns teaches a reader to ignore red.
            # A template deriving the colour from the conclusion string alone
            # could not know that, and would have got it wrong.
            "last_run_health": _health((last or {}).get("conclusion"),
                                       (last or {}).get("status"),
                                       name in SELF_REPORTING),
            "verdict": verdict,
        })
    rows.sort(key=lambda r: (r["verdict"] != "broken", r["verdict"] != "dormant", r["workflow"]))
    return rows


def _health(conclusion: str | None, status: str | None, self_reporting: bool) -> str:
    """"green" | "red" | "amber" | "running" | "unknown" for the most recent run.

    `unknown`, never a default of green: a loop that has never run has no health
    and saying otherwise is the silence this whole file exists to break. A run
    still in flight is `running` for the same reason -- `in_progress` carries no
    conclusion, and the first version of the column painted it green.
    """
    if conclusion in (None, ""):
        if status in ("in_progress", "queued", "requested", "waiting", "pending"):
            return "running"
        return "unknown"
    if conclusion == "success":
        return "green"
    if conclusion in ("cancelled", "skipped", "neutral", "stale", "action_required"):
        return "amber"
    # failure, timed_out, startup_failure
    return "amber" if self_reporting else "red"


# ── agents ──────────────────────────────────────────────────────────────────

def classify(body: str) -> str | None:
    for name, rx in _COMPILED:
        if rx.search(body):
            return name
    return None


def agents(repo: str, now: datetime, days: int) -> dict:
    """Per-agent activity and QA rounds, parsed from issue comments.

    One endpoint for the whole repo (`issues/comments?since=`), not one request
    per issue: the per-issue shape would be ~66 requests against a 1,000/hour
    budget, twice a day, to read the same rows.
    """
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = gh_json_pages("api", "--paginate",
                        f"repos/{repo}/issues/comments?since={since}&per_page=100",
                        "--jq", '[.[] | {user: .user.login, body, created_at, '
                                'issue: (.issue_url | split("/") | last)}]')

    # `claude[bot]` is the agents speaking. `github-actions[bot]` is the
    # workflows' own notices -- merge receipts, close-on-evidence messages --
    # which no agent wrote, so counting them as unmatched would make the parser
    # look 40% blind when the misses are mostly not agent comments at all.
    bots = [c for c in raw if c["user"] == "claude[bot]"]
    automation = [c for c in raw if c["user"] == "github-actions[bot]"]
    by_agent: Counter[str] = Counter()
    unmatched = []
    qa_by_issue: dict[str, list[str]] = defaultdict(list)

    for c in bots:
        who = classify(c["body"])
        if who is None:
            unmatched.append({"issue": c["issue"], "at": c["created_at"],
                              "head": " ".join(c["body"][:90].split())})
            continue
        by_agent[who] += 1
        if who == "qa":
            m = QA_VERDICT.search(c["body"])
            if m:
                qa_by_issue[c["issue"]].append(m.group(1).upper())

    # Rounds per issue, and how often the FIRST submission failed. /bug records
    # fifteen QA passes with every one failing its first submission; this is
    # the number that says whether that is still true.
    rounds = {k: v for k, v in qa_by_issue.items() if v}
    first_fail = sum(1 for v in rounds.values() if v[0] == "FAIL")
    reached_pass = sum(1 for v in rounds.values() if "PASS" in v)
    return {
        "window_days": days,
        "comments_total": len(raw),
        "comments_by_agents": len(bots),
        "comments_by_automation": len(automation),
        "by_agent": dict(by_agent.most_common()),
        "unmatched_count": len(unmatched),
        "unmatched_pct": round(len(unmatched) / len(bots) * 100) if bots else None,
        "unmatched_sample": unmatched[:8],
        "qa": {
            "issues_with_a_verdict": len(rounds),
            "issues_reaching_pass": reached_pass,
            "first_submission_failed": first_fail,
            "first_submission_fail_pct": round(first_fail / len(rounds) * 100) if rounds else None,
            "rounds_per_issue": {k: v for k, v in sorted(rounds.items(), key=lambda kv: -len(kv[1]))},
            "max_rounds": max((len(v) for v in rounds.values()), default=0),
        },
    }


# ── yield ───────────────────────────────────────────────────────────────────

def yield_view(loop_path: Path) -> dict:
    """Delivery yield, read from measurements/loop.json rather than recomputed.

    Two files disagreeing about how many cycles shipped is worse than one file
    saying nothing, so this never queries the API for something loop.json
    already records.
    """
    if not loop_path.is_file():
        return {"ok": False, "why": f"{loop_path.name} not present"}
    doc = json.loads(loop_path.read_text())
    rows = doc.get("rows") or []
    work = [r for r in rows if r.get("workflow") == "agent-work"]
    outcomes = Counter(r["outcome"] for r in work)
    mins = sorted(r["minutes"] for r in work if isinstance(r.get("minutes"), (int, float)))
    shipped = outcomes.get("shipped", 0)
    return {
        "ok": True,
        "cycles": len(work),
        "outcomes": dict(outcomes.most_common()),
        "yield_pct": round(shipped / len(work) * 100) if work else None,
        "median_minutes": mins[len(mins) // 2] if mins else None,
        "minutes_total": round(sum(mins), 1),
        # Runner minutes spent per issue that actually shipped. The only cost
        # signal available per loop: the Claude subscription is flat and cannot
        # be attributed per run.
        "minutes_per_shipped": round(sum(mins) / shipped, 1) if shipped else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default="mahAnuj/astro-ai")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="measurements/agents.json")
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    doc = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": args.repo,
        "window_days": args.days,
        "loops": liveness(args.repo, now, args.days),
        "delivery": yield_view(ROOT / "measurements" / "loop.json"),
        "agents": agents(args.repo, now, args.days),
    }
    doc["alerts"] = [r["workflow"] for r in doc["loops"]
                     if r["verdict"] in ("broken", "dormant", "missing-slots")]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    v = Counter(r["verdict"] for r in doc["loops"])
    print(f"{out}: {len(doc['loops'])} loops {dict(v)}; "
          f"delivery {doc['delivery'].get('yield_pct')}% yield; "
          f"{doc['agents']['unmatched_count']} of "
          f"{doc['agents']['comments_by_agents']} agent comments unmatched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
