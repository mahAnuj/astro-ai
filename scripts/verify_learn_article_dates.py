#!/usr/bin/env python3
"""Verify hardcoded festival dates in /learn articles against the repo's own sources.

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
repo fails a check.

  Gate 1 - article date vs its source.  Every "Month D, YYYY" in a learn
      article that can be CONFIDENTLY tied to a SOURCE (see below) must equal
      what that source says for that year. Anything that cannot be tied to a
      source is reported as UNCHECKED, not passed and not failed — see the
      coverage section, which prints every unchecked claim with the reason.
      Silent coverage is how #143 survived; an unchecked date is a fact about
      this gate, not about the article.

  Gate 2 - weekday name vs the date it labels.  A claim written
      "Tuesday, Nov 10, 2026" must actually fall on a Tuesday. This runs on
      every dated claim including the ones Gate 1 cannot attribute, because it
      needs no festival at all — just the calendar. It is the check that would
      have caught a date edit that forgot to move the day name with it, which
      is the exact mistake the #143 fix had to avoid making.

  Gate 3 - attribution completeness in muhurat/festival articles.  In a
      STRICT article (see below), a date this gate cannot attribute is a FAIL,
      not an UNCHECKED. A page whose entire subject is "here are the dates" has
      no business carrying a date that no source in this repo can confirm. In
      every other article the same claim stays UNCHECKED and does not affect the
      exit code, because a date in a prose explainer is usually an illustration,
      not a claim about the calendar.

  Gate 4 - corroboration of bare dates in muhurat/festival articles.  A
      date-shaped string with no year of its own ("Chaturmas opens two days
      later, on Jul 14") is checked in a STRICT article too: either it
      inherited a year and attributed, in which case Gate 1 owns it, or its
      month and day must match one of the dates that article has already
      verified. Before this gate, nothing reached
      `diwali-muhurat-2026.html:22`'s "until Nov 10" — Govardhan Puja, the #143
      date, in prose, in the article #143 was filed against — which is why it
      exists; the second clause now corroborates that string against the same
      article's own verified Nov 10. See the section on it below for why it
      cannot fabricate a failure.

TWO KINDS OF SOURCE
-------------------
A `Source` answers one question: "what date is <name> in <year>?".

  `RegistrySource` - a `festival_registry` row. Hand-typed, Drik-verified,
      three years of coverage.
  `ComputedSource` - a callable that COMPUTES the date from the ephemeris:
      `muhurat._ABUJHA_RULES` via `muhurat._abujha_days` (Akshaya Tritiya,
      Basant Panchami, Bhadli Navami, Devuthani Ekadashi, and Tulsi Vivah as
      Devuthani + 1, exactly as `_abujha_days` derives it), and
      `sankranti.sankranti_date` for the Dhanu / Makar / Meena / Mesha
      sankrantis.

Every computed source is code the repo ALREADY SHIPS and already renders to
users. No almanac fact is typed into this file: the only literal dates below
are the six sankranti anchors in `_SANKRANTI_ANCHORS`, which are assertions
ABOUT the computation, not inputs to it, and which fail the run if they stop
holding.

Where a phrase is known to both kinds, the REGISTRY WINS — it is the source of
truth, and the computed value is instead used to check it (preflight B).

COMPUTED SOURCES ARE THE OPPOSITE OF A SUPPRESSION LIST
-------------------------------------------------------
Read that section below first; this paragraph exists so nobody mistakes the
one for the other. A suppression list REMOVES claims from the gate's reach:
after adding to it, a wrong date passes. A computed source ADDS claims to the
gate's reach: "Bhadli Navami — Monday, Jul 12, 2027" was UNCHECKED before,
because the registry has no Bhadli Navami row, and is now compared against
`lunar_dates.shukla_tithi_date(2027, "Ashadha", 9)` — a wrong date there is a
FAIL that did not exist before. The direction of every source added here must
be that one. If a "source" you are about to add would make a currently-failing
claim stop failing, it is a suppression list wearing a different hat, and the
answer is no.

NO SUPPRESSION LIST
-------------------
There is deliberately no whitelist of known-bad articles here.
`verify_adhik_maas.py` had a defect tolerance, it hid a real break, and it was
deleted with a note saying not to reintroduce one. The same rule applies:
a mismatch is a FAIL naming the file, the line and both dates. If this script
exits 1 on a date nobody has fixed yet, that is the script working — fix the
date or the registry, do not teach the gate to look away.

There is also no opt-in list of strict articles, for the same reason a
suppression list is banned: a list is a thing you forget to update. Strictness
is DERIVED from the filename (`strict_articles`), so a future
`sharad-purnima-2027.html` enters strict mode the day it is created.

SCOPE
-----
Two written forms are recognised, both with an optional leading weekday:
"Month D, YYYY" ("Tuesday, Nov 10, 2026") and "D Month YYYY"
("Friday, 20 Nov 2026"). Both produce identical claims, so every gate treats
them the same.

The second form is not a convenience. Only the first was recognised at first,
and `griha-pravesh-muhurat-2026-2027.html` — a STRICT article — was written
entirely in the second, so all ~21 of its dates were invisible: the gate
reported it as "0 unattributed of 0" and passed a file it had never read. An
article must not be able to evade this gate by choosing a prose style, because
a gate that reports success on what it never examined is the exact defect it
exists to prevent. Any further form found in an article belongs here too.

A YEARLESS DATE IS REPORTED, NOT HIDDEN
---------------------------------------
Both forms above require a 4-digit year, because a date with no year cannot be
compared to anything. An article about a single year, though, naturally stops
repeating it: `vivah-muhurat-2027.html` says "Chaturmas opens two days later, on
Jul 14". Five such strings sat in that file while the coverage report called it
"0 unattributed of 20" — invisible to all three gates, which is the same shape
as #143 whatever the values happen to be.

So `_BARE_DATE_RE` (separate from `_DATE_RE`, which still defines what a claim
is) finds date-SHAPED strings, and Coverage prints every one the gate did not
turn into a claim, with the reason. Two kinds stay unchecked and are LISTED
rather than assumed away:

  ranges  - "Nov 20-25", "20-25 Nov", "17 May-15 Jun". A range names no single
            day; it has always been out of scope and still is. The gate now
            says so per occurrence instead of silently skipping it.
  bare dates with no year obtainable - "the sequence skips Nov 7 and Nov 9 this
            year" in a block that never states a year. Nothing can be inferred,
            so nothing is.

In a STRICT article only, a bare single "Month D" may INHERIT a year: from the
one distinct year of the full claims on its own line, else from the one distinct
year in its block, else not at all. Two or more distinct years in the winning
scope decline, as ambiguity always does here. Ranges never inherit. Non-strict
articles never inherit, because inventing claims across 71 unaudited explainers
would report failures on prose that never claimed a date.

An inherited claim is a real claim: same attribution, same Gate 1, same Gate 2.
It is marked `year_source="inherited"` and counted separately so it is never
read as something the article spelled out, and it may only ADD checks — see
`_attribute` for the guard that stops a bare date from taking a festival name
that a written-out date on the same line is already using. Gate 3 does not fail
an inherited date it cannot attribute: the article never wrote a year there, so
a decline is a fact about the gate's reach, and every one of them is listed in
Coverage.

A BARE DATE MUST CORROBORATE ONE THE ARTICLE ALREADY VERIFIED
-------------------------------------------------------------
Inheritance only reaches the bare dates whose scope names a single year and a
single festival; `diwali-muhurat-2026.html:22`'s "until Nov 10" has neither, and
sat UNCHECKED. The obvious-looking fix — let `_attribute` reach further — is the
wrong one and is deliberately NOT taken: that bare "Nov 10" sits in a block
about Amavasya and Chaturdashi, and `vivah-muhurat-2027.html:98`'s bare "Jul 14"
sits on a line naming Bhadli Navami while being Devshayani Ekadashi. Widening
attribution would hand each of them a name that belongs to a different
observance and FABRICATE a Gate 1 failure against a date that is correct.

Gate 4 asks a weaker question that cannot fabricate anything, because IT NEVER
ASSIGNS A NAME. For each bare date in a strict article it compares only
(month, day) against the set of (month, day) pairs that article's own explicit,
attributed claims stand behind — claims Gate 1 already checks, so a wrong value
in that set fails the run on its own. It cannot say "Bhadli Navami should be on
X"; the only thing it can say is "this date-shaped string is not one of the
dates this article already verified". There is no path from it to a Gate 1
comparison, and no year is needed, so no new inheritance tier exists and bare
dates stay out of `_attribute` entirely.

Three holes stay open, and are stated here rather than left to read as coverage:

  ranges  - still out of scope, as everywhere else in this file. A range names
            no single day, so a range endpoint can be corrupted invisibly to
            every gate here. Coverage prints this per run rather than implying
            the strict articles are fully defended.
  ordinals - "the 7th" carries no month, matches no regex here, and is
            therefore invisible to Gate 4. That is the accepted residual, and
            it is the shape of one of this gate's own remedies: rewriting a
            date-shaped string that claims no festival date as an ordinal moves
            it out of reach on purpose. It does not assert LESS — "the 7th"
            names the same day to a reader that "Nov 7" does — it only puts the
            string beyond this gate, which is appropriate where there is no
            festival-date claim and is an evasion where there is one.
  right day, wrong observance - this gate checks SET MEMBERSHIP, not identity.
            A bare date is corroborated by ANY day that article verified, so
            prose naming the wrong observance for the date beside it passes
            clean whenever that date happens to be some other verified day of
            the same article. A page carrying a run of festivals a few days
            apart — which every Diwali-week article does — therefore has dates
            that corroborate each other's prose no matter which name the
            sentence uses. This is inherent to never assigning a name: the
            property that stops the gate fabricating a failure is the same one
            that stops it seeing this. It is the price of the design, not a
            defect in it, and still strictly more than the nothing these
            strings had before.

Association is scoped, in exactly two conservative tiers:

  line  - exactly one distinct source named on the same line as the date.
  block - zero sources on the line, and exactly one distinct source in the
          BLOCK (the maximal run of consecutive non-blank lines around it).
          This exists because an article that opens a <ul> with the festival
          name and puts the date on the next <li> was previously unreachable.

There is no third tier and there never should be: a wrong attribution is worse
than no attribution, because it turns a real check into a fabricated one. Both
tiers additionally DECLINE when the winning scope carries two or more dates of
the same year — one festival name cannot say which of them it labels.

Usage:  uv run python scripts/verify_learn_article_dates.py
"""

from __future__ import annotations

import html
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
LEARN_DIR = REPO_ROOT / "src" / "astro_ai" / "templates" / "learn"

sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import festival_registry, muhurat, sankranti  # noqa: E402


# --------------------------------------------------------------------------
# Sources - the two things that can answer "what date is X in year Y?"
# --------------------------------------------------------------------------

class Source:
    """Something that can resolve a named observance to a date in a year.

    Identity is `key`, so the same source reached through two different
    spellings ("Chhoti Diwali", "Naraka Chaturdashi") counts once when a scope
    is checked for ambiguity.
    """

    kind = "source"

    def __init__(self, key: str, label: str) -> None:
        self.key = key
        self.label = label

    def date_for(self, year: int) -> date | None:  # pragma: no cover - abstract
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Source) and other.key == self.key

    def __hash__(self) -> int:
        return hash(self.key)

    def __repr__(self) -> str:
        return f"<{self.kind} {self.key}>"


class RegistrySource(Source):
    """A `festival_registry` row — the source of truth, and it wins ties."""

    kind = "registry"

    def __init__(self, slug: str) -> None:
        self.fest = _BY_SLUG[slug]
        super().__init__(f"registry:{slug}", self.fest.name_en)

    def date_for(self, year: int) -> date | None:
        iso = self.fest.dates.get(year)
        return date.fromisoformat(iso) if iso else None


class ComputedSource(Source):
    """A date computed from the ephemeris by code this repo already ships.

    `resolve` must return None rather than raise for a year it cannot answer;
    the preflight then reports that as a failure instead of the run dying.
    """

    kind = "computed"

    def __init__(self, name: str, resolve: Callable[[int], date | None]) -> None:
        self._resolve = resolve
        super().__init__(f"computed:{name.lower().replace(' ', '-')}", name)

    def date_for(self, year: int) -> date | None:
        try:
            return self._resolve(year)
        except Exception:
            return None


_BY_SLUG = {f.slug: f for f in festival_registry.FESTIVALS}


# --------------------------------------------------------------------------
# Computed sources - built from repo code, no dates typed here
# --------------------------------------------------------------------------

def _abujha_resolver(name: str) -> Callable[[int], date | None]:
    """Look `name` up in `muhurat._abujha_days(year)`.

    That function owns the month/tithi/reckoning per rule and owns the
    Tulsi Vivah = Devuthani + 1 derivation, so this reads its answer rather
    than restating any part of it.
    """
    def resolve(year: int) -> date | None:
        for day, entries in muhurat._abujha_days(year).items():
            if any(entry_name == name for entry_name, _events in entries):
                return day
        return None
    return resolve


def _sankranti_resolver(rashi: str) -> Callable[[int], date | None]:
    def resolve(year: int) -> date | None:
        return sankranti.sankranti_date(year, rashi)
    return resolve


# Rashis whose sankranti the articles actually name — the Kharmas boundaries
# (Dhanu opens Dhanurmas, Makar closes it, Meena opens Meenmas, Mesha closes
# it). Adding the other eight would cost nothing but claims nothing either.
_SANKRANTI_RASHIS: tuple[str, ...] = ("Dhanu", "Makara", "Meena", "Mesha")


def computed_sources() -> dict[str, ComputedSource]:
    """Phrase -> ComputedSource, derived entirely from repo code.

    `muhurat._ABUJHA_RULES` supplies its own four names; Tulsi Vivah is added
    because `muhurat._abujha_days` derives it from Devuthani + 1 and therefore
    already answers for it. `sankranti` supplies the four sankranti names plus
    the spellings in `sankranti._ALIASES` ("Makar" alongside "Makara"), so that
    the spelling the articles and the registry use is the spelling looked up.
    """
    sources: dict[str, ComputedSource] = {}

    abujha_names = [name for name, *_rest in muhurat._ABUJHA_RULES]
    abujha_names.append("Tulsi Vivah")
    for name in abujha_names:
        sources[name.lower()] = ComputedSource(name, _abujha_resolver(name))

    for rashi in _SANKRANTI_RASHIS:
        src = ComputedSource(f"{rashi} Sankranti", _sankranti_resolver(rashi))
        sources[f"{rashi} Sankranti".lower()] = src
        # `sankranti._ALIASES` is imported deliberately, same precedent as
        # `sankranti.py` importing `adhik_maas._sun_rashi`: the alias table is
        # the repo's own record of which spellings are in circulation, and
        # retyping "makar" here would be a second copy to drift.
        for alias, canonical in sankranti._ALIASES.items():
            if canonical == rashi:
                sources[f"{alias} sankranti"] = src

    return sources


# --------------------------------------------------------------------------
# Sankranti anchors - assertions ABOUT the computation, not inputs to it
# --------------------------------------------------------------------------

# Published almanac readings for six sankranti observance dates. They live in
# `sankranti.py`'s docstring as prose, where nothing executes them: if someone
# changes that module's sunset convention, the docstring goes stale silently
# and every sankranti date in every article moves with it. Asserting them here
# makes that change loud.
#
# The three Makar dates are independently corroborated INSIDE this repo by
# `festival_registry`'s makar-sankranti and pongal rows (both Drik-verified,
# festival_registry.py:141 and :174) — preflight B compares those rows against
# the same computation, so Makar is checked twice by two different paths.
#
# Dhanu 2026, Meena 2027 and Mesha 2027 have no registry row and are the ones
# these literals exist for: Drik Panchang, New Delhi (geoname-id 1261481),
# read 2026-08-08, per `sankranti.py`'s VALIDATION section (b).
_SANKRANTI_ANCHORS: tuple[tuple[int, str, str], ...] = (
    (2026, "Makara", "2026-01-14"),   # also registry-verified
    (2027, "Makara", "2027-01-15"),   # also registry-verified
    (2028, "Makara", "2028-01-15"),   # also registry-verified
    (2026, "Dhanu",  "2026-12-16"),   # Drik, New Delhi, read 2026-08-08
    (2027, "Meena",  "2027-03-15"),   # Drik, New Delhi, read 2026-08-08
    (2027, "Mesha",  "2027-04-14"),   # Drik, New Delhi, read 2026-08-08
)


# --------------------------------------------------------------------------
# Festival name -> Source
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


def registry_phrases() -> dict[str, str]:
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


def build_sources() -> tuple[dict[str, Source], list[tuple[str, RegistrySource, ComputedSource]]]:
    """The one phrase -> Source map, plus the phrases both kinds claim.

    Registry precedence: a phrase known to both resolves to the RegistrySource.
    The displaced ComputedSource is not discarded — it is returned as an
    overlap so the preflight can require the two to agree, which is how the
    computation gets checked against the hand-verified rows.
    """
    sources: dict[str, Source] = {}
    overlaps: list[tuple[str, RegistrySource, ComputedSource]] = []

    computed = computed_sources()
    for phrase, csrc in computed.items():
        sources[phrase] = csrc

    for phrase, slug in registry_phrases().items():
        if slug not in _BY_SLUG:
            continue  # reported by the preflight below, not silently dropped
        rsrc = RegistrySource(slug)
        prior = sources.get(phrase)
        if isinstance(prior, ComputedSource):
            overlaps.append((phrase, rsrc, prior))
        sources[phrase] = rsrc

    return sources, overlaps


SOURCES, OVERLAPS = build_sources()

_KNOWN_SLUGS = set(_BY_SLUG)
_UNKNOWN_ALIASES = sorted(set(HAND_ALIASES.values()) - _KNOWN_SLUGS)

# Longest phrase first so "Chhoti Diwali" is consumed before the "Diwali"
# sitting inside it can be matched separately.
_PHRASE_RE = re.compile(
    "|".join(
        rf"\b{re.escape(p)}\b"
        for p in sorted(SOURCES, key=len, reverse=True)
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

# Number -> the longest spelling `_MONTHS` carries, for report text only.
# Inverted from `_MONTHS` rather than retyped so there is one month table here,
# not two.
_MONTH_NAME = {
    num: name.capitalize()
    for name, num in sorted(_MONTHS.items(), key=lambda kv: len(kv[0]))
}

_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ORDINAL = r"(?:st|nd|rd|th)?"

# One regex with two alternatives, never two passes: `finditer` yields
# non-overlapping matches, so a date cannot be counted once per form and
# inflate the coverage denominator. "Month D" is tried first as the more
# specific form.
#
# Both alternatives require a real name from `_MONTHS` fenced by `\b`, so
# "15 minutes 2027" cannot match (no month) and "15 Maybe 2027" cannot either
# (the `\b` after the month rejects "May" inside "Maybe"). The year is factored
# out of the alternation, which is why only month/day need per-form names.
#
# The lookbehind on the "D Month" form rejects a day glued to punctuation:
# "20-25 Nov 2026" (a range — out of scope, same as "Nov 20-25, 2026"),
# "v1.2 Nov 2026", "10:25 Nov 2026". A preceding digit is already impossible
# because of the `\b`, so "2026 Nov" cannot yield a day of "26".
_DATE_RE = re.compile(
    rf"(?:(?P<weekday>{'|'.join(_WEEKDAYS)}),\s*)?"
    rf"(?:"
    rf"\b(?P<month_a>{_MONTH_RE})\b\s+(?P<day_a>\d{{1,2}}){_ORDINAL}"
    rf"|"
    rf"(?<![\d./:\-–—])\b(?P<day_b>\d{{1,2}}){_ORDINAL}"
    rf"\s+(?P<month_b>{_MONTH_RE})\b"
    rf")"
    rf",?\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)


def _month_day(m: re.Match[str]) -> tuple[int, int]:
    """(month number, day number) from whichever date form matched.

    Works for `_DATE_RE` and for the single-date forms of `_BARE_DATE_RE`,
    which use the same group names on purpose.
    """
    month = m.group("month_a") or m.group("month_b")
    day = m.group("day_a") or m.group("day_b")
    return _MONTHS[month.lower()], int(day)


# The blind spot `_DATE_RE` leaves, made visible instead of assumed away.
#
# `_DATE_RE` requires a 4-digit year on every match, which is right for a claim:
# a date with no year cannot be compared to anything. But an article about one
# year naturally drops the year on the second mention — "Chaturmas opens two
# days later, on Jul 14" — and every such string was invisible to all three
# gates while the coverage report called that file "0 unattributed of 20". A
# dated string no gate reads is the exact shape of #143, so it is now counted
# and listed even where it cannot be checked.
#
# This is a SEPARATE regex on purpose. Loosening `_DATE_RE` would change what
# counts as a claim in all 75 articles at once; this one feeds the report, the
# strict-article year inheritance below, and Gate 4's corroboration check —
# none of which can turn a string here into a named festival claim.
#
# Range alternatives come first so "Jan 19-20" is seen whole rather than as
# "Jan 19", and so a cross-month range ("17 May-15 Jun 2026") is not reported as
# the bare date "17 May". Ranges remain out of scope either way — the point is
# that "out of scope" is now printed rather than silent.
#
# `(?!\d)` on the single "Month D" form is what keeps "Jan 2027" from reading as
# "Jan 20"; `_DATE_RE` does not need it because a 4-digit year must follow there.
_BARE_DATE_RE = re.compile(
    rf"(?:(?P<weekday>{'|'.join(_WEEKDAYS)}),\s*)?"
    rf"(?:"
    rf"(?P<range_a>\b(?:{_MONTH_RE})\b\s+\d{{1,2}}{_ORDINAL}"
    rf"\s*[-–—]\s*\b(?:{_MONTH_RE})\b\s+\d{{1,2}}{_ORDINAL})"
    rf"|"
    rf"(?P<range_b>(?<![\d./:\-–—])\b\d{{1,2}}{_ORDINAL}\s+(?:{_MONTH_RE})\b"
    rf"\s*[-–—]\s*\d{{1,2}}{_ORDINAL}\s+(?:{_MONTH_RE})\b)"
    rf"|"
    rf"(?P<range_c>\b(?:{_MONTH_RE})\b\s+\d{{1,2}}{_ORDINAL}"
    rf"\s*[-–—]\s*\d{{1,2}}{_ORDINAL})"
    rf"|"
    rf"(?P<range_d>(?<![\d./:\-–—])\b\d{{1,2}}{_ORDINAL}"
    rf"\s*[-–—]\s*\d{{1,2}}{_ORDINAL}\s+(?:{_MONTH_RE})\b)"
    rf"|"
    rf"\b(?P<month_a>{_MONTH_RE})\b\s+(?P<day_a>\d{{1,2}}){_ORDINAL}(?!\d)"
    rf"|"
    rf"(?<![\d./:\-–—])\b(?P<day_b>\d{{1,2}}){_ORDINAL}"
    rf"\s+(?P<month_b>{_MONTH_RE})\b"
    rf")",
    re.IGNORECASE,
)

_RANGE_GROUPS = ("range_a", "range_b", "range_c", "range_d")

RANGE_REASON = (
    "date range — ranges name no single day and have always been out of this "
    "gate's scope, exactly as 'Nov 20-25, 2026' is"
)
NON_STRICT_REASON = (
    "no year — a bare date inherits one only in a muhurat/festival article"
)


def _is_range(m: re.Match[str]) -> bool:
    return any(m.group(g) for g in _RANGE_GROUPS)


def _unclaimed_dates(text: str) -> list[re.Match[str]]:
    """Date-shaped strings in `text` that `_DATE_RE` did not read as claims.

    Anything overlapping a real claim is dropped, so the "Jul 12" inside
    "Monday, Jul 12, 2027" is not reported as an unchecked bare date.
    """
    claimed = [(m.start(), m.end()) for m in _DATE_RE.finditer(text)]
    return [
        m for m in _BARE_DATE_RE.finditer(text)
        if not any(m.start() < end and start < m.end() for start, end in claimed)
    ]


def _inherit_year(
    line_years: Counter[int], blk_years: Counter[int]
) -> tuple[int | None, str]:
    """The year a bare date may borrow from its scope, or None and why not.

    Precedence is line, then block, and nothing looser. Two or more distinct
    years in the winning scope DECLINE rather than pick — same principle as the
    attribution tiers, where ambiguity is always a decline.
    """
    for scope, years in (("this line", line_years), ("its block", blk_years)):
        distinct = sorted(set(years))
        if len(distinct) == 1:
            return distinct[0], ""
        if len(distinct) > 1:
            return None, (
                f"no year of its own, and {scope} carries dates in "
                + ", ".join(str(y) for y in distinct)
                + " — ambiguous, so no year was inherited"
            )
    return None, "no year on this line or in its block"


@dataclass(frozen=True)
class BareDate:
    """A date-shaped string in a STRICT article that wrote no year of its own.

    Gate 4's population, and it is deliberately NOT a `Claim`: only the month
    and day are kept, because corroboration compares (month, day) and needs no
    year. That is what keeps these strings out of `_attribute` — see the
    corroboration section of the header.

    `became_claim` records that it inherited a year and went on through
    attribution as a `Claim`; whether that claim ATTRIBUTED is read back off
    the claims themselves, so the two can never disagree.
    """

    path: Path
    line_no: int
    raw: str
    month: int
    day_num: int
    became_claim: bool

    @property
    def where(self) -> str:
        return f"{self.path.name}:{self.line_no}"


@dataclass(frozen=True)
class Unclaimed:
    """A date-shaped string this gate did NOT turn into a claim, and why."""

    path: Path
    line_no: int
    raw: str
    reason: str

    @property
    def where(self) -> str:
        return f"{self.path.name}:{self.line_no}"


_JINJA_RE = re.compile(r"\{[%{#].*?[%}#]\}", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]*>")

# Comment delimiters that may span lines. `plain_text` is line-scoped and
# `_TAG_RE` only eats a `<...>` that closes on the same line, so the MIDDLE
# lines of a multi-line comment would otherwise arrive as prose — and the
# provenance comments in these articles are full of dates. That reads a
# comment's working as an article's claim. `_visible` closes the hole.
_COMMENT_SPANS: tuple[tuple[str, str], ...] = (("{#", "#}"), ("<!--", "-->"))


def _visible(line: str, open_span: int | None) -> tuple[str, int | None]:
    """Strip comment spans, carrying an unterminated one across lines.

    `open_span` is the index into `_COMMENT_SPANS` of a comment still open from
    an earlier line, or None. Returns the part of `line` a reader would see and
    the state to pass to the next line.
    """
    out: list[str] = []
    i = 0
    while i < len(line):
        if open_span is not None:
            closer = _COMMENT_SPANS[open_span][1]
            end = line.find(closer, i)
            if end == -1:
                break
            i = end + len(closer)
            open_span = None
            continue
        starts = [
            (line.find(opener, i), idx)
            for idx, (opener, _closer) in enumerate(_COMMENT_SPANS)
            if line.find(opener, i) != -1
        ]
        if not starts:
            out.append(line[i:])
            break
        start, idx = min(starts)
        out.append(line[i:start])
        i = start + len(_COMMENT_SPANS[idx][0])
        open_span = idx
    return " ".join(out), open_span


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
    text: str            # the whole plain-text line the claim sits on
    raw: str             # the matched date string as written
    weekday: str | None
    day: date | None     # None when the written date is not a real calendar day
    source: Source | None  # what the claim was attributed to, if anything
    scope: str           # "line" | "block" | "" when unattributed
    reason: str          # why it is unchecked; "" when checked
    # "explicit" when the year was written next to the date, "inherited" when a
    # bare "Month D" in a strict article borrowed it from its scope. Kept so an
    # inherited claim is never counted or reported as something the article
    # actually spelled out.
    year_source: str = "explicit"

    @property
    def where(self) -> str:
        return f"{self.path.name}:{self.line_no}"


def sources_in(text: str) -> list[Source]:
    """Distinct sources named in `text`, longest name winning."""
    found: list[Source] = []
    for m in _PHRASE_RE.finditer(text):
        src = SOURCES[m.group(0).lower()]
        if src not in found:
            found.append(src)
    return found


def _years_in(text: str) -> list[int]:
    return [int(m.group("year")) for m in _DATE_RE.finditer(text)]


def collect_claims() -> tuple[list[Claim], list[Unclaimed], int, list[BareDate]]:
    claims: list[Claim] = []
    unclaimed: list[Unclaimed] = []
    bare_dates: list[BareDate] = []
    articles = sorted(LEARN_DIR.glob("*.html"))
    for path in articles:
        raw_lines = path.read_text(encoding="utf-8").splitlines()

        # Pass 1: reader-visible text per line, with multi-line comments
        # suppressed, and the block each line belongs to. A block is a maximal
        # run of consecutive non-blank lines — the article's own paragraph /
        # list-item grouping, which is what "the surrounding text" means to a
        # reader.
        texts: list[str] = []
        block_of: list[int] = []
        open_span: int | None = None
        block = 0
        for raw in raw_lines:
            if not raw.strip():
                block += 1
                texts.append("")
                block_of.append(-1)
                continue
            visible, open_span = _visible(raw, open_span)
            texts.append(plain_text(visible))
            block_of.append(block)

        # Pass 2: per-block source sets and per-block year counts.
        block_sources: dict[int, list[Source]] = {}
        block_years: dict[int, Counter[int]] = {}
        for text, blk in zip(texts, block_of):
            if blk < 0 or not text:
                continue
            known = block_sources.setdefault(blk, [])
            for src in sources_in(text):
                if src not in known:
                    known.append(src)
            block_years.setdefault(blk, Counter()).update(_years_in(text))

        # Pass 2b: date-shaped strings `_DATE_RE` did not read, and the year (if
        # any) each may borrow. Resolved before pass 3 so that the same-year
        # guard there can see every inherited date in a scope, not just the ones
        # earlier on the line.
        strict = is_strict(path)
        bare: dict[int, list[tuple[re.Match[str], int | None, str]]] = {}
        line_inh_years: dict[int, Counter[int]] = {}
        blk_inh_years: dict[int, Counter[int]] = {}
        for line_no, (text, blk) in enumerate(zip(texts, block_of), 1):
            if not text:
                continue
            for m in _unclaimed_dates(text):
                if _is_range(m):
                    year, why = None, RANGE_REASON
                elif not strict:
                    # 71 articles nobody has audited: inventing claims there
                    # would report failures on prose that never claimed a date.
                    year, why = None, NON_STRICT_REASON
                else:
                    year, why = _inherit_year(
                        Counter(_years_in(text)),
                        block_years.get(blk, Counter()),
                    )
                bare.setdefault(line_no, []).append((m, year, why))
                if strict and not _is_range(m):
                    # Recorded whether or not it inherited a year: Gate 4's
                    # population is every bare date on these pages, and the
                    # ones that inherited are the ones clause (a) lets through.
                    month, day_num = _month_day(m)
                    bare_dates.append(BareDate(
                        path=path, line_no=line_no, raw=m.group(0),
                        month=month, day_num=day_num,
                        became_claim=year is not None,
                    ))
                if year is not None:
                    line_inh_years.setdefault(line_no, Counter())[year] += 1
                    blk_inh_years.setdefault(blk, Counter())[year] += 1

        # Pass 3: the claims themselves.
        for line_no, (text, blk) in enumerate(zip(texts, block_of), 1):
            if not text:
                continue
            line_sources = sources_in(text)
            line_years = Counter(_years_in(text))

            # Explicit claims first, then the bare dates that inherited a year.
            # Both go through the same attribution and produce the same `Claim`,
            # which is the point: an inherited claim is checked by every gate a
            # written-out one is.
            dated: list[tuple[re.Match[str], int, bool]] = [
                (m, int(m.group("year")), False) for m in _DATE_RE.finditer(text)
            ]
            dated += [
                (m, year, True)
                for m, year, _why in bare.get(line_no, [])
                if year is not None
            ]

            for m, year, inherited in dated:
                month, day_num = _month_day(m)
                try:
                    day = date(year, month, day_num)
                except ValueError:
                    day = None

                source, scope, reason = _attribute(
                    year=year,
                    day=day,
                    line_sources=line_sources,
                    line_years=line_years,
                    blk_sources=block_sources.get(blk, []),
                    blk_years=block_years.get(blk, Counter()),
                    line_inh_years=line_inh_years.get(line_no, Counter()),
                    blk_inh_years=blk_inh_years.get(blk, Counter()),
                    inherited=inherited,
                )

                weekday = m.group("weekday")
                claims.append(
                    Claim(
                        path=path,
                        line_no=line_no,
                        text=text,
                        raw=m.group(0),
                        weekday=weekday.capitalize() if weekday else None,
                        day=day,
                        source=source,
                        scope=scope,
                        reason=reason,
                        year_source="inherited" if inherited else "explicit",
                    )
                )

            for m, year, why in bare.get(line_no, []):
                if year is None:
                    unclaimed.append(
                        Unclaimed(path=path, line_no=line_no, raw=m.group(0),
                                  reason=why)
                    )
    return claims, unclaimed, len(articles), bare_dates


def _attribute(
    *,
    year: int,
    day: date | None,
    line_sources: list[Source],
    line_years: Counter[int],
    blk_sources: list[Source],
    blk_years: Counter[int],
    line_inh_years: Counter[int],
    blk_inh_years: Counter[int],
    inherited: bool,
) -> tuple[Source | None, str, str]:
    """Attribute one date to at most one source. Declines rather than guesses.

    Tier order is line, then block, and there is no third tier. The same-year
    guard applies to whichever scope won: one festival name in a scope holding
    two dates of that year says nothing about which of them it labels, and a
    coin flip there would manufacture a check out of nothing.

    An INHERITED date (a bare "Month D" that borrowed its year) counts the other
    inherited dates in scope towards that guard as well, so it attributes only
    when it is the single date of its year there. An explicit claim's tally is
    untouched — inheritance may only ADD checks, never take one away, and
    "Bhadli Navami — Monday, Jul 12, 2027 (... Chaturmas opens two days later,
    on Jul 14)" is why the guard has to bite here: the line names one festival,
    the bare Jul 14 is a different observance entirely, and handing it that name
    would fabricate a Gate 1 failure against a date that is correct.
    """
    if day is None:
        return None, "", "not a real calendar date"
    if year not in festival_registry.DATA_YEARS:
        return None, "", (
            f"year {year} is outside registry coverage "
            f"{min(festival_registry.DATA_YEARS)}-"
            f"{max(festival_registry.DATA_YEARS)}"
        )

    if len(line_sources) == 1:
        source, scope, same_year = line_sources[0], "line", line_years[year]
        if inherited:
            same_year += line_inh_years[year]
    elif len(line_sources) > 1:
        return None, "", (
            "ambiguous — " + ", ".join(s.label for s in line_sources)
            + " all named on this line"
        )
    elif len(blk_sources) == 1:
        source, scope, same_year = blk_sources[0], "block", blk_years[year]
        if inherited:
            same_year += blk_inh_years[year]
    elif len(blk_sources) > 1:
        return None, "", (
            "no festival named on this line, and the surrounding block names "
            + str(len(blk_sources)) + " (" + ", ".join(s.label for s in blk_sources) + ")"
        )
    else:
        return None, "", "no known festival named on this line or in its block"

    if same_year >= 2:
        return None, "", (
            f"ambiguous — {same_year} dates in {year} but only one festival "
            f"named in scope ({scope})"
            + (" — an inherited year may not take a name another date is using"
               if inherited else "")
        )
    return source, scope, ""


# --------------------------------------------------------------------------
# Strict articles - derived from the filename, never listed
# --------------------------------------------------------------------------

# A page whose own title is a muhurat, a festival, or a named registry festival
# is a page whose subject IS the dates. `festivals` covers the plural form.
_STRICT_TOKENS = {"muhurat", "festival", "festivals"}


def _contains_run(tokens: list[str], run: tuple[str, ...]) -> bool:
    return any(
        tuple(tokens[i:i + len(run)]) == run
        for i in range(len(tokens) - len(run) + 1)
    )


def strict_articles() -> list[Path]:
    """Every strict article on disk, whether or not it carries a dated claim.

    Enumerated from the directory rather than from the claims, so a strict
    article that currently has NO recognised date still appears in the coverage
    report as "0 of 0" instead of vanishing — a strict article silently
    dropping out of the report is the shape of regression this gate exists to
    make loud.
    """
    return sorted((p for p in LEARN_DIR.glob("*.html") if is_strict(p)),
                  key=lambda p: p.name)


def is_strict(path: Path) -> bool:
    """True if `path` is a muhurat/festival article, from its filename alone.

    Derived, never listed — see the docstring. `karva-chauth-2026.html` is
    strict because `karva-chauth` is a registry slug and its tokens appear
    contiguously in the stem; a future `sharad-purnima-2027.html` becomes
    strict on the day it is created, with nothing to remember to update.
    """
    tokens = path.stem.split("-")
    if _STRICT_TOKENS & set(tokens):
        return True
    return any(
        _contains_run(tokens, tuple(slug.split("-")))
        for slug in _KNOWN_SLUGS
    )


# --------------------------------------------------------------------------
# Preflight - the gate's own inputs, checked before any article is read
# --------------------------------------------------------------------------

def preflight() -> list[str]:
    """Problems with this script's sources. Any one of them stops the run.

    A gate whose sources are broken cannot report anything trustworthy about
    the articles, so these are checked first and reported separately from the
    article gates.
    """
    problems: list[str] = []

    if _UNKNOWN_ALIASES:
        problems.append(
            "HAND_ALIASES points at slug(s) the registry does not have: "
            + ", ".join(_UNKNOWN_ALIASES)
            + " — the alias table has drifted from the registry."
        )

    # A - every computed source answers for every covered year. A source that
    # returns None is not a check, it is a silent gap.
    computed = sorted(
        {s for s in SOURCES.values() if isinstance(s, ComputedSource)}
        | {c for _phrase, _r, c in OVERLAPS},
        key=lambda s: s.key,
    )
    for src in computed:
        for year in festival_registry.DATA_YEARS:
            if src.date_for(year) is None:
                problems.append(
                    f"computed source {src.label!r} resolves no date for {year} "
                    "— it cannot check anything in that year"
                )

    # B - where both kinds know a phrase, they must agree. The registry rows
    # are hand-typed and Drik-verified; the computation is independent of them.
    # A disagreement means one of the two is wrong and neither can be trusted
    # until it is resolved.
    for phrase, rsrc, csrc in sorted(OVERLAPS, key=lambda o: o[0]):
        for year in festival_registry.DATA_YEARS:
            want, got = rsrc.date_for(year), csrc.date_for(year)
            if want != got:
                problems.append(
                    f"{phrase!r} {year}: registry {rsrc.label} says {want}, "
                    f"computed {csrc.label} says {got} — the registry row and "
                    "the ephemeris disagree"
                )

    # C - the six published sankranti anchors. See _SANKRANTI_ANCHORS.
    for year, rashi, expected in _SANKRANTI_ANCHORS:
        got = sankranti.sankranti_date(year, rashi)
        if got is None or got.isoformat() != expected:
            problems.append(
                f"sankranti anchor {rashi} {year}: expected {expected}, "
                f"got {got} — sankranti.py no longer reproduces a published "
                "almanac date it is documented as reproducing"
            )

    return problems


# --------------------------------------------------------------------------
# Gate 1 - article date vs its source
# --------------------------------------------------------------------------

def gate_1_source_agreement(claims: list[Claim]) -> list[str]:
    failures: list[str] = []

    checked = 0
    by_kind: Counter[str] = Counter()
    for claim in claims:
        if claim.source is None or claim.day is None:
            continue
        src = claim.source
        want = src.date_for(claim.day.year)
        if want is None:
            failures.append(
                f"{claim.where}: {src.label} claimed on {claim.day.isoformat()} but "
                f"the {src.kind} source has no {claim.day.year} date for {src.key}"
            )
            continue
        checked += 1
        by_kind[src.kind] += 1
        if claim.day != want:
            delta = (claim.day - want).days
            fix = (
                "Registry is the source of truth; fix the article, or verify the "
                "date against the almanac and fix both."
                if src.kind == "registry" else
                "The computed value comes from the same engine the site renders "
                "from; fix the article, or if the engine is wrong fix that first."
            )
            failures.append(
                f"{claim.where}: {src.label} — article says {claim.raw!r} "
                f"({claim.day.isoformat()}), {src.kind} says {want.isoformat()} "
                f"({delta:+d} days). {fix}"
            )

    print(f"  {checked} date claim(s) attributed and compared "
          f"({by_kind['registry']} registry, {by_kind['computed']} computed)")
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
# Gate 3 - attribution completeness in muhurat/festival articles
# --------------------------------------------------------------------------

def gate_3_strict_attribution(claims: list[Claim]) -> list[str]:
    """Every date in a muhurat/festival article must be attributable.

    Elsewhere an unattributable date is UNCHECKED and costs nothing. Here it is
    a FAIL, because the article exists to state dates: a date on such a page
    that no source in this repo can confirm is either mis-worded (name the
    festival on the line) or is a claim nobody can verify, and #143 was exactly
    the second kind.
    """
    failures: list[str] = []
    strict = strict_articles()
    n_claims = 0
    n_inherited = 0
    for claim in claims:
        if not is_strict(claim.path):
            continue
        if claim.year_source == "inherited":
            # An inherited-year date is a bonus check, not part of this gate's
            # population: the article never wrote a year there, so a decline
            # says the gate could not reach it, not that the prose is wrong.
            # It is still compared by Gate 1 whenever it does attribute, and
            # every declined one is listed in Coverage rather than dropped.
            n_inherited += 1
            continue
        n_claims += 1
        if claim.source is not None:
            continue
        failures.append(
            f"{claim.where}: {claim.raw!r} cannot be attributed to any source "
            f"— {claim.reason}. This is a muhurat/festival article, so an "
            "unverifiable date is a failure: name the festival on the line, or "
            "drop the date."
        )
    print(f"  {n_claims} date claim(s) across {len(strict)} strict article(s)"
          + (f", plus {n_inherited} inherited-year date(s) not required to attribute"
             if n_inherited else ""))
    return failures


# --------------------------------------------------------------------------
# Gate 4 - bare dates in muhurat/festival articles must corroborate
# --------------------------------------------------------------------------

def _verified_days(claims: list[Claim]) -> dict[Path, set[tuple[int, int]]]:
    """Per article, the (month, day) pairs its own EXPLICIT claims stand behind.

    Only attributed claims count, because those are the ones Gate 1 compares
    against a source: a wrong value in here fails the run on its own, so
    nothing corroborated against it can be quietly wrong. Inherited claims are
    excluded — a date the article never spelled out is not something the
    article vouched for, and letting one corroborate another bare date would
    make two unverified strings agree and call that a check.

    The year is dropped deliberately. It is what removes any need for a bare
    date to obtain one, and therefore any need to put it through `_attribute`.
    """
    days: dict[Path, set[tuple[int, int]]] = {}
    for claim in claims:
        if claim.year_source != "explicit" or claim.source is None:
            continue
        if claim.day is None:
            continue
        days.setdefault(claim.path, set()).add((claim.day.month, claim.day.day))
    return days


def _attributed_inherited(claims: list[Claim]) -> set[tuple[Path, int, str]]:
    """Bare dates that inherited a year AND attributed, keyed as written."""
    return {
        (c.path, c.line_no, c.raw)
        for c in claims
        if c.year_source == "inherited" and c.source is not None
    }


def _corroboration(
    item: BareDate,
    verified: dict[Path, set[tuple[int, int]]],
    attributed: set[tuple[Path, int, str]],
) -> str:
    """One bare date's verdict: "attributed", "corroborated", or "" for neither.

    Shared by Gate 4 and Coverage so what is printed cannot drift from what set
    the exit code.
    """
    if item.became_claim and (item.path, item.line_no, item.raw) in attributed:
        return "attributed"
    if (item.month, item.day_num) in verified.get(item.path, set()):
        return "corroborated"
    return ""


def _fmt_md(month: int, day_num: int) -> str:
    return f"{_MONTH_NAME[month]} {day_num}"


def gate_4_corroboration(claims: list[Claim], bare: list[BareDate]) -> list[str]:
    """A bare date on a muhurat/festival page must agree with one of its own.

    Gate 3 reaches only strings that wrote a year. `diwali-muhurat-2026.html:22`
    said Shukla Pratipada runs "until Nov 10" — Govardhan Puja, the #143 date,
    in the article #143 was filed against — and no gate read it, because the
    line names no year and no single festival.

    This gate never assigns a name, so it cannot manufacture a Gate 1 failure
    the way a widened `_attribute` would; see the header. It asks only whether
    the (month, day) is one the article has already put its name to.
    """
    failures: list[str] = []
    verified = _verified_days(claims)
    attributed = _attributed_inherited(claims)

    counts: Counter[str] = Counter()
    for item in bare:
        verdict = _corroboration(item, verified, attributed)
        counts[verdict] += 1
        if verdict:
            continue
        known = sorted(verified.get(item.path, set()))
        shown = ", ".join(_fmt_md(*md) for md in known) or "none"
        failures.append(
            f"{item.where}: {item.raw!r} is not one of the dates this article "
            f"verifies ({shown}). If it is a festival-date claim, name the "
            "source on the line and write the year, so Gates 1-3 check it. If "
            "it is not, a bare ordinal (\"the 7th\") is acceptable — but it "
            "asserts the same day to a reader and only moves the string out of "
            "this gate's reach, so it rewords a non-claim and never fixes a "
            "wrong date."
        )

    print(f"  {len(bare)} bare date(s) in {len(strict_articles())} strict "
          f"article(s), {counts['corroborated']} corroborated, "
          f"{counts['attributed']} attributed, {counts['']} uncorroborated")
    return failures


# --------------------------------------------------------------------------
# Coverage - what this gate could not check, and why
# --------------------------------------------------------------------------

def print_coverage(
    claims: list[Claim], unclaimed: list[Unclaimed], n_articles: int,
    bare: list[BareDate],
) -> None:
    explicit = [c for c in claims if c.year_source == "explicit"]
    inherited = [c for c in claims if c.year_source == "inherited"]
    checked = [c for c in explicit if c.source is not None]
    unchecked = [c for c in explicit if c.source is None]
    pct = (100.0 * len(checked) / len(explicit)) if explicit else 0.0

    by_scope = Counter(c.scope for c in checked)
    print(f"  {n_articles} article(s) scanned, {len(explicit)} dated claim(s) found")
    print(f"  {len(checked)} checked ({pct:.0f}%), {len(unchecked)} unchecked")
    print(f"  attribution scope: {by_scope['line']} line, {by_scope['block']} block")
    for claim in unchecked:
        tag = "strict" if is_strict(claim.path) else "non-strict"
        print(f"    UNCHECKED {claim.where}: {claim.raw!r} — {claim.reason} ({tag})")
    if not unchecked:
        print("    every dated claim was attributed to a source")

    # Bare dates that borrowed a year. Printed apart from the claims above so an
    # inherited year is never mistaken for one the article wrote down.
    inh_checked = [c for c in inherited if c.source is not None]
    print(f"  {len(inherited)} bare date(s) inherited a year from their scope, "
          f"{len(inh_checked)} of them attributed and compared")
    for claim in inherited:
        shown = claim.day.isoformat() if claim.day else "not a real date"
        if claim.source is None:
            print(f"    INHERITED {claim.where}: {claim.raw!r} -> {shown} — "
                  f"unattributed: {claim.reason}")
        else:
            print(f"    INHERITED {claim.where}: {claim.raw!r} -> {shown} — "
                  f"{claim.source.label} ({claim.scope})")

    # Change 1: the strings this gate does NOT defend, counted and named. The
    # point of printing them is that a future editor can see the hole in one
    # line instead of discovering it the way #143 was discovered.
    print(f"  {len(unclaimed)} date-shaped string(s) carried no usable year and "
          "were not checked:")
    for item in unclaimed:
        tag = "strict" if is_strict(item.path) else "non-strict"
        print(f"    NO-YEAR {item.where}: {item.raw!r} — {item.reason} ({tag})")
    if not unclaimed:
        print("    every date-shaped string in every article was read as a claim")

    # Gate 4's population, one line per occurrence and with its verdict, for
    # the same reason the NO-YEAR list above is printed: a hole nobody can see
    # reads as coverage.
    verified = _verified_days(claims)
    attributed = _attributed_inherited(claims)
    print(f"  {len(bare)} bare date(s) in strict article(s) checked by Gate 4:")
    for item in bare:
        verdict = _corroboration(item, verified, attributed)
        if verdict == "attributed":
            detail = "inherited a year and attributed — compared by Gate 1"
        elif verdict == "corroborated":
            detail = (f"corroborated by this article's verified "
                      f"{_fmt_md(item.month, item.day_num)}")
        else:
            detail = "UNCORROBORATED"
        print(f"    BARE {item.where}: {item.raw!r} — {detail}")
    if not bare:
        print("    (none — no strict article carries a date without a year)")
    print("    range endpoints remain UNDEFENDED: a range names no single day, "
          "so either end of a 'Jan 19-20' can be corrupted and no gate here "
          "will see it")

    # Per-strict-article unchecked counts, so a regression in the articles that
    # matter most is one line rather than a diff of the list above.
    strict_paths = strict_articles()
    print("  strict article(s), unattributed count:")
    if not strict_paths:
        print("    (none — no article filename names a muhurat or a registry festival)")
    for path in strict_paths:
        n_bad = sum(1 for c in explicit if c.path == path and c.source is None)
        n_all = sum(1 for c in explicit if c.path == path)
        n_inh = sum(1 for c in inherited if c.path == path)
        n_no_year = sum(1 for u in unclaimed if u.path == path)
        print(f"    {path.name}: {n_bad} unattributed of {n_all}"
              f", {n_inh} inherited, {n_no_year} unchecked no-year string(s)")


# --------------------------------------------------------------------------

def main() -> int:
    strict_names = [p.name for p in strict_articles()]
    n_computed = len({s for s in SOURCES.values() if isinstance(s, ComputedSource)})
    n_registry = len({s for s in SOURCES.values() if isinstance(s, RegistrySource)})

    print("Learn article date verification")
    print(f"  articles : {LEARN_DIR.relative_to(REPO_ROOT)}/*.html")
    print("  registry : src/astro_ai/festival_registry.py")
    print("  computed : muhurat._ABUJHA_RULES (+ Tulsi Vivah), sankranti.sankranti_date")
    print(f"  years    : {', '.join(str(y) for y in festival_registry.DATA_YEARS)}")
    print(f"  sources  : {n_registry} registry + {n_computed} computed, "
          f"reached by {len(SOURCES)} name(s)/alias(es)")
    print(f"  strict   : {len(strict_names)} article(s) — {', '.join(strict_names)}")
    print()

    print("Preflight - this script's own sources")
    problems = preflight()
    for line in problems:
        print(f"  FAIL: {line}")
    if problems:
        print(f"  -> FAIL ({len(problems)} problem(s))")
        print()
        print("FAIL — the gate's sources are broken; no article was checked. "
              "Fix the source disagreement first.")
        return 1
    print(f"  {len(OVERLAPS)} phrase(s) known to both kinds agree with the registry "
          f"in all {len(festival_registry.DATA_YEARS)} year(s)")
    print(f"  {len(_SANKRANTI_ANCHORS)} published sankranti anchor(s) reproduced")
    print("  -> PASS")
    print()

    claims, unclaimed, n_articles, bare = collect_claims()

    gates = [
        ("Gate 1 - article date vs its source (registry or computed)",
         lambda: gate_1_source_agreement(claims)),
        ("Gate 2 - weekday name vs the date it labels",
         lambda: gate_2_weekday_agreement(claims)),
        ("Gate 3 - attribution completeness in muhurat/festival articles",
         lambda: gate_3_strict_attribution(claims)),
        ("Gate 4 - bare dates in muhurat/festival articles must corroborate",
         lambda: gate_4_corroboration(claims, bare)),
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
    print_coverage(claims, unclaimed, n_articles, bare)
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
