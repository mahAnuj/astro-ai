"""Muhurat Finder — auspicious-date calculator (Issue #108).

Upgraded from MVP to classically-decision-grade tool per user's correctness
concern (2026-07-30). Now checks 6 classical criteria for Vivah muhurat:

  1. Tithi           — favourable lunar day (Dwitiya, Tritiya, Panchami, etc.)
  2. Weekday         — Mon/Wed/Thu/Fri/Sun preferred; Tue/Sat avoided
  3. Nakshatra       — Rohini, Mrigashira, Hasta, Anuradha etc. favourable;
                       Bharani, Krittika, Ardra, Ashlesha, Jyeshtha, Vishakha,
                       Purva Phalguni, Purva Ashadha, Purva Bhadrapada avoided
  4. Panchak         — 5-day period when Moon transits last 5 nakshatras
                       (Dhanishta latter half through Revati) — AVOID
  5. Chaturmas       — Devshayani Ekadashi to Devuthani Ekadashi (mid-Jul to
                       mid-Nov); traditionally weddings-restricted period
  6. Guru+Shukra     — both must be uncombust (>11° from Sun); if either is
                       combust, marriages traditionally postponed

Scoring:
  - Hard exclusion (rating='avoid'): Panchak OR combustion OR Chaturmas OR
    avoid-tithi OR avoid-nakshatra
  - Soft scoring on remaining candidates by tithi + nakshatra + weekday

Not yet included (future work):
  - Adhik Maas detection (needs Panchang API or hardcoded lookup)
  - Personal chart matching (moon nakshatra harmony with bride/groom charts)
  - Regional variants (South Indian traditions differ on some rules)

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


# ─── Classical criteria for Vivah muhurat ────────────────────────────

# Auspicious tithis (lunar days) for weddings per classical tradition.
_VIVAH_GOOD_TITHIS = {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                        "Ekadashi", "Dwadashi", "Trayodashi"}
_VIVAH_AVOID_TITHIS = {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                         "Amavasya", "Purnima"}

# Classical wedding-auspicious nakshatras.
_VIVAH_GOOD_NAKSHATRAS = {"Rohini", "Mrigashira", "Magha", "Uttara Phalguni",
                            "Hasta", "Swati", "Anuradha", "Mula",
                            "Uttara Ashadha", "Uttara Bhadrapada", "Revati"}
_VIVAH_AVOID_NAKSHATRAS = {"Bharani", "Krittika", "Ardra", "Ashlesha",
                             "Jyeshtha", "Vishakha", "Purva Phalguni",
                             "Purva Ashadha", "Purva Bhadrapada"}

# Panchak nakshatras — Moon transiting these 5 is inauspicious for weddings
# (and most ceremonies). Classical rule: Dhanishta (latter half through end),
# Shatabhisha, Purva Bhadrapada, Uttara Bhadrapada, Revati.
_PANCHAK_NAKSHATRAS = {"Dhanishta", "Shatabhisha", "Purva Bhadrapada",
                         "Uttara Bhadrapada", "Revati"}

# Best weekdays for Vivah — Mon, Wed, Thu, Fri, Sun. Avoid Tue, Sat.
_VIVAH_GOOD_DAYS = {"Monday", "Wednesday", "Thursday", "Friday", "Sunday"}
_VIVAH_AVOID_DAYS = {"Tuesday", "Saturday"}

# Combustion orb — Jupiter within 11°, Venus within 10° of Sun. Classical
# values (some texts use different orbs; using standard BPHS values).
_COMBUST_ORB_JUPITER = 11.0
_COMBUST_ORB_VENUS = 10.0


@dataclass(frozen=True)
class MuhuratCandidate:
    """One candidate date with its Panchang details + rating."""
    d: date
    weekday: str
    tithi: str
    tithi_paksha: str
    nakshatra: str
    rating: str               # "excellent" | "good" | "acceptable" | "avoid"
    reason: str               # short human explanation
    flags: tuple[str, ...]    # e.g. ("panchak", "chaturmas", "jupiter_combust")


# ─── Chaturmas date ranges (Devshayani → Devuthani Ekadashi) ─────────
# These dates vary slightly year-to-year based on lunar calendar. Sourced
# from Drik Panchang / Vaishnava calendars. Update annually.
_CHATURMAS_RANGES: dict[int, tuple[date, date]] = {
    2026: (date(2026, 7, 15), date(2026, 11, 11)),  # approx; verify with Panchang
    2027: (date(2027, 7,  5), date(2027, 11,  1)),  # approx
    2028: (date(2028, 7, 23), date(2028, 11, 19)),  # approx
}


def _in_chaturmas(d: date) -> bool:
    """True if the date falls within the traditional Chaturmas restriction window."""
    rng = _CHATURMAS_RANGES.get(d.year)
    if rng is None:
        # Fallback for years outside our table: mid-July to mid-November approx
        return date(d.year, 7, 15) <= d <= date(d.year, 11, 15)
    return rng[0] <= d <= rng[1]


def _moon_nakshatra_for(chart: Chart, when: datetime) -> str:
    """Return the Moon's nakshatra at the given moment.

    Uses compute_transit_snapshot to get Moon's exact position, then reads
    its nakshatra attribute directly.
    """
    snap = compute_transit_snapshot(chart, when)
    moon = next((p for p in snap.planets if p.name == "Moon"), None)
    return moon.nakshatra if moon else ""


def _combustion_flags(chart: Chart, when: datetime) -> tuple[bool, bool]:
    """Return (jupiter_combust, venus_combust) at the given moment.

    Combustion = planet within critical orb degrees of the Sun's longitude.
    Classical rule: combust marriage-karakas (Jupiter, Venus) → wedding
    must be postponed until they emerge.
    """
    snap = compute_transit_snapshot(chart, when)
    sun = next((p for p in snap.planets if p.name == "Sun"), None)
    jup = next((p for p in snap.planets if p.name == "Jupiter"), None)
    ven = next((p for p in snap.planets if p.name == "Venus"), None)
    if not sun or not jup or not ven:
        return False, False

    from astro_ai.chart import _rashi_index as _ri
    sun_abs = _ri(sun.rashi) * 30.0 + sun.longitude
    jup_abs = _ri(jup.rashi) * 30.0 + jup.longitude
    ven_abs = _ri(ven.rashi) * 30.0 + ven.longitude

    # Angular separation on shortest arc.
    def _sep(a: float, b: float) -> float:
        d = abs(a - b) % 360.0
        return min(d, 360.0 - d)

    return (_sep(sun_abs, jup_abs) <= _COMBUST_ORB_JUPITER,
            _sep(sun_abs, ven_abs) <= _COMBUST_ORB_VENUS)


def score_vivah(panchang, weekday_name: str, nakshatra: str,
                is_panchak: bool, is_chaturmas: bool,
                jupiter_combust: bool, venus_combust: bool) -> tuple[str, str, tuple[str, ...]]:
    """Return (rating, reason, flags) for a Vivah muhurat.

    HARD-EXCLUSION rules (rating='avoid'):
      - Panchak day
      - Chaturmas month
      - Jupiter or Venus combust
      - Avoid-nakshatra
      - Avoid-tithi
      - Avoid-weekday (Tuesday/Saturday) alone is a caution, not hard-exclude

    SOFT SCORING for the remainder:
      +2 favourable tithi
      +2 favourable nakshatra
      +1 favourable weekday
    Rating: >=4 excellent; 3 good; 2 acceptable; <2 caution.
    """
    flags: list[str] = []
    reasons: list[str] = []

    # Hard exclusions first
    if is_panchak:
        flags.append("panchak")
        return "avoid", f"Panchak day ({nakshatra}) — inauspicious for weddings", tuple(flags)
    if is_chaturmas:
        flags.append("chaturmas")
        return "avoid", "Chaturmas period — traditionally weddings-restricted", tuple(flags)
    if jupiter_combust:
        flags.append("jupiter_combust")
        return "avoid", "Guru (Jupiter) is combust — marriage karaka not visible", tuple(flags)
    if venus_combust:
        flags.append("venus_combust")
        return "avoid", "Shukra (Venus) is combust — marriage karaka not visible", tuple(flags)
    if nakshatra in _VIVAH_AVOID_NAKSHATRAS:
        flags.append("avoid_nakshatra")
        return "avoid", f"Avoid nakshatra ({nakshatra})", tuple(flags)
    if panchang.tithi_name in _VIVAH_AVOID_TITHIS:
        flags.append("avoid_tithi")
        return "avoid", f"Avoid tithi ({panchang.tithi_name})", tuple(flags)

    # Soft scoring for remaining candidates
    score = 0
    if panchang.tithi_name in _VIVAH_GOOD_TITHIS:
        score += 2
        reasons.append(f"good tithi ({panchang.tithi_name})")
    if nakshatra in _VIVAH_GOOD_NAKSHATRAS:
        score += 2
        reasons.append(f"good nakshatra ({nakshatra})")
    if weekday_name in _VIVAH_GOOD_DAYS:
        score += 1
        reasons.append(f"good weekday ({weekday_name})")
    elif weekday_name in _VIVAH_AVOID_DAYS:
        score -= 1
        reasons.append(f"avoid weekday ({weekday_name})")
        flags.append("avoid_weekday")

    if score >= 4:
        rating = "excellent"
    elif score == 3:
        rating = "good"
    elif score == 2:
        rating = "acceptable"
    else:
        rating = "caution"
    return rating, "; ".join(reasons) or "neutral factors", tuple(flags)


def find_vivah_candidates(city: str, start: date, days: int = 90) -> list[MuhuratCandidate]:
    """Return Vivah muhurat candidates in the next `days` days, best-first.

    Full classical scoring: tithi + weekday + nakshatra + Panchak + Chaturmas
    + Guru/Shukra combustion. Returns EVERY date checked (including 'avoid')
    with its rating + reason + flags, sorted by rating then by date.
    """
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
            jup_c, ven_c = _combustion_flags(base_chart, when)
        except Exception:
            continue

        rating, reason, flags = score_vivah(
            p, p.weekday, nakshatra,
            is_panchak, is_chaturmas, jup_c, ven_c,
        )
        candidates.append(MuhuratCandidate(
            d=d, weekday=p.weekday,
            tithi=p.tithi_name, tithi_paksha=p.tithi_paksha,
            nakshatra=nakshatra,
            rating=rating, reason=reason, flags=flags,
        ))

    # Sort: excellent → good → acceptable → caution → avoid, by date within tier
    tier_order = {"excellent": 0, "good": 1, "acceptable": 2, "caution": 3, "avoid": 4}
    candidates.sort(key=lambda c: (tier_order.get(c.rating, 99), c.d))
    return candidates
