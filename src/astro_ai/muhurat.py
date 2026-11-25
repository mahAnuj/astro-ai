"""Muhurat Finder — auspicious-date calculator (Issue #108).

Full-tool version (cycle 9) with 5 classical event types:

  vivah          — wedding
  griha_pravesh  — housewarming
  namkaran       — baby naming
  vidyarambh     — starting education / Akshara-abhyasa
  business       — business venture start / shop opening

Per-event rules are declared in EVENT_RULES; a single score_event() function
consumes those rules + Panchang data + combustion flags and returns a rating.
Common checks (Panchak, Chaturmas, Guru/Shukra combustion, Mercury combustion
for business) are gated by per-event boolean flags in the rule table.

Abujha Muhurats (Tulsi Vivah, Basant Panchami, Akshaya Tritiya etc.) are a
BOOSTER inside score_event, applied after the hard exclusions (#1346): a regional
almanac custom lifts a day that passed them and never waives one.

Sources: none of the tables below is traced to a book in this repo's corpus
unless its own comment says so. Before #716 this line named three classical
texts that are not held, and each rule carried a per-table attribution to one of
them; those are withdrawn. Each table now says what knowledge/*.md records about
it (vedic_reference.md 2A, 29.9, 29.10) or that its source is not held.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta, timezone, datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

import swisseph as swe

from astro_ai import lunar_dates
from astro_ai.adhik_maas import adhik_maas_flag
from astro_ai.chart import (
    combustion_orb,
    Chart, compute_chart, compute_panchang, compute_transit_snapshot,
    compute_sade_sati_details, compute_dasha_state,
    ChartError, NAKSHATRAS, RASHIS,
    _tithi_at, julian_day_utc,
)


# ─── Panchak (Nakshatra Panchaka — avoided for most ceremonies) ──────
# Moon from the THIRD QUARTER (pada 3) of Dhanishta to the end of Revati: the
# last half of Dhanishta, then Shatabhisha, Purva Bhadrapada, Uttara Bhadrapada
# and Revati whole. Source: Raman, Muhurtha (1948) ch. IV "Influence of
# Constellations", p. 26, "Nakshatra Panchaka" (data/ L1227-1235; index L8459).
# Re-read against the book on 2026-11-10 after being filed in #713 as a
# transcription. The old constant flagged ALL of Dhanishta while
# its own comment said "latter half", so a Moon in pada 1-2 was marked Panchak
# too (2026-11-17 noon, pada 2, for one). Whole-nakshatra membership
# cannot say "pada 3 onward"; the rule lives in _is_panchak so it is one
# testable function rather than a set and a comment that can disagree.
_PANCHAK_WHOLE_NAKSHATRAS = {"Shatabhisha", "Purva Bhadrapada",
                             "Uttara Bhadrapada", "Revati"}
_PANCHAK_FIRST_DHANISHTA_PADA = 3


def _is_panchak(nakshatra: str, pada: int) -> bool:
    """True when the Moon is in Nakshatra Panchaka: Dhanishta pada 3 onward,
    or any pada of Shatabhisha .. Revati. An unknown nakshatra is not Panchak
    (the Moon missing from a snapshot must not mark a day avoid)."""
    if nakshatra == "Dhanishta":
        return pada >= _PANCHAK_FIRST_DHANISHTA_PADA
    return nakshatra in _PANCHAK_WHOLE_NAKSHATRAS

# Combustion orbs live in chart.COMBUSTION_ORBS, sourced to
# knowledge/grahas.md §12. This module used to carry its own three constants
# and they DISAGREED: Mercury 12.0 here against 14.0 there, and no retrograde
# distinction at all, where the source gives Mercury 14 direct / 13 retrograde
# and Venus 10 / 9. Jupiter and Venus happened to match on the direct value,
# which is exactly why the Mercury gap survived — two of three agreeing reads
# as a consistent table.
#
# The scoring below now calls chart.combustion_orb() so there is one sourced
# answer per planet. Nothing is recomputed here.


# ─── Personal-matching classical tables ──────────────────────────────
# Tara Bala (star strength): count from user's birth nakshatra to the
# transit day's nakshatra (mod 9 + 1). The nine NAMES are B.V. Raman's, from
# *Muhurtha or Electional Astrology* (1948): Janma, Sampat, Vipat, Kshema,
# Pratyak, Sadhana, Naidhana, Mitra, Parama Mitra (knowledge/vedic_reference.md
# 2A-ter, lines 897-914 of the djvu text; #879). Until #879 positions 5, 6, 7 and
# 9 carried a different spelling (Pratyari, Sadhaka, Vadha, Ati-Mitra) that
# knowledge/ does not trace to any held text. matching.py's Ashtakoota Tara is a
# different use and keeps its own spelling; it is untouched here.
# What is sourced: the names, and that the 1st, 3rd, 5th and 7th are the days to
# avoid (Raman L1063-1066). The split of the other five into "good" and
# "excellent" is this site's own grading, not drawn from a held text, and the
# finder says so. The English glosses that sat beside each name here (obstacle,
# achievement, destruction ...) are not carried: they were not checked against
# the book either.
_TARA_BALA_NAMES = {
    1: ("Janma",     "ok"),        # own birth star — "ok" stays for the single-user match and the bride; a Vivah groom is graded "avoid" in _couple_verdict (#714)
    2: ("Sampat",    "good"),
    3: ("Vipat",     "avoid"),
    4: ("Kshema",    "good"),
    5: ("Pratyak",   "avoid"),
    6: ("Sadhana",   "good"),
    7: ("Naidhana",  "avoid"),
    8: ("Mitra",     "good"),
    9: ("Parama Mitra", "excellent"),
}
# Janma, by name, so the Vivah groom rule below follows the table's own row rather
# than a second spelling that could drift from it (#714).
_JANMA_TARA_NAME = _TARA_BALA_NAMES[1][0]

# Chandra Bala (Moon strength): count from the user's natal Moon rashi to the
# transit-day Moon rashi (1..12). Two surfaces ask two different questions, so
# there are two grade tables (#715):
#
#   "gochara"  -- "how is today's Moon for me?" (daily Rashifal card and email,
#     via chandra_bala_by_rashi). The Moon row of knowledge/vedic_reference.md 2A
#     (Raman, Astrology for Beginners Ch. XII): benefic 1, 3, 6, 7, 10, 11 /
#     malefic 2, 4, 5, 8, 9, 12. House 6 is benefic here.
#   "muhurta"  -- "may I pick this day for an event?" (Muhurat Finder personal
#     match and the Vivah couple verdict). A house is weak when EITHER held source
#     names it: the 2A row above, or Raman, Muhurtha or Electional Astrology
#     (1948), chapter on Chandrabala, which says the Moon should not stand in the
#     6th, 8th or 12th from the person's Janma Rasi in the election chart
#     (knowledge/vedic_reference.md 2A-bis quotes it with its line range).
#     That makes 6 weak here: 2, 4, 5, 6, 8, 9, 12 weak; 1, 3, 7, 10, 11 strong.
#
# Neither source has a third grade, so there is none (until #715, 2, 5 and 9
# fell through to an invented "neutral" that _couple_verdict let pass). The
# attribution that stood here before #716 named a text that is not held and is
# withdrawn.
_CB_GOCHARA_STRONG = {1, 3, 6, 7, 10, 11}
_CB_GOCHARA_WEAK   = {2, 4, 5, 8, 9, 12}
_CB_MUHURTA_STRONG = {1, 3, 7, 10, 11}
_CB_MUHURTA_WEAK   = {2, 4, 5, 6, 8, 9, 12}
_CHANDRA_BALA_SETS = {
    "gochara": (_CB_GOCHARA_STRONG, _CB_GOCHARA_WEAK),
    "muhurta": (_CB_MUHURTA_STRONG, _CB_MUHURTA_WEAK),
}
# Fail at import rather than grade a house by fall-through: on each surface every
# house is one or the other, as in the source tables.
for _strong, _weak in _CHANDRA_BALA_SETS.values():
    assert _strong | _weak == set(range(1, 13)) and not _strong & _weak
del _strong, _weak


@dataclass(frozen=True)
class PartnerFactors:
    """One partner's per-day factors — used inside CoupleMatch for Vivah.

    Extracted subset of PersonalMatch that avoids the chart-level notes
    duplication (those go in CoupleMatch.notes as merged bride+groom).
    """
    tara_bala: str          # "excellent" | "good" | "ok" | "avoid"
    tara_bala_name: str
    chandra_bala: str       # "strong" | "weak" ("" when no Moon was placed)
    manglik_status: str     # "none" | "cancelled" | "mitigated" | "present"
    sade_sati_flag: str     # "" | "Sade Sati Peak/Rising/Setting" | "Ashtama Shani" | "Kantaka Shani"
    dasha_flag: str         # "" | "Rahu Mahadasha" | "Ketu Antardasha" etc.


@dataclass(frozen=True)
class CoupleMatch:
    """Wedding-specific per-day compatibility — computed when TWO charts
    (bride + groom) are provided for Vivah event.

    Each partner's factors are computed independently; the combined verdict
    reflects both partners' Tara + Chandra Bala on the day.
    """
    bride: PartnerFactors
    groom: PartnerFactors
    combined_verdict: str   # "excellent-for-both" | "good-for-both" | "mixed" | "avoid"


@dataclass(frozen=True)
class PersonalMatch:
    """Personal chart context for a muhurat candidate.

    Computed only when a user chart is supplied to find_candidates(). Never
    overrides the classical rating (that stays universal) — surfaces as an
    additional column so users see BOTH the classical read and the personal
    overlay.
    """
    tara_bala: str          # "excellent" | "good" | "ok" | "avoid"
    tara_bala_name: str     # "Sampat" (position 2) etc.
    tara_position: int      # 1..9
    chandra_bala: str       # "strong" | "weak"
    chandra_house: int      # 1..12
    notes: tuple[str, ...]  # e.g. ["Sade Sati Peak — cautious with major events"]


@dataclass(frozen=True)
class MuhuratCandidate:
    """One candidate date with its Panchang details + rating."""
    d: date
    weekday: str
    tithi: str
    tithi_paksha: str
    nakshatra: str
    rating: str               # "excellent" | "good" | "acceptable" | "caution" | "avoid"
    reason: str               # short human explanation
    flags: tuple[str, ...]    # e.g. ("panchak", "chaturmas", "jupiter_combust")
    personal: PersonalMatch | None = None  # only set when a user chart is passed
    couple: CoupleMatch | None = None      # only set for Vivah when two charts provided
    # Sub-day windows already computed in Panchang — surface for planning.
    # All three of rahu_kaal / abhijit_muhurta / choghadiya are EMPTY on a date
    # with no ordinary sunrise-to-sunset span, because each is a fraction of
    # one — see `find_candidates` and `DailyPanchang.daylight_ordinary` (#228).
    # Empty means "this date has no such window", never "not computed yet".
    rahu_kaal: str = ""       # "13:30–15:00"; "" if no daylight span
    abhijit_muhurta: str = "" # "11:48–12:36"; "" if no daylight span
    # Local sunrise "06:58", for the results page's "Times are local to ..." line (#1322). Empty on a
    # date with no ordinary sunrise (#228) for the same reason as rahu_kaal: there is no sunrise to name.
    sunrise: str = ""
    nitya_yoga: str = ""      # e.g. "Siddhi", "Vyatipata"
    boosters: tuple[str, ...] = ()  # Amrit Siddhi / Sarvartha Siddhi / Ravi Yoga names
    # Phase B additions — sub-day precision
    bhadra_window: str = ""   # "" if Bhadra not present; else "Bhadra active 09:00-16:00..."
    choghadiya: tuple[dict, ...] = ()   # 8 day-windows with name/start/end/auspiciousness; () if no daylight span
    # Display-only (#1025): the minutes in which the Abhijit window lies inside Rahu Kaal or
    # Bhadra, e.g. "Abhijit and Rahu Kaal overlap 11:45-12:06". () when it overlaps neither.
    # No rating reads it: the finder holds no source that ranks one window above the other.
    abhijit_overlaps: tuple[str, ...] = ()
    # The soft-scoring points behind `rating` (#1341, R1), so the ranked list can order days WITHIN a
    # tier. LAST and defaulted so every existing construction (tests, fixtures) still works. A
    # booster- or Abujha-lifted day carries its tier's floor (`_RATING_MIN_SCORE`), an avoid day 0.
    score: int = 0


# The ratings the site calls "auspicious" (#1322). "caution" is the lowest tier that passed no hard
# exclusion and is NOT auspicious: it stays visible, in its own group, and is never counted or
# listed as a good date. One definition, read by the finder's headline count (via the Jinja global
# `muhurat_auspicious_ratings`) and by the landing pages' next-dates list (#1325), so the two
# cannot drift apart.
AUSPICIOUS_RATINGS = ("excellent", "good", "acceptable")

# Minimum soft-scoring points for each rating, BEST FIRST (#1341). One table is read by both
# `score_event` (points -> rating) and `find_candidates` (a lifted day's score floor), so the cut-offs
# and the floors cannot drift apart. Dict order is load-bearing: the first floor a score clears wins.
# The weights (+2 tithi, +2 nakshatra, +1 weekday, +1 peak day, -1 avoid weekday) and these cut-offs
# are THIS SITE'S OWN CONVENTION, not a classical figure (astro-auditor 2026-11-21: the sources in
# knowledge/vedic_reference.md §29.11 and §29.13 name the factors, not their weights; the
# `peak_day` Thursday for Vidyarambh is CONTESTED). In-grade order is therefore a point count, and the
# results page says so.
#
# BOOSTER FLOOR DECISION: a day a booster (Amrit/Sarvartha Siddhi, Ravi Yoga) or an Abujha date lifts
# carries its tier's floor as its score. The floor adds NO weight to the booster and moves NO rating:
# the rating is what `score_event` already returned. It only lets the lifted day sort beside the plain
# days of its tier (a lifted day ties with plain 5s, earliest first; a plain 6 beats it) instead of
# at the top or the bottom of it. Sorting boosters first, or on a raw score that a booster never
# touched, were both rejected: docs/decisions/2026-11-21-muhurat-top-pick.md.
_RATING_MIN_SCORE = {"excellent": 5, "good": 4, "acceptable": 3}

# Tier order for the ranked list; "avoid" last. A module constant so `rank_key` and the sort share it.
_TIER_ORDER = {"excellent": 0, "good": 1, "acceptable": 2, "caution": 3, "avoid": 4}


def rank_key(c: MuhuratCandidate) -> tuple[int, int, date]:
    """Sort key of the ranked list: tier, then HIGHER score first, then earlier date (#1341).
    Deterministic, so `top_pick` and the page's order can never disagree."""
    return (_TIER_ORDER.get(c.rating, 99), -c.score, c.d)


def top_pick(candidates: list[MuhuratCandidate]) -> tuple[MuhuratCandidate | None, int]:
    """The best valid day of a result, and how many OTHER valid days tie it on (rating, score).

    Valid means an auspicious rating (never caution or avoid) and, in couple mode, a combined
    verdict that is not "avoid": a day the pair's own factors reject is never the headline. Those
    rows stay in the list. `(None, 0)` when nothing qualifies. A tie is broken by date, so the pick
    is the earliest of its ties and the count lets the page say so honestly."""
    eligible = [c for c in candidates
                if c.rating in AUSPICIOUS_RATINGS
                and not (c.couple and c.couple.combined_verdict == "avoid")]
    if not eligible:
        return None, 0
    best = min(eligible, key=rank_key)
    ties = sum(1 for c in eligible
               if c is not best and (c.rating, c.score) == (best.rating, best.score))
    return best, ties


# ─── Chaturmas (Devshayani Ekadashi → Devuthani Ekadashi) ────────────
# Vishnu's four-month sleep, traditionally weddings-restricted. The window
# runs from Ashadha Shukla Ekadashi to Kartika Shukla Ekadashi — four lunar
# months, ~118 civil days, or ~147 in a year whose Adhik Maas falls inside it.
#
# Both boundaries are COMPUTED from the ephemeris via
# `lunar_dates.shukla_tithi_date`, which resolves the tithi over
# `adhik_maas.lunar_months()` and so cannot be fooled by an intercalary month.
# The gate over it is `scripts/verify_muhurat_tables.py`; run that after any
# change here.
#
# WHY THIS IS NO LONGER A TABLE: a hand-typed `_CHATURMAS_RANGES` year->window
# dict used to sit here, covering 2026-2028 only, and ALL THREE of its rows
# disagreed with the almanac (drikpanchang.com, New Delhi, fetched 2026-08-07):
#
#     shipped 2026 Jul 15 - Nov 11   real 2026-07-25 .. 2026-11-20
#     shipped 2027 Jul  5 - Nov  1   real 2027-07-14 .. 2027-11-10
#     shipped 2028 Jul 23 - Nov 19   real 2028-07-02 .. 2028-10-27
#
# The 2028 row was 21 days out at both ends — it restricted three weeks of
# genuinely clear late-November dates while passing the whole first half of
# July as unrestricted. From 2029 on the dict had no row at all and a fixed
# Jul 15 - Nov 15 fallback took over, which is not a lunar window in any year
# and structurally cannot express the ~147-day adhik-maas case.
#
# NOTE FOR ANYONE READING ISSUE #146: the issue's own body quotes the 2027 and
# 2028 rows above back as "the real windows" (2027 Jul 5-Nov 1, 2028 Jul 23-
# Nov 19). Those are the WRONG table's own values, not almanac values. Drik
# gives Jul 14-Nov 9 and Jul 2-Oct 27. Restoring the issue's numbers trips
# Gate 1 of verify_muhurat_tables.py, which is exactly what it is there for.
# A table with no computation over it has nothing to disagree with.


@lru_cache(maxsize=8)
def _chaturmas_window(year: int) -> tuple[date, date] | None:
    """(Devshayani, Devuthani) Ekadashi for `year`, or None if either is missing.

    Cached at YEAR granularity because `find_candidates` calls `_in_chaturmas`
    once per candidate day and a scan runs up to 365 of them; uncached, each
    call would re-enumerate a year of lunar months.
    """
    start = lunar_dates.shukla_tithi_date(year, "Ashadha", 11)
    end = lunar_dates.shukla_tithi_date(year, "Kartika", 11)
    if start is None or end is None:
        return None
    return (start, end)


# ─── Abujha Muhurats (self-auspicious days) ──────────────────────────
# Regional almanac "swayam-siddha" / "abujha" days. No book this site holds names
# them (knowledge/vedic_reference.md 29.14, UNSOURCED), so they are a booster
# applied after the sourced hard exclusions in `score_event`, never an override:
# until #1346 an Abujha day skipped every exclusion and a Panchak Revati day was
# rated excellent for marriage.
#
# WHAT IS COMPUTED AND WHAT IS POLICY: the DATES below are computed from the
# ephemeris (lunar month + shukla tithi, via `lunar_dates.shukla_tithi_date`).
# The names, the event types each day applies to, and the choice of which days
# count as abujha at all are human policy and stay hand-written here.
#
# WHY THE DATES ARE NO LONGER A TABLE: a hand-typed `_ABUJHA_MUHURATS` dict
# used to sit here with 9 rows across 2026-2027, and ALL NINE disagreed with
# drikpanchang.com (New Delhi, fetched 2026-08-07):
#
#     Akshaya Tritiya 2026    shipped 2026-04-30   real 2026-04-19
#     Bhadli Navami 2026      shipped 2026-06-24   real ~2026-07-23 (a whole
#                                                  lunar month off)
#     Devuthani Ekadashi 2026 shipped 2026-11-19   real 2026-11-20
#     Tulsi Vivah 2026        shipped 2026-11-20   real 2026-11-21
#     Basant Panchami 2026    row missing entirely real 2026-01-23
#     Basant Panchami 2027    shipped 2027-01-23   real 2027-02-11
#     Akshaya Tritiya 2027    shipped 2027-05-19   real 2027-05-09
#     Bhadli Navami 2027      shipped 2027-06-13   real ~2027-07-12
#     Devuthani Ekadashi 2027 shipped 2027-10-31   real 2027-11-10
#     Tulsi Vivah 2027        shipped 2027-11-01   real 2027-11-11
#
# The 2027 Basant Panchami row is the 2026 date filed under a 2027 key — the
# same mistyped-year signature as issue #141's Adhik Maas table. And from 2028
# on the dict simply had no rows, so `.get(d.year, [])` returned [] and every
# abujha day silently ceased to exist: a 2028 wedding scan showed no Akshaya
# Tritiya at all.
#
# TWO RECKONINGS, AND THE SPLIT MATTERS. A tithi does not fill a civil day, so
# the almanac must say which instant fixes the observance:
#   * "sunrise"   — the tithi running at local sunrise. Correct for the
#                   Ekadashi fasts (Devuthani, and Bhadli Navami by the same
#                   convention).
#   * "madhyahna" — the tithi running at the OPENING of madhyahna (midday).
#                   Correct for Akshaya Tritiya and Basant Panchami, which are
#                   madhyahna-vyapini; `festival_registry`'s observance_window
#                   field records this independently.
# Reckoning the midday observances at sunrise moves them by a day in roughly
# one year in three — it gets Akshaya Tritiya 2026 wrong (returns 04-20 for
# Drik's 04-19). See `lunar_dates`' module docstring, which works the two
# discriminating Akshaya Tritiya years through in full.
#
# BHADLI NAVAMI SHIPS UNVERIFIED, AND SAYS SO. The rule (Ashadha Shukla Navami)
# is well attested, but no published almanac date was obtainable on 2026-08-07:
# drikpanchang's New Delhi Hindu calendar does not carry Bhadli / Bhadali /
# Kandarpa Navami in any year fetched (2015, 2026-2029) and its festival URLs
# 404. It is a regional Gujarati/Rajasthani observance. No date was invented to
# fill the gap. Gate 1 of verify_muhurat_tables.py therefore carries NO Bhadli
# Navami row, and the ONLY assertion made about it anywhere is Gate 2's
# structural one: it falls in the same nija Ashadha as the verified Devshayani
# and 1-3 days before it. If a citable source turns up, add it to Gate 1.
#
# (name, nija lunar month, shukla tithi, reckoning, event types)
_ABUJHA_RULES: tuple[tuple[str, str, int, str, tuple[str, ...]], ...] = (
    ("Akshaya Tritiya",    "Vaishakha", 3,  "madhyahna", ("vivah", "griha_pravesh", "business")),
    ("Basant Panchami",    "Magha",     5,  "madhyahna", ("vivah", "griha_pravesh", "vidyarambh", "business")),
    ("Bhadli Navami",      "Ashadha",   9,  "sunrise",   ("vivah",)),
    ("Devuthani Ekadashi", "Kartika",   11, "sunrise",   ("vivah", "griha_pravesh", "business")),
)


@lru_cache(maxsize=8)
def _abujha_days(year: int) -> dict[date, tuple[tuple[str, tuple[str, ...]], ...]]:
    """Abujha days in `year` -> ((name, event_types), ...) in rule order.

    A rule that does not resolve (kshaya month, i.e. that month name is deleted
    from the year's reckoning) is skipped rather than guessed at.

    TULSI VIVAH IS DERIVED AS DEVUTHANI + 1, NOT COMPUTED INDEPENDENTLY. Drik
    places it the day after Devuthani Ekadashi in 5 of 5 verified years (2015,
    2026-2029), including 2026 where the Ekadashi is a kshaya tithi. It is
    reckoned at pradosh (twilight) while `lunar_dates` samples sunrise and
    madhyahna only, so computing it independently could disagree with the
    Ekadashi it is tied to by a day, for no gain in accuracy.

    Cached at YEAR granularity — same reason as `_chaturmas_window`: a 365-day
    scan calls `_abujha_for` once per candidate day.
    """
    days: dict[date, list[tuple[str, tuple[str, ...]]]] = {}
    devuthani: date | None = None
    for name, month, tithi, reckoning, event_types in _ABUJHA_RULES:
        d = lunar_dates.shukla_tithi_date(year, month, tithi, reckoning)
        if d is None:
            continue
        if name == "Devuthani Ekadashi":
            devuthani = d
        days.setdefault(d, []).append((name, event_types))
    if devuthani is not None:
        days.setdefault(devuthani + timedelta(days=1), []).append(
            ("Tulsi Vivah", ("vivah",))
        )
    return {d: tuple(entries) for d, entries in days.items()}


# ─── Per-event classical rule tables ──────────────────────────────────
# ─── Adhik Maas (intercalary lunar month) — absolute blocker ─────────
# The Vedic lunisolar calendar inserts an extra month roughly every 3 years
# to keep the lunar year aligned with the solar one. Adhik Maas = "extra
# month" = Malamas, the "polluted month": no shubh karya inside it. It is an
# absolute blocker and applies to ALL events.
#
# Windows are COMPUTED from the ephemeris — see `astro_ai.adhik_maas`, which
# flags any amanta lunar month containing no solar sankranti. The gate over it
# is `scripts/verify_adhik_maas.py`; run that after any change here.
#
# WHY THIS IS NO LONGER A TABLE: a hand-typed year-to-windows dict used to sit
# here, and its 2028 row was the real 2026 window with the year mistyped (same
# month name, near-identical range). In production that suppressed every valid
# muhurat in May-June 2028 as malamas, while the genuine Adhik Chaitra of
# March-April 2029 raised no warning at all. A table with no computation over
# it has nothing to disagree with — do not reintroduce one.


def _adhik_maas_flag(d: date) -> tuple[bool, str]:
    """Return (is_adhik, name) if d falls within an Adhik Maas window."""
    return adhik_maas_flag(d)


# ─── Amrit Siddhi Yoga — universal-auspicious BOOSTERS ───────────────
# Classical nakshatra+weekday pairings that make a day excellent
# regardless of its soft score (comparable to the Abujha booster but rule-based
# rather than fixed-date; neither waives a hard exclusion). Not traced to the text it was credited to before
# #716, which is not held. knowledge/vedic_reference.md 29.9 finds the concept
# in Raman Ch. VI under the name Siddha Yoga: six of seven weekdays below
# match it; Monday does not (code: Mrigashira, Raman: Shravana). CONTESTED,
# rule unchanged. When active, boosts rating to "excellent" with a specific
# reason.
_AMRIT_SIDDHI_YOGA: dict[str, str] = {
    "Sunday|Hasta":     "Amrit Siddhi (Sun + Hasta)",
    "Monday|Mrigashira":"Amrit Siddhi (Moon + Mrigashira)",
    "Tuesday|Ashwini":  "Amrit Siddhi (Mars + Ashwini)",
    "Wednesday|Anuradha":"Amrit Siddhi (Mercury + Anuradha)",
    "Thursday|Pushya":  "Amrit Siddhi (Jupiter + Pushya)",
    "Friday|Revati":    "Amrit Siddhi (Venus + Revati)",
    "Saturday|Rohini":  "Amrit Siddhi (Saturn + Rohini)",
}


# ─── Sarvartha Siddhi Yoga — universal-auspicious BOOSTERS ───────────
# Broader nakshatra+weekday set. Source not held: UNSOURCED. vedic_reference.md
# 29.9 measures Raman's Siddha Yoga lists as a near-neighbour, not this table
# (2 to 6 entries shared per weekday), and Raman adds a tithi condition this
# code does not implement. Slightly less
# potent than Amrit Siddhi but still classifies the day as universally
# auspicious for shubh karya. Overrides Dagdha and other soft rules but
# NOT Panchak, Chaturmas, Kharmas, Adhik Maas, or Eclipse (those are
# absolute).
_SARVARTHA_SIDDHI_YOGA: dict[str, list[str]] = {
    "Sunday":    ["Hasta", "Mula", "Uttara Phalguni", "Uttara Ashadha",
                    "Uttara Bhadrapada", "Pushya", "Ashwini"],
    "Monday":    ["Rohini", "Mrigashira", "Pushya", "Anuradha", "Shravana"],
    "Tuesday":   ["Ashwini", "Mrigashira", "Krittika", "Ashlesha"],
    "Wednesday": ["Rohini", "Mrigashira", "Anuradha", "Hasta", "Krittika"],
    "Thursday":  ["Revati", "Anuradha", "Ashwini", "Punarvasu", "Pushya"],
    "Friday":    ["Revati", "Anuradha", "Ashwini", "Punarvasu", "Shravana"],
    "Saturday":  ["Rohini", "Swati", "Shravana"],
}


def _amrit_siddhi_flag(weekday: str, nakshatra: str) -> str:
    """Return the Amrit Siddhi Yoga name if active, else empty."""
    return _AMRIT_SIDDHI_YOGA.get(f"{weekday}|{nakshatra}", "")


def _sarvartha_siddhi_flag(weekday: str, nakshatra: str) -> str:
    """Return 'Sarvartha Siddhi Yoga' if active, else empty."""
    if nakshatra in _SARVARTHA_SIDDHI_YOGA.get(weekday, []):
        return "Sarvartha Siddhi Yoga (universally auspicious)"
    return ""


# ─── Ravi Yoga — Sun-based booster ───────────────────────────────────
# Source not held: UNSOURCED (vedic_reference.md section 29 intro and 29.10 item 4
# list _RAVI_YOGA_NAKSHATRAS as unsourced or contested). The table below is NOT the
# Ravi Yogas of knowledge/yogas.md 3 (Rao 11.2: planets beside the Sun in a
# chart). Before #716 it was credited to a text this repo does not hold, and
# that wording described a Sun-Moon nakshatra combination the code does not
# compute. Simplified rule: Sunday +
# nakshatras with Sun-lordship (Krittika, Uttara Phalguni, Uttara Ashadha)
# or Sun-friendly nakshatras. Boost only, doesn't override hard exclusions.
_RAVI_YOGA_NAKSHATRAS = {"Krittika", "Uttara Phalguni", "Uttara Ashadha",
                          "Hasta", "Ashwini", "Pushya"}


def _ravi_yoga_flag(weekday: str, nakshatra: str) -> str:
    """Return 'Ravi Yoga' if active, else empty. Only on Sunday."""
    if weekday == "Sunday" and nakshatra in _RAVI_YOGA_NAKSHATRAS:
        return "Ravi Yoga (Sun-based auspicious combination)"
    return ""


# ─── Atiganda, Shula, Ganda, Vyatipata, Vaidhriti — universal BLOCKERS ─
# Five of the 27 nitya yogas are hard exclusions (#1023). Raman, Muhurtha (1948),
# Panchanga Suddhi, lines 1343-1346 (knowledge/vedic_reference.md section 29.9):
# "the 16th (Atiganda) the 9th (Sula) 10th (Ganda) 17th (Vyathipatha) and 27th
# (Vaidhruti) have deleterious effects upon events which are started or commenced
# under them." ("16th" is an OCR slip for 6th: Atiganda is 6th in his own list.)
# Until #1023 only the last two blocked, so a day under Atiganda or Ganda could rate
# 'excellent'. His longer marriage-only list (lines 3757-3759) is NOT applied here: it
# names "Mrityu", which is not one of the 27, and needs its own check first.
# Nitya yoga is computed as (Sun_longitude + Moon_longitude) / 13.333°.
# Positions in the 27:
#    6 = Atiganda
#    9 = Shula (Raman: "Sula")
#   10 = Ganda
#   17 = Vyatipata — "great transgression"
#   27 = Vaidhriti — "no support"
# The 27 nitya-yoga names used to be duplicated here, with two spellings that
# differed from chart.py's — "Variyan"/"Aindra" against "Variyana"/"Indra"
# (#148). Both are defensible transliterations, but two copies of the same
# astrology with nothing computing over both is how #141 and #146 went wrong:
# they agreed only because the sequence order happened to match, which is luck,
# not a guarantee. chart.py's spellings win because /panchang is the almanac
# users read and chart.py is where the anga functions live.
#
# The blocking set is keyed on chart.py's spellings ("Shula", not Raman's "Sula"):
# `tests/test_muhurat_nitya_blockers.py` pins each name to its index in
# chart._NITYA_YOGA_NAMES, so a spelling drift cannot silently stop a blocker.
_BLOCKING_NITYA_YOGAS = {"Atiganda", "Shula", "Ganda", "Vyatipata", "Vaidhriti"}


def _nitya_yoga_flag(chart: Chart, when: datetime) -> tuple[str, bool]:
    """Return (yoga_name, is_blocking), delegating the maths to chart.py.

    Reads the same `_nitya_yoga_at` that /panchang renders, so the Muhurat
    Finder's blocker path and the almanac can no longer disagree about the
    same instant (#148). They are still read at DIFFERENT instants: /panchang
    at sunrise, the finder at `MUHURTA_INSTANT_HOUR`, so the two columns differ
    on a day the yoga changes in between (98 of 365 days, #1020). `chart` is unused now that the computation needs
    only the moment; it stays in the signature because callers pass it
    positionally and the natal chart is what identifies whose muhurat this is.
    """
    from astro_ai.chart import _nitya_yoga_at, julian_day_utc

    _idx, yoga_name, _sig = _nitya_yoga_at(julian_day_utc(when))
    return yoga_name, yoga_name in _BLOCKING_NITYA_YOGAS


# ─── Per-event landing-page SEO copy ─────────────────────────────────
# Evergreen intro/rules/related content for /muhurat/<slug> landing pages.
# Slugs match EVENT_RULES keys. Kept outside EVENT_RULES so the scoring
# code stays clean.
EVENT_LANDING: dict[str, dict[str, Any]] = {
    "vivah": {
        "slug": "vivah",
        "hero_title": "Vivah Muhurat — Auspicious Wedding Dates",
        "hero_subtitle": "Panchang rules + your chart, not calendar guesswork.",
        "seo_title": "Vivah Muhurat Finder — Wedding Dates with Bride+Groom Pair Scoring",
        "seo_desc": "Free Vivah Muhurat finder: tithi, nakshatra, Panchak, Chaturmas, Kharmas, Bhadra Karana, Nitya Yogas, Guru+Shukra combustion. Bride+groom two-chart scoring.",
        "intro_paragraphs": [
            "A Vivah Muhurat is not merely an 'auspicious day' from a calendar. This tool checks that the tithi and nakshatra are favourable and that the day is clear of Panchak, a rule B.V. Raman's Muhurtha records. It also applies widely followed conventions that are this finder's own choices, not rules from the books this site holds: that Guru (Jupiter) and Shukra (Venus) are not combust (Raman's wedding criteria do not list combustion), no Chaturmas (Devshayani → Devuthani Ekadashi), no Kharmas (Sun in Sagittarius or Pisces), no Dagdha tithi-weekday combinations and no eclipse days. It calls out Abujha muhurats (Tulsi Vivah, Basant Panchami, Akshaya Tritiya), another convention of this finder, which lift a date that has cleared those checks and never waive one.",
            "For a fully personalised recommendation, sign in first — the tool will then overlay Tara Bala (star strength between your natal Moon nakshatra and the transit day) and Chandra Bala (Moon-strength from your natal Moon) on every candidate, plus surface chart-level cautions from Sade Sati phase or active Rahu/Ketu Mahadasha.",
        ],
        "rules_summary": [
            "Guru (Jupiter) uncombust — this finder's own convention, not in Raman's wedding criteria",
            "Shukra (Venus) uncombust — this finder's own convention, not in Raman's wedding criteria",
            "Favourable tithi: 2, 3, 5, 7, 10, 11, 13 (avoid 4, 8, 9, 14, Amavasya, Purnima); the 11th-13th are excluded in the waning half, below",
            "Wedding dates on the 11th, 12th or 13th tithi of the waning (Krishna paksha) half are excluded, following B.V. Raman's Muhurtha, which rejects the dark-half 11th through New Moon for marriage",
            "The bright-half 12th is not credited: Rao's wedding guideline table lists it, Raman's rejects it, so the finder gives it no credit either way",
            "Favourable nakshatra: Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Mula, Uttara Ashadha, Uttara Bhadrapada, Revati; but the first quarter (pada) of Magha and of Mula is excluded, following B.V. Raman's Muhurtha, which rejects it for marriage",
            "No Panchak (Moon in Dhanishta latter half through Revati)",
            "No Chaturmas (Devshayani → Devuthani Ekadashi ≈ mid-July to mid-November) — widely followed convention this finder applies",
            "No Kharmas (Sun in Sagittarius ≈ mid-Dec to mid-Jan; Sun in Pisces ≈ mid-Mar to mid-Apr) — widely followed convention this finder applies",
            "No Dagdha yoga (Sun+Dwadashi, Mon+Ekadashi, Tue+Panchami, Wed+Tritiya, Thu+Shashti, Fri+Ashtami, Sat+Navami) — widely followed convention this finder applies",
            "No eclipse days (day of or ±1 day) — widely followed convention this finder applies",
        ],
        "related_articles": [
            ("/learn/vivah-muhurat-2027/", "Vivah Muhurat 2027 — full guide"),
            ("/learn/kundali-matching-ashtakoot-guna-milan/", "Kundali Matching (Ashtakoot) — check compatibility"),
            ("/learn/manglik-dosh/", "Manglik Dosh — verify before choosing a date"),
            ("/learn/marriage-timing-kundli/", "Marriage timing in your Kundli"),
        ],
        "related_tools": [
            ("/matching", "Kundali Matching", "Guna Milan compatibility for both partners"),
            ("/manglik-check", "Manglik Check", "Verify Manglik status for both partners"),
        ],
    },
    "griha_pravesh": {
        "slug": "griha-pravesh",
        "hero_title": "Griha Pravesh Muhurat — Auspicious House-Warming Dates",
        "hero_subtitle": "Seven criteria + your chart, not developer-handover convenience.",
        "seo_title": "Griha Pravesh Muhurat Finder — Housewarming Date Calculator",
        "seo_desc": "Free Griha Pravesh Muhurat finder: Jupiter visibility, tithi, nakshatra, Panchak, Chaturmas, Kharmas, Bhadra Karana. Apoorva / Sapoorva / Dwandwa entry types.",
        "intro_paragraphs": [
            "Griha Pravesh (house-warming) is the ceremony marking entry into a new home. Three kinds of entry are commonly distinguished: Apoorva (brand-new home), Sapoorva (re-entry after long absence or renovation), and Dwandwa (entry into a home you own but haven't lived in). This finder applies the same timing rules to each.",
            "What this finder checks: Guru (Jupiter) not combust; favourable moon nakshatra; favourable tithi; no Panchak; weekday preference (Monday/Wednesday/Thursday/Friday best; Tuesday excluded outright, Saturday scored one point lower because Raman's chapters disagree about it). It also applies widely followed conventions that are this finder's own choices, not rules from the books this site holds: no Chaturmas, no eclipse days, no Kharmas (Sun in Sagittarius/Pisces) and no Dagdha tithi-weekday combinations.",
        ],
        "rules_summary": [
            "Guru (Jupiter) uncombust — must be visible during ceremony hours",
            "Favourable nakshatra: Rohini, Mrigashira, Uttara Phalguni, Chitra, Anuradha, Uttara Ashadha, Uttara Bhadrapada, Revati",
            "Favourable tithi: 2, 3, 5, 7, 10, 11, 13",
            "Weekday: Mon, Wed, Thu, Fri preferred; Tuesday excluded (Raman); Saturday scores one point lower (Raman's chapters disagree)",
            "No Chaturmas (mid-July to mid-November) — widely followed convention this finder applies",
            "No Kharmas (Sun in Sagittarius/Pisces) — widely followed convention this finder applies",
            "No Panchak days",
            "No Dagdha yoga combinations — widely followed convention this finder applies",
            "No eclipse days — widely followed convention this finder applies",
        ],
        "related_articles": [
            ("/learn/griha-pravesh-muhurat-2026-2027/", "Griha Pravesh Muhurat 2026-27 — full guide"),
            ("/learn/vivah-muhurat-2027/", "Vivah Muhurat 2027 — sister guide"),
        ],
        "related_tools": [
            ("/kundli", "Free Janma Kundli", "Check personal factors for the chosen date"),
            ("/sade-sati-check", "Sade Sati Check", "Verify Saturn transit before major life events"),
        ],
    },
    "namkaran": {
        "slug": "namkaran",
        "hero_title": "Namkaran Muhurat — Auspicious Baby Naming Ceremony Dates",
        "hero_subtitle": "Raman's 10th, 12th or 16th day after birth + auspicious nakshatra and tithi selection for a newborn.",
        "seo_title": "Namkaran Muhurat + Baby First-Letter Nakshatra Table Calculator",
        "seo_desc": "Free Namkaran Muhurat finder: the traditional 108-syllable first-letter table (27 nakshatras × 4 padas) and auspicious days from birth details.",
        "intro_paragraphs": [
            "B.V. Raman's Muhurtha gives the 10th, 12th or 16th day after the child's birth for the naming ceremony, and says an auspicious day must be fixed if that is not possible; many families today choose another day within the first weeks. This finder has no birth date to count from, so its muhurat rules apply to whichever day is chosen. Because this is a child-driven ceremony, some rules that apply to adult-planned events (Chaturmas, Kharmas, Dagdha, Guru combustion) do NOT block Namkaran — the ceremony must happen close to the birth regardless.",
            "What we do check: auspicious nakshatras (Ashwini, Rohini, Mrigashira, Punarvasu, Pushya, Hasta, Chitra, Swati, Anuradha, Shravana, Dhanishta, Shatabhisha, Uttara Phalguni, Uttara Ashadha, Uttara Bhadrapada, Revati), favourable tithi, weekday preference (Mon/Wed/Thu/Fri best), no Panchak, no eclipse. Tithis Raman rejects for naming (4th, 6th, 8th, 12th, 14th, Full Moon, New Moon) are avoided, and so is the 9th, which this finder keeps as its own reading: Raman's figure for it is damaged in the copy this site holds and Rao's Table 79 row omits it. Harsh nakshatras (Bharani, Krittika, Ardra, Ashlesha, Magha, Jyeshtha, Mula) are avoided for infants; Magha is the contested one, because Raman lists it as auspicious for naming and Rao's Table 79 omits it, and this finder follows the avoid reading.",
        ],
        "rules_summary": [
            "Auspicious nakshatra required (Raman's list and Rao's Table 79 row for naming, which both include Dhanishta and Shatabhisha)",
            "Favourable tithi (2, 3, 5, 7, 10, 11, 13); the 4th, 6th, 8th, 9th, 12th, 14th, Full Moon and New Moon are avoided (Raman's list, plus the 9th as this finder's reading)",
            "Weekday: Mon, Wed, Thu, Fri preferred; Tuesday excluded (Raman allows it on the child's 10th, 12th or 16th day; this tool has no birth date to apply that); Saturday scores one point lower",
            "No Panchak",
            "No eclipse days — widely followed convention this finder applies",
            "Chaturmas, Kharmas, Dagdha, combustion checks NOT applied (child-driven timing)",
        ],
        "related_articles": [
            ("/learn/chandra-moon-in-vedic-astrology/", "Chandra (Moon) — most important for the child's naming"),
        ],
        "related_tools": [
            ("/kundli", "Compute the baby's Kundli", "Determine the birth nakshatra pada for the first-letter tradition"),
        ],
    },
    "vidyarambh": {
        "slug": "vidyarambh",
        "hero_title": "Vidyarambh Muhurat — Auspicious Education-Starting Dates",
        "hero_subtitle": "Guru's day + Guru's uncombust position + soft nakshatras.",
        "seo_title": "Vidyarambh Muhurat Finder — Aksharabhyasa / Study-Start Calculator",
        "seo_desc": "Free Vidyarambh (education-start) Muhurat finder: Thursday peak-day, Jupiter uncombust, soft nakshatras, Choghadiya windows. Aksharabhyasa timing.",
        "intro_paragraphs": [
            "Vidyarambh (starting education / Aksharabhyasa) is one of the classical samskaras — the child's first formal introduction to letters and learning. Jupiter (Guru) is the karaka of knowledge, so this muhurat centres on Jupiter: his day (Thursday) is peak, his uncombust visibility is required, and Vasant Panchami (Saraswati puja day) is the annual Abujha muhurat, a widely followed convention this finder lifts a cleared date for.",
            "Peak days: Thursday (Jupiter's day, +1 bonus in scoring), Wednesday (Mercury — intellect), Friday (Venus — arts). Soft nakshatras favoured. Chaturmas doesn't block Vidyarambh (education is ongoing), but Jupiter combustion does (karaka must be visible).",
        ],
        "rules_summary": [
            "Thursday peak-day (Guru's day + extra bonus)",
            "Jupiter (Guru) uncombust — learning karaka must be visible",
            "Favourable nakshatras (Ashwini, Rohini, Mrigashira, Ardra, Punarvasu, Pushya, Hasta, Chitra, Swati, Anuradha, Shravana, Dhanishta, Shatabhisha, Revati)",
            "Favourable tithi (2, 3, 5, 10, 11, 12)",
            "No Panchak",
            "No Dagdha yoga — widely followed convention this finder applies",
            "No eclipse days — widely followed convention this finder applies",
            "Basant Panchami (Vasant Panchami / Saraswati Puja) — Abujha Muhurat, lifts a date that has cleared the checks — widely followed convention this finder applies",
        ],
        "related_articles": [
            ("/learn/guru-jupiter-brihaspati-in-vedic-astrology/", "Guru (Jupiter) — the karaka of learning"),
            ("/learn/budha-mercury-in-vedic-astrology/", "Budha (Mercury) — intellect and communication"),
        ],
        "related_tools": [
            ("/kundli", "Free Janma Kundli", "Check personal Dasha before education milestones"),
        ],
    },
    "business": {
        "slug": "business",
        "hero_title": "Business Start Muhurat — Auspicious Venture Opening Dates",
        "hero_subtitle": "Budha's day + Budha's uncombust position + wealth-favourable tithi.",
        "seo_title": "Business Start Muhurat Finder — Shop Opening Date Calculator",
        "seo_desc": "Free business start Muhurat finder: Wednesday peak-day, Mercury uncombust, Kharmas exclusion, wealth-favourable tithis, Choghadiya opening windows.",
        "intro_paragraphs": [
            "Starting a business, opening a shop, or launching a venture is treated here like any shubh karya: the day must align with tithi, nakshatra and weekday, and clear this finder's no-eclipse convention. Mercury (Budha) is the karaka of commerce and communication, so his day (Wednesday) is peak and his uncombust visibility is required.",
            "Peak days: Wednesday (Mercury's day, +1 bonus), Thursday (Jupiter — wisdom in decisions), Friday (Venus — wealth), Sunday (Sun — authority) acceptable. Kharmas blocks new ventures here (Sun in Sagittarius or Pisces = periods of turning inward, not launching), and Abujha muhurats like Devuthani Ekadashi and Akshaya Tritiya lift a business date that has cleared those checks; both are widely followed conventions this finder applies, not rules from the books this site holds.",
        ],
        "rules_summary": [
            "Wednesday peak-day (Budha's day + extra bonus)",
            "Mercury (Budha) uncombust — commerce karaka must be visible",
            "Favourable nakshatra: Ashwini, Pushya, Uttara Phalguni, Hasta, Chitra, Anuradha, Uttara Ashadha, Shravana, Revati",
            "Favourable tithi (2, 3, 5, 7, 10, 11, 13)",
            "No Panchak",
            "No Kharmas (no new ventures during Sun in Sagittarius/Pisces) — widely followed convention this finder applies",
            "No Dagdha yoga — widely followed convention this finder applies",
            "No eclipse days — widely followed convention this finder applies",
            "Devuthani Ekadashi, Akshaya Tritiya, Basant Panchami lift a date that has cleared the checks — widely followed convention this finder applies",
        ],
        "related_articles": [
            ("/learn/budha-mercury-in-vedic-astrology/", "Budha (Mercury) — karaka of commerce"),
            ("/learn/dhana-yoga-wealth-combinations/", "Dhana Yogas — check for wealth combinations in your chart"),
        ],
        "related_tools": [
            ("/kundli", "Free Janma Kundli", "Check personal Dasha before major launches"),
            ("/numerology", "Numerology", "Auspicious name/date numerology for business branding"),
        ],
    },
}


EVENT_RULES: dict[str, dict[str, Any]] = {
    "vivah": {
        "label": "Vivah (Wedding)",
        # No Dwadashi (#1022): Rao's Table 79 Wedding row lists the 12th but Raman's marriage
        # chapter rejects it, so it is contested and gets no credit (and no exclusion) here.
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                         "Ekadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya", "Purnima"},
        # Krishna-paksha only (#1022): Raman's marriage chapter, as knowledge/vedic_reference.md
        # section 29.9 paraphrases it, rejects "the 11th of the dark half through New Moon"
        # and names the bright-half 11th and 13th among the best. Read by score_event via
        # .get(), so no other event has this key and none changes.
        "avoid_krishna_tithis": {"Ekadashi", "Dwadashi", "Trayodashi"},
        # First quarter only (#1232): Raman's marriage chapter lists Makha and Moola among the
        # best asterisms and then rejects their first quarter (knowledge/vedic_reference.md
        # section 29.14). Whole-nakshatra membership cannot say "pada 1", so the two stay in
        # good_nakshatras and score_event reads this via .get(), as it does the key above: no
        # other event has it and none changes. The third clause of the same sentence, the last
        # quarter of Revati, needs no entry: Revati is whole-nakshatra Panchak (_is_panchak).
        "avoid_nakshatra_padas": {"Magha": {1}, "Mula": {1}},
        "good_nakshatras": {"Rohini", "Mrigashira", "Magha", "Uttara Phalguni",
                             "Hasta", "Swati", "Anuradha", "Mula",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Jyeshtha", "Vishakha", "Purva Phalguni",
                              "Purva Ashadha", "Purva Bhadrapada"},
        # No Sunday (#1021): Raman's marriage chapter calls Sunday middling and Rao's
        # Table 79 Wedding row lists Mon, Wed, Thu, Fri; neither held source calls it good.
        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday"},
        "avoid_days": {"Tuesday", "Saturday"},
        "check_panchak": True,
        "check_chaturmas": True,
        "check_kharmas":   True,          # Dhanurmas + Meenmas (Sun in Sagittarius/Pisces)
        "check_dagdha":    True,          # burnt tithi-weekday pairings
        "check_jupiter_combust": True,
        "check_venus_combust":   True,
        "check_mercury_combust": False,
    },
    "griha_pravesh": {
        "label": "Griha Pravesh (Housewarming)",
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                         "Ekadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya", "Purnima"},
        # Nakshatras (#1061), knowledge/vedic_reference.md 29.13: Raman's house-entry chapter
        # names Rohini, Mrigasira, Uttara Phalguni, Uttarashadha, Chitta and Uttarabhadra as the
        # best and Anuradha and Revati as permissible; Rao's Table 79 row lists the same
        # and omits Hasta. Hasta was credited here with no support in either book, so it
        # is not credited now (it stays out of avoid_nakshatras: neither book names it as
        # a bad one for this event, it is simply not on their lists). Dhanishta and
        # Satabhisha are on Rao's row only, so they are contested and get no credit.
        "good_nakshatras": {"Rohini", "Mrigashira", "Uttara Phalguni",
                             "Chitra", "Anuradha",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula"},
        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday"},
        "avoid_days": {"Tuesday", "Saturday"},
        "check_panchak": True,
        "check_chaturmas": True,
        "check_kharmas":   True,
        "check_dagdha":    True,
        "check_jupiter_combust": True,
        "check_venus_combust":   False,
        "check_mercury_combust": False,
    },
    "namkaran": {
        "label": "Namkaran (Baby Naming)",
        # Raman's Namakarana names the 10th, 12th or 16th day after birth; no held book
        # names the 11th day or the Grihya Sutras (#1060, knowledge/vedic_reference.md
        # 29.13). The muhurat rules apply to whichever day is actually observed.
        #
        # Tithis (#1060): Rao's Table 79 "Naming a child" row is 2, 3, 5, 7, 10, 11, 13 and
        # omits the 12th. Raman's avoid list carries the 4th, 6th, 8th, 12th, 14th, Full
        # Moon and New Moon, so Dwadashi was credited here against both books, and Shashti
        # and Purnima were not avoided. Navami stays avoided: the figure is OCR-damaged in
        # Raman and Rao omits it (contested, unchanged).
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                         "Ekadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi",
                          "Chaturdashi", "Amavasya", "Purnima"},
        # Nakshatras (#1060): Raman's auspicious list and Rao's row both carry Dhanishta
        # and Satabhisha (Shatabhisha here), which were missing. Chitra is on Rao's row only
        # and stays credited. Magha stays in avoid_nakshatras: Raman lists Makha as
        # auspicious for naming and Rao's row omits it, so the two books disagree and this
        # finder keeps the harsh-star reading (contested, unchanged).
        "good_nakshatras": {"Ashwini", "Rohini", "Mrigashira", "Punarvasu",
                             "Pushya", "Hasta", "Chitra", "Swati",
                             "Anuradha", "Shravana", "Dhanishta", "Shatabhisha",
                             "Uttara Phalguni", "Uttara Ashadha",
                             "Uttara Bhadrapada", "Revati"},
        # Harsh (tikshna/krura) nakshatras avoided for infants.
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula", "Purva Bhadrapada"},
        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday"},
        "avoid_days": {"Tuesday", "Saturday"},
        "check_panchak": True,
        "check_chaturmas": False,   # Namkaran timing is child-driven, not liturgical
        "check_kharmas":   False,   # ditto — timed from the birth, not the liturgical year
        "check_dagdha":    False,   # child-driven timing overrides Dagdha
        # Combustion waived. UNSOURCED for Namkaran: knowledge/grahas.md 12.5 holds no
        # Namkaran line. It follows by analogy from Raman's Seemantha (p. 58) and
        # Annaprasana (p. 60) waivers ("such a circumstance may be ignored" / "one should
        # not mind"), the other child-timed samskaras he waives it for. (#219)
        "check_jupiter_combust": False,
        "check_venus_combust":   False,
        "check_mercury_combust": False,
    },
    "vidyarambh": {
        "label": "Vidyarambh (Starting Education)",
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Dashami",
                         "Ekadashi", "Dwadashi"},
        # Purnima (#1059): Raman's commencing-education chapter says "New and Full Moon
        # days should be avoided" (knowledge/vedic_reference.md 29.13); Amavasya was
        # already here, Purnima was not.
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya", "Purnima"},
        # Nakshatras (#1059): Ardra, Dhanishta and Satabhisha are on Raman's "most
        # beneficial for commencing education" list and in Rao's Table 79 "Teaching
        # alphabet" bracket. Ardra used to be AVOIDED here, which neither book supports.
        "good_nakshatras": {"Ashwini", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
                             "Pushya", "Hasta", "Chitra", "Swati",
                             "Anuradha", "Shravana", "Dhanishta", "Shatabhisha",
                             "Revati"},
        "avoid_nakshatras": {"Bharani", "Krittika", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula"},
        "good_days":  {"Wednesday", "Thursday", "Friday", "Monday"},
        "avoid_days": {"Tuesday", "Saturday", "Sunday"},
        # THIS FINDER'S CONVENTION, not a sourced rule (#1059, 29.13): Jupiter is karaka
        # of learning, so Guru's day gets the +1 peak bonus. Raman's one explicit best day
        # for commencing education is "Wednesday morning" (provided the chart is otherwise
        # well disposed); Thursday appears only inside a conditional Vidya Yoga, and Rao's
        # row lists Mon, Wed, Thu, Fri without ranking them.
        "peak_day":   "Thursday",
        "check_panchak": True,
        "check_chaturmas": False,
        "check_kharmas":   False,   # Vidyarambh is Guru-driven, not Sun-driven
        "check_dagdha":    True,
        "check_jupiter_combust": True,   # karaka must be visible
        "check_venus_combust":   False,
        "check_mercury_combust": False,
    },
    "business": {
        "label": "Business Start / Shop Opening",
        # Mercury is karaka of commerce; Wed/Thu/Fri best.
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                         "Ekadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya", "Purnima"},
        "good_nakshatras": {"Ashwini", "Pushya", "Uttara Phalguni", "Hasta",
                             "Chitra", "Anuradha", "Uttara Ashadha",
                             "Shravana", "Revati"},
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Jyeshtha", "Mula"},
        "good_days":  {"Wednesday", "Thursday", "Friday", "Sunday"},
        "avoid_days": {"Tuesday", "Saturday"},
        "peak_day":   "Wednesday",
        "check_panchak": True,
        "check_chaturmas": False,
        "check_kharmas":   True,   # Sun-in-Dhanu/Meen inauspicious for new ventures
        "check_dagdha":    True,
        "check_jupiter_combust": False,
        "check_venus_combust":   False,
        # OUR extension, not a sourced rule: this vetoes every weekday. Raman's only
        # Mercury-combustion line (Upanayana, p. 64) rejects Wednesday alone
        # (knowledge/grahas.md 12.5). The finder page says so. (#219)
        "check_mercury_combust": True,   # karaka must be visible
    },
}


def _abujha_for(d: date, event_type: str) -> str:
    """Return the Abujha Muhurat name if this date is one for this event, else ''.

    First match wins when two abujha days coincide, in `_ABUJHA_RULES` order.
    Degrades to "" rather than raising — see `_in_chaturmas` for why.
    """
    try:
        for name, event_types in _abujha_days(d.year).get(d, ()):
            if event_type in event_types:
                return name
        return ""
    except Exception:
        return ""


# What a row says about an Abujha date (#1346). The pass prefix is inserted by `score_event` when the
# day cleared every hard exclusion; the avoid suffix is appended by `find_candidates` when it did not.
# Both say it is a regional almanac custom, because no book this site holds names it (#1354: the old
# "universally auspicious" label beside that disclosure contradicted it).
_ABUJHA_PASS_REASON = ("Abujha date, {name}: a regional almanac custom this finder includes; "
                       "no book it holds names it")
_ABUJHA_AVOID_SUFFIX = ("{name} is listed as an Abujha date, a regional almanac custom; this finder "
                        "does not waive this exclusion for it.")


def _in_chaturmas(d: date) -> bool:
    """True if `d` falls in the Chaturmas restriction window (Devshayani ..
    Devuthani Ekadashi, end-exclusive — Devuthani itself ends the restriction).

    DEGRADES PERMISSIVELY, AND THAT IS DELIBERATE. This is called inside
    `find_candidates`' per-day `try:` (~muhurat.py:1218) whose `except
    Exception: continue` (~:1239) drops the ENTIRE day from the results. So an
    exception raised here would not surface as an error — it would silently
    delete every affected date from the user's muhurat list, which is both
    invisible and destructive. Returning False instead loses one restriction
    flag on a day that still gets scored and shown.

    Loudness belongs in `scripts/verify_muhurat_tables.py`, which asserts the
    window resolves for every year 2000-2100, not in a runtime fallback. There
    is deliberately NO fixed Jul 15 - Nov 15 fallback any more: it was wrong in
    every year and structurally could not express the ~147-day window of a year
    with an Adhik Maas inside Chaturmas.
    """
    try:
        w = _chaturmas_window(d.year)
        return w is not None and w[0] <= d < w[1]
    except Exception:
        return False


# ─── Kharmas / Malmas (Sun-in-inauspicious-rashi) ────────────────────
# Traditional weddings-restricted windows driven by the Sun's sidereal
# rashi (not lunar-month-driven like Chaturmas):
#   Dhanurmas / Kharmas — Sun in Sagittarius (~Dec 15 to ~Jan 14)
#   Meenmas / Malmas    — Sun in Pisces (~Mar 14 to ~Apr 14)
# During these two months, Sun's Guru-sanchara (transit through Jupiter's
# own sign) is considered a time of teachership/introspection — no shubh
# karya (weddings, housewarmings, new ventures). This is a hard classical
# rule in North Indian tradition; South Indian tradition observes it more
# loosely. We compute dynamically from Swiss Ephemeris (already used for
# transit snapshots) so it's correct for any year without hardcoded tables.
_KHARMAS_RASHIS = {
    "Sagittarius (Dhanu)": "Dhanurmas (Sun in Sagittarius) — Kharmas restriction",
    "Pisces (Meena)":      "Meenmas (Sun in Pisces) — Kharmas restriction",
}


def _kharmas_flag(chart: Chart, when: datetime) -> tuple[bool, str]:
    """Return (is_kharmas, reason) — True if Sun is in Sagittarius/Pisces sidereal."""
    snap = compute_transit_snapshot(chart, when)
    sun = next((p for p in snap.planets if p.name == "Sun"), None)
    if not sun:
        return False, ""
    reason = _KHARMAS_RASHIS.get(sun.rashi, "")
    return bool(reason), reason


# ─── Eclipse days (Grahana) — universal BLOCKER for all shubh karya ──
# Convention: eclipse day + 1 day before + 1 day after are all inauspicious. This
# ±1-day rule is a widely-followed convention and is UNSOURCED: knowledge/*.md holds
# no eclipse muhurta rule (the only eclipse lines are aspects.md:214, grahas.md:454,
# vedic_reference.md:1279, none of them a muhurta rule), so neither the margin nor
# "a penumbral or not-visible-in-India eclipse blocks too" is traced to a book.
# Applies to ALL event types (universal, not per-event).
#
# The DATES are computed from Swiss Ephemeris, not typed (#1018). The hand-typed table
# listed two 2028 lunar eclipses that do not exist (Feb 12, Aug 6 -- the real Jan 12
# and Jul 6 shifted a month, the #141/#146 signature), omitted four real ones, and
# was empty from 2029. Cross-checked against NASA GSFC, Lunar Eclipses 2021-2030 and
# Solar Eclipses 2021-2030 (eclipse.gsfc.nasa.gov). Inclusion set is unchanged: every
# GLOBAL eclipse of either kind and any type, whether or not India sees it.
# The date is the IST calendar date of the maximum, because every other date here is
# an Indian civil date; NASA lists UT, so 2027-02-21 04:42 IST is NASA's "Feb 20".
_IST_OFFSET_DAYS = 5.5 / 24


def _solar_eclipse_name(ret: int) -> str:
    # Order matters: swe sets CENTRAL/NONCENTRAL beside the type, and a hybrid is its own
    # flag, so test the type bits most-specific first.
    if ret & swe.ECL_ANNULAR_TOTAL:
        return "Hybrid Solar Eclipse"
    if ret & swe.ECL_TOTAL:
        return "Total Solar Eclipse"
    if ret & swe.ECL_ANNULAR:
        return "Annular Solar Eclipse"
    return "Partial Solar Eclipse"


def _lunar_eclipse_name(ret: int) -> str:
    if ret & swe.ECL_TOTAL:
        return "Total Lunar Eclipse"
    if ret & swe.ECL_PARTIAL:
        return "Partial Lunar Eclipse"
    return "Penumbral Lunar Eclipse"


@lru_cache(maxsize=64)
def _eclipses_in_year(year: int) -> tuple[tuple[date, str], ...]:
    """Every global solar and lunar eclipse whose maximum falls on IST calendar `year`.

    Computed once per year (memoised), so it covers any year and costs nothing after
    the first call. The search starts two days early and stops two days late because an
    eclipse maximum near a year boundary changes calendar year when UT becomes IST.
    """
    start = swe.julday(year, 1, 1, 0.0) - 2
    stop = swe.julday(year + 1, 1, 1, 0.0) + 2
    found: list[tuple[date, str]] = []
    for search, namer in ((swe.sol_eclipse_when_glob, _solar_eclipse_name),
                          (swe.lun_eclipse_when, _lunar_eclipse_name)):
        jd = start
        while True:
            ret, tret = search(jd)
            if tret[0] > stop:
                break
            y, m, dd, _ = swe.revjul(tret[0] + _IST_OFFSET_DAYS)
            if y == year:
                found.append((date(y, m, dd), namer(ret)))
            # Eclipses of one kind are at least ~29 days apart (lunar) or ~14 (solar).
            jd = tret[0] + 10
    return tuple(sorted(found))


def _eclipse_flag(d: date) -> tuple[bool, str]:
    """True if d is within 1 day of a computed eclipse. Applies to ALL events."""
    for year in (d.year, d.year - 1, d.year + 1):  # handles Jan/Dec boundary
        for edate, ename in _eclipses_in_year(year):
            gap = abs((d - edate).days)
            if gap == 0:
                return True, f"{ename} on this date — universal muhurat blocker"
            if gap == 1:
                which = "day before" if d < edate else "day after"
                return True, f"{ename} ({which}, {edate:%b %d}) — traditionally inauspicious"
    return False, ""


# ─── Dagdha ("burnt") tithi-weekday combinations ─────────────────────
# Source not held: UNSOURCED (vedic_reference.md 29.10: `dagdha` has 0 hits
# across the four books searched; the text it was credited to before #716 is
# not held). Rule as implemented: certain tithi+weekday pairings
# form Dagdha yoga — the day is "burnt" and unfit for shubh karya. Rule
# applies to Vivah, Griha Pravesh, Vidyarambh, Business. Not applied to
# Namkaran (child-driven timing overrides).
_DAGDHA_TITHI_BY_DAY: dict[str, str] = {
    "Sunday":    "Dwadashi",
    "Monday":    "Ekadashi",
    "Tuesday":   "Panchami",
    "Wednesday": "Tritiya",
    "Thursday":  "Shashti",
    "Friday":    "Ashtami",
    "Saturday":  "Navami",
}


# ─── Karana (11 of them) + Bhadra / Vishti detection ─────────────────
# Karana = half a tithi = 6° of Sun-Moon elongation. There are 60 karanas
# per lunar month cycling through 7 movable karanas (Bava, Balava, Kaulava,
# Taitila, Gara, Vanij, Vishti) followed by 4 fixed karanas at month-end
# (Shakuni, Chatushpad, Naga, Kimstughna). Vishti = "Bhadra" — universally
# inauspicious for shubh karya. Active roughly half of every day.
# The movable-karana tuple lived here until #148; the names now come from
# chart.py, which _karana_at() below delegates to. The note above stays
# because _bhadra_active_at() still depends on knowing that Vishti is Bhadra.


def _karana_at(chart: Chart, when: datetime) -> str:
    """Return the karana name at the given instant, delegating to chart.py.

    Had its own copy of the half-tithi maths until #148 — the same astrology
    chart.py already computed for /panchang, with no computation over both
    that would notice if they drifted. `chart` is unused now; kept in the
    signature because callers pass it positionally.
    """
    from astro_ai.chart import _karana_at as _chart_karana_at, julian_day_utc

    _idx, name, _sig = _chart_karana_at(julian_day_utc(when))
    return name


def _bhadra_active_at(chart: Chart, when: datetime) -> bool:
    """True if Bhadra (Vishti) karana is active at the given moment."""
    return _karana_at(chart, when) == "Vishti"


# A karana is 6 degrees of Sun-Moon elongation. The Moon gains 10-15 degrees a
# day on the Sun, so one karana lasts 9.4-14.2 hours and Vishti cannot begin and
# end between two samples 3 hours apart, nor can the gap between two Vishti
# spans. So a 3-hour grid sees every span and every edge lies in exactly one
# grid interval; the edge is then found by bisection (#1019). It used to be
# *reported* as the first sampled hour, up to 3 hours after Vishti began.
_BHADRA_GRID = timedelta(hours=3)
_BHADRA_EDGE_RESOLUTION = timedelta(seconds=1)


def _bhadra_edge(chart: Chart, before: datetime, after: datetime) -> datetime:
    """First instant in (before, after] at which Vishti's on/off state differs
    from its state at `before`. The two ends must differ and bracket one edge."""
    was_active = _bhadra_active_at(chart, before)
    while after - before > _BHADRA_EDGE_RESOLUTION:
        mid = before + (after - before) / 2
        if _bhadra_active_at(chart, mid) == was_active:
            before = mid
        else:
            after = mid
    return after


def _bhadra_spans_for_day(
    chart: Chart, day_start: datetime,
) -> tuple[datetime, datetime, list[tuple[datetime, datetime]]]:
    """(day_begin, day_end, spans): the local civil day containing `day_start`
    and every interval inside it in which Vishti is active, as UTC instants.

    A span that was already running at the day's first instant starts at
    `day_begin`; one still running at its last ends at `day_end`. The day is
    midnight to midnight in the datetime's own zone, stepped in UTC so a
    23- or 25-hour DST day is measured as it is.
    """
    zone = day_start.tzinfo
    day = day_start.date()
    begin = datetime.combine(day, time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min,
                           tzinfo=zone).astimezone(timezone.utc)
    points = [begin]
    while points[-1] + _BHADRA_GRID < end:
        points.append(points[-1] + _BHADRA_GRID)
    points.append(end)
    states = [_bhadra_active_at(chart, p) for p in points]

    spans: list[tuple[datetime, datetime]] = []
    opened = begin if states[0] else None
    for i in range(1, len(points)):
        if states[i] == states[i - 1]:
            continue
        edge = _bhadra_edge(chart, points[i - 1], points[i])
        if states[i]:
            opened = edge
        else:
            spans.append((opened, edge))
            opened = None
    if opened is not None:
        spans.append((opened, end))
    return begin, end, spans


def _bhadra_window_for_day(
    chart: Chart, day_start: datetime,
    daylight: tuple[datetime, datetime] | None = None,
    *, _spans=None,
) -> str:
    """Return a short string giving when Bhadra (Vishti) is active that day,
    to the minute, or "" when it is not active at any point of the day.

    The boundaries are the true karana boundaries (the function /panchang uses),
    rounded outward -- the start down and the end up to a whole minute -- so the
    stated window never omits a Vishti minute. A span that began the day before
    reads "until HH:MM" and one that runs past midnight reads "from HH:MM".
    `daylight` is (sunrise, sunset); when one span covers all of it the text
    says so, because the day then has no Bhadra-free daylight at all.
    """
    begin, end, spans = _spans if _spans is not None else _bhadra_spans_for_day(chart, day_start)
    if not spans:
        return ""
    zone = day_start.tzinfo
    parts: list[str] = []
    for s, e in spans:
        s_local = s.astimezone(zone)
        e_local = (e + timedelta(seconds=59, microseconds=999999)).astimezone(zone)
        e_local = e_local.replace(second=0, microsecond=0)
        from_prev, into_next = s == begin, e == end
        if from_prev and into_next:
            parts.append("Bhadra active all day")
        elif from_prev:
            parts.append(f"Bhadra active until {e_local:%H:%M}")
        elif into_next:
            parts.append(f"Bhadra active from {s_local.replace(second=0, microsecond=0):%H:%M}"
                         " (continues into the next day)")
        else:
            parts.append(f"Bhadra active {s_local.replace(second=0, microsecond=0):%H:%M}"
                         f"-{e_local:%H:%M}")
    text = " and ".join(parts)
    if daylight is not None:
        rise, sset = (t.astimezone(timezone.utc) for t in daylight)
        if any(s <= rise and e >= sset for s, e in spans):
            text += " (covers sunrise to sunset)"
    return f"{text} — avoid ceremonies in that window"


def _abhijit_overlaps(abhijit: tuple[datetime, datetime],
                      rahu_kaal: tuple[datetime, datetime],
                      bhadra_spans: list[tuple[datetime, datetime]],
                      zone) -> tuple[str, ...]:
    """Notes naming the minutes in which Abhijit lies inside Rahu Kaal or Bhadra (#1025).

    Rahu Kaal is a weekday-indexed eighth of daylight, so on every Wednesday and Friday
    half of Abhijit (a fifteenth, around noon) falls inside it; Vishti overlaps it on some
    other days. The row used to mark the same minutes both "✓ Abhijit" and "✗ Rahu Kaal".
    This states the overlap and picks no winner: knowledge/ holds no line ranking Abhijit
    against either, only Raman's rejection of Vishti. A sub-minute touch is not reported.
    """
    def _inside(window: tuple[datetime, datetime]) -> str:
        lo, hi = max(abhijit[0], window[0]), min(abhijit[1], window[1])
        if (hi - lo).total_seconds() < 60:
            return ""
        return f"{lo.astimezone(zone):%H:%M}-{hi.astimezone(zone):%H:%M}"

    notes: list[str] = []
    if span := _inside(rahu_kaal):
        notes.append(f"Abhijit and Rahu Kaal overlap {span}")
    for s, e in bhadra_spans:
        if span := _inside((s, e)):
            notes.append(f"Abhijit and Bhadra (Vishti) overlap {span}")
    return tuple(notes)


# ─── Choghadiya — 8 sub-day windows per weekday ──────────────────────
# Source not held: UNSOURCED (vedic_reference.md 29.10: `choghadiya` has 0 hits
# across the four books searched; the text it was credited to before #716 is
# not held). Day-Choghadiya sequence (sunrise-to-sunset ÷ 8) starts from
# a different divison per weekday. Real astrologers pick the auspicious
# Choghadiya window within a good day for the actual ceremony start.
_CHOGHADIYA_SEQUENCE: dict[str, tuple[str, ...]] = {
    "Sunday":    ("Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"),
    "Monday":    ("Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit"),
    "Tuesday":   ("Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"),
    "Wednesday": ("Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh"),
    "Thursday":  ("Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh"),
    "Friday":    ("Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal"),
    "Saturday":  ("Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal"),
}
_CHOGHADIYA_AUSPICIOUSNESS: dict[str, str] = {
    "Amrit": "best",   "Shubh": "good",  "Labh": "good",
    "Chal":  "neutral",
    "Rog":   "avoid",  "Kaal":  "avoid", "Udveg": "avoid",
}


def _choghadiya_windows(weekday: str, sunrise: datetime, sunset: datetime) -> list[dict]:
    """Return 8 day-Choghadiya windows for the date.

    Each entry: dict with name, start (HH:MM), end (HH:MM), auspiciousness.
    Divides sunrise-to-sunset into 8 equal windows and labels them per the
    classical weekday sequence.
    """
    sequence = _CHOGHADIYA_SEQUENCE.get(weekday, ())
    if not sequence:
        return []
    day_seconds = (sunset - sunrise).total_seconds()
    window_seconds = day_seconds / 8.0
    windows = []
    for i, name in enumerate(sequence):
        w_start = sunrise + timedelta(seconds=i * window_seconds)
        w_end = sunrise + timedelta(seconds=(i + 1) * window_seconds)
        windows.append({
            "name": name,
            "start": w_start.strftime("%H:%M"),
            "end":   w_end.strftime("%H:%M"),
            "auspiciousness": _CHOGHADIYA_AUSPICIOUSNESS.get(name, "neutral"),
        })
    return windows


# ─── Namkaran first-letter table (Nakshatra + Pada → syllable) ───────
# Classical 108-syllable naming table (27 nakshatras × 4 padas). The
# baby's Moon nakshatra pada at BIRTH determines auspicious first
# letters for the name. Real Namkaran astrologers consult this table.
# NOT taken from any held book (#1062). Raman's Muhurtha (1948), Appendix "Nama
# Nakshatra, Finding" (djvu L6969-7110, printed pp. 105-106) prints a 27 x 4 table
# in his own transliteration. Compared with this one: 18 of 27 rows agree after
# allowing for that spelling, Shravana differs (his Ju, Jay, Jo, Gha; the
# alternate below), Ardra pada 3 and Uttara Bhadrapada differ or are unreadable in
# the OCR, and six more cannot be settled from OCR alone. Those rows are left as
# they were: a printed Devanagari source or a second book must settle them, not
# the OCR. The texts it was credited to before #716 are not held, and the note
# that it was consolidated per Drik Panchang / Namkaran manuals is unverified.
# knowledge/vedic_reference.md 29.13 has the row-by-row comparison.
_NAMKARAN_LETTERS: dict[str, tuple[str, str, str, str]] = {
    "Ashwini":         ("Chu", "Che", "Cho", "La"),
    "Bharani":         ("Li",  "Lu",  "Le",  "Lo"),
    "Krittika":        ("A",   "I",   "U",   "E"),
    "Rohini":          ("O",   "Va",  "Vi",  "Vu"),
    "Mrigashira":      ("Ve",  "Vo",  "Ka",  "Ki"),
    "Ardra":           ("Ku",  "Gha", "Ang", "Chha"),
    "Punarvasu":       ("Ke",  "Ko",  "Ha",  "Hi"),
    "Pushya":          ("Hu",  "He",  "Ho",  "Da"),
    "Ashlesha":        ("Di",  "Du",  "De",  "Do"),
    "Magha":           ("Ma",  "Mi",  "Mu",  "Me"),
    "Purva Phalguni":  ("Mo",  "Ta",  "Ti",  "Tu"),
    "Uttara Phalguni": ("Te",  "To",  "Pa",  "Pi"),
    "Hasta":           ("Pu",  "Sha", "Na",  "Tha"),
    "Chitra":          ("Pe",  "Po",  "Ra",  "Ri"),
    "Swati":           ("Ru",  "Re",  "Ro",  "Ta"),
    "Vishakha":        ("Ti",  "Tu",  "Te",  "To"),
    "Anuradha":        ("Na",  "Ni",  "Nu",  "Ne"),
    "Jyeshtha":        ("No",  "Ya",  "Yi",  "Yu"),
    "Mula":            ("Ye",  "Yo",  "Bha", "Bhi"),
    "Purva Ashadha":   ("Bhu", "Dha", "Pha", "Dha"),
    "Uttara Ashadha":  ("Bhe", "Bho", "Ja",  "Ji"),
    "Shravana":        ("Khi", "Khu", "Khe", "Kho"),
    "Dhanishta":       ("Ga",  "Gi",  "Gu",  "Ge"),
    "Shatabhisha":     ("Go",  "Sa",  "Si",  "Su"),
    "Purva Bhadrapada":("Se",  "So",  "Da",  "Di"),
    "Uttara Bhadrapada":("Du", "Tha", "Jha", "Nya"),
    "Revati":          ("De",  "Do",  "Cha", "Chi"),
}


# Shravana is the one row where Raman's printed list is a different set of
# syllables, not a different spelling of ours (#1062). The finder keeps its own
# row as the primary and shows this one beside it. Raman prints "Ju, Jay, Jo, Gha";
# his "ay" is our "e" (his "Chay", "Day", "Tay" are our Che, De, Te), and he works
# the example "James" to Shravana pada 2 (L7096-7105).
_NAMKARAN_ALTERNATE_LETTERS: dict[str, tuple[str, str, str, str]] = {
    "Shravana": ("Ju", "Je", "Jo", "Gha"),
}


def _namkaran_alternate_letters(child_moon_nakshatra: str) -> tuple[str, ...]:
    """The second circulating pada set for a nakshatra, or () where the finder
    has only one."""
    return _NAMKARAN_ALTERNATE_LETTERS.get(child_moon_nakshatra, ())


def _namkaran_first_letters(child_moon_nakshatra: str, child_moon_pada: int) -> tuple[str, tuple[str, ...]]:
    """Return (recommended_letter, all_pada_letters_for_nakshatra) for a
    child's Moon nakshatra + pada. recommended_letter is the pada-specific
    syllable; all_pada_letters shows the full 4-pada set for context (some
    families choose from the whole nakshatra rather than pada-strict)."""
    letters = _NAMKARAN_LETTERS.get(child_moon_nakshatra)
    if not letters or child_moon_pada < 1 or child_moon_pada > 4:
        return "", ()
    return letters[child_moon_pada - 1], letters


def _child_moon_pada(chart: Chart) -> tuple[str, int]:
    """Return (nakshatra_name, pada 1-4) for the child's natal Moon."""
    moon = next((p for p in chart.planets if p.name == "Moon"), None)
    if not moon:
        return "", 0
    # Reads the field rather than recomputing it — see the note on
    # matching._moon_pada. The copy that used to live here also carried a
    # `min(pada, 4)` clamp, which capped the out-of-range value the buggy
    # arithmetic could produce instead of correcting it: the symptom was
    # hidden and the wrong pada still shipped for every 10-degree boundary.
    return moon.nakshatra, moon.pada


def _dagdha_flag(weekday: str, tithi: str) -> tuple[bool, str]:
    """True if this (weekday, tithi) forms a Dagdha yoga."""
    dagdha_tithi = _DAGDHA_TITHI_BY_DAY.get(weekday)
    if dagdha_tithi and dagdha_tithi == tithi:
        return True, f"Dagdha yoga ({weekday} + {tithi}) — day 'burnt', unfit for shubh karya"
    return False, ""


def _moon_nakshatra_for(chart: Chart, when: datetime) -> tuple[str, int]:
    """Return (nakshatra, pada 1-4) of the Moon at the given moment, or
    ("", 0) if the snapshot has no Moon. Pada is read from the field, not
    recomputed — see the note on matching._moon_pada."""
    snap = compute_transit_snapshot(chart, when)
    moon = next((p for p in snap.planets if p.name == "Moon"), None)
    return (moon.nakshatra, moon.pada) if moon else ("", 0)


def _transit_moon(chart: Chart, when: datetime):
    """Return the transit-day Moon planet object (has .rashi and .nakshatra)."""
    snap = compute_transit_snapshot(chart, when)
    return next((p for p in snap.planets if p.name == "Moon"), None)


def _tara_bala(user_moon_nakshatra: str, transit_nakshatra: str) -> tuple[int, str, str]:
    """Return (position, name, verdict) for the user's Tara Bala on this day.

    Position = (transit_index - user_index) mod 9 + 1. Names/verdicts from
    _TARA_BALA_NAMES (Janma, Sampat, Vipat, ...). Returns (0, '', '') if
    either nakshatra unknown.
    """
    try:
        u_idx = NAKSHATRAS.index(user_moon_nakshatra)
        t_idx = NAKSHATRAS.index(transit_nakshatra)
    except ValueError:
        return 0, "", ""
    position = ((t_idx - u_idx) % 9) + 1
    name, verdict = _TARA_BALA_NAMES.get(position, ("", ""))
    return position, name, verdict


def chandra_bala_by_rashi(transit_moon_rashi: str) -> dict[str, tuple[int, str]]:
    """{rashi slug: (house 1..12, verdict)} for all twelve, for the daily Rashifal.

    The Rashifal is keyed on the reader's janma rashi, which IS the natal Moon
    rashi `_chandra_bala` counts from -- so all twelve verdicts fall out of
    today's transit Moon alone, with nothing asked of the reader and no chart
    computed. Slugs are the lowercase English name ("aries"), matching what the
    email template already derives from a section title.

    This exists because the readings had no per-rashi field that changed from
    one day to the next: measured over 252 readings, the prose was 95% new words
    inside 100% identical scaffolding, so the email read as unchanged (#513).
    Chandra Bala varies on BOTH axes the prose failed on -- day to day, and
    across the twelve on one day -- and unlike a star rating it is computed from
    a fixed house list rather than invented (#514); that list matches
    knowledge/vedic_reference.md 2A, the Moon row, for both the strong and
    the weak houses (#715 closed the gap where 2, 5, 9 were "neutral"). House
    6 is strong HERE and weak on the muhurta surface (see `_CHANDRA_BALA_SETS`):
    this is a transit reading, not an election.

    Returns "" as the verdict for a rashi it cannot place, same as
    `_chandra_bala`; the caller renders nothing rather than guessing.
    """
    return {r.split(" (")[0].lower():
            _chandra_bala(r, transit_moon_rashi, surface="gochara")
            for r in RASHIS}


def _chandra_bala(user_moon_rashi: str, transit_moon_rashi: str, *,
                  surface: str) -> tuple[int, str]:
    """Return (house 1..12, verdict) for the user's Chandra Bala on this day.

    `surface` is "gochara" or "muhurta" and has no default: the two grade house
    6 differently, so a caller that forgets to say which question it is asking
    must fail (TypeError, or KeyError for an unknown name), not get one silently.
    """
    strong, _ = _CHANDRA_BALA_SETS[surface]
    try:
        u_idx = RASHIS.index(user_moon_rashi)
        t_idx = RASHIS.index(transit_moon_rashi)
    except ValueError:
        return 0, ""
    house = ((t_idx - u_idx) % 12) + 1
    # Two grades only: each surface's sets partition 1..12 (asserted at import).
    verdict = "strong" if house in strong else "weak"
    return house, verdict


def _personal_match_for(user_chart: Chart, when: datetime,
                         transit_nakshatra: str,
                         static_notes: tuple[str, ...]) -> PersonalMatch | None:
    """Compute Tara Bala + Chandra Bala + notes for one candidate day.

    `static_notes` are chart-level notes computed once (Sade Sati, Rahu/Ketu
    Mahadasha) — passed through per day rather than recomputed.
    """
    user_moon = next((p for p in user_chart.planets if p.name == "Moon"), None)
    if user_moon is None:
        return None
    transit_moon = _transit_moon(user_chart, when)
    if transit_moon is None:
        return None
    t_pos, t_name, t_verdict = _tara_bala(user_moon.nakshatra, transit_nakshatra)
    c_house, c_verdict = _chandra_bala(user_moon.rashi, transit_moon.rashi, surface="muhurta")
    return PersonalMatch(
        tara_bala=t_verdict, tara_bala_name=t_name, tara_position=t_pos,
        chandra_bala=c_verdict, chandra_house=c_house,
        notes=static_notes,
    )


def _partner_factors_for(chart: Chart, when: datetime,
                           transit_nakshatra: str, transit_moon,
                           manglik_status: str,
                           static_notes: tuple[str, ...]) -> PartnerFactors:
    """Compute one partner's factors for a Vivah candidate day.

    `static_notes` are the chart-level notes (Sade Sati, Rahu-Ketu Dasha)
    already computed once at start-of-search for this partner. Extract
    the flags out for structured storage on the PartnerFactors.
    """
    p_moon = next((p for p in chart.planets if p.name == "Moon"), None)
    if p_moon is None or transit_moon is None:
        return PartnerFactors("", "", "", manglik_status, "", "")
    _, t_name, t_verdict = _tara_bala(p_moon.nakshatra, transit_nakshatra)
    _, c_verdict = _chandra_bala(p_moon.rashi, transit_moon.rashi, surface="muhurta")
    # Extract Sade Sati and Dasha flags from static_notes (short labels).
    sade_sati_flag = ""
    dasha_flag = ""
    for n in static_notes:
        if "Sade Sati" in n or "Ashtama Shani" in n or "Kantaka Shani" in n:
            sade_sati_flag = n.split("—")[0].strip()
        elif "Mahadasha" in n or "Antardasha" in n:
            dasha_flag = n.split("—")[0].strip()
    return PartnerFactors(
        tara_bala=t_verdict, tara_bala_name=t_name,
        chandra_bala=c_verdict,
        manglik_status=manglik_status,
        sade_sati_flag=sade_sati_flag,
        dasha_flag=dasha_flag,
    )


def _couple_verdict(bride: PartnerFactors, groom: PartnerFactors) -> str:
    """Reduce both partners' factors to a single wedding-day verdict.

    A groom on his own Janma day is graded "avoid" for the Tara test; the bride on
    hers is not. Raman, Muhurtha (1948) puts the day ruled by the 1st star in the
    avoid list with the 3rd, 5th and 7th, names marriage among the events it is
    inauspicious for, and says "For a woman, Janma Nakshatra would be quite
    favourable for marriage" (knowledge/vedic_reference.md 2A-ter, #714). The
    "nuptials ... favourable without exception" sentence in the same passage is not
    used: the book contradicts itself on that word. `groom.tara_bala` itself stays
    "ok" (the single-user match and the per-partner chips are unchanged); only this
    verdict reads it as avoid.

    The "avoid only when BOTH avoid" rule below is unsourced, and that is a ruling, not
    an oversight (#885, chief, 2026-11-11, Option A): Raman's avoid-list names no person
    and his marriage chapter gives no combining rule, so neither "both" nor "either" is
    sourced. "Either" would move 39 of 81 position pairs from mixed to avoid on a reading no
    book states, so the grades stay and the finder discloses the convention. Overturned
    only by a passage in knowledge/*.md stating how the two partners' Taras combine.
    """
    g_tara = "avoid" if groom.tara_bala_name == _JANMA_TARA_NAME else groom.tara_bala
    b_tara_ok = bride.tara_bala in ("excellent", "good", "ok")
    g_tara_ok = g_tara in ("excellent", "good", "ok")
    b_chandra_ok = bride.chandra_bala == "strong"
    g_chandra_ok = groom.chandra_bala == "strong"

    both_tara_avoid = (bride.tara_bala == "avoid" and g_tara == "avoid")
    if both_tara_avoid:
        return "avoid"
    if (bride.tara_bala == "excellent" and g_tara == "excellent"
            and b_chandra_ok and g_chandra_ok):
        return "excellent-for-both"
    if b_tara_ok and g_tara_ok and b_chandra_ok and g_chandra_ok:
        return "good-for-both"
    return "mixed"


def _static_personal_notes(user_chart: Chart, start: date) -> tuple[str, ...]:
    """Chart-level cautions that apply to the whole search range.

    Computed once at start-of-search rather than per day since they change
    slowly (Sade Sati spans years; Mahadasha spans years too). If Sade Sati
    ends mid-range or Mahadasha changes mid-range, the note may slightly
    over-report — that's an acceptable trade for perf.
    """
    notes: list[str] = []
    anchor = datetime.combine(start, datetime.min.time().replace(hour=12),
                                tzinfo=ZoneInfo(user_chart.birth_tz))
    try:
        ss = compute_sade_sati_details(user_chart, anchor)
        if ss.is_active:
            phase_label = (ss.phase or "").capitalize()
            if ss.phase == "peak":
                notes.append(f"Sade Sati {phase_label} phase — cautious with major life events")
            else:
                notes.append(f"Sade Sati {phase_label} — soft caution around Saturn transits")
    except Exception:
        pass
    try:
        dasha = compute_dasha_state(user_chart, anchor)
        if dasha.mahadasha.lord in ("Rahu", "Ketu"):
            notes.append(f"{dasha.mahadasha.lord} Mahadasha active — some traditions advise deferring major muhurats")
        elif dasha.antardasha.lord in ("Rahu", "Ketu"):
            notes.append(f"{dasha.antardasha.lord} Antardasha within {dasha.mahadasha.lord} Mahadasha — mild caution")
    except Exception:
        pass
    return tuple(notes)


def _combustion_flags(chart: Chart, when: datetime) -> dict[str, bool]:
    """Return {'jupiter': bool, 'venus': bool, 'mercury': bool} at the moment."""
    snap = compute_transit_snapshot(chart, when)
    sun = next((p for p in snap.planets if p.name == "Sun"), None)
    jup = next((p for p in snap.planets if p.name == "Jupiter"), None)
    ven = next((p for p in snap.planets if p.name == "Venus"), None)
    mer = next((p for p in snap.planets if p.name == "Mercury"), None)
    if not sun:
        return {"jupiter": False, "venus": False, "mercury": False}

    from astro_ai.chart import _rashi_index as _ri
    sun_abs = _ri(sun.rashi) * 30.0 + sun.longitude

    def _sep(planet) -> float:
        if not planet:
            return 999.0
        p_abs = _ri(planet.rashi) * 30.0 + planet.longitude
        d = abs(sun_abs - p_abs) % 360.0
        return min(d, 360.0 - d)

    def _is_combust(planet) -> bool:
        if not planet:
            return False
        orb = combustion_orb(planet.name, getattr(planet, "retrograde", False))
        # `<`, matching chart.is_combust. Measure-zero on continuous
        # separations, but 39ae5bf's stated goal was ONE sourced answer per
        # planet and a differing predicate leaves two.
        return orb is not None and _sep(planet) < orb

    return {
        "jupiter": _is_combust(jup),
        "venus":   _is_combust(ven),
        "mercury": _is_combust(mer),
    }


# Tuesday is a HARD exclusion for every event (#1021). Raman, Muhurtha (1948),
# knowledge/vedic_reference.md section 29.9: line 790 "Tuesday and Saturday should be
# invariably avoided for all good and auspicious work"; the marriage chapter (lines
# 3734-3746) rejects Tuesday outright (the knowledge file's paraphrase, not a quote); Rao Table 79 (knowledge/grahas.md) lists
# Mon, Wed, Thu, Fri for a wedding. A one-point penalty let a good tithi + nakshatra
# still rate Tuesday 'acceptable', and a booster then lifted it to 'excellent'.
# Saturday is deliberately NOT here: Raman's Ch. II (avoid) and his marriage chapter
# (middling) disagree, so it stays a one-point penalty in `avoid_days`.
_HARD_AVOID_WEEKDAYS = frozenset({"Tuesday"})

# User-facing reason. The Amrit Siddhi sentence is a disclosure, not a rule: Raman's
# Amrita Siddha list pairs Tuesday with Ashwini and his text does not say whether that
# overrides line 790 (vedic_reference.md section 29.9), so this finder picks "no" and says so.
_HARD_AVOID_WEEKDAY_REASON = (
    "Tuesday is avoided for all auspicious work (Raman, Muhurtha: 'invariably avoided'; "
    "his marriage chapter rejects Tuesday outright for a wedding). Amrit Siddhi's Tuesday + Ashwini pairing does "
    "not override this in this finder; the source is silent on that case."
)
# Raman's one sourced exception (line 1331) is for the child's own days, which this
# finder cannot apply: it has no birth date. So it is disclosed, not computed.
_NAMKARAN_TUESDAY_EXCEPTION = (
    " Raman allows a Tuesday for the naming on the child's 10th, 12th or 16th day after "
    "birth; this finder has no birth date, so it cannot apply that exception."
)

# Vivah only (#1022). User-facing reason for a Krishna-paksha tithi in
# EVENT_RULES['vivah']['avoid_krishna_tithis']. It names Raman and the dark half and claims
# nothing about the other waning-half tithis: the knowledge file records Raman's marriage
# chapter as rejecting the dark-half 11th "through New Moon" and calling the bright-half
# 2nd, 3rd, 5th, 7th, 10th, 11th and 13th best, and it records nothing for the dark-half
# 2nd-10th, which keep the finder's own credit. Not worded as a quote: it is a paraphrase.
_VIVAH_KRISHNA_TITHI_REASON = (
    "Krishna-paksha (dark half, waning Moon) {tithi}: B.V. Raman's Muhurtha, marriage "
    "chapter, rejects the dark-half 11th through New Moon for a wedding. The bright-half "
    "{tithi} is not excluded."
)

# Vivah only (#1232). User-facing reason for a first-quarter Magha/Mula Moon, from
# EVENT_RULES['vivah']['avoid_nakshatra_padas']. The knowledge file records Raman's marriage
# chapter as calling Makha and Moola among the best asterisms and rejecting their first
# quarter, so the reason says both and claims nothing about the other three quarters.
_VIVAH_FIRST_PADA_REASON = (
    "Moon in the first quarter (pada 1) of {nakshatra}: B.V. Raman's Muhurtha, marriage "
    "chapter, rejects the first quarter of Makha and Moola for a wedding. The rest of "
    "{nakshatra} stays good."
)


def _soft_scoring(rules: dict, tithi_name: str, nakshatra: str,
                  weekday_name: str) -> tuple[int, list[str], list[str]]:
    """(points, reasons, flags) of the soft factors, in the order `score_event` has always shown
    them. One body for the points and the words, so a reason can never describe a score the
    ranking did not use (#1341)."""
    score = 0
    reasons: list[str] = []
    flags: list[str] = []
    if tithi_name in rules["good_tithis"]:
        score += 2
        reasons.append(f"good tithi ({tithi_name})")
    if nakshatra in rules["good_nakshatras"]:
        score += 2
        reasons.append(f"good nakshatra ({nakshatra})")
    if weekday_name in rules["good_days"]:
        score += 1
        reasons.append(f"good weekday ({weekday_name})")
        if rules.get("peak_day") == weekday_name:
            score += 1
            reasons.append("peak-day for this event")
    elif weekday_name in rules["avoid_days"]:
        score -= 1
        reasons.append(f"avoid weekday ({weekday_name})")
        flags.append("avoid_weekday")
    return score, reasons, flags


def _soft_points(rules: dict, tithi_name: str, nakshatra: str, weekday_name: str) -> int:
    """The soft-scoring points alone: what `find_candidates` stores as `MuhuratCandidate.score`."""
    return _soft_scoring(rules, tithi_name, nakshatra, weekday_name)[0]


def score_event(event_type: str, panchang, weekday_name: str, nakshatra: str,
                is_panchak: bool, is_chaturmas: bool,
                kharmas_reason: str, eclipse_reason: str,
                combust: dict[str, bool],
                adhik_reason: str = "",
                nitya_yoga: str = "", nitya_blocks: bool = False,
                boosters: tuple[str, ...] = (),
                moon_pada: int = 0,
                abujha_name: str = "") -> tuple[str, str, tuple[str, ...]]:
    """Return (rating, reason, flags) for the given event type.

    HARD exclusions (return 'avoid'), in priority order:
      1. Adhik Maas — universal blocker for all shubh karya
      2. Eclipse day / ±1 day — universal
      3. Panchak, Chaturmas, Kharmas, Dagdha (per-event flag)
      4. Atiganda / Shula / Ganda / Vyatipata / Vaidhriti Nitya Yogas — universal
      5. Combust karaka (per-event flag)
      6. Avoid-nakshatra, the pada-aware avoid_nakshatra_padas (Vivah, #1232; moon_pada 0
         = unknown, never rejects), avoid-tithi, and the paksha-aware avoid_krishna_tithis
         (Vivah, #1022)
      7. Tuesday (_HARD_AVOID_WEEKDAYS) — Raman, see the constant

    BOOSTERS lift the rating after the exclusions above (they never waive one):
      - Amrit Siddhi Yoga (nakshatra+weekday): always excellent
      - Sarvartha Siddhi Yoga (nakshatra+weekday), Ravi Yoga (Sun-based) and an Abujha date
        (`abujha_name`, #1346): caution → good, acceptable/good → excellent, never lower.
        They share ONE lift, so a day with two of them is lifted once.
    An Abujha day that fails an exclusion returns that exclusion's own verdict here, with no
    Abujha flag; the caller discloses the Abujha name on the avoid row (`_ABUJHA_AVOID_SUFFIX`).

    SOFT scoring: +2 favourable tithi, +2 favourable nakshatra, +1 favourable
    weekday. Peak-day (e.g. Thu for Vidyarambh) adds an extra +1. A Saturday
    subtracts 1 (it is the only avoid-weekday that reaches here: Tuesday is a hard
    exclusion above, Saturday is contested within Raman). Final rating: >=5 excellent, 4 good, 3 acceptable, else caution.
    """
    rules = EVENT_RULES.get(event_type)
    if rules is None:
        return "avoid", f"Unknown event type: {event_type}", ()

    flags: list[str] = []

    # ─── Hard exclusions (universal + per-event) ────────────────────
    # Adhik Maas is the top-priority universal blocker.
    if adhik_reason:
        flags.append("adhik_maas")
        return "avoid", adhik_reason, tuple(flags)
    # Eclipse is universal — no event override.
    if eclipse_reason:
        flags.append("eclipse")
        return "avoid", eclipse_reason, tuple(flags)
    # Atiganda / Shula / Ganda / Vyatipata / Vaidhriti nitya yogas — universal blockers.
    if nitya_blocks:
        flags.append("nitya_yoga_block")
        return "avoid", (f"{nitya_yoga} Nitya Yoga — Raman names it among the five yogas that harm "
                         "whatever is started under them"), tuple(flags)
    if rules["check_panchak"] and is_panchak:
        flags.append("panchak")
        return "avoid", f"Panchak day ({nakshatra}) — inauspicious", tuple(flags)
    if rules["check_chaturmas"] and is_chaturmas:
        flags.append("chaturmas")
        return "avoid", "Chaturmas period — traditionally restricted", tuple(flags)
    if rules.get("check_kharmas") and kharmas_reason:
        flags.append("kharmas")
        return "avoid", kharmas_reason, tuple(flags)
    if rules.get("check_dagdha"):
        dagdha_is, dagdha_reason = _dagdha_flag(weekday_name, panchang.tithi_name)
        if dagdha_is:
            flags.append("dagdha")
            return "avoid", dagdha_reason, tuple(flags)
    if rules["check_jupiter_combust"] and combust.get("jupiter"):
        flags.append("jupiter_combust")
        return "avoid", "Guru (Jupiter) is combust — marriage/learning karaka not visible", tuple(flags)
    if rules["check_venus_combust"] and combust.get("venus"):
        flags.append("venus_combust")
        return "avoid", "Shukra (Venus) is combust — marriage karaka not visible", tuple(flags)
    if rules["check_mercury_combust"] and combust.get("mercury"):
        flags.append("mercury_combust")
        return "avoid", "Budh (Mercury) is combust — commerce karaka not visible", tuple(flags)
    if nakshatra in rules["avoid_nakshatras"]:
        flags.append("avoid_nakshatra")
        return "avoid", f"Avoid nakshatra ({nakshatra})", tuple(flags)
    # Pada-aware nakshatra exclusion (#1232). Read with .get() so only the event that carries
    # the key is affected; an unknown pada (0) is in no set, so it never rejects.
    if moon_pada in rules.get("avoid_nakshatra_padas", {}).get(nakshatra, ()):
        flags.append("avoid_nakshatra_pada")
        return "avoid", _VIVAH_FIRST_PADA_REASON.format(nakshatra=nakshatra), tuple(flags)
    if panchang.tithi_name in rules["avoid_tithis"]:
        flags.append("avoid_tithi")
        return "avoid", f"Avoid tithi ({panchang.tithi_name})", tuple(flags)
    # Paksha-aware tithi exclusion (#1022). `avoid_tithis` is keyed on the NAME alone, so
    # it cannot say "dark half only". The event key is read with .get() and the paksha is
    # read only after the name matches, so every other event (no key) is unaffected.
    if (panchang.tithi_name in rules.get("avoid_krishna_tithis", ())
            and panchang.tithi_paksha == "Krishna"):
        flags.append("avoid_krishna_tithi")
        return "avoid", _VIVAH_KRISHNA_TITHI_REASON.format(tithi=panchang.tithi_name), tuple(flags)
    # Last of the hard exclusions, and still ahead of the boosters below: they only
    # lift soft scores, so an Amrit/Sarvartha Siddhi Tuesday cannot reach them.
    if weekday_name in _HARD_AVOID_WEEKDAYS:
        flags.append("avoid_weekday")
        reason = _HARD_AVOID_WEEKDAY_REASON
        if event_type == "namkaran":
            reason += _NAMKARAN_TUESDAY_EXCEPTION
        return "avoid", reason, tuple(flags)

    # ─── Soft scoring ───────────────────────────────────────────────
    score, reasons, soft_flags = _soft_scoring(
        rules, panchang.tithi_name, nakshatra, weekday_name)
    flags.extend(soft_flags)

    rating = next((r for r, floor in _RATING_MIN_SCORE.items() if score >= floor), "caution")

    # ─── Boosters lift the rating (caution → good, acceptable/good → excellent) ─
    # Amrit Siddhi, Sarvartha Siddhi, Ravi Yoga and an Abujha date lift the day regardless of
    # soft-score. They cannot override hard exclusions above, only lift the rating, and the
    # Abujha flag is set only here, after those exclusions, so it never sits on a row that failed one.
    if boosters or abujha_name:
        flags.extend(f.lower().replace(" ", "_") for f in ("Amrit Siddhi", "Sarvartha Siddhi", "Ravi Yoga") if any(b.startswith(f) for b in boosters))
        if abujha_name:
            flags.append("abujha_muhurat")
        booster_names = "; ".join(boosters)
        # Amrit Siddhi is the strongest — always lifts to excellent.
        # Sarvartha Siddhi / Ravi Yoga lift to excellent if not already above.
        if any(b.startswith("Amrit Siddhi") for b in boosters):
            rating = "excellent"
            reasons.insert(0, booster_names)
        elif rating in ("caution", "acceptable", "good"):
            # Lift only if not already excellent — don't downgrade.
            rating = "excellent" if rating != "caution" else "good"
            if booster_names:
                reasons.insert(0, booster_names)
        if abujha_name:
            reasons.insert(0, _ABUJHA_PASS_REASON.format(name=abujha_name))

    return rating, "; ".join(reasons) or "neutral factors", tuple(flags)


@dataclass(frozen=True)
class _MuhurtaInstant:
    """The tithi at the one instant a day is judged at; what `score_event` reads of its
    `panchang` argument (#1020)."""
    tithi_name: str
    tithi_paksha: str


# Every anga of a day's verdict is read at this local clock time. `find_candidates` judges a
# whole day, so it needs one representative instant, and the sourced constraint is only that it
# is the SAME for every anga (knowledge/vedic_reference.md 29.7, Rao: the nakshatra "at the time
# of a muhurta"; the angas of the muhurta are chosen together). Which instant is this
# finder's own choice; the page footnote says it.
MUHURTA_INSTANT_HOUR = 12


def find_candidates(event_type: str, city: str, start: date,
                    days: int = 90,
                    personal_chart: Chart | None = None,
                    bride_chart: Chart | None = None,
                    groom_chart: Chart | None = None) -> list[MuhuratCandidate]:
    """Return muhurat candidates for the given event in the next `days` days.

    Best-first sorted. Includes 'avoid' rows so users see which dates were
    rejected and why (transparency > filtering).

    If `personal_chart` is provided (user's natal Chart), each candidate is
    annotated with a PersonalMatch containing Tara Bala + Chandra Bala per
    day and chart-level notes (Sade Sati phase, Rahu/Ketu Mahadasha). The
    classical rating stays universal — personal factors surface separately
    so users see BOTH reads.

    For Vivah specifically: if both `bride_chart` and `groom_chart` are
    provided, each candidate is annotated with a CoupleMatch containing
    both partners' Tara/Chandra Bala + Manglik status + Sade Sati / Dasha
    cautions. Real astrologers ALWAYS check both partners' charts for
    wedding dates — this promotes the tool from single-perspective to
    couple-perspective for the top use-case.
    """
    if event_type not in EVENT_RULES:
        raise ValueError(f"Unknown event type: {event_type}")

    try:
        base_chart = compute_chart(start.isoformat(), "12:00", city)
    except ChartError as err:
        raise ValueError(f"Could not compute chart for {city!r}: {err}") from err

    candidates: list[MuhuratCandidate] = []
    days = max(1, min(days, 365))
    tz = ZoneInfo(base_chart.birth_tz)

    # Chart-level personal notes computed ONCE per search (Sade Sati + Dasha
    # move slowly; over-report of ~months is acceptable trade for perf).
    static_notes: tuple[str, ...] = ()
    if personal_chart is not None:
        static_notes = _static_personal_notes(personal_chart, start)

    # Couple mode — compute both partners' static notes + Manglik status
    # once per search. Only meaningful for Vivah.
    bride_notes: tuple[str, ...] = ()
    groom_notes: tuple[str, ...] = ()
    bride_manglik = ""
    groom_manglik = ""
    couple_mode = (event_type == "vivah"
                    and bride_chart is not None and groom_chart is not None)
    if couple_mode:
        bride_notes = _static_personal_notes(bride_chart, start)
        groom_notes = _static_personal_notes(groom_chart, start)
        try:
            from astro_ai.chart import compute_manglik_details
            bride_manglik = compute_manglik_details(bride_chart).effective_status
            groom_manglik = compute_manglik_details(groom_chart).effective_status
        except Exception:
            pass

    for i in range(days):
        d = start + timedelta(days=i)
        try:
            when = datetime.combine(
                d, datetime.min.time().replace(hour=MUHURTA_INSTANT_HOUR), tzinfo=tz)
            p = compute_panchang(base_chart, when)
            # Tithi at the SAME instant as nakshatra, yoga and combustion below, not
            # compute_panchang's sunrise tithi: one verdict judged a sunrise tithi beside a
            # noon nakshatra on days where the two never coexist (#1020).
            _t_idx, t_name, t_paksha, _t_sig = _tithi_at(julian_day_utc(when))
            at_instant = _MuhurtaInstant(t_name, t_paksha)
            nakshatra, moon_pada = _moon_nakshatra_for(base_chart, when)
            is_panchak = _is_panchak(nakshatra, moon_pada)
            is_chaturmas = _in_chaturmas(d)
            _kharmas_is, kharmas_reason = _kharmas_flag(base_chart, when)
            _eclipse_is, eclipse_reason = _eclipse_flag(d)
            _adhik_is, adhik_reason = _adhik_maas_flag(d)
            nitya_yoga, nitya_blocks = _nitya_yoga_flag(base_chart, when)
            combust = _combustion_flags(base_chart, when)
            # Boosters — universal-auspicious combinations
            boosters_list: list[str] = []
            if amrit := _amrit_siddhi_flag(p.weekday, nakshatra):
                boosters_list.append(amrit)
            if sarv := _sarvartha_siddhi_flag(p.weekday, nakshatra):
                boosters_list.append(sarv)
            if ravi := _ravi_yoga_flag(p.weekday, nakshatra):
                boosters_list.append(ravi)
            boosters = tuple(boosters_list)
            # Sub-day windows for planning — format as "HH:MM-HH:MM".
            #
            # All three are fractions of the sunrise-to-sunset period: Rahu
            # Kaal a weekday-indexed eighth of it and Abhijit a fifteenth
            # (`knowledge/vedic_reference.md` §28), Choghadiya the same span
            # cut into eight. `p.daylight_ordinary` is False on a date that
            # holds no such period (chart.py, #227) and the arithmetic is then
            # meaningless — Tromso 2026-05-17 produced rahu_kaal '00:14-00:06',
            # abhijit '00:42-00:37' and a choghadiya counting DOWNWARDS from
            # 01:14 to 00:06. The subtler shape is worse because it looks
            # right: Reykjavik 2026-06-21 gave abhijit '12:47-14:11' — 84
            # minutes, a fifteenth of a 21-hour span, rendered in a column
            # whose own footnote calls Abhijit "the best 48-minute window".
            # Reykjavik is south of the Arctic Circle and has 15 such dates in
            # 2026, none of which raises.
            #
            # Left EMPTY rather than dropped from the search: the date is still
            # a real candidate and its rating still holds — tithi, nakshatra
            # and yoga come from Sun and Moon longitudes, not from the length
            # of the day. Only the sub-day windows go. "" and () are the
            # dataclass's own defaults and `muhurat_finder.html` says so on the
            # row. #228.
            if p.daylight_ordinary:
                rk_str = f"{p.rahu_kaal_start.strftime('%H:%M')}-{p.rahu_kaal_end.strftime('%H:%M')}"
                ab_str = f"{p.abhijit_start.strftime('%H:%M')}-{p.abhijit_end.strftime('%H:%M')}"
                sunrise_str = p.sunrise.strftime('%H:%M')
            else:
                rk_str = ab_str = sunrise_str = ""
            # Phase B — Bhadra / Vishti karana window + Choghadiya table
            bhadra_spans = _bhadra_spans_for_day(base_chart, when)
            bhadra_window = _bhadra_window_for_day(
                base_chart, when,
                (p.sunrise, p.sunset) if p.daylight_ordinary else None,
                _spans=bhadra_spans,
            )
            abhijit_overlaps = (
                _abhijit_overlaps((p.abhijit_start, p.abhijit_end),
                                  (p.rahu_kaal_start, p.rahu_kaal_end),
                                  bhadra_spans[2], tz)
                if p.daylight_ordinary else ()
            )
            choghadiya = (
                tuple(_choghadiya_windows(p.weekday, p.sunrise, p.sunset))
                if p.daylight_ordinary else ()
            )
        except Exception:
            continue

        personal: PersonalMatch | None = None
        if personal_chart is not None:
            personal = _personal_match_for(personal_chart, when, nakshatra, static_notes)

        # Couple mode — compute both partners' factors for this day.
        couple: CoupleMatch | None = None
        if couple_mode:
            _tm = _transit_moon(bride_chart, when)  # same transit for both — use either chart
            bride_f = _partner_factors_for(bride_chart, when, nakshatra, _tm,
                                             bride_manglik, bride_notes)
            groom_f = _partner_factors_for(groom_chart, when, nakshatra, _tm,
                                             groom_manglik, groom_notes)
            couple = CoupleMatch(
                bride=bride_f, groom=groom_f,
                combined_verdict=_couple_verdict(bride_f, groom_f),
            )

        # An Abujha day is scored like any other: a booster inside score_event, after the hard
        # exclusions (#1346), never a branch that skips them.
        abujha_name = _abujha_for(d, event_type)

        rating, reason, flags = score_event(
            event_type, at_instant, p.weekday, nakshatra,
            is_panchak, is_chaturmas, kharmas_reason, eclipse_reason, combust,
            adhik_reason=adhik_reason,
            nitya_yoga=nitya_yoga, nitya_blocks=nitya_blocks,
            boosters=boosters, moon_pada=moon_pada,
            abujha_name=abujha_name,
        )
        if abujha_name and rating == "avoid":
            # The day is on the almanac list but failed a sourced exclusion: say so beside the
            # exclusion's own reason. Several reasons end in a full stop and the Panchak one does not.
            reason = reason.rstrip(" .") + ". " + _ABUJHA_AVOID_SUFFIX.format(name=abujha_name)
        # The soft points behind the rating. A lifted day (booster) never scores below its tier's
        # floor; an avoid day scores 0 (an unknown event has no rules to read either).
        score = 0 if rating == "avoid" else max(
            _soft_points(EVENT_RULES[event_type], t_name, nakshatra, p.weekday),
            _RATING_MIN_SCORE.get(rating, 0))
        candidates.append(MuhuratCandidate(
            d=d, weekday=p.weekday,
            tithi=t_name, tithi_paksha=t_paksha,
            nakshatra=nakshatra,
            rating=rating, reason=reason, flags=flags, score=score,
            personal=personal, couple=couple,
            rahu_kaal=rk_str, abhijit_muhurta=ab_str, sunrise=sunrise_str,
            nitya_yoga=nitya_yoga, boosters=boosters,
            bhadra_window=bhadra_window, choghadiya=choghadiya,
            abhijit_overlaps=abhijit_overlaps,
        ))

    candidates.sort(key=rank_key)
    return candidates


# ─── Backward-compat shim ────────────────────────────────────────────
def find_vivah_candidates(city: str, start: date, days: int = 90) -> list[MuhuratCandidate]:
    """Backward-compat wrapper — pre-refactor callers used this name."""
    return find_candidates("vivah", city, start, days)
