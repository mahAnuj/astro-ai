"""The slow-planet transit block `/ask` hands the model, and the cache key part that goes with it (#402).

Classical timing rests on dasha AND transit together; `/ask` carried only the
dasha, so "will I ... this year?" reached the model with half the apparatus
missing. This adds the transit half in the smallest honest form: the four slow
movers counted from the natal Moon, one line each.

THREE THINGS THAT ARE DELIBERATE
--------------------------------
* ONE PINNED MOMENT. `ask_transit_moment()` is local noon IST on the IST date
  `llm.today_anchor()` already names, via `chart.rashifal_day_moment`. The block
  and the cache key both read it, so a given date means one sky.
* THE KEY NEEDS NO CHART. `transit_fingerprint()` is a pure function of the
  moment, so GET (which computes no chart) and POST derive the same segment --
  the #181 failure class if they ever did not. It changes only when Saturn,
  Jupiter or Rahu changes sign (~4.4 times a year), so a cached answer is
  reused across days for the same question without ever going stale against
  the block it was written under.
* THREAD. `chart` sets the sidereal mode once, at import, and Swiss Ephemeris
  keeps it per thread (measured: a worker thread reads ayanamsa 25.10 where the
  importing thread reads 24.22, at JD 2461000). Both /ask handlers are
  `async def`, so they and the block all run on the loop thread; a test pins it.
* NO SWALLOWING `try/except`. A failure here must fail the request: returning
  "" would generate a no-transit answer and cache it under a with-transit key.

The verdicts are `chart._GOCHAR_BENEFIC_HOUSES`, which is Raman's Gochara table
(B.V. Raman, Astrology for Beginners, Ch. XII, p.101), transcribed in
knowledge/vedic_reference.md section 2A. Gochara is counted from the natal Moon,
never the Lagna (section 2A, first paragraph). Rahu and Ketu share one row.
No retrograde flag: the table does not condition on it.

The wording is hedged on purpose. By that table the slow planets are
"challenging" in most houses, so a bare "challenging" would read as a verdict
when it is the ordinary state; the base rate is therefore COMPUTED from the table
and printed beside the lines. The block never tells the model what the answer
must be and never names a source: ask.txt forbids both.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from astro_ai import chart as _chart

# The IST date llm.today_anchor() prints. Same zone, kept equal by
# tests/test_ask_transit.py rather than imported (llm imports this module).
_IST = ZoneInfo(_chart.RASHIFAL_REFERENCE_TZ)

_HEADER = "--- SLOW PLANETS (from natal Moon; context only) ---"
_FRAMING = (
    "A first approximation of the period's climate, never whether a specific "
    "event will happen."
)


def ask_transit_moment() -> datetime:
    """The one moment this request's transit is read at."""
    return _chart.rashifal_day_moment(datetime.now(_IST).date())


def transit_fingerprint(moment: datetime) -> str:
    """Short hash of the slow-mover signs at `moment` and of the block's wording.

    Pure function of `moment`: no chart needed (Ketu is Rahu's opposite and the
    house counts come from the chart fingerprint already in the key). The
    wording is hashed in so an edit to the block invalidates cached answers
    without anyone remembering to bump a constant.
    """
    # Only `lagna_rashi` is read by compute_transit_snapshot; the houses it
    # returns are not used here, only the signs.
    snap = _chart.compute_transit_snapshot(SimpleNamespace(lagna_rashi=_chart.RASHIS[0]), moment)
    signs = {p.name: p.rashi for p in snap.planets}
    raw = "|".join([_HEADER, _FRAMING, signs["Saturn"], signs["Jupiter"], signs["Rahu"]])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def _base_rate() -> str:
    """'challenging in 9 of 12 houses (Jupiter 7)', counted from the table.

    The modal planet group leads and the rest follow in brackets. Derived, not
    typed: a table edit moves the sentence with it (and tests pin the numbers).
    """
    by_count: dict[int, list[str]] = {}
    for planet, benefic in _chart._GOCHAR_BENEFIC_HOUSES.items():
        by_count.setdefault(12 - len(benefic), []).append(planet)
    lead = max(by_count, key=lambda n: len(by_count[n]))
    rest = "; ".join(f"{', '.join(ps)} {n}" for n, ps in by_count.items() if n != lead)
    return f"challenging in {lead} of 12 houses" + (f" ({rest})" if rest else "")


def format_ask_transit(natal, moment: datetime) -> str:
    """The block, ending in a blank line so it slots in ahead of `--- QUESTION ---`."""
    lines = [_HEADER]
    for g in _chart.compute_gochar_impacts(natal, moment):
        lines.append(f"{g.planet} {_ordinal(g.house_from_moon)} {g.favorability}")
    lines.append(f"Base rate: {_base_rate()}. {_FRAMING}")
    return "\n".join(lines) + "\n\n"


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
