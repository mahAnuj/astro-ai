"""The PRs-shipped bars and the Key metrics rows on /admin/ops Overview (#1133 slice 2b).

PURE, and it READS NOTHING of its own. `build(ops, kpis, links)` takes the dict
`ops_data.snapshot()` already assembled, the KPI row `ops_kpis.build` already
derived from it, and the rail's `tab_links` list, so the panels add 0 GCS reads,
0 GitHub reads and 0 LLM tokens.

PRs SHIPPED (bars). The same 7 complete IST days as the Results cards. Each PR is
counted ONCE, on the first IST day it shipped in the window (`ops_kpis._stats`
`pr_day`), so the 7 bars add up to the PRs-merged card; a PR worked on two days
is not two PRs. A day with no loop rows reads "no runs", never 0: the loop did
not run, which is not the same as running and shipping nothing.

KEY METRICS (rows), the owner's four:
  * Organic search clicks: `gsc-daily.json`. Its window ends at ITS OWN last row,
    not at `traffic.window`, which prefers GA4's window over GSC's and so would
    name a week the clicks do not cover (GSC trails the present by ~3 days).
    Nothing attributes a click to an agent, and the row says so.
  * Issues closed: `issues.json` `trend.days[].closed`, UTC days. The collector's
    last day is today and partial (`scripts/issue_flow.py`: "today included
    (partial)"), so the window ends the day BEFORE the newest date. The file
    counts closures for any reason, hence "closed", not "resolved"; the row also
    says how many were `close-on-evidence`.
  * Content published and Average cycle time: not collected. Slice 2e adds the
    collectors. The rows print the owner's definitions (2026-11-17, answer 5) and
    NO number and NO sparkline: a 0 here would mean "unknown".
A window with a gap in it never shows a delta, and never a sum over the hole.

NEVER RAISES. Each panel degrades on its own and `error` says one did. Garbage
rows (bool, NaN, non-dict, a bad or duplicated date) are skipped; a duplicated
date is dropped entirely, because which copy is right is unknowable. This module
does not rely on `ops_data._traffic_view` having screened the GSC rows.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import date, timedelta

from astro_ai.ops_data import _nice_top, _series
from astro_ai.ops_kpis import MIN_N, _delta, _span, windows

log = logging.getLogger(__name__)

#: issue_flow.CLOSERS key for the closer that is the loop's own fix path.
#: tests/test_ops_trends.py pins it to that tuple.
FIX_CLOSER = "close-on-evidence"

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

#: The two rows nothing collects yet. The definitions are the owner's
#: (2026-11-17, answer 5); the collectors are slice 2e of #1133.
NOT_COLLECTED = {
    "content": {
        "label": "Content published",
        "definition": "/learn articles merged in the window.",
    },
    "cycle_time": {
        "label": "Average cycle time",
        "definition": "Time from an issue being opened to its fix merging.",
    },
}
_NOT_COLLECTED_REASON = "unavailable: not collected, slice 2e adds it"

# Bar chart geometry (SVG user units; the template scales it).
_W, _PLOT_H, _LEFT, _RIGHT = 560, 120, 28, 8
_LABEL_Y = _PLOT_H + 28   # two label lines: weekday, then date


def _int(x) -> int | None:
    """`x` when it is a non-negative whole number (not a bool), else None."""
    if isinstance(x, bool):
        return None
    if isinstance(x, float) and math.isfinite(x) and x == int(x):
        x = int(x)
    return x if isinstance(x, int) and x >= 0 else None


def _iso(x) -> date | None:
    if not isinstance(x, str) or not _ISO.fullmatch(x):
        return None
    try:
        return date.fromisoformat(x)
    except ValueError:
        return None


def _daily(rows, key: str) -> tuple[dict[str, int], int]:
    """({iso date: count}, skipped). Only rows with a real date and a real count.

    A date that appears twice is dropped whole: the copies may disagree and
    there is nothing to say which one is right.
    """
    seen: dict[str, int] = {}
    dup: set[str] = set()
    skipped = 0
    for r in rows if isinstance(rows, list) else []:
        d = r.get("date") if isinstance(r, dict) else None
        v = _int(r.get(key)) if isinstance(r, dict) else None
        if _iso(d) is None or v is None:
            skipped += 1
            continue
        if d in seen:
            dup.add(d)
            continue
        seen[d] = v
    for d in dup:
        del seen[d]
    return seen, skipped + len(dup)


def _link(links, key: str) -> str:
    """The href the rail already built for tab `key`; "" when it is not there.

    `links` is `ops_tabs.tab_links(...)`, built from validated values, so no raw
    query string can reach an href through this module.
    """
    for lk in links if isinstance(links, list) else []:
        if isinstance(lk, dict) and lk.get("key") == key and isinstance(lk.get("href"), str):
            return lk["href"]
    return ""


def _no_delta(why: str) -> dict:
    return _delta(None, None, mode="pct", good_when="up", prev_window="", prev_n=0,
                  prev_text="", blocked=why)


def _metric(key: str, label: str, *, state: str, display: str = "", n_text: str = "",
            window_text: str = "", delta: dict | None = None, spark: dict | None = None,
            source: str = "", definition: str = "", href: str = "", link_text: str = "",
            note: str = "", n: int = 0) -> dict:
    low = state == "ok" and n < MIN_N
    return {
        "key": key, "label": label, "state": state,
        "display": display or ("unavailable" if state != "ok" else ""),
        "n": n, "low_n": low,
        "n_text": n_text + (" — too few to read" if low else ""),
        "window_text": window_text,
        "delta": delta or _no_delta("no change shown: no current value"),
        "spark": spark, "source": source, "definition": definition, "note": note,
        "href": href, "link_text": link_text if href else "",
    }


def _window_metric(key: str, label: str, counts: dict[str, int], today_ist: str, *,
                   unit: str, source: str, definition: str, href: str, link_text: str,
                   extra: str = "", note: str = "", as_of: str = "") -> dict:
    """One 7-day-against-7-day row from `{date: count}`.

    `today_ist` is the day AFTER the window's last day (`ops_kpis.windows` ends
    yesterday). The value needs all 7 current days; the delta needs all 14.
    """
    cur_dates, prev_dates = windows(today_ist)
    wtext, ptext = _span(cur_dates), _span(prev_dates)
    src = source + (f" · {as_of}" if as_of else "")
    common = dict(source=src, definition=definition, href=href, link_text=link_text, note=note)
    missing = [d for d in cur_dates if d not in counts]
    if missing:
        return _metric(key, label, state="unavailable", window_text=wtext,
                       n_text=f"unavailable: no data for {len(missing)} of 7 days "
                              f"in this window (first gap {missing[0]})", **common)
    cur = sum(counts[d] for d in cur_dates)
    gap = [d for d in prev_dates if d not in counts]
    if gap:
        delta = _no_delta(f"unavailable: no data for {len(gap)} of 7 days in the previous "
                          f"window (first gap {gap[0]})")
        delta["previous_window"] = ptext
    else:
        prev = sum(counts[d] for d in prev_dates)
        delta = _delta(cur, prev, mode="pct", good_when="up", prev_window=ptext, prev_n=prev,
                       prev_text=str(prev))
    spark = _series([{"date": d, "v": counts[d]} for d in cur_dates], "v",
                    width=120, height=32)
    return _metric(key, label, state="ok", display=f"{cur:,}", n=cur,
                   n_text=f"{cur:,} {unit} in 7 days{extra}", window_text=wtext,
                   delta=delta, spark=spark, **common)


def _organic(ops: dict, links) -> dict:
    kw = dict(source="measurements/gsc-daily.json", definition="Clicks from Google search "
              "results, summed over 7 days.", href=_link(links, "analytics"),
              link_text="Open Traffic", note="not attributed to any agent")
    counts, skipped = _daily((ops.get("traffic") or {}).get("gsc_rows"), "clicks")
    if not counts:
        return _metric("organic", "Organic search clicks", state="unavailable",
                       n_text="unavailable: gsc-daily.json not read or empty", **kw)
    # The window ends at GSC's OWN newest date, not traffic.window (GA4's wins there).
    end = max(date.fromisoformat(d) for d in counts)
    m = _window_metric("organic", "Organic search clicks", counts,
                       (end + timedelta(days=1)).isoformat(), unit="clicks", **kw)
    if skipped:
        m["n_text"] += f"; {skipped} row(s) skipped"
    return m


def _issues(ops: dict, links) -> dict:
    kw = dict(source="measurements/issues.json (trend)", definition="Issues closed for any "
              "reason, by UTC day, the 7 complete days before the collector's partial today.",
              href=_link(links, "backlog"), link_text="Open Issue flow")
    flow = ops.get("issue_flow")
    if not isinstance(flow, dict):
        return _metric("issues", "Issues closed", state="unavailable",
                       n_text="unavailable: issue trend not collected", **kw)
    if flow.get("error"):
        return _metric("issues", "Issues closed", state="unavailable",
                       n_text="unavailable: the issue trend could not be read", **kw)
    days = flow.get("days")
    counts, skipped = _daily(days, "closed")
    # The partial day is the newest date IN THE FILE, which `_daily` may have
    # dropped (a garbage count on it): read the newest of every well-formed date.
    dated = [d for d in (r.get("date") for r in days if isinstance(r, dict)) if _iso(d)] \
        if isinstance(days, list) else []
    if not counts or not dated:
        return _metric("issues", "Issues closed", state="unavailable",
                       n_text="unavailable: the issue trend has no usable days", **kw)
    # `windows` ends the day before the date it is given, so handing it the
    # newest (partial) date leaves that day out.
    newest = max(dated, key=date.fromisoformat)
    cur_dates, _ = windows(newest)
    closers = sum(_int(r["closed_by"].get(FIX_CLOSER)) or 0 for r in days
                  if isinstance(r, dict) and r.get("date") in cur_dates
                  and r["date"] in counts and isinstance(r.get("closed_by"), dict))
    age = flow.get("age") if isinstance(flow.get("age"), dict) else {}
    m = _window_metric("issues", "Issues closed", counts, newest, unit="closed",
                       extra=f", {closers} by {FIX_CLOSER}", as_of=str(age.get("text") or ""),
                       **kw)
    if skipped:
        m["n_text"] += f"; {skipped} day(s) skipped"
    return m


def _not_collected(key: str) -> dict:
    d = NOT_COLLECTED[key]
    return _metric(key, d["label"], state="unavailable", display="not collected",
                   n_text=_NOT_COLLECTED_REASON, definition=d["definition"],
                   source="not collected", delta=_no_delta("no change shown: not collected"))


def _unavailable_metrics(reason: str) -> list[dict]:
    return [_metric(k, lbl, state="unavailable", n_text=reason)
            for k, lbl in (("organic", "Organic search clicks"), ("issues", "Issues closed"))] \
        + [_not_collected(k) for k in NOT_COLLECTED]


def _bars_unavailable(reason: str) -> dict:
    return {"state": "unavailable", "reason": reason, "window_text": "", "n_text": reason,
            "total": None, "w": _W, "h": _LABEL_Y + 6, "plot_h": _PLOT_H, "left": _LEFT,
            "right_x": _W - _RIGHT, "top": 1, "yticks": [], "cols": [], "table": []}


def _bars(kpis: dict) -> dict:
    """One bar per window day from `kpis["pr_days"]`; the sum is the card's PR count."""
    days = kpis.get("pr_days") if isinstance(kpis, dict) else None
    if not isinstance(days, list) or not days:
        return _bars_unavailable("unavailable: the KPI row has no daily PR counts")
    cols_in = []
    for d in days:
        dt = _iso(d.get("date")) if isinstance(d, dict) else None
        runs = _int(d.get("runs")) if isinstance(d, dict) else None
        prs = [p for p in d.get("prs", []) if _int(p)] if isinstance(d, dict) and isinstance(d.get("prs"), list) else None
        if dt is None or runs is None or prs is None:
            return _bars_unavailable("unavailable: a daily PR count was malformed")
        cols_in.append((dt, runs, sorted(prs)))
    values = [len(prs) for _, runs, prs in cols_in if runs]
    peak = max(values, default=0)
    top = _nice_top(peak)
    slot = (_W - _LEFT - _RIGHT) / len(cols_in)
    bar_w = round(min(slot * 0.55, 40), 2)
    cols, table = [], []
    for i, (dt, runs, prs) in enumerate(cols_in):
        wd, iso = _WEEKDAYS[dt.weekday()], dt.isoformat()
        cx = _LEFT + i * slot + slot / 2
        if runs:
            h = len(prs) / top * _PLOT_H
            value_text = str(len(prs))
            state = "ok"
            tip = (f"{wd} {iso}: {len(prs)} PR{'' if len(prs) == 1 else 's'} shipped "
                   f"({runs} run{'' if runs == 1 else 's'})")
        else:
            h, value_text, state = 0.0, "no runs", "norun"
            tip = f"{wd} {iso}: no runs recorded"
        cols.append({
            "date": iso, "weekday": wd, "label": iso[5:], "state": state,
            "value": len(prs) if runs else None, "value_text": value_text,
            "runs": runs, "prs": ",".join(str(p) for p in prs), "tip": tip,
            "cx": round(cx, 2), "x": round(cx - bar_w / 2, 2), "w": bar_w,
            "y": round(_PLOT_H - h, 2), "h": round(h, 2),
            "value_y": round(max(_PLOT_H - h - 6, 10), 2),
        })
        table.append({"date": iso, "weekday": wd, "value_text": value_text,
                      "runs": runs, "prs": ", ".join(f"#{p}" for p in prs) or "none"})
    total = sum(values)
    n_runs = sum(1 for c in cols if c["state"] == "ok")
    wtext = _span([c["date"] for c in cols])
    low = total < MIN_N
    return {
        "state": "ok" if n_runs else "empty",
        "reason": "" if n_runs else "no runs in this window",
        "window_text": wtext,
        "n_text": (f"{total} PRs in {len(cols)} days, each on the day it first shipped; "
                   f"{len(cols) - n_runs} day(s) with no runs"
                   + (" — too few to read" if low else "")),
        "low_n": low, "total": total, "peak": peak,
        "w": _W, "h": _LABEL_Y + 6, "plot_h": _PLOT_H, "left": _LEFT, "right_x": _W - _RIGHT,
        "label_y": _LABEL_Y, "top": top,
        "yticks": sorted({top, top // 2, 0}, reverse=True),
        "cols": cols, "table": table,
    }


def _unavailable(reason: str, *, error: bool) -> dict:
    return {"error": error, "bars": _bars_unavailable(reason),
            "metrics": _unavailable_metrics(reason)}


def build(ops, kpis, links) -> dict:
    """{"error", "bars", "metrics"} for Overview. Never raises.

    `links` is `ops_tabs.tab_links(...)`: already-validated, so no raw query
    value reaches an href. Each panel degrades alone; `error` is True when any
    of them had to.
    """
    try:
        return _build(ops, kpis, links)
    except Exception as exc:  # noqa: BLE001 - the page must render without the panels
        log.warning("Overview trends could not be computed: %s", exc)
        return _unavailable("unavailable: could not be computed", error=True)


def _build(ops, kpis, links) -> dict:
    error = False
    try:
        bars = _bars(kpis)
    except Exception as exc:  # noqa: BLE001 - the page must render without the bars
        log.warning("PRs-shipped bars could not be computed: %s", exc)
        bars, error = _bars_unavailable("unavailable: could not be computed"), True
    metrics = []
    for key, label, fn in (("organic", "Organic search clicks", _organic),
                           ("issues", "Issues closed", _issues)):
        try:
            metrics.append(fn(ops, links))
        except Exception as exc:  # noqa: BLE001
            log.warning("key metric %s could not be computed: %s", key, exc)
            metrics.append(_metric(key, label, state="unavailable",
                                   n_text="unavailable: could not be computed"))
            error = True
    metrics += [_not_collected(k) for k in NOT_COLLECTED]
    return {"error": error, "bars": bars, "metrics": metrics}
