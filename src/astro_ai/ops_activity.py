"""The Recent activity panel on /admin/ops Overview (#1133 slice 2d).

PURE, and it READS NOTHING of its own: `build(ops, links, active)` takes the dict
`ops_data.snapshot()` already assembled and the rail's `tab_links` list, so the panel adds
0 GCS reads, 0 GitHub reads and 0 LLM tokens. The template gets a FULLY PRE-COMPUTED dict
and does no arithmetic (the rule the 2a/2b/2c span tests enforce on the block it lives in).

THREE SOURCES, three row shapes, merged newest first:
  Agent     one agent-work cycle from `loop.json` (outcome from the collector), plus, only
            when today's GitHub read succeeded, each PR merged today (it has the title);
  Workflow  the last run of one workflow from `agents.json` (the ring's own health words,
            `ops_loop_health._wf_state`), plus today's live failed runs;
  Issue     one issue still open, newest filed first.
Closed issues are not listed: `issues.json` carries closed numbers but no titles.
Deployments are not listed: no per-deploy record is collected (slice 4).

SUPERSEDE RULE (the two Workflow sources). Keyed by the workflow's display name,
casefolded (agents.json `display` and the live run `name` are the same GitHub run name). A
live failed run replaces that workflow's agents.json row only if it is strictly newer than
that row's `last_run`; a live row with no matching name is added. It fails OPEN: a name
mismatch costs a second row, never a hidden failure. When `today_live` is not True,
`today_shipped` and `today_failed` are loop rows already counted under Agent, so they are
ignored, otherwise every row would appear twice.

BOUNDED BY CONSTANTS, NOT BY DATA: `ROWS` per view, `TITLE_MAX`/`SUB_MAX` characters, so the
section's worst case is a constant. Each view shows the newest `ROWS` of its OWN kind, so
Issues is not empty because the newest eight overall were workflows.

NO ROW STRING REACHES AN HREF. Every link is built from `GH_REPO` plus a positive int, a
workflow filename matching `_WF_FILE`, or a static table, so a `javascript:` URL or a
lookalike host in a row cannot reach one. The `activity` query value is membership-tested
in `pick_filter` and never echoed.

NEVER RAISES. Each source degrades alone; a source that cannot be read is named in a note
and never rendered as "no activity".
"""
from __future__ import annotations

import heapq
import logging
import math
import re
import unicodedata
from datetime import timezone

from astro_ai.ops_data import GH_REPO, _age, _dict_rows, _ist
from astro_ai.ops_loop_health import _link, _loop_rows, _now, _wf_state, _wf_url, _word

log = logging.getLogger(__name__)

FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "All"), ("agents", "Agents"), ("workflows", "Workflows"), ("issues", "Issues"),
)
ROWS = 8
TITLE_MAX = 90
SUB_MAX = 110
_WF_FILE = re.compile(r"[a-z0-9][a-z0-9._-]{0,60}\.yml")
_KEYS = frozenset(k for k, _ in FILTERS)

#: "View all" target per chip. Runs & Traces lists agent cycles by day and shows no
#: workflow or issue rows, so those two chips link their own tab (a judgement beyond the
#: spec's single link; three lines to revert).
_VIEW_ALL = {"all": "runs", "agents": "runs", "workflows": "workflows", "issues": "backlog"}

#: loop.json `outcome` -> (state, word). Anything else is `unavailable`, never a green.
_OUTCOMES = {
    "shipped": ("ok", "shipped"),
    "pr open": ("watch", "PR open"),
    "failed": ("bad", "failed"),
    "nothing": ("info", "nothing to ship"),
    "judged": ("info", "judged"),
    "unknown": ("watch", "outcome unknown"),
}
_KIND_LABELS = {
    "issue": "Build cycle", "ranked": "Ranked build cycle", "qa-round": "QA round",
    "fix-pr": "Fix cycle", "unknown": "Agent cycle",
}
_TYPE = {"agent": "Agent", "workflow": "Workflow", "issue": "Issue"}
_SOURCE = {"agents": "Agent cycles", "workflows": "Workflows", "issues": "Issues"}
_EMPTY = {"all": "No activity in the data read", "agents": "No agent activity in the data read",
          "workflows": "No workflow activity in the data read",
          "issues": "No issue activity in the data read"}


def pick_filter(raw) -> str:
    """The chip key for a raw `?activity=` value; never raises.

    Membership in `FILTERS` and nothing else: an unknown value falls back to All (the
    `ops_tabs.pick_tab` rule), and the raw value is never echoed anywhere."""
    try:
        key = str(raw or "").strip().lower()
    except Exception:  # noqa: BLE001 - an object whose __str__ raises is still just unknown
        return "all"
    return key if key in _KEYS else "all"


def _text(s, n: int) -> str:
    """`s` for display: "" if not a str, controls and format characters removed,
    whitespace collapsed, cut at `n` characters with an ellipsis."""
    if not isinstance(s, str):
        return ""
    s = "".join(" " if unicodedata.category(c) == "Cc"
                else "" if unicodedata.category(c)[0] == "C" else c for c in s)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _pos_int(v) -> int | None:
    """`v` if it is a real positive int. `True` is not an id; "7" and 1.5 are not ids."""
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else None


def _pull_url(n: int) -> str:
    return f"https://github.com/{GH_REPO}/pull/{n}"


def _issue_url(n: int) -> str:
    return f"https://github.com/{GH_REPO}/issues/{n}"


def _actions_run_url(n: int) -> str:
    return f"https://github.com/{GH_REPO}/actions/runs/{n}"


def _run_url(pr, run) -> str:
    """A cycle's link: its PR, else its run, else "". The single place a cycle link is
    made, so slice 3 can repoint it to a per-cycle page in one line."""
    if _pos_int(pr):
        return _pull_url(pr)
    if _pos_int(run):
        return _actions_run_url(run)
    return ""


def _stamp(ts, now):
    """(datetime, when, at_ist, iso) for a readable time string, else None."""
    dt = _ist(ts) if isinstance(ts, str) else None
    if dt is None:
        return None
    a = _age(ts, now)
    return dt, a["text"], a["at_ist"] or "", dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(kind, state, word, title, subtitle, st, href) -> dict:
    dt, when, at_ist, iso = st
    return {"kind": kind, "state": state, "word": word,
            "title": _text(title, TITLE_MAX), "subtitle": _text(subtitle, SUB_MAX),
            "type_label": _TYPE[kind], "when": when, "at_ist": at_ist, "iso": iso,
            "href": href}


def _newest(cands: list, now) -> list:
    """[(datetime, row)] for the newest ROWS candidates. A candidate is
    (datetime, time string, maker, source row); the maker runs for the kept ones only."""
    top = heapq.nlargest(ROWS, cands, key=lambda c: c[0])
    out = []
    for dt, ts, maker, src in top:
        st = _stamp(ts, now)
        if st is not None:
            out.append((dt, maker(src, st)))
    return out


# ---------------------------------------------------------------- makers

def _cycle_row(r: dict, st) -> dict:
    state, word = _OUTCOMES.get(r.get("outcome"), ("unavailable", "outcome not recognised"))
    label = _KIND_LABELS.get(r.get("kind"), "Agent cycle")
    targets = []
    if _pos_int(r.get("issue")):
        targets.append(f"issue #{r['issue']}")
    if _pos_int(r.get("pr")):
        targets.append(f"PR #{r['pr']}")
    title = label + (" on " + " and ".join(targets) if targets else "")
    parts = [_text(r.get("workflow"), 40)]
    m = r.get("minutes")
    if isinstance(m, (int, float)) and not isinstance(m, bool) and math.isfinite(m) and m >= 0:
        parts.append(f"{m:.0f} min")
    return _row("agent", state, word, title, " · ".join(p for p in parts if p), st,
                _run_url(r.get("pr"), r.get("run")))


def _merged_row(r: dict, st) -> dict:
    by = r.get("by")
    sub = ("merged by the loop" if by == "loop"
           else "merged from a session" if by == "session" else "merged")
    pr = _pos_int(r.get("pr"))
    return _row("agent", "ok", "merged", _text(r.get("title"), TITLE_MAX) or
                (f"PR #{pr}" if pr else "Merged PR"), sub, st, _pull_url(pr) if pr else "")


def _workflow_row(r: dict, st) -> dict:
    state, word = _wf_state(r)
    wf = r.get("workflow")
    name = r.get("display") if _text(r.get("display"), 1) else (wf[:-4] if wf.endswith(".yml") else wf)
    return _row("workflow", state, word, name,
                f"last conclusion: {_word(r.get('last_conclusion'))}", st,
                _wf_url(wf) if _WF_FILE.fullmatch(wf) else "")


def _failed_row(r: dict, st) -> dict:
    run = _pos_int(r.get("run"))
    return _row("workflow", "bad", "failed", _text(r.get("workflow"), TITLE_MAX) or "Workflow run",
                f"run ended {_word(r.get('conclusion'))}", st,
                _actions_run_url(run) if run else "")


def _issue_row(r: dict, st) -> dict:
    n = _pos_int(r.get("number"))
    title = _text(r.get("title"), TITLE_MAX) or (f"Issue #{n}" if n else "Untitled issue")
    sub = " · ".join(p for p in ([f"#{n}"] if n else [])
                     + [_text(r.get("type"), 20), _text(r.get("priority"), 20)] if p)
    blocked = r.get("blocked") is True
    return _row("issue", "watch" if blocked else "info", "blocked" if blocked else "still open",
                title, sub, st, _issue_url(n) if n else "")


# -------------------------------------------------------------- builders
# Each returns ([(datetime, row)], why, skipped): `why` is "" when the source was
# readable, else the reason it was not (never an empty list standing in for "unread").

def _agent_rows(ops, now):
    loop = ops.get("loop") if isinstance(ops, dict) else None
    rows = loop.get("rows") if isinstance(loop, dict) else None
    ok = isinstance(loop, dict) and loop.get("ok") is True and isinstance(rows, list)
    live = isinstance(loop, dict) and loop.get("today_live") is True
    cands, skipped = [], 0
    merged_prs: set[int] = set()
    if live:
        for r in _dict_rows(loop.get("today_shipped")):
            ts = r.get("merged_at")
            dt = _ist(ts) if isinstance(ts, str) else None
            if dt is None:
                skipped += 1
                continue
            if _pos_int(r.get("pr")):
                merged_prs.add(r["pr"])
            cands.append((dt, ts, _merged_row, r))
    for r in rows if ok else []:
        if not isinstance(r, dict):
            skipped += 1
            continue
        if r.get("outcome") == "shipped" and _pos_int(r.get("pr")) in merged_prs:
            continue          # the live row has the title
        ts = r.get("started")
        dt = _ist(ts) if isinstance(ts, str) else None
        if dt is None:
            skipped += 1
            continue
        cands.append((dt, ts, _cycle_row, r))
    return _newest(cands, now), ("" if ok else "loop.json not read"), skipped


def _workflow_rows(ops, now):
    rows, _dup, why = _loop_rows(ops)
    loop = ops.get("loop") if isinstance(ops, dict) else None
    live = isinstance(loop, dict) and loop.get("today_live") is True
    pool: dict = {}
    by_name: dict[str, object] = {}
    skipped = 0
    for wf, r in rows.items():
        ts = r.get("last_run")
        dt = _ist(ts) if isinstance(ts, str) else None
        if dt is None:
            skipped += 1
            continue
        pool[wf] = (dt, ts, _workflow_row, r)
        name = _text(r.get("display"), 200).casefold() or wf[:-4].casefold()
        by_name.setdefault(name, wf)
    if live:
        for r in _dict_rows(loop.get("today_failed")):
            ts = r.get("started")
            dt = _ist(ts) if isinstance(ts, str) else None
            if dt is None:
                skipped += 1
                continue
            name = _text(r.get("workflow"), 200).casefold()
            key = by_name.get(name, ("live", name))
            if key in pool and not dt > pool[key][0]:
                continue      # an equal or older failure never replaces a newer last run
            pool[key] = (dt, ts, _failed_row, r)
    return _newest(list(pool.values()), now), why, skipped


def _issue_rows(ops, now):
    issues = ops.get("issues") if isinstance(ops, dict) else None
    rows = issues.get("rows") if isinstance(issues, dict) else None
    ok = isinstance(issues, dict) and issues.get("ok") is True and isinstance(rows, list)
    cands, skipped = [], 0
    for r in rows if ok else []:
        dt = _ist(r.get("created")) if isinstance(r, dict) and isinstance(r.get("created"), str) else None
        if dt is None:
            skipped += 1
            continue
        cands.append((dt, r["created"], _issue_row, r))
    return _newest(cands, now), ("" if ok else "issues.json not read"), skipped


_BUILDERS = {"agents": _agent_rows, "workflows": _workflow_rows, "issues": _issue_rows}


# ------------------------------------------------------------------ build

def _chips(links, active: str) -> list[dict]:
    base = _link(links, "overview") or "?tab=overview"
    return [{"key": k, "label": label, "href": f"{base}&activity={k}#recent-activity",
             "current": k == active} for k, label in FILTERS]


def _view_all(links, active: str) -> dict:
    target = _VIEW_ALL[active]
    return {"href": _link(links, target) or f"?tab={target}", "text": "View all →"}


def _as_of(ops) -> str:
    ages = ops.get("ages") if isinstance(ops, dict) else None
    parts = []
    for label, key in (("agent cycles", "Delivery"), ("workflows", "Team"), ("issues", "Backlog")):
        a = ages.get(key) if isinstance(ages, dict) else None
        if isinstance(a, dict) and isinstance(a.get("text"), str):
            parts.append(f"{label} {_text(a['text'], 30)}")
    return ", ".join(parts)


def _live_text(ops) -> str:
    loop = ops.get("loop") if isinstance(ops, dict) else None
    if isinstance(loop, dict) and loop.get("today_live") is True:
        return "Today's merges and failed runs are live, read from GitHub."
    return ("Today's merges and failed runs are not shown: GitHub was not read, so this is "
            "the committed snapshot.")


def _unavailable(reason: str, links=None, active: str = "all") -> dict:
    """Every key `build` returns, with empty values, so the template never meets a
    missing one (the rule `ops_loop_health._loop_view` states)."""
    try:
        chips, view_all = _chips(links, active), _view_all(links, active)
    except Exception:  # noqa: BLE001
        chips, view_all = [], {"href": "", "text": "View all →"}
    return {"state": "unavailable", "error": True, "active": active, "chips": chips,
            "rows": [], "reason": reason, "empty_text": "", "notes": [], "skipped": 0,
            "skipped_text": "", "as_of": "", "live_text": "", "view_all": view_all}


def build(ops, links, active="all") -> dict:
    """The Recent activity panel for Overview. Never raises.

    `links` is `ops_tabs.tab_links(...)`: already validated, so no raw query value
    reaches an href. `active` is re-validated here."""
    active = pick_filter(active)
    try:
        now = _now(ops)
        feeding = list(_BUILDERS) if active == "all" else [active]
        pairs, whys, skipped, error = [], {}, 0, False
        for name in feeding:
            try:
                got, why, sk = _BUILDERS[name](ops, now)
            except Exception as exc:  # noqa: BLE001 - one source failing must not take the others
                log.warning("recent activity source %s could not be computed: %s", name, exc)
                got, why, sk, error = [], "could not be computed", 0, True
            pairs.extend(got)
            skipped += sk
            if why:
                whys[name] = why
        rows = [r for _, r in heapq.nlargest(ROWS, pairs, key=lambda p: p[0])]
        notes = [f"{_SOURCE[n]}: {whys[n]}." for n in feeding if n in whys]
        if rows:
            state, reason = "ok", ""
        elif len(whys) == len(feeding):
            state = "unavailable"
            reason = "unavailable: " + "; ".join(whys[n] for n in feeding)
        else:
            state, reason = "empty", ""
        return {
            "state": state, "error": error, "active": active,
            "chips": _chips(links, active), "rows": rows, "reason": reason,
            "empty_text": _EMPTY[active] if state == "empty" else "", "notes": notes,
            "skipped": skipped,
            "skipped_text": (f"{skipped} row{'' if skipped == 1 else 's'} left out: "
                             "no readable time") if skipped else "",
            "as_of": _as_of(ops), "live_text": _live_text(ops),
            "view_all": _view_all(links, active),
        }
    except Exception as exc:  # noqa: BLE001 - last resort: the page must render
        log.warning("Recent activity could not be computed: %s", exc)
        return _unavailable("unavailable: could not be computed", links, active)
