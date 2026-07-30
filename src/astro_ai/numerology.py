"""Numerology calculator — Chaldean + Pythagorean systems (Issue #112).

Positioned as COMPLEMENTARY to Vedic astrology, not a replacement. Numerology
reads name + birth date; Vedic reads the full birth chart. Two lenses on
the same person. When they agree, the signal is stronger.

Design:
- Pure math + fixed interpretation strings. NO LLM call.
- Two systems: Chaldean (traditional, more accurate per numerology tradition)
  + Pythagorean (Western simpler mapping).
- 5 numbers computed:
    Life Path       — from full birth date (reduced to 1-9 or master 11/22/33)
    Destiny         — from all letters of full name
    Soul Urge       — from vowels of full name
    Personality     — from consonants of full name
    Name Number     — Chaldean-sum of full name (used for "lucky name" analysis)
- Interpretation strings hand-written honestly — no scam claims, no lucky-name
  upsell, no "wear this gem for your number" pitch.

Editorial:
- Always defer back to /kundli for depth
- Never predict specific outcomes
- Never recommend name changes based on numerology
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ─── Chaldean letter values ───────────────────────────────────────────
# Chaldean numerology (older system, aligned with Babylonian/Kabbalistic
# tradition) — DOES NOT use 9 as a letter value; 9 is sacred/divine.
_CHALDEAN = {
    "A": 1, "I": 1, "J": 1, "Q": 1, "Y": 1,
    "B": 2, "K": 2, "R": 2,
    "C": 3, "G": 3, "L": 3, "S": 3,
    "D": 4, "M": 4, "T": 4,
    "E": 5, "H": 5, "N": 5, "X": 5,
    "U": 6, "V": 6, "W": 6,
    "O": 7, "Z": 7,
    "F": 8, "P": 8,
}

# ─── Pythagorean letter values ────────────────────────────────────────
# Pythagorean (Western modern) — A=1, B=2, ..., Z=26, then reduced.
_PYTHAGOREAN = {chr(ord("A") + i): ((i % 9) + 1) for i in range(26)}

_VOWELS = set("AEIOU")


@dataclass(frozen=True)
class NumerologyRemedy:
    """Per-number remedy recommendations from Johari's Vedic-integrated system."""
    planet: str                # Sun, Moon, Jupiter, Rahu, Mercury, Venus, Ketu, Saturn, Mars
    planet_sanskrit: str
    colors: str                # comma-separated favorable colors
    gemstone: str              # e.g. "Ruby (Manikya)"
    gemstone_caveat: str       # chart-consultation warning
    metal: str
    day: str                   # Sun/Mon/Tue... best day for practice
    direction: str             # East/West/NW... best direction to face
    deity: str                 # Vishnu/Lakshmi/Shani-dev...
    mantra: str                # bija mantra transliteration
    dosha: str                 # Vata/Pitta/Kapha dominant
    fasting_day: str           # weekday for fast + prep notes


@dataclass(frozen=True)
class NumerologyReading:
    """One person's numerology profile."""
    name: str
    birth_date: str            # YYYY-MM-DD
    system: str                # "chaldean" | "pythagorean"

    # 5 Core Numbers (Kumar terminology) + name-number legacy alias
    life_path: int             # Destiny/Bhagyank — sum all DOB digits, reduce (1-9 or 11/22/33)
    birthday: int              # Psychic/Mulank — birth day-of-month reduced
    destiny: int               # Expression — sum Chaldean values of full name
    soul_urge: int             # Heart Desire — sum of vowels only
    personality: int           # Personality — sum of consonants only
    name_number: int           # Legacy alias — same as destiny; kept for backward compat

    life_path_meaning: str
    destiny_meaning: str
    soul_urge_meaning: str
    personality_meaning: str
    name_number_meaning: str
    birthday_meaning: str

    # Vedic remedies per Life Path (planet-number correspondences)
    life_path_remedy: NumerologyRemedy | None = None

    # Personal Year — current-year vibrational number (Kumar)
    personal_year: int = 0
    personal_year_theme: str = ""
    personal_year_target: int = 0    # the year this was computed for (default: current)

    # Karmic Debt flags per Kumar Ch.1 — presence of 13/14/16/19 in any
    # intermediate Core Number calculation is a soul-work indicator.
    karmic_debt_numbers: tuple[int, ...] = ()

    # Compound number of the name (before reduction) — Johari §5
    name_compound: int = 0
    name_compound_meaning: str = ""


# ─── Interpretation strings ──────────────────────────────────────────
# Hand-written honest interpretations. NEVER predict specific outcomes.

_LIFE_PATH = {
    1: "The Independent — leadership, self-reliance, pioneering spirit. Life path prompts you to build something original rather than follow. Watch out for isolation and ego.",
    2: "The Diplomat — cooperation, sensitivity, partnership-orientation. Path unfolds through relationships and mediating between others. Guard against people-pleasing and indecision.",
    3: "The Creator — expression, communication, joy. Path involves finding and using your creative voice. Watch for scattered energy and superficiality.",
    4: "The Builder — stability, discipline, method. Path is about building lasting structures — career, home, systems. Guard against rigidity.",
    5: "The Freedom-Seeker — adaptability, movement, sensory experience. Path involves change, travel, and personal freedom. Watch for restlessness.",
    6: "The Nurturer — responsibility, family, service. Path is about caring for others and creating harmony. Guard against martyrdom.",
    7: "The Seeker — introspection, wisdom, spirituality. Path involves deep thinking and often solitary study. Watch for over-isolation.",
    8: "The Achiever — power, material success, executive strength. Path is about building material abundance and influence. Guard against greed and burnout.",
    9: "The Humanitarian — compassion, completion, universal love. Path involves serving humanity at scale. Watch for savior complex and emotional exhaustion.",
    11: "The Visionary (Master 11) — spiritual insight, inspiration, high sensitivity. Elevated 2 — path involves leading through vision. Requires strong nervous system.",
    22: "The Master Builder (Master 22) — capable of building lasting structures that serve humanity. Elevated 4 — path is about grand-scale material contribution. Demanding but rewarding.",
    33: "The Master Teacher (Master 33) — enlightened service, healing. Elevated 6 — rare number, path involves guiding others toward higher understanding.",
}

_DESTINY = {
    1: "Destined to lead — original ventures, entrepreneurship, being first at something.",
    2: "Destined for partnership work — mediation, diplomacy, supporting roles that hold things together.",
    3: "Destined to communicate — writing, speaking, teaching, art. Your voice matters.",
    4: "Destined to build — real estate, engineering, systems, long-term structures.",
    5: "Destined for variety — sales, travel, marketing, roles requiring adaptability.",
    6: "Destined to care — teaching, medicine, family businesses, community roles.",
    7: "Destined for depth — research, spiritual work, specialised expertise, deep analysis.",
    8: "Destined for material achievement — business, finance, executive leadership.",
    9: "Destined for humanitarian work — non-profits, healing arts, global-impact roles.",
    11: "Destined for visionary work — psychic/spiritual leadership, inspirational teaching.",
    22: "Destined for large-scale building — architecture, foundational institutions, movements.",
    33: "Destined for enlightened service — spiritual teaching, deep healing, exceptional care.",
}

_SOUL_URGE = {
    1: "Inner drive: to lead, to be recognised as first, to originate.",
    2: "Inner drive: to be in loving relationship, to be needed.",
    3: "Inner drive: to express creatively, to be heard, to bring joy.",
    4: "Inner drive: to build something lasting, to be dependable.",
    5: "Inner drive: freedom, novelty, experiences that don't repeat.",
    6: "Inner drive: to nurture family, to be the caretaker, to create harmony.",
    7: "Inner drive: to understand deeply, to seek truth, to be alone with thoughts.",
    8: "Inner drive: material achievement, power, influence, financial security.",
    9: "Inner drive: to help humanity, to make a difference at scale, to serve.",
    11: "Inner drive: spiritual truth, illumination, inspirational connection.",
    22: "Inner drive: to build something the world needs at architectural scale.",
    33: "Inner drive: to be a healing presence for those who suffer.",
}

_PERSONALITY = {
    1: "Others see you as: confident, independent, sometimes intimidating.",
    2: "Others see you as: gentle, cooperative, easy to be with.",
    3: "Others see you as: expressive, playful, socially bright.",
    4: "Others see you as: reliable, hard-working, sometimes serious.",
    5: "Others see you as: adventurous, unpredictable, exciting.",
    6: "Others see you as: nurturing, family-oriented, responsible.",
    7: "Others see you as: mysterious, thoughtful, hard to know.",
    8: "Others see you as: successful, ambitious, in-charge.",
    9: "Others see you as: kind, wise, older than your years.",
    11: "Others see you as: unusual, insightful, spiritually attuned.",
    22: "Others see you as: capable of great things, calm under pressure.",
    33: "Others see you as: healing presence, gentle wisdom.",
}

_NAME_NUMBER = {
    1: "Name vibration favours leadership and original ventures.",
    2: "Name vibration favours partnerships and cooperative work.",
    3: "Name vibration favours creative expression.",
    4: "Name vibration favours stability and long-term building.",
    5: "Name vibration favours variety and travel-related pursuits.",
    6: "Name vibration favours family and service.",
    7: "Name vibration favours research and inner work.",
    8: "Name vibration favours business and material achievement.",
    9: "Name vibration favours humanitarian pursuits.",
    11: "Master vibration — spiritual leadership potential.",
    22: "Master vibration — building at scale.",
    33: "Master vibration — enlightened service.",
}


# ─── Birthday / Psychic Number meanings (Johari's Mulank) ────────────
# Reduce the day-of-birth to 1-9. This is how the native sees themselves —
# the number of ambition, desire, and self-perception. Dominant to age 35-40,
# then Life Path (Destiny/Bhagyank) takes over per Johari §2.1.
_BIRTHDAY_MEANING = {
    1: "Self-image: pioneer, initiator. You see yourself as someone who should lead, originate, be first. Ambitions run high; freedom and recognition matter.",
    2: "Self-image: harmoniser, partner. You see yourself as someone who works best in cooperation, mediating between others. Sensitivity is your strength — and your risk.",
    3: "Self-image: creator, teacher. You see yourself as an expressive, communicative, wisdom-carrying person. Sometimes preachy; often generous with time and counsel.",
    4: "Self-image: reformer, non-conformist. You see yourself as someone who breaks convention when needed. Watch for isolation from over-independence.",
    5: "Self-image: quick-thinker, communicator. You see yourself as versatile, adaptive, intellectually restless. Anxiety about missing out is a shadow to guard.",
    6: "Self-image: nurturer, artist. You see yourself as someone who creates beauty and holds people together. Over-giving is the risk.",
    7: "Self-image: seeker, mystic. You see yourself as someone who looks past surfaces — spiritually curious, intuitively wired. Grounding is a lifelong practice.",
    8: "Self-image: builder-through-struggle. You see yourself as someone who earns everything the hard way. Late-blooming success is your typical pattern.",
    9: "Self-image: warrior, humanitarian. You see yourself as a fighter for justice — competitive, perfectionist, fiery. Anger management matters.",
    11: "Master 11 self-image: intuitive leader. Extra sensitivity + spiritual openness; can become a teacher or channel. Nervous-system care is essential.",
    22: "Master 22 self-image: architect at scale. Not casual big — genuinely capable of building lasting institutions. Requires discipline to match the potential.",
    33: "Master 33 self-image: healer-teacher. Rare vibration; the drive is service to those suffering. Emotional exhaustion is the shadow.",
}


# ─── Per-number Vedic remedies (Johari's planet-number correspondences) ─
# From knowledge/numerology.md §3.3 + §4. Each number's ruling planet
# gives its remedies: gemstone, color, deity, mantra, day, direction,
# dosha. Users see this on the Life-Path result and can act on it.
# Gemstone caveats mirror those on the site's remedy articles.
_REMEDIES: dict[int, NumerologyRemedy] = {
    1: NumerologyRemedy(
        planet="Sun", planet_sanskrit="Surya",
        colors="Orange, yellow, gold, copper",
        gemstone="Ruby (Manikya)",
        gemstone_caveat="Chart consultation required. Women traditionally use garnet substitute. Avoid if Sun is functional malefic for your Lagna.",
        metal="Gold", day="Sunday", direction="East",
        deity="Surya (Sun-god)",
        mantra="Om Hraam Hreem Hraum Sah Suryaya Namah",
        dosha="Pitta dominant",
        fasting_day="Sunday — single meal salt-free before sunset (traditional: chickpea bread + milk with dates + cardamom)",
    ),
    2: NumerologyRemedy(
        planet="Moon", planet_sanskrit="Chandra",
        colors="White, cream, light green",
        gemstone="Pearl (Moti)",
        gemstone_caveat="Avoid for Scorpio Ascendant (Moon debilitates there). For other ascendants requires chart consultation — an afflicted Moon can be further destabilised.",
        metal="Silver", day="Monday", direction="North-west",
        deity="Shiva (or Parvati)",
        mantra="Om Shraam Shreem Shraum Sah Chandraya Namah",
        dosha="Kapha dominant",
        fasting_day="Monday — traditional pradosh vrat, water and fruits during day",
    ),
    3: NumerologyRemedy(
        planet="Jupiter", planet_sanskrit="Guru / Brihaspati",
        colors="Yellow, gold, orange",
        gemstone="Yellow Sapphire (Pukhraj)",
        gemstone_caveat="Avoid Capricorn Ascendant (Jupiter debilitates there and rules dusthanas). See /learn/jupiter-remedies for full ascendant guidance.",
        metal="Gold", day="Thursday", direction="North-east",
        deity="Vishnu (blue-skinned, four-armed)",
        mantra="Om Gram Greem Graum Sah Gurave Namah",
        dosha="Vata mixed Pitta",
        fasting_day="Thursday — salt-free chickpeas + jaggery, single meal",
    ),
    4: NumerologyRemedy(
        planet="Rahu", planet_sanskrit="Rahu (North Node)",
        colors="Grey, khaki, electric blue",
        gemstone="Hessonite Garnet (Gomed)",
        gemstone_caveat="One of the most volatile gemstones — chart consultation MANDATORY. Never wear without verifying Rahu is a functional benefic.",
        metal="Panch-dhatu (5-metal alloy)", day="Saturday", direction="South-west",
        deity="Ganesha (golden throne, obstacle remover)",
        mantra="Om Bhraam Bhreem Bhraum Sah Rahave Namah",
        dosha="Vata dominant",
        fasting_day="Saturday — partial fast; feed unusual/marginalised people (Rahu's karaka)",
    ),
    5: NumerologyRemedy(
        planet="Mercury", planet_sanskrit="Budha",
        colors="Light green, turquoise, silvery-grey",
        gemstone="Emerald (Panna)",
        gemstone_caveat="Avoid if natal Mercury is in Pisces (debilitation). Chart consultation before wearing.",
        metal="Silver / Gold", day="Wednesday", direction="North",
        deity="Mahalakshmi (pink lotus)",
        mantra="Om Bram Breem Braum Sah Budhaya Namah",
        dosha="Vata-Pitta mixed",
        fasting_day="Wednesday — moong daal khichdi at sunset",
    ),
    6: NumerologyRemedy(
        planet="Venus", planet_sanskrit="Shukra",
        colors="White, pink, pale blue, all light shades",
        gemstone="Diamond (Heera) or White Sapphire",
        gemstone_caveat="Edge case: if natal Venus is in Virgo (debilitated) for a Virgo lagna, Diamond may amplify weakness — consult before wearing.",
        metal="Silver / Platinum", day="Friday", direction="South-east",
        deity="Lakshmi (also Parvati)",
        mantra="Om Dram Dreem Draum Sah Shukraya Namah",
        dosha="Kapha with Pitta",
        fasting_day="Friday — sattvic food, offer white flowers to Lakshmi",
    ),
    7: NumerologyRemedy(
        planet="Ketu", planet_sanskrit="Ketu (South Node)",
        colors="Iridescent green/blue, mother-of-pearl, ash",
        gemstone="Cat's Eye (Lehsunia)",
        gemstone_caveat="Volatile — chart consultation mandatory. Ketu's afflictions are subtle; wrong gemstone amplifies confusion rather than clarity.",
        metal="Panch-dhatu", day="Tuesday (some traditions Sunday)", direction="South / South-west",
        deity="Nrisimha (Narasimha, lion-headed Vishnu avatar)",
        mantra="Om Sraam Sreem Sraum Sah Ketave Namah",
        dosha="Vata dominant",
        fasting_day="Tuesday partial fast; Sankashti Chaturthi Ganesh vrat (monthly)",
    ),
    8: NumerologyRemedy(
        planet="Saturn", planet_sanskrit="Shani",
        colors="Black, dark blue, dark purple, deep grey",
        gemstone="Blue Sapphire (Neelam)",
        gemstone_caveat="MOST DANGEROUS gemstone in Jyotish. Absolutely avoid for Aries Ascendant (Saturn debilitates there). Traditional 3-day test wear required even for compatible ascendants. Never wear casually.",
        metal="Panch-dhatu", day="Saturday", direction="West",
        deity="Shani-dev",
        mantra="Om Praam Preem Praum Sah Shanaishcharaya Namah",
        dosha="Vata dominant",
        fasting_day="Saturday — sunset-only meal; moong-urad khichdi with rock salt",
    ),
    9: NumerologyRemedy(
        planet="Mars", planet_sanskrit="Mangal",
        colors="Red, coral pink, deep pink",
        gemstone="Red Coral (Moonga)",
        gemstone_caveat="Avoid Cancer Ascendant (Mars debilitates there). Anger-prone natives should observe behavioural remedies first before gemstone.",
        metal="Copper", day="Tuesday", direction="South",
        deity="Hanuman (or Kartikeya / Subrahmanya)",
        mantra="Om Kram Kreem Kraum Sah Bhaumaya Namah",
        dosha="Pitta dominant",
        fasting_day="Tuesday — Hanuman Chalisa 5 times, red masoor daal (folk) or toor daal (classical grain)",
    ),
    # Master numbers reduce to their base for remedy purposes per Johari
    11: None,  # falls back to 2
    22: None,  # falls back to 4
    33: None,  # falls back to 6
}


def _get_remedy(n: int) -> NumerologyRemedy | None:
    """Return remedy for number n. Master numbers fall back to base."""
    if n in (11, 22, 33):
        n = {11: 2, 22: 4, 33: 6}[n]
    return _REMEDIES.get(n)


# ─── Compound numbers 10-31 (Johari §5) ──────────────────────────────
# Kumar (Ch.1) explicitly calls out 13, 14, 16, 19 as Karmic Debt Numbers.
# Johari treats each compound number as having its own vibration in
# addition to the reduced base. Sample of most-cited:
_COMPOUND_NUMBER_MEANING: dict[int, str] = {
    10: "Wheel of Fortune — honor, faith, self-confidence; rise + fall + rise cycle.",
    11: "Silent lion (master) — trials by treachery, hidden dangers; requires spiritual discipline to convert to fortune.",
    12: "The Sacrifice — often victim of others' schemes; use suffering as teacher.",
    13: "KARMIC DEBT — Warning against selfishness/misuse of power. Not 'unlucky' per se; requires ethical vigilance. Meditate on gemstone; practise ahimsa.",
    14: "KARMIC DEBT — Warning against over-indulgence in freedom. Balance is the teacher; extreme mercurial swings.",
    15: "The Magician — powerful for material gain but slightly self-serving; occult undertones.",
    16: "KARMIC DEBT — Rise-and-fall cycle (Sun-Venus conflict). Watch for accidents from height/water/travel. 'Fallen tower' vibration.",
    17: "Star of the Magi (Sun+Ketu) — real spiritual understanding through inner conflict; leaves mark on history after death.",
    18: "Materialism destroys spiritual side — beware of quarrels and sudden loss.",
    19: "KARMIC DEBT — Sun and success but risk of self-glorification. Called 'Prince of Heaven' if handled well.",
    20: "The Judgement — awakening, powerful upheaval; call to greater purpose.",
    21: "Universe / Crown of the Magi — universally auspicious for creative-life natives.",
    22: "Master builder-like — scale and karmic weight; potent for architects, reformers, movement-organisers.",
    23: "The Royal Star of the Lion — auspicious for success in high positions.",
    24: "Fortune-loved — great friendships, generous partners, likely to marry above station.",
    25: "Moon+Mercury tension — artistic but late-blooming; self-condemning tendency; avoid risky ventures.",
    26: "Warning of severe reversal from partnerships. Marriage-partner selection critical (avoid 4/8/9; select 1/3/6).",
    27: "The Sceptre — power through wisdom; auspicious for command roles.",
    28: "Rise-and-loss cycle. Great potential but loses through others' promises; caution with contracts.",
    29: "Trials by loved ones; deception; test of faith through relationships.",
    30: "The Contemplative — thoughtful; success comes late; strong intellectual/spiritual gifts.",
    31: "Self-contained genius; often solitary; unusual creative output.",
}
_KARMIC_DEBT_NUMBERS = {13, 14, 16, 19}


def _get_compound_meaning(n: int) -> str:
    """Return compound number meaning if n is in the tracked range."""
    return _COMPOUND_NUMBER_MEANING.get(n, "")


# ─── Personal Year (Kumar Ch.1) ──────────────────────────────────────
# Personal Year Number = birth-month + birth-day + Universal Year (all
# digits of the current/target year, reduced). Reveals the theme of that
# year for the person. Cycles 1-9 (master numbers preserved).
_PERSONAL_YEAR_THEME = {
    1: "Year 1 — Beginnings. New ventures, new self-image, planting seeds. Slow-start progress; year to sow.",
    2: "Year 2 — Partnership. Cooperation, relationships, patience, waiting for what was sown to sprout.",
    3: "Year 3 — Expression. Creative surge, social opportunities, communication expansion; harvest of self-expression.",
    4: "Year 4 — Foundation. Hard work, building structures, discipline; sometimes frustrating but necessary.",
    5: "Year 5 — Change. Movement, travel, new experiences; the year not to hold on tightly.",
    6: "Year 6 — Responsibility. Family, service, home matters take centre stage; nurturing year.",
    7: "Year 7 — Reflection. Solitude, study, spiritual work; not the year to push external goals.",
    8: "Year 8 — Harvest. Material achievement, business success, recognition; effort of prior years pays.",
    9: "Year 9 — Completion. Endings, letting go, humanitarian work; clearing space for the next 1-year cycle.",
    11: "Year 11 — Illumination (master). Spiritual insight peaks; inspirational leadership possible.",
    22: "Year 22 — Master builder year. Rare — capable of building lasting institutions this year.",
    33: "Year 33 — Master teacher year. Service to those suffering; deep healing capacity.",
}


def _personal_year(birth_date: str, target_year: int) -> int:
    """Compute Personal Year Number for a given target year (Kumar Ch.1).

    Formula: (birth month digits sum) + (birth day digits sum) +
             (target year digits sum), then reduce.
    """
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
    if not m:
        return 0
    _, mo, d = m.groups()
    month_sum = sum(int(x) for x in mo)
    day_sum = sum(int(x) for x in d)
    year_sum = sum(int(x) for x in str(target_year))
    return _reduce(month_sum + day_sum + year_sum)


def _karmic_debt_flags(birth_date: str, name: str, table: dict) -> tuple[int, ...]:
    """Detect Karmic Debt Numbers per Kumar Ch.1.

    Karmic Debt = presence of 13, 14, 16, or 19 in any intermediate
    Core Number sum (before final reduction).
    """
    flags: set[int] = set()
    # Intermediate sums during Life Path computation
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
    if m:
        y, mo, d = m.groups()
        for chunk in (y, mo, d):
            s = sum(int(x) for x in chunk)
            if s in _KARMIC_DEBT_NUMBERS:
                flags.add(s)
        total_raw = int(y[0]) + int(y[1]) + int(y[2]) + int(y[3]) + int(mo) + int(d)
        if total_raw in _KARMIC_DEBT_NUMBERS:
            flags.add(total_raw)
    # Intermediate name sum
    letters = _clean_name(name)
    name_sum_raw = sum(table.get(c, 0) for c in letters)
    if name_sum_raw in _KARMIC_DEBT_NUMBERS:
        flags.add(name_sum_raw)
    # Vowels-only raw
    vowels = "".join(c for c in letters if c in _VOWELS)
    v_sum = sum(table.get(c, 0) for c in vowels)
    if v_sum in _KARMIC_DEBT_NUMBERS:
        flags.add(v_sum)
    return tuple(sorted(flags))


def _birthday_number(birth_date: str) -> int:
    """Reduce day-of-month to 1-9 (Kumar Birthday / Johari Psychic / Mulank)."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
    if not m:
        return 0
    _, _, d = m.groups()
    return _reduce(int(d))


def _clean_name(name: str) -> str:
    """Uppercase A-Z only, spaces + hyphens stripped.

    Unicode-normalize first (NFD form) so accented letters decompose to
    base+combining and the combining marks get filtered out — 'José' becomes
    'JOSE', 'Śrī' becomes 'SRI'. Without this step, accented characters would
    be silently dropped ('José' → 'JOS') and the numerology of Indian /
    Latin-alphabet names with diacritics would be wrong.
    """
    import unicodedata
    normalized = unicodedata.normalize("NFD", name or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z]", "", ascii_only.upper())


def _reduce(n: int) -> int:
    """Reduce to single digit (1-9) preserving master numbers 11, 22, 33."""
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n


def _sum_letters(letters: str, table: dict[str, int]) -> int:
    """Sum letter values, then reduce."""
    total = sum(table.get(c, 0) for c in letters)
    return _reduce(total) if total else 0


def _life_path(birth_date: str) -> int:
    """Life Path = reduced sum of all digits in YYYY-MM-DD."""
    digits = re.sub(r"[^0-9]", "", birth_date or "")
    if not digits:
        return 0
    # Classical approach: reduce day, month, year separately, then sum.
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
    if m:
        y, mo, d = m.groups()
        return _reduce(_reduce(int(y)) + _reduce(int(mo)) + _reduce(int(d)))
    # Fallback: sum all digits
    return _reduce(sum(int(d) for d in digits))


def compute(name: str, birth_date: str, system: str = "chaldean",
            target_year: int | None = None) -> NumerologyReading:
    """Compute the full numerology reading for a person.

    Extended to include Kumar's Karmic Debt detection, Personal Year
    (target_year defaults to current year), and Johari's per-number
    Vedic remedies attached to the Life Path number.
    """
    from datetime import date as _date
    system = system.lower()
    table = _CHALDEAN if system != "pythagorean" else _PYTHAGOREAN

    letters = _clean_name(name)
    vowels = "".join(c for c in letters if c in _VOWELS)
    consonants = "".join(c for c in letters if c not in _VOWELS)

    lp = _life_path(birth_date)
    bd = _birthday_number(birth_date)
    d = _sum_letters(letters, table)
    su = _sum_letters(vowels, table)
    p = _sum_letters(consonants, table)
    nn = _sum_letters(letters, _CHALDEAN)  # Name number is always Chaldean by tradition

    # Personal Year for the target year (default: current year)
    ty = target_year if target_year is not None else _date.today().year
    py = _personal_year(birth_date, ty)

    # Karmic Debt flags across all intermediate sums
    karmic = _karmic_debt_flags(birth_date, name, table)

    # Compound name number (before reduction) — Johari §5
    name_raw = sum(_CHALDEAN.get(c, 0) for c in letters)
    name_compound = name_raw if 10 <= name_raw <= 52 else 0
    name_compound_meaning = _get_compound_meaning(name_compound)

    def _get(mapping: dict, n: int) -> str:
        return mapping.get(n, "Number outside standard interpretation range.")

    return NumerologyReading(
        name=name.strip() or "Unnamed",
        birth_date=birth_date,
        system=system,
        life_path=lp,
        birthday=bd,
        destiny=d,
        soul_urge=su,
        personality=p,
        name_number=nn,
        life_path_meaning=_get(_LIFE_PATH, lp),
        destiny_meaning=_get(_DESTINY, d),
        soul_urge_meaning=_get(_SOUL_URGE, su),
        personality_meaning=_get(_PERSONALITY, p),
        name_number_meaning=_get(_NAME_NUMBER, nn),
        birthday_meaning=_get(_BIRTHDAY_MEANING, bd),
        life_path_remedy=_get_remedy(lp),
        personal_year=py,
        personal_year_theme=_PERSONAL_YEAR_THEME.get(py, ""),
        personal_year_target=ty,
        karmic_debt_numbers=karmic,
        name_compound=name_compound,
        name_compound_meaning=name_compound_meaning,
    )
