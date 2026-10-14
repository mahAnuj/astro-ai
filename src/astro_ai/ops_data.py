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
FILES = ("loop.json", "cost.json", "issues.json",
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
        "by_priority": doc.get("by_priority") or dict(Counter(r["priority"] for r in rows)),
        "by_area": doc.get("by_area") or dict(Counter(r["area"] for r in rows)),
        "by_type": doc.get("by_type") or dict(Counter(r["type"] for r in rows)),
        "blocked": [r for r in rows if r.get("blocked")],
        "filed_today": filed_today,
    }


def _series(rows: list[dict], key: str, *, width: float = 100.0, height: float = 100.0) -> dict:
    """Turn a daily series into an SVG path, server-side.

    No charting library: the page loads nothing from a CDN but two fonts, and a
    line through 28 points is four lines of arithmetic. The path is emitted in
    a 0..100 viewBox and stretched by CSS, so the same string renders at any
    panel width without recomputing.

    The y axis starts at ZERO, always. A chart auto-scaled to its own minimum
    turns a wobble between 6 and 11 users into a cliff, which is the single
    easiest way for a dashboard to lie without containing a false number.
    """
    vals = [r.get(key) or 0 for r in rows]
    if not vals:
        return {"ok": False}
    top = max(vals) or 1
    n = len(vals)
    pts = [((i / (n - 1) if n > 1 else 0) * width, height - (v / top) * height)
           for i, v in enumerate(vals)]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    return {
        "ok": True,
        "line": line,
        # Closed back along the baseline, for the soft fill under the line.
        "area": f"{line} {width:.2f},{height:.2f} 0.00,{height:.2f}",
        "max": top,
        "last": vals[-1],
        "first": vals[0],
        "total": sum(vals),
        "n": n,
        "labels": [rows[0].get("date"), rows[-1].get("date")],
        # Marks the days the API returned nothing, so a collection gap is not
        # read as a day with no visitors.
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


def snapshot(now: datetime | None = None) -> dict:
    """Everything /admin/ops renders, in one dict. Never raises."""
    now = now or datetime.now(timezone.utc)
    now_ist = now.astimezone(IST)
    today_ist = now_ist.strftime("%Y-%m-%d")

    loop = _loop_view(_fetch("loop.json"), today_ist)
    issues = _issues_view(_fetch("issues.json"), today_ist)

    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    shipped_30d = sum(1 for r in loop["rows"]
                      if r["outcome"] == "shipped" and (r["date_ist"] or "") >= cutoff)
    cost = _cost_view(_fetch("cost.json"), shipped_30d)
    traffic = _traffic_view()

    return {
        "now_ist": now_ist,
        "today_ist": today_ist,
        "next_cycle_ist": next_cycle_ist(now),
        "loop": loop,
        "issues": issues,
        "cost": cost,
        "traffic": traffic,
        "source": "disk" if measurements_dir() else "github",
        # Named so the footer can say which panel is missing rather than
        # rendering an empty one with no explanation.
        "missing": [n for n, v in (("loop.json", loop["ok"]),
                                   ("cost.json", cost["ok"]),
                                   ("issues.json", issues["ok"]),
                                   ("traffic", traffic["ok"])) if not v],
    }
