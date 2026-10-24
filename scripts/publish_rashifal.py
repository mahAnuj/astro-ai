#!/usr/bin/env python3
"""Validate a generated rashifal document and, only if it passes, publish it (#515).

This is the safety gate of the nightly Claude Code job, and the gate matters
more than the generation. A malformed blob is **worse than no blob**: the app
reads GCS first (`_shared_three_tier`), so a bad document is a cache HIT. It
suppresses the Groq fallback and ships broken text for a whole day, to the
page and to every subscriber, with nothing raising an error anywhere. This
route already has a 21-day silent outage in its history (2026-08-01..08-21).

So the contract is: **publish a complete, clean document or publish nothing.**
Writing nothing is a success condition, not a failure — `/admin/warm-rashifal`
runs 90 minutes later and generates via Groq exactly as it does today. There is
no flag to leave in the wrong position.

Checks, in order, all of them fatal:
  1. Exactly 12 sections parse, each attributable to exactly ONE distinct rashi.
  2. Every body is inside the prompt's own word range.
  3. No body names a planet the prompt forbids.
  4. No body names Rahu Kaal / Abhijit, or any clock time (#513).
  5. No markdown survived (the page renders raw under `whitespace-pre-line`).

Usage:
    uv run python scripts/publish_rashifal.py --lang en --file /tmp/rashifal-en.txt
    uv run python scripts/publish_rashifal.py --lang en --file ... --dry-run

Exit codes:
    0  published (or validated, with --dry-run)
    1  validation failed — nothing was written, let the Groq path run
    2  could not reach storage — nothing was written, same consequence
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai import storage                                              # noqa: E402
from astro_ai.rashifal_derive import (combined_keys, parse_sectioned_reading,  # noqa: E402
                                      sections_by_rashi)

# The prompt asks for 120-160 words. The gate is deliberately wider than the
# instruction: a reading at 118 words is a style miss, not a reason to drop the
# whole day back to Groq. It is narrow enough to catch a truncated generation
# (the real failure, and what an interrupted job produces) and a runaway one.
_MIN_WORDS, _MAX_WORDS = 90, 220

# `Rahu` is matched only when NOT followed by `Kaal`, so the window ban below
# reports it once rather than twice.
_PLANETS = re.compile(
    r"\b(Sun|Moon|Jupiter|Saturn|Mercury|Mars|Venus|Ketu)\b|\bRahu\b(?!\s+Kaal)")
# Hard clock times AND the soft clocks the old prompt used to teach.
_CLOCK = re.compile(
    r"\b\d{1,2}\s*(?:[:.]\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\b"
    r"|\b(?:mid[- ]morning|near midday|before noon|after noon|midday)\b",
    re.I)
_WINDOWS = re.compile(r"\bRahu\s+Kaal\b|\bAbhijit\b", re.I)
_MARKDOWN = re.compile(r"\*\*|__|`")


def validate(text: str) -> list[str]:
    """Every problem found, as human-readable lines. Empty list = publishable."""
    fails: list[str] = []
    sections = parse_sectioned_reading(text or "")
    attributed = sections_by_rashi(text or "")

    if len(sections) != 12:
        fails.append(f"{len(sections)} section(s) parsed, need exactly 12")
    if len(attributed) != 12:
        # The stricter of the two: `sections_by_rashi` drops a rashi that has
        # no section or two, so this catches a duplicated or misnamed heading
        # that a bare count would wave through.
        fails.append(f"{len(attributed)} rashi/rashis attributable to exactly one "
                     f"section, need 12 — a heading is missing, duplicated or misspelt")

    for title, body in sections:
        name = title.split("/")[0].strip() or title.strip()
        words = len(body.split())
        if not _MIN_WORDS <= words <= _MAX_WORDS:
            fails.append(f"{name}: {words} words, outside {_MIN_WORDS}-{_MAX_WORDS}")
        for label, rx in (("names a planet", _PLANETS), ("states a clock time", _CLOCK),
                          ("names a day window", _WINDOWS), ("contains markdown", _MARKDOWN)):
            hit = rx.search(body)
            if hit:
                fails.append(f"{name}: {label} — {hit.group(0)!r}")
    return fails


# The rashifal day is the IST day, and this job runs when the two calendars
# DISAGREE. At 22:00 UTC the runner's own `date.today()` is still yesterday,
# while `compute_panchang(natal, when=None)` resolves the day through
# `datetime.now(ZoneInfo("Asia/Kolkata"))` and returns tomorrow's. Taking the
# runner's date would write tomorrow's panchang under yesterday's key -- a
# cache HIT on the wrong day, which is the one failure mode this whole job is
# built to avoid. So the default is computed in IST, never from the runner.
def _ist_today() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()


RUNS_KEY = "rashifal_runs.json"
RUNS_KEEP_DAYS = 14
# 12 rashis x 2 languages. The unit the owner asked to see on /admin/ops is the
# READING, not the job: "24/24 successful" or "23/24".
READINGS_PER_DAY = 24


def _record_run(day: str, lang: str, sections: int) -> None:
    """Note a published language on the day's run record. Never raises.

    Written only on a successful publish, so the record says what Claude
    actually put in the bucket -- not what a job reported about itself. A day
    with no entry means Claude published nothing and Groq generated it, which
    is the designed fallback and is exactly how /admin/ops should read it.

    Failing to record must never fail the publish: the reading is already live
    and a missing dashboard row is not worth losing it over.
    """
    def mutate(doc):
        doc = doc if isinstance(doc, dict) else {}
        entry = doc.setdefault(day, {})
        entry[lang] = {"sections": sections, "source": "claude",
                       "at": datetime.now(timezone.utc)
                                 .replace(microsecond=0).isoformat()}
        for stale in sorted(doc)[:-RUNS_KEEP_DAYS]:
            doc.pop(stale, None)
        return doc

    try:
        storage.update_json(RUNS_KEY, mutate, default={})
        print(f"recorded -> {RUNS_KEY}[{day}][{lang}] = {sections} sections")
    except Exception as exc:  # noqa: BLE001 - the reading is already published
        print(f"publish_rashifal: could not record the run ({exc}); the reading "
              f"IS published and serving.", file=sys.stderr)


def _rashi_of(title: str) -> str:
    """The English slug a section heading belongs to ("aries"), or ""."""
    return (title or "").split("/")[0].strip().lower()


def merge_into_day(new_text: str, existing_text: str) -> str:
    """Splice regenerated sections into the day's existing twelve.

    Regenerating ONE rashi must never publish a one-section document: the app
    reads GCS first, so that blob would be a cache HIT and eleven readings
    would vanish for the day. So a partial file is merged into what is already
    published, in the existing order, and the RESULT is what gets validated --
    which means a merge still has to produce twelve clean sections or nothing
    is written.

    A section whose rashi is not already in the day is appended rather than
    dropped; validation then rejects the document if that made thirteen, which
    is the right outcome for a heading nobody can place.
    """
    replacements = {_rashi_of(title): (title, body)
                    for title, body in parse_sectioned_reading(new_text or "")}
    out, seen = [], set()
    for title, body in parse_sectioned_reading(existing_text or ""):
        slug = _rashi_of(title)
        out.append(replacements.get(slug, (title, body)))
        seen.add(slug)
    for slug, pair in replacements.items():
        if slug not in seen:
            out.append(pair)
    return "\n\n".join(f"## {title}\n\n{body.strip()}" for title, body in out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", default="en", choices=("en", "hi"))
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--date", default=_ist_today())
    ap.add_argument("--dry-run", action="store_true",
                    help="validate and report, write nothing")
    ap.add_argument("--merge", action="store_true",
                    help="splice these sections into the day's published document "
                         "instead of replacing it — for regenerating one rashi")
    args = ap.parse_args()

    if not args.file.is_file():
        print(f"publish_rashifal: no such file: {args.file}", file=sys.stderr)
        return 1
    text = args.file.read_text(encoding="utf-8", errors="replace")
    _cache_key, storage_key = combined_keys(args.lang, args.date)

    if args.merge:
        existing = storage.get(storage_key) or ""
        if not existing.strip():
            print(f"publish_rashifal: --merge, but nothing is published at "
                  f"{storage_key} yet. There is no day to splice into; run the "
                  f"full twelve first.", file=sys.stderr)
            return 1
        before = len(parse_sectioned_reading(existing))
        incoming = [t for t, _ in parse_sectioned_reading(text)]
        text = merge_into_day(text, existing)
        print(f"merged {len(incoming)} section(s) into {before} already published: "
              f"{', '.join(_rashi_of(t) for t in incoming) or '(none)'}")

    fails = validate(text)
    print(f"lang={args.lang} date={args.date}")
    print(f"key={storage_key}")
    print(f"bytes={len(text.encode('utf-8'))} sections={len(parse_sectioned_reading(text))}")

    if fails:
        print(f"\nREFUSED — {len(fails)} problem(s), nothing written:")
        for f in fails:
            print(f"  - {f}")
        print("\nThis is not an error to route around. /admin/warm-rashifal will "
              "generate today's reading via Groq at 01:00 UTC, which is the "
              "designed fallback. Writing a partial document here would be a "
              "cache HIT and would suppress it.")
        return 1

    print("\nOK — 12 sections, all attributable, none naming a planet, "
          "a window, a clock time or carrying markdown.")
    if args.dry_run:
        print("--dry-run: nothing written.")
        return 0

    print(f"store: {storage.describe_store()}")
    if not storage.put(storage_key, text):
        print("publish_rashifal: storage.put returned False — nothing is cached. "
              "The Groq path will run.", file=sys.stderr)
        return 2
    print(f"published -> {storage_key}")
    _record_run(args.date, args.lang, len(parse_sectioned_reading(text)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
