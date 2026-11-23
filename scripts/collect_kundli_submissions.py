#!/usr/bin/env python3
"""Export the server's own per-day count of fresh kundli generations (#1272).

WHY THIS EXISTS
---------------
#1068 compares GA4 `kundli_generated` with a server-side count, and nothing the analyst
reads carried one. GA4 cannot be its own control: the event over-counted re-renders until
PR #1157. The server already records `form_kundli` events (30-day GCS log, read by
/admin/insights); this collector counts them per UTC day and writes COUNTS ONLY.

WHAT THE NUMBER IS, AND IS NOT (read before comparing it to anything)
`form_kundli` is written by GET /kundli (the render after `POST /reading` answers 303),
inside the `not was_cached` branch, only after a FRESH, SUCCESSFUL generation. So it is
NOT 1:1 with `POST /reading` 303s: cache hits (SQLite and durable GCS), re-views, failed
generations and the snapshot route (#967) never fire it. The same text is written into the
file as `semantics`, so a reader cannot take the count for something it is not.

PROBES. verify-production sends `X-Bhagya-Probe` through `POST /reading` -> 303 -> GET
/kundli, so each push adds one `form_kundli` row that GA4 never sees (curl runs no JS).
Since #1272 the event carries `probe` (bool); days before that deploy have no marker, so
their `probe` and `non_probe` are null, never a guess. `totals.probe` and `totals.non_probe`
cover ONLY the days listed in `totals.non_probe_dates` (days whose events all carry the
marker), while `totals.fresh_generations` covers every known day (#1408), so never put one
beside the other. Compare to GA4 only over days inside `non_probe_dates`.

NULL IS UNKNOWN, NEVER 0. `storage.get` returns None for both "no blob" and "GCS error", so
a day with no events of ANY type cannot be told from a read failure and is null. A day at
the events cap (`events._MAX_EVENTS_PER_DAY`) dropped its oldest rows and is null too.

PRIVACY. Events hold an email, an identity hash and rashis. They are read in memory and
only integers and constant strings are written. There is deliberately no `lang` or
per-profile field: an arbitrary event string would need an allow-list to be safe.

Needs BHAGYA_STORAGE_BUCKET and GCS read access. On any failure it writes nothing and
exits 1, so the previous file stands. Read-only, idempotent, ~one GCS read per day,
sequential, none on a request path, 0 LLM tokens.

EXIT CODES: 0 written   1 could not read events (nothing written)   2 bad args
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DAYS = 28
# events.EVENT_RETENTION_DAYS; `recent()` clamps silently, so the stated window must not exceed it.
MAX_DAYS = 30
_FALLBACK_CAP = 5000  # events._MAX_EVENTS_PER_DAY, if the private name ever moves

SEMANTICS = (
    "Counts `form_kundli` events, written by GET /kundli (the render that follows the "
    "POST /reading 303) only on a FRESH, successful generation. It is NOT 1:1 with "
    "POST /reading 303 responses: it excludes cache hits (SQLite and durable GCS), "
    "re-views, failed generations and the snapshot route (#967). It includes "
    "verify-production probes (X-Bhagya-Probe) unless `probe` is non-null. `totals.probe` and "
    "`totals.non_probe` cover ONLY the days listed in `totals.non_probe_dates` (days whose "
    "events all carry the probe marker); `totals.fresh_generations` covers every known day, "
    "so never put one beside the other. Compare to GA4 `kundli_generated` only over days "
    "inside `non_probe_dates`; those two totals are null while any day of the window is "
    "unknown, so sum `days[].non_probe` over the listed days instead. Days are UTC. null = unknown, never 0 "
    "(no events of any type that day, or the day hit the per-day event cap, or the "
    "events predate the probe marker)."
)


def _cap() -> int:
    try:
        from astro_ai import events  # noqa: PLC0415 -- needs src/ on the path
        return int(events._MAX_EVENTS_PER_DAY)
    except Exception:  # noqa: BLE001
        return _FALLBACK_CAP


def _read(days: int) -> list[dict]:
    # Runs on UTC hosts (CI); `events.recent` windows on the host's LOCAL date, which the
    # UTC day labels in `build` assume is the same day (#1408, accepted and documented).
    if not os.environ.get("BHAGYA_STORAGE_BUCKET"):
        raise RuntimeError("BHAGYA_STORAGE_BUCKET is unset")
    from astro_ai import events  # noqa: PLC0415 -- needs src/ on the path
    # All types (so "the day has any blob" is derivable) and an effectively
    # unbounded limit: limit=10_000 would silently drop the OLDEST days.
    return events.recent(types=None, limit=10**9, days=days)


def _sum(vals: list[int | None]) -> int | None:
    known = [v for v in vals if v is not None]
    total = sum(known)
    # Nothing known but something unknown is unknown, not a quiet 0.
    if total == 0 and len(known) < len(vals):
        return None
    return total


def build(evts: list[dict], now: datetime, days: int) -> dict:
    today = now.astimezone(timezone.utc).date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    any_events = {d: 0 for d in dates}
    kundli: dict[str, list[dict]] = {d: [] for d in dates}
    for e in evts:
        d = str(e.get("ts") or "")[:10]
        if d not in any_events:
            continue
        any_events[d] += 1
        if e.get("type") == "form_kundli":
            kundli[d].append(e)
    cap = _cap()
    rows = []
    for d in dates:
        if any_events[d] == 0 or any_events[d] >= cap:
            rows.append({"date": d, "fresh_generations": None, "probe": None, "non_probe": None})
            continue
        ks = kundli[d]
        marked = all(isinstance((e.get("data") or {}).get("probe"), bool) for e in ks)
        probe = sum(1 for e in ks if (e.get("data") or {}).get("probe") is True) if marked else None
        rows.append({"date": d, "fresh_generations": len(ks), "probe": probe,
                     "non_probe": len(ks) - probe if probe is not None else None})
    return {
        "generated_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"from": dates[0], "to": dates[-1]},
        "today_partial": True,
        "semantics": SEMANTICS,
        "days": rows,
        "totals": {
            "fresh_generations": _sum([r["fresh_generations"] for r in rows]),
            "probe": _sum([r["probe"] for r in rows]),
            "non_probe": _sum([r["non_probe"] for r in rows]),
            # The days probe/non_probe sum over; fresh_generations sums every known day (#1408).
            "non_probe_dates": [r["date"] for r in rows if r["non_probe"] is not None],
            "days_unknown": sum(1 for r in rows if r["fresh_generations"] is None),
            "probe_days_unknown": sum(1 for r in rows if r["probe"] is None),
        },
    }


def main(argv: list[str], reader: Callable[[int], list[dict]] = _read,
         now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=DAYS)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    if not 1 <= a.days <= MAX_DAYS:
        print(f"--days must be 1..{MAX_DAYS} (the event log keeps {MAX_DAYS} days)")
        return 2
    try:
        evts = reader(a.days) or []
    except Exception as exc:  # GCS auth, network, a missing bucket: say so, write nothing
        print(f"::warning::kundli submissions not read ({exc.__class__.__name__}: "
              f"{str(exc)[:160]}); the previous kundli-submissions.json stands")
        return 1
    doc = build(evts, now or datetime.now(timezone.utc), a.days)
    if all(r["fresh_generations"] is None for r in doc["days"]):
        print("::warning::no day of the window had any events -- not written (that is "
              "a reading error, not zero submissions); the previous kundli-submissions.json stands")
        return 1
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    t = doc["totals"]
    print(f"kundli submissions {doc['window']['from']}..{doc['window']['to']}: "
          f"fresh {t['fresh_generations']}, non-probe {t['non_probe']} "
          f"over {len(t['non_probe_dates'])} days, "
          f"days unknown {t['days_unknown']}, probe-unmarked days {t['probe_days_unknown']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
