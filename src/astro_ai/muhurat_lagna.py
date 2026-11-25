"""Vivah lagna windows for the muhurat finder (#1026): the spans of one date in which the rising
sign is owned by a benefic and the 7th house is clean, as Rao's wedding guideline reads.

Pure functions plus one `lru_cache`; no I/O beyond the already-cached `geocode_place`, no LLM, no
request field. NOTHING here is read by `muhurat.find_candidates`, so the day rating cannot move
(tests/test_muhurat_lagna.py pins that, by value and by AST).

Sources (knowledge/, re-read against the astro-auditor's #1026 ruling; no book is named here that
this repo does not hold, and `data/` was not present when this was written, so nothing below was
checked against a page of Rao):
  * grahas.md section 12.5, the "Two independent muhurta authorities" paragraph: Rao's wedding
    row gives lagna "Benefic planet owned" and the comment "The 7th house should be clean".
  * grahas.md section 2 (Rao 3.2.2): natural benefics are Jupiter, Venus, the waxing Moon and
    Mercury; natural malefics are Sun, Mars, Rahu, Ketu, the waning Moon, and Mercury when joined.
  * vedic_reference.md section 4.7: Mercury is benefic "when not joined by malefics" and the
    malefics are Saturn, Mars, Sun, Rahu, Ketu and the waning Moon. grahas.md section 2 omits
    Saturn from its extraction of the same Rao passage; the 4.7 set is the conservative reading
    (fewer Gemini/Virgo windows), and it is the one used: `_MERCURY_MALEFICS`.
  * vedic_reference.md section 29.7: what each anga is used for.

What is OUR reading, because the sources say nothing more (the legend says so on the page):
  * "clean" 7th house = none of the nine grahas, the nodes included, in the sign opposite the
    lagna. Aspects to the 7th are NOT considered: no held source says whether they count.
  * "joined" (Mercury) = the same sign, the whole-sign reading used everywhere in this site.
  * Rahu is the TRUE node, the one `chart.PLANETS` uses; Ketu is Rahu + 180 degrees.

The rule, per instant, sidereal Lahiri, whole-sign houses (the frame `compute_chart` uses):
  1. lagna sign owned by a benefic: Taurus, Libra, Sagittarius, Pisces always; Cancer only while
     the Moon is waxing (elongation 0..180); Gemini and Virgo only while Mercury shares its sign
     with no malefic.
  2. the 7th sign (lagna + 6) holds none of the nine bodies.
A window is a maximal span of daylight where both hold inside ONE lagna sign: the page names the
lagna, so two adjacent qualifying signs are two windows.

Edges are FOUND, not tabulated (the way `muhurat._bhadra_spans_for_day` finds karana edges): the
lagna sign on a 10-minute grid, the slow state (each body's sign, waxing or waning) on a 3-hour
grid, every change bisected to one second, then the predicate read once at the middle of each
piece. Rounding is INWARD to the whole minute (start up, end down), the opposite of
`_bhadra_window_for_day`: Bhadra states a hazard and must never omit a bad minute, this states a
qualifying span and must never claim a minute that does not qualify.

Not covered, on purpose: (a) a body crossing a sign line and re-crossing inside one 3-hour cell
(a retrograde station on a boundary); the Moon, the fastest, spends about 2 days in a sign and
over 14 waxing, the same argument as `_BHADRA_GRID`; (b) the ascendant going backwards inside one
10-minute cell, which only happens at polar latitudes where daylight is not ordinary anyway.

Rahu Kaal is a NOTE on a window ("overlaps Rahu Kaal HH:MM-HH:MM"), never a filter or a rank: the
note is built from the row's own printed `rahu_kaal`, so the minutes agree with the row.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

import swisseph as swe

from astro_ai import chart as _chart
from astro_ai.chart import (
    RASHIS,
    _sid_calc_ut,
    _sid_houses,
    _sign_name,
    _sunrise_sunset,
    julian_day_utc,
)
from astro_ai.muhurat import AUSPICIOUS_RATINGS

log = logging.getLogger(__name__)

# --- User-visible wording: the astro-auditor's #1026 ruling, transcribed. One place, so a test
# can pin each string without rendering. No book, chapter or table number in prose; Rao's name is
# allowed. Never "auspicious", "safe", "recommended" or "the Vivah muhurat" in this block.
HEADING = "Lagna windows (Rao's guideline)"
CAVEAT = ("These are guidelines, not final recommendations. Planetary strength matters more "
          "than following these thumb-rules.")
UNCHANGED = "The day rating is unchanged."
NONE_TEXT = ("No lagna window met this guideline on this day. This does not make the day "
             "unsuitable; the day rating is unchanged.")
BENEFIC_DISCLOSURE = ("Benefic follows Rao's natural benefics: Jupiter, Venus, the waxing Moon, "
                      "and Mercury unless joined by malefics.")
# Our own reading, stated once per page (see the module docstring for why each is ours).
LEGEND_NOTES = (
    "Houses are whole signs counted from the lagna, in the sidereal (Lahiri) zodiac. The 7th "
    "house is the sign opposite the lagna.",
    "Rao's guideline asks for a clean 7th house. This finder reads clean as: none of the nine "
    "grahas, Rahu and Ketu included, is in that sign. That is our reading. The sources we hold "
    "do not say whether aspects to the 7th house count, so aspects are not considered.",
    "Rahu is the true node, and Ketu is the point opposite it.",
    "Cancer counts only while the Moon is waxing at that moment. Gemini and Virgo count only "
    "while Mercury shares its sign with none of the Sun, Mars, Saturn, Rahu, Ketu or a waning "
    "Moon. Joined is read as the same sign.",
    "A planet changing sign during the day can start or end a window, so the edges are computed "
    "for each date and rounded inward to the whole minute. Times are local to the city searched.",
)

# --- The rule's constants. Written out from the ruling, never derived from the code under test.
_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
# Rahu is the TRUE node, as `chart.PLANETS` has it; Ketu is derived (Rahu + 180), never calculated.
_BODIES = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
           "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
           "Rahu": swe.TRUE_NODE}
# Sign indexes follow chart.RASHIS: Aries 0 ... Pisces 11.
_GEMINI, _CANCER, _VIRGO = 2, 3, 5
_ALWAYS_BENEFIC_SIGNS = frozenset({1, 6, 8, 11})   # Taurus, Libra, Sagittarius, Pisces
# vedic_reference.md section 4.7 (see the docstring): same-sign, whole-sign reading of "joined".
_MERCURY_MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")   # plus the Moon while waning
_QUALIFIER = {_CANCER: "Moon waxing",
              _GEMINI: "Mercury not joined by a malefic",
              _VIRGO: "Mercury not joined by a malefic"}

_LAGNA_GRID_S = 600.0     # 10 min: Delhi lagnas last about 1.5-2.5 h
_SLOW_GRID_S = 10800.0    # 3 h: see "Not covered" in the module docstring
_BISECT_S = 1.0
_RAHU_KAAL = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\s*$")


# --- The predicate, over a plain {body: sign index} dict so tests can inject a sky ---------------

def is_waxing(elongation: float) -> bool:
    """Moon waxing = 0 <= (Moon - Sun) mod 360 < 180 (Shukla paksha)."""
    return (elongation % 360.0) < 180.0


def is_benefic_lagna(lagna_sign: int, signs: dict[str, int], elongation: float) -> bool:
    """Is this lagna sign benefic-owned at a sky with these body signs and Moon-Sun elongation."""
    if lagna_sign in _ALWAYS_BENEFIC_SIGNS:
        return True
    if lagna_sign == _CANCER:
        return is_waxing(elongation)
    if lagna_sign in (_GEMINI, _VIRGO):
        mercury = signs["Mercury"]
        if any(signs[b] == mercury for b in _MERCURY_MALEFICS):
            return False
        return not (signs["Moon"] == mercury and not is_waxing(elongation))
    return False


def seventh_clean(lagna_sign: int, signs: dict[str, int]) -> bool:
    """No body of the nine, nodes included, in the sign opposite the lagna."""
    seventh = (lagna_sign + 6) % 12
    return not any(signs.get(b) == seventh for b in _GRAHAS)


def _sky(jd: float) -> tuple[dict[str, int], float]:
    """({body: sidereal sign index}, Moon-Sun elongation) at a Julian Day (UT)."""
    lon = {name: _sid_calc_ut(jd, body)[0][0] % 360.0 for name, body in _BODIES.items()}
    lon["Ketu"] = (lon["Rahu"] + 180.0) % 360.0
    return {n: int(v // 30) for n, v in lon.items()}, (lon["Moon"] - lon["Sun"]) % 360.0


def _slow_state(jd: float) -> tuple:
    signs, elongation = _sky(jd)
    return tuple(signs[b] for b in _GRAHAS), is_waxing(elongation)


def _lagna_sign(jd: float, lat: float, lon: float) -> int:
    _, ascmc = _sid_houses(jd, lat, lon)
    return int(float(ascmc[0]) // 30) % 12


# --- Edge finding ---------------------------------------------------------------------------

def _edges(f, lo: float, hi: float, s_lo, s_hi) -> list[float]:
    """Every time in (lo, hi] where `f` changes value, to _BISECT_S, given f(lo) and f(hi).
    A cell holding two changes yields both: after the first edge the search resumes from it."""
    out: list[float] = []
    for _ in range(16):
        if s_lo == s_hi:
            break
        a, b = lo, hi
        while b - a > _BISECT_S:
            mid = (a + b) / 2.0
            if f(mid) == s_lo:
                a = mid
            else:
                b = mid
        out.append(b)
        if b >= hi:
            break
        lo, s_lo = b, f(b)
    return out


def _grid_edges(f, span: float, step: float) -> list[float]:
    points = [0.0]
    while points[-1] + step < span:
        points.append(points[-1] + step)
    points.append(span)
    states = [f(p) for p in points]
    out: list[float] = []
    for i in range(1, len(points)):
        if states[i] != states[i - 1]:
            out += _edges(f, points[i - 1], points[i], states[i - 1], states[i])
    return out


@dataclass(frozen=True)
class _Window:
    start: datetime   # city-local, whole minute
    end: datetime     # city-local, whole minute
    sign: int         # lagna sign index, 0 = Aries


class _NoDaylight(Exception):
    """The date has no ordinary sunrise-to-sunset span (#227, #228): there is nothing to window,
    and that is NOT the same claim as 'no window met the guideline'."""


def _ceil_minute(dt: datetime) -> datetime:
    floor = dt.replace(second=0, microsecond=0)
    return floor if floor == dt else floor + timedelta(minutes=1)


@lru_cache(maxsize=512)
def _windows_for(day: date, lat: float, lon: float, tz_name: str) -> tuple[_Window, ...]:
    """The qualifying windows of `day` at a place. Deterministic in its key, so the cache can
    never be stale (same reasoning as chart._PANCHANG_CACHE); lat/lon are rounded by the caller."""
    tz = ZoneInfo(tz_name)
    sunrise, sunset = _sunrise_sunset(day, lat, lon, tz)
    if (sunrise is None or sunset is None or not sunset > sunrise
            or sunrise.date() != day or sunset.date() != day):
        raise _NoDaylight
    start_utc = sunrise.astimezone(timezone.utc)
    span = (sunset - sunrise).total_seconds()
    jd0 = julian_day_utc(start_utc)

    def jd(t: float) -> float:
        return jd0 + t / 86400.0

    def lagna_at(t: float) -> int:
        return _lagna_sign(jd(t), lat, lon)

    cuts = sorted({0.0, span,
                   *_grid_edges(lagna_at, span, _LAGNA_GRID_S),
                   *_grid_edges(lambda t: _slow_state(jd(t)), span, _SLOW_GRID_S)})
    leaves: list[tuple[float, float, int]] = []   # (from, to, lagna sign) of qualifying pieces
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2.0
        sign = lagna_at(mid)
        if sign not in _ALWAYS_BENEFIC_SIGNS and sign not in (_GEMINI, _CANCER, _VIRGO):
            continue   # Aries, Leo, Scorpio, Capricorn, Aquarius: no need to read the sky
        signs, elongation = _sky(jd(mid))
        if not (is_benefic_lagna(sign, signs, elongation) and seventh_clean(sign, signs)):
            continue
        if leaves and leaves[-1][2] == sign and leaves[-1][1] == a:
            leaves[-1] = (leaves[-1][0], b, sign)
        else:
            leaves.append((a, b, sign))

    windows: list[_Window] = []
    for a, b, sign in leaves:
        s = _ceil_minute((start_utc + timedelta(seconds=a)).astimezone(tz))
        e = (start_utc + timedelta(seconds=b)).astimezone(tz).replace(second=0, microsecond=0)
        if s < e:
            windows.append(_Window(s, e, sign))
    return tuple(windows)


# --- The view the template reads -------------------------------------------------------------

@dataclass(frozen=True)
class LagnaWindowView:
    start: str        # "HH:MM", city-local
    end: str
    sign: str         # "Taurus"
    qualifier: str    # "" | "Moon waxing" | "Mercury not joined by a malefic"
    rahu_note: str    # "" | "overlaps Rahu Kaal 09:00-10:30"


@dataclass(frozen=True)
class LagnaView:
    windows: tuple[LagnaWindowView, ...]
    heading: str = HEADING
    caveat: str = CAVEAT
    unchanged: str = UNCHANGED
    none_text: str = NONE_TEXT


@dataclass(frozen=True)
class LagnaLegend:
    heading: str = HEADING
    disclosure: str = BENEFIC_DISCLOSURE
    notes: tuple[str, ...] = LEGEND_NOTES
    caveat: str = CAVEAT
    unchanged: str = UNCHANGED


def _eligible(candidate, event_type: str) -> bool:
    """The gate shared by the row view and the legend: Vivah, a row the page calls auspicious,
    and a date with an ordinary sunrise (candidate.sunrise is "" otherwise, #228)."""
    return (event_type == "vivah" and candidate.rating in AUSPICIOUS_RATINGS
            and bool(candidate.sunrise))


def _parse_rahu_kaal(text: str) -> tuple[int, int] | None:
    """The row's printed "HH:MM-HH:MM" as minutes of the day, or None if it is not that."""
    m = _RAHU_KAAL.match(text or "")
    if not m:
        return None
    return int(m[1]) * 60 + int(m[2]), int(m[3]) * 60 + int(m[4])


def _rahu_note(window: _Window, rahu_kaal: tuple[int, int] | None, printed: str) -> str:
    if rahu_kaal is None:
        return ""
    s = window.start.hour * 60 + window.start.minute
    e = window.end.hour * 60 + window.end.minute
    # Both sides are whole minutes, so a strictly positive overlap is one the row can show;
    # a window that only touches Rahu Kaal at a minute mark is not reported.
    if min(e, rahu_kaal[1]) - max(s, rahu_kaal[0]) <= 0:
        return ""
    h0, m0, h1, m1 = (int(g) for g in _RAHU_KAAL.match(printed).groups())
    return f"overlaps Rahu Kaal {h0:02d}:{m0:02d}-{h1:02d}:{m1:02d}"


def lagna_view(candidate, event_type: str, city: str) -> LagnaView | None:
    """The lagna windows for one finder row, or None when the row gets no block.

    None means "render nothing": a non-Vivah event, a row the page does not call auspicious, a
    date without ordinary daylight, an unknown place, or ANY failure while computing. A failure
    must never read as an empty window list, because the empty list renders NONE_TEXT, which is
    a claim about the sky. Failures log a warning and are not alerted: one per row would page
    the owner once per date."""
    if not _eligible(candidate, event_type):
        return None
    try:
        # Through the module, not a copy of the name: `compute_chart` (and every test that stubs
        # the place) reaches the same attribute, so one stub covers the search and the windows.
        lat, lon, tz_name = _chart.geocode_place(city)
        windows = _windows_for(candidate.d, round(lat, 4), round(lon, 4), tz_name)
        rahu = _parse_rahu_kaal(candidate.rahu_kaal)
        return LagnaView(windows=tuple(
            LagnaWindowView(
                start=f"{w.start:%H:%M}", end=f"{w.end:%H:%M}",
                sign=_sign_name(RASHIS[w.sign]), qualifier=_QUALIFIER.get(w.sign, ""),
                rahu_note=_rahu_note(w, rahu, candidate.rahu_kaal))
            for w in windows))
    except Exception as err:   # noqa: BLE001 - see the docstring: render nothing, never a false "none"
        log.warning("lagna windows skipped for %s: %s: %s", candidate.d, type(err).__name__, err)
        return None


def legend(candidates, event_type: str, city: str) -> LagnaLegend | None:
    """The once-per-page disclosure, or None when no row on the page produced a block.

    Keyed on a produced `lagna_view`, not on `_eligible` alone (#1457): eligibility is only the
    gate, and a page whose every row failed to compute would otherwise print a legend explaining
    windows that are not there. It runs `lagna_view` per row, so it computes through the same
    cached windows the row partials use (`_windows_for` is memoised) and costs no new
    astronomy; `city` is required, with no default, so a caller cannot ask without the place."""
    if any(lagna_view(c, event_type, city) is not None for c in candidates):
        return LagnaLegend()
    return None
