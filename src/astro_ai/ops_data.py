"""Read the committed ops measurements for /admin/ops (#335, slice 2 of 3).

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


def _issues_view(doc: dict | None, today_ist: str) -> dict:
    """Backlog rows plus the three groupings the bars offer for drill-down."""
    if not doc or not isinstance(doc.get("rows"), list):
        return {"ok": False, "rows": []}
    rows = doc["rows"]
    filed_today = [r for r in rows
                   if (d := _ist(r.get("created"))) and d.strftime("%Y-%m-%d") == today_ist]
    return {
        "ok": True,
        "generated_at": doc.get("generated_at"),
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


def snapshot(now: datetime | None = None) -> dict:
    """Everything /admin/ops renders, in one dict. Never raises."""
    now = now or datetime.now(timezone.utc)
    now_ist = now.astimezone(IST)
    today_ist = now_ist.strftime("%Y-%m-%d")

    loop_doc = _fetch("loop.json")
    issues_doc = _fetch("issues.json")
    loop = _loop_view(loop_doc, today_ist)
    issues = _issues_view(issues_doc, today_ist)

    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    shipped_30d = sum(1 for r in loop["rows"]
                      if r["outcome"] == "shipped" and (r["date_ist"] or "") >= cutoff)
    cost = _cost_view(_fetch("cost.json"), shipped_30d)
    traffic = _traffic_view()
    agents = _agents_view()

    return {
        "now_ist": now_ist,
        "today_ist": today_ist,
        "next_cycle_ist": next_cycle_ist(now),
        "loop": loop,
        "issues": issues,
        "cost": cost,
        "traffic": traffic,
        "agents": agents,
        "source": "disk" if measurements_dir() else "github",
        # The one line every loop ranks against, carried in issues.json because
        # the Docker image copies only `src/` -- OBJECTIVE.md is not in the
        # container. "" when chief has not written one, which is a real state.
        "objective": (issues_doc or {}).get("objective") or "",
        # Per-source age, so a count can be read as of a time rather than as
        # now. Keyed by the panel that shows it, not by filename.
        "ages": {
            "delivery": _age((loop_doc or {}).get("generated_at"), now),
            "backlog": _age((issues_doc or {}).get("generated_at"), now),
            "team": _age((_fetch("agents.json") or {}).get("generated_at"), now),
        },
        # Named so the footer can say which panel is missing rather than
        # rendering an empty one with no explanation.
        "missing": [n for n, v in (("loop.json", loop["ok"]),
                                   ("cost.json", cost["ok"]),
                                   ("issues.json", issues["ok"]),
                                   ("traffic", traffic["ok"]),
                                   ("agents.json", agents["ok"])) if not v],
    }
