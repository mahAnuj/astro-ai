#!/usr/bin/env python3
"""Emit the EXACT prompt the runtime would send, as a brief for a writer (#515).

The nightly Claude Code job generates the day's twelve readings instead of
Groq. The one thing it must not do is carry its own copy of the prompt: a
second copy drifts, and then the job is writing to a cache key whose content
no longer matches what `rashifal_single.txt` says it is. So nothing here
composes a prompt. It calls `llm._system_prompt` and the same day-signal and
transit builders `_generate_rashifal_single` calls, and prints what they
produce.

`combined_keys` is called for the same reason, and its own docstring already
states it: "Two copies of these f-strings is a derive path that silently reads
a key nobody writes." The key printed here is the key the app reads.

Usage:
    uv run python scripts/rashifal_brief.py --lang en > /tmp/brief-en.md
    uv run python scripts/rashifal_brief.py --lang en --key-only

Exit codes:
    0  brief written
    2  the chart/panchang/transit could not be computed — the caller must NOT
       fall back to inventing a brief; it must write nothing and let the Groq
       path run.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai import festivals, llm                      # noqa: E402
from astro_ai.chart import (compute_chart, compute_panchang,              # noqa: E402
                            compute_transit_snapshot)
from astro_ai.rashifal_derive import combined_keys                        # noqa: E402
from astro_ai.routes.deps import RASHIFAL_PROMPT_PATH                     # noqa: E402

# The same neutral reference chart `send_daily_rashifal` uses. The rashifal is
# generic across users, so it is computed once against a fixed location; the
# panchang and transit it feeds are resolved for TODAY, not for 2000-01-01
# (`compute_panchang(natal, when=None)` reads `datetime.now`).
_NEUTRAL = ("2000-01-01", "12:00", "Mumbai, India")


# The rashifal day is the IST day, and this job runs when the two calendars
# DISAGREE. At 22:00 UTC the runner's own `date.today()` is still yesterday,
# while `compute_panchang(natal, when=None)` resolves the day through
# `datetime.now(ZoneInfo("Asia/Kolkata"))` and returns tomorrow's. Taking the
# runner's date would write tomorrow's panchang under yesterday's key -- a
# cache HIT on the wrong day, which is the one failure mode this whole job is
# built to avoid. So the default is computed in IST, never from the runner.
def _ist_today() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()


def build(lang: str, today_iso: str, rashi: str = "all") -> tuple[str, str]:
    """(storage key, brief markdown) for one language, all twelve or one rashi.

    `rashi` is an English slug ("aries") or "all". A single-rashi brief exists
    for regenerating one bad reading without redoing the day; the publisher
    then runs with --merge, which splices it into the published twelve and
    validates the RESULT, so a one-section document can never reach the bucket
    on its own.
    """
    natal = compute_chart(*_NEUTRAL)
    transit = compute_transit_snapshot(natal)
    panchang = compute_panchang(natal)
    today = date.fromisoformat(today_iso)

    signals = llm._build_rashifal_day_signals(
        transit, today_iso, lang, panchang, festivals.festival_for_date(today))
    day_signals_block = "\n".join(f"- {s}" for s in signals)
    transit_block = llm.format_transit_for_prompt(transit)
    _cache_key, storage_key = combined_keys(lang, today_iso)

    parts = [
        f"# Rashifal brief — {today_iso}, lang={lang}",
        "",
        "Everything below is generated from the running code. Do not edit it, "
        "do not summarise it, and do not substitute your own wording for any "
        "of it — it is the same text the live path sends.",
        "",
        f"**Storage key the app will read:** `{storage_key}`",
        "",
        "## SYSTEM PROMPT — follow it exactly, including every DO NOT",
        "",
        "```",
        llm._system_prompt(RASHIFAL_PROMPT_PATH, lang),
        "```",
        "",
        "## The twelve user messages",
        "",
        "Write one reading per message, in this order. Each must begin with its "
        "own `## ` heading exactly as the message states.",
        "",
    ]
    wanted = [a for a in llm._RASHI_ANCHORS
              if rashi == "all" or a["en"].lower() == rashi.lower()]
    if not wanted:
        raise ValueError(f"no such rashi: {rashi!r}")
    if rashi != "all":
        parts += [f"**Regenerating ONE rashi ({wanted[0]['en']}).** The other eleven "
                  f"stay as published; your text is spliced into them and the whole "
                  f"day is re-validated. Write only this one.", ""]
    for anchor in wanted:
        parts += [f"### {anchor['en']} / {anchor['sa']}", "", "```",
                  llm._rashifal_user_message(anchor, day_signals_block, transit_block)
                  if hasattr(llm, "_rashifal_user_message")
                  else _inline_user_message(anchor, day_signals_block, transit_block),
                  "```", ""]
    return storage_key, "\n".join(parts)


def _inline_user_message(anchor: dict, day_signals_block: str, transit_block: str) -> str:
    """The user message, built the way `_generate_rashifal_single` builds it.

    Only reached while that function composes the string inline rather than
    through a helper. It is a literal transcription, and
    `tests/test_rashifal_brief.py` pins it against a real call so the two
    cannot drift silently — if llm.py grows a helper, this is dead code and
    the `hasattr` branch above takes over.
    """
    return (
        f"TODAY'S SKY SIGNALS (use these to make the reading feel like TODAY):\n"
        f"{day_signals_block}\n"
        f"\n"
        f"Raw planetary positions (background context — do NOT recite):\n"
        f"{transit_block}\n"
        f"\n"
        f"RASHI TO WRITE FOR:\n"
        f"- Name: {anchor['en']} / {anchor['sa']}\n"
        f"- Ruling planet (Swami): {anchor['lord']}\n"
        f"- Element (Tattva): {anchor['element']}\n"
        f"- Quality (Guna): {anchor['quality']}\n"
        f"\n"
        f"OPENING STYLE HINT (CRITICAL — this is how you avoid opening with "
        f"'Today, you may feel...' like every other rashi will):\n"
        f"{anchor.get('opening_style', 'Open with a concrete image, not a generic feeling.')}\n"
        f"\n"
        f"Write ONLY the reading for {anchor['en']} / {anchor['sa']}. "
        f"Output must start with `## {anchor['en']} / {anchor['sa']}` then flowing prose. "
        f"Follow the opening-style hint above. Do not use any banned opening phrase."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", default="en", choices=("en", "hi"))
    ap.add_argument("--date", default=_ist_today())
    ap.add_argument("--rashi", default="all",
                    help="English slug (aries, taurus, ...) or 'all'")
    ap.add_argument("--key-only", action="store_true",
                    help="print just the GCS storage key and exit")
    args = ap.parse_args()
    try:
        key, brief = build(args.lang, args.date, args.rashi)
    except Exception as exc:  # noqa: BLE001 — the caller must write nothing
        print(f"rashifal_brief: could not build the brief: {exc}", file=sys.stderr)
        return 2
    print(key if args.key_only else brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
