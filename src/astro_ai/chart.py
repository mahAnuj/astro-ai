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
    ("taurus", "vrishabha", "vrish"),
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

    # Benefic conjunction / aspect — Jupiter is the primary classical cancellation
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

    # Venus with Mars — relationship karaka channels Martian energy
    if mars.house == venus.house:
        rules.append(ManglikRule(
            slug="venus_with_mars",
            description="Venus conjunct Mars (relationship karaka channels Martian energy)",
            effect="mitigates",
            source="Classical compatibility practice",
        ))

    # Combustion — Mars within 6° of Sun in the same rashi
    if mars.rashi == sun.rashi and abs(mars.longitude - sun.longitude) < 6.0:
        rules.append(ManglikRule(
            slug="mars_combust",
            description=f"Mars combust (within {abs(mars.longitude - sun.longitude):.1f}° of Sun)",
            effect="cancels",
            source="Classical matching practice",
        ))

    return tuple(rules)


def compute_manglik_details(chart: Chart) -> ManglikDetails:
    """Identify all Manglik-qualifying Mars positions + apply classical cancellation rules.

    Two-step model: first detect the raw mathematical Manglik pattern, then
    overlay cancellation/mitigation rules to compute an `effective_status`
    that the UI and LLM can act on without re-deriving classical doctrine.
    """
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


def format_yogas_for_prompt(yogas: tuple[YogaResult, ...]) -> str:
    """Tiny LLM hint listing detected yogas — only emitted when at least one fires.

    Stays ~50-300 tokens depending on how many yogas hit. Each line is just
    yoga name + effect; classical sources are deliberately omitted so the
    LLM can't echo them back as user-facing "per Rao Ch.11" jargon. Sources
    live in the structured UI panel, not in the LLM prose path.
    """
    if not yogas:
        return ""
    lines = [
        "--- YOGAS DETECTED ---",
        "Classical planetary combinations active in this chart. Mention them by NAME",
        "in the relevant section and paraphrase the effect in plain words. Do NOT name",
        "classical texts, chapters, or sanskrit shastra in your prose — those live in",
        "the UI panel separately.",
    ]
    for y in yogas:
        lines.append(f"  • {y.name}: {y.effect}")
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
    """

    is_active: bool
    phase: str | None                  # "rising" | "peak" | "setting"
    saturn_house_from_moon: int        # 1..12
    overall_start: date_ | None
    overall_end: date_ | None
    phase_end: date_ | None


def compute_sade_sati_details(chart: Chart, when: datetime | None = None) -> SadeSatiDetails:
    """Sade Sati state + start/end dates when active."""
    flags = compute_vedic_flags(chart, when)
    if not flags.sade_sati:
        return SadeSatiDetails(
            is_active=False, phase=None,
            saturn_house_from_moon=flags.saturn_house_from_natal_moon,
            overall_start=None, overall_end=None, phase_end=None,
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
    )


def _saturn_house_from_natal_moon(moon_idx: int, at: datetime) -> int:
    """Compute Saturn's house (from natal Moon) at moment `at` — single swisseph call."""
    jd = swe.julday(at.year, at.month, at.day, at.hour + at.minute / 60.0)
    pos, _ = swe.calc_ut(jd, swe.SATURN, swe.FLG_SIDEREAL)
    sign_idx = int(float(pos[0]) // 30)
    return ((sign_idx - moon_idx) % 12) + 1


def _saturn_house_change_forward(moon_idx: int, start: datetime, target_house: int) -> date_:
    """Find the last day Saturn is still in `target_house` (going forward from start).

    Weekly stride + daily bisection. Bounded at 3 years (Saturn changes sign
    every ~2.5 years so a single phase never exceeds that).
    """
    cursor = start
    step = timedelta(days=7)
    for _ in range(52 * 3):
        cursor += step
        if _saturn_house_from_natal_moon(moon_idx, cursor) != target_house:
            # Refine: bracket between cursor-step and cursor, find last day in target.
            lo, hi = cursor - step, cursor
            for _ in range(8):
                mid = lo + (hi - lo) / 2
                if _saturn_house_from_natal_moon(moon_idx, mid) == target_house:
                    lo = mid
                else:
                    hi = mid
            return lo.date()
    return cursor.date()


def _saturn_house_change_backward(moon_idx: int, start: datetime, target_house: int) -> date_:
    """First day going BACK that Saturn was still in `target_house`. Mirror of forward."""
    cursor = start
    step = timedelta(days=7)
    for _ in range(52 * 3):
        cursor -= step
        if _saturn_house_from_natal_moon(moon_idx, cursor) != target_house:
            lo, hi = cursor, cursor + step  # lo is OUT of target, hi is IN
            for _ in range(8):
                mid = lo + (hi - lo) / 2
                if _saturn_house_from_natal_moon(moon_idx, mid) == target_house:
                    hi = mid
                else:
                    lo = mid
            return hi.date()
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


def compute_life_chapters(natal: Chart, until_age: float = 80.0) -> list[LifeChapter]:
    """Return all Mahadasha periods from birth up to `until_age`, in age-window form.

    Used by the natal LLM prompt to ground the 'Life Stages' section in real
    dasha timing — the LLM phrases the chapters in life-experience language
    (the lord name is NOT mentioned in the output, only used for reasoning).
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
    chapters: list[LifeChapter] = []

    cursor = birth_date
    cursor_end = cursor + timedelta(days=first_remaining_years * _DAYS_PER_YEAR)
    chapters.append(LifeChapter(
        lord=first_lord,
        start_age=(cursor - birth_date).days / _DAYS_PER_YEAR,
        end_age=(cursor_end - birth_date).days / _DAYS_PER_YEAR,
    ))
    cursor = cursor_end

    start_idx = _VIM_ORDER.index(first_lord)
    i = 1
    while True:
        lord = _VIM_ORDER[(start_idx + i) % 9]
        yrs = _VIM_YEARS[lord]
        cursor_end = cursor + timedelta(days=yrs * _DAYS_PER_YEAR)
        end_age = (cursor_end - birth_date).days / _DAYS_PER_YEAR
        chapters.append(LifeChapter(
            lord=lord,
            start_age=(cursor - birth_date).days / _DAYS_PER_YEAR,
            end_age=end_age,
        ))
        cursor = cursor_end
        i += 1
        if end_age >= until_age:
            break
    return chapters


def format_life_chapters_for_prompt(chapters: list[LifeChapter]) -> str:
    """Plain-English Mahadasha sequence for the natal LLM (lord names included
    because the LLM uses them to reason; instructions tell it to NOT name them
    in output)."""
    lines = ["Vimshottari Mahadasha sequence (lord per age range — for reasoning only, do NOT name planets in output):"]
    for c in chapters:
        lines.append(f"- Age {c.start_age:.1f} to {c.end_age:.1f}: {c.lord}")
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
