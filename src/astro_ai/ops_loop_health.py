"""The engineering-loop ring, Agent health and System health on /admin/ops Overview
(#1133 slice 2c).

PURE, and it READS NOTHING of its own. `build(ops, agents_now, tabs_health, links)` takes
the dict `ops_data.snapshot()` already assembled, the cards `agent_status.snapshot()` the
route already fetched for every tab, the rail's `ops_tabs.health` block and its
`tab_links` list, so the three panels add 0 GCS reads, 0 GitHub reads and 0 LLM tokens.
The template gets a FULLY PRE-COMPUTED dict (geometry rounded, every text, every state,
every href, every aria string) and does no arithmetic, the rule the 2a/2b span tests
enforce on the block it lives in.

THE RING. Seven steps, one static table (`STEPS`). A step's state is the worst of its
workflows' `last_run_health` in `agents.json`, which is the COLLECTOR's colour and the
only authority: `loop-outcomes` exits non-zero by contract when it finds something, so
its last conclusion reads `failure` with health `amber`, and mapping the conclusion
string here would paint a working report as a crash (`ops_data._last_run_failed`). A
workflow with no row, a duplicated row or a health outside the four known values is
`unavailable`, never `ok`: absence is not a green. Nothing says which step is "current",
so none is marked.

`agents.json` is as of its LAST COLLECTION, not live: a step reading `running` says
"running at last collection", and the panel carries the Team age.

AGENT HEALTH is read from `agent_status.snapshot()["agents"]` (the `group` and `state`
of each card), per group in the snapshot's group order. Counts are made here from the
cards, not from the snapshot's own `counts`, so a card with no `state` is counted as
skipped rather than as zero.

SYSTEM HEALTH, four rows. Each threshold lives in ONE place and is called, never copied:
`ops_data._app_alerts` (LLM providers), `ops_data._last_run_failed` (GitHub Actions),
`ops_tabs.health` (Monitoring, the same words as the rail). The Website row is the last
`verify-production` run and says it is NOT an uptime monitor (owner, 2026-11-17: uptime
shows unavailable). No row says "operational" or "all healthy": only what was checked.

NEVER RAISES. Each panel degrades alone to `unavailable` and `error` says one did.
Every string from `agents.json` reaches the page through Jinja autoescape; a conclusion is
printed only if it matches `_WORD`, a cron only if it matches `_CRON`; no row string
reaches an href (workflow URLs are built from the static filenames in `STEPS`).
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone

from astro_ai.agent_status import STATES
from astro_ai.ops_data import (GH_REPO, _age, _app_alerts, _dict_rows,
                               _last_run_failed)

log = logging.getLogger(__name__)

#: A last run older than this is not evidence the site is fine today. verify-production
#: runs weekly (Mon 06:17 UTC) and on each deploying push, so a week plus a day of slack.
PROD_STALE_DAYS = 8
PROD_WORKFLOW = "verify-production.yml"

_WORD = re.compile(r"[a-z_ ]{1,24}")
_CRON = re.compile(r"[0-9*/,\- ]{1,40}")
_HEALTH = {"green": "ok", "amber": "watch", "red": "bad", "running": "running"}
#: Worst first. `unavailable` outranks `running` and `ok`: a step with a workflow we could
#: not read cannot be called ok.
_SEVERITY = {"bad": 4, "watch": 3, "unavailable": 2, "running": 1, "ok": 0}
STATE_WORDS = {
    "ok": "last run green",
    "watch": "last run amber",
    "bad": "last run red",
    "running": "running at last collection",
    "unavailable": "unavailable",
}
_BAD_CONCLUSIONS = {"failure", "timed_out", "cancelled", "startup_failure"}

#: (n, name, workflow files, static cadence caption, tab the step links to). The caption
#: was checked against each workflow's `on:` on 2026-11-27 (agent-measure daily + after each
#: Agent work run; agent-prioritise Sun, agent-discover Mon; agent-work six crons a day;
#: pr-gates on a PR push, a push to main and a daily cron; agent-merge */30 and after PR
#: gates; verify-production on a deploying push to main and weekly; loop-outcomes weekly).
#: The legend ALSO prints the real cron from agents.json, so a caption that drifts is visible.
STEPS: tuple[tuple[int, str, tuple[str, ...], str, str], ...] = (
    (1, "Measure", ("agent-measure.yml",), "daily", "workflows"),
    (2, "Decide", ("agent-prioritise.yml", "agent-discover.yml"), "weekly", "workflows"),
    (3, "Build", ("agent-work.yml",), "back to back", "runs"),
    (4, "Check", ("pr-gates.yml",), "each PR push", "workflows"),
    (5, "Merge", ("agent-merge.yml",), "every 30 min", "workflows"),
    (6, "Ship & Verify", (PROD_WORKFLOW,), "each deploy", "workflows"),
    (7, "Score", ("loop-outcomes.yml",), "weekly", "workflows"),
)

# Ring geometry (SVG user units; the template scales it).
_W, _H = 560, 380
_CX, _CY, _R, _NODE_R = 280, 190, 120, 20
_RING_CAPTION = "One change, from data to production and back"


def _link(links, key: str) -> str:
    """The href the rail already built for tab `key`; "" when it is not there.
    Same contract as `ops_trends._link`: no raw query value reaches an href."""
    for lk in links if isinstance(links, list) else []:
        if isinstance(lk, dict) and lk.get("key") == key and isinstance(lk.get("href"), str):
            return lk["href"]
    return ""


def _wf_url(workflow: str) -> str:
    """A workflow's GitHub page, from a STATIC filename (never a row string)."""
    return f"https://github.com/{GH_REPO}/actions/workflows/{workflow}"


def _now(ops) -> datetime:
    n = ops.get("now_ist") if isinstance(ops, dict) else None
    return n if isinstance(n, datetime) else datetime.now(timezone.utc)


def _word(s) -> str:
    """A conclusion for display: only a short lower-case word, else "unknown"."""
    if isinstance(s, str) and _WORD.fullmatch(s):
        return s.replace("_", " ").strip() or "unknown"
    return "unknown"


def _loop_rows(ops) -> tuple[dict[str, dict], set[str], str]:
    """({workflow: row}, duplicated workflows, why-not) from `ops["agents"]`.

    Re-screened here: this module does not rely on `ops_data._agents_view` having done
    it. A workflow named twice is dropped whole, because which copy is right is
    unknowable (the `ops_trends._daily` rule)."""
    agents = ops.get("agents") if isinstance(ops, dict) else None
    if not isinstance(agents, dict) or agents.get("ok") is not True:
        return {}, set(), "agents.json not read"
    if not isinstance(agents.get("loops"), list):
        return {}, set(), "agents.json has no loops list"
    seen: dict[str, dict] = {}
    dup: set[str] = set()
    for r in _dict_rows(agents["loops"]):
        wf = r.get("workflow")
        if not isinstance(wf, str):
            continue
        if wf in seen:
            dup.add(wf)
        else:
            seen[wf] = r
    for wf in dup:
        del seen[wf]
    return seen, dup, ""


def _cadence_text(row: dict) -> str:
    c = row.get("cadence")
    crons = [x.strip() for x in c if isinstance(x, str) and _CRON.fullmatch(x.strip())] \
        if isinstance(c, list) else []
    return ("cron " + "; ".join(crons) + " (UTC)") if crons else "on events"


def _last_text(row: dict, now: datetime) -> str:
    a = _age(row.get("last_run") if isinstance(row.get("last_run"), str) else None, now)
    if a["hours"] is None:
        return "no run recorded"
    return f"{a['text']} · {a['at_ist']} IST"


def _wf_state(row: dict | None, why: str = "") -> tuple[str, str]:
    """(state, word) for one workflow, from `last_run_health` alone."""
    if row is None:
        return "unavailable", why or "unavailable: no row in agents.json"
    state = _HEALTH.get(row.get("last_run_health"), "unavailable") \
        if isinstance(row.get("last_run_health"), str) else "unavailable"
    return state, STATE_WORDS[state]


def _workflow(f: str, rows: dict, dup: set, why: str, now: datetime) -> dict:
    row = rows.get(f)
    if f in dup:
        state, word = "unavailable", "unavailable: named twice in agents.json"
    else:
        state, word = _wf_state(row, f"unavailable: {why}" if why else "")
    concl = row.get("last_conclusion") if row else None
    return {
        "file": f, "name": f[:-4] if f.endswith(".yml") else f, "url": _wf_url(f),
        "state": state, "word": word,
        "cadence": _cadence_text(row) if row else "no schedule read",
        "last": _last_text(row, now) if row else "no run recorded",
        "conclusion": "none recorded" if concl in (None, "") else _word(concl),
    }


# ---------------------------------------------------------------- the ring

def _polar(deg: float, r: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return _CX + r * math.cos(rad), _CY + r * math.sin(rad)


def _ring(ops, links) -> dict:
    rows, dup, why = _loop_rows(ops)
    now = _now(ops)
    n = len(STEPS)
    step = 360.0 / n
    # Half the angle a node covers, plus a gap, so an arrow starts and ends clear of the
    # circles it joins.
    gap = math.degrees((_NODE_R + 5) / _R)
    nodes = []
    for i, (num, name, files, caption, tab) in enumerate(STEPS):
        ang = -90.0 + i * step
        x, y = _polar(ang, _R)
        lx, ly = _polar(ang, _R + _NODE_R + 10)
        c = math.cos(math.radians(ang))
        anchor = "middle" if abs(c) < 0.25 else ("start" if c > 0 else "end")
        wfs = [_workflow(f, rows, dup, why, now) for f in files]
        state = max((w["state"] for w in wfs), key=lambda s: _SEVERITY[s])
        word = STATE_WORDS[state]
        # A step above the circle puts its text above; below puts it below.
        s = math.sin(math.radians(ang))
        name_y = ly + (4 if abs(s) < 0.9 else (-14 if s < 0 else 12))
        nodes.append({
            "n": num, "name": name, "caption": caption, "state": state, "word": word,
            "href": _link(links, tab), "workflows": wfs,
            "x": round(x, 1), "y": round(y, 1), "r": _NODE_R,
            "label_x": round(lx, 1), "name_y": round(name_y, 1),
            "caption_y": round(name_y + 14, 1), "anchor": anchor,
            "aria": f"Step {num}, {name}, {caption}: {word}",
        })
    arrows = []
    for i in range(n):
        a0 = -90.0 + i * step + gap
        a1 = -90.0 + (i + 1) * step - gap
        (x0, y0), (x1, y1) = _polar(a0, _R), _polar(a1, _R)
        arrows.append({"from": i + 1, "to": (i + 1) % n + 1,
                       "d": f"M {x0:.1f} {y0:.1f} A {_R} {_R} 0 0 1 {x1:.1f} {y1:.1f}"})
    team = ((ops.get("ages") or {}).get("Team") if isinstance(ops, dict) else None) or {}
    return {
        "state": "ok" if not why else "unavailable",
        "reason": f"unavailable: {why}" if why else "",
        "as_of": f"as of {team.get('text')}" if isinstance(team.get("text"), str) else "",
        "stale": bool(team.get("stale")),
        "caption": _RING_CAPTION,
        "w": _W, "h": _H, "cx": _CX, "cy": _CY, "node_r": _NODE_R,
        "nodes": nodes, "arrows": arrows,
        "aria": ("The engineering loop, seven steps in a ring: "
                 + "; ".join(nd["aria"] for nd in nodes)
                 + (f". {why}." if why else ". States are as of the last collection.")),
        "table": [{"n": nd["n"], "name": nd["name"],
                   "last": "; ".join(w["last"] for w in nd["workflows"]),
                   "result": nd["word"]} for nd in nodes],
    }


def _ring_unavailable(reason: str) -> dict:
    return {"state": "unavailable", "reason": reason, "as_of": "", "stale": False,
            "caption": _RING_CAPTION, "w": _W, "h": _H, "cx": _CX, "cy": _CY,
            "node_r": _NODE_R, "nodes": [], "arrows": [], "aria": reason, "table": []}


# ------------------------------------------------------------ agent health

def _group_row(name: str, cards: list[dict], href: str) -> dict:
    counts: dict[str, int] = {}
    for c in cards:
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    order = [s for s in STATES if s in counts] + sorted(s for s in counts if s not in STATES)
    failed, blocked = counts.get("failed", 0), counts.get("blocked", 0)
    if failed:
        state, word = "bad", f"{failed} failed"
    elif blocked:
        state, word = "watch", f"{blocked} blocked"
    else:
        state, word = "ok", "none failed"
    return {"name": name, "label": name[:1].upper() + name[1:], "n": len(cards),
            "state": state, "word": word, "href": href,
            "counts_text": " · ".join(f"{counts[s]} {s}" for s in order)}


def _agent_health(agents_now, links) -> dict:
    href = _link(links, "agents")
    cards_raw = agents_now.get("agents") if isinstance(agents_now, dict) else None
    cards, skipped = [], 0
    for c in cards_raw if isinstance(cards_raw, list) else []:
        g = c.get("group") if isinstance(c, dict) else None
        s = c.get("state") if isinstance(c, dict) else None
        if isinstance(g, str) and g.strip() and isinstance(s, str) and s.strip():
            cards.append({"group": g.strip()[:24], "state": s.strip()[:24]})
        else:
            skipped += 1
    if not cards:
        return {"state": "unavailable",
                "reason": "unavailable: agent_status returned no agents",
                "header": "", "note": "", "live_text": "", "skipped": skipped,
                "skipped_text": "", "href": href, "groups": []}
    order = [g.strip()[:24] for g in (agents_now.get("groups") or [])
             if isinstance(g, str) and g.strip()] if isinstance(agents_now.get("groups"), list) else []
    for c in cards:           # a group the snapshot did not list still gets a row
        if c["group"] not in order:
            order.append(c["group"])
    groups = [_group_row(g, [c for c in cards if c["group"] == g], href)
              for g in dict.fromkeys(order) if any(c["group"] == g for c in cards)]
    live = agents_now.get("live")
    return {
        "state": "ok", "reason": "",
        "header": f"{len(cards)} cards · {len(groups)} groups",
        "note": ("One card, merge, is a workflow, not an agent. architect and the two "
                 "engineers have no run of their own: they read standby while a build "
                 "cycle runs and idle otherwise."),
        "live_text": ("live, read from GitHub" if live is True
                      else "last known, GitHub not read"),
        "skipped": skipped,
        "skipped_text": (f"{skipped} card{'' if skipped == 1 else 's'} skipped: "
                         "missing group or state") if skipped else "",
        "href": href, "groups": groups,
    }


# ----------------------------------------------------------- system health

def _row(key: str, name: str, state: str, word: str, detail: str, *, as_of: str = "",
         href: str = "", link_text: str = "") -> dict:
    return {"key": key, "name": name, "state": state, "word": word, "detail": detail,
            "as_of": as_of, "href": href, "link_text": link_text}


def _unavail(key: str, name: str, why: str, href: str = "", link_text: str = "") -> dict:
    return _row(key, name, "unavailable", f"unavailable: {why}", "", href=href,
                link_text=link_text)


def _sys_llm(ops, links) -> dict:
    href = _link(links, "monitoring")
    app = ops.get("app") if isinstance(ops, dict) else None
    if not isinstance(app, dict) or app.get("ok") is not True:
        return _unavail("llm", "LLM providers", "the app's own stores could not be read",
                        href, "Monitoring")
    days = app.get("days")
    window = f"last {days} days" if isinstance(days, int) and not isinstance(days, bool) \
        else "this window"
    found = _app_alerts(app)
    reds = [a for a in found if a.get("level") == "red"]
    ambers = [a for a in found if a.get("level") != "red"]
    more = lambda xs: f" (+{len(xs) - 1} more)" if len(xs) > 1 else ""  # noqa: E731
    if reds:
        state, word, detail = "bad", "failing", f"{reds[0].get('title')}{more(reds)}"
    elif ambers:
        state, word, detail = "watch", "needs a look", f"{ambers[0].get('title')}{more(ambers)}"
    else:
        state, word, detail = "ok", "no findings", f"no findings in the {window}"
    return _row("llm", "LLM providers", state, word, str(detail), as_of=window,
                href=href, link_text="Monitoring")


def _sys_actions(ops, links) -> dict:
    href = _link(links, "workflows")
    rows, _dup, why = _loop_rows(ops)
    if why:
        return _unavail("actions", "GitHub Actions", why, href, "Workflows")
    agents = ops["agents"]
    loops = [r for r in _dict_rows(agents.get("loops"))
             if isinstance(r.get("workflow"), str) and isinstance(r.get("verdict"), str)]
    broken = [r["workflow"] for r in loops if r["verdict"] == "broken"]
    watch = [r["workflow"] for r in loops
             if r["verdict"] == "missing-slots" or _last_run_failed(r)]
    alerts = agents.get("alerts")
    n_alerts = len(alerts) if isinstance(alerts, list) else 0
    team = (ops.get("ages") or {}).get("Team") or {}
    as_of = f"as of {team['text']}" if isinstance(team.get("text"), str) else ""
    names = lambda xs: ", ".join(x[:-4] if x.endswith(".yml") else x for x in xs[:3]) \
        + (f" and {len(xs) - 3} more" if len(xs) > 3 else "")  # noqa: E731
    if broken:
        state, word = "bad", f"{len(broken)} broken"
        detail = f"broken: {names(broken)}"
    elif watch:
        state, word = "watch", f"{len(watch)} to check"
        detail = f"missed slots or a failed last run: {names(watch)}"
    elif team.get("stale") is True:
        state, word = "watch", "collection stale"
        detail = "the loop snapshot is older than a day, so these counts may have moved"
    else:
        state, word = "ok", "none broken"
        detail = "no loop broken, behind schedule or ending red"
    detail += f"; {len(loops)} loops read, {n_alerts} alert{'' if n_alerts == 1 else 's'} listed"
    return _row("actions", "GitHub Actions", state, word, detail, as_of=as_of,
                href=href, link_text="Workflows")


def _sys_website(ops, now: datetime) -> dict:
    url = _wf_url(PROD_WORKFLOW)
    rows, dup, why = _loop_rows(ops)
    name = "Website (production)"
    note = "A check run on each deploy and weekly, not an uptime monitor."
    if why:
        return _unavail("website", name, why, url, "verify-production on GitHub")
    row = rows.get(PROD_WORKFLOW)
    if row is None:
        return _unavail("website", name, "verify-production not in agents.json",
                        url, "verify-production on GitHub")
    concl = row.get("last_conclusion")
    age = _age(row.get("last_run") if isinstance(row.get("last_run"), str) else None, now)
    last = f"{age['text']} · {age['at_ist']} IST" if age["hours"] is not None else "no run time recorded"
    word_c = _word(concl)
    if concl in _BAD_CONCLUSIONS:
        state, word = "bad", f"last check {word_c}"
    elif concl == "in_progress":
        state, word = "running", "check running at last collection"
    elif age["hours"] is not None and age["hours"] > PROD_STALE_DAYS * 24:
        state, word = "watch", "stale"
    elif concl == "success":
        state, word = "ok", "last check passed"
    else:
        state, word = "watch", f"last check {word_c}"
    return _row("website", name, state, word, f"last run {last}. {note}",
                as_of=age["text"] if age["hours"] is not None else "",
                href=url, link_text="verify-production on GitHub")


def _sys_monitoring(tabs_health, links) -> dict:
    href = _link(links, "monitoring")
    h = tabs_health
    if (isinstance(h, dict) and h.get("state") in ("ok", "watch", "bad")
            and isinstance(h.get("label"), str) and isinstance(h.get("detail"), str)):
        return _row("monitoring", "Monitoring & alerts", h["state"], h["label"], h["detail"],
                    href=href, link_text="Monitoring")
    return _unavail("monitoring", "Monitoring & alerts", "the page's findings were not computed",
                    href, "Monitoring")


def _system(ops, tabs_health, links) -> dict:
    now = _now(ops)
    error = False
    rows = []
    for key, name, fn in (("llm", "LLM providers", lambda: _sys_llm(ops, links)),
                          ("actions", "GitHub Actions", lambda: _sys_actions(ops, links)),
                          ("website", "Website (production)", lambda: _sys_website(ops, now)),
                          ("monitoring", "Monitoring & alerts",
                           lambda: _sys_monitoring(tabs_health, links))):
        try:
            rows.append(fn())
        except Exception as exc:  # noqa: BLE001 - one row failing must not take the others
            log.warning("system health row %s could not be computed: %s", key, exc)
            rows.append(_unavail(key, name, "could not be computed"))
            error = True
    return {"state": "ok", "rows": rows, "error": error}


# -------------------------------------------------------------------- build

def _unavailable(reason: str) -> dict:
    return {"error": True, "ring": _ring_unavailable(reason),
            "agents": {"state": "unavailable", "reason": reason, "header": "", "note": "",
                       "live_text": "", "skipped": 0, "skipped_text": "", "href": "",
                       "groups": []},
            "system": {"state": "unavailable", "error": True,
                       "rows": [_unavail(k, n, "could not be computed") for k, n in
                                (("llm", "LLM providers"), ("actions", "GitHub Actions"),
                                 ("website", "Website (production)"),
                                 ("monitoring", "Monitoring & alerts"))]}}


def build(ops, agents_now, tabs_health, links) -> dict:
    """{"error", "ring", "agents", "system"} for Overview. Never raises.

    `links` is `ops_tabs.tab_links(...)`: already validated, so no raw query value
    reaches an href. Each panel degrades alone; `error` is True when any had to.
    """
    try:
        error = False
        try:
            ring = _ring(ops, links)
        except Exception as exc:  # noqa: BLE001 - the page must render without the ring
            log.warning("engineering-loop ring could not be computed: %s", exc)
            ring, error = _ring_unavailable("unavailable: could not be computed"), True
        try:
            agents = _agent_health(agents_now, links)
        except Exception as exc:  # noqa: BLE001
            log.warning("Agent health could not be computed: %s", exc)
            agents, error = _unavailable("unavailable: could not be computed")["agents"], True
        system = _system(ops, tabs_health, links)
        return {"error": error or system["error"], "ring": ring, "agents": agents,
                "system": system}
    except Exception as exc:  # noqa: BLE001 - last resort: the page must render
        log.warning("Overview loop health could not be computed: %s", exc)
        return _unavailable("unavailable: could not be computed")
