"""Everything /admin/ops renders: committed measurements, plus a live backlog.

Issues: #335 (the page), #345 (the team panel), #353 (the live backlog).

WHERE THE DATA COMES FROM, AND WHY IT IS NOT READ FROM DISK IN PRODUCTION
------------------------------------------------------------------------
`agent-measure` commits three files under `measurements/` (#338):

    loop.json    one row per completed `agent-work` cycle
    cost.json    one row per vendor; `monthly_usd` is null where unreadable
    issues.json  the open backlog with a derived area/type/priority

The Docker image copies only `src/`, so **none of these files exist in the
deployed container** — the architect recorded that caveat on #338 before the
page was written. So this module reads from disk when a `measurements/`
directory is present (a developer's checkout, and the tests) and otherwise
fetches the files over HTTPS from the repository's committed `main`.

ONE PANEL IS LIVE: THE BACKLOG (#353)
-------------------------------------
Open issues are fetched from the GitHub API on the request, with the committed
`issues.json` as the fallback, because that panel is the only one where a live
read is affordable and the only one where staleness actively misleads:

    open issues          1 request    1.08 s      <- live
    agent performance   46 requests     38 s
    loop measurements   48 requests     92 s

The page always says which it is showing -- "live" or "as of 9h ago" -- and a
fallback raises its own amber alert, because a silent downgrade to yesterday's
count is the failure this page exists to catch rather than commit.

Every loader returns `None` on any failure instead of raising. A monitoring
page that 500s because one of its panels has no data is worse than a page that
renders the other three and says so — and a panel that silently shows zeros
would be the exact failure this page exists to catch (#313: four defects each
hid behind a green or absent status).

NO NUMBER ON THIS PAGE IS COMPUTED TWICE
----------------------------------------
The counts handed to the template are derived here from the same rows the
template lists, so a headline can never disagree with the list beneath it.
`cost.json`'s nulls are passed through as null; this module never coerces an
unknown cost to 0, and never sums a column containing one.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from astro_ai import issue_backlog

log = logging.getLogger(__name__)

#: Files this page reads, in the order the template presents them.
FILES = ("loop.json", "cost.json", "issues.json", "agents.json",
         "ga4-daily.json", "gsc-daily.json",
         "gsc-trend-page.json", "gsc-trend-query.json")

#: Committed `main` of the repository the agents work in. Raw content, so no
#: API token and no API rate limit — raw.githubusercontent.com is a CDN.
RAW_BASE = os.environ.get(
    "OPS_RAW_BASE",
    "https://raw.githubusercontent.com/mahAnuj/astro-ai/main/measurements",
)

#: Short, because this runs inside a request. A slow fetch renders an empty
#: panel with a reason rather than holding the page open.
HTTP_TIMEOUT = float(os.environ.get("OPS_HTTP_TIMEOUT", "4"))

#: The files change at most twice a day (the `agent-measure` commit), so a
#: per-process cache this long costs nothing and keeps a reload instant.
CACHE_TTL = float(os.environ.get("OPS_CACHE_TTL", "300"))

#: The repository whose open issues ARE the backlog.
GH_REPO = os.environ.get("OPS_GH_REPO", "mahAnuj/astro-ai")

#: Live backlog, on by default. "0" pins the page to the committed snapshot —
#: what the tests set, and what an environment with no egress wants.
LIVE_ISSUES = os.environ.get("OPS_LIVE_ISSUES", "1") != "0"

#: Optional. A token raises the API budget from 60/hour shared across every
#: tenant on this egress IP to 5,000/hour for this app alone. The live path
#: works without one — it just has less headroom before it falls back.
GH_TOKEN = os.environ.get("OPS_GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or None

#: Asia/Kolkata. The owner reads this page in IST and the schedules are
#: documented in IST ("04:30 IST, after the rolling cap resets"), so every
#: clock time rendered is IST. Fixed offset: India has no DST.
IST = timezone(timedelta(hours=5, minutes=30))

#: The two `agent-work` crons, as UTC hour/minute, from .github/workflows.
#: Used only to say when the next cycle is due.
CRONS_UTC = ((23, 0), (11, 0))

_cache: dict[str, tuple[float, Any]] = {}


def measurements_dir() -> Path | None:
    """The repository's `measurements/` directory, or None in the container.

    `OPS_MEASUREMENTS_DIR` wins when set (the tests set it). Otherwise walk up
    from this file looking for a directory named `measurements` that contains
    at least one of the files we want — a bare empty directory would otherwise
    shadow the HTTP path and leave every panel blank.
    """
    override = os.environ.get("OPS_MEASUREMENTS_DIR")
    if override:
        p = Path(override)
        return p if p.is_dir() else None
    for parent in Path(__file__).resolve().parents:
        cand = parent / "measurements"
        if cand.is_dir() and any((cand / f).is_file() for f in FILES):
            return cand
    return None


def _fetch(name: str) -> Any | None:
    """One file, disk first then HTTPS. None on any failure, with a log line."""
    now = time.monotonic()
    hit = _cache.get(name)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]

    data = None
    local = measurements_dir()
    if local is not None and (local / name).is_file():
        try:
            data = json.loads((local / name).read_text())
        except (OSError, ValueError) as exc:
            log.warning("ops_data: %s on disk is unreadable: %s", name, exc)
    if data is None:
        url = f"{RAW_BASE}/{name}"
        try:
            with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("ops_data: could not fetch %s: %s", url, exc)
            data = None

    if data is not None:
        _cache[name] = (now, data)
    return data


_live_cache: tuple[float, dict] | None = None


def _live_issues(objective: str) -> dict | None:
    """The backlog from the GitHub API, shaped exactly like issues.json.

    WHY THIS PANEL IS LIVE AND THE OTHERS ARE NOT
    ---------------------------------------------
    Because it is the only one that can be. Measured 2026-10-15:

        open issues          1 request    1.08 s
        agent performance   46 requests     38 s
        loop measurements   48 requests     92 s

    The backlog is one call; the other two walk workflow runs and their logs.
    `collect_agent_performance` is 1 workflow list + 2 run queries x 15 active
    workflows + up to 15 commit lookups -- ONE render would spend 46 of the
    60/hour unauthenticated budget, and the cheap shortcut does not exist:
    `/actions/runs?per_page=100` is one request but its newest 100 runs cover
    11 of 15 workflows, and the four it misses are the dormant ones, which are
    exactly the ones worth an alert.

    That panel could not be computed here at any price anyway: `liveness()`
    reads `.github/workflows/*.yml` and `schedule_since()` shells out to
    `git log`, and the image copies `src/` and three files.

    And the backlog is the panel where staleness actually misleads. On
    2026-10-14 the page read `66 open` against 65 actual and the number looked
    WRONG rather than OLD -- which is the whole reason `_age` exists. A count
    that disagrees with GitHub by two is worse than a count that admits it is
    a day behind, and both are worse than the right number.

    Returns None on ANY failure, including a 403 from a rate limit spent by
    another tenant on the same egress IP. The caller then renders the committed
    snapshot and labels it, so a failure here costs freshness, never the panel.
    """
    global _live_cache
    now = time.monotonic()
    if _live_cache and now - _live_cache[0] < CACHE_TTL:
        return _live_cache[1]
    try:
        issues = issue_backlog.fetch_live(
            GH_REPO, timeout=HTTP_TIMEOUT, token=GH_TOKEN)
        # The objective comes from the committed snapshot: it lives in
        # OBJECTIVE.md, which the container does not have. Fetching the
        # backlog live does not make that file appear.
        doc = issue_backlog.build(issues, repo=GH_REPO, objective=objective)
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        log.warning("ops_data: live backlog unavailable, using the snapshot: %s", exc)
        return None
    _live_cache = (now, doc)
    return doc


def _ist(ts: str | None) -> datetime | None:
    """Parse an ISO-8601 Z timestamp into IST. None stays None."""
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).astimezone(IST)
    except ValueError:
        return None


def next_cycle_ist(now: datetime | None = None) -> datetime:
    """When the next scheduled `agent-work` cycle is due, in IST.

    GitHub runs a cron late under load — the 23:00 UTC leg fired at 01:41 UTC
    on 2026-10-14 — so the page labels this "due", never "will run at".
    """
    now = now or datetime.now(timezone.utc)
    best = None
    for day in (0, 1):
        for hh, mm in CRONS_UTC:
            cand = (now + timedelta(days=day)).replace(
                hour=hh, minute=mm, second=0, microsecond=0)
            if cand > now and (best is None or cand < best):
                best = cand
    assert best is not None
    return best.astimezone(IST)


def _loop_view(doc: dict | None, today_ist: str) -> dict:
    """Rows for the ribbon, plus the counts the tiles show.

    `started_ist_minutes` is minutes past IST midnight, which is what the
    ribbon positions a block by. Computed once here so the template holds no
    arithmetic.
    """
    if not doc or not isinstance(doc.get("rows"), list):
        return {"ok": False, "rows": [], "generated_at": None}
    rows = []
    for r in doc["rows"]:
        started = _ist(r.get("started"))
        rows.append({
            **r,
            "date_ist": started.strftime("%Y-%m-%d") if started else r.get("date"),
            "time_ist": started.strftime("%H:%M") if started else "—",
            "started_ist_minutes": started.hour * 60 + started.minute if started else None,
        })
    today = [r for r in rows if r["date_ist"] == today_ist]
    return {
        "ok": True,
        "generated_at": doc.get("generated_at"),
        "rows": rows,
        "outcomes": dict(Counter(r["outcome"] for r in rows).most_common()),
        "attribution": dict(Counter(r.get("attribution") for r in rows).most_common()),
        "today": today,
        "today_shipped": [r for r in today if r["outcome"] == "shipped"],
        "today_failed": [r for r in today if r["outcome"] in ("failed", "unknown")],
        # Newest first in the file; the ribbon wants oldest-day at the bottom.
        "days": sorted({r["date_ist"] for r in rows if r["date_ist"]}, reverse=True),
        "latest": rows[0] if rows else None,
    }


def _age(ts: str | None, now: datetime) -> dict:
    """How old a committed snapshot is, in words.

    WHY THIS EXISTS, MEASURED
    -------------------------
    On 2026-10-14 the page showed `66 open` from a 07:22Z collection while 65
    were actually open -- #329 had closed at 16:13Z. The snapshot time WAS on
    the page, as `2026-10-14T07:22:00Z` in mono. A raw UTC timestamp does not
    read as stale, so the number read as WRONG rather than as OLD. "9h ago"
    reads as old. That is the entire difference this function makes.
    """
    at = _ist(ts)
    if at is None:
        return {"text": "age unknown", "hours": None, "stale": True,
                "at_ist": None}
    hours = (now.astimezone(IST) - at).total_seconds() / 3600.0
    hours = max(hours, 0.0)        # clock skew: never print a negative age
    if hours < 1:
        text = f"{int(hours * 60)}m ago"
    elif hours < 48:
        text = f"{int(hours)}h ago"
    else:
        text = f"{int(hours / 24)}d ago"
    # The collectors run daily, so past 26h a run has been MISSED -- an hour of
    # slack for a late start, not an opinion about how fresh is fresh enough.
    return {"text": text, "hours": round(hours, 1), "stale": hours > 26,
            "at_ist": at.strftime("%d %b %H:%M")}


def _issues_view(doc: dict | None, today_ist: str, *, live: bool = False,
                 fell_back: bool = False) -> dict:
    """Backlog rows plus the three groupings the bars offer for drill-down.

    `live` and `fell_back` travel WITH the numbers rather than being derived
    again by the template, because they are the only thing that says whether
    `open` is this minute's count or yesterday's. A panel that cannot say which
    it is showing is the failure #353 exists to fix.
    """
    if not doc or not isinstance(doc.get("rows"), list):
        return {"ok": False, "rows": [], "live": False, "fell_back": fell_back}
    rows = doc["rows"]
    filed_today = [r for r in rows
                   if (d := _ist(r.get("created"))) and d.strftime("%Y-%m-%d") == today_ist]
    return {
        "ok": True,
        "generated_at": doc.get("generated_at"),
        "live": live,
        "fell_back": fell_back,
        "open": len(rows),
        "rows": rows,
        # Stated, never implied. 29 of 65 issues yielded a readable ask on
        # 2026-10-14, so a column of 29 summaries over 65 rows has to say which
        # number is which or it reads as a column that silently lost 36 rows.
        "with_ask": doc.get("with_ask", sum(1 for r in rows if r.get("ask"))),
        "by_priority": doc.get("by_priority") or dict(Counter(r["priority"] for r in rows)),
        "by_area": doc.get("by_area") or dict(Counter(r["area"] for r in rows)),
        "by_type": doc.get("by_type") or dict(Counter(r["type"] for r in rows)),
        "blocked": [r for r in rows if r.get("blocked")],
        "filed_today": filed_today,
    }


def _nice_top(v: int) -> int:
    """A round number at or above `v`, so the y axis reads 20 rather than 18.

    Without this the top gridline is labelled with whatever the single busiest
    day happened to be, which makes two charts side by side impossible to
    compare and makes the axis look like data rather than a scale.
    """
    if v <= 0:
        return 1
    import math
    mag = 10 ** int(math.floor(math.log10(v)))
    # Fine enough that a peak of 540 tops out at 600, not 1000. A coarse
    # ladder leaves so much headroom the line flattens into the floor and the
    # chart stops showing the shape it exists to show.
    for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if v <= step * mag:
            return int(step * mag)
    return int(10 * mag)


def _series(rows: list[dict], key: str, *, width: float = 100.0, height: float = 100.0) -> dict:
    """Turn a daily series into an SVG path plus the labels an axis needs.

    No charting library: the page loads nothing from a CDN but two fonts, and a
    line through 28 points is arithmetic.

    The y axis starts at ZERO and tops out at a ROUND number, always. A chart
    auto-scaled to its own minimum turns a wobble between 6 and 11 users into a
    cliff, which is the easiest way for a dashboard to mislead while containing
    no false number.

    Axis text is NOT emitted into the SVG. The path is stretched with
    `preserveAspectRatio="none"` so it fills any panel width, and anything
    drawn in the same coordinate system stretches with it -- letters included.
    The labels are returned as plain values for the template to place in HTML
    beside the plot, where they stay legible at any width.
    """
    vals = [r.get(key) or 0 for r in rows]
    if not vals:
        return {"ok": False}
    peak = max(vals)
    top = _nice_top(peak)
    n = len(vals)

    def x_at(i: int) -> float:
        return (i / (n - 1) if n > 1 else 0) * width

    pts = [(x_at(i), height - (v / top) * height) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)

    # One hover band per day, full height, so the pointer never has to find a
    # 2px line. Each carries its own <title>, which is how a reader gets the
    # number for a specific day without any JavaScript.
    band = width / n
    bands = [{
        "x": round(i * band, 3), "w": round(band, 3),
        "value": vals[i],
        "date": rows[i].get("date"),
        "no_data": bool(rows[i].get("no_data")),
        # The point itself, for the dot drawn on hover.
        "px": round(pts[i][0], 2), "py": round(pts[i][1], 2),
    } for i in range(n)]

    # Four x labels at most: first, last, and two inside. More than that and
    # they collide on a phone.
    idx = sorted({0, (n - 1) // 3, 2 * (n - 1) // 3, n - 1})
    return {
        "ok": True,
        "line": line,
        "area": f"{line} {width:.2f},{height:.2f} 0.00,{height:.2f}",
        "top": top,
        "peak": peak,
        "max": peak,          # kept: the template already reads `max`
        "last": vals[-1],
        "first": vals[0],
        "total": sum(vals),
        "n": n,
        # Top, middle, zero — the three the eye actually uses.
        "yticks": [top, top // 2, 0],
        # Horizontal rules at the same three heights, in SVG units.
        "ygrid": [0.0, height / 2, height],
        "xticks": [{"i": i, "pos": round(x_at(i) / width * 100, 2),
                    "date": rows[i].get("date")} for i in idx],
        "bands": bands,
        "labels": [rows[0].get("date"), rows[-1].get("date")],
        "gaps": sum(1 for r in rows if r.get("no_data")),
    }


def _traffic_view() -> dict:
    """The two daily series and the two window-over-window movers.

    Each piece degrades on its own: a missing trend file blanks that table and
    leaves the charts alone, because these are four independent fetches and one
    403 should not take the panel with it.
    """
    ga4 = _fetch("ga4-daily.json") or {}
    gsc = _fetch("gsc-daily.json") or {}
    pages = _fetch("gsc-trend-page.json") or {}
    queries = _fetch("gsc-trend-query.json") or {}

    ga4_rows = ga4.get("rows") or []
    gsc_rows = gsc.get("rows") or []

    def movers(doc: dict, dim: str) -> dict:
        rows = doc.get("rows") or []
        # Already sorted by |delta| in the fetcher; split rather than re-sort so
        # the page and the file can never disagree about what moved most.
        return {
            "ok": bool(rows),
            "dimension": dim,
            "window": doc.get("window"),
            "window_prev": doc.get("window_prev"),
            "coverage_pct": doc.get("coverage_pct"),
            "coverage_note": doc.get("coverage_note"),
            "up": [r for r in rows if r["delta"] > 0][:6],
            "down": [r for r in rows if r["delta"] < 0][:6],
        }

    return {
        "ok": bool(ga4_rows or gsc_rows),
        "window": ga4.get("window") or gsc.get("window"),
        "users": _series(ga4_rows, "active_users"),
        "sessions_total": sum(r.get("sessions") or 0 for r in ga4_rows),
        "impressions": _series(gsc_rows, "impressions"),
        "clicks_total": sum(r.get("clicks") or 0 for r in gsc_rows),
        "ga4_rows": ga4_rows,
        "gsc_rows": gsc_rows,
        "pages": movers(pages, "page"),
        "queries": movers(queries, "query"),
    }


def _cost_view(doc: dict | None, shipped_30d: int) -> dict:
    """Vendor rows, the known subtotal, and the per-issue figure spelled out.

    `known_usd` sums ONLY rows whose `monthly_usd` is a number. `unknown` lists
    the rest by name, so the subtotal is never mistaken for the total — the
    page says "at least $X, plus N items with no readable figure".
    """
    if not doc or not isinstance(doc.get("rows"), list):
        return {"ok": False, "rows": []}
    rows = doc["rows"]
    known = [r for r in rows if isinstance(r.get("monthly_usd"), (int, float))]
    unknown = [r for r in rows if not isinstance(r.get("monthly_usd"), (int, float))]
    known_usd = sum(r["monthly_usd"] for r in known)
    return {
        "ok": True,
        "rows": rows,
        "known_usd": known_usd,
        "unknown": unknown,
        "shipped_30d": shipped_30d,
        # None rather than a divide-by-zero or a flattering 0.
        "per_issue_usd": round(known_usd / shipped_30d, 2) if shipped_30d else None,
    }


def _agents_view() -> dict:
    """Loop liveness, delivery yield and per-agent activity (#345).

    Passed through almost verbatim: the collector already decided every
    verdict, and re-deriving one here would let the page and the file disagree
    about whether a loop is dormant. The only thing added is the ordering the
    table renders in — alerts first, because a page that puts a broken loop
    eleventh is a page nobody reads to row eleven.
    """
    doc = _fetch("agents.json")
    if not doc or not isinstance(doc.get("loops"), list):
        return {"ok": False, "loops": []}
    rank = {"broken": 0, "dormant": 1, "missing-slots": 2, "reporting": 3,
            "ok": 4, "not-due-yet": 5, "on-demand": 6}
    loops = sorted(doc["loops"], key=lambda r: (rank.get(r["verdict"], 9), r["workflow"]))
    return {
        "ok": True,
        "generated_at": doc.get("generated_at"),
        "window_days": doc.get("window_days"),
        "loops": loops,
        "alerts": doc.get("alerts") or [],
        "scheduled": [r for r in loops if r["verdict"] != "on-demand"],
        "delivery": doc.get("delivery") or {},
        "agents": doc.get("agents") or {},
    }


APP_CACHE_TTL = float(os.environ.get("OPS_APP_CACHE_TTL", "60"))
_app_cache: tuple[float, dict] | None = None


def _app_view(days: int = 7) -> dict:
    """App health, read from the app's OWN stores, in-process.

    THE ONE LIVE PANEL, AND WHY IT CAN BE
    -------------------------------------
    Every other panel reads a committed snapshot, because its source is the
    GitHub API and /admin/ops runs on Cloud Run where an unauthenticated call
    is rate-limited per egress IP, shared with every other tenant on it.

    This source is different: `events` and `llm_stats` are THIS app's own GCS
    data, already read in-process by /admin/activity and /admin/usage. Nothing
    to collect, nothing to commit, no external quota. So it is read live on a
    60 s cache rather than once a day.

    NOTHING HERE IS NEW INSTRUMENTATION. Every figure below was already being
    written; none of it had ever been displayed as a rate or a trend.

    A ZERO DENOMINATOR IS NOT HEALTH
    --------------------------------
    With no GCS configured (dev, preview) every counter reads 0, and "0 errors"
    would render as a clean bill of health for an app that recorded nothing at
    all. `measured` is False in that case and the panel says so instead.
    """
    global _app_cache
    now = time.time()
    if _app_cache and now - _app_cache[0] < APP_CACHE_TTL:
        return _app_cache[1]

    # Said on the page, because "0 errors" from a developer's /tmp and from
    # production's bucket looked identical (#355).
    from astro_ai import storage
    store = storage.describe_store()
    out: dict[str, Any] = {"ok": False, "measured": False, "days": days,
                           "store": store, "store_is_local": store.startswith("local:")}
    try:
        from astro_ai import events, llm_stats

        usage = llm_stats.usage_summary(days) or {}
        rng = llm_stats.range_summary(days) or {}
        agg = rng.get("aggregate") or {}
        errors = events.recent(types=["error"], days=days, limit=500) or []

        calls = int(usage.get("total_calls") or 0)
        hits = int(usage.get("cache_hits") or 0)
        misses = max(int(usage.get("cache_misses") or 0), 0)
        fallbacks = int(agg.get("fallbacks") or 0)

        # Per feature. `input_tokens` is only accumulated on a MISS -- a cache
        # hit spends none -- so tokens per request divides by misses, not calls.
        # Dividing by calls would quietly understate every prompt as the cache
        # warms, which is the opposite of what a budget reader needs.
        routes = []
        for r in usage.get("by_route") or []:
            c, h = int(r.get("calls") or 0), int(r.get("hits") or 0)
            m = max(c - h, 0)
            per = (int(r.get("input_tokens") or 0) / m) if m else None
            routes.append({
                "route": r.get("route") or "unknown",
                "calls": c, "hits": h, "misses": m,
                "hit_rate": int(r.get("hit_rate_pct") or 0),
                "input_tokens": int(r.get("input_tokens") or 0),
                "output_tokens": int(r.get("output_tokens") or 0),
                "per_request": round(per) if per is not None else None,
                # None, not 0: no recorded latency means UNKNOWN, and a zero
                # would read as fast. Covers only days recorded since #355.
                "avg_miss_ms": r.get("avg_miss_latency_ms"),
                # What the cache avoided: hits x the mean cost of a miss on
                # this same route. An estimate, and labelled as one on the page.
                "saved": round(h * per) if per is not None else 0,
            })
        routes.sort(key=lambda r: -(r["input_tokens"] or 0))

        # A 413 is a size failure and a 429 is a rate failure; they need
        # opposite fixes. providers.py separates the exception types for
        # exactly this reason, and #266 cost real time to the conflation.
        kinds = Counter((e.get("data") or {}).get("error_type") or "?" for e in errors)
        sources = Counter((e.get("data") or {}).get("source") or "?" for e in errors)
        too_large = sum(v for k, v in kinds.items() if k == "RequestTooLarge")
        exhausted = sum(v for k, v in kinds.items() if k == "AllProvidersExhausted")

        out = {
            "ok": True,
            # The denominator, not a judgement: 0 calls means nothing was
            # recorded, which must never render as "no errors".
            "measured": calls > 0,
            "store": store, "store_is_local": store.startswith("local:"),
            "days": days,
            "calls": calls, "hits": hits, "misses": misses,
            "hit_rate": int(usage.get("hit_rate_pct") or 0),
            "avg_miss_ms": int(usage.get("avg_miss_latency_ms") or 0),
            "errors": len(errors),
            # Per 100 CALLS. Error sources and llm_stats routes are different
            # vocabularies (`chart:matching` vs `matching`), so this is an
            # overall rate; it is deliberately NOT broken down per route,
            # because no mapping between the two exists to do it honestly.
            "error_rate": round(len(errors) / calls * 100, 2) if calls else None,
            "fallbacks": fallbacks,
            # [(provider, reason, n)], most common first. Sums to LESS than
            # `fallbacks` over a window that includes pre-#355 days.
            "fallback_reasons": [
                (k.split("|", 1)[0], k.split("|", 1)[-1], n)
                for k, n in (agg.get("fallback_reasons") or {}).items()
            ],
            "fallback_rate": round(fallbacks / calls * 100, 2) if calls else None,
            # The leading indicator, by day, oldest first.
            "fallback_trend": [int(d.get("fallbacks") or 0)
                               for d in reversed(rng.get("days") or [])],
            "too_large": too_large, "exhausted": exhausted,
            "kinds": kinds.most_common(6),
            "sources": sources.most_common(8),
            "routes": routes,
            "input_tokens": int(usage.get("total_input_tokens") or 0),
            "output_tokens": int(usage.get("total_output_tokens") or 0),
            "by_provider": sorted((agg.get("by_provider") or {}).items(),
                                  key=lambda kv: -kv[1]),
        }
    except Exception:                       # noqa: BLE001 — the page never fails
        log.debug("ops app view failed", exc_info=True)

    _app_cache = (now, out)
    return out


# Thresholds are NAMED, not inlined, because an alert that fires on a magic
# number is an alert nobody can argue with. Each is a judgement and should be
# edited here when it proves wrong.
ERROR_RATE_RED = 5.0      # % of LLM calls producing an error event
ERROR_RATE_AMBER = 1.0
FALLBACK_RATE_AMBER = 2.0  # calls that only succeeded on a second provider


def _alerts(loop: dict, issues: dict, agents: dict, app: dict,
            ages: dict) -> list[dict]:
    """Everything currently wrong, worst first, or an empty list.

    WHY THIS LEADS THE PAGE
    -----------------------
    A dashboard that shows every number equally makes the reader do the
    triage. The panels below answer "how is it going"; this answers the only
    question worth putting first — "is something broken right now".

    TWO RULES THIS MUST NOT BREAK
    -----------------------------
    1. Silence means checked-and-clear, never not-checked. A source that could
       not be read emits its own alert rather than contributing nothing, so an
       empty strip can be trusted.
    2. No green badges. A row of reassurance for every passing check is noise
       that teaches the reader to skip the strip, and the one day it turns red
       they will skip it too.
    """
    out: list[dict] = []

    def add(level, title, detail, where=""):
        out.append({"level": level, "title": title, "detail": detail, "where": where})

    # --- the product ----------------------------------------------------
    if not app.get("ok"):
        add("amber", "App health unreadable",
            "events and llm_stats could not be read, so nothing below covers the product.")
    elif not app.get("measured"):
        add("amber", "No LLM calls recorded",
            f"Nothing in the last {app.get('days')} days. Either the app is idle or "
            "stats are not reaching GCS — a zero here is not a clean bill of health.")
    else:
        rate = app.get("error_rate") or 0.0
        if rate >= ERROR_RATE_RED:
            add("red", f"{rate}% of LLM calls are erroring",
                f"{app['errors']} error events against {app['calls']} calls in "
                f"{app['days']} days.", "/admin/activity")
        elif rate >= ERROR_RATE_AMBER:
            add("amber", f"Error rate {rate}%",
                f"{app['errors']} of {app['calls']} calls.", "/admin/activity")
        if app.get("exhausted"):
            add("red", f"{app['exhausted']} requests had every provider fail",
                "AllProvidersExhausted — the user saw the \u201chigh demand\u201d page, "
                "not a reading.", "/admin/activity")
        if app.get("too_large"):
            add("red", f"{app['too_large']} requests exceeded the provider's size limit",
                "RequestTooLarge (413) is a prompt-size failure, not a rate limit. "
                "Shrinking the prompt is the fix; waiting is not.", "/admin/activity")
        fr = app.get("fallback_rate") or 0.0
        if fr >= FALLBACK_RATE_AMBER:
            add("amber", f"{fr}% of calls needed a second provider",
                "Rising fallbacks arrive BEFORE user-visible failure.", "/admin/usage")

    # --- the agent team -------------------------------------------------
    for lp in (agents.get("loops") or []):
        # Keys are the collector's own: runs_scheduled / slots_due / last_run.
        # Guessing `ran`/`due` printed "0 of 0 scheduled runs succeeded" next to
        # the word BROKEN -- a line that argues against its own headline, which
        # is worse than no detail at all.
        ran, due = lp.get("runs_scheduled", 0), lp.get("slots_due", 0)
        last = (lp.get("last_run") or "")[:10]
        if lp.get("verdict") == "broken":
            add("red", f"{lp.get('workflow')} is broken",
                f"Last run {last or 'unknown'} ended "
                f"{lp.get('last_conclusion') or 'badly'}"
                + (f"; {ran} of {due} scheduled slots ran." if due else "."),
                lp.get("display") or "")
        elif lp.get("verdict") == "missing-slots":
            add("amber", f"{lp.get('workflow')} missed scheduled runs",
                f"{ran} of {due} slots since {(lp.get('schedule_since') or '')[:10]}.",
                lp.get("display") or "")

    if loop.get("ok") and loop.get("today_failed"):
        add("amber", f"{len(loop['today_failed'])} cycle(s) failed today",
            "A cycle that did not deliver leaves its issue untouched.")

    # --- the data under the page ----------------------------------------
    # Rule 1 above: a source that could not be read says so. The backlog is
    # normally live, so falling back to the committed file is a FAILED API
    # call, not a quiet downgrade -- and the figure it fell back to may be a
    # day old while the strip above it stays silent.
    if issues.get("fell_back"):
        add("amber", "Backlog fell back to the committed snapshot",
            "The live GitHub call failed, most likely the 60/hour unauthenticated "
            "budget on a shared egress IP. The count below is as of the last "
            "collection, not now.")

    for name, a in (ages or {}).items():
        # A live panel has no age to be stale. Reporting "Backlog data is 0m
        # ago" as an alert would be a row that fires every single render.
        if name == "Backlog" and issues.get("live"):
            continue
        if a.get("stale"):
            add("amber", f"{name} data is {a.get('text')}",
                "A daily collection has been missed, so the figures below are older "
                "than one run.")

    order = {"red": 0, "amber": 1}
    out.sort(key=lambda a: order.get(a["level"], 9))
    return out


def snapshot(now: datetime | None = None) -> dict:
    """Everything /admin/ops renders, in one dict. Never raises."""
    now = now or datetime.now(timezone.utc)
    now_ist = now.astimezone(IST)
    today_ist = now_ist.strftime("%Y-%m-%d")

    loop_doc = _fetch("loop.json")
    # Live first, committed file second. The snapshot is read either way: it
    # carries the objective, which is not in the container, and it is what the
    # page falls back to when the API call fails.
    snap_doc = _fetch("issues.json")
    live_doc = _live_issues((snap_doc or {}).get("objective") or "") if LIVE_ISSUES else None
    issues_doc = live_doc or snap_doc
    loop = _loop_view(loop_doc, today_ist)
    issues = _issues_view(issues_doc, today_ist, live=live_doc is not None,
                          fell_back=LIVE_ISSUES and live_doc is None)

    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    shipped_30d = sum(1 for r in loop["rows"]
                      if r["outcome"] == "shipped" and (r["date_ist"] or "") >= cutoff)
    cost = _cost_view(_fetch("cost.json"), shipped_30d)
    traffic = _traffic_view()
    agents = _agents_view()
    app = _app_view()
    ages = {
        "Delivery": _age((loop_doc or {}).get("generated_at"), now),
        "Backlog": _age((issues_doc or {}).get("generated_at"), now),  # "live" when fetched
        "Team": _age((_fetch("agents.json") or {}).get("generated_at"), now),
    }

    alerts = _alerts(loop, issues, agents, app, ages)

    return {
        "alerts": alerts,
        "reds": sum(1 for a in alerts if a["level"] == "red"),
        "now_ist": now_ist,
        "today_ist": today_ist,
        "next_cycle_ist": next_cycle_ist(now),
        "loop": loop,
        "issues": issues,
        "cost": cost,
        "traffic": traffic,
        "agents": agents,
        "app": app,
        "source": "disk" if measurements_dir() else "github",
        # Where the backlog specifically came from, which is no longer the same
        # answer as `source` now that one panel is fetched per request.
        "issues_source": ("the GitHub API, live" if live_doc is not None
                          else "measurements/issues.json"),
        # The one line every loop ranks against, carried in issues.json because
        # the Docker image copies only `src/` -- OBJECTIVE.md is not in the
        # container. "" when chief has not written one, which is a real state.
        "objective": (snap_doc or {}).get("objective") or "",
        # Per-source age, so a count can be read as of a time rather than as
        # now. Keyed by the panel that shows it, not by filename.
        "ages": ages,
        # Named so the footer can say which panel is missing rather than
        # rendering an empty one with no explanation.
        "missing": [n for n, v in (("loop.json", loop["ok"]),
                                   ("cost.json", cost["ok"]),
                                   ("issues.json", issues["ok"]),
                                   ("traffic", traffic["ok"]),
                                   ("agents.json", agents["ok"]),
                                   ("app health", app["ok"])) if not v],
    }
