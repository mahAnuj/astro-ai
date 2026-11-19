#!/usr/bin/env python3
"""Growth goals at every level, their meters, and the 60/40 split of the loop's build work.

WHY THIS EXISTS (owner, 2026-11-19)
-----------------------------------
*"our objective is the user-base growth for shubhagya.com website, who is making sure that it is
happening or not. I think we also need to have weekly growth goals, and work should be prioritised
to ensure loop does the necessary things in week related to the objective set apart from other
fixes from the backlog. so split everyday work into 60% growth and 40% other work ... CEO should
monitor if weekly goals are met, what is lacking and direct the loop accordingly for next week."*
And: *"a meter should be added for daily, weekly goal, overall goal that shows how much of the goal
is achieved. Let's also set monthly, quarterly goal and have a meter for that."* And: *"Week is 7
days work not 5 days ... It should be Sunday review and Monday next week start."*

Until then `project-manager` ranked by user harm and nothing reserved time for growth. Measured
2026-11-19: 13 of 62 build cycles in week 2026-W47 (21%) were growth work. Now:

  * `chief` (the CEO role) posts goals as comments on the one open issue labelled `weekly-goals`,
    from its SUNDAY review (`agent-sync.yml`, before Sunday's ranking): next week's goals every
    Sunday, next month's and next quarter's when none exist yet, and a score for each period
    that ends. A week is the 7-day ISO week, Monday to Sunday, IST.
  * Every build cycle's issue is classed GROWTH (label `growth` or one of GROWTH_LABELS, or named
    by a current goal), EXEMPT (production is broken: `severity:blocker`, or an `[OPS]` finding at
    `priority:high`) or OTHER.
  * `project-manager` runs this before ranking. When `must_pick_growth` is true it picks the
    highest-ranked eligible growth issue, unless an EXEMPT issue is open (always first, never
    counted against the split).
  * Five METERS for /admin/ops, each 0..1:
      daily      today's growth share against the 60% target
      weekly     the mean progress of this week's goals
      monthly    the mean progress of this month's goals
      quarterly  the mean progress of this quarter's goals
      overall    OBJECTIVE.md's lever: of the 10 highest-impression queries, how many rank top 5

THE RULES, so every reader computes the same answer
----------------------------------------------------
Days, weeks (Mon-Sun), months and quarters are IST (UTC+5:30), like /admin/ops. Counted cycles:
`agent-work` rows of kind `issue` or `ranked` naming an issue (QA rounds and PR fixes are not
choices of work). `must_pick_growth` is `growth < ceil(0.6 * (growth + other + 1))` over TODAY's
non-exempt cycles: true for a day's first pick, then it holds the running share at or just above 60%.

A goal's progress is `(current - baseline) / (target - baseline)`, clamped to 0..1, so a target
below its baseline (a position) works the same way. `current` comes from METRICS, read from the
committed `measurements/` files this run; a goal whose `metric_key` is not in METRICS falls back to
the share of its `issues` that are closed, and with neither it has no progress (shown, not guessed).

WHERE THE GOALS LIVE, and why not under measurements/
------------------------------------------------------
CLAUDE.md: *"Put nothing load-bearing under `measurements/` -- it never ships."* The goals steer
the loop, so they live on a GitHub issue the owner can read and edit. A goals comment:

    <!-- weekly-goals week=2026-W48 -->        (or monthly-goals month=2026-12,
    ...prose for humans...                      quarterly-goals quarter=2027-Q1)
    ```json
    {"week": "2026-W48", "goals": [{"id": "g1", "goal": "...", "metric": "words",
      "metric_key": "gsc_clicks_28d", "baseline": 383, "target": 450, "issues": [1071]}],
     "direction": "..."}
    ```

The JSON's period key is `week`, `month` or `quarter` and must equal the marker's. A score comment
uses `<!-- weekly-goals-score week=... -->` (and the monthly/quarterly forms) with
`{"week": ..., "results": [{"id": "g1", "status": "met|partial|missed", "actual": 22, "why": "..."}],
"lacking": "...", "direction": "..."}`. Only TRUSTED authors' comments count: the repo is public.

Stdlib plus the `gh` CLI, like the other collectors in agent-measure's commit job. No LLM.

EXIT CODES: 0 done   1 an API read failed (nothing written), or a file to post was invalid
            2 bad arguments
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str]], str]

sys.path.insert(0, str(Path(__file__).resolve().parent))
import outbox  # noqa: E402  -- the one posting path (#1188)

IST = timezone(timedelta(hours=5, minutes=30))
TARGET = 0.6
GROWTH_LABEL = "growth"
#: Labels that already meant growth before `growth` existed (measured 2026-11-19 on the repo's
#: label list), so the split has real history from its first day. `funnel:*` counts by prefix.
GROWTH_LABELS = frozenset({GROWTH_LABEL, "seo", "content", "engagement", "friction",
                           "category:content", "category:eeat", "category:structured-data"})
GOALS_LABEL = "weekly-goals"
COUNTED_KINDS = ("issue", "ranked")
DAYS = 14
TRUSTED = frozenset({"claude[bot]", "github-actions[bot]", "mahAnuj"})
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
STATUSES = ("met", "partial", "missed")

#: level -> (the JSON's period key, the period's pattern)
LEVELS = {"weekly": ("week", r"\d{4}-W\d{2}"),
          "monthly": ("month", r"\d{4}-\d{2}"),
          "quarterly": ("quarter", r"\d{4}-Q[1-4]")}
GOALS_MARKS = {lv: re.compile(rf"<!--\s*{lv}-goals\s+{key}=({pat})\s*-->") for lv, (key, pat) in LEVELS.items()}
SCORE_MARKS = {lv: re.compile(rf"<!--\s*{lv}-goals-score\s+{key}=({pat})\s*-->") for lv, (key, pat) in LEVELS.items()}
# Kept for callers and tests that name the weekly marks directly.
GOALS_MARK, SCORE_MARK = GOALS_MARKS["weekly"], SCORE_MARKS["weekly"]

#: The OBJECTIVE.md lever: "Move the 6–20 position band into the top 5 on the ten
#: highest-impression queries."
OBJECTIVE_QUERIES = 10
OBJECTIVE_POSITION = 5.0


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.strptime(s or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def iso_week(d: datetime) -> str:
    """The 7-day ISO week, Monday to Sunday, in IST."""
    y, w, _ = d.astimezone(IST).isocalendar()
    return f"{y}-W{w:02d}"


def periods(now: datetime) -> dict[str, str]:
    d = now.astimezone(IST)
    return {"weekly": iso_week(now), "monthly": d.strftime("%Y-%m"),
            "quarterly": f"{d.year}-Q{(d.month - 1) // 3 + 1}"}


def _shift(level: str, period: str, step: int) -> str:
    """The period `step` periods after `period` (negative: before)."""
    if level == "weekly":
        y, w = period.split("-W")
        monday = datetime.fromisocalendar(int(y), int(w), 1).replace(tzinfo=IST)
        return iso_week(monday + timedelta(weeks=step))
    if level == "monthly":
        y, m = map(int, period.split("-"))
        i = y * 12 + (m - 1) + step
        return f"{i // 12}-{i % 12 + 1:02d}"
    y, q = period.split("-Q")
    i = int(y) * 4 + (int(q) - 1) + step
    return f"{i // 4}-Q{i % 4 + 1}"


def effective_periods(now: datetime, posted: dict[str, set[str]]) -> dict[str, str]:
    """The period whose goals steer the loop NOW, per level. Normally the calendar one, but on
    the LAST DAY of a period (Sunday for a week), once the next period's goals are posted they
    take over: QA on #1241 measured the Sunday review landing at 20:53 IST and Sunday's ranking
    (22:30 IST) still reading the old week's goals until Monday."""
    cal, tomorrow = periods(now), periods(now + timedelta(days=1))
    return {lv: (tomorrow[lv] if tomorrow[lv] != cal[lv] and tomorrow[lv] in posted.get(lv, set())
                 else cal[lv]) for lv in cal}


def classify(issue: dict | None, goal_issues: set[int]) -> str:
    """growth | exempt | other, for one issue as the listing returns it."""
    if not issue:
        return "other"
    labels = {(l.get("name") if isinstance(l, dict) else l) for l in issue.get("labels") or []}
    title = (issue.get("title") or "").lstrip()
    if "severity:blocker" in labels or (title.upper().startswith("[OPS]") and "priority:high" in labels):
        return "exempt"
    if labels & GROWTH_LABELS or any(str(l).startswith("funnel:") for l in labels) \
            or issue.get("number") in goal_issues:
        return "growth"
    return "other"


def must_pick_growth(growth: int, other: int) -> bool:
    return growth < math.ceil(TARGET * (growth + other + 1))


def _share(g: int, o: int) -> float | None:
    return round(g / (g + o), 3) if g + o else None


# --------------------------------------------------------------- goals

def _parse(body: str, mark: re.Pattern, key: str = "week") -> tuple[str, dict] | None:
    m = mark.search(body or "")
    j = JSON_BLOCK.search(body or "")
    if not m or not j:
        return None
    try:
        doc = json.loads(j.group(1))
    except ValueError:
        return None
    if not isinstance(doc, dict) or doc.get(key) != m.group(1):
        return None
    return m.group(1), doc


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _valid_goals(doc: dict) -> bool:
    """Shape only: every field the readers touch has the type they expect (QA on #1241: a list
    metric_key crashed progress(), and `issues: 5` made every read raise)."""
    goals = doc.get("goals")
    return isinstance(goals, list) and bool(goals) and all(
        isinstance(g, dict) and isinstance(g.get("id"), str) and isinstance(g.get("goal"), str)
        and isinstance(g.get("issues", []), list)
        and all(isinstance(n, int) and not isinstance(n, bool) for n in g.get("issues") or [])
        and (g.get("metric_key") is None or isinstance(g["metric_key"], str))
        and all(g.get(k) is None or _num(g[k]) for k in ("baseline", "target"))
        for g in goals)


def _measurable(doc: dict) -> bool:
    """Posting only: every goal can move a meter -- a known metric_key, or issues to count."""
    return all(g.get("metric_key") in METRIC_KEYS or bool(g.get("issues")) for g in doc["goals"])


def _valid_score(doc: dict) -> bool:
    res = doc.get("results")
    return isinstance(res, list) and all(
        isinstance(r, dict) and isinstance(r.get("id"), str) and r.get("status") in STATUSES for r in res)


def _comments(gh: Runner, repo: str) -> tuple[int | None, list[dict]]:
    issues = json.loads(gh(["api", f"repos/{repo}/issues?labels={GOALS_LABEL}&state=open&per_page=5"]))
    issues = [i for i in issues if "pull_request" not in i]
    if not issues:
        return None, []
    n = min(i["number"] for i in issues)                     # the one standing issue
    raw = gh(["api", "--paginate", f"repos/{repo}/issues/{n}/comments?per_page=100",
              "--jq", ".[] | {login: .user.login, at: .created_at, body}"])
    out = []
    for line in raw.splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue
        if c.get("login") in TRUSTED:
            out.append(c)
    return n, out


def read_goals(gh: Runner, repo: str, now: datetime) -> dict:
    """{issue, levels: {weekly|monthly|quarterly: {period, current, previous_score, history}},
    current, previous_score}. The newest trusted comment per period wins; `current` is THIS
    period's goals only (last month's are not this month's), and the top-level `current` and
    `previous_score` are the weekly ones."""
    issue, comments = _comments(gh, repo)
    now_p = periods(now)
    levels = {}
    for lv, (key, _) in LEVELS.items():
        seen: dict[str, dict] = {}
        for c in comments:
            g = _parse(c.get("body") or "", GOALS_MARKS[lv], key)
            if g and _valid_goals(g[1]):
                seen.setdefault(g[0], {})["goals"] = {**g[1], "at": c["at"], "by": c["login"]}
            s = _parse(c.get("body") or "", SCORE_MARKS[lv], key)
            if s and _valid_score(s[1]):
                seen.setdefault(s[0], {})["score"] = {**s[1], "at": c["at"], "by": c["login"]}
        this = effective_periods(now, {lv: {p for p in seen if "goals" in seen[p]}})[lv]
        scored = sorted(p for p in seen if p < this and "score" in seen[p])
        levels[lv] = {
            "period": this,
            "current": (seen.get(this) or {}).get("goals"),
            "previous_score": seen[scored[-1]]["score"] if scored else None,
            "history": [{"period": p, "goals": len((seen[p].get("goals") or {}).get("goals") or []),
                         "met": sum(r["status"] == "met" for r in (seen[p].get("score") or {}).get("results") or []),
                         "scored": "score" in seen[p]}
                        for p in sorted(seen)[-8:]],
        }
    return {"issue": issue, "levels": levels,
            "current": levels["weekly"]["current"], "previous_score": levels["weekly"]["previous_score"]}


def goal_issue_numbers(goals: dict) -> set[int]:
    return {n for lv in (goals.get("levels") or {}).values()
            for g in ((lv.get("current") or {}).get("goals") or []) for n in g.get("issues") or []}


# --------------------------------------------------------------- metrics

def _load(mdir: Path, name: str) -> dict | None:
    try:
        return json.loads((mdir / name).read_text())
    except (OSError, ValueError):
        return None


def objective_top5(mdir: Path) -> dict | None:
    """Of the OBJECTIVE_QUERIES highest-impression queries, how many rank at or above
    OBJECTIVE_POSITION (gsc-trend-query.json, its own window)."""
    doc = _load(mdir, "gsc-trend-query.json")
    rows = [r for r in (doc or {}).get("rows") or []
            if _num(r.get("impressions")) and _num(r.get("position")) and not r.get("is_gone")]
    if not rows:
        return None
    top = sorted(rows, key=lambda r: -r["impressions"])[:OBJECTIVE_QUERIES]
    hit = [r for r in top if r["position"] <= OBJECTIVE_POSITION]
    return {"value": len(hit), "of": len(top), "window": doc.get("window"),
            "queries": [{"query": r.get("query"), "impressions": r["impressions"],
                         "position": r["position"]} for r in top]}


METRIC_KEYS = ("gsc_clicks_28d", "gsc_impressions_28d", "ga4_users_28d", "ga4_new_users_28d",
               "ga4_sessions_28d", "objective_top5", "growth_share_today", "growth_share_week",
               "growth_share_month")


def metrics(mdir: Path, split: dict) -> dict[str, float]:
    """Every metric a goal may name as `metric_key`, measured now. Absent when unreadable."""
    out: dict[str, float] = {}
    gsc = _load(mdir, "gsc-daily.json") or {}
    if _num(gsc.get("total_clicks")):
        out["gsc_clicks_28d"] = gsc["total_clicks"]
    if _num(gsc.get("total_impressions")):
        out["gsc_impressions_28d"] = gsc["total_impressions"]
    rows = (_load(mdir, "ga4-daily.json") or {}).get("rows") or []
    if rows:
        out["ga4_users_28d"] = sum(r.get("active_users") or 0 for r in rows)
        out["ga4_new_users_28d"] = sum(r.get("new_users") or 0 for r in rows)
        out["ga4_sessions_28d"] = sum(r.get("sessions") or 0 for r in rows)
    top = objective_top5(mdir)
    if top:
        out["objective_top5"] = top["value"]
    for k, src in (("growth_share_today", "today"), ("growth_share_week", "this_week"),
                   ("growth_share_month", "this_month")):
        v = (split.get(src) or {}).get("share")
        if v is not None:
            out[k] = v
    return out


def progress(goal: dict, measured: dict[str, float], issues: dict[int, dict]) -> dict:
    """{current, progress (0..1 or None), basis}. See the header for the rule."""
    key, base, tgt = goal.get("metric_key"), goal.get("baseline"), goal.get("target")
    if key in measured and _num(base) and _num(tgt) and tgt != base:
        cur = measured[key]
        p = max(0.0, min(1.0, (cur - base) / (tgt - base)))
        return {"current": cur, "progress": round(p, 3), "basis": key}
    known = [n for n in goal.get("issues") or [] if isinstance(n, int) and n in issues]
    if known:
        closed = sum(issues[n].get("state") == "closed" for n in known)
        return {"current": f"{closed}/{len(known)} issues closed", "progress": round(closed / len(known), 3),
                "basis": "issues"}
    return {"current": None, "progress": None, "basis": None}


def meters(goals: dict, measured: dict[str, float], issues: dict[int, dict], split: dict,
           top5: dict | None) -> dict:
    out: dict = {}
    t = split["today"]
    out["daily"] = {"label": "Today: growth share of build cycles", "period": split["today_date"],
                    "progress": None if t["share"] is None else round(min(1.0, t["share"] / TARGET), 3),
                    "detail": f'{t["growth"]} of {t["growth"] + t["other"]} cycles on growth, target 60%'
                              + (f', {t["exempt"]} exempt' if t["exempt"] else ""),
                    "goals": []}
    levels = goals.get("levels") or {}
    for lv in LEVELS:
        info = levels.get(lv) or {}
        rows = [{k: g.get(k) for k in ("id", "goal", "metric", "metric_key", "baseline", "target", "issues")}
                | progress(g, measured, issues)
                for g in (info.get("current") or {}).get("goals") or []]
        ps = [r["progress"] for r in rows if r["progress"] is not None]
        out[lv] = {"label": f"{lv.capitalize()} goals", "period": info.get("period"),
                   "progress": round(sum(ps) / len(ps), 3) if ps else None,
                   "detail": (f"{len(rows)} goals, {len(ps)} measurable" if rows
                              else "no goals set for this period yet (chief sets them in its Sunday review)"),
                   "goals": rows}
    out["overall"] = {"label": "Objective: top-10 queries ranking top 5",
                      "period": "quarter lever (OBJECTIVE.md)",
                      "progress": round(top5["value"] / OBJECTIVE_QUERIES, 3) if top5 else None,
                      "detail": (f'{top5["value"]} of {top5["of"]} highest-impression queries at position ≤ 5'
                                 if top5 else "gsc-trend-query.json unreadable"),
                      "queries": (top5 or {}).get("queries", []), "goals": []}
    return out


# --------------------------------------------------------------- split

def recent_issues(gh: Runner, repo: str, now: datetime) -> dict[int, dict]:
    """Every issue updated in the window, with labels, state and title -- one paginated listing."""
    since = (now - timedelta(days=DAYS + 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = gh(["api", "--paginate", f"repos/{repo}/issues?state=all&since={since}&per_page=100",
              "--jq", '.[] | select(.pull_request == null) | {number, title, state, labels: [.labels[].name]}'])
    out = {}
    for line in raw.splitlines():
        try:
            i = json.loads(line)
        except ValueError:
            continue
        out[i["number"]] = i
    return out


#: At most this many issues are fetched one by one: cycle and goal issues the listing did not
#: return because nothing touched them in the last DAYS+1 days. Unread ones count as `other`.
MAX_SINGLE_READS = 60


def fill_missing(gh: Runner, repo: str, rows: list[dict], issues: dict[int, dict], now: datetime,
                 extra: set[int] = frozenset()) -> None:
    floor = now - timedelta(days=40)       # this month's cycles too, for the monthly share
    want = sorted(({r["issue"] for r in rows if isinstance(r.get("issue"), int)
                    and r.get("kind") in COUNTED_KINDS and (_ts(r.get("started")) or floor) >= floor}
                   | set(extra)) - set(issues))
    for n in want[:MAX_SINGLE_READS]:
        i = json.loads(gh(["api", f"repos/{repo}/issues/{n}"]))
        issues[n] = {"number": n, "title": i.get("title"), "state": i.get("state"),
                     "labels": [l.get("name") for l in i.get("labels") or []]}


def build(rows: list[dict], issues: dict[int, dict], goals: dict, now: datetime,
          mdir: Path | None = None) -> dict:
    goal_issues = goal_issue_numbers(goals)
    today = now.astimezone(IST).date()
    floor = today - timedelta(days=DAYS - 1)
    this_week, this_month = iso_week(now), today.strftime("%Y-%m")
    days = {(floor + timedelta(days=i)).isoformat(): {"growth": 0, "other": 0, "exempt": 0}
            for i in range(DAYS)}
    cycles = []
    week = {"growth": 0, "other": 0, "exempt": 0}
    month = {"growth": 0, "other": 0, "exempt": 0}
    for r in rows:
        at = _ts(r.get("started"))
        if at is None or r.get("kind") not in COUNTED_KINDS or not isinstance(r.get("issue"), int):
            continue
        d = at.astimezone(IST).date()
        if d > today:
            continue
        cls = classify(issues.get(r["issue"]), goal_issues)
        if d.strftime("%Y-%m") == this_month:
            month[cls] += 1
        if d < floor:
            continue
        days[d.isoformat()][cls] += 1
        if iso_week(at) == this_week:
            week[cls] += 1
        cycles.append({"run": r.get("run"), "started": r.get("started"), "issue": r["issue"],
                       "title": (issues.get(r["issue"]) or {}).get("title"), "class": cls,
                       "outcome": r.get("outcome"), "pr": r.get("pr"),
                       "agents": r.get("agents_called")})
    cycles.sort(key=lambda c: c["started"] or "", reverse=True)
    t = days[today.isoformat()]
    split = {
        "today_date": today.isoformat(),
        "today": {**t, "share": _share(t["growth"], t["other"])},
        "this_week": {**week, "share": _share(week["growth"], week["other"])},
        "this_month": {**month, "share": _share(month["growth"], month["other"])},
    }
    measured = metrics(mdir, split) if mdir else {}
    top5 = objective_top5(mdir) if mdir else None
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": TARGET,
        "week": this_week,
        **split,
        "must_pick_growth": must_pick_growth(t["growth"], t["other"]),
        "days": [{"date": k, **v, "share": _share(v["growth"], v["other"])} for k, v in days.items()],
        "cycles": cycles[:40],
        "goals": goals,
        "metrics": measured,
        "meters": meters(goals, measured, issues, split, top5),
        "open_growth": sorted(n for n, i in issues.items()
                             if i.get("state") == "open" and classify(i, goal_issues) == "growth"),
    }


def validate(doc) -> list[str]:
    errs = []
    if not isinstance(doc, dict):
        return ["not an object"]
    for k in ("generated_at", "week", "today", "this_week", "days", "cycles", "goals", "meters"):
        if k not in doc:
            errs.append(f"{k} missing")
    if errs:
        return errs
    if len(doc["days"]) != DAYS:
        errs.append(f"days is not {DAYS} long")
    for d in doc["days"]:
        if any(not isinstance(d.get(k), int) or d[k] < 0 for k in ("growth", "other", "exempt")):
            errs.append(f"day {d.get('date')} has a bad count")
    if any(c.get("class") not in ("growth", "other", "exempt") for c in doc["cycles"]):
        errs.append("a cycle has an unknown class")
    for name in ("daily", "weekly", "monthly", "quarterly", "overall"):
        m = doc["meters"].get(name)
        if not isinstance(m, dict):
            errs.append(f"meter {name} missing")
        elif m.get("progress") is not None and not (0 <= m["progress"] <= 1):
            errs.append(f"meter {name} progress out of 0..1")
    return errs


# --------------------------------------------------------------- posting (agent-sync)

ISSUE_TITLE = "Growth goals: weekly, monthly, quarterly"
ISSUE_BODY = """<!-- weekly-goals-issue -->
The one standing issue for the loop's **growth goals** (owner, 2026-11-19): weekly, monthly and
quarterly. A week is Monday to Sunday (IST).

- `chief` posts goals here from its **Sunday** review: next week's every Sunday, next month's and
  next quarter's when none exist yet, and a score for each period that ends.
- `project-manager` reads the current goals before every ranking and keeps at least 60% of build
  cycles on growth issues (`scripts/growth_split.py`), production breakage excepted.
- `/admin/ops` shows a meter for each level, the scores and the daily split.

Comments here are posted by the `agent-sync` workflow from chief's files. Only comments by the
owner, `claude[bot]` or `github-actions[bot]` are read. Edit a goal by posting a corrected goals
comment for the same period; the newest one wins. This issue is never closed by the loop."""


#: GitHub refuses a comment body over 65,536 characters with a 422.
MAX_BODY = 60_000
_MENTION = re.compile(r"(?<![\w`])@(?=[A-Za-z0-9])")


def neutralise_mentions(body: str) -> str:
    """`@name` -> `@\u200bname`: still readable, pings nobody. The poster is github-actions[bot],
    and chief reads text anyone can write (PR titles in /tmp/week.txt), so an `@everyone` or an
    owner mention in its file must not become a notification (QA on #1241)."""
    return _MENTION.sub("@\u200b", body)


def classify_file(body: str, now: datetime | None = None) -> tuple[str, str, str, dict] | None:
    """(kind 'goals'|'score', level, period, doc) for one of chief's files, or None. With `now`,
    also the posting rules: goals only for this period or the next, a score only for this period
    or the last, and every goal measurable."""
    cal = periods(now) if now else {}
    for lv, (key, _) in LEVELS.items():
        for kind, marks, check in (("score", SCORE_MARKS, _valid_score), ("goals", GOALS_MARKS, _valid_goals)):
            parsed = _parse(body, marks[lv], key)
            if not (parsed and check(parsed[1])):
                continue
            if now is not None:
                allowed = {cal[lv], _shift(lv, cal[lv], 1 if kind == "goals" else -1)}
                if parsed[0] not in allowed or (kind == "goals" and not _measurable(parsed[1])):
                    return None
            return kind, lv, parsed[0], parsed[1]
    return None


def _goals_issue(gh: Runner, repo: str) -> int | None:
    issues = json.loads(gh(["api", f"repos/{repo}/issues?labels={GOALS_LABEL}&state=open&per_page=5"]))
    issues = [i for i in issues if "pull_request" not in i]
    return min(i["number"] for i in issues) if issues else None


def post(gh: Runner, repo: str, path: str, now: datetime, box: "outbox.Outbox | None" = None) -> int:
    """Post one of chief's files on the standing issue, through scripts/outbox.py (#1188):
    dedupe, a daily cap, retry, a ledger line. 0 posted or a duplicate, 3 nothing to post,
    1 refused or failed."""
    f = Path(path)
    if not f.is_file() or not f.read_text().strip():
        print(f"no {path}: nothing to post")
        return 3
    body = neutralise_mentions(f.read_text())
    if len(body) > MAX_BODY:
        print(f"::error::{path} is {len(body)} characters, over {MAX_BODY}; not posted")
        return 1
    got = classify_file(body, now)
    if not got:
        print(f"::error::{path} has no valid marker + ```json block, names a period other than this "
              "one or the next (goals) / the last (scores), or has a goal with neither a known "
              "metric_key nor issues (see growth_split.py header); not posted")
        return 1
    box = box or outbox.Outbox(gh, repo)
    n = _goals_issue(gh, repo)
    if n is None:
        made = box.create_issue("growth-goals-issue", ISSUE_TITLE, ISSUE_BODY, [GOALS_LABEL])
        n = _goals_issue(gh, repo)
        if n is None:
            print(f"::error::could not create the {GOALS_LABEL} issue ({made.outcome}); not posted")
            return 1
    o = box.post(n, "growth-goals", body)
    print(f"{path} ({got[1]} {got[0]}, {got[2]}) on #{n}: {o.outcome}")
    return 0 if o.outcome in ("sent", "deduped") else 1


def main(argv: list[str] | None = None, gh: Runner = run_gh, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=os.environ.get("GH_REPO", "mahAnuj/astro-ai"))
    ap.add_argument("--loop", default="measurements/loop.json")
    ap.add_argument("--measurements", default="measurements", help="directory holding the GSC/GA4 files")
    ap.add_argument("--out", help="write the full document here (agent-measure); else print the decision")
    ap.add_argument("--post", nargs="+", metavar="FILE",
                    help="chief's goals/score files to post on the weekly-goals issue (agent-sync); "
                         "missing files are skipped, an invalid one is refused")
    a = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    if a.post:
        codes = []
        try:
            # scores before goals, so the issue reads in order
            for path in sorted(a.post, key=lambda p: 0 if "score" in Path(p).name else 1):
                codes.append(post(gh, a.repo, path, now))
        except (RuntimeError, ValueError, TypeError) as e:
            print(f"::error::posting failed: {e}")
            return 1
        return 1 if 1 in codes else 0
    try:
        rows = json.loads(Path(a.loop).read_text()).get("rows") or []
    except (OSError, ValueError) as e:
        print(f"::error::cannot read {a.loop}: {e}")
        return 2
    try:
        goals = read_goals(gh, a.repo, now)
        issues = recent_issues(gh, a.repo, now)
        fill_missing(gh, a.repo, rows, issues, now, goal_issue_numbers(goals))
    except (RuntimeError, ValueError, TypeError) as e:
        print(f"::error::GitHub read failed, nothing written: {e}")
        return 1
    try:
        doc = build(rows, issues, goals, now, Path(a.measurements))
    except (TypeError, ValueError, KeyError) as e:
        print(f"::error::could not build the document, nothing written: {e}")
        return 1
    errs = validate(doc)
    if errs:
        print(f"::error::document does not validate, nothing written: {errs}")
        return 1
    if a.out:
        Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
        print(f"growth split: today {doc['today']}, week {doc['this_week']} -> {a.out}")
        return 0
    lv = doc["goals"].get("levels") or {}
    print(json.dumps({
        "week": doc["week"], "today": doc["today"], "this_week": doc["this_week"],
        "this_month": doc["this_month"],
        "must_pick_growth": doc["must_pick_growth"], "target": TARGET,
        "meters": {k: {"progress": m["progress"], "detail": m["detail"]} for k, m in doc["meters"].items()},
        "goals": {k: [{f: g.get(f) for f in ("id", "goal", "metric_key", "target", "issues")}
                      for g in ((v.get("current") or {}).get("goals") or [])] for k, v in lv.items()},
        "direction": ((lv.get("weekly") or {}).get("current") or {}).get("direction")
                     or ((lv.get("weekly") or {}).get("previous_score") or {}).get("direction"),
        "goals_issue": doc["goals"].get("issue"),
        "metric_keys": list(METRIC_KEYS),
        "open_growth_issues": doc["open_growth"][:30],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
