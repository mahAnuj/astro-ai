#!/usr/bin/env python3
"""Which IST day a rashifal-generate run writes (#852).

WHY THIS EXISTS
---------------
The job used to write TODAY at a 22:00 UTC cron. GitHub started it 2h50m-6h
late (last 12 runs began 00:50-03:59 UTC), so it landed after the 01:00 UTC
`/admin/warm-rashifal`, which found no blob and generated the day on Groq:
177 Groq calls and 778,261 input tokens in the week to 2026-11-10, while
Claude's correct readings arrived afterwards and changed nothing that was
already cached.

So a SCHEDULED run now writes TOMORROW, from a 06:17 UTC cron (11:47 IST),
leaving ~12h of slack before IST midnight even at the worst measured delay.
The blob then exists before the day starts and the warm is a GCS hit.

The rule is "the IST date 18 hours from now", not "tomorrow": a run delayed
past IST midnight then writes the day that has just started (still useful, and
still ahead of the 01:00 UTC warm) instead of the day after it, which nobody
reads for another 24h. From 06:00 IST onwards +18h is the next day; before
06:00 IST it is the current one.

A manual run (workflow_dispatch) writes TODAY unless a date is given: it is
how a bad day is regenerated or one rashi is spliced into the published day.

Prints YYYY-MM-DD. EXIT CODES: 0 printed   2 bad --date
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
LEAD = timedelta(hours=18)


def target(event: str, given: str, now: datetime) -> str:
    if given:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", given):
            raise ValueError(f"--date must be YYYY-MM-DD, got {given[:20]!r}")
        date.fromisoformat(given)
        return given
    ist = now.astimezone(IST)
    if event == "schedule":
        return (ist + LEAD).date().isoformat()
    return ist.date().isoformat()


def main(argv: list[str], now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--event", default="")
    ap.add_argument("--date", default="")
    args = ap.parse_args(argv[1:])
    try:
        print(target(args.event, args.date.strip(), now or datetime.now(timezone.utc)))
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
