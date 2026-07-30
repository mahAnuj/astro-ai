"""Ashtakoot Guna Milan — classical Vedic marriage compatibility scoring.

Eight kootas, scored against fixed maximums summing to 36:

    Varna (1)     - varna/caste alignment via Moon Rashi
    Vashya (2)    - mutual control via Moon Rashi classification
    Tara (3)      - longevity/health via Nakshatra count
    Yoni (4)      - sexual compatibility via Nakshatra animal
    Graha Maitri (5) - mental harmony via Moon Rashi lord friendship
    Gana (6)      - temperament via Nakshatra gana (Deva/Manushya/Rakshasa)
    Bhakoot (7)   - family/relationship via Moon Rashi distance
    Nadi (8)      - genetic/progeny via Nakshatra Nadi (Adi/Madhya/Antya)

    Total: 36

Verdicts (broadly accepted):
    >= 30  Uttam     (excellent)
    24-29  Madhyam   (good)
    18-23  Avara     (acceptable, with caveats)
    < 18   Not recommended

Mangal Dosh compatibility is reported separately — both Manglik or both
non-Manglik is considered favourable; one of each is the classic dosha
that requires careful evaluation of cancellations (not computed here).

References: Brihat Parashara Hora Shastra; Muhurta Chintamani; modern
syntheses (Kapiel Raaj, B.V. Raman). This implementation uses the most
widely accepted variants — different schools differ on edge cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from astro_ai.chart import (
    Chart,
    NAKSHATRAS,
    RASHI_LORDS,
    RASHIS,
    VedicFlags,
    compute_vedic_flags,
)


# ---------------------------------------------------------------------------
# Reference tables (27 Nakshatras, 12 Rashis)
# ---------------------------------------------------------------------------

# Each Nakshatra's gana — temperament class.
_NAKSHATRA_GANA: Final[dict[str, str]] = {
    "Ashwini": "Deva", "Bharani": "Manushya", "Krittika": "Rakshasa",
    "Rohini": "Manushya", "Mrigashira": "Deva", "Ardra": "Manushya",
    "Punarvasu": "Deva", "Pushya": "Deva", "Ashlesha": "Rakshasa",
    "Magha": "Rakshasa", "Purva Phalguni": "Manushya",
    "Uttara Phalguni": "Manushya", "Hasta": "Deva", "Chitra": "Rakshasa",
    "Swati": "Deva", "Vishakha": "Rakshasa", "Anuradha": "Deva",
    "Jyeshtha": "Rakshasa", "Mula": "Rakshasa", "Purva Ashadha": "Manushya",
    "Uttara Ashadha": "Manushya", "Shravana": "Deva", "Dhanishta": "Rakshasa",
    "Shatabhisha": "Rakshasa", "Purva Bhadrapada": "Manushya",
    "Uttara Bhadrapada": "Manushya", "Revati": "Deva",
}

# Each Nakshatra's nadi (Adi / Madhya / Antya).
_NAKSHATRA_NADI: Final[dict[str, str]] = {
    "Ashwini": "Adi", "Bharani": "Madhya", "Krittika": "Antya",
    "Rohini": "Antya", "Mrigashira": "Madhya", "Ardra": "Adi",
    "Punarvasu": "Adi", "Pushya": "Madhya", "Ashlesha": "Antya",
    "Magha": "Antya", "Purva Phalguni": "Madhya", "Uttara Phalguni": "Adi",
    "Hasta": "Adi", "Chitra": "Madhya", "Swati": "Antya",
    "Vishakha": "Antya", "Anuradha": "Madhya", "Jyeshtha": "Adi",
    "Mula": "Adi", "Purva Ashadha": "Madhya", "Uttara Ashadha": "Antya",
    "Shravana": "Antya", "Dhanishta": "Madhya", "Shatabhisha": "Adi",
    "Purva Bhadrapada": "Adi", "Uttara Bhadrapada": "Madhya", "Revati": "Antya",
}

# Each Nakshatra's yoni (14 animals across 27 nakshatras).
_NAKSHATRA_YONI: Final[dict[str, str]] = {
    "Ashwini": "Horse", "Bharani": "Elephant", "Krittika": "Sheep",
    "Rohini": "Serpent", "Mrigashira": "Serpent", "Ardra": "Dog",
    "Punarvasu": "Cat", "Pushya": "Sheep", "Ashlesha": "Cat",
    "Magha": "Rat", "Purva Phalguni": "Rat", "Uttara Phalguni": "Cow",
    "Hasta": "Buffalo", "Chitra": "Tiger", "Swati": "Buffalo",
    "Vishakha": "Tiger", "Anuradha": "Deer", "Jyeshtha": "Deer",
    "Mula": "Dog", "Purva Ashadha": "Monkey", "Uttara Ashadha": "Mongoose",
    "Shravana": "Monkey", "Dhanishta": "Lion", "Shatabhisha": "Horse",
    "Purva Bhadrapada": "Lion", "Uttara Bhadrapada": "Cow", "Revati": "Elephant",
}

# Classical yoni "enemy" pairs — both directions. Same yoni = 4 pts;
# enemy pair = 0; everything else = 2 (neutral). Some traditions add a 3-pt
# "friend" tier; we keep three levels for the wider classical consensus.
_YONI_ENEMIES: Final[set[frozenset[str]]] = {
    frozenset({"Horse", "Buffalo"}),
    frozenset({"Elephant", "Lion"}),
    frozenset({"Sheep", "Monkey"}),
    frozenset({"Serpent", "Mongoose"}),
    frozenset({"Dog", "Deer"}),
    frozenset({"Cat", "Rat"}),
    frozenset({"Cow", "Tiger"}),
}

# Rashi (0..11 = Aries..Pisces) → varna class.
_RASHI_VARNA: Final[dict[int, str]] = {
    3: "Brahmin",  7: "Brahmin",  11: "Brahmin",   # Cancer, Scorpio, Pisces
    0: "Kshatriya", 4: "Kshatriya", 8: "Kshatriya",  # Aries, Leo, Sagittarius
    1: "Vaishya",   5: "Vaishya",   9: "Vaishya",   # Taurus, Virgo, Capricorn
    2: "Shudra",    6: "Shudra",   10: "Shudra",    # Gemini, Libra, Aquarius
}

# Varna hierarchy: higher index = higher rank (for Varna koota match rule).
_VARNA_RANK: Final[dict[str, int]] = {"Shudra": 1, "Vaishya": 2, "Kshatriya": 3, "Brahmin": 4}

# Rashi → vashya classification (5 classes; simplified — half-sign nuances
# of Sagittarius/Capricorn/Aquarius collapsed into majority class).
_RASHI_VASHYA: Final[dict[int, str]] = {
    0: "Chatushpada", 1: "Chatushpada",       # Aries, Taurus
    2: "Manava", 5: "Manava", 6: "Manava", 10: "Manava",  # Gemini, Virgo, Libra, Aquarius
    3: "Jalachara", 11: "Jalachara",          # Cancer, Pisces
    4: "Vanachara",                            # Leo
    7: "Keeta",                                # Scorpio
    8: "Manava",                               # Sagittarius (first-half human)
    9: "Jalachara",                            # Capricorn (water-leaning)
}

# Friendly vashya pairs (other than identical). Score 2 same, 1 friendly,
# 0.5 mutual food, 0 enmity. We use a simplified 3-level system.
_VASHYA_FRIENDLY: Final[set[frozenset[str]]] = {
    frozenset({"Manava", "Chatushpada"}),
    frozenset({"Manava", "Jalachara"}),
    frozenset({"Chatushpada", "Vanachara"}),
}

# Rashi → ruling planet shared from chart.py (also drives Graha Maitri here).
_RASHI_LORD: Final[dict[int, str]] = {i: RASHI_LORDS[i] for i in range(12)}

# Classical planetary friendships (Naisargika Maitri).
_FRIENDS: Final[dict[str, set[str]]] = {
    "Sun":     {"Moon", "Mars", "Jupiter"},
    "Moon":    {"Sun", "Mercury"},
    "Mars":    {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"},
    "Venus":   {"Mercury", "Saturn"},
    "Saturn":  {"Mercury", "Venus"},
}
_ENEMIES: Final[dict[str, set[str]]] = {
    "Sun":     {"Venus", "Saturn"},
    "Moon":    set(),
    "Mars":    {"Mercury"},
    "Mercury": {"Moon"},
    "Jupiter": {"Mercury", "Venus"},
    "Venus":   {"Sun", "Moon"},
    "Saturn":  {"Sun", "Moon", "Mars"},
}


def _planet_relationship(a: str, b: str) -> str:
    """Naisargika relationship of planet a to b: 'friend', 'neutral', 'enemy'."""
    if a == b:
        return "friend"  # same planet is treated as mutually friendly for matching
    if b in _FRIENDS.get(a, set()):
        return "friend"
    if b in _ENEMIES.get(a, set()):
        return "enemy"
    return "neutral"


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KootaScore:
    """One koota's verdict: name, max points, awarded, plain-English note."""

    name: str
    sanskrit: str
    max_points: int
    awarded: float
    note: str


@dataclass(frozen=True)
class GunaMilan:
    """Full 8-koota Ashtakoot Guna Milan result + Mangal Dosh check + verdict."""

    kootas: tuple[KootaScore, ...]
    total_awarded: float
    total_max: int

    mangal_dosh_compatible: bool
    mangal_dosh_note: str

    overall_verdict: str        # "Uttam" / "Madhyam" / "Avara" / "Not recommended"
    overall_verdict_label: str  # human-readable: "Excellent compatibility (Uttam)" etc.

    @property
    def percent(self) -> int:
        """Total as a percent of 36, rounded to nearest integer."""
        return int(round(self.total_awarded / self.total_max * 100))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_guna_milan(groom: Chart, bride: Chart) -> GunaMilan:
    """Score Ashtakoot Guna Milan for two natal charts (groom + bride)."""
    g_moon = next(p for p in groom.planets if p.name == "Moon")
    b_moon = next(p for p in bride.planets if p.name == "Moon")

    g_rashi_idx = RASHIS.index(g_moon.rashi)
    b_rashi_idx = RASHIS.index(b_moon.rashi)
    g_nak = g_moon.nakshatra
    b_nak = b_moon.nakshatra

    kootas = (
        _varna(g_rashi_idx, b_rashi_idx),
        _vashya(g_rashi_idx, b_rashi_idx),
        _tara(g_nak, b_nak),
        _yoni(g_nak, b_nak),
        _graha_maitri(g_rashi_idx, b_rashi_idx),
        _gana(g_nak, b_nak),
        _bhakoot(g_rashi_idx, b_rashi_idx),
        _nadi(g_nak, b_nak),
    )
    total = sum(k.awarded for k in kootas)

    # Mangal Dosh compatibility (both same status = favourable).
    g_flags = compute_vedic_flags(groom)
    b_flags = compute_vedic_flags(bride)
    mangal_compatible = (g_flags.manglik == b_flags.manglik)
    mangal_note = _mangal_dosh_note(g_flags, b_flags)

    verdict, label = _overall_verdict(total)
    return GunaMilan(
        kootas=kootas,
        total_awarded=total,
        total_max=36,
        mangal_dosh_compatible=mangal_compatible,
        mangal_dosh_note=mangal_note,
        overall_verdict=verdict,
        overall_verdict_label=label,
    )


def _overall_verdict(total: float) -> tuple[str, str]:
    """Map total score to (short verdict, human label)."""
    if total >= 30:
        return "Uttam", "Excellent compatibility (Uttam)"
    if total >= 24:
        return "Madhyam", "Good compatibility (Madhyam)"
    if total >= 18:
        return "Avara", "Acceptable with caveats (Avara)"
    return "Not recommended", "Below recommended threshold"


def _mangal_dosh_note(g: VedicFlags, b: VedicFlags) -> str:
    if g.manglik and b.manglik:
        return (
            "Both partners are Manglik. Traditionally this is favourable — the dosha "
            "cancels through matching, so marital concerns from Mars are mitigated."
        )
    if not g.manglik and not b.manglik:
        return "Neither partner is Manglik. No Mangal Dosh concerns indicated."
    manglik_side = "groom" if g.manglik else "bride"
    return (
        f"Only the {manglik_side} is Manglik. Classically this is the "
        "configuration that requires careful evaluation. Cancellations may apply "
        "(Mars in own/exalted sign, Jupiter aspect, certain conjunctions); these "
        "are not computed here. Consult a knowledgeable astrologer before deciding."
    )


# ---------------------------------------------------------------------------
# Individual koota scorers
# ---------------------------------------------------------------------------


def _varna(g_idx: int, b_idx: int) -> KootaScore:
    g_varna = _RASHI_VARNA[g_idx]
    b_varna = _RASHI_VARNA[b_idx]
    # Award 1 point if groom's varna >= bride's varna (the classical rule).
    awarded = 1.0 if _VARNA_RANK[g_varna] >= _VARNA_RANK[b_varna] else 0.0
    return KootaScore(
        name="Varna",
        sanskrit="वर्ण",
        max_points=1,
        awarded=awarded,
        note=f"Groom {g_varna} / Bride {b_varna}. "
             + ("Compatible" if awarded else "Bride's varna outranks groom's — 0 points"),
    )


def _vashya(g_idx: int, b_idx: int) -> KootaScore:
    g_v = _RASHI_VASHYA[g_idx]
    b_v = _RASHI_VASHYA[b_idx]
    if g_v == b_v:
        awarded, note = 2.0, f"Same vashya ({g_v}) — full match"
    elif frozenset({g_v, b_v}) in _VASHYA_FRIENDLY:
        awarded, note = 1.0, f"Friendly vashya ({g_v} / {b_v}) — partial match"
    else:
        awarded, note = 0.0, f"Vashya mismatch ({g_v} / {b_v})"
    return KootaScore(name="Vashya", sanskrit="वश्य", max_points=2, awarded=awarded, note=note)


def _tara(g_nak: str, b_nak: str) -> KootaScore:
    """Count nakshatras from each Moon to the other, mod 9.

    0-indexed position → 1-indexed classical name:
      0=Janma, 1=Sampat, 2=Vipat, 3=Kshema, 4=Pratyari,
      5=Sadhaka, 6=Vadha, 7=Mitra, 8=Ati-Mitra
    Favourable set = {Janma, Sampat, Kshema, Sadhaka, Mitra, Ati-Mitra}
    = positions {0, 1, 3, 5, 7, 8}. Ati-Mitra (position 8) is the
    STRONGEST positive tara — was previously excluded from `favourable`,
    silently miscounting ~11% of couples as unfavourable.
    """
    g_i = NAKSHATRAS.index(g_nak)
    b_i = NAKSHATRAS.index(b_nak)
    favourable = {0, 1, 3, 5, 7, 8}
    g_to_b = ((b_i - g_i) % 27) % 9
    b_to_g = ((g_i - b_i) % 27) % 9
    g_ok = g_to_b in favourable
    b_ok = b_to_g in favourable
    if g_ok and b_ok:
        awarded = 3.0
        note = "Both taras favourable — full strength"
    elif g_ok or b_ok:
        awarded = 1.5
        note = "Half-favourable — one direction works, the other doesn't"
    else:
        awarded = 0.0
        note = "Neither tara favourable"
    return KootaScore(name="Tara", sanskrit="तारा", max_points=3, awarded=awarded, note=note)


def _yoni(g_nak: str, b_nak: str) -> KootaScore:
    g_y = _NAKSHATRA_YONI[g_nak]
    b_y = _NAKSHATRA_YONI[b_nak]
    if g_y == b_y:
        awarded, note = 4.0, f"Same yoni ({g_y}) — full match"
    elif frozenset({g_y, b_y}) in _YONI_ENEMIES:
        awarded, note = 0.0, f"Enemy yonis ({g_y} / {b_y}) — full opposition"
    else:
        awarded, note = 2.0, f"Neutral yonis ({g_y} / {b_y})"
    return KootaScore(name="Yoni", sanskrit="योनि", max_points=4, awarded=awarded, note=note)


def _graha_maitri(g_idx: int, b_idx: int) -> KootaScore:
    g_lord = _RASHI_LORD[g_idx]
    b_lord = _RASHI_LORD[b_idx]
    g_to_b = _planet_relationship(g_lord, b_lord)
    b_to_g = _planet_relationship(b_lord, g_lord)
    awarded, note = _graha_maitri_score(g_to_b, b_to_g, g_lord, b_lord)
    return KootaScore(
        name="Graha Maitri", sanskrit="ग्रह मैत्री",
        max_points=5, awarded=awarded, note=note,
    )


def _graha_maitri_score(a: str, b: str, lord_a: str, lord_b: str) -> tuple[float, str]:
    pair = {a, b}
    if pair == {"friend"}:
        return 5.0, f"Lords {lord_a} & {lord_b} are mutual friends — full match"
    if "friend" in pair and "neutral" in pair:
        return 4.0, f"Lords {lord_a} & {lord_b}: one friend / one neutral"
    if pair == {"neutral"}:
        return 3.0, f"Lords {lord_a} & {lord_b} are mutually neutral"
    if "neutral" in pair and "enemy" in pair:
        return 1.0, f"Lords {lord_a} & {lord_b}: one neutral / one enemy"
    if "friend" in pair and "enemy" in pair:
        return 0.5, f"Lords {lord_a} & {lord_b}: mixed friend / enemy"
    return 0.0, f"Lords {lord_a} & {lord_b} are mutual enemies"


def _gana(g_nak: str, b_nak: str) -> KootaScore:
    g_g = _NAKSHATRA_GANA[g_nak]
    b_g = _NAKSHATRA_GANA[b_nak]
    if g_g == b_g:
        awarded, note = 6.0, f"Same gana ({g_g}) — full harmony"
    elif {g_g, b_g} == {"Deva", "Manushya"}:
        awarded, note = 5.0, f"Deva / Manushya — favourable"
    elif {g_g, b_g} == {"Manushya", "Rakshasa"}:
        awarded, note = 1.0, f"Manushya / Rakshasa — temperamental friction"
    else:  # Deva / Rakshasa
        awarded, note = 0.0, "Deva / Rakshasa — strongly opposed temperaments"
    return KootaScore(name="Gana", sanskrit="गण", max_points=6, awarded=awarded, note=note)


def _bhakoot(g_idx: int, b_idx: int) -> KootaScore:
    """0 points if Moon-rashi distance is 6-8, 5-9, or 2-12. Otherwise full 7."""
    distance_g_to_b = ((b_idx - g_idx) % 12) + 1
    distance_b_to_g = ((g_idx - b_idx) % 12) + 1
    dosha_pairs = ({6, 8}, {5, 9}, {2, 12})
    pair_set = {distance_g_to_b, distance_b_to_g}
    for bad in dosha_pairs:
        if pair_set == bad:
            return KootaScore(
                name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=0.0,
                note=f"Bhakoot dosha — distance {sorted(bad)} between Moon rashis is "
                     "classically considered an obstacle to marital harmony",
            )
    return KootaScore(
        name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=7.0,
        note=f"No bhakoot dosha (Moon-rashi distance {distance_g_to_b}/{distance_b_to_g})",
    )


def _nadi(g_nak: str, b_nak: str) -> KootaScore:
    """Different nadis = 8 points; same nadi = 0 (Nadi Dosha — strongly discouraged)."""
    g_n = _NAKSHATRA_NADI[g_nak]
    b_n = _NAKSHATRA_NADI[b_nak]
    if g_n != b_n:
        return KootaScore(
            name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=8.0,
            note=f"Different nadis ({g_n} / {b_n}) — favourable",
        )
    return KootaScore(
        name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=0.0,
        note=f"Same nadi ({g_n}) — Nadi Dosha. Classically considered the most serious "
             "obstacle, traditionally requiring consultation before proceeding.",
    )
