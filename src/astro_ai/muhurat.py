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
    ChartError, NAKSHATRAS,
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


def _moon_nakshatra_for(chart: Chart, when: datetime) -> str:
    """Return Moon's nakshatra at the given moment."""
    snap = compute_transit_snapshot(chart, when)
    moon = next((p for p in snap.planets if p.name == "Moon"), None)
    return moon.nakshatra if moon else ""


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
                combust: dict[str, bool]) -> tuple[str, str, tuple[str, ...]]:
    """Return (rating, reason, flags) for the given event type.

    HARD exclusions (return 'avoid'): Panchak, Chaturmas (if enabled),
    combust karaka (if enabled), avoid-nakshatra, avoid-tithi.

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
    if rules["check_panchak"] and is_panchak:
        flags.append("panchak")
        return "avoid", f"Panchak day ({nakshatra}) — inauspicious", tuple(flags)
    if rules["check_chaturmas"] and is_chaturmas:
        flags.append("chaturmas")
        return "avoid", "Chaturmas period — traditionally restricted", tuple(flags)
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
                    days: int = 90) -> list[MuhuratCandidate]:
    """Return muhurat candidates for the given event in the next `days` days.

    Best-first sorted. Includes 'avoid' rows so users see which dates were
    rejected and why (transparency > filtering).
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

    for i in range(days):
        d = start + timedelta(days=i)
        try:
            when = datetime.combine(d, datetime.min.time().replace(hour=12), tzinfo=tz)
            p = compute_panchang(base_chart, when)
            nakshatra = _moon_nakshatra_for(base_chart, when)
            is_panchak = nakshatra in _PANCHAK_NAKSHATRAS
            is_chaturmas = _in_chaturmas(d)
            combust = _combustion_flags(base_chart, when)
        except Exception:
            continue

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
            ))
            continue

        rating, reason, flags = score_event(
            event_type, p, p.weekday, nakshatra,
            is_panchak, is_chaturmas, combust,
        )
        candidates.append(MuhuratCandidate(
            d=d, weekday=p.weekday,
            tithi=p.tithi_name, tithi_paksha=p.tithi_paksha,
            nakshatra=nakshatra,
            rating=rating, reason=reason, flags=flags,
        ))

    tier_order = {"excellent": 0, "good": 1, "acceptable": 2, "caution": 3, "avoid": 4}
    candidates.sort(key=lambda c: (tier_order.get(c.rating, 99), c.d))
    return candidates


# ─── Backward-compat shim ────────────────────────────────────────────
def find_vivah_candidates(city: str, start: date, days: int = 90) -> list[MuhuratCandidate]:
    """Backward-compat wrapper — pre-refactor callers used this name."""
    return find_candidates("vivah", city, start, days)
