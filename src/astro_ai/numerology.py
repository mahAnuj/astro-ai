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
class NumerologyReading:
    """One person's numerology profile."""
    name: str
    birth_date: str            # YYYY-MM-DD
    system: str                # "chaldean" | "pythagorean"

    life_path: int             # 1-9 or 11/22/33 (master)
    destiny: int               # 1-9 or 11/22/33
    soul_urge: int             # 1-9 or 11/22/33
    personality: int           # 1-9 or 11/22/33
    name_number: int           # 1-9 or 11/22/33

    life_path_meaning: str
    destiny_meaning: str
    soul_urge_meaning: str
    personality_meaning: str
    name_number_meaning: str


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


def _clean_name(name: str) -> str:
    """Uppercase A-Z only, spaces + hyphens stripped."""
    return re.sub(r"[^A-Z]", "", (name or "").upper())


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


def compute(name: str, birth_date: str, system: str = "chaldean") -> NumerologyReading:
    """Compute the full 5-number numerology reading for a person."""
    system = system.lower()
    table = _CHALDEAN if system != "pythagorean" else _PYTHAGOREAN

    letters = _clean_name(name)
    vowels = "".join(c for c in letters if c in _VOWELS)
    consonants = "".join(c for c in letters if c not in _VOWELS)

    lp = _life_path(birth_date)
    d = _sum_letters(letters, table)
    su = _sum_letters(vowels, table)
    p = _sum_letters(consonants, table)
    nn = _sum_letters(letters, _CHALDEAN)  # Name number is always Chaldean by tradition

    def _get(mapping: dict, n: int) -> str:
        return mapping.get(n, "Number outside standard interpretation range.")

    return NumerologyReading(
        name=name.strip() or "Unnamed",
        birth_date=birth_date,
        system=system,
        life_path=lp,
        destiny=d,
        soul_urge=su,
        personality=p,
        name_number=nn,
        life_path_meaning=_get(_LIFE_PATH, lp),
        destiny_meaning=_get(_DESTINY, d),
        soul_urge_meaning=_get(_SOUL_URGE, su),
        personality_meaning=_get(_PERSONALITY, p),
        name_number_meaning=_get(_NAME_NUMBER, nn),
    )
