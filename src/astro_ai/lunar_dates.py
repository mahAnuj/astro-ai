"""Civil date of a named shukla-paksha tithi — "Vaishakha Shukla Tritiya, 2027".

The primitive the repo was missing. `muhurat.py` carried two hand-typed date
tables — `_CHATURMAS_RANGES` and `_ABUJHA_MUHURATS` — because nothing here could
answer "when is Kartika Shukla Ekadashi in 2029?". This module answers it, and
those tables are gone (issue #146).

THE RULE
--------
A tithi belongs to the day at whose **local sunrise in New Delhi** it is running
— the classical convention, and the one `compute_panchang()` uses for "today's
tithi" (chart.py:2660), `lunar_observances` uses for its Ekadashis and
`adhik_maas` uses for its month boundaries. The lunar month is amanta
(amavasya to amavasya), enumerated by `adhik_maas.lunar_months()`.

TWO RECKONINGS, BECAUSE THE ALMANAC USES TWO
--------------------------------------------
Sunrise reckoning is not universal, and assuming it was cost two of the twenty
dates on the first attempt at this module. A **madhyahna-vyapini** observance is
fixed by the tithi prevailing at *midday*, not at sunrise, and
`festival_registry` already records which is which in its `observance_window`
field: Akshaya Tritiya is `"sunrise to madhyahna, Tritiya prevailing"` and Vasant
Panchami is `"madhyahna"`, while the Ekadashis are sunrise-reckoned fasts.

`reckoning="madhyahna"` therefore samples the tithi at the **start of madhyahna**
— sunrise + 2/5 of the daylength, the opening of the third of the day's five
parts — and falls back to the sunrise-reckoned day when the target tithi does not
prevail there on any day. Both halves of that rule are load-bearing, and the two
discriminating cases are Akshaya Tritiya in consecutive years:

  * **2026** — Tritiya runs 04-19 10:50 IST -> 04-20 07:30 IST. Madhyahna on
    04-19 opens 11:02, so Tritiya covers the whole of it; on 04-20 Tritiya is
    running at sunrise (05:50) but has ended long before madhyahna. Drik gives
    **2026-04-19**, the madhyahna day, *not* the sunrise day. Pure sunrise
    reckoning returns 04-20 and is wrong.
  * **2027** — Tritiya runs 05-08 11:50 IST -> 05-09 09:10 IST. Madhyahna on
    05-08 opens 10:57, i.e. *before* Tritiya begins, so it does not prevail at
    madhyahna on 05-08; and on 05-09 it has ended before madhyahna opens. No day
    qualifies, and Drik falls back to the sunrise day, **2027-05-09**. Sampling
    the middle of madhyahna instead of its start returns 05-08 and is wrong, and
    so does taking the earlier day of the gap.

That rule was derived from those two cases and is then held against ten
published dates spanning 2015-2030 in `verify_muhurat_tables.py` Gate 1, plus
`festival_registry`'s independently hand-verified 2026-2028 rows in Gate 4(b).
It is an approximation of a classical rule to a single sampled instant, and it is
labelled as one — if a future year disagrees, widen Gate 1 with the almanac date
first and change the rule second.

Provenance matches `festival_registry`, `lunar_observances` and `adhik_maas`
exactly: New Delhi (NCT) 28.6139N 77.2090E, IST, Swiss Ephemeris (pyswisseph,
Lahiri sidereal). Tithi is in fact ayanamsa-invariant — Sun and Moon shift
equally and it cancels — but the month *names* are not, and they come from
`adhik_maas._sun_rashi`, which is sidereal and requires the Lahiri mode that
importing `astro_ai.chart` sets process-globally.

PURNIMANTA VS AMANTA DOES NOT ARISE HERE
----------------------------------------
The two reckonings disagree about which month a **krishna** paksha belongs to —
purnimanta Kartika Krishna is amanta Ashwina Krishna. They agree on every
**shukla** paksha. Every caller of this module asks for a shukla tithi
(Devshayani, Devuthani, Akshaya Tritiya, Vasant Panchami, Bhadli Navami), so the
ambiguity is structurally absent. `shukla_tithi_date` therefore takes no
reckoning argument, and must not be generalised to krishna tithis without one.

THE VRIDDHI / KSHAYA DAY-PICK IS COPIED, NOT INVENTED
-----------------------------------------------------
`_pick_day` below reproduces `lunar_observances._observances_for_year`'s two
passes exactly, `_VIDDHA_TITHIS = {10, 25}` included:

  * **vriddhi** — a tithi spanning two consecutive sunrises gives two candidate
    days. Take the FIRST, except for Ekadashi (tithi index 10 or 25), which takes
    the SECOND under the classical *dashami-viddha* rule. That restriction is
    load-bearing and has been shipped wrong here once already: applied as a
    general vriddhi tie-break it silently moved three Purnimas and an Amavasya a
    day late while every count-based check stayed green. See
    `lunar_observances`' "HOW THAT WENT WRONG ONCE" section. **Do not widen
    `_VIDDHA_TITHIS`.**
  * **kshaya** — a tithi that begins after one sunrise and ends before the next,
    so no sunrise falls inside it and the naive scan does not mislabel it, it
    drops it. Assign it to the day it **begins** on. This is not exotic: Drik's
    Devutthana Ekadashi 2026-11-20 is a kshaya Ekadashi.

It is a copy rather than a call because `observances_between()` emits only tithi
indices 10/14/25/29 and attaches no month identity to them, so it cannot express
"Vaishakha Shukla Tritiya" or tell Devshayani from any other of the ~24 Ekadashis
in a year. `scripts/verify_muhurat_tables.py` Gate 4(a) holds the two
implementations in agreement — every Devshayani and Devuthani this module
computes must appear as an `ekadashi-<iso>` slug from `lunar_observances` on the
same day — so the copy cannot drift unnoticed.

KSHAYA MONTH — DEGRADE, DO NOT GUESS
------------------------------------
A kshaya *month* (two sankrantis in one lunation) deletes a month name from the
year entirely. `nija_month()` then returns None and `shukla_tithi_date()` returns
None, and callers treat that as "no such day this year" rather than substituting
a neighbour. `verify_muhurat_tables.py` Gate 3(c) asserts that the only years a
target month fails to resolve are exactly the years `intercalary_months()`
reports a kshaya month of that name, so the exception is proven rather than
allowlisted.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import swisseph as swe

# Private cross-module helpers, imported deliberately — same precedent and same
# reasons as `lunar_observances.py:139-148` and `adhik_maas.py:104-118`. Importing
# `astro_ai.chart` is also what sets the Lahiri sidereal mode process-globally,
# which `adhik_maas._sun_rashi` needs to name a month at all.
from astro_ai.chart import _sunrise_sunset, _tithi_at
from astro_ai import adhik_maas
from astro_ai.lunar_observances import _tithi_index_at_sunrise

_DELHI_LAT = 28.6139
_DELHI_LON = 77.2090
_DELHI_TZ = ZoneInfo("Asia/Kolkata")
_UTC = ZoneInfo("UTC")

# Madhyahna is the third of the day's five equal parts, so it OPENS at
# sunrise + 2/5 of the daylength. Sampling that opening instant — rather than the
# middle of madhyahna, or sunrise — is what distinguishes Akshaya Tritiya 2026
# from 2027; see the module docstring, which works both years through.
_MADHYAHNA_START_FRACTION = 2 / 5

# The only tithi indices the *dashami-viddha* second-day pick applies to: Shukla
# Ekadashi (10) and Krishna Ekadashi (25), 0-based as `chart._tithi_at` returns
# them. Copied from `lunar_observances._VIDDHA_TITHIS`, which carries the
# evidence — five vriddhi Ekadashis read off Drik, all five on the second day,
# against three Purnimas and an Amavasya all on the first. Do NOT add tithis
# here; that regression is invisible to every count-based check.
_VIDDHA_TITHIS = frozenset({10, 25})

# Sampling window for a month's shukla paksha, as day offsets from `month.start`.
# Shukla Pratipada is the month's first day by construction (amanta months open
# at the new moon), so shukla tithis 1..15 occupy roughly days 0..15. -1 gives
# the run/gap detector a sample before the month opens; +20 clears Purnima with
# room for a vriddhi run and for the sampling slack a kshaya tithi needs.
_SAMPLE_BEFORE = 1
_SAMPLE_AFTER = 20


def nija_month(year: int, name: str) -> adhik_maas.LunarMonth | None:
    """The **nija** (true) lunar month called `name` overlapping `year`, or None.

    THE `kind == "nija"` TEST IS THE ENTIRE ADHIK MAAS CORRECTION, and it reads
    like a no-op because in most years there is only one candidate. In an Adhik
    Maas year there are TWO months with the same name — the sankranti-less adhik
    one, which comes first, and the nija one that follows it. Dropping the filter
    silently takes the adhik month, moving every date this module computes back
    by a whole lunar month in exactly the years the almanac is hardest to check.

    Decisive case: 2015 has an Adhik Ashadha. With the filter, Devshayani
    Ekadashi 2015 = 2015-07-27 (Drik, New Delhi). Without it, 2015-06-28 — which
    is Padmini Ekadashi, an observance that exists *only* inside an Adhik Maas.
    `verify_muhurat_tables.py` Gate 1 carries 2015 for this reason and nothing
    else.

    Returns None for a kshaya month — a month name deleted from that year's
    reckoning has no nija occurrence, and inventing one would be a guess.
    """
    for m in adhik_maas.lunar_months(year):
        if m.name == name and m.kind == "nija":
            return m
    return None


def _tithi_index_at_madhyahna(day: date) -> int:
    """Tithi index 0-29 running at the START of madhyahna in New Delhi on `day`.

    Madhyahna opens at sunrise + 2/5 of the daylength. Deliberately NOT the
    middle of madhyahna: sampling the middle moves Akshaya Tritiya 2027 to
    05-08, against Drik's 05-09. See the module docstring.
    """
    sunrise, sunset = _sunrise_sunset(day, _DELHI_LAT, _DELHI_LON, _DELHI_TZ)
    instant = sunrise + (sunset - sunrise) * _MADHYAHNA_START_FRACTION
    ut = instant.astimezone(_UTC)
    jd = swe.julday(
        ut.year, ut.month, ut.day, ut.hour + ut.minute / 60 + ut.second / 3600
    )
    return _tithi_at(jd)[0]


def _pick_day(samples: list[tuple[date, int]], idx: int) -> tuple[date | None, str]:
    """The civil date carrying tithi index `idx`, from consecutive daily samples.

    Returns `(day, mode)` where mode is ``"run"`` (the index was actually sampled
    on some day), ``"gap"`` (it was skipped between two samples — a kshaya tithi)
    or ``"none"``. The mode matters: the madhyahna reckoning treats a gap as "the
    tithi never prevailed at midday" and falls back to sunrise, whereas the
    sunrise reckoning accepts the gap day as the answer.

    Reproduces `lunar_observances._observances_for_year`'s two passes for a
    single target index. `samples` must be one entry per consecutive civil day,
    ascending.
    """
    # Pass 1 — runs. Consecutive days sharing an index are a vriddhi tithi.
    # Purnima/Amavasya/everything else takes the run's FIRST day; Ekadashi takes
    # the SECOND (dashami-viddha). The `idx in _VIDDHA_TITHIS` guard is the whole
    # rule and is NOT redundant — see the module docstring.
    i = 0
    while i < len(samples):
        run_idx = samples[i][1]
        run_end = i
        while run_end + 1 < len(samples) and samples[run_end + 1][1] == run_idx:
            run_end += 1
        if run_idx == idx:
            pick = i
            if run_end > i and idx in _VIDDHA_TITHIS:
                pick = i + 1
            return samples[pick][0], "run"
        i = run_end + 1

    # Pass 2 — gaps. The index never appeared at any sample, so the tithi began
    # after one sample instant and ended before the next: a kshaya tithi under
    # sunrise reckoning. It is observed on the day it begins, i.e. the earlier of
    # the two straddling samples.
    for (day_a, idx_a), (_day_b, idx_b) in zip(samples, samples[1:]):
        skipped = (idx_b - idx_a) % 30
        for step in range(1, skipped):
            if (idx_a + step) % 30 == idx:
                return day_a, "gap"
    return None, "none"


@lru_cache(maxsize=512)
def shukla_tithi_date(
    year: int, month: str, tithi: int, reckoning: str = "sunrise"
) -> date | None:
    """Civil date of shukla tithi `tithi` (1..15) in the nija `month` of `year`.

    e.g. ``shukla_tithi_date(2027, "Ashadha", 11)`` -> Devshayani Ekadashi 2027,
    and ``shukla_tithi_date(2026, "Vaishakha", 3, "madhyahna")`` -> Akshaya
    Tritiya 2026.

    `reckoning` is ``"sunrise"`` (the default, and correct for the Ekadashi
    fasts) or ``"madhyahna"`` (correct for the midday-reckoned observances —
    Akshaya Tritiya, Vasant Panchami). Picking the wrong one moves the date by a
    day in roughly one year in three; see the module docstring for the two
    Akshaya Tritiya cases that pin the rule down.

    Returns None when the month does not exist in that year (kshaya month) or
    when the tithi cannot be located in the sample window. Callers degrade rather
    than guessing; nothing here raises on an ordinary miss.

    Cached per (year, month, tithi, reckoning): a 365-day muhurat scan asks for
    the same handful of dates once per candidate day, and each miss costs ~22
    sunrise + tithi computations on top of a month enumeration.
    """
    if not 1 <= tithi <= 15:
        raise ValueError(f"shukla tithi must be 1..15, got {tithi}")
    if reckoning not in ("sunrise", "madhyahna"):
        raise ValueError(f"reckoning must be 'sunrise' or 'madhyahna', got {reckoning!r}")

    m = nija_month(year, month)
    if m is None:
        return None

    # `_tithi_at` is 0-based (0 = Shukla Pratipada .. 29 = Amavasya), while the
    # classical tithi number is 1-based. Shukla N -> index N-1.
    idx = tithi - 1

    start = m.start - timedelta(days=_SAMPLE_BEFORE)
    end = m.start + timedelta(days=_SAMPLE_AFTER)
    # The window must cover the whole shukla paksha with slack at both ends, or
    # `_pick_day`'s gap detector could report a kshaya tithi at a sample edge that
    # is really just the window running out.
    assert (end - start).days >= 20, "sample window too short to cover shukla paksha"

    days: list[date] = []
    day = start
    while day <= end:
        days.append(day)
        day += timedelta(days=1)

    sunrise_pick, _mode = _pick_day([(d, _tithi_index_at_sunrise(d)) for d in days], idx)
    if reckoning == "sunrise":
        return sunrise_pick

    # Madhyahna reckoning. A "run" means the tithi genuinely prevailed at the
    # opening of madhyahna on some day, and that day is the answer even when it
    # is not the sunrise day (Akshaya Tritiya 2026). A "gap" means it prevailed
    # at midday on NO day, and the observance falls back to the ordinary
    # sunrise-reckoned day (Akshaya Tritiya 2027) — NOT to the earlier day of the
    # gap, which is what the sunrise rule would do and which is wrong here.
    madhyahna_pick, mode = _pick_day(
        [(d, _tithi_index_at_madhyahna(d)) for d in days], idx
    )
    if mode == "run":
        return madhyahna_pick
    return sunrise_pick
