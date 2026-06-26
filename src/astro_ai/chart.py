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

from dataclasses import dataclass
from datetime import date as date_, datetime, time, timedelta
from zoneinfo import ZoneInfo

import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

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

_GEOCODER = Nominatim(user_agent="astro-ai/0.0.1 (mahajananuj07@gmail.com)")
_TF = TimezoneFinder()

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


def geocode_place(place: str) -> tuple[float, float, str]:
    """Resolve a free-text place into (lat, lon, tz_name).

    Uses Nominatim (OpenStreetMap, free). Raises ChartError on miss.
    """
    try:
        location = _GEOCODER.geocode(place, timeout=10)
    except Exception as err:
        raise ChartError(f"Geocoding failed for {place!r}: {err}") from err
    if location is None:
        raise ChartError(
            f"Couldn't find the place {place!r}. Try a more specific form like "
            "'Mumbai, India' or 'Brooklyn, New York, USA'."
        )
    lat, lon = float(location.latitude), float(location.longitude)
    tz = _TF.timezone_at(lat=lat, lng=lon)
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


def compute_vedic_flags(natal: Chart, when: datetime | None = None) -> VedicFlags:
    """Compute Mangal Dosh (natal) + Sade Sati (uses current Saturn transit)."""
    moment = (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC"))
    julian_day = swe.julday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour + moment.minute / 60 + moment.second / 3600,
    )

    mars = next(p for p in natal.planets if p.name == "Mars")
    moon = next(p for p in natal.planets if p.name == "Moon")
    moon_idx = _rashi_index(moon.rashi)
    mars_idx = _rashi_index(mars.rashi)

    # MANGAL DOSH — Mars in house 1, 2, 4, 7, 8, or 12 from Lagna OR Moon.
    # Some traditions exclude 2nd; we include for the broadest definition.
    # Cancellations (Mars in own/exalted sign, Jupiter aspect, etc.) are not
    # yet computed — flag this in the LLM prompt so it adds the usual caveat.
    manglik_reasons: list[str] = []
    if mars.house in {1, 2, 4, 7, 8, 12}:
        manglik_reasons.append(f"Mars in {_ordinal(mars.house)} house from Lagna")
    mars_from_moon = ((mars_idx - moon_idx) % 12) + 1
    if mars_from_moon in {1, 2, 4, 7, 8, 12}:
        manglik_reasons.append(f"Mars in {_ordinal(mars_from_moon)} house from Moon")

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
        manglik=bool(manglik_reasons),
        manglik_reasons=tuple(manglik_reasons),
        sade_sati=sade_sati_phase is not None,
        sade_sati_phase=sade_sati_phase,
        saturn_house_from_natal_moon=saturn_house_from_moon,
    )


def format_flags_for_prompt(flags: VedicFlags) -> str:
    """Plain-English flag block appended to the LLM user message."""
    lines = ["Vedic flags (deterministic, do not contradict):"]
    if flags.manglik:
        reasons = "; ".join(flags.manglik_reasons)
        lines.append(f"- Manglik (Mangal Dosh): YES — {reasons}. Address this in the Relationships section.")
    else:
        lines.append("- Manglik (Mangal Dosh): NO")
    if flags.sade_sati:
        phase_text = {
            "rising": "rising phase (arohini) — Saturn transiting 12th from natal Moon",
            "peak": "peak phase (madhya) — Saturn transiting natal Moon's own sign (1st from Moon)",
            "setting": "setting phase (avarohini) — Saturn transiting 2nd from natal Moon",
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
class ManglikDetails:
    """Manglik (Mangal Dosh) — fuller than VedicFlags so we can render an explanatory panel."""

    is_manglik: bool
    houses: tuple[int, ...]       # all qualifying Mars houses (1/2/4/7/8/12 from Lagna or Moon)
    primary_house: int            # most-severe house (or 0 if not manglik)
    severity: str                 # "high" | "moderate" | "low" | "none"


def compute_manglik_details(chart: Chart) -> ManglikDetails:
    """Identify all Manglik-qualifying Mars positions + grade severity by worst house."""
    mars = next(p for p in chart.planets if p.name == "Mars")
    moon = next(p for p in chart.planets if p.name == "Moon")
    moon_idx = _rashi_index(moon.rashi)
    mars_idx = _rashi_index(mars.rashi)

    qualifying = set()
    if mars.house in {1, 2, 4, 7, 8, 12}:
        qualifying.add(mars.house)
    mars_from_moon = ((mars_idx - moon_idx) % 12) + 1
    if mars_from_moon in {1, 2, 4, 7, 8, 12}:
        qualifying.add(mars_from_moon)

    if not qualifying:
        return ManglikDetails(is_manglik=False, houses=(), primary_house=0, severity="none")

    # Severity grading: 7th/8th = most serious; 1st/4th/12th = moderate; 2nd alone = low.
    if {7, 8} & qualifying:
        severity = "high"
    elif {1, 4, 12} & qualifying:
        severity = "moderate"
    else:
        severity = "low"

    # "Primary" house for storytelling — the most-impactful qualifying house.
    house_priority = (7, 8, 1, 4, 12, 2)
    primary = next(h for h in house_priority if h in qualifying)
    return ManglikDetails(
        is_manglik=True,
        houses=tuple(sorted(qualifying)),
        primary_house=primary,
        severity=severity,
    )


@dataclass(frozen=True)
class SadeSatiDetails:
    """Sade Sati — phase + Saturn position relative to natal Moon, for educational panel."""

    is_active: bool
    phase: str | None                  # "rising" | "peak" | "setting"
    saturn_house_from_moon: int        # 1..12


def compute_sade_sati_details(chart: Chart, when: datetime | None = None) -> SadeSatiDetails:
    """Same calc as the flag, exposed as a dedicated value object for the panel."""
    flags = compute_vedic_flags(chart, when)
    return SadeSatiDetails(
        is_active=flags.sade_sati,
        phase=flags.sade_sati_phase,
        saturn_house_from_moon=flags.saturn_house_from_natal_moon,
    )


@dataclass(frozen=True)
class MarriageProfile:
    """Compact relationship readout drawn from the natal chart."""

    seventh: HouseProfile             # marriage / partnerships
    venus_sign: str                   # love + romance significator
    venus_house: int
    is_manglik: bool                  # surface the dosha here too — it's marriage-relevant


def compute_marriage_profile(chart: Chart) -> MarriageProfile:
    venus = next(p for p in chart.planets if p.name == "Venus")
    flags = compute_vedic_flags(chart)
    return MarriageProfile(
        seventh=house_profile(chart, 7),
        venus_sign=venus.rashi,
        venus_house=venus.house,
        is_manglik=flags.manglik,
    )


@dataclass(frozen=True)
class WealthProfile:
    """Compact wealth/money readout drawn from the natal chart.

    Two key houses (2nd = accumulated wealth/family/speech; 11th = gains/income)
    plus Jupiter (wealth significator in classical Vedic astrology).
    """

    dhana: HouseProfile               # 2nd house — accumulated wealth, family, speech
    labha: HouseProfile               # 11th house — gains, income, aspirations
    jupiter_sign: str
    jupiter_house: int


# ---------------------------------------------------------------------------
# Gochar (transit) impacts — slow movers' current placement + favourability
# ---------------------------------------------------------------------------


# Classical favourability per (planet, house from Lagna). Houses 3/6/10/11
# generally support malefics (Saturn especially); 5/9/2/11 favour benefics.
# Anything not listed defaults to neutral.
_GOCHAR_FAVOURABILITY: dict[tuple[str, int], str] = {
    # Saturn — likes upachaya houses (3, 6, 10, 11)
    ("Saturn", 3): "favorable", ("Saturn", 6): "favorable", ("Saturn", 11): "favorable",
    ("Saturn", 4): "challenging", ("Saturn", 8): "challenging", ("Saturn", 12): "challenging",
    # Jupiter — favours dharma + dhana houses
    ("Jupiter", 1): "favorable", ("Jupiter", 2): "favorable", ("Jupiter", 5): "favorable",
    ("Jupiter", 9): "favorable", ("Jupiter", 11): "favorable",
    ("Jupiter", 6): "challenging", ("Jupiter", 8): "challenging", ("Jupiter", 12): "challenging",
    # Rahu — broadly unpredictable; mark known patterns
    ("Rahu", 3): "favorable", ("Rahu", 6): "favorable", ("Rahu", 11): "favorable",
    ("Rahu", 1): "challenging", ("Rahu", 7): "challenging", ("Rahu", 8): "challenging",
    # Ketu — similar but mirror
    ("Ketu", 3): "favorable", ("Ketu", 9): "favorable", ("Ketu", 12): "favorable",
    ("Ketu", 1): "challenging", ("Ketu", 7): "challenging", ("Ketu", 8): "challenging",
}


@dataclass(frozen=True)
class GocharImpact:
    """One slow-mover's current transit + houses + favourability classification."""

    planet: str
    sign: str
    house_from_lagna: int
    house_from_moon: int
    retrograde: bool
    favorability: str  # "favorable" | "neutral" | "challenging"


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
                favorability=_GOCHAR_FAVOURABILITY.get((name, p.house), "neutral"),
            )
        )
    return impacts


def compute_wealth_profile(chart: Chart) -> WealthProfile:
    jupiter = next(p for p in chart.planets if p.name == "Jupiter")
    return WealthProfile(
        dhana=house_profile(chart, 2),
        labha=house_profile(chart, 11),
        jupiter_sign=jupiter.rashi,
        jupiter_house=jupiter.house,
    )


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
# Classical Vedic assignment — varies by weekday.
_RAHU_KAAL_SEGMENT: dict[int, int] = {
    0: 2,  # Monday    — 2nd part
    1: 7,  # Tuesday   — 7th part
    2: 5,  # Wednesday — 5th part
    3: 6,  # Thursday  — 6th part
    4: 4,  # Friday    — 4th part
    5: 3,  # Saturday  — 3rd part
    6: 8,  # Sunday    — 8th part
}


@dataclass(frozen=True)
class DailyPanchang:
    """Today's Muhurta data — what to do (and not do), plus the day's favourable color.

    All times are tz-aware local datetimes at the natal birthplace. Rahu Kaal
    is the inauspicious window; Abhijit Muhurta is the most auspicious window
    (centered on solar noon).
    """

    weekday: str            # "Friday"
    day_lord: str           # "Venus"
    day_color: str          # human-readable, e.g. "White or Light Pink"
    day_color_hex: str      # for a UI color swatch
    sunrise: datetime
    sunset: datetime
    rahu_kaal_start: datetime
    rahu_kaal_end: datetime
    abhijit_start: datetime
    abhijit_end: datetime


def compute_panchang(natal: Chart, when: datetime | None = None) -> DailyPanchang:
    """Compute today's Rahu Kaal, Abhijit Muhurta, and day's color for the natal birthplace.

    Uses natal lat/lon because we don't know where the seeker physically is
    now. Note this on the UI — for the most precise local Muhurta, the
    seeker should ideally compute against their current location.
    """
    tz = ZoneInfo(natal.birth_tz)
    moment = (when or datetime.now(tz)).astimezone(tz)
    today = moment.date()
    weekday = today.weekday()  # 0=Mon..6=Sun

    weekday_name, day_lord, day_color, day_color_hex = _WEEKDAY_LORDS[weekday]
    sunrise, sunset = _sunrise_sunset(today, natal.birth_lat, natal.birth_lon, tz)

    # Rahu Kaal: which 1/8 segment of the daylight period?
    day_seconds = (sunset - sunrise).total_seconds()
    segment_seconds = day_seconds / 8.0
    rk_segment_idx = _RAHU_KAAL_SEGMENT[weekday]
    rk_start = sunrise + timedelta(seconds=(rk_segment_idx - 1) * segment_seconds)
    rk_end = sunrise + timedelta(seconds=rk_segment_idx * segment_seconds)

    # Abhijit Muhurta: 8th of the 15 daylight muhurtas — centered on solar noon,
    # spanning roughly day_length/15 (~48 minutes on equinox days).
    midday = sunrise + timedelta(seconds=day_seconds / 2.0)
    abhijit_half = timedelta(seconds=(day_seconds / 15.0) / 2.0)
    return DailyPanchang(
        weekday=weekday_name,
        day_lord=day_lord,
        day_color=day_color,
        day_color_hex=day_color_hex,
        sunrise=sunrise,
        sunset=sunset,
        rahu_kaal_start=rk_start,
        rahu_kaal_end=rk_end,
        abhijit_start=midday - abhijit_half,
        abhijit_end=midday + abhijit_half,
    )


def format_panchang_for_prompt(panchang: DailyPanchang) -> str:
    """Plain-English Panchang block for the daily-reading user message."""
    return (
        "Today's Panchang (computed for the seeker's natal birthplace):\n"
        f"- Day: {panchang.weekday}, ruled by {panchang.day_lord}\n"
        f"- Favourable color: {panchang.day_color}\n"
        f"- Sunrise: {panchang.sunrise.strftime('%H:%M')} local\n"
        f"- Sunset: {panchang.sunset.strftime('%H:%M')} local\n"
        f"- Rahu Kaal (inauspicious — avoid starting anything new, signing, big decisions): "
        f"{panchang.rahu_kaal_start.strftime('%H:%M')}–{panchang.rahu_kaal_end.strftime('%H:%M')} local\n"
        f"- Abhijit Muhurta (most auspicious — favourable for important actions): "
        f"{panchang.abhijit_start.strftime('%H:%M')}–{panchang.abhijit_end.strftime('%H:%M')} local"
    )


def _sunrise_sunset(
    day: date_, lat: float, lon: float, tz: ZoneInfo
) -> tuple[datetime, datetime]:
    """Sunrise + sunset for `day` at (lat, lon), returned as tz-aware local datetimes."""
    midnight_local = datetime.combine(day, time(0), tzinfo=tz)
    midnight_utc = midnight_local.astimezone(ZoneInfo("UTC"))
    start_jd = swe.julday(
        midnight_utc.year, midnight_utc.month, midnight_utc.day,
        midnight_utc.hour + midnight_utc.minute / 60.0,
    )
    geopos = (lon, lat, 0.0)  # pyswisseph wants (lon, lat, elev) in that order
    _, rise_arr = swe.rise_trans(start_jd, swe.SUN, swe.CALC_RISE, geopos)
    _, set_arr = swe.rise_trans(start_jd, swe.SUN, swe.CALC_SET, geopos)
    return (
        _jd_to_utc_datetime(rise_arr[0]).astimezone(tz),
        _jd_to_utc_datetime(set_arr[0]).astimezone(tz),
    )


def _jd_to_utc_datetime(jd: float) -> datetime:
    """Inverse of swe.julday — convert a Julian Day number to a tz-aware UTC datetime."""
    y, m, d, hour_frac = swe.revjul(jd)
    hours = int(hour_frac)
    minutes = int((hour_frac - hours) * 60)
    seconds = int(round(((hour_frac - hours) * 60 - minutes) * 60))
    if seconds >= 60:
        minutes += 1
        seconds = 0
    return datetime(int(y), int(m), int(d), hours, minutes, seconds, tzinfo=ZoneInfo("UTC"))


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
            retrograde=True,
        )
    )
    return planets


def _rashi_index(rashi_label: str) -> int:
    """0..11 index for a 'Cancer (Karka)'-style RASHIS label."""
    return RASHIS.index(rashi_label)


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
