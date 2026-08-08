"""Computed sankranti (solar ingress) instants and observance dates.

The solar counterpart of `lunar_dates`. `festival_registry` carries Makar
Sankranti and Pongal as hand-typed date rows (festival_registry.py:141,174) —
three years, verified against Drik, and unextendable: nothing in the repo could
answer "when is Makar Sankranti in 2031?" without another manual almanac read.
This module answers it, and answers it for all twelve rashis.

THE RULE
--------
A **sankranti** is the instant the Sun crosses a sidereal 30° boundary and
enters the next rashi. It is a point in time, computed — not a convention and
not a table. Twelve happen per year, roughly one every 30.4 days, and each
Gregorian year contains exactly one ingress into each rashi.

The dates drift slowly and in one direction: the sidereal year is ~20 minutes
longer than the tropical one, so a sankranti falls ~20 minutes later each year
and about one day later per 72 years. Makar Sankranti observance dates across
`SUPPORTED_YEARS`, from this module: 1900-01-13, 1950-01-14, 2000-01-15,
2050-01-15, 2100-01-15. Any hard-coded "always 14 January" is already wrong at
both ends of the range this module covers.

WHAT IS COMPUTED VS. WHAT IS CONVENTION
---------------------------------------
**Computed:** the ingress instant (`sankranti_instant`), to well under a second,
by daily scan plus bisection on `adhik_maas._sun_rashi`. The Sun covers ~1°/day
so a 30° arc lasts ~30 days; a one-day coarse step cannot skip an ingress.

**Convention:** the observance *date* (`sankranti_date`). The instant does not
determine the day on its own — a sankranti late in the evening is kept the
following day, because the punya kaal (the meritorious window for snan, daan and
tarpan) cannot be observed after dark. The rule applied here is a deliberate
simplification, stated so it can be argued with:

    the civil date of the ingress instant if the instant falls **at or before
    New Delhi sunset that day**, otherwise the **next day**.

This is an approximation of the punya-kaal rules reduced to a single test, in
exactly the sense `lunar_dates` labels its madhyahna sampling an approximation of
a classical rule to a single sampled instant. Real almanacs are finer and
regionally divided: the punya kaal is variously 16 ghatis (~6h24m) either side of
the instant, or 40 ghatis, or the whole day; Bengal and Odisha use Mishra Kaal
and the southern reckoning differs again; an ingress in the last few ghatis
before sunset is kept the next day in some traditions even though this test keeps
it the same day. Where those rules disagree with this one, they disagree — this
module reports one convention and names it.

VALIDATION — six published dates, 6 for 6
-----------------------------------------
(a) `festival_registry`'s Makar Sankranti rows, already independently verified
    against Drik Panchang for 2026-2028 (festival_registry.py:141, and Pongal at
    :174 carries the same three dates from a second Drik page):

      2026-01-14  ingress 2026-01-14 15:07:20 IST, 2h38m before sunset -> same day
      2027-01-15  ingress 2027-01-14 21:10:25 IST, 3h25m AFTER sunset  -> next day
      2028-01-15  ingress 2028-01-15 03:24:02 IST, 14h22m before sunset -> same day

    **2027 is the discriminating case and the reason the sunset test exists.**
    Taking the civil date of the instant gives 2027-01-14 and contradicts Drik;
    only the post-sunset roll-forward reproduces 2027-01-15. A one-line
    implementation that returns `instant.date()` passes 2026 and 2028 and fails
    exactly here.

(b) Three further dates read off Drik Panchang's New Delhi monthly calendar on
    **2026-08-08**, chosen to exercise other rashis and both sides of a year
    boundary:

      Dhanu Sankranti 2026  = 2026-12-16 (Wed)   ingress 2026-12-16 10:25:03 IST
      Meena Sankranti 2027  = 2027-03-15 (Mon)   ingress 2027-03-15 07:00:06 IST
      Mesha Sankranti 2027  = 2027-04-14 (Wed)   ingress 2027-04-14 15:28:24 IST

    URL form (geoname-id 1261481 is New Delhi):
    `https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=YYYY&geoname-id=1261481&month=M`

The instants above are what this module prints, to the second. They were also
bisected independently before this module existed, and the two agree to within
one second on all twelve ingresses of 2026-2028 — a sub-second rounding
difference, immaterial here because every anchor sits hours away from sunset.

(c) One more instant, from a source inside the repo that predates this module:
    `adhik_maas`' docstring states "the Mithuna Sankranti is 2026-06-15 12:53
    IST" (adhik_maas.py:82-83), where it is load-bearing for the Adhik Jyeshtha
    of 2026. `sankranti_instant(2026, "Mithuna")` returns 2026-06-15 12:53:01
    IST. That is agreement with a number nobody adjusted to match.

WHAT WOULD FALSIFY THE CONVENTION
---------------------------------
A sankranti whose observance date is verified in a published New Delhi almanac
and differs from what the sunset test yields. The dangerous shape is an ingress
close to sunset, where a finer punya-kaal rule can land on the other day, and the
six anchors do not reach into that band: the nearest is Makar 2026 at 2h38m
before sunset, and on the post-sunset side Makar 2027 at 3h25m after. **Roughly
±2h either side of sunset is therefore untested here.** If such a case turns up:
add the almanac date to this list first and change the rule second — and do not
tune the rule to a single regional almanac, since the traditions genuinely
disagree about exactly these marginal cases.

PROVENANCE
----------
Matches `festival_registry`, `lunar_dates` and `adhik_maas` exactly: New Delhi
(NCT) 28.6139N 77.2090E, IST, Swiss Ephemeris (pyswisseph, Lahiri sidereal). A
rashi boundary is an absolute sidereal position and is NOT ayanamsa-invariant —
`adhik_maas._sun_rashi` requires the Lahiri mode that importing `astro_ai.chart`
sets process-globally. Under a different ayanamsa every date in this file moves.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import swisseph as swe

# Private cross-module helpers, imported deliberately — same precedent and same
# reasons as `lunar_dates.py:115` and `adhik_maas.py:104-118`. This import is ALSO
# what executes `swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)` (chart.py:162,
# process-global, once at module import); `_sun_rashi` is sidereal and is
# meaningless without it, so do not make either import function-local.
from astro_ai.chart import _sunrise_sunset
from astro_ai.adhik_maas import SUPPORTED_YEARS, _jd_to_utc, _sun_rashi

_DELHI_LAT = 28.6139
_DELHI_LON = 77.2090
_DELHI_TZ = ZoneInfo("Asia/Kolkata")

# Index = the value `adhik_maas._sun_rashi` returns, i.e. sidereal longitude // 30.
# Sanskrit names only: this is the rashi the Sun ENTERS, which is what names the
# sankranti ("Makara Sankranti" = the Sun's entry into Makara). `chart.RASHIS`
# carries the same twelve in the same order with the Western name attached.
RASHIS: tuple[str, ...] = (
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrishchika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
)

# Spellings in circulation that must not silently resolve to None. "Makar
# Sankranti" is how the festival is spelled everywhere in this repo
# (festival_registry.py:137, festivals.py, trivia.py) while `chart.RASHIS` spells
# the rashi "Makara" — a caller reaching for one and getting a None back would be
# a real bug with no error message. Lookup is case-insensitive on top of this.
_ALIASES: dict[str, str] = {
    "makar": "Makara",
    "vrishchik": "Vrishchika",
    "vrishabh": "Vrishabha",
}

# One coarse step of the ingress scan, in days. The Sun advances ~0.986°/day, so
# it needs ~30 days to cross a 30° rashi and a one-day step cannot step over one.
_SCAN_STEP_DAYS = 1.0

# Bisection halvings of that one-day bracket. 40 would already reach the double
# resolution of a Julian Day near 2.46e6 (~40 microseconds); 60 costs ~20 extra
# ephemeris calls per sankranti, runs once per (year, rashi) thanks to the cache,
# and removes any argument about the tolerance.
_BISECT_STEPS = 60


def _rashi_index(rashi: str) -> int | None:
    """Index of `rashi` in `RASHIS`, tolerating case and the `_ALIASES` spellings.

    Returns None rather than raising: an unknown name is a caller mistake, but
    the whole module degrades to None rather than raising (see
    `sankranti_instant`), and one code path for "no answer" is easier to use
    correctly than two.
    """
    key = rashi.strip().lower()
    key = _ALIASES.get(key, key).lower()
    for i, name in enumerate(RASHIS):
        if name.lower() == key:
            return i
    return None


@lru_cache(maxsize=256)
def sankranti_instant(year: int, rashi: str) -> datetime | None:
    """IST instant the Sun enters `rashi` during Gregorian `year`, or None.

    e.g. ``sankranti_instant(2027, "Makara")`` -> 2027-01-14 21:10:25+05:30, the
    ingress that is *observed* on 2027-01-15 (see `sankranti_date`).

    Coarse daily scan for the rashi change, then bisection to well under a
    second — the same shape as `adhik_maas._new_moon_instants`, with the rashi
    index playing the role the elongation wrap plays there. The scan runs
    1 Jan .. 1 Jan of `year + 1`, which contains exactly one ingress into each
    rashi; the first match is therefore also the only one.

    Returns None for a `year` outside `adhik_maas.SUPPORTED_YEARS` or an
    unrecognised `rashi`, and does NOT raise. A caller that cannot get a date
    must be able to say "no date" — the one thing it must never do is guess, and
    an exception in a per-day scan gets swallowed (see
    `adhik_maas.adhik_maas_flag`'s note on muhurat.py:1238) into exactly that.
    """
    if year not in SUPPORTED_YEARS:
        return None
    target = _rashi_index(rashi)
    if target is None:
        return None

    jd = swe.julday(year, 1, 1, 0.0)
    jd_end = swe.julday(year + 1, 1, 1, 0.0)
    prev = _sun_rashi(jd)
    while jd < jd_end:
        nxt = jd + _SCAN_STEP_DAYS
        cur = _sun_rashi(nxt)
        if cur != prev and cur == target:
            lo, hi = jd, nxt  # lo is pre-ingress, hi is post-ingress
            for _ in range(_BISECT_STEPS):
                mid = (lo + hi) / 2.0
                if _sun_rashi(mid) == target:
                    hi = mid
                else:
                    lo = mid
            return _jd_to_utc((lo + hi) / 2.0).astimezone(_DELHI_TZ)
        jd, prev = nxt, cur
    return None  # pragma: no cover — every rashi is entered once per year


def sankranti_date(year: int, rashi: str) -> date | None:
    """Observance date of the `rashi` sankranti of `year`, or None.

    e.g. ``sankranti_date(2027, "Makara")`` -> date(2027, 1, 15) — Makar
    Sankranti 2027, one day after its ingress instant.

    The ingress day if the instant falls at or before New Delhi sunset, else the
    next day. That single test is a reduction of the punya-kaal rules and is
    labelled as one in the module docstring, which also records the six published
    dates it reproduces and what would falsify it. Do not reach for
    `sankranti_instant(...).date()` in a caller: it disagrees with the almanac
    roughly one year in three (2027 Makar among them) and looks right in the two
    years either side.

    Returns None on the same conditions as `sankranti_instant` — unsupported
    year, unknown rashi.
    """
    instant = sankranti_instant(year, rashi)
    if instant is None:
        return None
    day = instant.date()
    _sunrise, sunset = _sunrise_sunset(day, _DELHI_LAT, _DELHI_LON, _DELHI_TZ)
    if instant <= sunset:
        return day
    return day + timedelta(days=1)
