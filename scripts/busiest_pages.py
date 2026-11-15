#!/usr/bin/env python3
"""Rank the pages people actually use, so verification goes where the traffic is.

WHY THIS EXISTS
---------------
Owner, 2026-11-15: "look at what users are spending more time on and make sure
that is absolutely working fine, with no error and 100% correctness" -- and then
"why the analyst didn't automatically do what I am asking". It could not: the
analyst measures and decides nothing, and nothing turned "this page is where
the traffic is" into "re-verify this page". This file is that hand-off, made
deterministic so it does not depend on an agent remembering to write it.

It reads the GA4 landing export and the GSC page export already fetched by
agent-measure and writes `verify-first.json`: the top pages by engaged sessions,
each with its search impressions and the module or template that serves it.
`scripts/research_queue.py` appends it to the Research team's work list, so the
astro-auditor re-checks the busiest pages without being asked.

Engaged sessions come from GA4's `engagedSessions` when the export carries it
(fetch_ga4.py since 2026-11-15) and otherwise from sessions x (1 - bounce rate),
which is the same quantity by GA4's definition of bounce rate.

Named busiest_pages.py, NOT verify_first.py: pr-gates runs every
`scripts/verify_*.py` with no arguments as a gate, and a script that needs
--ga4/--gsc exits 2 there ("SKIPPED ... not a pass"), which turned #1063 red.

No model, no network. EXIT CODES: 0 written   2 an input is missing or unreadable
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOP = 10
SKIP_PREFIXES = ("/admin", "/static", "/r/")
SKIP_EXACT = {"", "(not set)"}


def fold(landing: str) -> str | None:
    """`/learn/x/?fbclid=..` and `/learn/x` are one page; admin and junk are none."""
    path = landing.split("?", 1)[0].split("#", 1)[0]
    if path in SKIP_EXACT or not path.startswith("/"):
        return None
    if path != "/":
        path = path.rstrip("/")
    if any(path == p or path.startswith(p + "/") or path.startswith(p) and p.endswith("/")
           for p in SKIP_PREFIXES):
        return None
    return path


def serves(path: str) -> str:
    """Where to look. A hint for the reader, not a guarantee."""
    if path == "/":
        return "routes/home.py -> templates/index.html"
    if path.startswith("/hi/"):
        return serves(path[3:] or "/") + " (Hindi)"
    head, _, rest = path.lstrip("/").partition("/")
    if head == "learn" and rest:
        return f"templates/learn/{rest}.html"
    known = {"muhurat": "routes/muhurat.py, muhurat.py", "kundli": "routes/kundli.py, chart.py",
             "reading": "routes/kundli.py, chart.py", "matching": "routes/matching.py, matching.py",
             "numerology": "routes/numerology.py, numerology.py", "ask": "routes/ask.py, intents.py, llm.py",
             "panchang": "routes/panchang.py, chart.py", "rashifal": "routes/rashifal.py",
             "dasha": "routes/dasha.py, chart.py", "festivals": "festivals.py, festival_registry.py"}
    return known.get(head, f"routes/ for /{head}")


def build(ga4: dict, gsc: dict, top: int = TOP) -> dict:
    pages: dict[str, dict] = {}
    for r in ga4.get("rows") or []:
        path = fold(r.get("landing", ""))
        if not path:
            continue
        s = int(r.get("sessions") or 0)
        engaged = r.get("engaged_sessions")
        if engaged is None:
            engaged = s * (1 - float(r.get("bounce_rate") or 0))
        p = pages.setdefault(path, {"path": path, "sessions": 0, "engaged_sessions": 0.0,
                                    "engagement_seconds": None})
        p["sessions"] += s
        p["engaged_sessions"] += float(engaged)
        if r.get("engagement_seconds") is not None:
            p["engagement_seconds"] = (p["engagement_seconds"] or 0) + int(r["engagement_seconds"])

    search: dict[str, dict] = {}
    for r in gsc.get("rows") or []:
        url = r.get("page") or ""
        path = fold("/" + url.split("://", 1)[-1].split("/", 1)[-1]) if "://" in url else fold(url)
        if path:
            agg = search.setdefault(path, {"impressions": 0, "clicks": 0, "_wpos": 0.0})
            imp = int(r.get("impressions") or 0)
            agg["impressions"] += imp
            agg["clicks"] += int(r.get("clicks") or 0)
            agg["_wpos"] += imp * float(r.get("position") or 0)

    rows = []
    for p in pages.values():
        g = search.get(p["path"], {})
        imp = g.get("impressions", 0)
        rows.append({
            "path": p["path"],
            "sessions": p["sessions"],
            "engaged_sessions": round(p["engaged_sessions"], 1),
            "engaged_rate": round(p["engaged_sessions"] / p["sessions"], 2) if p["sessions"] else None,
            "avg_engagement_seconds": (round(p["engagement_seconds"] / p["sessions"])
                                       if p["engagement_seconds"] is not None and p["sessions"] else None),
            "gsc_impressions": imp,
            "gsc_clicks": g.get("clicks", 0),
            "gsc_position": round(g["_wpos"] / imp, 1) if imp else None,
            "serves": serves(p["path"]),
        })
    rows.sort(key=lambda r: (-r["engaged_sessions"], -r["gsc_impressions"], r["path"]))
    return {"source": "busiest_pages.py", "window": ga4.get("window"),
            "basis": ("GA4 engagedSessions" if any(r.get("engaged_sessions") is not None
                                                     for r in ga4.get("rows") or [])
                      else "sessions x (1 - bounce_rate)"),
            "rows": rows[:top]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ga4", required=True)
    ap.add_argument("--gsc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=TOP)
    a = ap.parse_args(argv)
    try:
        ga4 = json.loads(Path(a.ga4).read_text())
        gsc = json.loads(Path(a.gsc).read_text())
    except (OSError, ValueError) as exc:
        print(f"::warning::busiest_pages.py could not read its inputs: {exc}")
        return 2
    out = build(ga4, gsc, a.top)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"verify-first: {len(out['rows'])} pages ({out['basis']}), top: "
          + ", ".join(r["path"] for r in out["rows"][:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
