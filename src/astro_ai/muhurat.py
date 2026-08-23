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

Abujha Muhurats (Tulsi Vivah, Basant Panchami, Akshaya Tritiya etc.) override
normal scoring — these classical "self-perfected" days need no calculation.

Sources: Brihat Parashara Hora Shastra, Muhurtha Chintamani, Phaladeepika.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from astro_ai import lunar_dates
from astro_ai.adhik_maas import adhik_maas_flag
from astro_ai.chart import (
    combustion_orb,
    Chart, compute_chart, compute_panchang, compute_transit_snapshot,
    compute_sade_sati_details, compute_dasha_state,
    ChartError, NAKSHATRAS, RASHIS,
)


# ─── Panchak nakshatras (avoided for most ceremonies) ────────────────
# Classical: Moon transiting Dhanishta (latter half), Shatabhisha, Purva
# Bhadrapada, Uttara Bhadrapada, Revati is "Panchak" — the 5 nakshatra
# window traditionally avoided for weddings, house entry, funeral rites.
_PANCHAK_NAKSHATRAS = {"Dhanishta", "Shatabhisha", "Purva Bhadrapada",
                         "Uttara Bhadrapada", "Revati"}

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
# transit day's nakshatra (mod 9 + 1). BPHS assigns each of the 9
# positions a name + verdict.
_TARA_BALA_NAMES = {
    1: ("Janma",     "ok"),        # own birth star — variable (traditionally cautious)
    2: ("Sampat",    "good"),      # wealth
    3: ("Vipat",     "avoid"),     # calamity
    4: ("Kshema",    "good"),      # welfare
    5: ("Pratyari",  "avoid"),     # obstacle
    6: ("Sadhaka",   "good"),      # achievement
    7: ("Vadha",     "avoid"),     # destruction
    8: ("Mitra",     "good"),      # friend
    9: ("Ati-Mitra", "excellent"), # best friend
}

# Chandra Bala (Moon strength): count from user's natal Moon rashi to
# transit-day Moon rashi (1..12). BPHS marks certain houses as good/bad.
_CHANDRA_BALA_STRONG = {1, 3, 6, 7, 10, 11}
_CHANDRA_BALA_WEAK   = {4, 8, 12}


@dataclass(frozen=True)
class PartnerFactors:
    """One partner's per-day factors — used inside CoupleMatch for Vivah.

    Extracted subset of PersonalMatch that avoids the chart-level notes
    duplication (those go in CoupleMatch.notes as merged bride+groom).
    """
    tara_bala: str          # "excellent" | "good" | "ok" | "avoid"
    tara_bala_name: str
    chandra_bala: str       # "strong" | "neutral" | "weak"
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
    chandra_bala: str       # "strong" | "neutral" | "weak"
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
    rahu_kaal: str = ""       # "13:30–15:00"
    abhijit_muhurta: str = "" # "11:48–12:36"
    nitya_yoga: str = ""      # e.g. "Siddhi", "Vyatipata"
    boosters: tuple[str, ...] = ()  # Amrit Siddhi / Sarvartha Siddhi / Ravi Yoga names
    # Phase B additions — sub-day precision
    bhadra_window: str = ""   # "" if Bhadra not present; else "Bhadra active 09:00-16:00..."
    choghadiya: tuple[dict, ...] = ()   # 8 day-windows with name/start/end/auspiciousness


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
# Classical "swayam-siddha" / "abujha" days — universally auspicious without
# reference to the day's Panchang, so they override normal scoring.
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
# Classical nakshatra+weekday pairings that make a day auto-excellent
# regardless of other factors (comparable to Abujha muhurats but rule-based
# rather than fixed-date). Per Muhurta Chintamani. When active, boosts
# rating to "excellent" with a specific reason.
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
# Broader nakshatra+weekday set. Per Muhurta Chintamani. Slightly less
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
# When Sun's nakshatra + Moon's nakshatra combine in specific ways per
# Muhurta Chintamani, Ravi Yoga is formed. Simplified rule: Sunday +
# nakshatras with Sun-lordship (Krittika, Uttara Phalguni, Uttara Ashadha)
# or Sun-friendly nakshatras. Boost only, doesn't override hard exclusions.
_RAVI_YOGA_NAKSHATRAS = {"Krittika", "Uttara Phalguni", "Uttara Ashadha",
                          "Hasta", "Ashwini", "Pushya"}


def _ravi_yoga_flag(weekday: str, nakshatra: str) -> str:
    """Return 'Ravi Yoga' if active, else empty. Only on Sunday."""
    if weekday == "Sunday" and nakshatra in _RAVI_YOGA_NAKSHATRAS:
        return "Ravi Yoga (Sun-based auspicious combination)"
    return ""


# ─── Vaidhriti + Vyatipata Nitya Yogas — universal BLOCKERS ──────────
# Two of the 27 nitya yogas are classical hard-exclusions for shubh karya.
# Nitya yoga is computed as (Sun_longitude + Moon_longitude) / 13.333°.
# Positions:
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
# The blocking set is safe to key on names because "Vyatipata" and "Vaidhriti"
# were spelled identically in both copies — the divergence was elsewhere in
# the tuple.
_BLOCKING_NITYA_YOGAS = {"Vyatipata", "Vaidhriti"}


def _nitya_yoga_flag(chart: Chart, when: datetime) -> tuple[str, bool]:
    """Return (yoga_name, is_blocking), delegating the maths to chart.py.

    Reads the same `_nitya_yoga_at` that /panchang renders, so the Muhurat
    Finder's blocker path and the almanac can no longer disagree about the
    same instant (#148). `chart` is unused now that the computation needs
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
        "hero_subtitle": "Classical Panchang rules + your chart, not calendar guesswork.",
        "seo_title": "Vivah Muhurat Finder — Wedding Dates with Bride+Groom Pair Scoring",
        "seo_desc": "Free Vivah Muhurat finder: tithi, nakshatra, Panchak, Chaturmas, Kharmas, Dagdha, Adhik Maas, Bhadra Karana, Nitya Yogas (Vaidhriti/Vyatipata avoided), Amrit Siddhi / Sarvartha Siddhi / Ravi Yoga boosters, plus Guru+Shukra combustion checks. Bride+groom two-chart scoring (Tara Bala + Chandra Bala + Manglik + Sade Sati per partner).",
        "intro_paragraphs": [
            "A Vivah Muhurat is not merely an 'auspicious day' from a calendar. Classical tradition applies six specific criteria that must all align: Guru (Jupiter) and Shukra (Venus) visible above the horizon and uncombust, favourable tithi and nakshatra, no Panchak, no Chaturmas (Devshayani → Devuthani Ekadashi), no Kharmas (Sun in Sagittarius or Pisces), and no eclipse days. This tool checks all of these plus Dagdha tithi-weekday combinations and calls out Abujha muhurats (Tulsi Vivah, Basant Panchami, Akshaya Tritiya) that override normal scoring.",
            "For a fully personalised recommendation, sign in first — the tool will then overlay Tara Bala (star strength between your natal Moon nakshatra and the transit day) and Chandra Bala (Moon-strength from your natal Moon) on every candidate, plus surface chart-level cautions from Sade Sati phase or active Rahu/Ketu Mahadasha.",
        ],
        "rules_summary": [
            "Guru (Jupiter) uncombust — marriage karaka must be visible",
            "Shukra (Venus) uncombust — marriage karaka must be visible",
            "Favourable tithi: 2, 3, 5, 7, 10, 11, 12, 13 (avoid 4, 8, 9, 14, Amavasya, Purnima)",
            "Favourable nakshatra: Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Mula, Uttara Ashadha, Uttara Bhadrapada, Revati",
            "No Panchak (Moon in Dhanishta latter half through Revati)",
            "No Chaturmas (Devshayani → Devuthani Ekadashi ≈ mid-July to mid-November)",
            "No Kharmas (Sun in Sagittarius ≈ mid-Dec to mid-Jan; Sun in Pisces ≈ mid-Mar to mid-Apr)",
            "No Dagdha yoga (Sun+Dwadashi, Mon+Ekadashi, Tue+Panchami, Wed+Tritiya, Thu+Shashti, Fri+Ashtami, Sat+Navami)",
            "No eclipse days (day of or ±1 day)",
        ],
        "related_articles": [
            ("/learn/vivah-muhurat-2027/", "Vivah Muhurat 2027 — full classical guide"),
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
        "hero_subtitle": "Classical seven criteria + your chart, not developer-handover convenience.",
        "seo_title": "Griha Pravesh Muhurat Finder — Housewarming Date Calculator",
        "seo_desc": "Free Griha Pravesh Muhurat finder: Jupiter visibility, tithi, nakshatra, Panchak, Chaturmas, Kharmas, Dagdha, Adhik Maas, Bhadra Karana avoidance, plus Choghadiya sub-day windows and Amrit Siddhi / Sarvartha Siddhi boosters. Covers Apoorva / Sapoorva / Dwandwa entry types.",
        "intro_paragraphs": [
            "Griha Pravesh (house-warming) is the ceremony marking entry into a new home. Classical tradition names three types: Apoorva (brand-new home), Sapoorva (re-entry after long absence or renovation), and Dwandwa (entry into a home you own but haven't lived in). Each still requires the same classical timing rules.",
            "The seven classical criteria: Guru (Jupiter) uncombust and visible; favourable moon nakshatra; favourable tithi; no Chaturmas; no eclipse; no Panchak; weekday preference (Monday/Wednesday/Thursday/Friday best, Tuesday/Saturday avoided). This tool applies all of these plus Kharmas (Sun in Sagittarius/Pisces) and Dagdha tithi-weekday exclusions.",
        ],
        "rules_summary": [
            "Guru (Jupiter) uncombust — must be visible during ceremony hours",
            "Favourable nakshatra: Rohini, Mrigashira, Uttara Phalguni, Hasta, Chitra, Anuradha, Uttara Ashadha, Revati",
            "Favourable tithi: 2, 3, 5, 7, 10, 11, 13",
            "Weekday: Mon, Wed, Thu, Fri preferred; Tue, Sat avoided",
            "No Chaturmas (mid-July to mid-November)",
            "No Kharmas (Sun in Sagittarius/Pisces)",
            "No Panchak days",
            "No Dagdha yoga combinations",
            "No eclipse days",
        ],
        "related_articles": [
            ("/learn/griha-pravesh-muhurat-2026-2027/", "Griha Pravesh Muhurat 2026-27 — full guide"),
            ("/learn/vivah-muhurat-2027/", "Vivah Muhurat 2027 — sister classical guide"),
        ],
        "related_tools": [
            ("/kundli", "Free Janma Kundli", "Check personal factors for the chosen date"),
            ("/sade-sati-check", "Sade Sati Check", "Verify Saturn transit before major life events"),
        ],
    },
    "namkaran": {
        "slug": "namkaran",
        "hero_title": "Namkaran Muhurat — Auspicious Baby Naming Ceremony Dates",
        "hero_subtitle": "Traditional 11th-day timing + soft nakshatra selection for a newborn.",
        "seo_title": "Namkaran Muhurat + Baby First-Letter Nakshatra Table Calculator",
        "seo_desc": "Free Namkaran Muhurat finder with the classical 108-syllable first-letter table (27 nakshatras × 4 padas) — enter baby's birth details and get the traditional Sanskrit starting-letters for the name, plus soft-nakshatra day picks, favourable tithi, Bhadra avoidance, Choghadiya sub-day windows, and no-Panchak checks per Grihya Sutras.",
        "intro_paragraphs": [
            "Namkaran (naming ceremony) is classically observed on the 11th day after birth per Grihya Sutras, though modern families choose within the first 3-4 weeks. The muhurat rules apply to whichever day is chosen. Because this is a child-driven ceremony, some rules that apply to adult-planned events (Chaturmas, Kharmas, Dagdha, Guru combustion) do NOT block Namkaran — the ceremony must happen close to the birth regardless.",
            "What we do check: soft/friendly nakshatras (Ashwini, Rohini, Mrigashira, Punarvasu, Pushya, Hasta, Chitra, Swati, Anuradha, Shravana, Revati), favourable tithi, weekday preference (Mon/Wed/Thu/Fri best), no Panchak, no eclipse. Harsh nakshatras (Bharani, Krittika, Ardra, Ashlesha, Magha, Jyeshtha, Mula) are avoided for infants.",
        ],
        "rules_summary": [
            "Soft/friendly nakshatra required (mridu, laghu, dhruva, chara classifications)",
            "Favourable tithi (2, 3, 5, 7, 10, 11, 12, 13)",
            "Weekday: Mon, Wed, Thu, Fri preferred; Tue, Sat avoided",
            "No Panchak",
            "No eclipse days",
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
        "seo_desc": "Free Vidyarambh (education-start) Muhurat finder: Thursday peak-day, Jupiter uncombust, soft nakshatras, Choghadiya sub-day windows, Amrit Siddhi / Sarvartha Siddhi boosters, Basant Panchami / Saraswati Puja Abujha auto-favourable. Classical Aksharabhyasa timing rules.",
        "intro_paragraphs": [
            "Vidyarambh (starting education / Aksharabhyasa) is one of the classical samskaras — the child's first formal introduction to letters and learning. Jupiter (Guru) is the karaka of knowledge, so this muhurat centres on Jupiter: his day (Thursday) is peak, his uncombust visibility is required, and Vasant Panchami (Saraswati puja day) is the annual universal Abujha muhurat.",
            "Peak days: Thursday (Jupiter's day, +1 bonus in scoring), Wednesday (Mercury — intellect), Friday (Venus — arts). Soft nakshatras favoured. Chaturmas doesn't block Vidyarambh (education is ongoing), but Jupiter combustion does (karaka must be visible).",
        ],
        "rules_summary": [
            "Thursday peak-day (Guru's day + extra bonus)",
            "Jupiter (Guru) uncombust — learning karaka must be visible",
            "Soft nakshatras (Ashwini, Rohini, Mrigashira, Punarvasu, Pushya, Hasta, Chitra, Swati, Anuradha, Shravana, Revati)",
            "Favourable tithi (2, 3, 5, 10, 11, 12)",
            "No Panchak",
            "No Dagdha yoga",
            "No eclipse days",
            "Basant Panchami (Vasant Panchami / Saraswati Puja) auto-excellent — Abujha Muhurat",
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
        "seo_desc": "Free business start Muhurat finder: Wednesday peak-day, Mercury uncombust, Kharmas exclusion, wealth-favourable tithis, Choghadiya sub-day opening windows (Labh, Amrit, Shubh), Bhadra Karana avoidance, plus Amrit Siddhi and Sarvartha Siddhi boosters. Ideal for shop openings, new ventures, and product launches.",
        "intro_paragraphs": [
            "Starting a business, opening a shop, or launching a venture is classically treated similarly to any shubh karya — the day must align with tithi, nakshatra, weekday, and no-eclipse rules. Mercury (Budha) is the karaka of commerce and communication, so his day (Wednesday) is peak and his uncombust visibility is required.",
            "Peak days: Wednesday (Mercury's day, +1 bonus), Thursday (Jupiter — wisdom in decisions), Friday (Venus — wealth), Sunday (Sun — authority) acceptable. Kharmas blocks new ventures (Sun in Sagittarius or Pisces = periods of turning inward, not launching). Abujha muhurats like Devuthani Ekadashi and Akshaya Tritiya are auto-excellent for business.",
        ],
        "rules_summary": [
            "Wednesday peak-day (Budha's day + extra bonus)",
            "Mercury (Budha) uncombust — commerce karaka must be visible",
            "Favourable nakshatra: Ashwini, Pushya, Uttara Phalguni, Hasta, Chitra, Anuradha, Uttara Ashadha, Shravana, Revati",
            "Favourable tithi (2, 3, 5, 7, 10, 11, 13)",
            "No Panchak",
            "No Kharmas (no new ventures during Sun in Sagittarius/Pisces)",
            "No Dagdha yoga",
            "No eclipse days",
            "Devuthani Ekadashi, Akshaya Tritiya, Basant Panchami auto-excellent",
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
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                         "Ekadashi", "Dwadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya", "Purnima"},
        "good_nakshatras": {"Rohini", "Mrigashira", "Magha", "Uttara Phalguni",
                             "Hasta", "Swati", "Anuradha", "Mula",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Jyeshtha", "Vishakha", "Purva Phalguni",
                              "Purva Ashadha", "Purva Bhadrapada"},
        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday", "Sunday"},
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
        "good_nakshatras": {"Rohini", "Mrigashira", "Uttara Phalguni",
                             "Hasta", "Chitra", "Anuradha",
                             "Uttara Ashadha", "Revati"},
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
        # Namkaran classically done on the 11th day post-birth, but the
        # muhurat rules apply to whichever day it's actually observed.
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                         "Ekadashi", "Dwadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya"},
        # Soft/friendly (mridu/laghu/dhruva/chara) nakshatras favoured.
        "good_nakshatras": {"Ashwini", "Rohini", "Mrigashira", "Punarvasu",
                             "Pushya", "Hasta", "Chitra", "Swati",
                             "Anuradha", "Shravana", "Uttara Phalguni",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},
        # Harsh (tikshna/krura) nakshatras avoided for infants.
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula", "Purva Bhadrapada"},
        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday"},
        "avoid_days": {"Tuesday", "Saturday"},
        "check_panchak": True,
        "check_chaturmas": False,   # Namkaran timing is child-driven, not liturgical
        "check_kharmas":   False,   # ditto — must happen ~11th day post-birth regardless
        "check_dagdha":    False,   # child-driven timing overrides Dagdha
        "check_jupiter_combust": False,
        "check_venus_combust":   False,
        "check_mercury_combust": False,
    },
    "vidyarambh": {
        "label": "Vidyarambh (Starting Education)",
        # Jupiter is karaka of learning — Jupiter's day (Thursday) is peak.
        "good_tithis": {"Dwitiya", "Tritiya", "Panchami", "Dashami",
                         "Ekadashi", "Dwadashi"},
        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                          "Amavasya"},
        "good_nakshatras": {"Ashwini", "Rohini", "Mrigashira", "Punarvasu",
                             "Pushya", "Hasta", "Chitra", "Swati",
                             "Anuradha", "Shravana", "Revati"},
        "avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula"},
        # Thursday best (Guru's day) — reflect via boost in scoring.
        "good_days":  {"Wednesday", "Thursday", "Friday", "Monday"},
        "avoid_days": {"Tuesday", "Saturday", "Sunday"},
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
# Classical rule: eclipse day + 1 day before + 1 day after are all inauspicious.
# Even after grahana sutak ends, the atmosphere is considered energetically
# unsettled. Dates sourced from NASA eclipse tables + Drik Panchang.
# Update annually. Applies to ALL event types (universal, not per-event).
_ECLIPSE_DATES: dict[int, list[tuple[date, str]]] = {
    2026: [
        (date(2026, 2, 17), "Annular Solar Eclipse"),
        (date(2026, 3, 3),  "Total Lunar Eclipse"),
        (date(2026, 8, 12), "Total Solar Eclipse"),
        (date(2026, 8, 28), "Partial Lunar Eclipse"),
    ],
    2027: [
        (date(2027, 2, 6),  "Annular Solar Eclipse"),
        (date(2027, 2, 20), "Penumbral Lunar Eclipse"),
        (date(2027, 7, 18), "Penumbral Lunar Eclipse"),
        (date(2027, 8, 2),  "Total Solar Eclipse"),
    ],
    2028: [
        (date(2028, 1, 26), "Annular Solar Eclipse"),
        (date(2028, 2, 12), "Total Lunar Eclipse"),
        (date(2028, 7, 22), "Total Solar Eclipse"),
        (date(2028, 8, 6),  "Partial Lunar Eclipse"),
    ],
}


def _eclipse_flag(d: date) -> tuple[bool, str]:
    """True if d is within 1 day of a known eclipse. Applies to ALL events."""
    for year in (d.year, d.year - 1, d.year + 1):  # handles Jan/Dec boundary
        for edate, ename in _ECLIPSE_DATES.get(year, []):
            gap = abs((d - edate).days)
            if gap == 0:
                return True, f"{ename} on this date — universal muhurat blocker"
            if gap == 1:
                which = "day before" if d < edate else "day after"
                return True, f"{ename} ({which}, {edate:%b %d}) — traditionally inauspicious"
    return False, ""


# ─── Dagdha ("burnt") tithi-weekday combinations ─────────────────────
# Classical rule from Muhurtha Chintamani: certain tithi+weekday pairings
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


def _bhadra_window_for_day(chart: Chart, day_start: datetime) -> str:
    """Return a short string describing Bhadra's presence during the day.

    Samples 6 points across the day (every 4 hours) — accurate enough
    for user-facing "morning / afternoon" guidance without doing full
    half-tithi boundary computation.
    """
    from datetime import timedelta as _td
    hours_active: list[int] = []
    for h in range(0, 24, 3):
        when = day_start.replace(hour=h, minute=0, second=0)
        if _bhadra_active_at(chart, when):
            hours_active.append(h)
    if not hours_active:
        return ""
    # Compress into a period description.
    start_h = min(hours_active)
    end_h = max(hours_active) + 3
    if end_h > 23:
        end_h = 23
    period = "morning" if start_h < 12 and end_h < 15 else \
             "afternoon" if start_h >= 12 and start_h < 17 else \
             "evening" if start_h >= 17 else \
             "most of day"
    return f"Bhadra active ~{start_h:02d}:00-{end_h:02d}:00 ({period}) — avoid ceremonies in that window"


# ─── Choghadiya — 8 sub-day windows per weekday (Muhurta Chintamani) ─
# Classical day-Choghadiya sequence (sunrise-to-sunset ÷ 8) starts from
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
# Sources: Muhurta Chintamani + Ashvalayana Grihya Sutra; consolidated
# per Drik Panchang / traditional Namkaran manuals.
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


def _moon_nakshatra_for(chart: Chart, when: datetime) -> str:
    """Return Moon's nakshatra at the given moment."""
    snap = compute_transit_snapshot(chart, when)
    moon = next((p for p in snap.planets if p.name == "Moon"), None)
    return moon.nakshatra if moon else ""


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


def _chandra_bala(user_moon_rashi: str, transit_moon_rashi: str) -> tuple[int, str]:
    """Return (house 1..12, verdict) for the user's Chandra Bala on this day."""
    try:
        u_idx = RASHIS.index(user_moon_rashi)
        t_idx = RASHIS.index(transit_moon_rashi)
    except ValueError:
        return 0, ""
    house = ((t_idx - u_idx) % 12) + 1
    if house in _CHANDRA_BALA_STRONG:
        verdict = "strong"
    elif house in _CHANDRA_BALA_WEAK:
        verdict = "weak"
    else:
        verdict = "neutral"
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
    c_house, c_verdict = _chandra_bala(user_moon.rashi, transit_moon.rashi)
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
    _, c_verdict = _chandra_bala(p_moon.rashi, transit_moon.rashi)
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
    """Reduce both partners' factors to a single wedding-day verdict."""
    b_tara_ok = bride.tara_bala in ("excellent", "good", "ok")
    g_tara_ok = groom.tara_bala in ("excellent", "good", "ok")
    b_chandra_ok = bride.chandra_bala in ("strong", "neutral")
    g_chandra_ok = groom.chandra_bala in ("strong", "neutral")

    both_tara_avoid = (bride.tara_bala == "avoid" and groom.tara_bala == "avoid")
    if both_tara_avoid:
        return "avoid"
    if (bride.tara_bala == "excellent" and groom.tara_bala == "excellent"
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


def score_event(event_type: str, panchang, weekday_name: str, nakshatra: str,
                is_panchak: bool, is_chaturmas: bool,
                kharmas_reason: str, eclipse_reason: str,
                combust: dict[str, bool],
                adhik_reason: str = "",
                nitya_yoga: str = "", nitya_blocks: bool = False,
                boosters: tuple[str, ...] = ()) -> tuple[str, str, tuple[str, ...]]:
    """Return (rating, reason, flags) for the given event type.

    HARD exclusions (return 'avoid'), in priority order:
      1. Adhik Maas — universal blocker for all shubh karya
      2. Eclipse day / ±1 day — universal
      3. Panchak, Chaturmas, Kharmas, Dagdha (per-event flag)
      4. Vaidhriti / Vyatipata Nitya Yogas — universal
      5. Combust karaka (per-event flag)
      6. Avoid-nakshatra, avoid-tithi

    UNIVERSAL BOOSTERS override caution/acceptable → excellent:
      - Amrit Siddhi Yoga (nakshatra+weekday)
      - Sarvartha Siddhi Yoga (nakshatra+weekday)
      - Ravi Yoga (Sun-based)

    SOFT scoring: +2 favourable tithi, +2 favourable nakshatra, +1 favourable
    weekday. Peak-day (e.g. Thu for Vidyarambh) adds an extra +1. Avoid-weekday
    subtracts 1. Final rating: >=5 excellent, 4 good, 3 acceptable, else caution.
    """
    rules = EVENT_RULES.get(event_type)
    if rules is None:
        return "avoid", f"Unknown event type: {event_type}", ()

    flags: list[str] = []
    reasons: list[str] = []

    # ─── Hard exclusions (universal + per-event) ────────────────────
    # Adhik Maas is the top-priority universal blocker.
    if adhik_reason:
        flags.append("adhik_maas")
        return "avoid", adhik_reason, tuple(flags)
    # Eclipse is universal — no event override.
    if eclipse_reason:
        flags.append("eclipse")
        return "avoid", eclipse_reason, tuple(flags)
    # Vaidhriti / Vyatipata nitya yogas — universal blockers.
    if nitya_blocks:
        flags.append("nitya_yoga_block")
        return "avoid", f"{nitya_yoga} Nitya Yoga — universally inauspicious for shubh karya", tuple(flags)
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
    if panchang.tithi_name in rules["avoid_tithis"]:
        flags.append("avoid_tithi")
        return "avoid", f"Avoid tithi ({panchang.tithi_name})", tuple(flags)

    # ─── Soft scoring ───────────────────────────────────────────────
    score = 0
    if panchang.tithi_name in rules["good_tithis"]:
        score += 2
        reasons.append(f"good tithi ({panchang.tithi_name})")
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

    if score >= 5:
        rating = "excellent"
    elif score == 4:
        rating = "good"
    elif score == 3:
        rating = "acceptable"
    else:
        rating = "caution"

    # ─── Universal boosters override caution/acceptable → excellent ─
    # Amrit Siddhi, Sarvartha Siddhi, Ravi Yoga are classical universal-
    # auspicious combinations that lift the day regardless of soft-score
    # (they cannot override hard exclusions above, only lift the rating).
    if boosters:
        flags.extend(f.lower().replace(" ", "_") for f in ("Amrit Siddhi", "Sarvartha Siddhi", "Ravi Yoga") if any(b.startswith(f) for b in boosters))
        booster_names = "; ".join(boosters)
        # Amrit Siddhi is the strongest — always lifts to excellent.
        # Sarvartha Siddhi / Ravi Yoga lift to excellent if not already above.
        if any(b.startswith("Amrit Siddhi") for b in boosters):
            rating = "excellent"
            reasons.insert(0, booster_names)
        elif rating in ("caution", "acceptable", "good"):
            # Lift only if not already excellent — don't downgrade.
            rating = "excellent" if rating != "caution" else "good"
            reasons.insert(0, booster_names)

    return rating, "; ".join(reasons) or "neutral factors", tuple(flags)


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
            when = datetime.combine(d, datetime.min.time().replace(hour=12), tzinfo=tz)
            p = compute_panchang(base_chart, when)
            nakshatra = _moon_nakshatra_for(base_chart, when)
            is_panchak = nakshatra in _PANCHAK_NAKSHATRAS
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
            # Sub-day windows for planning — format as "HH:MM-HH:MM"
            rk_str = f"{p.rahu_kaal_start.strftime('%H:%M')}-{p.rahu_kaal_end.strftime('%H:%M')}"
            ab_str = f"{p.abhijit_start.strftime('%H:%M')}-{p.abhijit_end.strftime('%H:%M')}"
            # Phase B — Bhadra / Vishti karana window + Choghadiya table
            bhadra_window = _bhadra_window_for_day(base_chart, when)
            choghadiya = tuple(_choghadiya_windows(p.weekday, p.sunrise, p.sunset))
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

        # Abujha override — universally auspicious days for this event type.
        abujha_name = _abujha_for(d, event_type)
        if abujha_name:
            candidates.append(MuhuratCandidate(
                d=d, weekday=p.weekday,
                tithi=p.tithi_name, tithi_paksha=p.tithi_paksha,
                nakshatra=nakshatra,
                rating="excellent",
                reason=f"Abujha Muhurat — {abujha_name} (universally auspicious)",
                flags=("abujha_muhurat",),
                personal=personal, couple=couple,
                rahu_kaal=rk_str, abhijit_muhurta=ab_str,
                nitya_yoga=nitya_yoga, boosters=boosters,
                bhadra_window=bhadra_window, choghadiya=choghadiya,
            ))
            continue

        rating, reason, flags = score_event(
            event_type, p, p.weekday, nakshatra,
            is_panchak, is_chaturmas, kharmas_reason, eclipse_reason, combust,
            adhik_reason=adhik_reason,
            nitya_yoga=nitya_yoga, nitya_blocks=nitya_blocks,
            boosters=boosters,
        )
        candidates.append(MuhuratCandidate(
            d=d, weekday=p.weekday,
            tithi=p.tithi_name, tithi_paksha=p.tithi_paksha,
            nakshatra=nakshatra,
            rating=rating, reason=reason, flags=flags,
            personal=personal, couple=couple,
            rahu_kaal=rk_str, abhijit_muhurta=ab_str,
            nitya_yoga=nitya_yoga, boosters=boosters,
            bhadra_window=bhadra_window, choghadiya=choghadiya,
        ))

    tier_order = {"excellent": 0, "good": 1, "acceptable": 2, "caution": 3, "avoid": 4}
    candidates.sort(key=lambda c: (tier_order.get(c.rating, 99), c.d))
    return candidates


# ─── Backward-compat shim ────────────────────────────────────────────
def find_vivah_candidates(city: str, start: date, days: int = 90) -> list[MuhuratCandidate]:
    """Backward-compat wrapper — pre-refactor callers used this name."""
    return find_candidates("vivah", city, start, days)
