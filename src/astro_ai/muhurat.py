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
from typing import Any
from zoneinfo import ZoneInfo

from astro_ai.chart import (
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

# Combustion orbs from BPHS — planet within these degrees of Sun = combust.
_COMBUST_ORB_JUPITER = 11.0
_COMBUST_ORB_VENUS   = 10.0
_COMBUST_ORB_MERCURY = 12.0    # Mercury has widest orb (per BPHS)


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


# ─── Chaturmas date ranges (Devshayani → Devuthani Ekadashi) ─────────
# Vishnu-sleeping period, traditionally weddings-restricted. Dates vary
# yearly by lunar calendar. Update annually from Drik Panchang.
_CHATURMAS_RANGES: dict[int, tuple[date, date]] = {
    2026: (date(2026, 7, 15), date(2026, 11, 11)),
    2027: (date(2027, 7,  5), date(2027, 11,  1)),
    2028: (date(2028, 7, 23), date(2028, 11, 19)),
}


# ─── Abujha Muhurats (self-auspicious days) ──────────────────────────
# Classical "swayam-siddha" days that override normal Panchang scoring.
# See top-of-file docstring in previous version for full details.
_ABUJHA_MUHURATS: dict[int, list[tuple[date, str, tuple[str, ...]]]] = {
    2026: [
        (date(2026, 4, 30), "Akshaya Tritiya",        ("vivah", "griha_pravesh", "business")),
        (date(2026, 6, 24), "Bhadli Navami",          ("vivah",)),
        (date(2026, 11, 12), "Devuthani Ekadashi",    ("vivah", "griha_pravesh", "business")),
        (date(2026, 11, 13), "Tulsi Vivah",           ("vivah",)),
    ],
    2027: [
        (date(2027, 1, 23), "Basant Panchami",        ("vivah", "griha_pravesh", "vidyarambh", "business")),
        (date(2027, 5, 19), "Akshaya Tritiya",        ("vivah", "griha_pravesh", "business")),
        (date(2027, 6, 13), "Bhadli Navami",          ("vivah",)),
        (date(2027, 10, 31), "Devuthani Ekadashi",    ("vivah", "griha_pravesh", "business")),
        (date(2027, 11, 1),  "Tulsi Vivah",           ("vivah",)),
    ],
}


# ─── Per-event classical rule tables ──────────────────────────────────
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
    """Return the Abujha Muhurat name if this date is one for this event, else ''."""
    for entry_date, name, event_types in _ABUJHA_MUHURATS.get(d.year, []):
        if entry_date == d and event_type in event_types:
            return name
    return ""


def _in_chaturmas(d: date) -> bool:
    """True if date falls within Chaturmas restriction window."""
    rng = _CHATURMAS_RANGES.get(d.year)
    if rng is None:
        return date(d.year, 7, 15) <= d <= date(d.year, 11, 15)
    return rng[0] <= d <= rng[1]


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

    return {
        "jupiter": _sep(jup) <= _COMBUST_ORB_JUPITER,
        "venus":   _sep(ven) <= _COMBUST_ORB_VENUS,
        "mercury": _sep(mer) <= _COMBUST_ORB_MERCURY,
    }


def score_event(event_type: str, panchang, weekday_name: str, nakshatra: str,
                is_panchak: bool, is_chaturmas: bool,
                kharmas_reason: str, eclipse_reason: str,
                combust: dict[str, bool]) -> tuple[str, str, tuple[str, ...]]:
    """Return (rating, reason, flags) for the given event type.

    HARD exclusions (return 'avoid'), in priority order:
      1. Eclipse day / ±1 day — universal; applies to all events
      2. Panchak, Chaturmas, Kharmas, Dagdha (per-event flag)
      3. Combust karaka (per-event flag)
      4. Avoid-nakshatra, avoid-tithi

    SOFT scoring: +2 favourable tithi, +2 favourable nakshatra, +1 favourable
    weekday. Peak-day (e.g. Thu for Vidyarambh) adds an extra +1. Avoid-weekday
    subtracts 1. Final rating: >=5 excellent, 4 good, 3 acceptable, else caution.
    """
    rules = EVENT_RULES.get(event_type)
    if rules is None:
        return "avoid", f"Unknown event type: {event_type}", ()

    flags: list[str] = []
    reasons: list[str] = []

    # ─── Hard exclusions ────────────────────────────────────────────
    # Eclipse is universal — no event override.
    if eclipse_reason:
        flags.append("eclipse")
        return "avoid", eclipse_reason, tuple(flags)
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
    return rating, "; ".join(reasons) or "neutral factors", tuple(flags)


def find_candidates(event_type: str, city: str, start: date,
                    days: int = 90,
                    personal_chart: Chart | None = None) -> list[MuhuratCandidate]:
    """Return muhurat candidates for the given event in the next `days` days.

    Best-first sorted. Includes 'avoid' rows so users see which dates were
    rejected and why (transparency > filtering).

    If `personal_chart` is provided (user's natal Chart), each candidate is
    annotated with a PersonalMatch containing Tara Bala + Chandra Bala per
    day and chart-level notes (Sade Sati phase, Rahu/Ketu Mahadasha). The
    classical rating stays universal — personal factors surface separately
    so users see BOTH reads.
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
            combust = _combustion_flags(base_chart, when)
        except Exception:
            continue

        personal: PersonalMatch | None = None
        if personal_chart is not None:
            personal = _personal_match_for(personal_chart, when, nakshatra, static_notes)

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
                personal=personal,
            ))
            continue

        rating, reason, flags = score_event(
            event_type, p, p.weekday, nakshatra,
            is_panchak, is_chaturmas, kharmas_reason, eclipse_reason, combust,
        )
        candidates.append(MuhuratCandidate(
            d=d, weekday=p.weekday,
            tithi=p.tithi_name, tithi_paksha=p.tithi_paksha,
            nakshatra=nakshatra,
            rating=rating, reason=reason, flags=flags,
            personal=personal,
        ))

    tier_order = {"excellent": 0, "good": 1, "acceptable": 2, "caution": 3, "avoid": 4}
    candidates.sort(key=lambda c: (tier_order.get(c.rating, 99), c.d))
    return candidates


# ─── Backward-compat shim ────────────────────────────────────────────
def find_vivah_candidates(city: str, start: date, days: int = 90) -> list[MuhuratCandidate]:
    """Backward-compat wrapper — pre-refactor callers used this name."""
    return find_candidates("vivah", city, start, days)
