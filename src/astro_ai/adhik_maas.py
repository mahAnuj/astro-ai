"""Computed Adhik Maas (intercalary lunar month) windows, from the ephemeris.

`muhurat._ADHIK_MAAS_RANGES` (muhurat.py:177) is a hand-typed table of six years,
read by `_adhik_maas_flag()` (muhurat.py:187) and consumed once per candidate day
by the shipped Muhurat Finder at muhurat.py:1220. Its 2028 row is the real **2026**
window with the year mistyped — same month name (`Adhik Jyeshtha`), near-identical
range. The live effect is two-sided: every valid muhurat in May-June 2028 is
suppressed as malamas, and the genuine Adhik Chaitra of March-April 2029 raises no
warning at all. Nothing in the repo could see it, because a table with no
computation over it has nothing to disagree with. This module is that computation.

THE RULE
--------
A lunar month runs amavasya -> amavasya (**amanta** reckoning). The Sun crosses a
sidereal 30° boundary — a **sankranti** — roughly once a solar month, slightly less
often than the Moon laps it. So a lunar month normally contains exactly one
sankranti. When it contains **none**, it is an **Adhik Maas** ("extra month", also
*malamas*, the polluted month — no shubh karya). When it contains **two**, it is a
**Kshaya Maas**, a month deleted from the reckoning. The adhik month takes the name
of the **following** nija (true) month, prefixed "Adhik": the leap month before nija
Jyeshtha is Adhik Jyeshtha.

Equivalently, and this is the formulation the code uses: take the Sun's rashi at the
two bounding new-moon **instants**. If it is unchanged, no boundary was crossed
between them — adhik. If it advanced by two, two were crossed — kshaya.

SUNRISE-RECKONED BOUNDARY CONVENTION
------------------------------------
The new-moon instant is a point in time; a calendar window needs whole civil days.
A lunar day belongs to the month that is running at its **local sunrise in New
Delhi** — the same convention `lunar_observances` uses for its tithis and
`compute_panchang()` uses for "today's tithi" (chart.py:2660). So the window starts
on the first day whose sunrise falls after the opening new moon, and ends on the day
before the first day whose sunrise falls after the closing new moon. Windows come
out 29 or 30 days inclusive, which is what a 29.53-day synodic month permits.

**A 31-day window is always the signature of one specific mistake**: taking the two
bounding new moons' *civil dates* inclusive. Issue #141's own proposed table made
exactly that error for 2029 (Mar 15 - Apr 14) and 2031 (Aug 18 - Sep 17) — one day
too wide at each edge, 31 days long, and therefore not a lunar month. The verified
answers are 2029-03-16 .. 2029-04-13 and 2031-08-19 .. 2031-09-16. Do not tune this
detector to reproduce the issue's rows; that would "fix" correct output into wrong.

PROVENANCE
----------
Matches `festival_registry` and `lunar_observances` exactly: New Delhi (NCT)
28.6139N 77.2090E, IST, Swiss Ephemeris (pyswisseph, Lahiri sidereal).

VERIFIED EVIDENCE — 2026-08-07, drikpanchang.com New Delhi year calendars
-------------------------------------------------------------------------
`https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=YYYY&geoname-id=1261481`

  2026  `Vat Savitri / May 16, 2026 / Jyeshtha, Krishna Amavasya`;
        `Padmini Ekadashi / May 27, 2026 / Jyeshtha Adhika, Shukla Ekadashi`;
        `Parama Ekadashi / June 11, 2026 / Jyeshtha Adhika, Krishna Ekadashi`
        => **2026-05-17 .. 2026-06-15, Jyeshtha**
  2027  no evidence of a leap month => **none**
  2028  **no `Adhika` row anywhere** in the 2028 calendar => **none**
        (this is the row muhurat.py currently gets wrong)
  2029  `Padmini Ekadashi / March 26, 2029 / Chaitra Adhika, Shukla Ekadashi`;
        `Ugadi / Gudi Padwa / April 14, 2029 / Chaitra, Shukla Pratipada`
        (nija Chaitra begins Apr 14, so Adhika ends Apr 13)
        => **2029-03-16 .. 2029-04-13, Chaitra**
  2030  no evidence of a leap month => **none**
  2031  `Somavati Amavasya / August 18, 2031 / Bhadrapada, Krishna Amavasya`
        (so Adhika begins Aug 19);
        `Hartalika Teej / September 19, 2031 / Bhadrapada, Shukla Tritiya`
        (so nija Bhadrapada Pratipada = Sep 17, and Adhika ends Sep 16)
        => **2031-08-19 .. 2031-09-16, Bhadrapada**

Padmini Ekadashi and Parama Ekadashi occur *only* inside an Adhik Maas, so their
appearance on a Drik year calendar is itself a positive leap-month marker — which is
what makes the 2028 calendar's silence meaningful rather than merely unhelpful.
`lunar_observances`' docstring independently records Drik's "Padmini Ekadashi
2026-05-27", and `festival_registry.py:396,431` independently assert that 2026 has
an Adhik Jyeshtha. Three sources, one answer.

THE TRAP THIS FORMULATION AVOIDS
--------------------------------
Sankranti membership must be decided by **instant**, never by civil date, and 2026
is the year that proves it by 4 hours 29 minutes. The new moon is 2026-06-15
08:24 IST and the Mithuna Sankranti is 2026-06-15 12:53 IST — the **same civil
day**. The sankranti falls after the new moon, so it belongs to the *next* month,
which is precisely what leaves Adhik Jyeshtha sankranti-free. An implementation that
compares calendar dates puts that crossing inside the adhik month, counts one
sankranti, and concludes 2026 has no Adhik Maas — reintroducing the exact bug being
fixed, on the one year every reviewer spot-checks.

`intercalary_months` is immune by construction: it compares the Sun's rashi at the
two new-moon instants and never handles a sankranti date at all. Rewriting it to
bisect explicitly for sankranti instants is the temptation; there is nothing to gain
and that trap to re-enter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import swisseph as swe

# Private cross-module helper, imported deliberately. Precedent:
# `lunar_observances.py:148` imports this same symbol, and main.py:790 imports
# `astro_ai.muhurat._choghadiya_windows` the same way.
#
# `_sunrise_sunset(day, lat, lon, tz)` takes raw coordinates and needs no Chart.
# `compute_panchang()` would be the obvious public entry point but requires a full
# Chart, which requires compute_chart() -> geocode_place() -> a Nominatim network
# call (chart.py:326) — unusable for a multi-day scan.
#
# This import is ALSO what executes `swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)`
# (chart.py:162, process-global, set once at module import). `_sun_rashi` below is
# sidereal and is meaningless without it. Do not "clean this up" into a
# function-local import: the sid mode would then be unset the first time
# `_sun_rashi` runs, and every month name would be silently wrong.
from astro_ai.chart import _sunrise_sunset

_DELHI_LAT = 28.6139
_DELHI_LON = 77.2090
_DELHI_TZ = ZoneInfo("Asia/Kolkata")

# Index = the rashi the Sun *enters* to open that month, so Mesha (0) sankranti
# opens Chaitra. A month is named for the rashi entered during it.
_MONTH_NAMES: tuple[str, ...] = (
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashwina",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
)

# Bounded by the Swiss Ephemeris data shipped with pyswisseph and by the fact that
# nobody is planning a muhurat outside it.
SUPPORTED_YEARS = range(1900, 2101)

_UTC = ZoneInfo("UTC")


@dataclass(frozen=True)
class LunarMonth:
    """One amanta lunar month, as an inclusive civil-date window.

    `start` and `end` use exactly the same sunrise-reckoned convention as
    `IntercalaryMonth` — `start` is the first day whose New Delhi sunrise follows
    the opening new-moon instant, `end` is the day before the first day whose
    sunrise follows the closing one. Windows are 29 or 30 days inclusive; a
    31-day one is the civil-date-inclusive mistake the module docstring warns
    about.

    `name` is the **nija** month name with no prefix (``"Jyeshtha"``), for every
    kind — an adhik month carries the name of the following nija month, and
    callers render ``f"Adhik {name}"`` themselves.

    `kind` is ``"nija"`` (one sankranti — an ordinary month), ``"adhik"`` (none)
    or ``"kshaya"`` (two). These are three distinct phenomena and must not be
    collapsed: only "adhik" is malamas, and "kshaya" means the name is *deleted*
    from that year's reckoning.
    """

    start: date
    end: date
    name: str
    kind: str


@dataclass(frozen=True)
class IntercalaryMonth:
    """One leap or deleted lunar month, as an inclusive civil-date window.

    `name` is the **nija** month name with no prefix (``"Jyeshtha"``); callers
    render ``f"Adhik {name}"`` themselves. `kind` is ``"adhik"`` or ``"kshaya"`` —
    they are opposite phenomena and must not be collapsed into one flag.
    """

    start: date
    end: date
    name: str
    kind: str


def _elongation(jd: float) -> float:
    """Moon-minus-Sun ecliptic longitude in [0, 360), which is 0 at new moon.

    Deliberately computed with NO sidereal flag: a difference of two longitudes is
    ayanamsa-invariant, because the ayanamsa shifts Sun and Moon by the same amount
    and it cancels. Adding FLG_SIDEREAL here would be harmless but misleading.
    Compare `_sun_rashi`, where the flag is mandatory rather than optional — having
    these two backwards produces plausible-looking output with month names off by
    one, which is the kind of wrong that survives review.
    """
    moon = swe.calc_ut(jd, swe.MOON)[0][0]
    sun = swe.calc_ut(jd, swe.SUN)[0][0]
    return (moon - sun) % 360.0


def _sun_rashi(jd: float) -> int:
    """Sidereal rashi (0 = Mesha .. 11 = Meena) occupied by the Sun at `jd`.

    FLG_SIDEREAL is REQUIRED. A rashi is an absolute position, not a difference, so
    it is not ayanamsa-invariant — tropical longitudes sit ~24° ahead of sidereal
    and would misassign roughly one date in twelve, plus every month name. The
    Lahiri ayanamsa this relies on is set process-globally by importing
    `astro_ai.chart` (see the import comment above).
    """
    return int(swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0] // 30)


def _new_moon_instants(jd_start: float, jd_end: float) -> list[float]:
    """Every new-moon instant in [jd_start, jd_end], as Julian Days (UT).

    Elongation climbs monotonically at ~12.19°/day, so on a 0.25-day grid (~3° per
    step) the only way for it to *decrease* is the 360 -> 0 wrap at conjunction.
    That gives a bracket with no risk of missing a lunation, which is then closed by
    plain bisection — ~50 halvings of a 0.25-day interval is far below the second,
    which is more precision than the sunrise comparison can consume.
    """
    step = 0.25
    instants: list[float] = []
    jd = jd_start
    prev = _elongation(jd)
    while jd < jd_end:
        nxt = jd + step
        cur = _elongation(nxt)
        if cur < prev:  # wrapped past 360 -> conjunction lies in (jd, nxt)
            lo, hi = jd, nxt
            for _ in range(50):
                mid = (lo + hi) / 2.0
                if _elongation(mid) > 180.0:
                    lo = mid  # still pre-conjunction
                else:
                    hi = mid
            instants.append((lo + hi) / 2.0)
        jd, prev = nxt, cur
    return instants


def _jd_to_utc(jd: float) -> datetime:
    """Julian Day (UT) -> tz-aware UTC datetime."""
    y, m, d, hour_frac = swe.revjul(jd)
    hours = int(hour_frac)
    minutes = int((hour_frac - hours) * 60)
    seconds = int(round(((hour_frac - hours) * 60 - minutes) * 60))
    if seconds >= 60:
        minutes, seconds = minutes + 1, 0
    if minutes >= 60:
        hours, minutes = hours + 1, 0
    return datetime(int(y), int(m), int(d), hours, minutes, seconds, tzinfo=_UTC)


def _dt_to_jd(dt: datetime) -> float:
    """tz-aware datetime -> Julian Day (UT). Inverse of `_jd_to_utc`."""
    u = dt.astimezone(_UTC)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60.0 + u.second / 3600.0)


def _first_sunrise_day_after(instant_jd: float) -> date:
    """First New Delhi civil day whose sunrise is strictly later than `instant_jd`.

    Starts a day early (the instant's own IST date minus one) so that an instant
    falling before that morning's sunrise is attributed to its own date rather than
    the next. Each step costs two `swe.rise_trans` calls, but this is only ever
    called for a month already flagged intercalary — two calls per boundary, a
    handful per century — so the cost is negligible and no caching is warranted.
    """
    day = _jd_to_utc(instant_jd).astimezone(_DELHI_TZ).date() - timedelta(days=1)
    for _ in range(5):
        rise, _sunset = _sunrise_sunset(day, _DELHI_LAT, _DELHI_LON, _DELHI_TZ)
        if _dt_to_jd(rise) > instant_jd:
            return day
        day += timedelta(days=1)
    raise RuntimeError(f"no sunrise found after JD {instant_jd}")


@lru_cache(maxsize=8)
def lunar_months(year: int) -> tuple[LunarMonth, ...]:
    """Every amanta lunar month overlapping the Gregorian `year`, ascending.

    Ordinary ("nija") months included, which is the only thing that distinguishes
    this from `intercalary_months` — that function is now a filter over this one.

    The scan runs 1 Oct of `year-1` to 1 Mar of `year+1` so that both bounding new
    moons of every month touching `year` are inside it, with slack.

    CONSUMER: `astro_ai.lunar_dates.nija_month()` resolves "the nija Ashadha of
    2027" against this, which is how Devshayani Ekadashi and the abujha muhurats
    in `muhurat.py` land in the right lunar month in an Adhik Maas year. That
    consumer depends on the `kind` field being exact, not merely on the windows
    being right — see the `kind` note on `LunarMonth`.

    GATE: `scripts/verify_adhik_maas.py` (5 gates) covers this function through
    `intercalary_months`, and `scripts/verify_muhurat_tables.py` covers the nija
    months this one additionally emits. Run both after any change here.
    """
    if year not in SUPPORTED_YEARS:
        raise ValueError(f"year {year} outside SUPPORTED_YEARS {SUPPORTED_YEARS}")

    jd_start = swe.julday(year - 1, 10, 1, 0.0)
    jd_end = swe.julday(year + 1, 3, 1, 0.0)
    moons = _new_moon_instants(jd_start, jd_end)

    jan1, dec31 = date(year, 1, 1), date(year, 12, 31)
    found: list[LunarMonth] = []
    for a, b in zip(moons, moons[1:]):
        ra, rb = _sun_rashi(a), _sun_rashi(b)
        step = (rb - ra) % 12
        kind = (
            "nija" if step == 1
            else "adhik" if step == 0
            else "kshaya" if step == 2
            else None
        )
        if kind is None:  # pragma: no cover — astronomically impossible
            continue
        start = _first_sunrise_day_after(a)
        end = _first_sunrise_day_after(b) - timedelta(days=1)
        # The month is named for the rashi the Sun enters to open the *following*
        # nija month; at `a` the Sun still sits in the previous one.
        name = _MONTH_NAMES[(ra + 1) % 12]
        # Filter on OVERLAP, not on `start.year == year`. An adhik maas can straddle
        # 31 Dec, and a start-year test would make it invisible from the year that
        # holds its tail — which is the year whose muhurats it suppresses. Nija
        # months need the same treatment for the same reason: Pausha and Magha
        # routinely straddle 1 Jan, and `lunar_dates` must find Magha from the year
        # its shukla paksha falls in.
        if end >= jan1 and start <= dec31:
            found.append(LunarMonth(start=start, end=end, name=name, kind=kind))
    return tuple(found)


def intercalary_months(year: int) -> tuple[IntercalaryMonth, ...]:
    """Every adhik or kshaya month overlapping the Gregorian `year`.

    A filter over `lunar_months`, which holds the enumeration. Output is
    unchanged from when this function owned the loop itself — `lunar_months`
    keeps the same scan window, the same rashi-step classification and the same
    overlap filter, and only additionally emits `kind == "nija"`, which is
    dropped here.
    """
    return tuple(
        IntercalaryMonth(start=m.start, end=m.end, name=m.name, kind=m.kind)
        for m in lunar_months(year)
        if m.kind != "nija"
    )


def adhik_maas_for_date(d: date) -> IntercalaryMonth | None:
    """The Adhik Maas containing `d`, or None."""
    for m in intercalary_months(d.year):
        # Kshaya months are skipped on purpose. A kshaya maas is a *deleted* month,
        # not malamas — it carries no prohibition on shubh karya and must never
        # suppress a muhurat. Only "adhik" is a blocker.
        if m.kind == "adhik" and m.start <= d <= m.end:
            return m
    return None


def adhik_maas_flag(d: date) -> tuple[bool, str]:
    """Drop-in replacement for `muhurat._adhik_maas_flag`.

    The reason string is byte-identical to what muhurat.py:191 emits today,
    em-dash included, so swapping the implementation changes no user-facing text.

    The blanket except is deliberate. `find_candidates` wraps its whole per-day
    factor block in `except Exception: continue` (muhurat.py:1238), so a detector
    that raises does not surface an error to anyone — it **silently deletes that
    entire day** from the user's results. Degrading permissively to "not adhik" is
    the lesser evil: at worst a handful of days are offered that a leap month would
    have blocked, instead of days vanishing with no explanation.
    """
    try:
        m = adhik_maas_for_date(d)
        if m is not None:
            return True, (
                f"Adhik Maas (Adhik {m.name}) — no shubh karya during intercalary month"
            )
        return False, ""
    except Exception:
        return False, ""
