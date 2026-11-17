#!/usr/bin/env python3
"""Collect the last week's saved /ask answers for the weekly correctness audit (#1167).

WHY THIS EXISTS
---------------
The owner, 2026-11-17: "we have been saving questions answers, but I don't think
we have analysed those". Every /ask answer is recorded as a `form_ask` event
(`routes/ask.py`, `events.record`) and kept 30 days in GCS, and nothing ever
graded one. agent-measure's `measure` job reads this sample and hands it to a
`qa` prose audit.

THE PRIVACY BOUNDARY IS THIS FILE (owner's decision on #1167, act #5)
--------------------------------------------------------------------
The repository is public and so are its Actions logs. A recorded event carries
the signed-in user's EMAIL beside the question. So:

  * Fields are WHITELISTED (`SAMPLE_FIELDS`), never blacklisted. A field added to
    `form_ask` later stays out of the sample until someone adds it here on
    purpose. `email` is not on the list and never can be: `_slim` asserts it.
  * The sample goes to a /tmp path the workflow deletes in an `always()` step.
    It is never written under `measurements/` and never printed.
  * The meta file IS committed (via /tmp/measure), so it holds COUNTS only:
    no question, no answer, no id, and category/lang/context values only when
    they match a closed shape (anything else is counted as "other").

Reads through `astro_ai.events.recent`, the same reader /admin/activity uses,
rather than a second copy of the GCS access.

EXIT CODES: 0 written (zero events is a valid, empty sample)
            2 could not read storage, or bad arguments -- nothing written
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DAYS = 7
LIMIT = 300
EVENT_TYPE = "form_ask"

# What the audit may see. `id` and `ts` come from the event; the rest from its
# `data`. `chart` is the compact snapshot slice 2 of #1167 adds (signs, houses,
# lagna, nakshatra, dasha -- never birth date, time or place); until then it is
# absent and the audit grades "rules-only".
DATA_FIELDS = ("category", "lang", "model", "context", "cache_hit",
               "question", "answer", "chart")
SAMPLE_FIELDS = ("id", "ts") + DATA_FIELDS

# Closed shapes for the values the COMMITTED meta file may name.
_TOKEN = re.compile(r"^[a-z_]{1,24}$")
_LANG = re.compile(r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$")


def _id(ts: str, question: str) -> str:
    return hashlib.sha256(f"{ts}\n{question}".encode("utf-8")).hexdigest()[:16]


def _slim(evt: dict) -> dict:
    """One event reduced to the whitelist. Everything else is dropped."""
    data = evt.get("data") if isinstance(evt.get("data"), dict) else {}
    ts = str(evt.get("ts") or "")
    row = {"id": _id(ts, str(data.get("question") or "")), "ts": ts}
    for k in DATA_FIELDS:
        if k in data:
            row[k] = data[k]
    assert set(row) <= set(SAMPLE_FIELDS) and "email" not in row
    return row


def _bucket(value, pattern: re.Pattern) -> str:
    v = str(value or "")
    return v if pattern.match(v) else "other"


def meta_for(rows: list[dict], window: tuple[str, str], now: datetime,
             truncated: bool) -> dict:
    """Counts only. Nothing in here may be user text."""
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": list(window),
        "window_days": DAYS,
        "total": len(rows),
        "fresh": sum(1 for r in rows if not r.get("cache_hit")),
        "cache_hits": sum(1 for r in rows if r.get("cache_hit")),
        "with_chart": sum(1 for r in rows if r.get("chart")),
        "truncated": truncated,
        "by_category": dict(sorted(Counter(_bucket(r.get("category"), _TOKEN) for r in rows).items())),
        "by_lang": dict(sorted(Counter(_bucket(r.get("lang"), _LANG) for r in rows).items())),
        "by_context": dict(sorted(Counter(_bucket(r.get("context"), _TOKEN) for r in rows).items())),
    }


def _probe() -> str | None:
    """None when the bucket can be read; otherwise why not.

    `storage.get` swallows every error into None, so a bucket we cannot reach
    looks exactly like a quiet week. This asks once, with the error visible: a
    404 on today's blob is a reading (no events yet), anything else is not.
    """
    from astro_ai import storage  # noqa: PLC0415 -- needs src/ on the path
    blob = storage._blob(f"events/{datetime.now(timezone.utc).date().isoformat()}.json")
    if blob is None:
        return "storage not configured (BHAGYA_STORAGE_BUCKET unset or no GCS client)"
    try:
        blob.download_as_text()
    except Exception as exc:  # noqa: BLE001 -- classify, never raise
        if getattr(exc, "code", None) == 404 or exc.__class__.__name__ == "NotFound":
            return None
        return f"{exc.__class__.__name__}: {str(exc)[:160]}"
    return None


def _read(days: int, limit: int) -> list[dict]:
    from astro_ai import events  # noqa: PLC0415 -- needs src/ on the path
    return events.recent(types=[EVENT_TYPE], days=days, limit=limit)


def main(argv: list[str], read: Callable[[int, int], list[dict]] = _read,
         probe: Callable[[], str | None] = _probe, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="the sample; a /tmp path, never measurements/")
    ap.add_argument("--meta", required=True, help="counts only; committed via /tmp/measure")
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--limit", type=int, default=LIMIT)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    if "measurements" in Path(a.out).parts:
        print("::error::the sample must never be written under measurements/ (it is committed)")
        return 2
    now = now or datetime.now(timezone.utc)
    why = probe()
    if why:
        print(f"::warning::/ask sample not collected -- cannot read storage ({why})")
        return 2
    try:
        events = read(a.days, a.limit + 1)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::/ask sample not collected ({exc.__class__.__name__})")
        return 2
    truncated = len(events) > a.limit
    rows = [_slim(e) for e in events[:a.limit] if e.get("type", EVENT_TYPE) == EVENT_TYPE]
    window = ((now - timedelta(days=a.days - 1)).date().isoformat(), now.date().isoformat())
    sample = {"window": list(window), "n": len(rows), "answers": rows}
    Path(a.out).write_text(json.dumps(sample, ensure_ascii=False, indent=1) + "\n")
    meta = meta_for(rows, window, now, truncated)
    Path(a.meta).parent.mkdir(parents=True, exist_ok=True)
    Path(a.meta).write_text(json.dumps(meta, indent=1) + "\n")
    # Counts only on stdout: the log is public.
    print(f"/ask sample: {meta['total']} answers ({meta['fresh']} fresh, "
          f"{meta['cache_hits']} cache hits, {meta['with_chart']} with a chart snapshot), "
          f"window {window[0]}..{window[1]}{' (truncated)' if truncated else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
