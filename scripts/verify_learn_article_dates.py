#!/usr/bin/env python3
"""Verify hardcoded festival dates in /learn articles against the registry.

WHY THIS EXISTS
---------------
`festival_registry.py` is the single source of truth for festival dates and is
held there by `scripts/verify_festivals.py` (five gates) and
`scripts/verify_adhik_maas.py`. The 75 static articles under
`templates/learn/` are NOT derived from it — they restate dates inline as
prose, so nothing stopped the two from drifting apart.

They did drift. `learn/diwali-muhurat-2026.html` shipped Govardhan Puja on
Nov 9 2026 and Bhai Dooj on Nov 10 2026, one day early each, while the
registry carried the verified Nov 10 and Nov 11 (issue #143). The article's
weekday names were correct *for the wrong dates*, so a reader sanity-checking
the day names would not have caught it, and no gate anywhere looked at article
prose.

Rendering 75 static articles off the registry is a much larger change than the
bug warranted. This script is the cheap version of the same guarantee: the
articles may keep hardcoding dates, but a hardcoded date that contradicts the
registry fails a check.

  Gate 1 - article date vs registry date.  Every "Month D, YYYY" in a learn
      article that can be CONFIDENTLY tied to a festival slug must equal that
      festival's registry date for that year. Confidently means: exactly one
      festival name appears on the same line as the date, and the year is one
      the registry covers. Anything else is reported as UNCHECKED, not passed
      and not failed — see the coverage section, which prints every unchecked
      claim with the reason. Silent coverage is how #143 survived; an
      unchecked date is a fact about this gate, not about the article.

  Gate 2 - weekday name vs the date it labels.  A claim written
      "Tuesday, Nov 10, 2026" must actually fall on a Tuesday. This runs on
      every dated claim including the ones Gate 1 cannot attribute, because it
      needs no festival at all — just the calendar. It is the check that would
      have caught a date edit that forgot to move the day name with it, which
      is the exact mistake the #143 fix had to avoid making.

NO SUPPRESSION LIST
-------------------
There is deliberately no whitelist of known-bad articles here.
`verify_adhik_maas.py` had a defect tolerance, it hid a real break, and it was
deleted with a note saying not to reintroduce one. The same rule applies:
a mismatch is a FAIL naming the file, the line and both dates. If this script
exits 1 on a date nobody has fixed yet, that is the script working — fix the
date or the registry, do not teach the gate to look away.

SCOPE
-----
Only dates of the form "Month D, YYYY" (with an optional leading weekday) are
recognised. Date ranges ("Nov 20-25"), bare months, and tithi names carry no
year and are not claims this gate can check. Association is line-local: a
festival named on a different line than its date is not associated, by design.

Usage:  uv run python scripts/verify_learn_article_dates.py
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LEARN_DIR = REPO_ROOT / "src" / "astro_ai" / "templates" / "learn"

sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import festival_registry  # noqa: E402


# --------------------------------------------------------------------------
# Festival name -> slug
# --------------------------------------------------------------------------

# Spellings the articles use that the registry's `name_en` does not produce on
# its own. Kept short and hand-written: every entry is a transliteration
# variant of a name already in the registry, never a new festival. Adding a
# festival here that the registry does not carry would be inventing data.
HAND_ALIASES: dict[str, str] = {
    "naraka chaturdashi": "narak-chaturdashi",
    "chhoti diwali": "narak-chaturdashi",
    "kali chaudas": "narak-chaturdashi",
    "deepawali": "diwali",
    "basant panchami": "vasant-panchami",
    "karwa chauth": "karva-chauth",
    "janmashtami": "krishna-janmashtami",
    "mahashivratri": "maha-shivratri",
    "maha shivaratri": "maha-shivratri",
    "vijaya dashami": "dussehra",
    "gudi padwa": "ugadi-gudi-padwa",
    "ugadi": "ugadi-gudi-padwa",
}

# Parenthetical fragments in `name_en` that are qualifiers, not names.
_NOT_A_NAME = {"begins"}


def festival_phrases() -> dict[str, str]:
    """Lowercased name phrase -> festival slug.

    Derived from the registry first — `name_en` plus each of its
    slash-separated and parenthesised alternatives, so "Diwali (Deepavali)"
    yields both "diwali" and "deepavali" without anyone typing them here —
    then extended by HAND_ALIASES.
    """
    phrases: dict[str, str] = {}
    for fest in festival_registry.FESTIVALS:
        parts = re.split(r"[()/]", fest.name_en)
        for part in parts:
            phrase = part.strip()
            if len(phrase) < 4 or not phrase[0].isupper():
                continue
            if phrase.lower() in _NOT_A_NAME:
                continue
            phrases[phrase.lower()] = fest.slug
    for phrase, slug in HAND_ALIASES.items():
        phrases[phrase] = slug
    return phrases


PHRASES = festival_phrases()
_KNOWN_SLUGS = {f.slug for f in festival_registry.FESTIVALS}
_UNKNOWN_ALIASES = sorted(set(HAND_ALIASES.values()) - _KNOWN_SLUGS)

# Longest phrase first so "Chhoti Diwali" is consumed before the "Diwali"
# sitting inside it can be matched separately.
_PHRASE_RE = re.compile(
    "|".join(
        rf"\b{re.escape(p)}\b"
        for p in sorted(PHRASES, key=len, reverse=True)
    ),
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Date claims
# --------------------------------------------------------------------------

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_WEEKDAYS = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
)

_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DATE_RE = re.compile(
    rf"(?:(?P<weekday>{'|'.join(_WEEKDAYS)}),\s*)?"
    rf"\b(?P<month>{_MONTH_RE})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?,?\s+"
    rf"(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)

_JINJA_RE = re.compile(r"\{[%{#].*?[%}#]\}", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]*>")


def plain_text(line: str) -> str:
    """One template line as reader-visible text, tags and Jinja removed.

    Tags become a space rather than nothing so that `<strong>Bhai
    Dooj</strong> — Nov 11` does not weld words together, and so that nothing
    inside an attribute (a URL, a class list) can be read as prose.
    """
    line = _JINJA_RE.sub(" ", line)
    line = _TAG_RE.sub(" ", line)
    return re.sub(r"\s+", " ", html.unescape(line)).strip()


@dataclass(frozen=True)
class Claim:
    path: Path
    line_no: int
    text: str          # the whole plain-text line the claim sits on
    raw: str           # the matched date string as written
    weekday: str | None
    day: date | None   # None when the written date is not a real calendar day
    slug: str | None   # festival the claim was attributed to, if exactly one
    reason: str        # why it is unchecked; "" when checked

    @property
    def where(self) -> str:
        return f"{self.path.name}:{self.line_no}"


def slugs_on_line(text: str) -> list[str]:
    """Distinct festival slugs named on this line, longest name winning."""
    found: list[str] = []
    for m in _PHRASE_RE.finditer(text):
        slug = PHRASES[m.group(0).lower()]
        if slug not in found:
            found.append(slug)
    return found


def collect_claims() -> tuple[list[Claim], int]:
    claims: list[Claim] = []
    articles = sorted(LEARN_DIR.glob("*.html"))
    for path in articles:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            text = plain_text(line)
            if not text:
                continue
            for m in _DATE_RE.finditer(text):
                year = int(m.group("year"))
                month = _MONTHS[m.group("month").lower()]
                try:
                    day = date(year, month, int(m.group("day")))
                except ValueError:
                    day = None

                slugs = slugs_on_line(text)
                slug: str | None = None
                reason = ""
                if day is None:
                    reason = "not a real calendar date"
                elif year not in festival_registry.DATA_YEARS:
                    reason = (
                        f"year {year} is outside registry coverage "
                        f"{min(festival_registry.DATA_YEARS)}-"
                        f"{max(festival_registry.DATA_YEARS)}"
                    )
                elif not slugs:
                    reason = "no registry festival named on this line"
                elif len(slugs) > 1:
                    reason = "ambiguous — " + ", ".join(slugs) + " all named on this line"
                else:
                    slug = slugs[0]

                weekday = m.group("weekday")
                claims.append(
                    Claim(
                        path=path,
                        line_no=line_no,
                        text=text,
                        raw=m.group(0),
                        weekday=weekday.capitalize() if weekday else None,
                        day=day,
                        slug=slug,
                        reason=reason,
                    )
                )
    return claims, len(articles)


# --------------------------------------------------------------------------
# Gate 1 - article date vs registry date
# --------------------------------------------------------------------------

def gate_1_registry_agreement(claims: list[Claim]) -> list[str]:
    failures: list[str] = []
    by_slug = {f.slug: f for f in festival_registry.FESTIVALS}

    checked = 0
    for claim in claims:
        if claim.slug is None or claim.day is None:
            continue
        fest = by_slug[claim.slug]
        want_iso = fest.dates.get(claim.day.year)
        if want_iso is None:
            failures.append(
                f"{claim.where}: {fest.name_en} claimed on {claim.day.isoformat()} but "
                f"the registry has no {claim.day.year} date for {fest.slug}"
            )
            continue
        checked += 1
        want = date.fromisoformat(want_iso)
        if claim.day != want:
            delta = (claim.day - want).days
            failures.append(
                f"{claim.where}: {fest.name_en} — article says {claim.raw!r} "
                f"({claim.day.isoformat()}), registry says {want_iso} "
                f"({delta:+d} days). Registry is the source of truth; fix the article, "
                f"or verify the date against the almanac and fix both."
            )

    print(f"  {checked} date claim(s) attributed to a registry festival and compared")
    return failures


# --------------------------------------------------------------------------
# Gate 2 - weekday name vs the date it labels
# --------------------------------------------------------------------------

def gate_2_weekday_agreement(claims: list[Claim]) -> list[str]:
    failures: list[str] = []
    checked = 0
    for claim in claims:
        if claim.weekday is None:
            continue
        if claim.day is None:
            failures.append(f"{claim.where}: {claim.raw!r} is not a real calendar date")
            continue
        checked += 1
        actual = claim.day.strftime("%A")
        if actual != claim.weekday:
            failures.append(
                f"{claim.where}: {claim.raw!r} — {claim.day.isoformat()} is a {actual}, "
                f"not a {claim.weekday}. Either the date moved and the day name did not, "
                "or the reverse."
            )
    unlabelled = sum(1 for c in claims if c.weekday is None)
    print(f"  {checked} weekday label(s) checked, {unlabelled} date(s) carry no weekday")
    return failures


# --------------------------------------------------------------------------
# Coverage - what this gate could not check, and why
# --------------------------------------------------------------------------

def print_coverage(claims: list[Claim], n_articles: int) -> None:
    checked = [c for c in claims if c.slug is not None]
    unchecked = [c for c in claims if c.slug is None]

    print(f"  {n_articles} article(s) scanned, {len(claims)} dated claim(s) found")
    print(f"  {len(checked)} checked against the registry, {len(unchecked)} unchecked")
    for claim in unchecked:
        print(f"    UNCHECKED {claim.where}: {claim.raw!r} — {claim.reason}")
    if not unchecked:
        print("    every dated claim was attributed to a festival")


# --------------------------------------------------------------------------

def main() -> int:
    print("Learn article date verification")
    print(f"  articles : {LEARN_DIR.relative_to(REPO_ROOT)}/*.html")
    print("  registry : src/astro_ai/festival_registry.py")
    print(f"  years    : {', '.join(str(y) for y in festival_registry.DATA_YEARS)}")
    print(f"  names    : {len(PHRASES)} festival name(s)/alias(es) recognised")
    print()

    if _UNKNOWN_ALIASES:
        print("HAND_ALIASES points at slug(s) the registry does not have: "
              + ", ".join(_UNKNOWN_ALIASES))
        print("FAIL — the alias table has drifted from the registry.")
        return 1

    claims, n_articles = collect_claims()

    gates = [
        ("Gate 1 - article date vs registry date",
         lambda: gate_1_registry_agreement(claims)),
        ("Gate 2 - weekday name vs the date it labels",
         lambda: gate_2_weekday_agreement(claims)),
    ]

    all_failures: list[str] = []
    results: list[tuple[str, int]] = []
    for title, run in gates:
        print(title)
        failures = run()
        for line in failures:
            print(f"  FAIL: {line}")
        print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
        print()
        results.append((title, len(failures)))
        all_failures.extend(failures)

    print("Coverage")
    print_coverage(claims, n_articles)
    print()

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print()
    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s). Do not add a suppression list; "
              "fix the article, or verify against the almanac and fix the registry.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
