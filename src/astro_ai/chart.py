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

# Unicode zodiac glyphs — universal visual shorthand for each rashi.
# Same 12 symbols Western astrology uses; Vedic users recognise them too.
RASHI_SYMBOLS: tuple[str, ...] = (
    "♈",  # ♈ Aries
    "♉",  # ♉ Taurus
    "♊",  # ♊ Gemini
    "♋",  # ♋ Cancer
    "♌",  # ♌ Leo
    "♍",  # ♍ Virgo
    "♎",  # ♎ Libra
    "♏",  # ♏ Scorpio
    "♐",  # ♐ Sagittarius
    "♑",  # ♑ Capricorn
    "♒",  # ♒ Aquarius
    "♓",  # ♓ Pisces
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
    # Additional Saturn-transit conditions that are distinct from Sade Sati
    # but often confused with it. Per knowledge/vedic_reference.md §2.5:
    ashtama_shani: bool = False        # Saturn in 8th from natal Moon (~2.5y)
    kantaka_shani: bool = False        # Saturn in 4th from natal Moon (~2.5y)


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
        # Ashtama Shani (Saturn 8th from Moon) and Kantaka Shani (4th) are
        # distinct ~2.5y Saturn transits that classical texts flag alongside
        # Sade Sati. Previously the /sade-sati-check would silently report
        # "no Sade Sati" for users in these phases, leaving them unaware.
        ashtama_shani=(saturn_house_from_moon == 8),
        kantaka_shani=(saturn_house_from_moon == 4),
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

    Carrying the source on each rule lets the LLM cite specific texts
    (Jataka Parijata, Phaladeepika, …) instead of asserting cancellations
    on its own authority — turning a generic "don't worry" into a defensible
    statement the seeker can verify.
    """

    slug: str          # stable id for code paths / tests
    description: str   # human-readable rule
    effect: str        # "cancels" | "mitigates"
    source: str        # classical text it comes from


@dataclass(frozen=True)
class ManglikDetails:
    """Manglik (Mangal Dosh) — fuller than VedicFlags so we can render an explanatory panel.

    Raw mathematical flag (`is_manglik`) is augmented with cancellation /
    mitigation rules from classical practice. `effective_status` summarises
    what to actually tell the seeker. See knowledge/vedic_reference.md §1.3
    for the rule catalogue + classical citations.
    """

    is_manglik: bool
    houses: tuple[int, ...]                 # all qualifying Mars houses (1/2/4/7/8/12 from Lagna or Moon)
    primary_house: int                      # most-severe house (or 0 if not manglik)
    severity: str                           # "high" | "moderate" | "low" | "none"
    cancellations: tuple[ManglikRule, ...]  # all cancellation / mitigation rules that fired
    effective_status: str                   # "none" | "present" | "mitigated" | "cancelled"


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
    mars_abs = _rashi_index(mars.rashi) * 30.0 + mars.longitude
    sun_abs = _rashi_index(sun.rashi) * 30.0 + sun.longitude
    sep = abs(mars_abs - sun_abs) % 360.0
    sep = min(sep, 360.0 - sep)
    if sep < 6.0:
        rules.append(ManglikRule(
            slug="mars_combust",
            description=f"Mars combust (within {sep:.1f}° of Sun)",
            effect="cancels",
            source="Classical matching practice",
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

    qualifying = set()
    if mars.house in {1, 2, 4, 7, 8, 12}:
        qualifying.add(mars.house)
    mars_from_moon = ((mars_idx - moon_idx) % 12) + 1
    if mars_from_moon in {1, 2, 4, 7, 8, 12}:
        qualifying.add(mars_from_moon)
    mars_from_venus = ((mars_idx - venus_idx) % 12) + 1
    if mars_from_venus in {1, 2, 4, 7, 8, 12}:
        qualifying.add(mars_from_venus)

    if not qualifying:
        return ManglikDetails(
            is_manglik=False, houses=(), primary_house=0, severity="none",
            cancellations=(), effective_status="none",
        )

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

    return ManglikDetails(
        is_manglik=True,
        houses=tuple(sorted(qualifying)),
        primary_house=primary,
        severity=severity,
        cancellations=cancellations,
        effective_status=effective_status,
    )


# ---------------------------------------------------------------------------
# Yogas — classical planetary combinations
#
# Source: P.V.R. Narasimha Rao, "Vedic Astrology: An Integrated Approach",
# Chapter 11 (data/vedic_astro_textbook.pdf), cross-checked with BPHS and
# Phaladeepika. See knowledge/vedic_reference.md §4 for the full catalogue
# and rule definitions — keep this code and that file in sync when adding
# new yogas.
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
# Sourced from BPHS, Chapter 3 (Planets). Capricorn for Sasa is Saturn's
# moolatrikona; Cancer for Hamsa is Jupiter's exaltation sign.
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
    significations string the LLM can paraphrase; `source` is the classical
    text or modern compilation it comes from.
    """

    slug: str
    name: str
    category: str       # "pancha_mahapurusha" | "sun" | "moon" | "vipareeta_raja" | "other"
    effect: str
    source: str


def _pancha_mahapurusha_yogas(chart: Chart) -> list[YogaResult]:
    """The 5 'Great Person' yogas — own/exalted graha in a kendra from Lagna.

    Skipped for Sun and Moon (these are luminaries, not the 5 non-luminary grahas).
    """
    out: list[YogaResult] = []
    names = {
        "Mars":    ("ruchaka_yoga",  "Ruchaka Yoga",  "Fiery great-man: courage, leadership, victory, occult skill"),
        "Mercury": ("bhadra_yoga",   "Bhadra Yoga",   "Earthy great-man: learning, eloquence, systematic mind, business"),
        "Jupiter": ("hamsa_yoga",    "Hamsa Yoga",    "Ethery great-man: wisdom, dharma, respect, scholarly fame"),
        "Venus":   ("malavya_yoga",  "Malavya Yoga",  "Watery great-man: beauty, luxury, art, marital happiness"),
        "Saturn":  ("sasha_yoga",    "Sasha Yoga",    "Airy great-man: discipline, leadership of multitudes, charity"),
    }
    for p in chart.planets:
        if p.name not in _PMP_QUALIFYING_SIGNS:
            continue
        sign = _sign_name(p.rashi)
        if sign in _PMP_QUALIFYING_SIGNS[p.name] and p.house in _KENDRA_HOUSES:
            slug, name, effect = names[p.name]
            out.append(YogaResult(
                slug=slug, name=name, category="pancha_mahapurusha",
                effect=effect, source="BPHS / Phaladeepika",
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
            source="Brihat Parashara Hora Shastra",
        ))
    elif in_2nd:
        out.append(YogaResult(
            slug="vesi_yoga", name="Vesi Yoga", category="sun",
            effect="Balanced outlook, truthful, content",
            source="Brihat Parashara Hora Shastra",
        ))
    elif in_12th:
        out.append(YogaResult(
            slug="vosi_yoga", name="Vosi Yoga", category="sun",
            effect="Skillful, charitable, famous, learned",
            source="Brihat Parashara Hora Shastra",
        ))

    # Budha-Aditya: Sun + Mercury same sign. Combust if within ~6° → weakened.
    mercury = next(p for p in chart.planets if p.name == "Mercury")
    if mercury.rashi == sun.rashi:
        combust_note = ""
        if abs(mercury.longitude - sun.longitude) < 6.0:
            combust_note = " (weakened — Mercury is combust within 6° of Sun)"
        out.append(YogaResult(
            slug="budha_aditya_yoga", name="Budha-Aditya Yoga (Nipuna)", category="sun",
            effect=f"Intelligence, skill, respect; bright mind{combust_note}",
            source="Brihat Parashara Hora Shastra",
        ))
    return out


def _moon_yogas(chart: Chart) -> list[YogaResult]:
    """Sunaphaa, Anaphaa, Duradhara, Kemadruma, Chandra-Mangala, Gaja-Kesari."""
    out: list[YogaResult] = []
    moon = next(p for p in chart.planets if p.name == "Moon")
    others = [p for p in chart.planets if p.name not in {"Moon", "Sun", "Rahu", "Ketu"}]

    in_2nd = any(_house_from_planet(p.house, moon.house) == 2 for p in others)
    in_12th = any(_house_from_planet(p.house, moon.house) == 12 for p in others)
    in_same = any(p.house == moon.house for p in others)

    if in_2nd and in_12th:
        out.append(YogaResult(
            slug="duradhara_yoga", name="Duradhara Yoga", category="moon",
            effect="Pleasures, charity, wealth, vehicles, good servants",
            source="Brihat Parashara Hora Shastra",
        ))
    elif in_2nd:
        out.append(YogaResult(
            slug="sunaphaa_yoga", name="Sunaphaa Yoga", category="moon",
            effect="Royal stature; intelligence, wealth, fame, self-earned success",
            source="Brihat Parashara Hora Shastra",
        ))
    elif in_12th:
        out.append(YogaResult(
            slug="anaphaa_yoga", name="Anaphaa Yoga", category="moon",
            effect="Good-looking, disease-free, reputed, comfortable",
            source="Brihat Parashara Hora Shastra",
        ))

    # Kemadruma: NONE of 1st/2nd/12th from Moon AND no planets in kendras from Lagna.
    # Classical cancellations exist (Moon conjoined with planet, kendras occupied);
    # we apply the second cancellation deterministically. Don't flag if any kendra is occupied.
    kendras_occupied = any(p.house in _KENDRA_HOUSES for p in chart.planets if p.name not in {"Moon"})
    if not in_2nd and not in_12th and not in_same and not kendras_occupied:
        out.append(YogaResult(
            slug="kemadruma_yoga", name="Kemadruma Yoga", category="moon",
            effect="Lonely / unsupported Moon; emotional fragility — verify cancellations before alarm",
            source="Brihat Parashara Hora Shastra",
        ))

    # Chandra-Mangala: Moon and Mars conjunct
    mars = next(p for p in chart.planets if p.name == "Mars")
    if moon.house == mars.house:
        out.append(YogaResult(
            slug="chandra_mangala_yoga", name="Chandra-Mangala Yoga", category="moon",
            effect="Worldly-wise, materially successful; energetic relationship with money",
            source="Brihat Parashara Hora Shastra",
        ))

    # Gaja-Kesari: Jupiter in kendra (1/4/7/10) FROM Moon (not from Lagna).
    # Strict version requires Jupiter not debilitated/combust/in enemy sign — we
    # apply the debilitation check (Jupiter in Capricorn) as a downgrade signal.
    jupiter = next(p for p in chart.planets if p.name == "Jupiter")
    if _house_from_planet(jupiter.house, moon.house) in {1, 4, 7, 10}:
        debilitated = _sign_name(jupiter.rashi) == "Capricorn"
        note = " (weakened — Jupiter debilitated in Capricorn)" if debilitated else ""
        out.append(YogaResult(
            slug="gaja_kesari_yoga", name="Gaja-Kesari Yoga", category="moon",
            effect=f"Fame, wealth, intelligence, virtue, favor from authority{note}",
            source="Brihat Parashara Hora Shastra",
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
                slug=slug, name=name, category="vipareeta_raja",
                effect=effect, source="BPHS / Phaladeepika",
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
            source="Classical Vedic tradition",
        ))

    # Trilochana: Sun, Moon, Mars in mutual trines (4 signs apart from each other)
    diffs = sorted({(sun.house - mars.house) % 12, (moon.house - mars.house) % 12,
                    (sun.house - moon.house) % 12})
    if all(d in {0, 4, 8} for d in diffs):
        out.append(YogaResult(
            slug="trilochana_yoga", name="Trilochana Yoga", category="other",
            effect="Wealthy, intelligent, long-lived, victorious",
            source="Classical Vedic tradition",
        ))

    # Amala: only natural benefics in 10th from Lagna
    in_10th_lagna = [p for p in chart.planets if p.house == 10 and p.name not in {"Rahu", "Ketu"}]
    if in_10th_lagna and all(p.name in _NATURAL_BENEFICS for p in in_10th_lagna):
        out.append(YogaResult(
            slug="amala_yoga", name="Amala Yoga", category="other",
            effect="Ever-lasting fame, royal respect, virtue — clean reputation through career",
            source="Classical Vedic tradition",
        ))

    # Vasumati: benefics in upachayas (3rd, 6th, 10th, 11th from Lagna)
    benefics_in_upachaya = [p for p in chart.planets
                             if p.name in _NATURAL_BENEFICS and p.house in _UPACHAYA_HOUSES]
    if len(benefics_in_upachaya) >= 2:
        out.append(YogaResult(
            slug="vasumati_yoga", name="Vasumati Yoga", category="other",
            effect="Abundant wealth — benefics concentrated in growth-houses",
            source="Classical Vedic tradition",
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
            source="Classical Vedic tradition",
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
    for y in yogas:
        line = f"  • {y.name}: {y.effect}"
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


def format_planet_dignity_for_prompt(chart: "Chart") -> str:
    """Planet dignity report (Issue #61).

    For each of the 7 luminary+non-luminary planets (Rahu/Ketu don't own
    signs so are omitted here — their dignity theory is contested), report:
    - Sign + house
    - Dignity: EXALTED / OWN SIGN / DEBILITATED / neutral
    - Combust flag if within ~8° of Sun

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
        # Combust check: within ~8° of Sun (skip for Sun itself)
        if sun is not None and p.name != "Sun":
            sun_abs = _rashi_index(sun.rashi) * 30.0 + sun.longitude
            p_abs = _rashi_index(p.rashi) * 30.0 + p.longitude
            sep = min(abs(p_abs - sun_abs), 360 - abs(p_abs - sun_abs))
            if sep < 8.0:
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
    _special: dict[str, tuple[int, ...]] = {
        "Mars":    (4, 8),
        "Jupiter": (5, 9),
        "Saturn":  (3, 10),
        "Rahu":    (5, 9),
        "Ketu":    (5, 9),
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
        lines.append(f"  {p.name} in {p.nakshatra}{note}")
    return "\n".join(lines)


def format_manglik_for_prompt(details: ManglikDetails) -> str:
    """Tiny LLM hint for the Relationships section — only inject when relevant.

    Stays ~80-180 tokens. Tells the LLM the effective status and the
    cancelling/mitigating reasons in plain language; sources are deliberately
    omitted so the LLM can't echo them back as user-facing "per Phaladeepika"
    jargon. Classical citations live in the structured UI panel.
    """
    if details.effective_status == "none":
        return ""

    houses_str = ", ".join(_ordinal(h) for h in details.houses)
    lines = [
        f"--- MANGLIK DETAIL ---",
        f"Mathematical: YES — Mars in {houses_str} (severity: {details.severity}).",
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
        lines.append("No classical cancellation or mitigation reasons apply to this chart.")

    lines.append(f"Effective status: {details.effective_status.upper()}.")

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
            "Suggest the traditional remedy of matching with another Manglik partner. "
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

    # Sub-divide active Maha into Antardashas.
    antardashas = _build_antardashas(active_maha)
    active_antar = next((p for p in antardashas if p.start <= moment <= p.end), antardashas[0])
    active_antar_idx = antardashas.index(active_antar)
    upcoming = tuple(antardashas[active_antar_idx + 1 :])

    return DashaState(
        mahadasha=active_maha,
        antardasha=active_antar,
        upcoming_antardashas=upcoming,
        next_mahadasha=next_maha,
    )


def _build_antardashas(maha: DashaPeriod) -> list[DashaPeriod]:
    """9 sub-periods within `maha`, starting with the Maha lord, weighted by Vimshottari years."""
    start_idx = _VIM_ORDER.index(maha.lord)
    out: list[DashaPeriod] = []
    cursor = maha.start
    for i in range(9):
        sub_lord = _VIM_ORDER[(start_idx + i) % 9]
        sub_years = (maha.years * _VIM_YEARS[sub_lord]) / 120.0
        new_end = cursor + timedelta(days=sub_years * _DAYS_PER_YEAR)
        # Clamp last sub-period to exact Maha end to avoid float drift.
        if i == 8:
            new_end = maha.end
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
    sunrise: datetime         # local time at natal birthplace — LOCATION-DEPENDENT
    sunset: datetime          # local time at natal birthplace — LOCATION-DEPENDENT
    rahu_kaal_start: datetime # LOCATION-DEPENDENT
    rahu_kaal_end: datetime   # LOCATION-DEPENDENT
    abhijit_start: datetime   # LOCATION-DEPENDENT
    abhijit_end: datetime     # LOCATION-DEPENDENT


# In-process cache keyed by (date, rounded lat, rounded lon, tz name). Two
# subscribers in the same city on the same day share one compute — the
# per-request panchang_cache dict in the send loop already dedups within a
# batch; this cache extends dedup across the whole process's lifetime.
#
# Rounded to ~55km (0.5deg) — sunrise/sunset differ by seconds within that
# radius, well below the ~2min classical rounding. Cache is bounded by the
# small number of cities in the subscriber base, so we don't LRU-cap it.
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


def compute_panchang(natal: Chart, when: datetime | None = None) -> DailyPanchang:
    """Compute today's Panchang for the natal birthplace, cached per (date, city).

    Uses natal lat/lon because we don't know where the seeker physically is
    now. Note this on the UI — for the most precise local Muhurta, the
    seeker should ideally compute against their current location.

    Location-independent fields (weekday, tithi, paksha) are the same
    worldwide for a given date; location-dependent ones (sunrise, Rahu Kaal,
    Abhijit) genuinely vary by city. The in-process cache dedups per city.
    """
    tz = ZoneInfo(natal.birth_tz)
    moment = (when or datetime.now(tz)).astimezone(tz)
    today = moment.date()

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
    result = DailyPanchang(
        weekday=weekday_name,
        day_lord=day_lord,
        day_color=day_color,
        day_color_hex=day_color_hex,
        tithi_index=tithi_idx,
        tithi_name=tithi_name,
        tithi_paksha=tithi_paksha,
        tithi_significance=tithi_sig,
        sunrise=sunrise,
        sunset=sunset,
        rahu_kaal_start=rk_start,
        rahu_kaal_end=rk_end,
        abhijit_start=midday - abhijit_half,
        abhijit_end=midday + abhijit_half,
    )
    _PANCHANG_CACHE[cache_key] = result
    return result


def format_panchang_for_prompt(panchang: DailyPanchang) -> str:
    """Plain-English Panchang block for the daily-reading user message."""
    tithi_line = f"- Tithi: {panchang.tithi_paksha} {panchang.tithi_name}"
    if panchang.tithi_significance:
        tithi_line += f" — {panchang.tithi_significance}"
    return (
        "Today's Panchang (computed for the seeker's natal birthplace):\n"
        f"- Day: {panchang.weekday}, ruled by {panchang.day_lord}\n"
        f"{tithi_line}\n"
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
# Classical use: marriage/dharma readings, and confirming raja yogas —
# a yoga must survive in D-9 to fully manifest per Parashara.
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
    planet is enough for classical yoga-confirmation reading.
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
# Kaal Sarp Dosh — for the standalone /kaal-sarp-check tool (Issue #111)
# ---------------------------------------------------------------------------
#
# Classical rule: when ALL 7 non-shadow planets (Sun, Moon, Mars, Mercury,
# Jupiter, Venus, Saturn) fall on ONE SIDE of the Rahu-Ketu axis, the chart
# has Kaal Sarp Dosha. The Rahu-Ketu axis divides the zodiac into two
# 180° semicircles; ALL 7 planets in one semicircle = KSD.
#
# 12 named types based on which house pair holds the Rahu-Ketu axis:
#   Anant     — Rahu in 1st, Ketu in 7th
#   Kulik     — Rahu in 2nd, Ketu in 8th
#   Vasuki    — Rahu in 3rd, Ketu in 9th
#   Shankhpal — Rahu in 4th, Ketu in 10th
#   Padma     — Rahu in 5th, Ketu in 11th
#   Mahapadma — Rahu in 6th, Ketu in 12th
#   Takshak   — Rahu in 7th, Ketu in 1st
#   Karkotak  — Rahu in 8th, Ketu in 2nd
#   Shankchur — Rahu in 9th, Ketu in 3rd
#   Ghatak    — Rahu in 10th, Ketu in 4th
#   Vishdhar  — Rahu in 11th, Ketu in 5th
#   Sheshnag  — Rahu in 12th, Ketu in 6th
#
# Partial KSD: if 6 of 7 planets are on one side and 1 straddles, some
# schools call it Partial (Anshik). We treat this as a soft flag.

_KAAL_SARP_TYPES: dict[int, tuple[str, str]] = {
    1:  ("Anant",     "Ambition-driven, restless; identity themes; often forceful early-life"),
    2:  ("Kulik",     "Wealth-family friction, speech guarded; hidden financial pressures"),
    3:  ("Vasuki",    "Sibling tension, courage tested, effort-heavy chapters; media/writing pull"),
    4:  ("Shankhpal", "Home/mother themes weight-bearing; property fluctuations; emotional roots strained"),
    5:  ("Padma",     "Progeny challenges, love-marriage complications, creative outbursts"),
    6:  ("Mahapadma", "Health/service life demanding; enemy patterns; disciplined recovery"),
    7:  ("Takshak",   "Partnership instability; foreign spouse or unusual union pattern"),
    8:  ("Karkotak",  "Sudden life transformations; in-law dynamics complex; hidden gains + losses"),
    9:  ("Shankchur", "Dharmic wanderings; father-relationship distant; foreign settling common"),
    10: ("Ghatak",    "Career elevated dramatically OR delayed; authority/reputation swings"),
    11: ("Vishdhar",  "Elder sibling / large-network gains + karmic tests; group-based work"),
    12: ("Sheshnag",  "Foreign lands, spiritual retreat, expenditure themes; second-half prominence"),
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
    """Detect Kaal Sarp Dosh — strict binary per classical Vedic tradition.

    Classical sources (Brihat Parashara Hora Shastra, Phaladeepika, Saravali)
    treat Kaal Sarp Dosh as BINARY: all 7 non-shadow planets fall on one
    semicircle of the Rahu-Ketu axis, or they don't. No "partial" concept
    exists in the classical texts.

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
