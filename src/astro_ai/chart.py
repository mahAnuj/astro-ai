"""Compute a Vedic birth chart from form-supplied birth details.

Pipeline:
    place name --geopy/Nominatim--> (lat, lon)
              --timezonefinder--> tz name
              --zoneinfo--> birth datetime in UTC
              --pyswisseph--> planetary longitudes, Ascendant, nakshatra

Defaults reflect Indian Vedic convention:
- Sidereal zodiac with Lahiri ayanamsa (most widely used in India)
- Whole Sign houses (classical Parashari standard)
- 9 grahas: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu
  (mean nodes for Rahu/Ketu — the smoother classical choice; true nodes
  are more astronomically literal but introduce wobble)

The output is a `Chart` dataclass that renders to a string via `format_for_prompt`.
That string is what gets handed to the LLM as user-message context.
"""

from __future__ import annotations

from typing import Final

import threading
from dataclasses import dataclass
from datetime import date as date_, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import swisseph as swe

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RASHIS = [
    "Aries (Mesha)", "Taurus (Vrishabha)", "Gemini (Mithuna)", "Cancer (Karka)",
    "Leo (Simha)", "Virgo (Kanya)", "Libra (Tula)", "Scorpio (Vrishchika)",
    "Sagittarius (Dhanu)", "Capricorn (Makara)", "Aquarius (Kumbha)", "Pisces (Meena)",
]

# 3-letter codes for the diamond-chart corner labels.
RASHI_SHORT = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir",
               "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]

# Unicode zodiac glyphs — universal visual shorthand for each rashi.
# Same 12 symbols Western astrology uses; Vedic users recognise them too.
RASHI_SYMBOLS: tuple[str, ...] = (
    "♈︎",  # ♈︎ Aries
    "♉︎",  # ♉︎ Taurus
    "♊︎",  # ♊︎ Gemini
    "♋︎",  # ♋︎ Cancer
    "♌︎",  # ♌︎ Leo
    "♍︎",  # ♍︎ Virgo
    "♎︎",  # ♎︎ Libra
    "♏︎",  # ♏︎ Scorpio
    "♐︎",  # ♐︎ Sagittarius
    "♑︎",  # ♑︎ Capricorn
    "♒︎",  # ♒︎ Aquarius
    "♓︎",  # ♓︎ Pisces
)

# Synonyms for fuzzy-matching section titles back to a rashi index.
# Each tuple covers English + Sanskrit names (lowercased) for one rashi.
_RASHI_NAME_TOKENS: tuple[tuple[str, ...], ...] = (
    ("aries", "mesha"),
    ("taurus", "vrishabha"),
    ("gemini", "mithuna", "mithun"),
    ("cancer", "karka"),
    ("leo", "simha", "sinh"),
    ("virgo", "kanya"),
    ("libra", "tula"),
    ("scorpio", "vrishchika", "vrischika"),
    ("sagittarius", "dhanu"),
    ("capricorn", "makara", "makar"),
    ("aquarius", "kumbha", "kumbh"),
    ("pisces", "meena", "min"),
)


def symbol_for_rashi_label(label: str) -> str | None:
    """Return the Unicode glyph for a rashi label like 'Cancer', 'Karka', or
    'Cancer (Karka)' or 'Aries / Mesha'. Returns None if no match.
    """
    if not label:
        return None
    lower = label.lower()
    for i, tokens in enumerate(_RASHI_NAME_TOKENS):
        if any(t in lower for t in tokens):
            return RASHI_SYMBOLS[i]
    return None

# Rashi (0..11 = Aries..Pisces) → ruling planet. Used by house-profile
# computation and by matching.py's Graha Maitri scoring.
RASHI_LORDS: tuple[str, ...] = (
    "Mars",     # Aries (Mesha)
    "Venus",    # Taurus (Vrishabha)
    "Mercury",  # Gemini (Mithuna)
    "Moon",     # Cancer (Karka)
    "Sun",      # Leo (Simha)
    "Mercury",  # Virgo (Kanya)
    "Venus",    # Libra (Tula)
    "Mars",     # Scorpio (Vrishchika)
    "Jupiter",  # Sagittarius (Dhanu)
    "Saturn",   # Capricorn (Makara)
    "Saturn",   # Aquarius (Kumbha)
    "Jupiter",  # Pisces (Meena)
)

# 2-letter Vedic graha codes for cell-interior labels.
PLANET_SHORT = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}

# North Indian diamond chart positions in a 400x400 viewBox. For each house:
# (sign_x, sign_y) places the small rashi number near the cell's outer edge;
# (planet_cx, planet_cy) is the starting point for the planet-label stack
# (planets after the first stack downward by ~13px line-height).
DIAMOND_POSITIONS: dict[int, dict[str, int]] = {
    1:  {"sign_x": 200, "sign_y": 22,  "planet_cx": 200, "planet_cy": 95},
    2:  {"sign_x":  95, "sign_y": 18,  "planet_cx": 100, "planet_cy": 50},
    3:  {"sign_x":  18, "sign_y": 95,  "planet_cx":  55, "planet_cy": 105},
    4:  {"sign_x":  18, "sign_y": 200, "planet_cx": 100, "planet_cy": 205},
    5:  {"sign_x":  18, "sign_y": 305, "planet_cx":  55, "planet_cy": 305},
    6:  {"sign_x":  95, "sign_y": 388, "planet_cx": 100, "planet_cy": 360},
    7:  {"sign_x": 200, "sign_y": 385, "planet_cx": 200, "planet_cy": 280},
    8:  {"sign_x": 305, "sign_y": 388, "planet_cx": 300, "planet_cy": 360},
    9:  {"sign_x": 388, "sign_y": 305, "planet_cx": 345, "planet_cy": 305},
    10: {"sign_x": 388, "sign_y": 200, "planet_cx": 300, "planet_cy": 205},
    11: {"sign_x": 388, "sign_y":  95, "planet_cx": 345, "planet_cy": 105},
    12: {"sign_x": 305, "sign_y":  18, "planet_cx": 300, "planet_cy": 50},
}

# 27 nakshatras, each spanning 360/27 = 13°20' of the sidereal zodiac.
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]

# pyswisseph planet IDs. SE_TRUE_NODE = Rahu's true (oscillating) position;
# Ketu = Rahu + 180°. Most Indian astrology software (Future Point, JHora,
# Parashar's Light) uses true node; mean node smooths out the oscillation
# and produces values ~20 arc-minutes off the true position.
PLANETS: list[tuple[str, int]] = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mars", swe.MARS),
    ("Mercury", swe.MERCURY),
    ("Jupiter", swe.JUPITER),
    ("Venus", swe.VENUS),
    ("Saturn", swe.SATURN),
    ("Rahu", swe.TRUE_NODE),
]

# geopy and timezonefinder are imported lazily. timezonefinder pulls in the h3
# native extension plus numpy, which costs ~5.5s of first-touch disk I/O on a
# cold Cloud Run container whose image layers stream on demand. Only geocoding
# needs them, so routes that never geocode should never pay for them. The
# singletons are also expensive to construct (TimezoneFinder ~0.2s), hence the
# memoisation into module globals.
_GEOCODER = None
_TF = None
_GEO_LOCK = threading.Lock()


def _geocoder():
    """Nominatim client, constructed on first use."""
    global _GEOCODER
    if _GEOCODER is None:
        with _GEO_LOCK:
            if _GEOCODER is None:
                from geopy.geocoders import Nominatim

                # user_agent identifies us to Nominatim — do not change it
                # casually; unrecognised agents get rate-limited.
                _GEOCODER = Nominatim(
                    user_agent="shubh-bhagya/1.0 (contact@shubhagya.com)"
                )
    return _GEOCODER


def _tf():
    """TimezoneFinder instance, constructed on first use."""
    global _TF
    if _TF is None:
        with _GEO_LOCK:
            if _TF is None:
                from timezonefinder import TimezoneFinder

                _TF = TimezoneFinder()
    return _TF

# Configure Swiss Ephemeris for Vedic/sidereal mode with Lahiri ayanamsa.
# This is process-global state — set once at module import.
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanetPosition:
    """One graha in its computed sign + house, with nakshatra and retrograde state."""

    name: str
    rashi: str          # sidereal sign
    house: int          # 1..12 (Whole Sign relative to Lagna)
    longitude: float    # sidereal degrees within the sign (0..30)
    nakshatra: str      # 27-fold lunar mansion based on absolute longitude
    retrograde: bool    # vakri — Sun/Moon never; Rahu/Ketu always (Vedic convention)
    # Quarter of the nakshatra, 1-4 (#209). Each nakshatra spans 13 deg 20',
    # divided into four padas of 3 deg 20'. Added because /kundli's landing
    # copy, its meta description and its JSON-LD all advertised "planetary
    # positions in nakshatra padas" while nothing computed one — the field
    # did not exist. Implemented rather than deleting the claim: the
    # arithmetic is one division and the pada is what maps a planet into the
    # Navamsha, so it is genuinely useful rather than decorative.
    #
    # Defaulted so the four existing construction sites keep working, but
    # every one of them now passes it explicitly.
    pada: int = 0


@dataclass(frozen=True)
class HouseSlot:
    """One of the 12 houses in the Lagna chart, grouped for diamond-chart rendering."""

    house: int          # 1..12
    sign_num: int       # 1..12 (Aries..Pisces); the rashi occupying this house
    sign_short: str     # e.g. "Sco" — terse label for the diamond corner
    planets: list[tuple[str, int, bool]]  # (abbr, integer degree, retrograde) tuples


@dataclass(frozen=True)
class Chart:
    """A computed Vedic birth chart, ready for prompt formatting."""

    lagna_rashi: str
    lagna_longitude: float
    planets: list[PlanetPosition]
    birth_lat: float
    birth_lon: float
    birth_tz: str
    birth_utc: datetime

    def diamond_chart(self) -> list[dict[str, object]]:
        """Render-ready data for the North Indian diamond Lagna chart SVG.

        Each entry has the cell's SVG placement coordinates plus the rashi
        number, short rashi label, and the planets occupying that house.
        Template iterates this and emits one block of SVG text per house.
        """
        summary_map = {s.house: s for s in self.house_summary()}
        return [
            {
                **DIAMOND_POSITIONS[h],
                "house": h,
                "sign_num": summary_map[h].sign_num,
                "sign_short": summary_map[h].sign_short,
                "planets": summary_map[h].planets,
            }
            for h in range(1, 13)
        ]

    def south_indian_chart(self) -> list[dict[str, object]]:
        """Render-ready data for the South Indian square (chatuska) Lagna chart.

        Different convention from North Indian:
          - Rashis are FIXED in a 4x4 grid border (Pisces top-left, clockwise).
            Meena(12) | Mesha(1)     | Vrishabha(2) | Mithuna(3)
            Kumbha(11)| (middle 2x2  )               | Karka(4)
            Makara(10)| (empty area )                | Simha(5)
            Dhanu(9)  | Vrishchika(8)| Tula(7)      | Kanya(6)
          - Houses ROTATE: the "1st house" is wherever the Lagna rashi's
            cell is; count clockwise from there for 2, 3, 4 ...
          - Each cell always shows the same rashi; planets appear in whichever
            cell corresponds to their rashi.

        This is the standard convention in Tamil Nadu / Karnataka / Andhra /
        Kerala / Telangana and matches most Sanskrit classical texts.
        """
        # Cells laid out per convention above.  (col, row) indexed 0..3.
        # rashi_num is 1-based (1=Mesha/Aries ... 12=Meena/Pisces).
        _CELLS = [
            (0, 0, 12),  # Pisces (Meena) top-left
            (1, 0, 1),   # Aries (Mesha)
            (2, 0, 2),   # Taurus (Vrishabha)
            (3, 0, 3),   # Gemini (Mithuna) top-right
            (3, 1, 4),   # Cancer (Karka)
            (3, 2, 5),   # Leo (Simha)
            (3, 3, 6),   # Virgo (Kanya) bottom-right
            (2, 3, 7),   # Libra (Tula)
            (1, 3, 8),   # Scorpio (Vrishchika)
            (0, 3, 9),   # Sagittarius (Dhanu) bottom-left
            (0, 2, 10),  # Capricorn (Makara)
            (0, 1, 11),  # Aquarius (Kumbha)
        ]
        lagna_sign_num = _rashi_index(self.lagna_rashi) + 1  # 1..12
        # Group planets by rashi_num (1..12) for O(1) cell lookup below.
        per_rashi: dict[int, list[tuple[str, int, bool]]] = {n: [] for n in range(1, 13)}
        for p in self.planets:
            per_rashi[_rashi_index(p.rashi) + 1].append(
                (PLANET_SHORT[p.name], int(round(p.longitude)), p.retrograde)
            )
        # House number of a given cell: 1 for the Lagna cell, then count
        # clockwise around the border.  Precompute a mapping rashi -> house.
        rashi_to_house: dict[int, int] = {}
        # Walk the cells in canonical order starting from Mesha and count
        # forward from wherever the lagna is.
        for i, (_, _, rashi_num) in enumerate(_CELLS):
            house = ((rashi_num - lagna_sign_num) % 12) + 1
            rashi_to_house[rashi_num] = house
        return [
            {
                "col": col,
                "row": row,
                "rashi_num": rashi_num,
                "rashi_short": RASHI_SHORT[rashi_num - 1],
                "house": rashi_to_house[rashi_num],
                "is_lagna": rashi_num == lagna_sign_num,
                "planets": per_rashi[rashi_num],
            }
            for col, row, rashi_num in _CELLS
        ]

    def house_summary(self) -> list[HouseSlot]:
        """Group planets by house and resolve each house's rashi.

        Used by the diamond-chart SVG renderer in the result template. Returns
        a fixed list of 12 HouseSlot entries in house order (1..12).
        """
        lagna_sign_idx = _rashi_index(self.lagna_rashi)
        slots = [
            HouseSlot(
                house=h,
                sign_num=((lagna_sign_idx + (h - 1)) % 12) + 1,
                sign_short=RASHI_SHORT[(lagna_sign_idx + (h - 1)) % 12],
                planets=[],
            )
            for h in range(1, 13)
        ]
        # HouseSlot is frozen — rebuild with mutated planets list at the end.
        per_house: dict[int, list[tuple[str, int, bool]]] = {h: [] for h in range(1, 13)}
        for p in self.planets:
            per_house[p.house].append(
                (PLANET_SHORT[p.name], int(round(p.longitude)), p.retrograde)
            )
        return [
            HouseSlot(
                house=s.house,
                sign_num=s.sign_num,
                sign_short=s.sign_short,
                planets=per_house[s.house],
            )
            for s in slots
        ]


class ChartError(ValueError):
    """Raised when the chart can't be computed — bad place name, bad date, etc."""


# ---------------------------------------------------------------------------
# Geocoding + timezone
# ---------------------------------------------------------------------------


@lru_cache(maxsize=512)
def geocode_place(place: str) -> tuple[float, float, str]:
    """Resolve a free-text place into (lat, lon, tz_name).

    Uses Nominatim (OpenStreetMap, free). Raises ChartError on miss.

    Cached on the exact input string — no normalisation, so two spellings of
    the same city are two entries. lru_cache does not memoise a call that
    raises, which is what we want here: a transient Nominatim outage must not
    turn into a permanently cached failure for that place.
    """
    try:
        location = _geocoder().geocode(place, timeout=10)
    except Exception as err:
        raise ChartError(f"Geocoding failed for {place!r}: {err}") from err
    if location is None:
        raise ChartError(
            f"Couldn't find the place {place!r}. Try a more specific form like "
            "'Mumbai, India' or 'Brooklyn, New York, USA'."
        )
    lat, lon = float(location.latitude), float(location.longitude)
    tz = _tf().timezone_at(lat=lat, lng=lon)
    if tz is None:
        raise ChartError(
            f"Found {place!r} at ({lat:.3f}, {lon:.3f}) but couldn't determine "
            "its timezone. Pick a nearby major city instead."
        )
    return lat, lon, tz


# ---------------------------------------------------------------------------
# Chart calculation
# ---------------------------------------------------------------------------


def compute_chart(birth_date: str, birth_time: str, place: str) -> Chart:
    """End-to-end: form fields → fully computed sidereal chart.

    birth_date: ISO "YYYY-MM-DD"; birth_time: 24h "HH:MM"; place: free text.
    Raises ChartError on geocoding failure, bad date/time format, etc.
    """
    lat, lon, tz_name = geocode_place(place)
    local_dt = _parse_local_datetime(birth_date, birth_time, tz_name)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

    julian_day = swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600,
    )

    # Ascendant + cusps via Whole Sign houses ('W' = whole-sign in pyswisseph).
    _, ascmc = swe.houses_ex(julian_day, lat, lon, b"W", swe.FLG_SIDEREAL)
    asc_long = float(ascmc[0])  # sidereal ascendant longitude
    lagna_sign_idx = int(asc_long // 30)
    lagna_rashi = RASHIS[lagna_sign_idx]

    planets = _compute_planet_positions(julian_day, lagna_sign_idx)

    return Chart(
        lagna_rashi=lagna_rashi,
        lagna_longitude=asc_long - lagna_sign_idx * 30,
        planets=planets,
        birth_lat=lat,
        birth_lon=lon,
        birth_tz=tz_name,
        birth_utc=utc_dt,
    )


# ---------------------------------------------------------------------------
# Transit snapshot — current planetary positions vs natal Lagna
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitSnapshot:
    """Today's planetary positions evaluated against a natal Lagna.

    Houses on each PlanetPosition are computed RELATIVE TO THE NATAL LAGNA
    (not the rising sign at the moment of computation). That's what Vedic
    transit interpretation actually wants — "Saturn is transiting your
    natal 4th house" is the meaningful statement, not "what's rising now".
    """

    moment: datetime  # UTC
    natal_lagna_rashi: str
    planets: list[PlanetPosition]


def compute_transit_snapshot(
    natal_chart: Chart,
    when: datetime | None = None,
) -> TransitSnapshot:
    """Compute today's transit positions, with houses measured from the natal Lagna."""
    moment = (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))
    julian_day = swe.julday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour + moment.minute / 60 + moment.second / 3600,
    )
    natal_lagna_idx = _rashi_index(natal_chart.lagna_rashi)
    planets = _compute_planet_positions(julian_day, natal_lagna_idx)
    return TransitSnapshot(
        moment=moment,
        natal_lagna_rashi=natal_chart.lagna_rashi,
        planets=planets,
    )


#: The reference place every Rashifal is computed at. A Rashifal is written for
#: a rashi, not a person, so there is no birthplace to use -- this is the
#: neutral stand-in the whole surface already shared by convention.
RASHIFAL_REFERENCE_PLACE = "Mumbai, India"

#: Its timezone, as a constant rather than read off a Chart. The pin must be a
#: pure function of the DATE: two callers holding differently-built charts for
#: the same reference place would otherwise be able to pin differently, which
#: is the bug this whole mechanism exists to remove.
RASHIFAL_REFERENCE_TZ = "Asia/Kolkata"


def rashifal_day_moment(day: date_) -> datetime:
    """Local NOON on `day` at the reference place -- the moment a Rashifal means.

    WHY A PINNED MOMENT, AND WHY THIS IS NOT COSMETIC
    -------------------------------------------------
    A Rashifal is a statement about a CALENDAR DAY, and every artefact of that
    day has to be computed from one moment or they disagree with each other.
    Before this, each caller passed no `when` and got `datetime.now()`, so:

      * `routes/rashifal.py` computed the panel's counts at render time while
        the reading beside them had been generated (and cached for the day)
        at some earlier hour. QA measured the two disagreeing on 9 of 90 days,
        with the area counts moving for 10 of 12 rashis on 2026-10-31.
      * worse, and not what QA tested: the nightly job (#515) generates every
        reading at ~03:30 IST and the page renders it all day, so under
        `now()` the panel and the published prose would diverge by DESIGN
        rather than occasionally.

    Pinning makes the agreement structural -- any process, at any hour, asking
    for a given day gets the same sky -- which is what `_day_detail_today`
    already claimed and could not deliver.

    LOCAL NOON, following the convention already in the tree: `routes/panchang`
    pins a named date the same way (`_target_moment`, local noon in the chart's
    own tz). Noon is also the safe choice for a date: it cannot land on the
    previous or next calendar day under any timezone offset, which an hour near
    midnight can.

    NOT sunrise, though sunrise is the classical day boundary and
    `compute_panchang` uses it for the tithi. Sunrise is location-dependent and
    can be absent entirely at polar latitudes (`DailyPanchang.daylight_ordinary`
    exists for exactly that), so it would make a Rashifal's own transit fail on
    dates where the panchang already degrades. The tithi keeps its sunrise
    convention; this pins the GOCHARA, which has no classical clock.

    EVERY Rashifal call site must pass this as `when=`:

        compute_transit_snapshot(natal, when=rashifal_day_moment(day))

    There is deliberately no wrapper that does both. The call sites are stubbed
    in tests by patching `compute_transit_snapshot` where it is imported, and a
    wrapper calling it internally would route around that seam. The guarantee
    does not need a wrapper anyway: this function is a pure function of the
    date, so two callers that both pass it agree by construction.
    The guard is the spy block in `tests/test_rashifal_day_detail.py`
    (`test_the_panel_helpers_*`, `test_the_reading_path_*`, `test_the_morning_blast_*`,
    `test_the_warm_job_*`, `test_the_welcome_email_*`, `test_the_nightly_brief_*`): each
    drives one path and fails if the `when` reaching `compute_transit_snapshot` is not
    this function's value. A NEW call site is not covered until it gets a test there --
    grep `compute_transit_snapshot(` when adding one.
    """
    tz = ZoneInfo(RASHIFAL_REFERENCE_TZ)
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=tz)


# ---------------------------------------------------------------------------
# Vedic dosha flags — Mangal Dosh + Sade Sati
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VedicFlags:
    """Computed yes/no dosha flags used to ground the LLM reading in classical facts.

    These are deterministic from the chart + current date — not opinions. The LLM
    should reference them by name when present rather than hedging or inventing.
    """

    manglik: bool
    manglik_reasons: tuple[str, ...]  # e.g. ("Mars in 7th house from Lagna",)
    sade_sati: bool
    sade_sati_phase: str | None        # "rising" | "peak" | "setting"
    saturn_house_from_natal_moon: int  # 1..12 — useful even when not Sade Sati
    # Additional Saturn-transit conditions that are distinct from Sade Sati
    # but often confused with it. Per knowledge/vedic_reference.md §2.5:
    ashtama_shani: bool = False        # Saturn in 8th from natal Moon (~2.5y)
    kantaka_shani: bool = False        # Saturn in 4th from natal Moon (~2.5y)
    # THE carrier of everything Manglik. `manglik` and `manglik_reasons` above
    # are convenience projections of this object, never independently computed:
    #     manglik         == manglik_details.is_manglik
    #     manglik_reasons == manglik_details.axis_reasons
    # There is deliberately no `manglik_status` field — the status lives on
    # `manglik_details.effective_status` and nowhere else, because a third copy
    # of the same fact is exactly what issues #176/#165/#166 were about.
    # scripts/verify_manglik_coherence.py enforces the invariants above.
    manglik_details: "ManglikDetails | None" = None


def compute_vedic_flags(natal: Chart, when: datetime | None = None) -> VedicFlags:
    """Compute Mangal Dosh (natal) + Sade Sati (uses current Saturn transit)."""
    moment = (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))
    julian_day = swe.julday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour + moment.minute / 60 + moment.second / 3600,
    )

    moon = next(p for p in natal.planets if p.name == "Moon")
    moon_idx = _rashi_index(moon.rashi)

    # MANGAL DOSH — delegated wholesale to compute_manglik_details(), which is
    # the only Manglik engine in this codebase. It checks all three classical
    # axes (Lagna, Moon, Venus per §1.1) and applies the cancellation catalogue
    # (§1.3); the inline two-axis, no-cancellation version that used to live
    # here disagreed with it on 12.5% of charts and told seekers a different
    # answer in the reading than /manglik-check showed them.
    details = compute_manglik_details(natal)

    # SADE SATI — Saturn currently transiting 12th, 1st, or 2nd house from natal Moon.
    saturn_pos, _ = swe.calc_ut(julian_day, swe.SATURN, swe.FLG_SIDEREAL)
    saturn_sign_now = int(float(saturn_pos[0]) // 30)
    saturn_house_from_moon = ((saturn_sign_now - moon_idx) % 12) + 1
    sade_sati_phase: str | None = None
    if saturn_house_from_moon == 12:
        sade_sati_phase = "rising"
    elif saturn_house_from_moon == 1:
        sade_sati_phase = "peak"
    elif saturn_house_from_moon == 2:
        sade_sati_phase = "setting"

    return VedicFlags(
        manglik=details.is_manglik,
        manglik_reasons=details.axis_reasons,
        manglik_details=details,
        sade_sati=sade_sati_phase is not None,
        sade_sati_phase=sade_sati_phase,
        saturn_house_from_natal_moon=saturn_house_from_moon,
        # Ashtama Shani (Saturn 8th from Moon) and Kantaka Shani (4th) are
        # distinct ~2.5y Saturn transits that classical texts flag alongside
        # Sade Sati. Previously the /sade-sati-check would silently report
        # "no Sade Sati" for users in these phases, leaving them unaware.
        ashtama_shani=(saturn_house_from_moon == 8),
        kantaka_shani=(saturn_house_from_moon == 4),
    )


# The one and only way a prompt is allowed to state a Manglik verdict.
# EXACTLY ONE line in any assembled user message may start with this prefix —
# format_flags_for_prompt() emits it, and nothing else may. In particular
# format_manglik_for_prompt() supplies evidence and phrasing guidance only, and
# asserts nothing. scripts/verify_manglik_coherence.py counts occurrences of
# this prefix per assembled message and fails on anything other than one.
MANGLIK_ASSERTION_PREFIX = "- Manglik (Mangal Dosh):"


def format_flags_for_prompt(flags: VedicFlags) -> str:
    """Plain-English flag block appended to the LLM user message.

    Carries the single Manglik assertion for the whole prompt — see
    MANGLIK_ASSERTION_PREFIX. Wordings per knowledge/vedic_reference.md §1.4's
    three rungs (cancelled / mitigated / present), which also ban the
    colloquial "Angshik Manglik" label (§1.2, §1.3 F).
    """
    lines = ["Vedic flags (deterministic, do not contradict):"]
    details = flags.manglik_details
    # A hand-built VedicFlags may carry no details (the field is defaulted);
    # treat that as "nothing to assert" rather than crashing a prompt.
    status = details.effective_status if details is not None else "none"
    axes = "; ".join(flags.manglik_reasons)
    if status == "cancelled":
        rules = "; ".join(
            r.description for r in details.cancellations if r.effect == "cancels"
        )
        # compute_manglik_details only reaches "cancelled" when a §1.3 rule with
        # effect="cancels" fired, so `rules` is non-empty on every computed chart.
        # A hand-built ManglikDetails could break that, and "Cancelled by: ." is
        # worse than no clause at all — so never emit the clause without content.
        cause = (
            f"Cancelled by: {rules}. " if rules
            else "No specific cancellation reason is recorded for this chart. "
        )
        lines.append(
            f"{MANGLIK_ASSERTION_PREFIX} PRESENT BUT CANCELLED — {axes}. "
            f"{cause}Say the dosha is technically present but cancelled, "
            "and that it should not be treated as an obstacle to marriage. Never call this "
            'chart Manglik without the word "cancelled" in the same sentence. Do not say it '
            'is uncancelled, partial, or "Angshik".'
        )
    elif status == "mitigated":
        rules = "; ".join(
            r.description for r in details.cancellations if r.effect == "mitigates"
        )
        # "mitigated" has two causes and only one of them names a rule: either a
        # §1.3 mitigation fired, or compute_manglik_details capped a Venus-axis-only
        # chart down from "present" with no rule involved. In the second case
        # `rules` is empty and "Softened by: ." both dangles and contradicts the
        # evidence block, which correctly reports that no classical rule applies.
        if rules:
            cause = f"Softened by: {rules}. "
        elif details.venus_axis_only:
            cause = (
                "No classical cancellation or mitigation rule applies here — the reduction "
                "comes from the axis: Mars is not in a Manglik house from the Lagna or from "
                "the Moon, only from Venus. We treat a Venus-axis-only (Kuja-Shukra) chart "
                "as a supplementary, marriage-specific indicator rather than a full Mangal "
                "Dosha, so its weight is reduced. "
            )
        else:
            cause = "No specific softening reason is recorded for this chart. "
        lines.append(
            f"{MANGLIK_ASSERTION_PREFIX} PRESENT BUT REDUCED — {axes}. "
            f"{cause}Say the dosha is present and its effect is reduced. "
            'Do NOT say it is cancelled or absent. Do not use the term "Angshik Manglik".'
        )
    elif status == "present":
        lines.append(
            f"{MANGLIK_ASSERTION_PREFIX} PRESENT, NOT CANCELLED — {axes}. "
            "No classical cancellation or mitigation applies. Address this in the "
            "Relationships section as something to be aware of, not as destiny. "
            "Do not predict marital failure."
        )
    else:
        lines.append(
            f"{MANGLIK_ASSERTION_PREFIX} NO — Mars is not in the 1st, 2nd, 4th, 7th, 8th "
            "or 12th house from Lagna, from the Moon, or from Venus. Do not raise Mangal "
            "Dosha in this reading at all."
        )
    if flags.sade_sati:
        phase_text = {
            "rising": "rising phase — Saturn transiting 12th from natal Moon",
            "peak": "peak phase (madhya) — Saturn transiting natal Moon's own sign (1st from Moon)",
            "setting": "setting phase — Saturn transiting 2nd from natal Moon",
        }[flags.sade_sati_phase or ""]
        lines.append(
            f"- Sade Sati: YES, currently in {phase_text}. "
            "Address this directly in the Health & Wellbeing section."
        )
    else:
        lines.append(
            f"- Sade Sati: NO (Saturn currently transiting {_ordinal(flags.saturn_house_from_natal_moon)} "
            "house from natal Moon)"
        )
    if flags.ashtama_shani:
        lines.append(
            "- Ashtama Shani: YES — Saturn transiting 8th from natal Moon (~2.5y). "
            "Health, hidden losses, transformation themes. Address in Health & Wellbeing."
        )
    if flags.kantaka_shani:
        lines.append(
            "- Kantaka Shani: YES — Saturn transiting 4th from natal Moon (~2.5y). "
            "Home, mother, inner peace themes. Address in Family / Wellbeing."
        )
    return "\n".join(lines)


def _ordinal(n: int) -> str:
    """1 → '1st', 22 → '22nd', etc."""
    suffix = "th" if 11 <= (n % 100) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# Structured insight panels — Sade Sati, Manglik, Marriage, Wealth
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HouseProfile:
    """Snapshot of one house: its rashi, ruling planet, and any natal occupants.

    Used as the building block for the Marriage panel (7th), Wealth panel
    (2nd + 11th), and future house-centric panels.
    """

    number: int                   # 1..12
    sign: str                     # e.g. "Cancer (Karka)"
    sign_idx: int                 # 0..11
    lord: str                     # planet ruling the sign
    planets: tuple[str, ...]      # planets occupying this house


def house_profile(chart: Chart, house: int) -> HouseProfile:
    """Compute a HouseProfile for the Nth house (1-indexed) of `chart`."""
    lagna_idx = _rashi_index(chart.lagna_rashi)
    sign_idx = (lagna_idx + house - 1) % 12
    occupants = tuple(p.name for p in chart.planets if p.house == house)
    return HouseProfile(
        number=house,
        sign=RASHIS[sign_idx],
        sign_idx=sign_idx,
        lord=RASHI_LORDS[sign_idx],
        planets=occupants,
    )


@dataclass(frozen=True)
class ManglikRule:
    """One classical Mangal Dosha cancellation or mitigation that applies to this chart.

    `source` is what result.html prints beside the rule, so the seeker can
    check the claim rather than take the cancellation on our authority.

    It does NOT reach the LLM. This docstring used to say it "lets the LLM
    cite specific texts", which was never true of the shipped code:
    format_manglik_for_prompt() sends `description` only and says in its own
    docstring that sources are omitted so the model cannot echo them back as
    "per Phaladeepika" jargon. The claim survived long enough to be believed
    (#218) — a source string is a page string, and a wrong one is a wrong
    page, not a wrong prompt.
    """

    slug: str          # stable id for code paths / tests
    description: str   # human-readable rule
    effect: str        # "cancels" | "mitigates"
    source: str        # citation shown to the reader; see the note above


@dataclass(frozen=True)
class ManglikDetails:
    """Manglik (Mangal Dosh) — fuller than VedicFlags so we can render an explanatory panel.

    Raw mathematical flag (`is_manglik`) is augmented with cancellation /
    mitigation rules from classical practice. `effective_status` summarises
    what to actually tell the seeker. See knowledge/vedic_reference.md §1.3
    for the rule catalogue + classical citations.
    """

    is_manglik: bool
    houses: tuple[int, ...]                 # all qualifying Mars houses (1/2/4/7/8/12 from Lagna, Moon or Venus)
    primary_house: int                      # most-severe house (or 0 if not manglik)
    severity: str                           # "high" | "moderate" | "low" | "none"
    cancellations: tuple[ManglikRule, ...]  # all cancellation / mitigation rules that fired
    effective_status: str                   # "none" | "present" | "mitigated" | "cancelled"
    # Appended last with defaults so positional construction keeps working.
    # Human-readable reason per qualifying axis, in the order Lagna, Moon, Venus —
    # e.g. ("Mars in 7th house from Lagna", "Mars in 4th house from Venus").
    # Empty when the chart does not qualify on any axis.
    axis_reasons: tuple[str, ...] = ()
    # True when ONLY the Venus axis fired (pure Kuja-Shukra Manglik, the weaker
    # marriage-specific indicator) — neither Lagna nor Moon qualified.
    venus_axis_only: bool = False


EFFECTIVELY_MANGLIK_STATUSES: frozenset[str] = frozenset({"present", "mitigated"})


def is_effectively_manglik(status: str) -> bool:
    """The single definition of "does this chart count as Manglik?".

    Per knowledge/vedic_reference.md §1.3: "Each rule is tagged **cancels**
    (dosha is fully nullified) or **mitigates** (effect is softened, not
    removed)." Softened-not-removed still bites, so a `mitigated` chart is
    still effectively Manglik and must be told so.

    `present` and `mitigated` are True; `cancelled` and `none` are False.
    Every "is this chart Manglik" test in the codebase goes through here —
    do not re-test `effective_status` against string literals anywhere else.
    """
    return status in EFFECTIVELY_MANGLIK_STATUSES


def _jupiter_aspects(jupiter_house: int, target_house: int) -> bool:
    """Jupiter's 5/7/9 graha drishti — true if Jupiter aspects the target house."""
    delta = (target_house - jupiter_house) % 12
    return delta in {4, 6, 8}   # +4 = 5th aspect, +6 = 7th, +8 = 9th


def _manglik_cancellations(chart: Chart) -> tuple[ManglikRule, ...]:
    """All classical cancellation/mitigation rules that apply to this chart's Mars.

    Compiled from Jataka Parijata, Phaladeepika, Jataka Chandrika, and Muhurtha
    Chintamani via P.V.R. Narasimha Rao's Jagannath Hora rule-set. See
    knowledge/vedic_reference.md §1.3 for the full citation list — keep that
    file and this function in sync when adding new rules.
    """
    mars = next(p for p in chart.planets if p.name == "Mars")
    jupiter = next(p for p in chart.planets if p.name == "Jupiter")
    venus = next(p for p in chart.planets if p.name == "Venus")
    sun = next(p for p in chart.planets if p.name == "Sun")

    # Rashis are stored as "Aries (Mesha)" — strip the Sanskrit gloss for sign checks.
    mars_sign = mars.rashi.split(" ")[0]
    lagna_sign = chart.lagna_rashi.split(" ")[0]

    rules: list[ManglikRule] = []

    # Sign-based cancellations
    if mars_sign in {"Aries", "Scorpio"}:
        rules.append(ManglikRule(
            slug="mars_own_sign",
            description=f"Mars in own sign ({mars_sign})",
            effect="cancels",
            source="Jataka Parijata",
        ))
    if mars_sign == "Capricorn":
        rules.append(ManglikRule(
            slug="mars_exalted",
            description="Mars exalted in Capricorn",
            effect="cancels",
            source="Jataka Parijata",
        ))
    if mars_sign == "Cancer":
        rules.append(ManglikRule(
            slug="mars_debilitated",
            description="Mars debilitated in Cancer (lacks strength to disturb)",
            effect="cancels",
            source="Jataka Chandrika",
        ))
    # Movable-sign (Chara rashi) — per Jataka Parijata, Mars in Libra also
    # cancels (Aries/Cancer/Capricorn already covered by own/exalted/debilitated).
    if mars_sign == "Libra":
        rules.append(ManglikRule(
            slug="mars_libra_movable",
            description="Mars in Libra (movable sign — Chara rashi cancellation)",
            effect="cancels",
            source="Jataka Parijata",
        ))
    # Friendly-sign mitigations — Mars in Jupiter's signs (Sagittarius, Pisces)
    # or Venus's signs (Taurus, Libra; Libra already handled above)
    if mars_sign in {"Sagittarius", "Pisces"}:
        rules.append(ManglikRule(
            slug="mars_in_jupiters_sign",
            description=f"Mars in Jupiter's sign ({mars_sign}) — dispositor benefic mitigates",
            effect="mitigates",
            source="Phaladeepika",
        ))
    if mars_sign == "Taurus":
        rules.append(ManglikRule(
            slug="mars_in_venus_sign",
            description="Mars in Taurus (Venus's sign) — dispositor karaka softens marriage impact",
            effect="mitigates",
            source="Phaladeepika",
        ))

    # Ascendant-specific yogakaraka exclusions (Cancer/Leo lagna)
    if lagna_sign == "Cancer":
        rules.append(ManglikRule(
            slug="cancer_lagna_yogakaraka",
            description="Cancer Lagna — Mars is Yogakaraka (rules 5th + 10th); excluded from dosha",
            effect="cancels",
            source="Jataka Parijata / Muhurtha Chintamani",
        ))
    if lagna_sign == "Leo":
        rules.append(ManglikRule(
            slug="leo_lagna_yogakaraka",
            description="Leo Lagna — Mars is Yogakaraka (rules 4th + 9th); excluded from dosha",
            effect="cancels",
            source="Jataka Parijata / Muhurtha Chintamani",
        ))

    # Benefic conjunction / aspect — Jupiter is the primary classical cancellation.
    # Extended per vedic_reference.md §1.3: Jupiter aspecting the 7th house or
    # 7th lord ALSO cancels, not only aspecting Mars directly.
    if mars.house == jupiter.house:
        rules.append(ManglikRule(
            slug="mars_jupiter_conjunct",
            description="Mars conjunct Jupiter (Jupiter neutralises Martian disturbance)",
            effect="cancels",
            source="Jataka Parijata",
        ))
    elif _jupiter_aspects(jupiter.house, mars.house):
        rules.append(ManglikRule(
            slug="jupiter_aspects_mars",
            description="Jupiter aspects Mars (primary classical Mangal Dosha cancellation)",
            effect="cancels",
            source="Phaladeepika",
        ))
    elif _jupiter_aspects(jupiter.house, 7):
        rules.append(ManglikRule(
            slug="jupiter_aspects_7h",
            description="Jupiter aspects the 7th house (marital karaka support)",
            effect="cancels",
            source="Phaladeepika",
        ))
    else:
        # 7th lord aspect check — find who rules the 7th and see if Jupiter aspects them.
        # Rashi order = ["Aries (Mesha)", ...]; 7th house sign = lagna sign + 6 mod 12.
        _RASHI_LORDS = ("Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
                          "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter")
        lagna_idx = _rashi_index(chart.lagna_rashi)
        seventh_sign_idx = (lagna_idx + 6) % 12
        seventh_lord_name = _RASHI_LORDS[seventh_sign_idx]
        seventh_lord = next((p for p in chart.planets if p.name == seventh_lord_name), None)
        if seventh_lord and _jupiter_aspects(jupiter.house, seventh_lord.house):
            rules.append(ManglikRule(
                slug="jupiter_aspects_7l",
                description=f"Jupiter aspects the 7th lord ({seventh_lord_name})",
                effect="cancels",
                source="Phaladeepika",
            ))

    # Venus with Mars — conjunction OR 7th aspect (opposition) both help.
    # 7th aspect: Venus and Mars in houses 7 apart from each other.
    if mars.house == venus.house:
        rules.append(ManglikRule(
            slug="venus_with_mars",
            description="Venus conjunct Mars (relationship karaka channels Martian energy)",
            effect="mitigates",
            source="Classical compatibility practice",
        ))
    elif (mars.house - venus.house) % 12 == 6:
        rules.append(ManglikRule(
            slug="venus_aspects_mars",
            description="Venus aspects Mars from 7th (opposition — relationship karaka moderates)",
            effect="cancels",
            source="Phaladeepika",
        ))

    # Combustion — Mars within 6° of Sun on absolute sidereal longitude
    # (not same-rashi only — a Mars at 29° Aries and Sun at 2° Taurus are 3°
    # apart across the rashi boundary; the old same-rashi check missed this).
    #
    # THIS RULE IS UNSOURCED, and the label now says so on the page (#218).
    # It used to read source="Classical matching practice", which is not a
    # citation — it is a phrase shaped like one, and it sat next to real book
    # names in the same list, so a reader had no way to tell them apart.
    #
    # What the corpus actually holds (knowledge/grahas.md §12.4 has the full
    # audit; books present 2026-08-27 were Rao's textbook, Rao's *Lessons*,
    # Vasudev and Raman's *Muhurtha*):
    #   - Raman, *Muhurtha*, "ANTIDOTES FOR KUJA DOSHA" is a purpose-built
    #     exception list from the same book that supplies COMBUSTION_ORBS.
    #     Mars combustion is not on it.
    #   - Vasudev discusses Kuja dosha across 18 lines and never mentions it.
    #   - The rule's usual rationale — combustion weakens Mars, so the dosha
    #     lapses — is contradicted by the only passage in the corpus on Mars
    #     combustion: Rao, *Lessons* #21, "Ma with Su is combust. But, it
    #     really doesn't matter since both are agni planets and Ma is not
    #     effected." That is NOT a refutation (he is grading natal strength,
    #     not Kuja dosha) and he must NOT be cited FOR the rule — but it
    #     removes the premise.
    #   - The 6° is unsourced too. No book here states a Manglik orb, and
    #     the only combustion orb we hold gives Mars 17° (COMBUSTION_ORBS).
    #     Do NOT substitute 17 on the strength of that: this is a different
    #     rule that happens to measure Sun-proximity, and swapping the number
    #     would move live Manglik verdicts on no better authority.
    #
    # Left in force, honestly labelled. Deleting it silently changes whose
    # dosha is cancelled; keeping it unlabelled was the defect.
    mars_abs = _rashi_index(mars.rashi) * 30.0 + mars.longitude
    sun_abs = _rashi_index(sun.rashi) * 30.0 + sun.longitude
    sep = abs(mars_abs - sun_abs) % 360.0
    sep = min(sep, 360.0 - sep)
    if sep < 6.0:
        rules.append(ManglikRule(
            slug="mars_combust",
            description=f"Mars combust (within {sep:.1f}° of Sun)",
            effect="cancels",
            source="unsourced: absent from the classical Kuja-dosha antidote lists we hold",
        ))

    return tuple(rules)


def compute_manglik_details(chart: Chart) -> ManglikDetails:
    """Identify all Manglik-qualifying Mars positions + apply classical cancellation rules.

    Two-step model: first detect the raw mathematical Manglik pattern, then
    overlay cancellation/mitigation rules to compute an `effective_status`
    that the UI and LLM can act on without re-deriving classical doctrine.

    Detection is from THREE axes per knowledge/vedic_reference.md §1.1:
      - Lagna (Ascendant)
      - Chandra (Moon)
      - Shukra (Venus)
    Historically only Lagna + Moon were checked here — a chart genuinely
    Manglik-from-Venus would silently read as clean, producing a
    false-negative that misleads marriage decisions.
    """
    mars = next(p for p in chart.planets if p.name == "Mars")
    moon = next(p for p in chart.planets if p.name == "Moon")
    venus = next(p for p in chart.planets if p.name == "Venus")
    moon_idx = _rashi_index(moon.rashi)
    mars_idx = _rashi_index(mars.rashi)
    venus_idx = _rashi_index(venus.rashi)

    # Track per-axis qualifying so we can distinguish 'primary Lagna/Moon
    # Manglik' from 'Venus-axis-only Kuja-Shukra Manglik' — the two are
    # NOT equivalent in classical weight. Lagna + Moon axes = the standard
    # Manglik call every mainstream tool (AstroSage / mPanchang / physical
    # Jataka Parijata-based readings) reports. Venus axis is a
    # supplementary marriage-specific indicator (Kuja-Shukra Manglik) from
    # modern extended practice — real per K.N. Rao + Cheiro but weaker
    # than the primary axes. Reporting Venus-only as full Manglik gives
    # false positives against people's offline kundalis.
    from_lagna: set[int] = set()
    from_moon:  set[int] = set()
    from_venus: set[int] = set()
    axis_reasons: list[str] = []
    if mars.house in {1, 2, 4, 7, 8, 12}:
        from_lagna.add(mars.house)
        axis_reasons.append(f"Mars in {_ordinal(mars.house)} house from Lagna")
    mars_from_moon = ((mars_idx - moon_idx) % 12) + 1
    if mars_from_moon in {1, 2, 4, 7, 8, 12}:
        from_moon.add(mars_from_moon)
        axis_reasons.append(f"Mars in {_ordinal(mars_from_moon)} house from Moon")
    mars_from_venus = ((mars_idx - venus_idx) % 12) + 1
    if mars_from_venus in {1, 2, 4, 7, 8, 12}:
        from_venus.add(mars_from_venus)
        axis_reasons.append(f"Mars in {_ordinal(mars_from_venus)} house from Venus")
    qualifying = from_lagna | from_moon | from_venus
    venus_axis_only = not from_lagna and not from_moon and bool(from_venus)

    if not qualifying:
        return ManglikDetails(
            is_manglik=False, houses=(), primary_house=0, severity="none",
            cancellations=(), effective_status="none",
        )

    # Severity grading: 7th/8th = most serious; 1st/4th/12th = moderate; 2nd alone = low.
    #
    # THIS LADDER IS BHAGYA'S OWN EDITORIAL WEIGHTING, NOT CLASSICAL DOCTRINE (#429).
    # No book held in data/ states it. Only "7th/8th are the most serious" has
    # any support (Vasudev's per-house prose; vedic_reference.md §1.1/§1.6) — and
    # he grades no tiers, reading the 8th as worse than the 7th. "1st = moderate"
    # is counter-indicated (his list is 2/4/7/8/12; the 1st is "some include"),
    # and "2nd alone is lowest" is stated nowhere. The grades are kept as shipped
    # pending the owner's tier decision on #429; every surface that shows them
    # must say they are editorial (manglik_check_result.html, the LLM line in
    # format_manglik_for_prompt). Do not cite a classical text for the tiers.
    if {7, 8} & qualifying:
        severity = "high"
    elif {1, 4, 12} & qualifying:
        severity = "moderate"
    else:
        severity = "low"

    # "Primary" house for storytelling — the most-impactful qualifying house.
    house_priority = (7, 8, 1, 4, 12, 2)
    primary = next(h for h in house_priority if h in qualifying)

    # Apply cancellation rules and reduce to a single effective status.
    cancellations = _manglik_cancellations(chart)
    has_cancel = any(r.effect == "cancels" for r in cancellations)
    has_mitigate = any(r.effect == "mitigates" for r in cancellations)
    if has_cancel:
        effective_status = "cancelled"
    elif has_mitigate:
        effective_status = "mitigated"
    else:
        effective_status = "present"

    # Venus-axis-only DOWNGRADE — if neither Lagna nor Moon axis fired,
    # we're looking at pure Kuja-Shukra Manglik (marriage-specific
    # supplementary indicator). Never report as full 'present' — cap at
    # 'mitigated' so users don't panic over what their offline kundali
    # rightly calls a non-Manglik chart. Also downgrade severity by one
    # notch so the number-badge on the UI reads accurately.
    if venus_axis_only:
        if effective_status == "present":
            effective_status = "mitigated"
        if severity == "high":
            severity = "moderate"
        elif severity == "moderate":
            severity = "low"

    return ManglikDetails(
        is_manglik=True,
        houses=tuple(sorted(qualifying)),
        primary_house=primary,
        severity=severity,
        cancellations=cancellations,
        effective_status=effective_status,
        axis_reasons=tuple(axis_reasons),
        venus_axis_only=venus_axis_only,
    )


# ---------------------------------------------------------------------------
# Yogas — classical planetary combinations
#
# Source: P.V.R. Narasimha Rao, "Vedic Astrology: An Integrated Approach",
# Chapter 11 (data/vedic_astro_textbook.pdf). See knowledge/vedic_reference.md
# §4 for the full catalogue and rule definitions — keep this code and that
# file in sync when adding new yogas.
#
# This used to end "cross-checked with BPHS and Phaladeepika". Neither book
# is in `data/`, neither is one of the eight entries in fetch_corpus.py, and
# no such cross-check could have happened here (#216). Rao is the whole
# provenance, and he is enough: he states every one of these rules outright.
#
# Scope decision: we implement the high-signal trivially-computable yogas
# (Pancha Mahapurusha, Sun/Moon yogas, Vipareeta Raja, Trilochana, Amala,
# Vasumati, Guru-Mangala). Complex yogas requiring Jaimini karakas, navamsa
# dispositor chains, or functional malefic logic are deferred to V2.
# ---------------------------------------------------------------------------


# Natural-benefic / malefic classification.
# Mercury is benefic unless conjoined with a malefic (deferred — V1 treats
# Mercury as benefic). Moon's waxing/waning gradient is also deferred.
_NATURAL_BENEFICS: frozenset[str] = frozenset({"Jupiter", "Venus", "Mercury", "Moon"})
_NATURAL_MALEFICS: frozenset[str] = frozenset({"Saturn", "Mars", "Sun", "Rahu", "Ketu"})

# Own-sign + exaltation tables for Pancha Mahapurusha detection.
#
# Verified sign-by-sign against Rao §§11.4.1-11.4.5 on 2026-08-27: Mars
# "Ar, Sc or Cp", Mercury "Ge or Vi", Saturn "Cp, Aq or Li", Venus
# "Ta, Li or Pi", Jupiter "Sg, Pi or Cn". All five match.
#
# The previous attribution — "BPHS, Chapter 3 (Planets)" — named a book not
# in `data/` (#216), and its gloss was wrong besides: it called Capricorn
# Saturn's moolatrikona, which is Aquarius. Capricorn is simply one of
# Saturn's two own signs, as the inline notes below say.
_PMP_QUALIFYING_SIGNS: dict[str, set[str]] = {
    "Mars":    {"Aries", "Scorpio", "Capricorn"},     # own (Ar, Sc) + exalted (Cp)
    "Mercury": {"Gemini", "Virgo"},                   # own (Ge) + own/exalted (Vi)
    "Jupiter": {"Sagittarius", "Pisces", "Cancer"},   # own (Sg, Pi) + exalted (Cn)
    "Venus":   {"Taurus", "Libra", "Pisces"},         # own (Ta, Li) + exalted (Pi)
    "Saturn":  {"Capricorn", "Aquarius", "Libra"},    # own (Cp, Aq) + exalted (Li)
}

_KENDRA_HOUSES: frozenset[int] = frozenset({1, 4, 7, 10})
_TRINE_HOUSES: frozenset[int] = frozenset({1, 5, 9})
_UPACHAYA_HOUSES: frozenset[int] = frozenset({3, 6, 10, 11})
_DUSTHANA_HOUSES: frozenset[int] = frozenset({6, 8, 12})


def _sign_name(rashi_label: str) -> str:
    """Strip the Sanskrit parenthesis from a rashi label.

    "Cancer (Karka)" -> "Cancer". Centralised here so every yoga rule
    can do a clean equality check without re-parsing the format.
    """
    return rashi_label.split(" ")[0]


def _house_from_planet(target_house: int, ref_house: int) -> int:
    """Distance in houses from ref_planet to target. 1 = same house, 2 = next, …, 12 = previous."""
    return ((target_house - ref_house) % 12) + 1


@dataclass(frozen=True)
class YogaResult:
    """One yoga detected in the chart.

    `slug` is a stable id for tests / templates; `name` is human-readable;
    `category` groups yogas in the prompt block; `effect` is a 1-line
    significations string the LLM can paraphrase; `source` is the citation
    result.html prints to the reader under "Source:".

    `source` is NOT in the LLM prompt — format_yogas_for_prompt() omits it
    deliberately so the model cannot echo a citation back as prose. It is a
    page string only.
    """

    slug: str
    name: str
    category: str       # "pancha_mahapurusha" | "sun" | "moon" | "vipareeta_raja" | "other"
    effect: str
    source: str


# The book every yoga below is actually checked against, and the reason the
# citations changed (#216, #218).
#
# These rules used to carry source="Brihat Parashara Hora Shastra" and
# "BPHS / Phaladeepika", and result.html renders that verbatim as
# "Source: Brihat Parashara Hora Shastra" on the chart page. BPHS is not in
# `data/` and never was — it is not even one of the eight entries in
# scripts/fetch_corpus.py — so not one of those twelve citations was
# checkable by anybody, here or reading the site. A rule wearing a real
# book's name is worse than an unlabelled one, because it tells the reader
# not to check.
#
# Every yoga in this module was re-audited against the corpus on 2026-08-27
# with scripts/corpus_search.py. Books present that day (4 of 8, per
# scripts/fetch_corpus.py): Rao *Vedic Astrology: An Integrated Approach*,
# Rao *Lessons* Vol. I, Vasudev *Astrology*, Raman *Muhurtha* (1948). All
# twelve resolved to Rao's Ch. 11, whose definitions and "Results" lines are
# what the `effect` strings here paraphrase — sections cited individually
# below. That is a proximate source, not the ur-text, and naming it is the
# point: it is the one a reader can open.
#
# SOURCES.md used to license a bare `[BPHS]` for "universally cited" rules.
# That licence is what let an uncheckable attribution into shipped code, and
# it has been withdrawn — see knowledge/SOURCES.md, "Citation convention".
_RAO = "Rao, Vedic Astrology: An Integrated Approach"


def _pancha_mahapurusha_yogas(chart: Chart) -> list[YogaResult]:
    """The 5 'Great Person' yogas — own/exalted graha in a kendra from Lagna.

    Skipped for Sun and Moon (these are luminaries, not the 5 non-luminary grahas).
    """
    out: list[YogaResult] = []
    # The 4th element is Rao's section for that yoga (§11.4.1-11.4.5). Each
    # gives the same "quadrant in own or exaltation sign" definition, and the
    # sign sets in _PMP_QUALIFYING_SIGNS above match his sign-by-sign.
    names = {
        "Mars":    ("ruchaka_yoga",  "Ruchaka Yoga",  "Fiery great-man: courage, leadership, victory, occult skill", "11.4.1"),
        "Mercury": ("bhadra_yoga",   "Bhadra Yoga",   "Earthy great-man: learning, eloquence, systematic mind, business", "11.4.2"),
        "Jupiter": ("hamsa_yoga",    "Hamsa Yoga",    "Ethery great-man: wisdom, dharma, respect, scholarly fame", "11.4.5"),
        "Venus":   ("malavya_yoga",  "Malavya Yoga",  "Watery great-man: beauty, luxury, art, marital happiness", "11.4.4"),
        "Saturn":  ("sasha_yoga",    "Sasha Yoga",    "Airy great-man: discipline, leadership of multitudes, charity", "11.4.3"),
    }
    for p in chart.planets:
        if p.name not in _PMP_QUALIFYING_SIGNS:
            continue
        sign = _sign_name(p.rashi)
        if sign in _PMP_QUALIFYING_SIGNS[p.name] and p.house in _KENDRA_HOUSES:
            slug, name, effect, section = names[p.name]
            out.append(YogaResult(
                slug=slug, name=name, category="pancha_mahapurusha",
                effect=effect, source=f"{_RAO} §{section}",
            ))
    return out


def _sun_yogas(chart: Chart) -> list[YogaResult]:
    """Vesi, Vosi, Ubhayachara, Budha-Aditya — planet placements around the Sun."""
    out: list[YogaResult] = []
    sun = next(p for p in chart.planets if p.name == "Sun")
    others = [p for p in chart.planets if p.name not in {"Sun", "Moon", "Rahu", "Ketu"}]

    # 2nd / 12th from Sun (excluding Moon, per classical definition)
    in_2nd = any(_house_from_planet(p.house, sun.house) == 2 for p in others)
    in_12th = any(_house_from_planet(p.house, sun.house) == 12 for p in others)

    if in_2nd and in_12th:
        out.append(YogaResult(
            slug="ubhayachara_yoga", name="Ubhayachara Yoga", category="sun",
            effect="All comforts, royal stature; planets flanking the Sun on both sides",
            source=f"{_RAO} §11.2.3",
        ))
    elif in_2nd:
        out.append(YogaResult(
            slug="vesi_yoga", name="Vesi Yoga", category="sun",
            effect="Balanced outlook, truthful, content",
            source=f"{_RAO} §11.2.1",
        ))
    elif in_12th:
        out.append(YogaResult(
            slug="vosi_yoga", name="Vosi Yoga", category="sun",
            effect="Skillful, charitable, famous, learned",
            source=f"{_RAO} §11.2.2",
        ))

    # Budha-Aditya: Sun + Mercury same sign. Combust if within ~6° → weakened.
    #
    # The yoga is Rao §11.2.4, and so is the PRINCIPLE that combustion weakens
    # it — "Yogas formed by combust planets lose some of their power to do
    # good". The NUMBER is not. Rao writes only "too close" and gives no
    # degree; no book in the corpus states a Budha-Aditya orb, and this file's
    # own COMBUSTION_ORBS calls Mercury combust at 14° direct / 13° retrograde
    # — more than twice the 6° used here, so at Mercury 9° from the Sun this
    # branch prints an unweakened yoga for a planet the same file calls
    # combust. The direction is contested too — Rao's *Lessons* Lesson #21
    # reports him holding that closeness HELPS, and flags "there are different
    # opinions on this". knowledge/grahas.md §12.3 has the full audit (#218).
    #
    # So the disclosure rides on the label, and only when the 6° actually
    # changed what the reader is told. Deleting the number instead would move
    # yoga output; saying nothing would leave a reader unable to weigh it.
    mercury = next(p for p in chart.planets if p.name == "Mercury")
    if mercury.rashi == sun.rashi:
        combust_note = ""
        if abs(mercury.longitude - sun.longitude) < 6.0:
            combust_note = " (weakened — Mercury is combust within 6° of Sun)"
        out.append(YogaResult(
            slug="budha_aditya_yoga", name="Budha-Aditya Yoga (Nipuna)", category="sun",
            effect=f"Intelligence, skill, respect; bright mind{combust_note}",
            source=f"{_RAO} §11.2.4" + (
                " — the 6° cut-off is ours, not his, and the weakening is contested"
                if combust_note else ""
            ),
        ))
    return out


def _moon_yogas(chart: Chart) -> list[YogaResult]:
    """Sunaphaa, Anaphaa, Duradhara, Kemadruma, Chandra-Mangala, Gaja-Kesari."""
    out: list[YogaResult] = []
    moon = next(p for p in chart.planets if p.name == "Moon")
    # "Planets other than the Sun" — the nodes are NOT excluded (#208).
    #
    # Rao §§11.3.1-11.3.4 and both corpus files define Sunapha/Anapha/
    # Duradhara/Kemadruma over "planets other than Sun", with no node
    # exclusion. Dropping Rahu and Ketu changed the yoga set on 23.8% of
    # charts, and on 0.8% it declared KEMADRUMA — an inauspicious yoga of
    # isolation and poverty — where the source gives a positive one, because
    # the only planet flanking the Moon was a node that had been filtered out.
    #
    # Some schools do exclude the nodes here, so this is a genuine divergence
    # rather than a slip. It resolves to the corpus, as everything else on
    # this site does; if that is ever revisited it should be a sourced
    # decision recorded here, not a silent filter.
    others = [p for p in chart.planets if p.name not in {"Moon", "Sun"}]

    in_2nd = any(_house_from_planet(p.house, moon.house) == 2 for p in others)
    in_12th = any(_house_from_planet(p.house, moon.house) == 12 for p in others)
    in_same = any(p.house == moon.house for p in others)

    if in_2nd and in_12th:
        out.append(YogaResult(
            slug="duradhara_yoga", name="Duradhara Yoga", category="moon",
            effect="Pleasures, charity, wealth, vehicles, good servants",
            source=f"{_RAO} §11.3.3",
        ))
    elif in_2nd:
        out.append(YogaResult(
            slug="sunaphaa_yoga", name="Sunaphaa Yoga", category="moon",
            effect="Royal stature; intelligence, wealth, fame, self-earned success",
            source=f"{_RAO} §11.3.1",
        ))
    elif in_12th:
        out.append(YogaResult(
            slug="anaphaa_yoga", name="Anaphaa Yoga", category="moon",
            effect="Good-looking, disease-free, reputed, comfortable",
            source=f"{_RAO} §11.3.2",
        ))

    # Kemadruma: NONE of 1st/2nd/12th from Moon AND no planets in kendras from Lagna.
    # Classical cancellations exist (Moon conjoined with planet, kendras occupied);
    # we apply the second cancellation deterministically. Don't flag if any kendra is occupied.
    kendras_occupied = any(p.house in _KENDRA_HOUSES for p in chart.planets if p.name not in {"Moon"})
    if not in_2nd and not in_12th and not in_same and not kendras_occupied:
        out.append(YogaResult(
            # category "challenge", not "moon" (#208 follow-up). Kemadruma is
            # an INAUSPICIOUS yoga — an isolated, unsupported Moon — and
            # sharing a category with Sunapha/Anapha/Duradhara meant it
            # rendered under a green "Strengths" badge captioned "Strengths
            # around your mind and emotional life", and scored +5 in the
            # Bhagya Score alongside them. The one yoga on this page a reader
            # should pause over was being presented as a gift.
            slug="kemadruma_yoga", name="Kemadruma Yoga", category="challenge",
            effect="Lonely / unsupported Moon; emotional fragility — verify cancellations before alarm",
            source=f"{_RAO} §11.3.4",
        ))

    # Chandra-Mangala: Moon and Mars conjunct
    mars = next(p for p in chart.planets if p.name == "Mars")
    if moon.house == mars.house:
        out.append(YogaResult(
            slug="chandra_mangala_yoga", name="Chandra-Mangala Yoga", category="moon",
            effect="Worldly-wise, materially successful; energetic relationship with money",
            source=f"{_RAO} §11.3.5",
        ))

    # Gaja-Kesari: Jupiter in kendra (1/4/7/10) FROM Moon (not from Lagna).
    # Rao §11.6 gives THREE conditions — (1) Jupiter in a quadrant from Moon,
    # (2) a benefic conjoins or aspects Jupiter, (3) Jupiter not debilitated,
    # combust or in an enemy's house. We test (1), and use debilitation from
    # (3) as a downgrade note rather than a disqualifier. So the label says
    # "simplified": citing Rao flat for a rule looser than his would overstate
    # what he supports. He himself records the looser reading — "Some authors
    # consider Gaja-Kesari yoga to be present even when Jupiter is in a
    # quadrant from lagna and not Moon" — so a relaxed form is within the
    # tradition; it is just not the one his three conditions define.
    jupiter = next(p for p in chart.planets if p.name == "Jupiter")
    if _house_from_planet(jupiter.house, moon.house) in {1, 4, 7, 10}:
        debilitated = _sign_name(jupiter.rashi) == "Capricorn"
        note = " (weakened — Jupiter debilitated in Capricorn)" if debilitated else ""
        out.append(YogaResult(
            slug="gaja_kesari_yoga", name="Gaja-Kesari Yoga", category="moon",
            effect=f"Fame, wealth, intelligence, virtue, favor from authority{note}",
            source=f"{_RAO} §11.6 — simplified; his benefic-aspect condition is not applied",
        ))
    return out


def _vipareeta_raja_yogas(chart: Chart) -> list[YogaResult]:
    """Harsha / Sarala / Vimala — lord of a dusthana placed in own dusthana.

    Classical pattern that turns the 'house of suffering' into a source of
    strength through struggle. Computed via the house's ruling lord (rashi
    lord of the sign occupying that house).
    """
    out: list[YogaResult] = []
    lagna_idx = _rashi_index(chart.lagna_rashi)
    names = {
        6:  ("harsha_yoga",  "Harsha Yoga (Vipareeta Raja)",  "Strength against enemies and illness; success after struggle"),
        8:  ("sarala_yoga",  "Sarala Yoga (Vipareeta Raja)",  "Long life, fearlessness, learning, lasting prosperity"),
        12: ("vimala_yoga",  "Vimala Yoga (Vipareeta Raja)",  "Frugality, independence, noble character"),
    }
    for house, (slug, name, effect) in names.items():
        sign_idx = (lagna_idx + house - 1) % 12
        lord = RASHI_LORDS[sign_idx]
        lord_planet = next((p for p in chart.planets if p.name == lord), None)
        if lord_planet and lord_planet.house == house:
            out.append(YogaResult(
                # All three are in Rao §11.6 ("Other Popular Yogas"), one
                # sentence each: 6th lord in the 6th, 8th in the 8th, 12th in
                # the 12th. The effect strings above paraphrase his Results.
                slug=slug, name=name, category="vipareeta_raja",
                effect=effect, source=f"{_RAO} §11.6",
            ))
    return out


def _other_yogas(chart: Chart) -> list[YogaResult]:
    """Guru-Mangala, Trilochana, Amala, Vasumati, Adhi."""
    out: list[YogaResult] = []
    sun = next(p for p in chart.planets if p.name == "Sun")
    moon = next(p for p in chart.planets if p.name == "Moon")
    mars = next(p for p in chart.planets if p.name == "Mars")
    jupiter = next(p for p in chart.planets if p.name == "Jupiter")

    # Guru-Mangala: Jupiter and Mars conjunct or in mutual 7th
    delta = (mars.house - jupiter.house) % 12
    if delta == 0 or delta == 6:
        out.append(YogaResult(
            slug="guru_mangala_yoga", name="Guru-Mangala Yoga", category="other",
            effect="Righteous energy; courage directed at dharmic action",
            source=f"{_RAO} §11.6",
        ))

    # Trilochana: Sun, Moon, Mars in mutual trines (4 signs apart from each other)
    # 4 and 8 only — NOT 0 (#210). `vedic_reference.md` §4.5 defines this as
    # "mutual trines (4 signs apart)", and Rao Ch. 11 the same. Accepting 0
    # meant a conjunction counted as a trine, so all three in ONE house
    # satisfied a rule that asks for them spread across three. Measured on a
    # chart sweep: declared on 6.15% of charts against 0.88% correct — a 7x
    # over-detection of a yoga promising wealth and long life.
    diffs = sorted({(sun.house - mars.house) % 12, (moon.house - mars.house) % 12,
                    (sun.house - moon.house) % 12})
    if all(d in {4, 8} for d in diffs):
        out.append(YogaResult(
            slug="trilochana_yoga", name="Trilochana Yoga", category="other",
            effect="Wealthy, intelligent, long-lived, victorious",
            source=f"{_RAO} §11.6",
        ))

    # Amala: only natural benefics in the 10th from Lagna OR FROM THE MOON.
    #
    # The "or Moon" limb was missing until #207 — Rao Ch. 11 gives it as "in
    # the 10th house from lagna or Moon", and yogas.md §6.3 and
    # vedic_reference.md §4.5 agree. Checking Lagna alone missed the yoga on
    # 10.5% of charts.
    #
    # The node exclusion is also gone. Amala asks that the 10th hold ONLY
    # benefics; Rahu and Ketu are not benefics, so skipping them turned a
    # chart with Rahu plus a benefic in the 10th into a qualifying one —
    # wrongly declared on 2.3%. A node in the house now fails the test, which
    # is what "only benefics" means.
    moon_house = next((p.house for p in chart.planets if p.name == "Moon"), None)

    def _tenth_from(house: int) -> int:
        """The 10th house counted from `house`, 1-indexed and wrapping."""
        return ((house - 1 + 9) % 12) + 1

    def _amala_from(house: int) -> bool:
        occupants = [p for p in chart.planets if p.house == _tenth_from(house)]
        return bool(occupants) and all(p.name in _NATURAL_BENEFICS for p in occupants)

    amala = _amala_from(1) or (moon_house is not None and _amala_from(moon_house))
    if amala:
        out.append(YogaResult(
            slug="amala_yoga", name="Amala Yoga", category="other",
            effect="Ever-lasting fame, royal respect, virtue — clean reputation through career",
            source=f"{_RAO} §11.6",
        ))

    # Vasumati: benefics in upachayas (3rd, 6th, 10th, 11th from Lagna)
    benefics_in_upachaya = [p for p in chart.planets
                             if p.name in _NATURAL_BENEFICS and p.house in _UPACHAYA_HOUSES]
    if len(benefics_in_upachaya) >= 2:
        out.append(YogaResult(
            slug="vasumati_yoga", name="Vasumati Yoga", category="other",
            effect="Abundant wealth — benefics concentrated in growth-houses",
            source=f"{_RAO} §11.6",
        ))

    # Adhi: natural benefics in 6th, 7th and 8th from Moon
    adhi_houses_from_moon = {6, 7, 8}
    benefics_present = {
        _house_from_planet(p.house, moon.house)
        for p in chart.planets if p.name in _NATURAL_BENEFICS
    }
    if adhi_houses_from_moon.issubset(benefics_present):
        out.append(YogaResult(
            slug="adhi_yoga", name="Adhi Yoga", category="other",
            effect="Leadership at scale — minister, army chief, or trusted authority",
            source=f"{_RAO} §11.3.6",
        ))
    return out


def compute_yogas(chart: Chart) -> tuple[YogaResult, ...]:
    """Detect all classical yogas this chart triggers.

    Aggregates Pancha Mahapurusha, Sun/Moon yogas, Vipareeta Raja, and the
    high-signal 'other' yogas. Order is deterministic (category-grouped) so
    repeated calls produce identical output for cache fingerprinting.
    """
    all_yogas: list[YogaResult] = []
    all_yogas.extend(_pancha_mahapurusha_yogas(chart))
    all_yogas.extend(_sun_yogas(chart))
    all_yogas.extend(_moon_yogas(chart))
    all_yogas.extend(_vipareeta_raja_yogas(chart))
    all_yogas.extend(_other_yogas(chart))
    return tuple(all_yogas)


@dataclass(frozen=True)
class TopicSummary:
    """A distilled article summary for LLM enrichment injection.

    Selected per chart via `topic_summaries_for_chart` (deterministic
    feature-to-topic map). The LLM uses the summary to add classical depth
    to the relevant reading section and emits the link as a "For more, see
    our <title>" cross-link.
    """

    slug: str        # article slug (for the /learn/ link)
    title: str       # article title (anchor-text hint for the LLM)
    summary: str     # 50-100 token distilled classical takeaways


_GRAHA_ARTICLE: dict[str, str] = {
    "Sun":     "surya-sun-in-vedic-astrology",
    "Moon":    "chandra-moon-in-vedic-astrology",
    "Mars":    "mangal-mars-in-vedic-astrology",
    "Mercury": "budha-mercury-in-vedic-astrology",
    "Jupiter": "guru-jupiter-in-vedic-astrology",
    "Venus":   "shukra-venus-in-vedic-astrology",
    "Saturn":  "shani-saturn",
    "Rahu":    "rahu-in-vedic-astrology",
    "Ketu":    "ketu-in-vedic-astrology",
}

_GRAHA_REMEDY_ARTICLE: dict[str, str] = {
    "Mars":    "mars-remedies",
    "Mercury": "mercury-remedies",
    "Jupiter": "jupiter-remedies",
    "Venus":   "venus-remedies",
    "Saturn":  "saturn-remedies",
}

_NAKSHATRA_ARTICLE: dict[str, str] = {
    "Ashwini":         "ashwini-nakshatra",
    "Bharani":         "bharani-nakshatra",
    "Krittika":        "krittika-nakshatra",
    "Rohini":          "rohini-nakshatra",
    "Mrigashira":      "mrigashira-nakshatra",
    "Ardra":           "ardra-nakshatra",
    "Punarvasu":       "punarvasu-nakshatra",
    "Pushya":          "pushya-nakshatra",
    "Ashlesha":        "ashlesha-nakshatra",
    "Magha":           "magha-nakshatra",
    "Purva Phalguni":  "purva-phalguni-nakshatra",
    "Uttara Phalguni": "uttara-phalguni-nakshatra",
    "Hasta":           "hasta-nakshatra",
    "Chitra":          "chitra-nakshatra",
    "Swati":           "swati-nakshatra",
    # 12 more nakshatras exist classically but articles not yet written;
    # graceful fallback below skips slugs missing from the registry
}


def topic_summaries_for_chart(
    chart: "Chart",
    dasha_state: "DashaState",
    articles: tuple,  # tuple[Article, ...] from learn_registry (avoids circular import)
) -> list[TopicSummary]:
    """Select 2-5 most relevant article summaries for this chart.

    Deterministic feature-to-topic map — no embeddings, no retrieval, no
    per-request LLM cost. Reads chart features + Dasha state, returns
    TopicSummary objects for the LLM to weave into the reading.

    Selection priority (cap 5):
      1. Manglik (if flag active)
      2. Sade Sati (if active)
      3. Current Mahadasha's graha foundation article + specific dasha article
         if applicable (currently only rahu-mahadasha)
      4. Placement-based: planet in 10th → matching career article;
         Saturn/Rahu in 7th → marriage-delayed
      5. Moon's nakshatra article (adds personality specificity)
      6. Filler: current Dasha's remedy article, then Vimshottari foundation

    Extend the maps at the top of this module as more articles get
    llm_summary backfilled or new chart signatures need coverage.
    """
    selected: list[str] = []

    flags = compute_vedic_flags(chart)
    # The gate here is the RAW flag (`flags.manglik`, i.e. effective_status is
    # anything but "none"), deliberately not is_effectively_manglik() — a
    # cancelled chart still gets the explainer, and that is the point.
    #
    # This list is not a "related reading" rail; it is the only chart-conditional
    # article selection in the codebase. It feeds
    # format_topic_summaries_for_prompt() -> the natal prompt's RELEVANT TOPIC
    # SUMMARIES block, so what gets injected is the article's llm_summary. The
    # /learn link the seeker eventually sees is downstream of that: the model
    # emits /learn/<slug>/ and routes/deps.py::_linkify_learn labels it from the
    # article's seo_title.
    #
    # For a CANCELLED chart the injected summary is exactly the text the model
    # needs — it carries the cancellation catalogue and closes on "Effective
    # status is per-chart: PRESENT / MITIGATED / CANCELLED", which is what lets
    # the reading explain the green verdict instead of asserting it. Dropping it
    # would make that reading worse, not safer. result.html gates its Manglik
    # panel on the same raw flag, so narrowing here would render a verdict panel
    # while refusing to link the article that explains it.
    #
    # The known residue is a LABELLING problem, not a selection one: _linkify_learn
    # uses seo_title, so it must stay neutral beside a "Cancelled" panel (#311 made
    # it "Is It Real? Cancellation Rules Most Skip"); never imply the reader is Manglik.
    if flags.manglik:
        selected.append("manglik-dosh")
    if flags.sade_sati:
        selected.append("sade-sati")

    # Current Mahadasha lord — graha foundation + special-case articles
    maha_lord = dasha_state.mahadasha.lord
    if maha_lord == "Rahu":
        selected.append("rahu-mahadasha-career-problems")
    graha_article = _GRAHA_ARTICLE.get(maha_lord)
    if graha_article:
        selected.append(graha_article)

    # Placement-based (planet in 10th house)
    for planet in chart.planets:
        if planet.house == 10:
            if planet.name == "Saturn":
                selected.append("saturn-in-10th-house-career")
            elif planet.name == "Sun":
                selected.append("sun-in-10th-house-career")
            elif planet.name == "Jupiter":
                selected.append("jupiter-in-10th-house-career")
        if planet.house == 7 and planet.name in ("Saturn", "Rahu"):
            selected.append("marriage-delayed")

    # Marriage-favouring Mahadasha surfaces the timing / mahadasha guides
    if maha_lord in ("Venus", "Jupiter"):
        selected.append("marriage-mahadasha-timing")
        selected.append("marriage-timing-kundli")

    # Venus + Rahu in the same house or in mutual aspect (7 houses apart) =
    # classical love-marriage signature; surface the love-vs-arranged guide
    venus = next((p for p in chart.planets if p.name == "Venus"), None)
    rahu = next((p for p in chart.planets if p.name == "Rahu"), None)
    if venus is not None and rahu is not None:
        same_house = venus.house == rahu.house
        opposition = abs(venus.house - rahu.house) == 6  # 7 houses apart circularly
        if same_house or opposition:
            selected.append("love-vs-arranged-marriage-kundli")

    # Moon's nakshatra — adds personality-specific depth
    moon = next((p for p in chart.planets if p.name == "Moon"), None)
    if moon is not None:
        nak_slug = _NAKSHATRA_ARTICLE.get(getattr(moon, "nakshatra", ""))
        if nak_slug:
            selected.append(nak_slug)

    # Fillers (only if we still have room in the cap)
    remedy_slug = _GRAHA_REMEDY_ARTICLE.get(maha_lord)
    if remedy_slug:
        selected.append(remedy_slug)
    selected.append("vimshottari-dasha-explained")

    # Dedupe preserving priority order + cap at 5
    seen: set[str] = set()
    unique = [s for s in selected if not (s in seen or seen.add(s))][:5]

    by_slug = {a.slug: a for a in articles}
    result: list[TopicSummary] = []
    for slug in unique:
        art = by_slug.get(slug)
        if art and getattr(art, "llm_summary", ""):
            result.append(TopicSummary(slug=slug, title=art.title, summary=art.llm_summary))
    return result


def format_topic_summaries_for_prompt(summaries: list[TopicSummary]) -> str:
    """Emit the RELEVANT TOPIC SUMMARIES block for the LLM.

    Each entry gives the LLM: the topic name, distilled classical rules,
    and the /learn/ link to emit as a cross-reference from the matching
    reading section. Empty list ⇒ empty string (no block emitted).
    """
    if not summaries:
        return ""
    lines = [
        "--- RELEVANT TOPIC SUMMARIES ---",
        "Classical distillations for topics that specifically apply to THIS chart.",
        "Use them to add depth to relevant sections. At the end of each section",
        "where you draw on a summary, add a natural cross-link like",
        "  \"For more, see our <title> guide → /learn/<slug>/\"",
        "so the reader can dig deeper. Do not force every summary in; use only",
        "where it fits naturally.",
    ]
    for s in summaries:
        lines.append(f"  • [{s.slug}] {s.title}")
        lines.append(f"    Summary: {s.summary}")
        lines.append(f"    Link: /learn/{s.slug}/")
    return "\n".join(lines)


_YOGA_ACTIVATORS_STATIC: dict[str, tuple[str, ...]] = {
    # Pancha Mahapurusha — activator is the yoga's own planet
    "ruchaka_yoga":         ("Mars",),
    "bhadra_yoga":          ("Mercury",),
    "hamsa_yoga":           ("Jupiter",),
    "malavya_yoga":         ("Venus",),
    "sasha_yoga":           ("Saturn",),
    # Sun-related — planets forming Vesi/Vosi/Ubhayachara around Sun
    "budha_aditya_yoga":    ("Sun", "Mercury"),
    "vesi_yoga":            ("Sun",),
    "vosi_yoga":            ("Sun",),
    "ubhayachara_yoga":     ("Sun",),
    # Moon-related — planets around/aspecting Moon
    "anaphaa_yoga":         ("Moon",),
    "sunaphaa_yoga":        ("Moon",),
    "duradhara_yoga":       ("Moon",),
    "gaja_kesari_yoga":     ("Jupiter", "Moon"),
    "chandra_mangala_yoga": ("Moon", "Mars"),
    "adhi_yoga":            ("Moon", "Jupiter", "Venus", "Mercury"),
    "trilochana_yoga":      ("Moon",),
    # Others — planets forming the specific combination
    "amala_yoga":           ("Jupiter", "Venus"),
    "vasumati_yoga":        ("Jupiter", "Venus", "Mercury", "Moon"),
    "guru_mangala_yoga":    ("Jupiter", "Mars"),
    "jupiter_aspects_mars": ("Jupiter", "Mars"),
    "mars_jupiter_conjunct": ("Mars", "Jupiter"),
    "venus_with_mars":      ("Venus", "Mars"),
    # Mars descriptors — Mars Dasha activates
    "mars_combust":         ("Mars",),
    "mars_debilitated":     ("Mars",),
    "mars_exalted":         ("Mars",),
    "mars_own_sign":        ("Mars",),
    "cancer_lagna_yogakaraka": ("Mars",),
    "leo_lagna_yogakaraka":    ("Mars",),
    # Kemadruma is a NEGATIVE yoga (isolated Moon) — no positive activation
    "kemadruma_yoga":       (),
}

# Vipareeta Raja Yogas — activator is the ruler of the specific dusthana that
# the yoga names (6th/8th/12th). Computed dynamically from the chart's Lagna.
_HOUSE_LORD_YOGAS: dict[str, int] = {
    "harsha_yoga":  6,
    "sarala_yoga":  8,
    "vimala_yoga":  12,
}


def yoga_activator_lords(yoga: YogaResult, chart: Chart) -> tuple[str, ...]:
    """Which Vimshottari Dasha lords activate this yoga's specific gift.

    Classical rule: a yoga's benefit peaks during the Dasha or Antardasha of
    the planet(s) forming that yoga. For Vipareeta Raja yogas the activator
    is the ruler of the specific dusthana (6th/8th/12th) named by the yoga.
    """
    if yoga.slug in _YOGA_ACTIVATORS_STATIC:
        return _YOGA_ACTIVATORS_STATIC[yoga.slug]
    if yoga.slug in _HOUSE_LORD_YOGAS:
        house = _HOUSE_LORD_YOGAS[yoga.slug]
        lagna_idx = _rashi_index(chart.lagna_rashi)
        sign_idx = (lagna_idx + house - 1) % 12
        return (RASHI_LORDS[sign_idx],)
    return ()


def format_yogas_for_prompt(yogas: tuple[YogaResult, ...], chart: Chart | None = None) -> str:
    """Tiny LLM hint listing detected yogas — only emitted when at least one fires.

    Stays ~50-300 tokens depending on how many yogas hit. Each line is yoga
    name + effect + (if chart is provided) which Mahadasha chapters activate
    its gift. Classical sources are deliberately omitted so the LLM can't
    echo them back as user-facing "per Rao Ch.11" jargon.
    """
    if not yogas:
        return ""
    lines = [
        "--- YOGAS DETECTED ---",
        "Classical planetary combinations active in this chart. Mention them by NAME",
        "in the relevant section and paraphrase the effect in plain words. Do NOT name",
        "classical texts, chapters, or sanskrit shastra in your prose — those live in",
        "the UI panel separately.",
        "The [activates in X chapters] hint tells you which Mahadasha chapter(s) bring",
        "each yoga's gift forward — use this to weave yoga names into the matching",
        "Life Stages chapter description (still without naming the planet itself).",
    ]
    # Challenge-category yogas are flagged INLINE rather than filtered out
    # (#208 QA). The block's preamble frames everything in it as a gift the
    # model should weave into a Life Stages chapter — handing Kemadruma to it
    # unmarked invited a reading of isolation as a blessing. Dropping it
    # instead would be worse: the chart genuinely has it, and a reader asking
    # about a hard period deserves the model to know.
    if any(y.category == "challenge" for y in yogas):
        lines.append(
            "NOTE: lines marked [DIFFICULT] are NOT gifts. The tradition reads them "
            "as areas needing attention, and most carry classical cancellations. "
            "Mention them with that caveat and without alarm — never as a promise "
            "of misfortune, and never woven in as a benefit."
        )
    for y in yogas:
        marker = " [DIFFICULT]" if y.category == "challenge" else ""
        line = f"  • {y.name}{marker}: {y.effect}"
        if chart is not None:
            activators = yoga_activator_lords(y, chart)
            if activators:
                line += f"  [activates in {'/'.join(activators)} chapters]"
        lines.append(line)
    return "\n".join(lines)


_HOUSE_LORD_HINT: dict[int, str] = {
    1:  "(self, personality)",
    2:  "(wealth, family, speech)",
    3:  "(courage, siblings, communication)",
    4:  "(home, mother, comfort)",
    5:  "(intelligence, children, romance)",
    6:  "(service, enemies, health struggle)",
    7:  "(marriage, partnership, public)",
    8:  "(longevity, in-laws, hidden matters)",
    9:  "(dharma, father, fortune)",
    10: "(career, action, status)",
    11: "(gains, elder siblings, network)",
    12: "(loss, foreign, moksha)",
}

_PLACEMENT_HINT: dict[int, str] = {
    1:  "grounds identity in the lord's themes",
    2:  "channels resources / speech through the lord",
    3:  "expresses via own effort and siblings",
    4:  "roots in home + emotional life",
    5:  "creative + child + past-life expression",
    6:  "activates via service / conflict / effort — often struggle-first",
    7:  "expresses through partnership + public dealings",
    8:  "hidden / karmic / transformative expression",
    9:  "flows through dharma + fortune + father",
    10: "channels into career + public standing",
    11: "gains + network + elder-sibling channel",
    12: "loss / foreign / moksha channel",
}


def format_house_lords_for_prompt(chart: "Chart") -> str:
    """House-lord placement report (Issue #60).

    For each of the 12 houses: which planet rules the sign in that house,
    where that planet actually sits, and a plain-English hint about what
    the placement produces. Classical readings live on this data — a chart
    with 10th lord in the 6th house reads very differently than 10th lord
    in the 10th, even though both charts have "career" as a theme.
    """
    lagna_idx = _rashi_index(chart.lagna_rashi)
    lines = ["--- HOUSE LORD PLACEMENTS (where each house-ruler sits) ---"]
    planet_by_name = {p.name: p for p in chart.planets}
    for house in range(1, 13):
        sign_idx = (lagna_idx + house - 1) % 12
        lord = RASHI_LORDS[sign_idx]
        lord_planet = planet_by_name.get(lord)
        if lord_planet is None:
            continue
        lord_house = lord_planet.house
        theme = _HOUSE_LORD_HINT[house]
        placement_note = _PLACEMENT_HINT.get(lord_house, "")
        lines.append(
            f"  {house}th lord {theme}: {lord} in house {lord_house} — {placement_note}"
        )
    return "\n".join(lines)


# Dignity dispositor helpers (used by format_planet_dignity_for_prompt below)
_OWN_SIGNS: dict[str, set[str]] = {
    "Sun": {"Leo"},
    "Moon": {"Cancer"},
    "Mars": {"Aries", "Scorpio"},
    "Mercury": {"Gemini", "Virgo"},
    "Jupiter": {"Sagittarius", "Pisces"},
    "Venus": {"Taurus", "Libra"},
    "Saturn": {"Capricorn", "Aquarius"},
}
_EXALTATION_SIGN: dict[str, str] = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra",
}
_DEBILITATION_SIGN: dict[str, str] = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries",
}


# Combustion orbs (asta), sourced from knowledge/grahas.md §12.
#
# This is the DIGNITY-BLOCK definition. It is not yet the only one, and an
# earlier version of this comment claimed it was — wrongly, so the correction
# is worth keeping.
#
# What changed: the dignity block used a flat 8 degrees for every planet and
# now uses these. Measured on 800 random charts, that changes the block on
# ~34% of them (two independent 800-chart samples, seeds 1 and 2: 34.4% and
# 34.2%, re-measured 2026-08-23 against the CORRECTED orbs). It read ~29%
# (28.4% / 29.5%) under the pre-0a1b6ee retrograde orbs, and was left stale in
# the same comment block whose next paragraph had just been re-measured.
#
# A flat orb is not a simplification of the classical rule but a narrower
# rule, so it under-reported, describing genuinely combust planets to the LLM
# as "neutral". The change can only ADD flags, never remove one — every orb in
# the table is >= 9.0 (the minimum is Venus-retrograde, at 9.0 since 0a1b6ee
# corrected it from an invented 8.0), so sep < 8.0 implies sep < new_orb for
# every planet. That is structural, not a property of whichever sample
# happened to be measured.
#
# What did NOT change, and is still separate:
#   _manglik_cancellations()  Mars combust the Sun, 6 deg — a Manglik
#                             CANCELLATION test
#   _sun_yogas()              Budha-Aditya weakening, 6 deg
# (muhurat.py:49's Mercury 12 was on this list until 39ae5bf deleted it; both
#  survivors are UNSOURCED — see #218.) Both still are, and both now SAY so in
#  the `source` string result.html prints, rather than only here where no
#  reader can see it. The numbers are unchanged: labelling them was the fix,
#  because replacing them would need an authority nobody has.
#
# The last two are deliberately untouched: they are distinct classical rules
# that happen to measure Sun-proximity, not this rule at a different orb, and
# folding them in would silently move Manglik verdicts and yoga detection.
# muhurat.py WAS a genuine duplicate of THIS rule. It adopted combustion_orb()
# in 39ae5bf and its three constants are gone, so the count is back to three
# Sun-proximity rules, all deliberate and all distinct. That change did move
# muhurat ratings, exactly as this note warned: measured over 365 days of 2026,
# mercury flips on 24 days, venus on 3, jupiter on 0 — measured against the
# retrograde orbs in force at the time, which 0a1b6ee then corrected. Against
# the corrected orbs the 2026 figures are mercury 18 and venus 2.
#
# Counting honestly at the time, #206 took the repo from three Sun-proximity
# constants to four; it fixed the one that was wrong and named the rest.
#
# Retrograde variants are part of the classical rule, not a refinement: an
# inferior planet moving retrograde is on the near side of the Sun and burns at
# a tighter orb. `PlanetPosition.retrograde` already carries what is needed.
#
# Rahu and Ketu are absent deliberately — they are shadow points, not bodies,
# and cannot be burned by the Sun. Sun is absent because it cannot combust
# itself.
COMBUSTION_ORBS: Final[dict[str, tuple[float, float]]] = {
    # planet:   (direct orb, retrograde orb)  — degrees from the Sun
    "Moon":     (12.0, 12.0),
    "Mars":     (17.0, 17.0),
    "Mercury":  (14.0, 13.0),
    "Jupiter":  (11.0, 11.0),
    "Venus":    (10.0,  9.0),
    "Saturn":   (15.0, 15.0),
}
# Source: B.V. Raman, "Muhurtha or Electional Astrology" (1948), Appendix
# p.197 — data/matching/raman-muhurtha-1948-electional-astrology_djvu.txt
# lines 7183-7207 for the table AND 7227-7228 for the footnote. The footnote
# sits 20 lines below the table, under an intervening entry; quoting only the
# table range would send a reader past the sentence the retrograde orbs
# entirely rest on. Already plain text; no pdftotext involved.
#
#     Planets, Combustion of : — Planets situated within
#     distances mentioned below from the Sun become combust.*
#     The Moon within 12°   Mars 17°   Mercury 14°*
#     Jupiter 11°   Venus 10°*   Saturn 15°
#
#     * When Mercury and Venus [are] retrograde the angle will be
#       one degree less.
#
# THE RETROGRADE VALUES USED TO BE 10 AND 8, AND THAT WAS INVENTED. The
# footnote says ONE degree less, so Mercury is 13 and Venus is 9. The
# asterisks bind to exactly those two rows and to the lead sentence, and
# "one degree" is spelled out — there is no digit for OCR to corrupt.
#
# The direction was right and the magnitude was made up. Worse, the comment
# that carried it asserted the retrograde rule was "part of the classical
# rule, not a refinement" at a time when no source for it existed in the
# repo at all — the justification was written first and the evidence looked
# for later, which is the failure mode CLAUDE.md opens with.
#
# The six DIRECT orbs are correct and unchanged; every one matches p.197.
#
# On the deleted "(per BPHS)" attribution: BPHS is not in data/ and never
# was, so that citation was never checkable. SOURCES.md used to license
# [BPHS] for "universally cited" rules, which is how an uncheckable
# attribution reached a code comment and a published article. That licence
# has been withdrawn (#216) and twelve yoga rules that cited BPHS to the
# reader now cite Rao Ch. 11; scripts/verify_rule_citations.py fails the
# build if a new one names a book we do not hold. Cite the page we hold.
#
# Note grahas.md §12 was written 2026-07-24 (372396a) "from Rao Ch. 3",
# which contains no combustion material whatsoever. Raman's Muhurtha only
# entered data/ around 2026-08-16. So §12 was unsourced when written and was
# corroborated by luck three weeks later — on six numbers, not on eight.


def combustion_orb(planet_name: str, retrograde: bool) -> float | None:
    """Orb in degrees within which `planet_name` is combust, or None.

    None means the planet has no combustion rule — the Sun itself, and the
    nodes. Callers must treat None as "not applicable", never as zero.
    """
    orbs = COMBUSTION_ORBS.get(planet_name)
    if orbs is None:
        return None
    return orbs[1] if retrograde else orbs[0]


def is_combust(planet, sun) -> tuple[bool, float]:
    """(combust?, separation in degrees) for `planet` against `sun`.

    Separation is the true angular distance, wrapping at 180 — a planet 359
    degrees "ahead" of the Sun is one degree away, not 359.
    """
    orb = combustion_orb(planet.name, planet.retrograde)
    sun_abs = _rashi_index(sun.rashi) * 30.0 + sun.longitude
    p_abs = _rashi_index(planet.rashi) * 30.0 + planet.longitude
    sep = abs(p_abs - sun_abs) % 360.0
    sep = min(sep, 360.0 - sep)
    if orb is None:
        return False, sep
    return sep < orb, sep


def format_planet_dignity_for_prompt(chart: "Chart") -> str:
    """Planet dignity report (Issue #61).

    For each of the 7 luminary+non-luminary planets (Rahu/Ketu don't own
    signs so are omitted here — their dignity theory is contested), report:
    - Sign + house
    - Dignity: EXALTED / OWN SIGN / DEBILITATED / neutral
    - Combust flag per COMBUSTION_ORBS (per-planet, retrograde-aware)

    Debilitation dramatically reverses a planet's expression; the LLM often
    misses this in output. Explicit flag prevents "Sun in Libra is
    authoritative" errors when Sun is deeply debilitated there.
    """
    lines = ["--- PLANET DIGNITY (own sign / exalted / debilitated / combust) ---"]
    sun = next((p for p in chart.planets if p.name == "Sun"), None)
    for p in chart.planets:
        if p.name in ("Rahu", "Ketu"):
            continue
        # p.rashi is like "Aries (Mesha)"; extract just the English name
        # for dict lookups against _OWN_SIGNS / _EXALTATION_SIGN / etc.
        english_rashi = p.rashi.split(" ")[0]
        dignities: list[str] = []
        if english_rashi in _OWN_SIGNS.get(p.name, set()):
            dignities.append("OWN SIGN")
        if _EXALTATION_SIGN.get(p.name) == english_rashi:
            dignities.append("EXALTED")
        if _DEBILITATION_SIGN.get(p.name) == english_rashi:
            dignities.append("DEBILITATED")
        # Combust check — per-planet orbs from knowledge/grahas.md §12, with
        # the classical retrograde variants. See COMBUSTION_ORBS (#206).
        if sun is not None and p.name != "Sun":
            combust, sep = is_combust(p, sun)
            if combust:
                dignities.append(f"COMBUST ({sep:.1f}° from Sun)")
        tag = " — ".join(dignities) if dignities else "neutral"
        lines.append(f"  {p.name} in {p.rashi} (house {p.house}) — {tag}")
    return "\n".join(lines)


_NAKSHATRA_ARCHETYPE_SHORT: dict[str, str] = {
    "Ashwini":         "rapid healing, first-mover, initiation, speed",
    "Bharani":         "gatekeeper of transitions, moral intensity, bearing burdens",
    "Krittika":        "cutting through illusion, sharp discernment, purification by fire",
    "Rohini":          "growth, abundance, sensuality, wealth-accumulation",
    "Mrigashira":      "gentle seeker, restless curiosity, poetry, exploration",
    "Ardra":           "storm-that-clears, breakthrough after breakdown, emotional intensity",
    "Punarvasu":       "return home, renewal, unconditional love, moral compass",
    "Pushya":          "MOST auspicious classically — nourishment, blessings, dharmic support",
    "Ashlesha":        "hypnotic charm, occult knowledge, serpent wisdom, penetrating insight",
    "Magha":           "royal lineage, ancestral pride, ceremonial authority",
    "Purva Phalguni":  "pleasure, romance, luxury, creative expression",
    "Uttara Phalguni": "dependable partnership, contract-honouring, patronage",
    "Hasta":           "skilled hand, craftsmanship, healing touch, precision",
    "Chitra":          "dazzling beauty, artistic brilliance, structural design",
    "Swati":           "independent, diplomatic, adaptable, wind-like movement",
    "Vishakha":        "goal-oriented, forked path, strategic ambition",
    "Anuradha":        "devoted friendship, loyal collaboration, spiritual discipline",
    "Jyeshtha":        "eldest, protective authority, hidden power, responsibility",
    "Mula":            "root-cutting, philosophical depth, tearing away illusions",
    "Purva Ashadha":   "early victory, invigorating, purification through water",
    "Uttara Ashadha":  "unconquerable, lasting victory, ethical achievement",
    "Shravana":        "listening, learning, tradition-bearing, communication",
    "Dhanishta":       "wealth of skill, rhythmic mastery, generous prosperity",
    "Shatabhisha":     "hundred healers, secretive, unconventional healing, mystery",
    "Purva Bhadrapada":"burning intensity, ascetic fire, dual-natured transformation",
    "Uttara Bhadrapada":"deep waters, kundalini serpent, wise seclusion, sacrificial giving",
    "Revati":          "shepherding, nourishment, safe passage, gentle guidance",
}


def _house_diff(from_house: int, to_house: int) -> int:
    """1-based house distance from -> to (1..12 inclusive)."""
    return ((to_house - from_house) % 12) + 1


def format_aspects_for_prompt(chart: "Chart") -> str:
    """Classical Vedic aspects report (Issue #63).

    Every planet aspects the 7th house/planet (opposition). Beyond that:
    - Mars additionally aspects the 4th and 8th from itself
    - Jupiter additionally aspects the 5th and 9th
    - Saturn additionally aspects the 3rd and 10th
    - Rahu/Ketu follow the same rules as Jupiter (5/7/9) in most schools

    Emits the special aspects for each planet — the everyday 7th-aspect
    (opposition) is universal so we skip it to save tokens; the LLM can
    infer it if needed. Special aspects are what classically add colour
    to marriage / career / partnership readings.
    """
    # ONLY Mars, Jupiter and Saturn have special aspects (#205).
    #
    # Rahu and Ketu carried (5, 9) here until the Kundli correctness audit.
    # `knowledge/aspects.md:74` says the opposite in as many words:
    # "Everything else (Sun, Moon, Mercury, Venus, Rahu, Ketu) has *only* the
    # 7th house aspect", and Rao §10.2 and Raman Ch. II both close the list at
    # Mars/Jupiter/Saturn. `_jupiter_aspects()` further down this same file
    # already got it right, so the file contradicted itself.
    #
    # The cost was not subtle: every single Kundli reading received two
    # fabricated "CLASSICAL ASPECTS" lines asserting node aspects the
    # tradition does not give them. Some schools do assign nodes a 5/9
    # drishti, so this is a real divergence rather than a typo — but the
    # corpus this site cites is unambiguous, and a claim we cannot trace is
    # one we do not make.
    _special: dict[str, tuple[int, ...]] = {
        "Mars":    (4, 8),
        "Jupiter": (5, 9),
        "Saturn":  (3, 10),
    }
    _archetype: dict[str, str] = {
        "Mars":    "Mars energy — pushes / disrupts / activates",
        "Jupiter": "Jupiter grace — expands / blesses / protects",
        "Saturn":  "Saturn discipline — delays / matures / weighs",
        "Rahu":    "Rahu amplifier — obsesses / distorts / boundary-crosses",
        "Ketu":    "Ketu detachment — thins / releases / spiritualises",
    }
    lines = ["--- CLASSICAL ASPECTS (special drishti — 7th is universal, skipped) ---"]
    for p in chart.planets:
        aspects = _special.get(p.name)
        if not aspects:
            continue
        aspected_houses = []
        for a in aspects:
            aspected_house = ((p.house - 1 + a - 1) % 12) + 1
            aspected_houses.append(str(aspected_house))
        archetype = _archetype.get(p.name, "")
        lines.append(
            f"  {p.name} in house {p.house} — aspects houses "
            f"{' + '.join(aspected_houses)} ({archetype})"
        )
    return "\n".join(lines)


def format_planet_nakshatras_for_prompt(chart: "Chart") -> str:
    """Nakshatra placement report per planet (Issue #59).

    For each of the 7 luminary+non-luminary planets, emit the planet's
    nakshatra + a compact archetype hint. Classical astrologers use
    nakshatra placement as a finer-grained layer than sign — Sun in Bharani
    reads very differently than Sun in Krittika even though both are in
    Aries. Currently the LLM only sees Moon's nakshatra (via life_chapters);
    this block exposes ALL planets' nakshatras.
    """
    lines = ["--- PLANET NAKSHATRA PLACEMENTS (finer layer than sign) ---"]
    for p in chart.planets:
        if p.name in ("Rahu", "Ketu"):
            continue
        archetype = _NAKSHATRA_ARCHETYPE_SHORT.get(p.nakshatra, "")
        note = f" — {archetype}" if archetype else ""
        # Pada included since #209. The landing page has always advertised
        # "positions in nakshatra padas"; until the pada was computed there
        # was nothing to advertise. It is also the quarter that selects the
        # Navamsha sign, so it is the useful half of the placement.
        pada = f" pada {p.pada}" if p.pada else ""
        lines.append(f"  {p.name} in {p.nakshatra}{pada}{note}")
    return "\n".join(lines)


def format_manglik_for_prompt(details: ManglikDetails) -> str:
    """Tiny LLM hint for the Relationships section — only inject when relevant.

    Carries NO verdict. The single Manglik assertion for the prompt is emitted
    by format_flags_for_prompt() (see MANGLIK_ASSERTION_PREFIX); this block only
    supplies the severity grade, the cancelling/mitigating evidence and the
    phrasing directives for the Relationships section. Stays ~80-180 tokens.
    Sources are deliberately omitted so the LLM can't echo them back as
    user-facing "per Phaladeepika" jargon. Classical citations live in the
    structured UI panel.
    """
    if details.effective_status == "none":
        return ""

    lines = [
        "--- MANGLIK DETAIL (supporting evidence only) ---",
        "The Manglik verdict is stated once in the Vedic flags block above — "
        "do not restate a different one.",
        # Severity reaches the LLM ONLY here. Without it an 8th-house 'high'
        # dosha and a 2nd-house 'low' one read in the same register.
        # The tiers are Bhagya's own weighting, not a classical grading (#429), so
        # the line says "internal" and bars attributing them to scripture — but not
        # "editorial", which the model would echo into the reading as a disclaimer.
        f"Severity: {details.severity} — an internal weighting of the qualifying "
        "houses (7th/8th highest, 1st/4th/12th moderate, 2nd alone lowest), reduced "
        "one grade (never below low) when only the Venus axis qualifies; not a "
        "classical grade. Match the weight of your language to this grade: do not "
        "treat a low severity as an emergency, nor a high one as trivial.",
    ]

    cancels = [r for r in details.cancellations if r.effect == "cancels"]
    mitigates = [r for r in details.cancellations if r.effect == "mitigates"]

    if cancels:
        lines.append("Reasons the dosha is cancelled in this chart:")
        for r in cancels:
            lines.append(f"  • {r.description}")
    if mitigates:
        lines.append("Reasons the dosha is softened in this chart:")
        for r in mitigates:
            lines.append(f"  • {r.description}")
    if not cancels and not mitigates:
        # A Venus-axis-only chart is downgraded to "mitigated" with no rule behind
        # it, so the bare "no reasons apply" line would contradict the flags block's
        # "its effect is reduced". Name the actual cause of the reduction here —
        # without restating the verdict, which this block never asserts.
        if details.venus_axis_only:
            lines.append(
                "No classical cancellation or mitigation rule applies to this chart. Its "
                "reduced weight comes from the axis alone: Mars qualifies only from Venus, "
                "not from the Lagna or the Moon — a supplementary marriage-specific "
                "indicator rather than a full Mangal Dosha."
            )
        else:
            lines.append(
                "No classical cancellation or mitigation reasons apply to this chart."
            )

    if details.effective_status == "cancelled":
        lines.append(
            "→ Tell the seeker the dosha is present but cancelled, and paraphrase the "
            "reason(s) above in plain words. Do not alarm. Do NOT name classical texts, "
            "chapters, or sanskrit shastra — those live in the UI panel separately."
        )
    elif details.effective_status == "mitigated":
        lines.append(
            "→ Acknowledge the dosha honestly but explain the softening reason in plain words. "
            "Avoid 'your marriage will fail'-style framing. Do NOT name classical texts."
        )
    else:
        lines.append(
            "→ Mention the dosha honestly as 'something to be aware of', not as destiny. "
            "The traditional remedy — a partner who also carries the dosha — classically "
            "holds only when both carry it at comparable strength, so give it as that "
            "condition and never as 'marry any Manglik'. Only this one chart is in scope, "
            "so say comparability is settled by a compatibility check of both charts. "
            "Do NOT predict marital failure. Do NOT name classical texts."
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class SadeSatiDetails:
    """Sade Sati — phase + timing + Saturn position, for the educational panel.

    Timing fields are computed only when active (otherwise None):
      - overall_start: when Saturn first entered the 12th from natal Moon
      - overall_end:   when Saturn will exit the 2nd from natal Moon
      - phase_end:     when the current phase (rising/peak/setting) ends

    Ashtama Shani (Saturn 8th from Moon) and Kantaka Shani (4th) are distinct
    ~2.5y Saturn transits — surface them here so /sade-sati-check doesn't
    silently tell users they're clear when they're actually in one of these.
    """

    is_active: bool
    phase: str | None                  # "rising" | "peak" | "setting"
    saturn_house_from_moon: int        # 1..12
    overall_start: date_ | None
    overall_end: date_ | None
    phase_end: date_ | None
    ashtama_shani: bool = False        # Saturn 8th from Moon (~2.5y)
    kantaka_shani: bool = False        # Saturn 4th from Moon (~2.5y)


def compute_sade_sati_details(chart: Chart, when: datetime | None = None) -> SadeSatiDetails:
    """Sade Sati state + start/end dates when active."""
    flags = compute_vedic_flags(chart, when)
    if not flags.sade_sati:
        return SadeSatiDetails(
            is_active=False, phase=None,
            saturn_house_from_moon=flags.saturn_house_from_natal_moon,
            overall_start=None, overall_end=None, phase_end=None,
            ashtama_shani=flags.ashtama_shani,
            kantaka_shani=flags.kantaka_shani,
        )

    moon_idx = _rashi_index(next(p for p in chart.planets if p.name == "Moon").rashi)
    anchor = (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))
    current_house = flags.saturn_house_from_natal_moon

    phase_end = _saturn_house_change_forward(moon_idx, anchor, current_house)
    overall_start = _walk_back_to_ss_entry(moon_idx, anchor, current_house)
    overall_end = _walk_forward_to_ss_exit(moon_idx, anchor, current_house)

    return SadeSatiDetails(
        is_active=True,
        phase=flags.sade_sati_phase,
        saturn_house_from_moon=current_house,
        overall_start=overall_start,
        overall_end=overall_end,
        phase_end=phase_end,
        ashtama_shani=flags.ashtama_shani,
        kantaka_shani=flags.kantaka_shani,
    )


def _saturn_house_from_natal_moon(moon_idx: int, at: datetime) -> int:
    """Compute Saturn's house (from natal Moon) at moment `at` — single swisseph call."""
    jd = swe.julday(at.year, at.month, at.day, at.hour + at.minute / 60.0)
    pos, _ = swe.calc_ut(jd, swe.SATURN, swe.FLG_SIDEREAL)
    sign_idx = int(float(pos[0]) // 30)
    return ((sign_idx - moon_idx) % 12) + 1


# Saturn retrogrades ~140 days per year. When Saturn is exiting a house, it
# often retrogrades briefly back into that house before continuing forward.
# A naive "walk until Saturn leaves once" gets the FIRST exit, not the true
# last day — reported Sade Sati start/end dates could be 6-12 months off.
_SATURN_RETROGRADE_LOOKAHEAD = timedelta(days=220)


def _saturn_house_change_forward(moon_idx: int, start: datetime, target_house: int) -> date_:
    """Find the definitive last day Saturn is in `target_house`, retrograde-aware.

    Two-pass: first the classical weekly-stride-then-bisect for the initial
    boundary. Then look ahead ~220 days (Saturn's max retrograde swing) and
    if Saturn re-enters `target_house`, keep pushing the boundary forward
    until we find a genuinely quiet 220-day window with no re-entry.
    Bounded at 3 years (Saturn changes sign every ~2.5 years).
    """
    cursor = start
    step = timedelta(days=7)
    boundary_dt: datetime | None = None
    for _ in range(52 * 3):
        cursor += step
        if _saturn_house_from_natal_moon(moon_idx, cursor) != target_house:
            lo, hi = cursor - step, cursor
            for _ in range(8):
                mid = lo + (hi - lo) / 2
                if _saturn_house_from_natal_moon(moon_idx, mid) == target_house:
                    lo = mid
                else:
                    hi = mid
            boundary_dt = lo
            break
    if boundary_dt is None:
        return cursor.date()

    # Retrograde-aware pass: search ahead of the boundary for a re-entry.
    while True:
        lookahead = boundary_dt + _SATURN_RETROGRADE_LOOKAHEAD
        re_entry_dt: datetime | None = None
        probe = boundary_dt + step
        while probe <= lookahead:
            if _saturn_house_from_natal_moon(moon_idx, probe) == target_house:
                re_entry_dt = probe
                break
            probe += step
        if re_entry_dt is None:
            return boundary_dt.date()
        # Saturn re-entered — find the new last-in day starting from re_entry.
        cursor = re_entry_dt
        for _ in range(52 * 3):
            cursor += step
            if _saturn_house_from_natal_moon(moon_idx, cursor) != target_house:
                lo, hi = cursor - step, cursor
                for _ in range(8):
                    mid = lo + (hi - lo) / 2
                    if _saturn_house_from_natal_moon(moon_idx, mid) == target_house:
                        lo = mid
                    else:
                        hi = mid
                boundary_dt = lo
                break
        else:
            return cursor.date()


def _saturn_house_change_backward(moon_idx: int, start: datetime, target_house: int) -> date_:
    """First day going BACK that Saturn was in `target_house`, retrograde-aware.

    Mirror of forward: initial boundary, then look BACK ~220 days for a
    prior-entry; if found, push the boundary earlier and repeat.
    """
    cursor = start
    step = timedelta(days=7)
    boundary_dt: datetime | None = None
    for _ in range(52 * 3):
        cursor -= step
        if _saturn_house_from_natal_moon(moon_idx, cursor) != target_house:
            lo, hi = cursor, cursor + step  # lo out, hi in
            for _ in range(8):
                mid = lo + (hi - lo) / 2
                if _saturn_house_from_natal_moon(moon_idx, mid) == target_house:
                    hi = mid
                else:
                    lo = mid
            boundary_dt = hi
            break
    if boundary_dt is None:
        return cursor.date()

    # Retrograde-aware pass: look further back for an earlier entry.
    while True:
        lookback = boundary_dt - _SATURN_RETROGRADE_LOOKAHEAD
        prior_entry_dt: datetime | None = None
        probe = boundary_dt - step
        while probe >= lookback:
            if _saturn_house_from_natal_moon(moon_idx, probe) == target_house:
                prior_entry_dt = probe
                break
            probe -= step
        if prior_entry_dt is None:
            return boundary_dt.date()
        # Saturn was in target house earlier — find the first-in day.
        cursor = prior_entry_dt
        for _ in range(52 * 3):
            cursor -= step
            if _saturn_house_from_natal_moon(moon_idx, cursor) != target_house:
                lo, hi = cursor, cursor + step
                for _ in range(8):
                    mid = lo + (hi - lo) / 2
                    if _saturn_house_from_natal_moon(moon_idx, mid) == target_house:
                        hi = mid
                    else:
                        lo = mid
                boundary_dt = hi
                break
        else:
            return cursor.date()


def _walk_back_to_ss_entry(moon_idx: int, start: datetime, current_house: int) -> date_:
    """Walk back through SS phases to find when Saturn first entered 12th from Moon.

    Sequence (in reverse): setting (h=2) → peak (h=1) → rising (h=12).
    Each phase is ~2.5 years, so worst-case 3 phase boundaries to cross.
    """
    cursor = start
    house = current_house
    while house in {12, 1, 2}:
        phase_start = _saturn_house_change_backward(moon_idx, cursor, house)
        cursor = datetime.combine(phase_start, datetime.min.time(), tzinfo=ZoneInfo("UTC"))
        if house == 12:
            return phase_start  # rising-phase entry = overall Sade Sati start
        # Step one day earlier to check the previous house.
        previous_day = cursor - timedelta(days=1)
        house = _saturn_house_from_natal_moon(moon_idx, previous_day)
    return cursor.date()


def _walk_forward_to_ss_exit(moon_idx: int, start: datetime, current_house: int) -> date_:
    """Walk forward through SS phases to find when Saturn exits the 2nd from Moon."""
    cursor = start
    house = current_house
    while house in {12, 1, 2}:
        phase_end_date = _saturn_house_change_forward(moon_idx, cursor, house)
        cursor = datetime.combine(phase_end_date, datetime.min.time(), tzinfo=ZoneInfo("UTC")) + timedelta(days=1)
        if house == 2:
            return phase_end_date  # setting-phase exit = overall Sade Sati end
        house = _saturn_house_from_natal_moon(moon_idx, cursor)
    return cursor.date()


# ---------------------------------------------------------------------------
# Vimshottari Dasha — 120-year planetary period system
# ---------------------------------------------------------------------------


# Standard 9-planet order for Vimshottari (Ketu first by convention).
_VIM_ORDER: tuple[str, ...] = (
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
)

# Years allotted to each planet's Mahadasha (sum = 120).
_VIM_YEARS: dict[str, int] = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

# Each nakshatra's ruling planet — determines which Maha starts at birth.
# (Pattern cycles through _VIM_ORDER every 9 nakshatras: Ashwini→Ketu,
# Bharani→Venus, Krittika→Sun, etc.)
_NAKSHATRA_LORDS: dict[str, str] = {
    NAKSHATRAS[i]: _VIM_ORDER[i % 9] for i in range(27)
}

# Length of a year in days used for Dasha calculation. Vedic tradition uses
# the solar (tropical) year ≈ 365.2425 days; close enough to Julian 365.25
# for our purposes. We use 365.25 — matches Future Point, JHora.
_DAYS_PER_YEAR: float = 365.25


@dataclass(frozen=True)
class DashaPeriod:
    """One Vimshottari period (Mahadasha or Antardasha)."""

    lord: str
    start: date_
    end: date_
    years: float       # nominal duration of this period (Maha years, or Antar fraction)


@dataclass(frozen=True)
class DashaState:
    """Currently-active Mahadasha + Antardasha + lookaheads."""

    mahadasha: DashaPeriod
    antardasha: DashaPeriod
    upcoming_antardashas: tuple[DashaPeriod, ...]  # remaining Antardashas in this Maha
    next_mahadasha: DashaPeriod | None              # the Maha after the current one
    # The whole Mahadasha sequence from birth forward, and where the active one
    # sits in it. `compute_dasha_state` has always built this list to find the
    # active period and then thrown it away; the redesign's proportional
    # timeline needs the periods either side, so it is carried out rather than
    # recomputed. No extra Swiss Ephemeris work and no extra arithmetic — the
    # same objects that were already in memory.
    sequence: tuple[DashaPeriod, ...] = ()
    active_index: int = 0


def compute_dasha_state(natal: Chart, when: datetime | None = None) -> DashaState:
    """Find the active Mahadasha + Antardasha at the given moment.

    Algorithm:
      1. Moon's absolute sidereal longitude → nakshatra index + fractional position
      2. Nakshatra → first Dasha lord; fractional position → portion already
         consumed at birth (so the first Maha is shorter than its nominal years)
      3. Walk forward from birth date through full Mahadashas to find the
         one covering `when`. Then sub-divide it into Antardashas the same way.
    """
    moment = (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC")).date()
    moon = next(p for p in natal.planets if p.name == "Moon")
    moon_abs_long = _rashi_index(moon.rashi) * 30.0 + moon.longitude

    nak_span = 360.0 / 27.0
    nak_idx = int(moon_abs_long // nak_span)
    nak_position = (moon_abs_long % nak_span) / nak_span   # 0..1 within the nakshatra
    first_lord = _NAKSHATRA_LORDS[NAKSHATRAS[nak_idx]]
    first_lord_years = _VIM_YEARS[first_lord]

    # Maha already "consumed" at birth — the chunk between nakshatra start and Moon's position.
    consumed_at_birth_years = nak_position * first_lord_years
    first_remaining_years = first_lord_years - consumed_at_birth_years

    birth_date = natal.birth_utc.date()

    # Build forward sequence of Mahadashas (first is partial, rest are full).
    periods: list[DashaPeriod] = []
    cursor = birth_date
    end = cursor + timedelta(days=first_remaining_years * _DAYS_PER_YEAR)
    periods.append(DashaPeriod(first_lord, cursor, end, first_remaining_years))
    cursor = end

    start_idx = _VIM_ORDER.index(first_lord)
    # Keep extending until we pass `moment` by at least one more full cycle's worth.
    while cursor < moment + timedelta(days=120 * _DAYS_PER_YEAR):
        for i in range(1, 10):
            lord = _VIM_ORDER[(start_idx + i) % 9]
            yrs = _VIM_YEARS[lord]
            new_end = cursor + timedelta(days=yrs * _DAYS_PER_YEAR)
            periods.append(DashaPeriod(lord, cursor, new_end, float(yrs)))
            cursor = new_end
            if cursor > moment + timedelta(days=60 * _DAYS_PER_YEAR):
                break
        # Reset the inner ordering pointer to continue cycling.
        start_idx = (start_idx + 9) % 9  # always 0; restart from first_lord
        # Avoid infinite loop — break once we've definitely passed `moment`.
        if cursor > moment + timedelta(days=60 * _DAYS_PER_YEAR):
            break

    # Identify the active Mahadasha.
    active_maha = next((p for p in periods if p.start <= moment <= p.end), periods[0])
    active_idx = periods.index(active_maha)
    next_maha = periods[active_idx + 1] if active_idx + 1 < len(periods) else None

    # Sub-divide active Maha into Antardashas. The birth Mahadasha — and only
    # it — is subdivided over its FULL nominal duration rather than the
    # remaining balance, per Rao §16.3 (#204); see _build_antardashas. Its
    # notional start sits before birth, so the sub-periods already finished by
    # the time the person was born are dropped: they are real in the scheme
    # and simply not part of this life.
    if active_idx == 0:
        antardashas = [
            p for p in _build_antardashas(
                active_maha,
                full_years=first_lord_years,
                nominal_start=birth_date - timedelta(
                    days=consumed_at_birth_years * _DAYS_PER_YEAR
                ),
            )
            if p.end > active_maha.start
        ]
    else:
        antardashas = _build_antardashas(active_maha)
    active_antar = next((p for p in antardashas if p.start <= moment <= p.end), antardashas[0])
    active_antar_idx = antardashas.index(active_antar)
    upcoming = tuple(antardashas[active_antar_idx + 1 :])

    return DashaState(
        mahadasha=active_maha,
        antardasha=active_antar,
        upcoming_antardashas=upcoming,
        next_mahadasha=next_maha,
        sequence=tuple(periods),
        active_index=active_idx,
    )


def dasha_timeline(state: DashaState, span: int = 6) -> tuple[DashaPeriod, ...]:
    """A window of `span` Mahadashas centred on the active one.

    The redesign renders the Vimshottari sequence as one horizontal strip whose
    segments are proportional to each period's LENGTH — Ketu's 7 years next to
    Venus's 20 — so the reader can see at a glance that they are in a long
    period or a short one. That only reads if the window includes what came
    before and what is coming.

    Two periods back and the rest forward, because a chart is read facing
    forward: the past is context, the future is the question. Clamped at both
    ends, so a young chart (active period at index 0 or 1) still gets `span`
    segments by taking more from the future, and a sequence shorter than
    `span` returns whole.

    Pure list arithmetic over what `compute_dasha_state` already built — no
    ephemeris calls, no dates recomputed.
    """
    seq = state.sequence
    if not seq:
        return ()
    if len(seq) <= span:
        return seq
    start = max(0, min(state.active_index - 2, len(seq) - span))
    return seq[start:start + span]


def _build_antardashas(
    maha: DashaPeriod,
    *,
    full_years: float | None = None,
    nominal_start: "date_ | None" = None,
) -> list[DashaPeriod]:
    """9 sub-periods within `maha`, starting with the Maha lord, weighted by Vimshottari years.

    `full_years` / `nominal_start` exist for the BIRTH Mahadasha (#204), the
    only one a person enters part-way through. Rao is explicit (§16.3):

        "In the case of the first dasa, we don't divide the remainder at birth
         ... Instead, we divide the complete duration of the first dasa ...
         So a few antardasas may be over before birth and only a few
         antardasas may be left at birth."

    Until this fix the birth Mahadasha's `years` (the REMAINING balance) and
    `start` (the birth date) were used, which squeezed all nine antardashas
    into the leftover span. Someone with 2.2 years of a 7-year Mars dasha left
    got nine antardashas crammed into 2.2 years instead of the correct few
    survivors of a 7-year subdivision — wrong dates for everyone still in
    their birth Mahadasha, and usually the wrong lord as well.

    Passing both makes the subdivision run over the whole nominal dasha,
    anchored where it notionally began (before birth). The caller then drops
    the sub-periods that were already over at birth.
    """
    span_years = maha.years if full_years is None else full_years
    cursor = maha.start if nominal_start is None else nominal_start
    nominal_end = cursor + timedelta(days=span_years * _DAYS_PER_YEAR)

    start_idx = _VIM_ORDER.index(maha.lord)
    out: list[DashaPeriod] = []
    for i in range(9):
        sub_lord = _VIM_ORDER[(start_idx + i) % 9]
        sub_years = (span_years * _VIM_YEARS[sub_lord]) / 120.0
        new_end = cursor + timedelta(days=sub_years * _DAYS_PER_YEAR)
        # Clamp the last sub-period to the exact span end to avoid float drift.
        if i == 8:
            new_end = maha.end if full_years is None else nominal_end
        out.append(DashaPeriod(sub_lord, cursor, new_end, sub_years))
        cursor = new_end
    return out


@dataclass(frozen=True)
class LifeChapter:
    """One Mahadasha period framed as an age window (for natal Life Stages section)."""

    lord: str             # Vimshottari dasha lord (Vedic-technical, hidden from output)
    start_age: float      # seeker's age at start
    end_age: float        # seeker's age at end
    phase: str = "past"   # "past" | "current" | "upcoming" — LLM uses this to pick tense


def compute_life_chapters(natal: Chart, until_age: float = 80.0) -> list[LifeChapter]:
    """Return all Mahadasha periods from birth up to `until_age`, in age-window form.

    Each chapter is tagged with `phase` (past / current / upcoming) based on
    the seeker's current age at chart-generation time — this is what lets the
    LLM correctly pick tense ("looking back" vs "right now" vs "the years
    ahead") without duplicating the current chapter or misattributing it.
    """
    moon = next(p for p in natal.planets if p.name == "Moon")
    moon_abs_long = _rashi_index(moon.rashi) * 30.0 + moon.longitude

    nak_span = 360.0 / 27.0
    nak_idx = int(moon_abs_long // nak_span)
    nak_position = (moon_abs_long % nak_span) / nak_span
    first_lord = _NAKSHATRA_LORDS[NAKSHATRAS[nak_idx]]
    first_lord_years = _VIM_YEARS[first_lord]
    first_remaining_years = first_lord_years * (1 - nak_position)

    birth_date = natal.birth_utc.date()
    today = date_.today()
    current_age = (today - birth_date).days / _DAYS_PER_YEAR

    def _phase_for(start: float, end: float) -> str:
        if end <= current_age:
            return "past"
        if start > current_age:
            return "upcoming"
        return "current"

    chapters: list[LifeChapter] = []

    cursor = birth_date
    cursor_end = cursor + timedelta(days=first_remaining_years * _DAYS_PER_YEAR)
    first_start = (cursor - birth_date).days / _DAYS_PER_YEAR
    first_end = (cursor_end - birth_date).days / _DAYS_PER_YEAR
    chapters.append(LifeChapter(
        lord=first_lord,
        start_age=first_start,
        end_age=first_end,
        phase=_phase_for(first_start, first_end),
    ))
    cursor = cursor_end

    start_idx = _VIM_ORDER.index(first_lord)
    i = 1
    while True:
        lord = _VIM_ORDER[(start_idx + i) % 9]
        yrs = _VIM_YEARS[lord]
        cursor_end = cursor + timedelta(days=yrs * _DAYS_PER_YEAR)
        start_age = (cursor - birth_date).days / _DAYS_PER_YEAR
        end_age = (cursor_end - birth_date).days / _DAYS_PER_YEAR
        chapters.append(LifeChapter(
            lord=lord,
            start_age=start_age,
            end_age=end_age,
            phase=_phase_for(start_age, end_age),
        ))
        cursor = cursor_end
        i += 1
        if end_age >= until_age:
            break
    return chapters


_MAHADASHA_ARCHETYPE: dict[str, str] = {
    "Sun":     "authority + visibility + father-figure influence + confidence-building; conflict with hierarchy possible",
    "Moon":    "emotional life + home + mother + public-facing warmth; mood cycles matter, nurturing central",
    "Mars":    "energy + drive + conflict + sports/military/property; physical risks, disputes, courage-tested",
    "Rahu":    "ambition + unconventional paths + foreign/tech pull + sudden rise-or-fall; the outsider chapter, ambition outpaces clarity, confusion-into-breakthrough pattern",
    "Jupiter": "wisdom + expansion + dharmic authority + marriage-often-triggers + wealth-through-respect + teaching/advisory work; the trust chapter",
    "Saturn":  "discipline + slow structural building + delay-then-elevation + service + longevity; the long-tenure chapter; unglamorous foundations that compound",
    "Mercury": "communication + trade + learning + networks + business dealmaking + analytical career-building; often money-and-career-building phase",
    "Ketu":    "detachment + spirituality + retreat + unexpected loss or letting-go + moksha themes; the inward chapter, worldly pursuits feel hollow",
    "Venus":   "relationships + marriage + luxury + arts + partnerships + material comfort; the relational chapter, strongest marriage-trigger period",
}


def format_life_chapters_for_prompt(
    chapters: list[LifeChapter],
    current_antardasha: "DashaPeriod | None" = None,
) -> str:
    """Plain-English Mahadasha sequence for the natal LLM.

    Ages rendered as whole years. Each chapter tagged [PAST], [NOW], or
    [LATER] so the LLM picks the right tense. Each chapter also gets an
    ARCHETYPE hint — the flavour of the ruling planet in plain English,
    so the LLM can weave chapter-specific character into the prose
    without naming the planet itself.

    If `current_antardasha` is provided, an additional "CURRENT SUB-WINDOW"
    line appends at the end — used to sharpen the [NOW] chapter's specific
    right-now-ish months (Mahadasha is 6-19 years; antardasha is months to
    a couple of years and has its own distinctive flavour).
    """
    _tag = {"past": "[PAST]", "current": "[NOW]", "upcoming": "[LATER]"}
    lines = ["Vimshottari Mahadasha sequence (lord per age range — for reasoning only, do NOT name planets in output. The ARCHETYPE hint is the flavour of that chapter — weave those specific themes into the prose):"]
    for c in chapters:
        start = int(round(c.start_age))
        end = int(round(c.end_age))
        archetype = _MAHADASHA_ARCHETYPE.get(c.lord, "")
        lines.append(f"- Age {start} to {end}: {c.lord} {_tag[c.phase]} — ARCHETYPE: {archetype}")
    if current_antardasha is not None:
        sub_arch = _MAHADASHA_ARCHETYPE.get(current_antardasha.lord, "")
        lines.append(
            f"\nCURRENT SUB-WINDOW (within the [NOW] chapter): "
            f"{current_antardasha.lord} sub-period from {current_antardasha.start.isoformat()} "
            f"to {current_antardasha.end.isoformat()} — ARCHETYPE: {sub_arch}"
        )
    return "\n".join(lines)


def format_dasha_for_prompt(state: DashaState) -> str:
    """One-block summary of the active Dasha for inclusion in LLM user message."""
    m = state.mahadasha
    a = state.antardasha
    lines = [
        "Active Vimshottari Dasha (120-year planetary-period system):",
        f"- Mahadasha: {m.lord} ({m.start.isoformat()} to {m.end.isoformat()})",
        f"- Antardasha: {a.lord} ({a.start.isoformat()} to {a.end.isoformat()})",
    ]
    if state.next_mahadasha:
        lines.append(
            f"- Next Mahadasha (after current): {state.next_mahadasha.lord} "
            f"starting {state.next_mahadasha.start.isoformat()}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gochar (transit) impacts — slow movers' current placement + favourability
# ---------------------------------------------------------------------------


# Classical favourability per (planet, house from Lagna). Houses 3/6/10/11
# generally support malefics (Saturn especially); 5/9/2/11 favour benefics.
# Anything not listed defaults to neutral.
# Gochara results by house FROM THE NATAL MOON — B.V. Raman, "Astrology for
# Beginners", Ch. XII "Transits or Gochara", benefic/malefic table (p.101).
# Transcribed from `pdftotext -layout` of the copy in data/; the per-house
# prose on pp.98-100 agrees with the table for all four planets here.
#
# FROM THE MOON, not the Lagna. Two verbatim lines from the same chapter, both
# needing no editorial hand: "The passage of planets through certain angular
# positions from the radical Moon is technically termed Gochara", and "The
# following results are produced by the different planets while transiting the
# different signs from Janma Rasi (Radical Moon)."
#
# An earlier draft of this comment quoted a THIRD line as "the Moon and the
# birth [rashi] play a prominent part". The book says "the birth
# CONSTELLATION", and Raman uses "constellation" for nakshatra throughout — so
# the bracket quietly turned a statement about the birth star into one about
# the birth sign. The doctrine was right and the evidence for it was doctored.
# If a quotation needs a bracket to say what you want, find a better quotation.
#
# This file already encoded the from-the-Moon rule elsewhere and disagreed with
# itself: Sade Sati is computed from the Moon at line ~543, and
# knowledge/vedic_reference.md §2 and the Ashtama Shani note both define
# themselves as "from natal Moon". Only this lookup used the Lagna.
#
# Only the four slow movers are listed because only they are computed here.
# Raman backs that scope: "the transiting effects of the slow moving ones,
# viz., Jupiter, Saturn and Rahu are universally held to be most powerful."
# His full table (all nine, houses from the Moon) is recorded in
# knowledge/vedic_reference.md §2A so the rest is not lost.
#
# Every house 1-12 is present for each planet. There is deliberately no
# "neutral" default left reachable: the previous table listed 3-5 houses per
# planet and silently called the other 7-9 neutral, which is not a claim
# Raman makes anywhere — he classifies all twelve.
_GOCHAR_BENEFIC_HOUSES: dict[str, frozenset[int]] = {
    "Jupiter": frozenset({2, 5, 7, 9, 11}),
    "Saturn":  frozenset({3, 6, 11}),
    "Rahu":    frozenset({3, 6, 11}),
    # Raman brackets Rahu and Ketu on one row of the table with one set of
    # values; they are not given separate lists.
    "Ketu":    frozenset({3, 6, 11}),
}

_GOCHAR_FAVOURABILITY: dict[tuple[str, int], str] = {
    (planet, house): ("favorable" if house in benefic else "challenging")
    for planet, benefic in _GOCHAR_BENEFIC_HOUSES.items()
    for house in range(1, 13)
}


# --- Gochara for a whole rashi, all nine grahas (#513) -----------------------
#
# `_GOCHAR_BENEFIC_HOUSES` above carries only the four slow movers, because
# only those are computed for a natal chart. Its own comment records why the
# rest was left: "His full table (all nine, houses from the Moon) is recorded
# in knowledge/vedic_reference.md §2A so the rest is not lost." This is that
# table, transcribed from §2A, for the daily Rashifal -- which can use it
# because the Rashifal is keyed on janma rashi, and Gochara is measured from
# the janma rashi by definition.
#
# Raman, verbatim via §2A: "The passage of planets through certain angular
# positions from the radical Moon is technically termed Gochara." Source:
# B.V. Raman, *Astrology for Beginners*, Ch. XII, benefic/malefic table p.101
# (line 5203+ under `pdftotext -layout` in the copy in data/). §2A records two
# OCR repairs it resolved by cross-reading the prose, and Rahu and Ketu share
# ONE row there -- Raman gives them no separate lists.
#
# All twelve houses are classified for every graha, with no reachable
# "neutral": the four-planet table above documents that trap, and the same
# reasoning applies here -- Raman classifies all twelve, so a default of
# neutral would be a claim he does not make.
_GOCHARA_BENEFIC_FROM_MOON: dict[str, frozenset[int]] = {
    "Sun":     frozenset({3, 6, 10, 11}),
    "Moon":    frozenset({1, 3, 6, 7, 10, 11}),
    "Mars":    frozenset({3, 6, 11}),
    "Mercury": frozenset({2, 4, 6, 8, 10, 11}),
    "Jupiter": frozenset({2, 5, 7, 9, 11}),
    "Venus":   frozenset({1, 2, 3, 4, 5, 8, 9, 11, 12}),
    "Saturn":  frozenset({3, 6, 11}),
    "Rahu":    frozenset({3, 6, 11}),
    "Ketu":    frozenset({3, 6, 11}),
}

# Raman's own weighting of which transits dominate, quoted in the four-planet
# table above: "the transiting effects of the slow moving ones, viz., Jupiter,
# Saturn and Rahu are universally held to be most powerful." That is the ONLY
# ordering he gives, so it is the only one used -- the grahas are reported
# individually and are NEVER summed into a single score. Raman classifies each
# planet-house pair and supplies no aggregation rule; inventing weights to
# produce one number would be an unsourced rule wearing a citation.
_GOCHARA_WEIGHTY = ("Saturn", "Jupiter", "Rahu")


def gochara_for_rashi(rashi_index: int, transit: "TransitSnapshot") -> list[dict]:
    """Every graha's Gochara verdict for one rashi today, strongest first.

    `rashi_index` is 0-based from Aries, i.e. the janma rashi the Rashifal is
    written for. Each entry carries the graha, the house it occupies counted
    FROM that rashi, and Raman's classification of that planet in that house.

    Returns [] rather than raising: this feeds a reading and a panel, and
    neither may fail over a decoration.
    """
    out: list[dict] = []
    try:
        # Guarded, like llm.generate_rashifal_for_rashi: `((p - r) % 12) + 1`
        # accepts any int silently, and rashi_index=12 returned an ALL-ZEROS
        # panel -- the worst-looking day possible and indistinguishable from a
        # real one. Both call sites pass range(12) today, so this is a latch,
        # not a live bug.
        if not 0 <= rashi_index < 12:
            return []
        for planet in transit.planets:
            benefic = _GOCHARA_BENEFIC_FROM_MOON.get(planet.name)
            if benefic is None:
                continue
            try:
                p_idx = RASHIS.index(planet.rashi)
            except ValueError:
                continue
            house = ((p_idx - rashi_index) % 12) + 1
            out.append({
                "planet": planet.name,
                "house": house,
                "verdict": "favourable" if house in benefic else "challenging",
                "weighty": planet.name in _GOCHARA_WEIGHTY,
            })
    except Exception:  # noqa: BLE001 - see docstring
        return []
    out.sort(key=lambda e: (not e["weighty"], e["planet"]))
    return out


# --- Per-area day ratings, from the Gochara karakas (#523) -------------------
#
# `gochara_for_rashi` gives nine verdicts and the Rashifal surfaced them as one
# number, "1 of 9 favourable" -- honest and unscannable. These are the same
# verdicts grouped by the life area each graha signifies.
#
# THE KARAKA SETS ARE THE WHOLE Karakas: FIELD, NOT ITS FIRST LINE. The first
# version of this table dropped Mercury from Health, Mars from Relationships
# and Saturn from Work, and QA found why: every dropped graha was one whose
# NAME falls on the wrap continuation of a two-line markdown paragraph. The
# giveaway was Jupiter at houses.md:296 -- kept, because the word "Jupiter"
# ends line 296, while its own qualifier "(dharmic profession)" and Saturn two
# words later sit on 297 and were dropped. No editorial rule produces that; a
# line-wise read does. The sets below are taken from the full field:
#
#   Work           10th Karma Bhava   houses.md:296-297  Sun, Mercury, Jupiter,
#                                                        Saturn
#   Money          2nd Dhana          houses.md:83-84    Jupiter, Mercury, Venus
#                  + 11th Labha       houses.md:336      (Jupiter, Mercury again)
#   Relationships  7th Kalatra        houses.md:217-218  Venus, Jupiter, Mars
#   Health         6th Roga           houses.md:194-195  Mars, Saturn, Mercury
#                  + 1st Tanu         houses.md:51       + Sun
#
# A CHOICE OF TABLE WAS MADE AND IT IS NOT PURELY A SOURCING ONE. houses.md:611
# redirects "Karakas per house" to vedic_reference.md §5A.2, which gives ONE
# Naisargika karaka per house: 10th Mercury, 2nd/11th Jupiter, 7th Venus, 6th
# Mars, 1st Sun. Both tables are Naisargika, so Rao's warning at §5A.1 -- "One
# should not use the three types of karakas in a mixed-up way" -- is about
# mixing Naisargika with Chara and Sthira and does not forbid the fuller list.
#
# But §5A.2 would give denominators of 1 and 2, and a rating that reads 0/1 or
# 1/1 is a binary, not a scale. So the fuller per-house field is used BECAUSE
# IT PRODUCES A USABLE DENOMINATOR, which is a product reason and not a
# scriptural one. Saying so here rather than implying the corpus settled it.
# Worth an astro-auditor ruling: if §5A.2 is meant to be canonical for this,
# the feature should be re-shaped around 1-2 denominators rather than quietly
# using a different list.
#
# A SECOND, SEPARATE CHOICE, for the same astro-auditor ruling: several houses
# are multi-topic, and a graha is listed there for ONE facet that is not always
# the facet of the area it is counted under. Three assignments cite a different
# facet than the area's name suggests:
#   * Mercury under Health -- houses.md:194-195 gives Mercury at the 6th as
#     "debts / accounts", not health.
#   * Sun under Health -- houses.md:51 gives Sun at the 1st as "soul-atma", not
#     bodily health (the 1st is in the set for the body; the Sun's own entry
#     there is the self).
#   * Venus under Money -- houses.md:83-84 gives Venus at the 2nd as "family
#     comfort", where Jupiter is the one given as "wealth".
# Each is in the corpus's Karakas: field for a house the area counts, so none is
# invented; but the reader sees "Health" or "Money" and not the facet. The karaka
# sets above are deliberately NOT changed here -- that is the astro-auditor's
# call -- this only records that the area label is wider than the facet cited.
#
# NONE OF THE SIX LINES CARRIES ITS OWN CITATION. The [Raman, Ch. IV, p. 36]
# style citations near them attach to neighbouring claims -- longevity,
# Maraka, Kendra/Digbala -- not to the Karakas: fields. houses.md:616
# describes the file as "Classical significations cross-verified ... where
# Raman was brief". The earlier claim that these lists are "cited to Raman with
# page numbers" was wrong and is corrected in the PR body.
#
# A COUNT, NEVER A SCORE. Raman classifies each planet-house pair and supplies
# no aggregation rule (verified against vedic_reference.md §2A, which is a
# table plus prose and gives none). Turning verdicts into stars would be an
# invented weighting wearing a citation.
#
# RELATIONSHIPS COUNTS VENUS, JUPITER AND MARS. houses.md:217-218 gives "Venus
# (spouse for men), Jupiter (husband for women), Mars (marriage in some
# traditions)". The first two are gendered and a Rashifal has no gender, so
# both are counted rather than one silently chosen; Mars is carried with the
# hedge the corpus itself uses.
_AREA_KARAKAS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("Work",          ("Sun", "Mercury", "Jupiter", "Saturn"), "10th house karakas"),
    ("Money",         ("Jupiter", "Mercury", "Venus"), "2nd and 11th house karakas"),
    ("Relationships", ("Venus", "Jupiter", "Mars"), "7th house karakas"),
    ("Health",        ("Mars", "Saturn", "Mercury", "Sun"), "6th and 1st house karakas"),
)


def area_ratings_for_rashi(rashi_index: int, transit: "TransitSnapshot") -> list[dict]:
    """Per-area day verdicts for one rashi: [{area, favourable, total, ...}].

    Each entry counts how many of that area's karakas transit favourably from
    this rashi today, using the same `gochara_for_rashi` verdicts the reading is
    written from -- so the ratings and the prose cannot disagree.

    Returns [] rather than raising: this feeds a panel and a prompt, and neither
    may fail over a decoration.
    """
    try:
        verdicts = {e["planet"]: e for e in gochara_for_rashi(rashi_index, transit)}
        if not verdicts:
            return []
        out = []
        for area, karakas, basis in _AREA_KARAKAS:
            seen = [verdicts[k] for k in karakas if k in verdicts]
            if not seen:
                continue
            fav = [e for e in seen if e["verdict"] == "favourable"]
            out.append({
                "area": area,
                "favourable": len(fav),
                "total": len(seen),
                "basis": basis,
                "karakas": [{"planet": e["planet"], "house": e["house"],
                             "verdict": e["verdict"]} for e in seen],
            })
        return out
    except Exception:  # noqa: BLE001 - see docstring
        return []


# --- The day's remedy, for the graha weighing most against this rashi (#523) --
#
# AstroSage carries a one-line Remedy and it is a real part of why its page
# reads as specific. This is that field, sourced: Rao's per-planet good deeds,
# knowledge/remedies.md §5 (Rao §34.3), which the corpus records verbatim.
#
# WHICH graha, and why that is a selection and not an invented weighting:
# among the grahas transiting UNfavourably from this rashi, prefer the ones
# Raman names as dominant -- "the transiting effects of the slow moving ones,
# viz., Jupiter, Saturn and Rahu are universally held to be most powerful"
# (quoted in _GOCHARA_WEIGHTY). That is his ordering, not ours. Nothing is
# summed or scored; one graha is picked and named, so the reader can see which.
#
# NEVER A GEMSTONE. remedies.md §1.4 is categorical: gemstones require the
# Ascendant AND the functional benefic/malefic classification for it, and the
# wrong stone -- blue sapphire for Saturn above all -- WORSENS the affliction.
# A Rashifal has no Ascendant. This table is good deeds only, and the gemstone
# table in §4.2 is deliberately not reachable from here.
#
# EVERY CLAUSE HERE IS RAO'S, and that took a correction. remedies.md §11.2 --
# titled "Unsourced additions already in this file", written by earlier work so
# "a reader can tell the two apart" -- names four clauses in §5's table that are
# NOT in Rao §34.3: Mars "blood donation", Venus "support artists", Saturn
# "serve the elderly", Ketu "support renunciates". The first version of this
# table picked precisely those four as its second clause, under a commit
# claiming "Rao's own wording". The warning sits immediately below the table it
# warns about; the table was read and the warning was not.
#
# TWO CLAUSES ARE STILL NOT VERBATIM, disclosed rather than hidden:
#   * Jupiter. Rao (remedies.md:187) writes "a learned Brahmin/priest". Rendered
#     here as "a learned priest or teacher" -- a deliberate softening of a caste
#     referent for daily user-facing copy, NOT a sourcing claim. The act Rao
#     describes (respect and donation to a learned religious figure) is intact.
#   * Mercury. Rao writes "organizations of scholars"; "a body of scholars" is a
#     plain-English rendering of the same referent, not "a place of learning",
#     which the first version used and which is a different thing.
#
# Selection is also described accurately now: these are Rao's first and second
# clauses, or first and third where the second is a §11.2 addition. The earlier
# comment claimed "trimmed to the first clause", which no entry actually was.
_GRAHA_GOOD_DEED: dict[str, str] = {
    "Sun":     "visit a temple, or donate to one",
    "Moon":    "help a woman who needs it, or give to a music school",
    "Mars":    "take physical exercise, or give to a school gym",
    "Mercury": "seek a scholar's blessing, or give to a body of scholars",
    "Jupiter": "show respect to a learned priest or teacher, and give to them",
    "Venus":   "read poetry, or help a poet",
    "Saturn":  "do physical work yourself, or help manual labourers",
    "Rahu":    "give to research, or make a pilgrimage",
    "Ketu":    "sit in meditation",
}

# The same deeds in Hindi, matched clause for clause to the English above. An
# English SENTENCE inside a Hindi reading is the #124/#270 defect class, which
# verify_hindi_surface does not catch at this length -- a gap in the gate, not
# permission.
_GRAHA_GOOD_DEED_HI: dict[str, str] = {
    "Sun":     "\u092e\u0902\u0926\u093f\u0930 \u091c\u093e\u090f\u0901, \u092f\u093e \u092e\u0902\u0926\u093f\u0930 \u0915\u094b \u0926\u093e\u0928 \u0926\u0947\u0902",
    "Moon":    "\u0915\u093f\u0938\u0940 \u091c\u093c\u0930\u0942\u0930\u0924\u092e\u0902\u0926 \u0938\u094d\u0924\u094d\u0930\u0940 \u0915\u0940 \u0938\u0939\u093e\u092f\u0924\u093e \u0915\u0930\u0947\u0902, \u092f\u093e \u0938\u0902\u0917\u0940\u0924 \u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f \u0915\u094b \u0926\u093e\u0928 \u0926\u0947\u0902",
    "Mars":    "\u0935\u094d\u092f\u093e\u092f\u093e\u092e \u0915\u0930\u0947\u0902, \u092f\u093e \u0935\u094d\u092f\u093e\u092f\u093e\u092e\u0936\u093e\u0932\u093e \u0915\u094b \u0926\u093e\u0928 \u0926\u0947\u0902",
    "Mercury": "\u0915\u093f\u0938\u0940 \u0935\u093f\u0926\u094d\u0935\u093e\u0928 \u0915\u093e \u0906\u0936\u0940\u0930\u094d\u0935\u093e\u0926 \u0932\u0947\u0902, \u092f\u093e \u0935\u093f\u0926\u094d\u0935\u093e\u0928\u094b\u0902 \u0915\u0940 \u0938\u0902\u0938\u094d\u0925\u093e \u0915\u094b \u0926\u093e\u0928 \u0926\u0947\u0902",
    "Jupiter": "\u0915\u093f\u0938\u0940 \u0935\u093f\u0926\u094d\u0935\u093e\u0928 \u092a\u0941\u0930\u094b\u0939\u093f\u0924 \u092f\u093e \u0917\u0941\u0930\u0941 \u0915\u093e \u0938\u092e\u094d\u092e\u093e\u0928 \u0915\u0930\u0947\u0902, \u0914\u0930 \u0909\u0928\u094d\u0939\u0947\u0902 \u0926\u093e\u0928 \u0926\u0947\u0902",
    "Venus":   "\u0915\u0935\u093f\u0924\u093e \u092a\u0922\u093c\u0947\u0902, \u092f\u093e \u0915\u093f\u0938\u0940 \u0915\u0935\u093f \u0915\u0940 \u0938\u0939\u093e\u092f\u0924\u093e \u0915\u0930\u0947\u0902",
    "Saturn":  "\u0938\u094d\u0935\u092f\u0902 \u0936\u093e\u0930\u0940\u0930\u093f\u0915 \u0936\u094d\u0930\u092e \u0915\u0930\u0947\u0902, \u092f\u093e \u0936\u094d\u0930\u092e\u093f\u0915\u094b\u0902 \u0915\u0940 \u0938\u0939\u093e\u092f\u0924\u093e \u0915\u0930\u0947\u0902",
    "Rahu":    "\u0936\u094b\u0927-\u0915\u093e\u0930\u094d\u092f \u0915\u094b \u0926\u093e\u0928 \u0926\u0947\u0902, \u092f\u093e \u0924\u0940\u0930\u094d\u0925\u092f\u093e\u0924\u094d\u0930\u093e \u0915\u0930\u0947\u0902",
    "Ketu":    "\u0927\u094d\u092f\u093e\u0928 \u0915\u0930\u0947\u0902",
}

# Graha names and house ordinals in Devanagari, so the remedy's parenthetical
# attribution does not put Latin script inside a Hindi sentence. QA caught
# "(Jupiter 4th भाव)" on a brand-new line: the planet name is arguably the same
# pre-existing class as the Gochara panel, but `house_ord` was introduced by
# this change and "4th" had never appeared on a Hindi surface before. A new
# leak is not covered by a disclosure about old ones.
_GRAHA_HI: dict[str, str] = {
    "Sun": "\u0938\u0942\u0930\u094d\u092f", "Moon": "\u091a\u0902\u0926\u094d\u0930",
    "Mars": "\u092e\u0902\u0917\u0932", "Mercury": "\u092c\u0941\u0927",
    "Jupiter": "\u0917\u0941\u0930\u0941", "Venus": "\u0936\u0941\u0915\u094d\u0930",
    "Saturn": "\u0936\u0928\u093f", "Rahu": "\u0930\u093e\u0939\u0941",
    "Ketu": "\u0915\u0947\u0924\u0941",
}
_HOUSE_ORDINAL_HI: dict[int, str] = { 1: "\u092a\u0939\u0932\u0947",
    2: "\u0926\u0942\u0938\u0930\u0947", 3: "\u0924\u0940\u0938\u0930\u0947",
    4: "\u091a\u094c\u0925\u0947", 5: "\u092a\u093e\u0902\u091a\u0935\u0947\u0902",
    6: "\u091b\u0920\u0947", 7: "\u0938\u093e\u0924\u0935\u0947\u0902",
    8: "\u0906\u0920\u0935\u0947\u0902", 9: "\u0928\u094c\u0935\u0947\u0902",
    10: "\u0926\u0938\u0935\u0947\u0902",
    11: "\u0917\u094d\u092f\u093e\u0930\u0939\u0935\u0947\u0902",
    12: "\u092c\u093e\u0930\u0939\u0935\u0947\u0902",}
"""Twelve literal entries, for exactly the reason the English table below
states about itself. The first version here was `{n: f"{n}\u0935\u0947\u0902"}` -- the same
naive rule -- and it rendered "1\u0935\u0947\u0902" and "3\u0935\u0947\u0902" where Hindi wants
\u092a\u0939\u0932\u0947 and \u0924\u0940\u0938\u0930\u0947. Hindi ordinals are irregular at the same places the
English ones are (1, 2, 3, 6), so a derived rule is wrong in 4 of 12 cases --
QA found 2 of the 3 pages it rendered showing one."""

_HOUSE_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th",
                  7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}
"""Spelled out rather than derived: "3th" shipped from a naive f"{h}th" in the
first draft of remedy_for_rashi, and an ordinal rule that handles 1/2/3 but not
11/12/13 is the classic version of the same bug. Twelve entries, no rule."""


def remedy_for_rashi(rashi_index: int, transit: "TransitSnapshot",
                     lang: str = "en") -> dict | None:
    """{'planet', 'house', 'deed'} for ONE adverse transit today, or None.

    Not "the heaviest". The tiers that are SOURCED -- a Saturn Sade Sati phase
    (Saturn 12th/1st/2nd from the Moon, vedic_reference.md \u00a72.7.1), then Raman's
    slow movers (Saturn, Jupiter, Rahu) -- settle only about half the cases; the rest are
    broken by house NUMBER, which carries no weight in the corpus and is not a
    heaviness claim (QA measured the number deciding on 6 of 12 rashis today).
    So: one of the grahas the corpus names as dominant, picked
    deterministically. The panel prints the graha and its house so a reader can
    check it rather than trust an ordering.

    None when nothing transits unfavourably -- a day with no affliction needs no
    remedy, and inventing one would be the fabrication this product avoids.
    Never raises.
    """
    try:
        adverse = [e for e in gochara_for_rashi(rashi_index, transit)
                   if e["verdict"] == "challenging" and e["planet"] in _GRAHA_GOOD_DEED]
        if not adverse:
            return None
        # ORDERING. Tiers 1 and 2 are sourced; tier 3 is a tie-break, not a claim.
        #
        # 1. Saturn in the 12th, 1st or 2nd from the janma rashi -- Sade Sati.
        #    SOURCED: vedic_reference.md §2.7.1, Rao, *Lessons on Vedic
        #    Astrology* Vol. I, Lesson 1 note 11: Saturn "in three signs i.e.,
        #    the sign behind the Moon, the sign of the Mo and the sign ahead of
        #    the Mo". The Rashifal counts from the janma rashi, which IS that
        #    Moon, so the three houses are directly computable.
        #
        #    The 8th (Ashtama Shani) is DELIBERATELY NOT in this tier. An earlier
        #    version had (12, 1, 2, 8) and called all of it sourced; §2.4 is
        #    marked UNSOURCED by the repo's own audit (vedic_reference.md §2.7.3:
        #    `ashtama shani` = 0 across 14 books, `ashtama` = 0 in Rao). Saturn
        #    in the 8th is still an adverse Saturn transit and still ranks in
        #    tier 2 like any other slow mover; it just does not outrank Jupiter
        #    or Rahu on a claim the corpus cannot back.
        #
        #    This tier exists because the first version had none, and it showed:
        #    on the day QA checked, Aries was in Sade Sati arambha (Saturn 12th)
        #    and Aquarius in Sade Sati uttara (2nd), and the remedy named Jupiter
        #    and Rahu instead -- because houses 4 and 1 sort before 12 and 2.
        #    Phases of a Saturn Sade Sati were passed over by a rule whose
        #    docstring said "heaviest".
        #
        # 2. Then Raman's own weighting, quoted at _GOCHARA_WEIGHTY: "the
        #    transiting effects of the slow moving ones, viz., Jupiter, Saturn
        #    and Rahu are universally held to be most powerful."
        #
        # 3. Then house number, PURELY to make the pick deterministic. This tier
        #    is not a heaviness claim and the corpus supports no such reading of
        #    it; it only stops the answer depending on dict order.
        def _rank(e: dict) -> tuple:
            saturn_phase = e["planet"] == "Saturn" and e["house"] in (12, 1, 2)
            return (not saturn_phase, e["planet"] not in _GOCHARA_WEIGHTY, e["house"])

        adverse.sort(key=_rank)
        pick = adverse[0]
        return {"planet": pick["planet"], "house": pick["house"],
                "house_ord": (_HOUSE_ORDINAL_HI if lang == "hi"
                              else _HOUSE_ORDINAL).get(
                                  pick["house"], str(pick["house"])),
                "planet_label": (_GRAHA_HI[pick["planet"]] if lang == "hi"
                                 else pick["planet"]),
                "deed": (_GRAHA_GOOD_DEED_HI if lang == "hi"
                         else _GRAHA_GOOD_DEED)[pick["planet"]]}
    except Exception:  # noqa: BLE001 - see docstring
        return None


@dataclass(frozen=True)
class GocharImpact:
    """One slow-mover's current transit + houses + favourability classification."""

    planet: str
    sign: str
    house_from_lagna: int
    house_from_moon: int
    retrograde: bool
    favorability: str  # "favorable" | "challenging" — NO neutral; see below


def compute_gochar_impacts(natal: Chart, when: datetime | None = None) -> list[GocharImpact]:
    """Slow-mover gochar (Saturn, Jupiter, Rahu, Ketu) with houses + favourability.

    These four planets define the life-chapter backdrop of any given period —
    Saturn (~2.5 yr/sign), Jupiter (~13 mo/sign), Rahu/Ketu (~18 mo/sign).
    For monthly and yearly views, we re-use this with different `when=` dates.
    """
    transit = compute_transit_snapshot(natal, when)
    moon = next(p for p in natal.planets if p.name == "Moon")
    moon_idx = _rashi_index(moon.rashi)

    impacts: list[GocharImpact] = []
    for name in ("Saturn", "Jupiter", "Rahu", "Ketu"):
        p = next((t for t in transit.planets if t.name == name), None)
        if p is None:
            continue
        sign_idx = _rashi_index(p.rashi)
        h_from_moon = ((sign_idx - moon_idx) % 12) + 1
        impacts.append(
            GocharImpact(
                planet=name,
                sign=p.rashi,
                house_from_lagna=p.house,
                house_from_moon=h_from_moon,
                retrograde=p.retrograde,
                # h_from_moon, NOT p.house. p.house is the transit's house from
            # the LAGNA; Gochara is measured from the natal Moon. Keying on
            # the Lagna changed the verdict on 62.5% of gochar lines (300 of
            # 480, over 120 random charts) AGAINST THE TABLE THEN IN FORCE —
            # that is the "how much shipped output was wrong" number, stable
            # at 61-66% across four seeds. Re-running the same experiment
            # against the CORRECTED table below gives ~40%, because the two
            # measure different things; do not read 62.5% as describing the
            # current code. And the line handed to the model
            # prints both houses and then this label, so a Saturn reported as
            # "house 8 from natal Moon. Favourability: favorable" was telling
            # people their Ashtama Shani was going well.
            favorability=_GOCHAR_FAVOURABILITY[(name, h_from_moon)],
            )
        )
    return impacts


# ---------------------------------------------------------------------------
# Varshaphala — annual chart cast at the moment of solar return
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Varshaphala:
    """The annual chart (Tajik / Varshaphala basics) for the seeker.

    The full Tajik system includes Muntha, Year Lord (Patyayini Dasha lord),
    Sahams, and dozens of other layers. For v1 we expose the four headline
    elements most readers care about:

    - solar_return_moment: the UT moment when Sun returns to natal longitude
    - annual_chart: a Chart object cast for that moment at natal birthplace
    - muntha_house: the house in the annual chart that holds the natal Sun's
      sign (classical Muntha — the "year house")
    - year_lord: the lord of the annual chart's Lagna
    """

    solar_return_moment: datetime
    annual_chart: Chart
    muntha_house: int
    year_lord: str


def compute_varshaphala(natal: Chart, when: datetime | None = None) -> Varshaphala:
    """Compute the annual chart cast at solar return for the year containing `when`.

    Finds the upcoming solar return (within the next 365 days from `when`),
    then casts a Chart at that moment using natal birthplace coords.
    Search algorithm: scan day-by-day until the angular distance to natal Sun
    crosses zero, then bisect to minute precision.
    """
    natal_sun = next(p for p in natal.planets if p.name == "Sun")
    natal_sun_long = _rashi_index(natal_sun.rashi) * 30.0 + natal_sun.longitude

    start = (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))
    # Coarse scan: step day-by-day for up to 366 days, find where Sun's angular
    # distance from natal Sun crosses through zero (signed minimum).
    coarse_step = timedelta(days=1)
    prev_diff = _sun_angular_diff(natal, start, natal_sun_long)
    cursor = start + coarse_step
    found_after = None
    while cursor < start + timedelta(days=370):
        diff = _sun_angular_diff(natal, cursor, natal_sun_long)
        # Sign-flip from negative to positive (or vice versa, given Sun's
        # monotonic eastward motion) means we crossed the natal longitude.
        if prev_diff <= 0 and diff > 0:
            found_after = cursor
            break
        prev_diff = diff
        cursor += coarse_step

    # If solar return is somehow missed (shouldn't happen — Sun returns ~yearly),
    # fall back to one full year ahead.
    refine_anchor = found_after or (start + timedelta(days=365))
    # Bisect within [refine_anchor - 1 day, refine_anchor] to find minute-precision moment.
    lo = refine_anchor - coarse_step
    hi = refine_anchor
    for _ in range(40):  # ~ minute precision well within 40 bisections
        mid = lo + (hi - lo) / 2
        diff = _sun_angular_diff(natal, mid, natal_sun_long)
        if diff < 0:
            lo = mid
        else:
            hi = mid
    sr_moment = hi

    # Cast the annual chart at the solar-return moment, natal birthplace.
    annual_chart = _cast_chart_at(sr_moment, natal.birth_lat, natal.birth_lon, natal.birth_tz)

    # Muntha — the natal Sun's sign in the annual chart, expressed as a house from annual Lagna.
    annual_lagna_idx = _rashi_index(annual_chart.lagna_rashi)
    natal_sun_sign_idx = _rashi_index(natal_sun.rashi)
    muntha_house = ((natal_sun_sign_idx - annual_lagna_idx) % 12) + 1

    year_lord = RASHI_LORDS[annual_lagna_idx]

    return Varshaphala(
        solar_return_moment=sr_moment,
        annual_chart=annual_chart,
        muntha_house=muntha_house,
        year_lord=year_lord,
    )


def _sun_angular_diff(natal: Chart, at: datetime, target_long: float) -> float:
    """Sun's signed angular distance from `target_long` at moment `at`.

    Returns a value in (-180, +180]. Negative = Sun hasn't reached target yet;
    positive = Sun has crossed past target. Used by the solar-return search.
    """
    jd = swe.julday(
        at.year, at.month, at.day,
        at.hour + at.minute / 60 + at.second / 3600,
    )
    pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
    sun_now = float(pos[0])
    diff = (sun_now - target_long) % 360
    return diff if diff <= 180 else diff - 360


def _cast_chart_at(moment: datetime, lat: float, lon: float, tz_name: str) -> Chart:
    """Build a Chart for an arbitrary moment + place (used for Varshaphala annual chart).

    Mirrors compute_chart's internals, but skips the form-input parsing path —
    the moment is already a tz-aware datetime in UT.
    """
    moment_utc = moment.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(
        moment_utc.year, moment_utc.month, moment_utc.day,
        moment_utc.hour + moment_utc.minute / 60 + moment_utc.second / 3600,
    )
    _, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    asc_long = float(ascmc[0])
    lagna_sign_idx = int(asc_long // 30)
    planets = _compute_planet_positions(jd, lagna_sign_idx)
    return Chart(
        lagna_rashi=RASHIS[lagna_sign_idx],
        lagna_longitude=asc_long - lagna_sign_idx * 30,
        planets=planets,
        birth_lat=lat,
        birth_lon=lon,
        birth_tz=tz_name,
        birth_utc=moment_utc,
    )


# ---------------------------------------------------------------------------
# Transit event detection — sign changes + retrograde flips
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitEvent:
    """One notable transit event detected within a future window.

    `event_type` is one of: 'sign_change', 'retrograde_start', 'retrograde_end'.
    `summary` is a one-line human label like "Mercury enters Cancer" or
    "Mercury goes retrograde".
    """

    date: date_
    planet: str
    event_type: str
    from_state: str
    to_state: str
    summary: str


def compute_transit_events(
    natal: Chart,
    start: datetime | None = None,
    days: int = 30,
    step_days: int = 1,
    planets: tuple[str, ...] = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"),
) -> list[TransitEvent]:
    """Scan day-by-day for sign changes and retrograde flips within the window.

    `step_days=1` works well for the 30-day monthly window. For the 365-day
    yearly window pass `step_days=7` and a narrower planet list (slow movers
    only) to keep the cost down — daily steps over a year is 365 swisseph
    calls per planet but still completes in well under a second.

    Rahu/Ketu are excluded from retrograde detection by design — Vedic
    convention shows them perpetually retrograde, so the flag never flips.
    They're still tracked for sign changes if included in `planets`.
    """
    anchor = (start or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))

    prev_snap = compute_transit_snapshot(natal, anchor)
    prev_state: dict[str, tuple[str, bool]] = {
        p.name: (p.rashi, p.retrograde) for p in prev_snap.planets
    }

    events: list[TransitEvent] = []
    for offset in range(step_days, days + 1, step_days):
        d = anchor + timedelta(days=offset)
        snap = compute_transit_snapshot(natal, d)
        for p in snap.planets:
            if p.name not in planets:
                continue
            prev_rashi, prev_retro = prev_state.get(p.name, (p.rashi, p.retrograde))
            if p.rashi != prev_rashi:
                events.append(
                    TransitEvent(
                        date=d.date(),
                        planet=p.name,
                        event_type="sign_change",
                        from_state=prev_rashi,
                        to_state=p.rashi,
                        summary=f"{p.name} enters {p.rashi}",
                    )
                )
            # Retrograde flip — skip Rahu/Ketu (always-retrograde by Vedic convention).
            if p.name not in {"Rahu", "Ketu"} and p.retrograde != prev_retro:
                events.append(
                    TransitEvent(
                        date=d.date(),
                        planet=p.name,
                        event_type="retrograde_end" if prev_retro else "retrograde_start",
                        from_state="retrograde" if prev_retro else "direct",
                        to_state="retrograde" if p.retrograde else "direct",
                        summary=(
                            f"{p.name} goes retrograde"
                            if p.retrograde
                            else f"{p.name} returns to direct motion"
                        ),
                    )
                )
            prev_state[p.name] = (p.rashi, p.retrograde)

    return events


def format_events_for_prompt(events: list[TransitEvent]) -> str:
    """Plain-English event list for the LLM user message; empty → 'None notable'."""
    if not events:
        return "Notable transit events in this window: none detected."
    lines = ["Notable transit events in this window (chronological):"]
    for e in events:
        lines.append(f"- {e.date.isoformat()}: {e.summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panchang — Rahu Kaal, Abhijit Muhurta, day-lord color
# ---------------------------------------------------------------------------


# Weekday (Python: Monday=0..Sunday=6) → (name, planetary lord, favourable color, swatch hex).
# Standard Vedic correspondence used in classical Panchang.
_WEEKDAY_LORDS: dict[int, tuple[str, str, str, str]] = {
    0: ("Monday",    "Moon",    "White or Cream",     "#f3ead5"),
    1: ("Tuesday",   "Mars",    "Red",                "#c8202b"),
    2: ("Wednesday", "Mercury", "Green",              "#16a34a"),
    3: ("Thursday",  "Jupiter", "Yellow or Gold",     "#eab308"),
    4: ("Friday",    "Venus",   "White or Light Pink","#fda4af"),
    5: ("Saturday",  "Saturn",  "Blue or Black",      "#1e3a8a"),
    6: ("Sunday",    "Sun",     "Red or Orange",      "#ea580c"),
}

# 1-based 1/8 segment of the daylight (sunrise to sunset) when Rahu Kaal falls.
#
# Source: B.V. Raman, "Muhurtha or Electional Astrology" (1948), glossary
# entry "Rahu Kalam" — data/matching/raman-muhurtha-1948-electional-astrology
# _djvu.txt, lines 7318-7356 (already plain text; no pdftotext involved).
# Raman states it as clock times against a 6 a.m. sunrise, which makes each
# eighth exactly 1h30m; reversing that gives the segment ordinals below.
# Verified by execution, all 7/7 — e.g. Saturday's "9 a.m. to 10-30 a.m." is
# segment 3, Sunday's "4-30 p.m. to 6 p.m." is segment 8.
#
# `scripts/corpus_search.py "rahu kala"` reports 0 hits and that is a FALSE
# NEGATIVE: the glossary spells it "Rahu Kalam" and the OCR splits the entry
# across three columns, so the expander never reaches it. Do not cite that
# zero as evidence of absence — this is the second time a "measured absence"
# in this repo turned out to be a search artefact.
_RAHU_KAAL_SEGMENT: dict[int, int] = {
    0: 2,  # Monday    — 2nd part
    1: 7,  # Tuesday   — 7th part
    2: 5,  # Wednesday — 5th part
    3: 6,  # Thursday  — 6th part
    4: 4,  # Friday    — 4th part
    5: 3,  # Saturday  — 3rd part
    6: 8,  # Sunday    — 8th part
}


# 30 Tithi names — 15 waxing (Shukla Paksha) then 15 waning (Krishna Paksha).
# Purnima (index 14) = full moon; Amavasya (index 29) = new moon.
# Classical significance is loose but widely-cited; used to colour the day's
# character in the LLM Rashifal prompt.
_TITHI_NAMES: tuple[str, ...] = (
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashti",   "Saptami", "Ashtami", "Navami",    "Dashami",
    "Ekadashi",  "Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashti",   "Saptami", "Ashtami", "Navami",    "Dashami",
    "Ekadashi",  "Dwadashi","Trayodashi","Chaturdashi","Amavasya",
)

# Widely-cited classical character notes for the special tithis. Not exhaustive
# — deliberately short so the LLM can weave them into readings without turning
# them into a lecture. Empty string = ordinary tithi, no special guidance.
_TITHI_SIGNIFICANCE: dict[str, str] = {
    "Ekadashi":    "fasting day, spiritual introspection, avoid grains",
    "Dwadashi":    "breaking-fast day after Ekadashi, gentle refuelling",
    "Trayodashi":  "Pradosh Vrat — evening Shiva worship, releasing tension",
    "Chaturdashi": "sensitive day, meditation and quiet effort favoured",
    "Purnima":     "full moon — culmination, generosity, worship, emotional peak",
    "Amavasya":    "new moon — ancestral rites (Pitru), quiet resets, avoid new ventures",
    "Chaturthi":   "Ganesh day — remove obstacles, start small things",
    "Panchami":    "Nag/Saraswati themes — learning, arts, snakes in symbolism",
    "Saptami":     "Sun-themed — health, vitality, father matters",
    "Ashtami":     "Durga/Shakti themes — courage, protection, focused action",
    "Navami":      "Devi themes — completion of a cycle of worship",
    "Dashami":     "Vijayadashami undertones — victory, right action",
}


# ─── Nitya Yoga — the 4th anga ───────────────────────────────────────
# The 27 Nitya ("daily") Yogas of the classical almanac. NOT the natal-chart
# yogas in `compute_yogas` above (Gaja-Kesari, Ruchaka, ...) — a completely
# different concept that happens to share the word.
#
# Formula: (Sun_longitude + Moon_longitude) mod 360, divided into 27 equal
# parts of 13°20'. Per the classical muhurta tradition (Muhurta Chintamani),
# Vyatipata (17th) and Vaidhriti (27th) are hard exclusions for shubh karya.
# muhurat.py carries its own copy of this list for its blocker check; the
# two must stay in the same ORDER (spelling variants are cosmetic).
_NITYA_YOGA_NAMES: tuple[str, ...] = (
    "Vishkambha", "Priti",   "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda",   "Sukarma", "Dhriti",   "Shula",     "Ganda",
    "Vriddhi",    "Dhruva",  "Vyaghata", "Harshana",  "Vajra",
    "Siddhi",     "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha",     "Sadhya",  "Shubha",   "Shukla",    "Brahma",
    "Indra",      "Vaidhriti",
)

# Short character notes for the yogas the classical tradition singles out.
# Empty/absent = ordinary yoga, no special guidance. Deliberately terse so
# the UI card and the LLM prompt stay readable.
_NITYA_YOGA_SIGNIFICANCE: dict[str, str] = {
    "Vyatipata": "classically inauspicious — avoid new undertakings",
    "Vaidhriti": "classically inauspicious — avoid new undertakings",
    "Siddhi":    "favourable for accomplishment and completion",
    "Amrita":    "nectar-like; broadly favourable",
    "Ayushman":  "longevity and vitality themes",
    "Saubhagya": "good fortune, favourable for auspicious work",
    "Shubha":    "broadly auspicious",
    "Harshana":  "joy, celebration, favourable news",
}


# ─── Karana — the 5th anga ───────────────────────────────────────────
# A karana is half a tithi (6° of Sun–Moon elongation), so there are 60 in a
# lunar month. Indexing (matching Drik Panchang / classical almanac order):
#   index 0        → Kimstughna, FIXED — first half of Shukla Pratipada
#   index 1..56    → the 7 movable karanas repeating 8 times
#   index 57,58,59 → Shakuni, Chatushpada, Naga — FIXED, the month's last
#                    three halves (2nd half of Krishna Chaturdashi and both
#                    halves of Amavasya)
# Vishti (also called Bhadra) is the movable karana universally avoided for
# shubh karya in the classical muhurta tradition.
_MOVABLE_KARANA_NAMES: tuple[str, ...] = (
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanij", "Vishti",
)
_FIXED_TAIL_KARANA_NAMES: tuple[str, ...] = ("Shakuni", "Chatushpada", "Naga")
_FIRST_KARANA_NAME = "Kimstughna"

_KARANA_SIGNIFICANCE: dict[str, str] = {
    "Vishti":      "Bhadra — traditionally avoided for auspicious beginnings",
    "Shakuni":     "fixed karana; suited to remedial and medicinal work",
    "Chatushpada": "fixed karana; cattle, land and ancestral rites",
    "Naga":        "fixed karana; ancestral and propitiatory rites",
    "Kimstughna":  "fixed karana; favourable for auspicious beginnings",
    "Bava":        "favourable for stable, long-lasting undertakings",
    "Balava":      "favourable for learning and devotional work",
    "Kaulava":     "favourable for friendship and alliances",
    "Taitila":     "favourable for trade and negotiation",
    "Gara":        "favourable for agriculture and building",
    "Vanij":       "favourable for commerce and transactions",
}


@dataclass(frozen=True)
class DailyPanchang:
    """Today's Muhurta data — what to do (and not do), plus the day's favourable color.

    Mixes UNIVERSAL fields (weekday, day_lord, tithi, tithi_paksha,
    tithi_significance — same worldwide for any given date) with
    LOCATION-DEPENDENT fields (sunrise/sunset and the Rahu Kaal / Abhijit
    windows derived from them — differ by lat/lon).

    All time fields are tz-aware local datetimes at the natal birthplace.
    Rahu Kaal is the inauspicious window; Abhijit Muhurta is the most
    auspicious window (centered on solar noon).
    """

    weekday: str              # "Friday" — universal
    day_lord: str             # "Venus" — universal
    day_color: str            # e.g. "White or Light Pink" — universal
    day_color_hex: str        # UI swatch — universal
    tithi_index: int          # 0..29 — universal (0=Shukla Pratipada, 14=Purnima, 29=Amavasya)
    tithi_name: str           # e.g. "Ekadashi" — universal
    tithi_paksha: str         # "Shukla" (bright/waxing) or "Krishna" (dark/waning) — universal
    tithi_significance: str   # classical character note; "" if ordinary tithi — universal
    yoga_index: int           # 0..26 Nitya Yoga at sunrise — universal
    yoga_name: str            # e.g. "Siddhi" — universal
    yoga_significance: str    # classical note; "" if ordinary yoga — universal
    karana_index: int         # 0..59 half-tithi at sunrise — universal
    karana_name: str          # e.g. "Vishti" — universal
    karana_significance: str  # classical note; "" if ordinary karana — universal
    sunrise: datetime         # local time at natal birthplace — LOCATION-DEPENDENT
    sunset: datetime          # local time at natal birthplace — LOCATION-DEPENDENT
    rahu_kaal_start: datetime # LOCATION-DEPENDENT
    rahu_kaal_end: datetime   # LOCATION-DEPENDENT
    abhijit_start: datetime   # LOCATION-DEPENDENT
    abhijit_end: datetime     # LOCATION-DEPENDENT
    # False when this date has no ordinary sunrise→sunset span at this
    # latitude, so the four fields above are arithmetic on a span that does
    # not exist and MUST NOT be presented. See compute_panchang. #227.
    daylight_ordinary: bool = True


# In-process cache keyed by (date, rounded lat, rounded lon, tz name). Two
# subscribers in the same city on the same day share one compute — the
# per-request panchang_cache dict in the send loop already dedups within a
# batch; this cache extends dedup across the whole process's lifetime.
#
# Rounded to ~55km (0.5deg). This is NOT "a few seconds", which is what this
# comment used to claim. Measured 2026-08-26 on each cell's SW-NE corner pair
# (where the annual sunrise maximum falls) over 365 days of 2026: sunrise
# differs by up to 3.37 min in the Srinagar cell (mean 2.05, over 1 min on
# 296/365 days) and 3.18 min in the Delhi cell (mean 2.04, 313/365) — no
# calendar-day flip in either, but a 2 min MEAN is not seconds. For scale,
# that 3.37 is 84% of scripts/verify_panchang_angas.py's
# SUNRISE_TOLERANCE_MIN = 4; that gate builds one chart for one city, so it
# cannot itself see cache error — the comparison is of magnitude only.
# Moon rise/set deliberately does NOT come through here — compute_moon_rise_set
# computes at the exact coordinates, because at 0.5deg the printed DATE flips.
# Cache is bounded by the small number of cities in the subscriber base, so we
# don't LRU-cap it.
_PANCHANG_CACHE: dict[tuple, "DailyPanchang"] = {}


def _tithi_at(julian_day: float) -> tuple[int, str, str, str]:
    """(index 0-29, name, paksha, significance) at the given Julian Day.

    Formula: tithi = (Moon_longitude - Sun_longitude) mod 360, divided by 12.
    Uses sidereal Lahiri to match the rest of the chart code (though tithi is
    actually invariant under ayanamsa choice — both Sun and Moon shift equally).
    """
    sun_pos, _ = swe.calc_ut(julian_day, swe.SUN, swe.FLG_SIDEREAL)
    moon_pos, _ = swe.calc_ut(julian_day, swe.MOON, swe.FLG_SIDEREAL)
    diff = (float(moon_pos[0]) - float(sun_pos[0])) % 360.0
    idx = int(diff / 12.0)
    name = _TITHI_NAMES[idx]
    paksha = "Shukla" if idx < 15 else "Krishna"
    significance = _TITHI_SIGNIFICANCE.get(name, "")
    return idx, name, paksha, significance


def julian_day_utc(when: datetime) -> float:
    """Julian Day for an instant, normalised to UTC.

    Exists so callers outside this module can reach the anga functions below,
    which all take a Julian Day (#148). `muhurat.py` previously could not, so
    it grew its own copies of the nitya-yoga and karana maths instead — two
    implementations of the same astrology with no computation over both that
    would notice if they drifted.

    Naive datetimes are treated as UTC, matching `compute_transit_snapshot`.
    """
    moment = when if when.tzinfo else when.replace(tzinfo=ZoneInfo("UTC"))
    moment = moment.astimezone(ZoneInfo("UTC"))
    return swe.julday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour + moment.minute / 60 + moment.second / 3600,
    )


def _pada_of(long_abs: float) -> int:
    """Quarter of the nakshatra a longitude falls in, 1-4 (#209).

    A nakshatra spans 360/27 = 13 deg 20'; a pada is a quarter of that,
    3 deg 20'. Equivalent to 360/108 of the zodiac, which is why the pada is
    exactly the Navamsha division — the same 108 slices, counted differently.
    """
    # Scale to nakshatra-fractions FIRST, then take the quarter (#209 QA).
    #
    # The obvious form — `(long_abs % (360/27)) // (360/108)` — is wrong at
    # every exact 10-degree multiple, which is every third pada boundary and
    # exactly representable in binary. 360/27 = 13.333... and 360/108 =
    # 3.3333...; at 10.0 the remainder computes as 9.999999999999998, which
    # floors to pada 3 instead of 4. Measured against exact `Fraction`
    # arithmetic over 36,000 points: 35 wrong, all at 10.0, 20.0, ... 350.0.
    #
    # The commit that introduced this function claimed 10.0 had been verified
    # as a boundary. It had been printed and misread — the printed 3 was the
    # bug, not the confirmation.
    #
    # This form divides before taking the fractional part, so the boundary
    # lands on a value binary floating point represents exactly: 0 mismatches
    # over the same 36,000 points.
    return int((long_abs * 27 / 360 % 1) * 4) + 1


def _nitya_yoga_at(julian_day: float) -> tuple[int, str, str]:
    """(index 0-26, name, significance) of the Nitya Yoga at the given Julian Day.

    Formula: yoga = (Sun_longitude + Moon_longitude) mod 360, divided by
    360/27 = 13°20'. Sidereal Lahiri — unlike tithi, the yoga is NOT invariant
    under ayanamsa choice (the two ayanamsa shifts add rather than cancel), so
    the sidereal convention shared with the rest of the almanac is load-bearing.
    """
    sun_pos, _ = swe.calc_ut(julian_day, swe.SUN, swe.FLG_SIDEREAL)
    moon_pos, _ = swe.calc_ut(julian_day, swe.MOON, swe.FLG_SIDEREAL)
    combined = (float(sun_pos[0]) + float(moon_pos[0])) % 360.0
    idx = int(combined / (360.0 / 27.0)) % 27
    name = _NITYA_YOGA_NAMES[idx]
    return idx, name, _NITYA_YOGA_SIGNIFICANCE.get(name, "")


def _karana_at(julian_day: float) -> tuple[int, str, str]:
    """(index 0-59, name, significance) of the karana at the given Julian Day.

    A karana is half a tithi: ((Moon - Sun) mod 360) / 6. The index therefore
    always satisfies `karana_index // 2 == tithi_index` at the same instant.

    Index 0 is Kimstughna (fixed, first half of Shukla Pratipada); 1..56 cycle
    the 7 movable karanas eight times; 57/58/59 are the fixed Shakuni,
    Chatushpada and Naga closing the lunar month.
    """
    sun_pos, _ = swe.calc_ut(julian_day, swe.SUN, swe.FLG_SIDEREAL)
    moon_pos, _ = swe.calc_ut(julian_day, swe.MOON, swe.FLG_SIDEREAL)
    diff = (float(moon_pos[0]) - float(sun_pos[0])) % 360.0
    idx = int(diff / 6.0) % 60
    if idx == 0:
        name = _FIRST_KARANA_NAME
    elif idx >= 57:
        name = _FIXED_TAIL_KARANA_NAMES[idx - 57]
    else:
        name = _MOVABLE_KARANA_NAMES[(idx - 1) % 7]
    return idx, name, _KARANA_SIGNIFICANCE.get(name, "")


def _local_day(natal: Chart, when: datetime | None) -> tuple[ZoneInfo, date_]:
    """(birthplace tz, local calendar date) for the anchor moment `when`.

    A panchang day is the LOCAL calendar date at the birthplace, not the UTC
    date and not the caller's date. Shared by `compute_panchang` and
    `compute_moon_rise_set` so the two cannot drift: if they derived the day
    differently, the moonrise returned for a date would belong to a different
    day than the tithi returned for it.
    """
    tz = ZoneInfo(natal.birth_tz)
    return tz, (when or datetime.now(tz)).astimezone(tz).date()


def compute_panchang(natal: Chart, when: datetime | None = None) -> DailyPanchang:
    """Compute today's Panchang for the natal birthplace, cached per (date, city).

    Uses natal lat/lon because we don't know where the seeker physically is
    now. Note this on the UI — for the most precise local Muhurta, the
    seeker should ideally compute against their current location.

    Location-independent fields (weekday, tithi, paksha) are the same
    worldwide for a given date; location-dependent ones (sunrise, Rahu Kaal,
    Abhijit) genuinely vary by city. The in-process cache dedups per city.
    """
    tz, today = _local_day(natal, when)

    # Cache key: date + coarse coords + tz. ~55km radius shares one entry.
    cache_key = (
        today.isoformat(),
        round(natal.birth_lat * 2) / 2,
        round(natal.birth_lon * 2) / 2,
        natal.birth_tz,
    )
    cached = _PANCHANG_CACHE.get(cache_key)
    if cached is not None:
        return cached

    weekday = today.weekday()  # 0=Mon..6=Sun
    weekday_name, day_lord, day_color, day_color_hex = _WEEKDAY_LORDS[weekday]
    sunrise, sunset = _sunrise_sunset(today, natal.birth_lat, natal.birth_lon, tz)

    # Tithi at local sunrise — the classical convention for "today's tithi".
    sunrise_ut = sunrise.astimezone(ZoneInfo("UTC"))
    sunrise_jd = swe.julday(
        sunrise_ut.year, sunrise_ut.month, sunrise_ut.day,
        sunrise_ut.hour + sunrise_ut.minute / 60 + sunrise_ut.second / 3600,
    )
    tithi_idx, tithi_name, tithi_paksha, tithi_sig = _tithi_at(sunrise_jd)
    # Yoga and karana share the sunrise convention — issue #142.
    yoga_idx, yoga_name, yoga_sig = _nitya_yoga_at(sunrise_jd)
    karana_idx, karana_name, karana_sig = _karana_at(sunrise_jd)

    # Does this date HAVE an ordinary sunrise→sunset span? At high latitude it
    # can not: `_rise_or_set` anchors at local midnight, so near the solstice
    # the first set it finds is the tail of the PREVIOUS solar day and lands
    # before the rise, and on other days both instants fall on D+1. Every
    # window below is a fraction of daylight (`knowledge/vedic_reference.md`
    # §28 — Rahu Kaal is a weekday-indexed eighth of it, Abhijit a fifteenth),
    # so on such a date they are fractions of a span that does not exist:
    # day_seconds goes negative and each window ends before it starts.
    # Measured 2026-08-26 at Tromso (69.6492N/18.9553E, Europe/Oslo) over the
    # 365 days of 2026: 117 raise before reaching here (no rise or no set at
    # all), 4 arrive with sunset <= sunrise (2026-05-17 sunrise 01:14:09 /
    # sunset 00:06:04, daylength −1.13h; 07-26, 07-27, 07-28) and 1 more
    # (2026-05-16) with a sunset on D+1. Those 5 used to render a confident
    # backwards table on `/panchang` — 200 OK, no error, no clue. Issue #227.
    #
    # The four derived fields are still POPULATED rather than set to None:
    # `llm.py` formats them unconditionally for the daily-reading and rashifal
    # prompts, so a None would convert this quiet render defect into a crash on
    # the email path. Callers that PRESENT a daylight window must check this
    # flag; `routes/panchang.py` does.
    daylight_ordinary = (
        sunset > sunrise and sunrise.date() == today and sunset.date() == today
    )

    # Rahu Kaal: which 1/8 segment of the daylight period?
    day_seconds = (sunset - sunrise).total_seconds()
    segment_seconds = day_seconds / 8.0
    rk_segment_idx = _RAHU_KAAL_SEGMENT[weekday]
    rk_start = sunrise + timedelta(seconds=(rk_segment_idx - 1) * segment_seconds)
    rk_end = sunrise + timedelta(seconds=rk_segment_idx * segment_seconds)

    # Abhijit Muhurta: centred on LOCAL solar noon, spanning day_length/15
    # (~48 minutes on equinox days).
    #
    # Centring on solar noon: Narasimha Rao, "Lessons Vol. I", Lesson #1 item
    # 16 — "you use the muhurta of mid day (i.e. when Sun is at the highest
    # point in the sky at a particular location) ... called Abhijit muhurta".
    # The 15-muhurta division of daylight and the ~48-minute width: Raman,
    # "Muhurtha" pp.31-32.
    #
    # UNSOURCED, and left in place only because it is arithmetically the same
    # thing: the label "8th of the 15". Segments 7/15 to 8/15 of daylight do
    # centre on midday, so the code is right either way — but no book we hold
    # states that Abhijit IS the 8th diurnal muhurta, and Raman's own numbered
    # list names his 8th "Vidhi" and treats "abhijit" as a separate name. The
    # arithmetic is sourced; the ordinal label is not. Do not repeat it as
    # though it were.
    midday = sunrise + timedelta(seconds=day_seconds / 2.0)
    abhijit_half = timedelta(seconds=(day_seconds / 15.0) / 2.0)
    result = DailyPanchang(
        weekday=weekday_name,
        day_lord=day_lord,
        day_color=day_color,
        day_color_hex=day_color_hex,
        tithi_index=tithi_idx,
        tithi_name=tithi_name,
        tithi_paksha=tithi_paksha,
        tithi_significance=tithi_sig,
        yoga_index=yoga_idx,
        yoga_name=yoga_name,
        yoga_significance=yoga_sig,
        karana_index=karana_idx,
        karana_name=karana_name,
        karana_significance=karana_sig,
        sunrise=sunrise,
        sunset=sunset,
        rahu_kaal_start=rk_start,
        rahu_kaal_end=rk_end,
        abhijit_start=midday - abhijit_half,
        abhijit_end=midday + abhijit_half,
        daylight_ordinary=daylight_ordinary,
    )
    _PANCHANG_CACHE[cache_key] = result
    return result


def compute_moon_rise_set(
    natal: Chart, when: datetime | None = None
) -> tuple[datetime | None, datetime | None]:
    """(moonrise, moonset) at the natal birthplace for the local day of `when`.

    Either may carry a NEXT-DAY instant, or be None. Successive moonrises are
    ~24h50m apart, so on 13 of 365 Delhi days in 2026 the day holds no moonrise
    of its own and the first one after midnight is on D+1; at polar latitudes
    the event can be absent for a week at a time. Both are correct — see
    `_rise_or_set`. Callers must render the date, not just the clock time, and
    must handle None.

    `routes/panchang.py` calls it (#150). It shipped with no caller at all —
    two comments referred to it and nothing reached it, so the paragraph above
    was advice to nobody and `/panchang` showed neither instant. Absence is not rare and is not only polar: BOTH are absent
    on 166 of 365 days in 2026 at Tromso and 88 at Reykjavik (64.15N, south of
    the Arctic Circle — the Moon's ~5.1deg orbital inclination takes it
    circumpolar where the Sun never is). At New Delhi and Mumbai, zero. Do not
    reach for `DailyPanchang.daylight_ordinary` for this: that flag is about the
    Sun, and Tromso 2026-05-16 has no ordinary daylight span AND a moonrise at
    00:36. `scripts/verify_panchang_angas.py` Gate 7 holds both apart.

    Deliberately NOT a `DailyPanchang` field and deliberately uncached. The two
    Swiss Ephemeris calls cost ~0.5 ms, which `compute_panchang`'s callers were
    paying 90 times over on a muhurat search that reads neither value (#150).
    Putting them behind a `with_lunar=` flag was rejected on correctness, not
    cost: a search would have filled `_PANCHANG_CACHE` with lunar-less entries,
    and a later `/panchang` hitting one would render "no moonrise today" —
    indistinguishable from the genuine absence the None exists to express.

    Computed at the EXACT birth coordinates, not `_PANCHANG_CACHE`'s 0.5° grid
    point — which is why it does not go through that cache. The moon lands near
    midnight often enough that the grid offset flips the printed CALENDAR DAY on
    2 of 365 days in the Srinagar cell; the worst is 2026-12-17, moonset
    17-Dec 00:00:42 at the true point vs 18-Dec 00:59:21 at the grid point. Off
    the grid, that flip cannot happen. Sunrise/sunset do not need this
    — measured across the same cell corner pairs over 2026, they move at most
    3.37 min (Srinagar) / 3.18 min (Delhi) and flip no calendar day at either.
    """
    tz, today = _local_day(natal, when)
    return (
        _rise_or_set(today, natal.birth_lat, natal.birth_lon, tz,
                     swe.MOON, swe.CALC_RISE),
        _rise_or_set(today, natal.birth_lat, natal.birth_lon, tz,
                     swe.MOON, swe.CALC_SET),
    )


def format_panchang_for_prompt(panchang: DailyPanchang) -> str:
    """Plain-English Panchang block for the daily-reading user message."""
    tithi_line = f"- Tithi: {panchang.tithi_paksha} {panchang.tithi_name}"
    if panchang.tithi_significance:
        tithi_line += f" — {panchang.tithi_significance}"
    yoga_line = f"- Yoga (Nitya Yoga): {panchang.yoga_name}"
    if panchang.yoga_significance:
        yoga_line += f" — {panchang.yoga_significance}"
    karana_line = f"- Karana: {panchang.karana_name}"
    if panchang.karana_significance:
        karana_line += f" — {panchang.karana_significance}"
    return (
        "Today's Panchang (computed for the seeker's natal birthplace):\n"
        f"- Day: {panchang.weekday}, ruled by {panchang.day_lord}\n"
        f"{tithi_line}\n"
        f"{yoga_line}\n"
        f"{karana_line}\n"
        f"- Favourable color: {panchang.day_color}\n"
        f"- Sunrise: {panchang.sunrise.strftime('%H:%M')} local\n"
        f"- Sunset: {panchang.sunset.strftime('%H:%M')} local\n"
        f"- Rahu Kaal (inauspicious — avoid starting anything new, signing, big decisions): "
        f"{panchang.rahu_kaal_start.strftime('%H:%M')}–{panchang.rahu_kaal_end.strftime('%H:%M')} local\n"
        f"- Abhijit Muhurta (most auspicious — favourable for important actions): "
        f"{panchang.abhijit_start.strftime('%H:%M')}–{panchang.abhijit_end.strftime('%H:%M')} local"
    )


# Segment -> the i18n keys for its ordinal and its part of the day. The SEGMENT
# ORDINAL is universal — it depends only on the weekday (_RAHU_KAAL_SEGMENT
# above) — and the CLOCK TIME is not; see format_day_windows_for_rashifal
# below for why that matters.
#
# Spelled out as literals rather than built as f"rahu_band_{n}": the
# "no translation key is defined but unused" test matches quoted keys, and a
# key assembled at run time is invisible to it. The band TEXT lives in i18n.py
# (with the Wednesday-segment-5 caveat beside it) since #270 localised it.
_RAHU_KAAL_KEYS: dict[int, tuple[str, str]] = {
    1: ("rahu_ord_1", "rahu_band_1"),
    2: ("rahu_ord_2", "rahu_band_2"),
    3: ("rahu_ord_3", "rahu_band_3"),
    4: ("rahu_ord_4", "rahu_band_4"),
    5: ("rahu_ord_5", "rahu_band_5"),
    6: ("rahu_ord_6", "rahu_band_6"),
    7: ("rahu_ord_7", "rahu_band_7"),
    8: ("rahu_ord_8", "rahu_band_8"),
}


def format_day_windows_for_rashifal(panchang: DailyPanchang, lang: str = "en") -> str:
    """Rahu Kaal / Abhijit for the SHARED rashifal — named, never clocked.

    The rashifal is one text read nationally, generated from a single
    reference chart. Rahu Kaal and Abhijit are derived from local sunrise and
    sunset, so any clock time in that shared text is one city's time presented
    to everyone. Measured for 2026-08-22 against compute_panchang:

        Mumbai    Rahu Kaal 09:31-11:06   Abhijit 12:16-13:06
        Kolkata             08:27-10:03           11:13-12:04
        Guwahati            08:12-09:48           10:59-11:51

    That is a 79-minute national spread, and Kolkata's and Guwahati's real
    Abhijit windows do not overlap Mumbai's AT ALL. A reader in Guwahati told
    to act at 12:30 would be acting a full 39 minutes after their Abhijit had
    closed — precise-looking, confidently wrong, and worse than saying nothing
    because the precision is what makes it credible.

    So this block gives the model what IS universal: the segment ordinal (a
    function of the weekday alone), the part of the day it falls in, and the
    fact that Abhijit is centred on LOCAL solar noon wherever the reader is.
    The real clock times still reach the reader — the email renders them from
    the subscriber's own city and the web page from the seeker's own chart —
    but they come from compute_panchang, not from the model.

    Reuses the already-computed `panchang`; recomputes nothing.

    `lang` supplies the EXACT terms to use. Without it the block named both
    windows in English only, and the Hindi readings improvised: 6 of 12 came
    back defective — `**Rahu Kaal**` in Latin script inside Devanagari prose,
    `रूह क़ाल` ("rooh" is *soul*, not Rahu), `रहुकाल` unspaced, and `अभिजीत`
    in 9 of 9 occurrences while the strip directly above the text said
    `अभिजित मुहूर्त`. Naming a term for the model without giving it the term
    in the target language is asking it to transliterate, and it guesses.
    The strings come from i18n so there is one spelling per language, the
    same one the strip and the email already render.

    The WHOLE block is localised, not just the two names (#270). Localising
    only the names left ~168 English words in the Hindi prompt — band,
    ordinal, directive and the example phrases ('during Rahu Kaal', 'in the
    Abhijit window near midday') — and the model echoed them into Devanagari
    prose ("Rahu काल", "in the Abhijit window near midday" seen live on
    /hi/rashifal/virgo). So this function is only an assembler: the facts
    template, the ordinal, the band and the directive are all i18n keys, and
    `translate()` falls back to English for any language without a table.
    The English output is byte-identical to the pre-#270 literals; the test
    pins it.
    """
    from astro_ai.i18n import translate  # local: i18n must not import chart

    segment = _RAHU_KAAL_SEGMENT[panchang.sunrise.weekday()]
    ordinal_key, band_key = _RAHU_KAAL_KEYS[segment]
    rahu = translate(lang, "rahu_kaal")
    abhijit = translate(lang, "abhijit_muhurta")
    facts = translate(
        lang,
        "rashifal_window_facts",
        rahu=rahu,
        abhijit=abhijit,
        ordinal=translate(lang, ordinal_key),
        band=translate(lang, band_key),
    )
    directive = translate(lang, "rashifal_window_directive", rahu=rahu, abhijit=abhijit)
    return f"{facts}\n{directive}"


def _rise_or_set(
    day: date_, lat: float, lon: float, tz: ZoneInfo, body: int, calc_flag: int
) -> datetime | None:
    """First rise (or set) of `body` at (lat, lon) at or after LOCAL MIDNIGHT on `day`.

    Returns a tz-aware local datetime, or None when the event does not occur.

    ALWAYS CHECK THE RETURN FLAG — this is not defensive coding. When the event
    does not occur, `swe.rise_trans` returns `ret == -2` with `tret[0] == 0.0`,
    and JD 0.0 is 4713 BC, which is outside `datetime`'s range: passing it to
    `_jd_to_utc_datetime` raises `ValueError: year -4713 is out of range`.
    Measured at Tromso (69.65N, 18.96E, Europe/Oslo) with swe.MOON/CALC_RISE —
    seven consecutive days with no moonrise at all:

        2026-12-05  ret  0  jd 2461379.70  -> 05:54
        2026-12-06  ret -2  jd 0.0         -> ValueError
        ...  seven consecutive days ...
        2026-12-12  ret -2  jd 0.0         -> ValueError
        2026-12-13  ret  0  jd 2461388.02  -> 13:33

    ANCHORED AT LOCAL MIDNIGHT, the convention the Sun call already used.
    Successive moonrises are ~24h50m apart, so at ANY latitude some calendar
    days contain no moonrise of their own and the first instant found falls on
    D+1 — 13 of 365 days at Delhi (28.61N) in 2026, e.g. 04-Sep 23:23, then both
    05-Sep and 06-Sep yielding 00:27 on 06-Sep. That next-day instant is CORRECT
    and must not be "fixed"; only the calendar cut is arbitrary, and the caller
    discloses it. The alternative anchor (sunrise) was measured and is worse: it
    removes zero duplicates and puts a next-day label on 105 of 365 days.
    """
    midnight_local = datetime.combine(day, time(0), tzinfo=tz)
    midnight_utc = midnight_local.astimezone(ZoneInfo("UTC"))
    start_jd = swe.julday(
        midnight_utc.year, midnight_utc.month, midnight_utc.day,
        midnight_utc.hour + midnight_utc.minute / 60.0,
    )
    geopos = (lon, lat, 0.0)  # pyswisseph wants (lon, lat, elev) in that order
    ret, tret = swe.rise_trans(start_jd, body, calc_flag, geopos)
    if ret != 0 or not tret or tret[0] <= 0.0:
        return None
    return _jd_to_utc_datetime(tret[0]).astimezone(tz)


def _sunrise_sunset(
    day: date_, lat: float, lon: float, tz: ZoneInfo
) -> tuple[datetime, datetime]:
    """Sunrise + sunset for `day` at (lat, lon), returned as tz-aware local datetimes.

    The annotation OVERSTATES: under polar night / midnight sun the Sun neither
    rises nor sets and a member is None. That is not new breakage from the
    delegation — the same input previously raised `ValueError: year -4713 is out
    of range` from `_jd_to_utc_datetime` on the JD 0.0 sentinel. Both shapes are
    unusable, so no caller changed. BOTH SHAPES ARE REACHABLE IN PRODUCTION —
    this docstring used to say they were not. `/panchang` takes `?city=` as free
    text with no allow-list, so a polar city arrives here: at Tromso, 117 of 365
    days in 2026 raise and the route degrades to Mumbai, but 4 used to render
    200 OK with `sunset <= sunrise` (2026-05-17 showed sunrise 01:14, sunset
    00:06, Rahu Kaal 00:14–00:06 and a backwards choghadiya). It is the
    Delhi-hardcoded callers (`sankranti.py`, `lunar_observances.py`,
    `lunar_dates.py`, `adhik_maas.py`) that cannot reach it.

    The reversed shape is now DETECTED rather than rendered: `compute_panchang`
    sets `DailyPanchang.daylight_ordinary = False` for it and `/panchang`
    discloses instead of showing daylight-fraction windows (#227). The None /
    raise shape is unchanged and still degrades the route to Mumbai — loud, and
    still open.
    """
    return (
        _rise_or_set(day, lat, lon, tz, swe.SUN, swe.CALC_RISE),
        _rise_or_set(day, lat, lon, tz, swe.SUN, swe.CALC_SET),
    )


def _jd_to_utc_datetime(jd: float) -> datetime:
    """Inverse of swe.julday — convert a Julian Day number to a tz-aware UTC datetime.

    Do NOT rewrite this component-wise (hours/minutes/seconds built separately). The
    previous version did, and carried a rounded 60th second up into minutes but never a
    60th minute up into hours — so any JD landing within half a second of a minute
    boundary raised `ValueError: minute must be in 0..59`. That silently emptied
    `lunar_observances` for 14 years between 2000 and 2100 (2035 among them) and made
    `adhik_maas` miss the real Adhik Jyeshtha of 2007. Adding one datetime to a timedelta
    carries seconds -> minutes -> hours -> days -> months -> years for free. Issue #147.
    """
    y, m, d, hour_frac = swe.revjul(jd)
    base = datetime(int(y), int(m), int(d), tzinfo=ZoneInfo("UTC"))
    return base + timedelta(seconds=round(hour_frac * 3600))


# ---------------------------------------------------------------------------


def format_transit_for_prompt(snapshot: TransitSnapshot) -> str:
    """Human-readable transit block for the daily-reading user message."""
    lines = [
        f"Today's transits ({snapshot.moment.strftime('%Y-%m-%d %H:%M UT')}), "
        f"houses reckoned from natal Lagna in {snapshot.natal_lagna_rashi}:",
        "",
    ]
    for p in snapshot.planets:
        retro = " (retrograde)" if p.retrograde else ""
        lines.append(
            f"{p.name}{retro}: now in {p.rashi} at {p.longitude:.1f}deg, "
            f"transiting your natal house {p.house} — Nakshatra: {p.nakshatra}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------


def format_for_prompt(chart: Chart) -> str:
    """Render the chart as the human-readable block the LLM will consume."""
    lines = [
        "Birth chart (Vedic, sidereal zodiac, Lahiri ayanamsa, Whole Sign houses):",
        "",
        f"Lagna (Ascendant): {chart.lagna_rashi} at {chart.lagna_longitude:.1f}deg",
    ]
    for p in chart.planets:
        retro = " (retrograde)" if p.retrograde else ""
        lines.append(
            f"{p.name}{retro}: {p.rashi} at {p.longitude:.1f}deg "
            f"(house {p.house}) — Nakshatra: {p.nakshatra}"
        )
    lines.append("")
    lines.append(
        f"Birth coords: {chart.birth_lat:.3f}, {chart.birth_lon:.3f} "
        f"({chart.birth_tz}); UTC: {chart.birth_utc.isoformat()}"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_planet_positions(julian_day: float, lagna_sign_idx: int) -> list[PlanetPosition]:
    """Shared planet-loop for natal and transit charts.

    `lagna_sign_idx` (0..11) anchors the Whole-Sign house numbering — pass the
    natal Lagna's index for transit snapshots so houses are reckoned natally.
    """
    planets: list[PlanetPosition] = []
    rahu_long_abs: float = 0.0
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED  # SPEED so we can detect retrograde
    for name, swe_id in PLANETS:
        position, _ = swe.calc_ut(julian_day, swe_id, flags)
        long_abs = float(position[0])
        long_speed = float(position[3])  # deg/day; negative = retrograde
        sign_idx = int(long_abs // 30)
        house = ((sign_idx - lagna_sign_idx) % 12) + 1
        # Vedic convention: Rahu (and Ketu below) always shown retrograde —
        # they're the "shadow planets", independent of true-node oscillation.
        is_retro = True if name == "Rahu" else long_speed < 0
        planets.append(
            PlanetPosition(
                name=name,
                rashi=RASHIS[sign_idx],
                house=house,
                longitude=long_abs - sign_idx * 30,
                nakshatra=NAKSHATRAS[int(long_abs // (360 / 27))],
                pada=_pada_of(long_abs),
                retrograde=is_retro,
            )
        )
        if name == "Rahu":
            rahu_long_abs = long_abs

    # Ketu = Rahu + 180° (always opposite, always retrograde in Vedic convention).
    ketu_long_abs = (rahu_long_abs + 180) % 360
    ketu_sign_idx = int(ketu_long_abs // 30)
    planets.append(
        PlanetPosition(
            name="Ketu",
            rashi=RASHIS[ketu_sign_idx],
            house=((ketu_sign_idx - lagna_sign_idx) % 12) + 1,
            longitude=ketu_long_abs - ketu_sign_idx * 30,
            nakshatra=NAKSHATRAS[int(ketu_long_abs // (360 / 27))],
            pada=_pada_of(ketu_long_abs),
            retrograde=True,
        )
    )
    return planets


def _rashi_index(rashi_label: str) -> int:
    """0..11 index for a 'Cancer (Karka)'-style RASHIS label."""
    return RASHIS.index(rashi_label)


# ---------------------------------------------------------------------------
# D-9 Navamsha divisional chart (Issue #62)
# ---------------------------------------------------------------------------
#
# Each rashi (30°) is divided into 9 equal 3°20' parts (pada). The rashi
# occupying a given pada follows Parashari rules: from the starting rashi
# (Aries for Aries/Leo/Sagittarius pada 1; the 9th sign for fixed signs;
# the 5th sign for dual signs), Navamsha rashis run in zodiacal order.
#
# The concise equivalent formula, derivable directly from those rules:
#     d9_sign_index = int(abs_longitude / (30/9)) % 12
#
# where abs_longitude is the sidereal longitude in 0..360°. Verified against
# classical examples: 15° Aries → Leo (5th pada), 0° Taurus → Capricorn
# (Taurus is fixed, starts from 9th from itself).
#
# Classical use: marriage/dharma readings. NOT a gate on yogas — Rao puts
# manifestation in D-1 and D-10 (§36.4; knowledge/divisional_charts.md, #398).
_NAVAMSHA_STEP = 30.0 / 9.0  # 3°20'


def compute_navamsha_chart(chart: Chart) -> Chart:
    """Compute the D-9 Navamsha divisional chart from a natal Chart.

    Returns a Chart object carrying D-9 lagna + planet placements; the
    birth-detail fields (lat/lon/tz/utc) are passed through unchanged
    because D-9 is a lens on the same birth, not a new event.

    Nakshatra and retrograde are preserved from D-1 (both are properties
    of the absolute longitude, not the divisional). Longitude within
    D-9 sign is computed from the residual pada position, so the diamond
    renderer can still display a degree for context.
    """
    d1_asc_abs = _rashi_index(chart.lagna_rashi) * 30.0 + chart.lagna_longitude
    d9_lagna_step = d1_asc_abs / _NAVAMSHA_STEP
    d9_lagna_idx = int(d9_lagna_step) % 12
    d9_lagna_long = (d9_lagna_step - int(d9_lagna_step)) * 30.0

    d9_planets: list[PlanetPosition] = []
    for p in chart.planets:
        abs_long = _rashi_index(p.rashi) * 30.0 + p.longitude
        step = abs_long / _NAVAMSHA_STEP
        d9_idx = int(step) % 12
        d9_long = (step - int(step)) * 30.0
        d9_house = ((d9_idx - d9_lagna_idx) % 12) + 1
        d9_planets.append(PlanetPosition(
            name=p.name,
            rashi=RASHIS[d9_idx],
            house=d9_house,
            longitude=d9_long,
            nakshatra=p.nakshatra,
            pada=p.pada,
            retrograde=p.retrograde,
        ))

    return Chart(
        lagna_rashi=RASHIS[d9_lagna_idx],
        lagna_longitude=d9_lagna_long,
        planets=d9_planets,
        birth_lat=chart.birth_lat,
        birth_lon=chart.birth_lon,
        birth_tz=chart.birth_tz,
        birth_utc=chart.birth_utc,
    )


def format_navamsha_for_prompt(chart: Chart) -> str:
    """Emit D-9 Navamsha placements as compact lines for LLM context.

    Format: one line per planet, plus the D-9 lagna at top. Prefix with
    a header the prompt can key off. Kept short — house + rashi per
    planet is enough for the marriage cross-check (not for yoga strength).
    """
    d9 = compute_navamsha_chart(chart)
    lines = [f"D-9 Navamsha Lagna: {d9.lagna_rashi.split(' ')[0]}"]
    for p in d9.planets:
        lines.append(f"  {p.name}: {p.rashi.split(' ')[0]} (house {p.house})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# D-10 Dashamsa divisional chart (Issue #64) — career/dharma lens
# ---------------------------------------------------------------------------
#
# Each rashi is divided into 10 equal parts of 3° each. Starting sign for
# the 1st pada follows the odd/even rule:
#   Odd signs (Aries, Gemini, Leo, Libra, Sagittarius, Aquarius) — start
#     from the same sign; each successive pada is the next sign.
#   Even signs (Taurus, Cancer, Virgo, Scorpio, Capricorn, Pisces) — start
#     from the 9th sign from itself (that's +8 in 0-indexed math).
#
# Classical use: read the 10th house of D-10 (and its lord) for career
# strength; a strong D-10 10th confirms professional success even when
# D-1 10th is weak.
_DASHAMSA_STEP = 3.0  # 30/10


def _dashamsa_sign_index(sign_idx: int, long_in_sign: float) -> int:
    pada = int(long_in_sign / _DASHAMSA_STEP)
    if sign_idx % 2 == 0:  # odd sign in classical 1-indexed count
        return (sign_idx + pada) % 12
    return (sign_idx + 8 + pada) % 12


def compute_dashamsa_chart(chart: Chart) -> Chart:
    """Compute the D-10 Dashamsa divisional chart from a natal Chart.

    D-10 lens on career/profession. Ascendant + planets remapped by the
    Parashari odd/even rule. Birth details + nakshatras carry through
    (same seeker, different divisional lens).
    """
    d1_lagna_idx = _rashi_index(chart.lagna_rashi)
    d10_lagna_idx = _dashamsa_sign_index(d1_lagna_idx, chart.lagna_longitude)
    pada_pos = chart.lagna_longitude % _DASHAMSA_STEP
    d10_lagna_long = (pada_pos / _DASHAMSA_STEP) * 30.0

    d10_planets: list[PlanetPosition] = []
    for p in chart.planets:
        p_sign_idx = _rashi_index(p.rashi)
        d10_idx = _dashamsa_sign_index(p_sign_idx, p.longitude)
        d10_pada_pos = p.longitude % _DASHAMSA_STEP
        d10_long = (d10_pada_pos / _DASHAMSA_STEP) * 30.0
        d10_house = ((d10_idx - d10_lagna_idx) % 12) + 1
        d10_planets.append(PlanetPosition(
            name=p.name,
            rashi=RASHIS[d10_idx],
            house=d10_house,
            longitude=d10_long,
            nakshatra=p.nakshatra,
            pada=p.pada,
            retrograde=p.retrograde,
        ))

    return Chart(
        lagna_rashi=RASHIS[d10_lagna_idx],
        lagna_longitude=d10_lagna_long,
        planets=d10_planets,
        birth_lat=chart.birth_lat,
        birth_lon=chart.birth_lon,
        birth_tz=chart.birth_tz,
        birth_utc=chart.birth_utc,
    )


def format_dashamsa_for_prompt(chart: Chart) -> str:
    """Emit D-10 Dashamsa placements for LLM context. Same shape as D-9."""
    d10 = compute_dashamsa_chart(chart)
    lines = [f"D-10 Dashamsa Lagna: {d10.lagna_rashi.split(' ')[0]}"]
    for p in d10.planets:
        lines.append(f"  {p.name}: {p.rashi.split(' ')[0]} (house {p.house})")
    return "\n".join(lines)


def _parse_local_datetime(date_str: str, time_str: str, tz_name: str) -> datetime:
    """Combine ISO date + HH:MM time + tz name into a tz-aware datetime."""
    try:
        return datetime.fromisoformat(f"{date_str}T{time_str}").replace(
            tzinfo=ZoneInfo(tz_name)
        )
    except ValueError as err:
        raise ChartError(
            f"Couldn't parse birth date/time {date_str!r} {time_str!r}: {err}"
        ) from err


# ---------------------------------------------------------------------------
# Kaal Sarp Yoga — for the standalone /kaal-sarp-check tool (Issue #111)
# ---------------------------------------------------------------------------
#
# HONEST NOTE ON PROVENANCE (added 2026-08-04 after Shyamasundara Dasa
# audit + independent classical-source review):
#
# Kaal Sarp Yoga does NOT appear in the classical Sanskrit Jyotish canon —
# not in Brihat Parashara Hora Shastra, Brihat Jataka, Saravali,
# Phaladeepika, Jataka Parijata, or Uttara Kalamrita. Its first verifiable
# Indian print discussion is in The Astrological Magazine in the late
# 1970s–early 1980s. K.N. Rao (Bharatiya Vidya Bhavan, founder of the
# Jyotish course) has publicly called it "one of the biggest frauds in
# astrology" and "of not much importance in individual charts." B.V. Raman
# added it as an APPENDIX (not the main text) to the 9th edition of
# Three Hundred Important Combinations because it had become "much feared"
# — his own treatment was nuanced, not alarmist.
#
# We keep the geometric detection because users search for it — but the
# 12 named variants (Anant, Kulik, Vasuki, ...) are unattributed folk
# taxonomy stabilised in mid-20th-c. Hindi almanac/pandit literature, not
# classical shastra. The previous per-variant "effects" text on this list
# was editorial invention repeated across every Kaal-Sarp site; we have
# replaced it with neutral geometry-only descriptions. Serious readings
# of Rahu-Ketu should judge them by the houses/lords they conjoin, not
# by axis-based blanket yogas.
#
# Classical geometric rule: when ALL 7 non-shadow planets (Sun, Moon,
# Mars, Mercury, Jupiter, Venus, Saturn) fall on ONE SIDE of the
# Rahu-Ketu axis, the chart matches the Kaal Sarp geometry. The
# Rahu-Ketu axis divides the zodiac into two 180° semicircles.
#
# Traditional Naga labels for each Rahu-house position, with geometry-
# only descriptions (no unsourced per-variant "effects" prediction):

_KAAL_SARP_TYPES: dict[int, tuple[str, str]] = {
    1:  ("Anant",     "Rahu-Ketu axis crosses your Lagna (1st) and Partnership (7th) houses — the self/other axis."),
    2:  ("Kulik",     "Rahu-Ketu axis crosses your Wealth (2nd) and Legacy (8th) houses — the resource/transformation axis."),
    3:  ("Vasuki",    "Rahu-Ketu axis crosses your Effort (3rd) and Dharma (9th) houses — the initiative/belief axis."),
    4:  ("Shankhpal", "Rahu-Ketu axis crosses your Home (4th) and Career (10th) houses — the inner-life/public-life axis."),
    5:  ("Padma",     "Rahu-Ketu axis crosses your Creativity (5th) and Community (11th) houses — the expression/network axis."),
    6:  ("Mahapadma", "Rahu-Ketu axis crosses your Service (6th) and Retreat (12th) houses — the discipline/dissolution axis."),
    7:  ("Takshak",   "Rahu-Ketu axis crosses your Partnership (7th) and Lagna (1st) houses — the other/self axis (reverse of Anant)."),
    8:  ("Karkotak",  "Rahu-Ketu axis crosses your Legacy (8th) and Wealth (2nd) houses — the transformation/resource axis (reverse of Kulik)."),
    9:  ("Shankchur", "Rahu-Ketu axis crosses your Dharma (9th) and Effort (3rd) houses — the belief/initiative axis (reverse of Vasuki)."),
    10: ("Ghatak",    "Rahu-Ketu axis crosses your Career (10th) and Home (4th) houses — the public-life/inner-life axis (reverse of Shankhpal)."),
    11: ("Vishdhar",  "Rahu-Ketu axis crosses your Community (11th) and Creativity (5th) houses — the network/expression axis (reverse of Padma)."),
    12: ("Sheshnag",  "Rahu-Ketu axis crosses your Retreat (12th) and Service (6th) houses — the dissolution/discipline axis (reverse of Mahapadma)."),
}


@dataclass(frozen=True)
class KaalSarpDetails:
    """Kaal Sarp Dosh — presence, type, and severity for the standalone checker.

    `type_name` and `type_meaning` are populated only when is_kaal_sarp is True.
    `is_partial` marks the softer case where one non-shadow planet straddles
    the Rahu-Ketu axis by ≤3° (some schools count this as Anshik / Partial KSD).
    """
    is_kaal_sarp: bool
    is_partial: bool
    type_name: str          # "" when not KSD
    type_meaning: str       # "" when not KSD
    rahu_house: int         # 1..12 (0 if Rahu missing from chart, defensive)
    ketu_house: int         # 1..12
    planets_before_rahu: tuple[str, ...]  # non-shadow planets on Rahu's side (walked in zodiacal order Rahu→Ketu)
    planets_after_ketu: tuple[str, ...]   # non-shadow planets on Ketu's side


def compute_kaal_sarp(chart: Chart) -> KaalSarpDetails:
    """Detect Kaal Sarp Dosh — strict binary, and the binary is OURS, not theirs.

    An earlier version of this docstring read "strict binary per classical
    Vedic tradition" and said "Classical sources (Brihat Parashara Hora
    Shastra, Phaladeepika, Saravali) treat Kaal Sarp Dosh as BINARY... No
    'partial' concept exists in the classical texts."

    That contradicted the module comment 64 lines above it, which records --
    with its print history -- that Kaal Sarp Yoga "does NOT appear in the
    classical Sanskrit Jyotish canon -- not in Brihat Parashara Hora Shastra,
    Brihat Jataka, Saravali, Phaladeepika, Jataka Parijata, or Uttara
    Kalamrita", first surfacing in The Astrological Magazine around 1980.
    Both cannot be true: a text that does not contain the concept cannot
    treat it as binary. The comment above is the researched one, so this is
    the sentence that was wrong -- and it was wrong in the direction that
    lends a modern construct the authority of books nobody here can open.
    None of the three named books is in `data/`; see #216.

    The binary rule is still right, and the reasons below are the real ones:
    there is no agreed threshold, a partial diagnosis manufactures anxiety,
    and reputable practitioners do not make it. Those stand on their own.
    They do not need, and never had, a classical citation.

    Modern practitioners have introduced "Anshik/Partial KSD" for near-axis
    cases, but (a) there's no agreed threshold across schools, (b) it
    generates false-positive anxiety, and (c) most reputable classical
    astrologers do NOT diagnose it. We follow the classical binary rule.

    Algorithm:
      1. Find Rahu's absolute longitude L_R (0..360°); Ketu is L_R + 180°.
      2. For each of the 7 non-shadow planets, compute their forward angular
         distance from Rahu: delta = (L_p - L_R) mod 360.
      3. If ALL 7 planets have 0 < delta < 180, they're on Rahu's side
         (the Rahu → Ketu half). If ALL 7 have 180 < delta < 360, they're
         on Ketu's side. Either way = FULL KSD.
      4. Otherwise: no KSD. Period.

    Removed the previous "partial" straddle logic (2026-07-30) after a
    user reported false positive that no astrologer had confirmed. If
    Anshik/Partial diagnosis is genuinely needed in the future, add it
    as an explicit opt-in with a documented threshold + classical source.
    """
    rahu = next((p for p in chart.planets if p.name == "Rahu"), None)
    ketu = next((p for p in chart.planets if p.name == "Ketu"), None)
    if rahu is None or ketu is None:
        return KaalSarpDetails(False, False, "", "", 0, 0, (), ())

    rahu_house = rahu.house
    ketu_house = ketu.house

    rahu_abs = _rashi_index(rahu.rashi) * 30.0 + rahu.longitude

    non_shadow = [p for p in chart.planets if p.name not in ("Rahu", "Ketu")]
    on_rahu_side: list[str] = []   # delta in (0, 180) — Rahu → Ketu semicircle
    on_ketu_side: list[str] = []   # delta in (180, 360) — Ketu → Rahu semicircle
    for p in non_shadow:
        abs_long = _rashi_index(p.rashi) * 30.0 + p.longitude
        delta = (abs_long - rahu_abs) % 360.0
        # Strict classical: any planet exactly on the axis (delta 0 or 180)
        # is a measurement-boundary edge case, not a "partial" trigger.
        # Assign to whichever side is closer.
        if delta < 180.0:
            on_rahu_side.append(p.name)
        else:
            on_ketu_side.append(p.name)

    # Strict binary: all 7 must be on the same side.
    is_full = len(on_rahu_side) == 7 or len(on_ketu_side) == 7

    if not is_full:
        return KaalSarpDetails(
            is_kaal_sarp=False,
            is_partial=False,          # deprecated; retained in dataclass for template compat
            type_name="",
            type_meaning="",
            rahu_house=rahu_house,
            ketu_house=ketu_house,
            planets_before_rahu=tuple(on_rahu_side),
            planets_after_ketu=tuple(on_ketu_side),
        )

    type_name, type_meaning = _KAAL_SARP_TYPES.get(rahu_house, ("", ""))
    return KaalSarpDetails(
        is_kaal_sarp=True,
        is_partial=False,              # never set True — classical binary
        type_name=type_name,
        type_meaning=type_meaning,
        rahu_house=rahu_house,
        ketu_house=ketu_house,
        planets_before_rahu=tuple(on_rahu_side),
        planets_after_ketu=tuple(on_ketu_side),
    )


# ---------------------------------------------------------------------------
# Bhagya Score — gamified 0-100 read of the chart's current chapter
# ---------------------------------------------------------------------------
#
# A single-number 'current-chapter weather' score. Explicitly NOT a
# 'good-vs-bad chart' rating — the reader sees WHY (top 3 signals) below
# the number so a low score reads as 'here is where classical remedies
# matter most right now' rather than 'you have bad luck'.
#
# Editorial framing rule (see README): the score changes as transits
# and dashas shift. Someone with a 42 today may be at 71 in 18 months
# when Sade Sati exits. It is weather, not destiny.
#
# Signals are weighted deliberately so no single signal dominates. Bad
# transits reduce; classical yogas and benefic dashas restore. Every
# reducer has a matching booster somewhere on the chart, so the base of
# 50 tends to move ±20 for most people — extreme scores (either end)
# require multiple aligned signals and are honest indicators.

@dataclass(frozen=True)
class BhagyaScoreDriver:
    """One signal feeding into the Bhagya Score total.

    `weight` is the delta from base (positive or negative). `note` is
    the human-readable reason shown in the 'why' panel.
    """
    weight: int
    note: str
    kind: str   # 'boost' or 'reduce' — for template styling


@dataclass(frozen=True)
class BhagyaScore:
    """0-100 gamified reading of the chart's current chapter.

    Never a fixed 'chart quality' number — it moves with dashas and
    transits. Template shows drivers so the number is transparent.
    """
    value: int              # 0..100
    label: str              # 'Strong current chapter' / 'Steady period' / etc.
    label_class: str        # tailwind color for the label ('emerald' / 'astro' / 'amber' / 'rose')
    drivers: tuple[BhagyaScoreDriver, ...]   # ordered by absolute weight desc

    @property
    def top_drivers(self) -> tuple[BhagyaScoreDriver, ...]:
        """Top-3 highest-impact drivers, for the compact 'why' panel."""
        return self.drivers[:3]


def _localize_house_ordinal(n: int, lang: str) -> str:
    """Render a house number for Bhagya-Score driver notes.

    English: "2nd", "3rd", etc. via _ordinal helper.
    Hindi:   "{n}वें" (nth) — same suffix works for 2वें/3वें/4वें/...
    """
    if lang == "hi":
        return f"{n}वें"
    return _ordinal(n)


def compute_bhagya_score(chart: Chart, lang: str = "en") -> BhagyaScore:
    """Compute the Bhagya Score for a chart.

    All classical rules already implemented elsewhere in chart.py — we
    just aggregate their outputs into a single scalar for gamification.

    `lang` selects the driver-note + label language. Notes are looked up
    from i18n.py so Hindi users see driver reasons in Devanagari, not
    English mid-page (Shyamasundara audit follow-up 2026-08-04).
    """
    from astro_ai.i18n import (
        translate,
        planet_name as _p_name,
        planet_names_joined as _p_joined,
        yoga_names_joined as _y_joined,
        kaal_sarp_variant_name as _ks_name,
    )

    drivers: list[BhagyaScoreDriver] = []
    score = 50

    def _add(delta: int, key: str, **kwargs) -> None:
        nonlocal score
        score += delta
        drivers.append(BhagyaScoreDriver(
            weight=delta, note=translate(lang, key, **kwargs),
            kind="boost" if delta > 0 else "reduce",
        ))

    # ─── Yogas: auspicious classical combinations ──────────────────
    yogas = compute_yogas(chart)
    # Only AUSPICIOUS yogas boost the score (#208 follow-up). This used to be
    # `if yogas:` over the whole list, so Kemadruma — a yoga of isolation —
    # added +5 exactly as Gaja-Kesari does. The "challenge" category exists to
    # keep that distinction; anything filed under it is not a strength and
    # must never be scored as one.
    auspicious = [y for y in yogas if y.category != "challenge"]
    if auspicious:
        n_yogas = min(len(auspicious), 3)   # cap so a single feature doesn't dominate
        yoga_names = _y_joined([y.name for y in auspicious[:n_yogas]], lang)
        _add(+5 * n_yogas, "bs_yogas_active", n=n_yogas,
             plural=("s" if n_yogas > 1 and lang == "en" else ""), names=yoga_names)

    # ─── Manglik status (from Mars-in-1/2/4/7/8/12 with all classical
    #     cancellation rules applied — mangal_details returns the FINAL
    #     effective status, not the raw placement). Possible values are
    #     'none' | 'present' | 'mitigated' | 'cancelled'.
    #     - none      : no Manglik pattern detected, no driver
    #     - cancelled : all classical cancellations applied, +5
    #     - mitigated : Manglik pattern but some (not all) cancellations, -3
    #     - present   : Manglik pattern, no cancellations applied, -8
    mangal = compute_manglik_details(chart)
    # Venus-axis-only (Kuja-Shukra) gets a friendlier driver note — many charts
    # flagged 'mitigated' here are actually clean per the mainstream
    # Lagna/Moon-only Manglik check. This used to be inferred from a
    # status/house/severity proxy; compute_manglik_details now carries the fact
    # itself, so read it at source instead of guessing at it.
    v_only = mangal.venus_axis_only
    if mangal.effective_status == "cancelled":
        _add(+5, "bs_manglik_cancelled")
    elif v_only:
        _add(-1, "bs_manglik_kuja_shukra")
    elif mangal.effective_status == "mitigated":
        _add(-3, "bs_manglik_mitigated")
    elif mangal.effective_status == "present":
        _add(-8, "bs_manglik_present")

    # ─── Sade Sati transit phase — Saturn ±1 rashi from natal Moon ─
    flags = compute_vedic_flags(chart)
    if flags.sade_sati:
        phase = (flags.sade_sati_phase or "").lower()
        if phase == "peak":
            _add(-10, "bs_sade_sati_peak")
        elif phase == "rising":
            _add(-5, "bs_sade_sati_rising")
        elif phase == "setting":
            _add(-3, "bs_sade_sati_setting")
    else:
        _add(+3, "bs_sade_sati_inactive")

    # Kantaka + Ashtama Shani — softer classical Saturn cautions.
    if flags.ashtama_shani:
        _add(-4, "bs_ashtama_shani")
    if flags.kantaka_shani:
        _add(-3, "bs_kantaka_shani")

    # ─── Kaal Sarp — geometric pattern (not classical shastra — the
    #     20th-c. modern classification per our /kaal-sarp-check review).
    #     Keep in the score but treat as a prompt, not a verdict.
    ksd = compute_kaal_sarp(chart)
    if ksd.is_kaal_sarp:
        _add(-12, "bs_kaal_sarp",
             variant=_ks_name(ksd.type_name or "active", lang))

    # ─── Planet dignities — exalted planets add, debilitated subtract
    exalted = []
    debilitated = []
    for p in chart.planets:
        if p.name in ("Rahu", "Ketu"):
            continue  # nodal dignity theory contested; skip
        rashi_en = p.rashi.split(" ")[0] if " " in p.rashi else p.rashi
        if _EXALTATION_SIGN.get(p.name) == rashi_en:
            exalted.append(p.name)
        elif _DEBILITATION_SIGN.get(p.name) == rashi_en:
            debilitated.append(p.name)
    if exalted:
        pts = min(len(exalted) * 3, 9)   # cap +9
        _add(+pts, "bs_exalted", n=len(exalted),
             plural=("s" if len(exalted) > 1 and lang == "en" else ""),
             names=_p_joined(exalted, lang))
    if debilitated:
        pts = -min(len(debilitated) * 3, 9)   # cap -9
        _add(pts, "bs_debilitated", n=len(debilitated),
             plural=("s" if len(debilitated) > 1 and lang == "en" else ""),
             names=_p_joined(debilitated, lang))

    # ─── Current Mahadasha lord — Jupiter/Venus/Moon add, Saturn/Rahu subtract
    #     Sun/Mars/Mercury/Ketu are neutral (context matters too much) ─
    try:
        dasha = compute_dasha_state(chart)
        lord = (dasha.mahadasha.lord or "").split(" ")[0]
        if lord in ("Jupiter", "Venus", "Moon"):
            _add(+5, "bs_maha_benefic", lord=_p_name(lord, lang))
        elif lord in ("Saturn", "Rahu"):
            _add(-3, "bs_maha_malefic", lord=_p_name(lord, lang))
        # ─── Current Antardasha — shifts every few months, adds daily
        #     relevance the Mahadasha alone can't. Softer weight than
        #     Mahadasha because a benefic Antardasha inside a malefic
        #     Mahadasha still feels malefic overall.
        ad_lord = (dasha.antardasha.lord or "").split(" ")[0]
        if ad_lord and ad_lord != lord:  # avoid double-counting Maha=Antar overlap
            if ad_lord in ("Jupiter", "Venus", "Moon"):
                _add(+2, "bs_antar_benefic", lord=_p_name(ad_lord, lang))
            elif ad_lord in ("Saturn", "Rahu"):
                _add(-2, "bs_antar_malefic", lord=_p_name(ad_lord, lang))
    except Exception:
        pass

    # ─── Gochar (today's transits) — the actually-daily-changing layer.
    #     Score up till now was mostly natal + dasha (both slow). Gochar
    #     is what makes the score meaningfully move day-to-day. Two most
    #     impactful classical gochar signals:
    #       - Jupiter's house from natal Moon (Guru Gochar): 2, 5, 7, 9,
    #         11 favourable; 3, 4, 8, 12 challenging; 1, 6, 10 neutral
    #       - Rahu / Ketu currently over natal Moon or Lagna: -2 each
    try:
        transit = compute_transit_snapshot(chart)
        natal_moon = next((p for p in chart.planets if p.name == "Moon"), None)
        if natal_moon:
            natal_moon_idx = _rashi_index(natal_moon.rashi)
            # Jupiter Gochar from Moon
            t_jup = next((p for p in transit.planets if p.name == "Jupiter"), None)
            if t_jup:
                jup_house_from_moon = ((_rashi_index(t_jup.rashi) - natal_moon_idx) % 12) + 1
                house_str = _localize_house_ordinal(jup_house_from_moon, lang)
                if jup_house_from_moon in (2, 5, 7, 9, 11):
                    _add(+3, "bs_jup_gochar_good", house=house_str)
                elif jup_house_from_moon in (3, 4, 8, 12):
                    _add(-2, "bs_jup_gochar_slow", house=house_str)
            # Rahu / Ketu transiting over natal Moon or natal Lagna axis
            natal_lagna_idx = _rashi_index(chart.lagna_rashi)
            for node in ("Rahu", "Ketu"):
                t_node = next((p for p in transit.planets if p.name == node), None)
                if t_node:
                    t_idx = _rashi_index(t_node.rashi)
                    if t_idx == natal_moon_idx:
                        _add(-2, "bs_node_over_moon", node=_p_name(node, lang))
                    elif t_idx == natal_lagna_idx:
                        _add(-2, "bs_node_over_lagna", node=_p_name(node, lang))
    except Exception:
        pass

    # ─── Clamp + label bucket ──────────────────────────────────────
    score = max(0, min(100, score))
    if score >= 75:
        label = translate(lang, "bs_label_strong")
        label_class = "emerald"
    elif score >= 50:
        label = translate(lang, "bs_label_steady")
        label_class = "astro"
    elif score >= 25:
        label = translate(lang, "bs_label_testing")
        label_class = "amber"
    else:
        label = translate(lang, "bs_label_deep")
        label_class = "rose"

    # Sort drivers by absolute impact so the 'why' panel highlights the
    # biggest movers first.
    drivers.sort(key=lambda d: abs(d.weight), reverse=True)
    return BhagyaScore(
        value=score,
        label=label,
        label_class=label_class,
        drivers=tuple(drivers),
    )
