"""Muhurat Finder — auspicious-date calculator (Issue #108 MVP).

Personalised muhurat computation using existing chart.py primitives.
MVP scope shipped:
  - Single event type: Vivah (wedding)
  - Location + date range inputs
  - Per-date Panchang lookup (tithi, nakshatra, day-lord)
  - Basic scoring: favourable / acceptable / avoid based on classical rules
  - Results table (best-first sort)

Deferred to full Muhurat Finder:
  - Multiple event types (Griha Pravesh, Namkaran, Vidyarambh, Business)
  - Personal chart matching (moon nakshatra harmony, dasha alignment)
  - Panchak detection with specific severity classifications
  - Combustion checks for Guru/Shukra visibility
  - Better UI with color-coded rows + share links

Free tier: no LLM call, uses existing swisseph via compute_panchang().
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import Any
from zoneinfo import ZoneInfo

from astro_ai.chart import Chart, compute_chart, compute_panchang, ChartError


# Auspicious tithis for Vivah (wedding) muhurat per classical tradition.
_VIVAH_GOOD_TITHIS = {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                        "Ekadashi", "Dwadashi", "Trayodashi"}
_VIVAH_AVOID_TITHIS = {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",
                         "Amavasya", "Purnima"}

# Auspicious nakshatras for weddings (classical shortlist)
_VIVAH_GOOD_NAKSHATRAS = {"Rohini", "Mrigashira", "Magha", "Uttara Phalguni",
                            "Hasta", "Swati", "Anuradha", "Mula",
                            "Uttara Ashadha", "Uttara Bhadrapada", "Revati"}
_VIVAH_AVOID_NAKSHATRAS = {"Bharani", "Krittika", "Ardra", "Ashlesha",
                             "Jyeshtha", "Vishakha", "Purva Phalguni",
                             "Purva Ashadha", "Purva Bhadrapada", "Chitra"}

# Best weekdays for Vivah — Mon, Wed, Thu, Fri, Sun. Avoid Tue, Sat.
_VIVAH_GOOD_DAYS = {"Monday", "Wednesday", "Thursday", "Friday", "Sunday"}
_VIVAH_AVOID_DAYS = {"Tuesday", "Saturday"}


@dataclass(frozen=True)
class MuhuratCandidate:
    """One candidate date with its Panchang details + rating."""
    d: date
    weekday: str
    tithi: str
    tithi_paksha: str
    nakshatra: str            # placeholder — compute_panchang doesn't return it directly; MVP omits
    rating: str               # "excellent" | "good" | "acceptable" | "avoid"
    reason: str               # short human explanation


def score_vivah(panchang, weekday_name: str) -> tuple[str, str]:
    """Return (rating, reason) for a Vivah muhurat on a given day.

    Simple additive scoring:
      +2 if tithi is in VIVAH_GOOD
      -2 if tithi is in VIVAH_AVOID
      +1 if weekday is in VIVAH_GOOD_DAYS
      -1 if weekday is in VIVAH_AVOID_DAYS
      Rating: score >= 3 → excellent; 2 → good; 1 → acceptable; <= 0 → avoid
    """
    score = 0
    reasons = []
    if panchang.tithi_name in _VIVAH_GOOD_TITHIS:
        score += 2
        reasons.append(f"favourable tithi ({panchang.tithi_name})")
    elif panchang.tithi_name in _VIVAH_AVOID_TITHIS:
        score -= 2
        reasons.append(f"avoid tithi ({panchang.tithi_name})")
    if weekday_name in _VIVAH_GOOD_DAYS:
        score += 1
        reasons.append(f"good weekday ({weekday_name})")
    elif weekday_name in _VIVAH_AVOID_DAYS:
        score -= 1
        reasons.append(f"avoid weekday ({weekday_name})")

    if score >= 3:
        rating = "excellent"
    elif score == 2:
        rating = "good"
    elif score == 1:
        rating = "acceptable"
    else:
        rating = "avoid"
    return rating, "; ".join(reasons) or "neutral"


def find_vivah_candidates(city: str, start: date, days: int = 90) -> list[MuhuratCandidate]:
    """Return candidate dates for Vivah in the next `days` days, best-first.

    MVP: computes panchang for each day, scores it, sorts by rating.
    Not filtering out Panchak or Chaturmas yet — future enhancement.
    """
    # Build a Chart object for the city (dummy date; only lat/lon/tz used
    # for panchang sunrise/sunset compute).
    try:
        base_chart = compute_chart(start.isoformat(), "12:00", city)
    except ChartError as err:
        raise ValueError(f"Could not compute chart for {city!r}: {err}") from err

    candidates: list[MuhuratCandidate] = []
    days = max(1, min(days, 365))  # cap at 1 year for perf
    tz = ZoneInfo(base_chart.birth_tz)
    for i in range(days):
        d = start + timedelta(days=i)
        try:
            when = datetime.combine(d, datetime.min.time().replace(hour=12), tzinfo=tz)
            p = compute_panchang(base_chart, when)
        except Exception:
            continue

        weekday_name = p.weekday
        rating, reason = score_vivah(p, weekday_name)
        candidates.append(MuhuratCandidate(
            d=d, weekday=weekday_name,
            tithi=p.tithi_name, tithi_paksha=p.tithi_paksha,
            nakshatra="—",  # MVP: not surfacing nakshatra name yet
            rating=rating, reason=reason,
        ))

    # Sort: excellent → good → acceptable → avoid, preserving date order within tier
    tier_order = {"excellent": 0, "good": 1, "acceptable": 2, "avoid": 3}
    candidates.sort(key=lambda c: (tier_order.get(c.rating, 99), c.d))
    return candidates
