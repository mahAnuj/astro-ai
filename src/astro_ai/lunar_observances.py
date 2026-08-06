"""Computed monthly lunar observances — Purnima, Amavasya, both Ekadashis.

These are the `tier="recurring"` rows the /festivals hub renders alongside the
hand-verified `festival_registry.FESTIVALS`. They are *computed*, not tabulated:
there are ~50 of them a year and tabulating them by hand would be 150 rows of
transcription risk for three years of coverage.

THE RULE
--------
An observance falls on the day at whose **local sunrise in New Delhi** the
target tithi is running. Sunrise, not midnight and not the tithi's own start
instant — that is the classical convention and it is what `compute_panchang()`
already does for "today's tithi" (chart.py:2660).

Provenance matches `festival_registry` exactly: New Delhi (NCT) 28.6139N
77.2090E, IST, Swiss Ephemeris (pyswisseph, Lahiri sidereal). Tithi is in fact
invariant under ayanamsa — both Sun and Moon shift equally — so the sidereal
choice affects nothing here, but we keep it aligned with the rest of the code.

TWO EDGE CASES, BOTH REAL
-------------------------
* **vriddhi** — a tithi long enough to span two consecutive sunrises, giving
  two candidate days. We take the **first** (Smarta convention). Confirmed
  correct for Purnima; see the KNOWN DISAGREEMENT below for Ekadashi, where it
  is not.
* **kshaya** — a tithi that begins after one sunrise and ends before the next,
  so **no** sunrise falls inside it at all. A naive sunrise scan does not
  mislabel these, it **silently drops them**: the list just comes out one row
  short and looks fine in review. Worked case — Magha Purnima 2027 runs
  2027-02-20 08:00 IST → 2027-02-21 04:53 IST, with sunrise at 06:55 on the
  20th and 06:54 on the 21st, neither inside it; a naive scan yields 12
  Purnimas in 2027 instead of 13. We detect the gap explicitly (see
  `_observances_for_year`) and assign the observance to the day the tithi
  **begins** on.

`scripts/verify_lunar_observances.py` is the gate for both cases. Its Gate A
asserts every lunation contributes exactly one Purnima and one Amavasya, which
is the check that catches a dropped kshaya day; do not weaken it.

SPOT-CHECK — 2026-08-07, drikpanchang.com Hindu calendar (New Delhi)
--------------------------------------------------------------------
Every edge-case date Gate C flags for 2026-2028 was read off the Drik year
calendar (…/calendars/hindu/hinducalendar.html?year=YYYY). 17 of 19 dates
checked agree exactly:

  kshaya, all 6 AGREE — 2026-07-10 Yogini Ekadashi, 2026-11-20 Devutthana
    Ekadashi, 2026-12-23 Margashirsha Purnima, 2027-02-20 Magha Purnima,
    2027-07-29 Kamika Ekadashi, 2028-04-05 Kamada Ekadashi. Each of these is a
    row a naive sunrise scan drops entirely, and Drik prints every one of them
    on the day the tithi begins — the gap-detection rule is right.
  vriddhi Purnima, all 3 AGREE on the FIRST day — 2026-06-29 Jyeshtha Purnima,
    2027-06-18 Jyeshtha Purnima, 2028-12-01 Margashirsha Purnima.
  Sampled ordinary rows also agree: 2026-05-13 Apara, 2026-06-11 Parama,
    2026-07-25 Devshayani, 2026-11-05 Rama, 2027-03-18 Amalaki, 2027-07-14
    Devshayani, 2028-04-20 Varuthini, 2028-12-31 Pausha Purnima.
  A useful confirmation of the Gate B window logic: Drik prints "Sharad
    Purnima" on 2027-10-14 (moonrise reckoning) and "Ashwina Purnima" on
    2027-10-15 (sunrise reckoning). We compute 10-15, and `festival_registry`
    ships 10-14 for the moonrise festival. Both are correct.

KNOWN DISAGREEMENT — vriddhi Ekadashi (2 of 2 checked)
------------------------------------------------------
We emit the FIRST day; Drik gives the SECOND, for both cases in range:
    2026-05-26 → Drik: Padmini Ekadashi, 2026-05-27
    2027-03-03 → Drik: Vijaya Ekadashi,  2027-03-04
This is the classical dashami-viddha rule: an Ekadashi touched by Dashami is
not "shuddha", so the fast moves to the following day — a rule that applies to
Ekadashi specifically and NOT to Purnima or Amavasya, which is why the three
vriddhi Purnimas above match on the first day. Ekadashi is therefore the one
kind whose vriddhi handling here is believed wrong. It is left as-is rather
than patched: changing it is a rule change, not a bug fix, and it needs the
architect's call plus a wider sample than two dates. Both dates are computed
correctly as *tithis*; only the choice of observance day is in question.

Do not import `shloks.TITHI_OBSERVANCES` or call `shloks.observance_for_tithi()`
here. That dict is keyed 1..30 (shloks.py:110-114) while `_tithi_at` returns
0..29, so the lookup is off by one and would silently mislabel every row. The
bilingual names below are copied out of it literally, by hand, after checking
the key convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import swisseph as swe

# Private cross-module helpers, imported deliberately. Precedent: main.py:790
# imports `astro_ai.muhurat._choghadiya_windows` the same way.
#
# `_tithi_at(jd) -> (index 0-29, name, paksha, significance)` and
# `_sunrise_sunset(day, lat, lon, tz)` take raw coordinates and need no Chart.
# `compute_panchang()` would be the obvious public entry point but it requires a
# full Chart, which requires compute_chart() -> geocode_place() -> a Nominatim
# network call (chart.py:326) — unusable for a multi-day scan. Importing these
# two keeps the diff on chart.py (3400+ lines, highest-traffic module) at zero.
from astro_ai.chart import _sunrise_sunset, _tithi_at

_DELHI_LAT = 28.6139
_DELHI_LON = 77.2090
_DELHI_TZ = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class Observance:
    """One occurrence of a computed monthly observance.

    `slug` is unique **per occurrence**, not per kind — `f"{kind}-{iso}"`, e.g.
    ``ekadashi-2026-08-09``. The hub uses it as an HTML `id` and as an anchor
    target, and there are ~24 Ekadashis a year; a bare ``"ekadashi"`` would
    emit two dozen duplicate DOM ids and every anchor would land on the first
    one. Split on the first ``-`` to recover the kind.

    `tier` is ``"recurring"`` to match `festival_registry.Festival.tier`, so the
    hub and the template can treat both kinds of row through one code path.
    """

    slug: str
    name_en: str
    name_hi: str
    rule: str
    tier: str = "recurring"


# Tithi index (0-29, as returned by `_tithi_at`) -> (kind, name_en, name_hi, rule).
# 10 = Shukla Ekadashi, 14 = Purnima, 25 = Krishna Ekadashi, 29 = Amavasya.
# Names copied from shloks.TITHI_OBSERVANCES, which is keyed 1..30 — the keys
# here are one lower on purpose. See the module docstring.
_TARGETS: dict[int, tuple[str, str, str, str]] = {
    10: (
        "ekadashi",
        "Ekadashi",
        "एकादशी",
        "Shukla Ekadashi — eleventh tithi of the waxing fortnight, at sunrise",
    ),
    14: (
        "purnima",
        "Purnima",
        "पूर्णिमा",
        "Purnima — fifteenth tithi of the waxing fortnight (full moon), at sunrise",
    ),
    25: (
        "ekadashi",
        "Ekadashi",
        "एकादशी",
        "Krishna Ekadashi — eleventh tithi of the waning fortnight, at sunrise",
    ),
    29: (
        "amavasya",
        "Amavasya",
        "अमावस्या",
        "Amavasya — fifteenth tithi of the waning fortnight (new moon), at sunrise",
    ),
}


def _tithi_index_at_sunrise(day: date) -> int:
    """Tithi index 0-29 running at New Delhi sunrise on `day`."""
    sunrise, _sunset = _sunrise_sunset(day, _DELHI_LAT, _DELHI_LON, _DELHI_TZ)
    sunrise_ut = sunrise.astimezone(ZoneInfo("UTC"))
    sunrise_jd = swe.julday(
        sunrise_ut.year,
        sunrise_ut.month,
        sunrise_ut.day,
        sunrise_ut.hour + sunrise_ut.minute / 60 + sunrise_ut.second / 3600,
    )
    return _tithi_at(sunrise_jd)[0]


def _observance(day: date, idx: int) -> Observance:
    kind, name_en, name_hi, rule = _TARGETS[idx]
    return Observance(
        slug=f"{kind}-{day.isoformat()}",
        name_en=name_en,
        name_hi=name_hi,
        rule=rule,
    )


@lru_cache(maxsize=8)
def _observances_for_year(year: int) -> tuple[tuple[date, Observance], ...]:
    """Every Purnima / Amavasya / Ekadashi falling in `year`, ascending.

    Cached because a year is ~390 sunrise + tithi computations (~20ms) and the
    hub asks for the same one or two years on every request. Nothing here runs
    at import time — a Cloud Run cold start must not pay for a route most
    requests never touch.

    Sampling runs from 20 Dec of the previous year to 10 Jan of the next so
    that a run straddling either year boundary is seen whole; the result is
    filtered back to `year` at the end.
    """
    start = date(year - 1, 12, 20)
    end = date(year + 1, 1, 10)

    samples: list[tuple[date, int]] = []
    day = start
    while day <= end:
        samples.append((day, _tithi_index_at_sunrise(day)))
        day += timedelta(days=1)

    out: list[tuple[date, Observance]] = []

    # Pass 1 — runs. Consecutive days sharing a tithi index are a vriddhi tithi;
    # the run's FIRST day is the observance (Smarta convention).
    for i, (day_i, idx) in enumerate(samples):
        if i > 0 and samples[i - 1][1] == idx:
            continue
        if idx in _TARGETS:
            out.append((day_i, _observance(day_i, idx)))

    # Pass 2 — gaps. If the index jumps by more than one between consecutive
    # sunrises, the skipped tithi(s) began and ended entirely between them: a
    # kshaya tithi, which pass 1 cannot see at all. It is observed on the day it
    # begins, which is the earlier of the two sampled days.
    for (day_a, idx_a), (_day_b, idx_b) in zip(samples, samples[1:]):
        skipped = (idx_b - idx_a) % 30
        for step in range(1, skipped):
            missing = (idx_a + step) % 30
            if missing in _TARGETS:
                out.append((day_a, _observance(day_a, missing)))

    out = [(d, o) for d, o in out if d.year == year]
    out.sort(key=lambda pair: (pair[0], pair[1].slug))
    return tuple(out)


def observances_between(start: date, end: date) -> list[tuple[date, Observance]]:
    """Every (date, observance) falling in [`start`, `end`], ascending.

    Crosses year boundaries. Mirrors `festival_registry.upcoming()`'s contract:
    a year that fails to compute is skipped rather than raised, so the hub
    degrades to a shorter list, never to a 500.
    """
    if end < start:
        return []
    out: list[tuple[date, Observance]] = []
    for year in range(start.year, end.year + 1):
        try:
            rows = _observances_for_year(year)
        except Exception:  # pragma: no cover - ephemeris/IO failure, degrade
            continue
        out.extend((d, o) for d, o in rows if start <= d <= end)
    out.sort(key=lambda pair: (pair[0], pair[1].slug))
    return out
