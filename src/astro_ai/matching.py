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

Mangal Dosh compatibility is reported separately. Both non-Manglik is
favourable; both Manglik is favourable ONLY when the two severities are
comparable (see _severity_comparable) — a low against a high does not
mutually cancel. One of each is the classic dosha that requires careful
evaluation of cancellations.

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
        _nadi(g_moon, b_moon, g_nak, b_nak, g_rashi_idx, b_rashi_idx),
    )
    total = sum(k.awarded for k in kootas)

    # Mangal Dosh compatibility — uses full compute_manglik_details() rather
    # than raw VedicFlags so cancellations (Jupiter aspects, own-sign Mars,
    # etc.) are properly reflected in the matching narrative.
    from astro_ai.chart import compute_manglik_details
    g_manglik = compute_manglik_details(groom)
    b_manglik = compute_manglik_details(bride)
    mangal = mangal_dosh_verdict(g_manglik, b_manglik)

    verdict, label = _overall_verdict(total)
    return GunaMilan(
        kootas=kootas,
        total_awarded=total,
        total_max=36,
        mangal_dosh_compatible=mangal.compatible,
        mangal_dosh_note=mangal.note,
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


_SEVERITY_RANK: dict[str, int] = {"low": 0, "moderate": 1, "high": 2}


def _severity_comparable(a: str, b: str) -> bool:
    """Are two Manglik severities "comparable" for the mutual-cancellation rule?

    knowledge/vedic_reference.md §1.3 table E rule 20, verbatim:
    "Both partners are Manglik of comparable severity | cancels for the
    marriage match".

    The corpus gives no band. It says "comparable" and stops — no classical
    source we hold defines how far apart two Manglik charts may sit and still
    cancel each other. Our own three-notch ladder (low < moderate < high) is a
    Bhagya construct, graded from the qualifying Mars house; the texts do not
    grade Manglik that way at all. So on that ladder `low` versus `high` is the
    only pair unambiguously outside any reading of "comparable" — excluding it
    invents nothing. Treating equal or adjacent grades as comparable
    (low↔moderate, moderate↔high) IS a Bhagya convention, chosen over
    exact-match-only because exact-match-only would deny mutual cancellation to
    most genuinely matched Manglik pairs purely on the strength of buckets we
    invented — over-firing in the harmful direction, i.e. telling couples they
    are incompatible. The convention is disclosed to the user in the note.

    Total over any input: unknown or "none" severities return True rather than
    raising. Those are unreachable from the both-effectively-Manglik branch
    (a Manglik chart always carries low/moderate/high), but this must not be
    the function that explodes on a status the engine grows later.
    """
    if a not in _SEVERITY_RANK or b not in _SEVERITY_RANK:
        return True
    return abs(_SEVERITY_RANK[a] - _SEVERITY_RANK[b]) <= 1


@dataclass(frozen=True)
class MangalVerdict:
    """Badge + prose for Mangal Dosh, decided together so they cannot disagree.

    Issue #165: the badge and the note used to be computed independently from
    two different definitions of "effectively Manglik", so the page could show
    a red badge above prose saying the dosha cancels. Both now come from one
    call to mangal_dosh_verdict().
    """

    compatible: bool
    branch: str
    note: str


_BRANCH_COMPATIBLE: dict[str, bool] = {
    "neither": True,
    "both_comparable": True,
    "both_incomparable": False,
    "one_sided": False,
}

# CLAUDE.md: state which convention a page uses rather than implying a single
# universal answer. Two separate facts, so two separate constants — every branch
# that mentions severity needs the grading rule, but only the branches that
# actually discuss mutual cancellation may mention the comparability band.
#
# How severity is graded. Must keep describing what compute_manglik_details()
# in chart.py actually does: grade on the UNION of qualifying houses across the
# Lagna, Moon and Venus axes, then drop one notch when only the Venus axis
# qualified. Defined once, referenced by all three Manglik branches — two copies
# of one fact is the class of bug this module was fixed to remove.
_SEVERITY_GRADING_SENTENCE = (
    "Severity here is graded from the houses Mars occupies counted from the "
    "Lagna, the Moon and Venus: 7th or 8th is high, 1st, 4th or 12th moderate, "
    "2nd alone low — and one grade lower when only the Venus-axis count "
    "qualifies."
)

# Where Bhagya draws the "comparable severity" band. Only meaningful when both
# partners are Manglik and mutual cancellation is on the table, so it is NOT
# appended to the one-sided note.
_COMPARABILITY_BAND_SENTENCE = (
    "Classical texts require 'comparable "
    "severity' for this mutual cancellation but do not define the band — Bhagya "
    "treats equal or adjacent grades as comparable, and a low-versus-high "
    "pairing as not comparable."
)

# Composed, not a third variant: both both-Manglik notes need both facts in this
# order, and composing here keeps that order defined once too.
_SEVERITY_CONVENTION_SENTENCE = (
    _SEVERITY_GRADING_SENTENCE + " " + _COMPARABILITY_BAND_SENTENCE
)


def mangal_dosh_verdict(g, b) -> MangalVerdict:
    """The single place the Mangal Dosh badge and note are decided.

    Accepts two ManglikDetails (from compute_manglik_details). "Does this chart
    count as Manglik?" is answered only by chart.is_effectively_manglik() — no
    effective_status literal lives here, because that duplication was the bug.
    """
    from astro_ai.chart import is_effectively_manglik

    g_effective = g.effective_status  # "none" | "cancelled" | "mitigated" | "present"
    b_effective = b.effective_status

    def _label(status: str) -> str:
        return {
            "none":      "not Manglik",
            "cancelled": "Manglik BUT classical cancellation applies",
            "mitigated": "Manglik with mitigating factors",
            "present":   "Manglik (uncancelled)",
        }.get(status, "unknown")

    g_lbl = _label(g_effective)
    b_lbl = _label(b_effective)

    g_present = is_effectively_manglik(g_effective)
    b_present = is_effectively_manglik(b_effective)

    if not g_present and not b_present:
        branch = "neither"
        if g_effective == "cancelled" or b_effective == "cancelled":
            note = (
                f"Groom: {g_lbl}. Bride: {b_lbl}. Both effectively clear after "
                "classical cancellations. No Mangal Dosh concerns for the match."
            )
        else:
            note = "Neither partner is Manglik. No Mangal Dosh concerns indicated."
    elif g_present and b_present:
        if _severity_comparable(g.severity, b.severity):
            branch = "both_comparable"
            note = (
                f"Groom: {g_lbl}. Bride: {b_lbl}. Both effectively Manglik — the "
                "dosha cancels through matching per classical tradition. Mars-related "
                "marital concerns are mitigated by the symmetry. "
                + _SEVERITY_CONVENTION_SENTENCE
            )
        else:
            branch = "both_incomparable"
            note = (
                f"Groom: {g_lbl}. Bride: {b_lbl}. Both are effectively Manglik, but "
                f"at different strengths ({g.severity} versus {b.severity}). The "
                "classical mutual-cancellation rule applies to partners of comparable "
                "severity, so we do not apply it here — this pairing still needs "
                "careful evaluation. " + _SEVERITY_CONVENTION_SENTENCE
            )
    else:
        branch = "one_sided"
        manglik_side = "groom" if g_present else "bride"
        other_side = "bride" if g_present else "groom"
        other_note = g_lbl if manglik_side == "bride" else b_lbl
        note = (
            f"Only the {manglik_side} is effectively Manglik (the {other_side} is {other_note}). "
            "Classically the configuration requiring careful evaluation. Look at the "
            "severity grade and consult before deciding — this is the case where "
            "matching may need extra remediation. " + _SEVERITY_GRADING_SENTENCE
        )

    return MangalVerdict(
        compatible=_BRANCH_COMPATIBLE[branch],
        branch=branch,
        note=note,
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
    """Score the Moon-lord friendship pair, 0-5.

    THE LADDER MUST STAY MONOTONIC (#174). Ordered by the quality of the two
    relationships, the six rows are:

        friend + friend    5.0
        friend + neutral   4.0
        neutral + neutral  3.0
        friend + enemy     1.0
        neutral + enemy    0.5
        enemy + enemy      0.0

    Until #174 the last two were transposed — friend+enemy scored 0.5 and
    neutral+enemy 1.0. Holding one side fixed at "enemy" and upgrading the
    other from neutral to friend therefore made the couple's score go DOWN,
    which no reading of any school supports. It was the only inversion in the
    table, which is what marks it as two adjacent rows swapped rather than a
    deliberate choice.

    The justification for the fix is internal, not textual, and that
    distinction matters: **no source we hold adjudicates these six values.**
    The corpus has no Graha Maitri scoring table — measured, not assumed —
    and #177 tracks that absence for the whole 36-point engine. What is being
    corrected here is a self-contradiction, which is wrong under every school
    at once. If a sourced table ever arrives and disagrees with these numbers,
    it supersedes this function; the ordering constraint is the part that
    should survive.

    31% of the 144 rashi pairs (44) land on the two corrected rows, so this
    moves real scores — do not treat it as cosmetic.
    """
    pair = {a, b}
    if pair == {"friend"}:
        return 5.0, f"Lords {lord_a} & {lord_b} are mutual friends — full match"
    if "friend" in pair and "neutral" in pair:
        return 4.0, f"Lords {lord_a} & {lord_b}: one friend / one neutral"
    if pair == {"neutral"}:
        return 3.0, f"Lords {lord_a} & {lord_b} are mutually neutral"
    if "friend" in pair and "enemy" in pair:
        return 1.0, f"Lords {lord_a} & {lord_b}: mixed friend / enemy"
    if "neutral" in pair and "enemy" in pair:
        return 0.5, f"Lords {lord_a} & {lord_b}: one neutral / one enemy"
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
    """Bhakoot koota with classical cancellation rules.

    Base rule: 0 points if Moon-rashi distance is 6-8, 5-9, or 2-12.
    Otherwise full 7.

    Classical cancellations (Muhurta Chintamani / BPHS §36) — if any of
    these hold, Bhakoot Dosh is cancelled and the couple gets full 7 with
    an explanatory note. Silently omitting these cancellations was flagging
    many otherwise-compatible couples as incompatible.
      - Same rashi lord (both rashis ruled by the same planet)
      - Rashi lords are Naisargika friends
    """
    distance_g_to_b = ((b_idx - g_idx) % 12) + 1
    distance_b_to_g = ((g_idx - b_idx) % 12) + 1
    dosha_pairs = ({6, 8}, {5, 9}, {2, 12})
    pair_set = {distance_g_to_b, distance_b_to_g}
    for bad in dosha_pairs:
        if pair_set == bad:
            # Check cancellations before failing.
            g_lord = _RASHI_LORD[g_idx]
            b_lord = _RASHI_LORD[b_idx]
            if g_lord == b_lord:
                return KootaScore(
                    name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=7.0,
                    note=f"Bhakoot dosha ({sorted(bad)}) cancelled — both rashis ruled by "
                         f"{g_lord}. Same rashi lord dissolves the classical dosha.",
                )
            if _planet_relationship(g_lord, b_lord) == "friend":
                return KootaScore(
                    name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=7.0,
                    note=f"Bhakoot dosha ({sorted(bad)}) cancelled — rashi lords "
                         f"{g_lord} and {b_lord} are Naisargika friends. Classical "
                         "cancellation per Muhurta Chintamani.",
                )
            return KootaScore(
                name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=0.0,
                note=f"Bhakoot dosha — distance {sorted(bad)} between Moon rashis is "
                     "classically an obstacle. No cancellation available "
                     f"(lords {g_lord} + {b_lord} not friendly).",
            )
    return KootaScore(
        name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=7.0,
        note=f"No bhakoot dosha (Moon-rashi distance {distance_g_to_b}/{distance_b_to_g})",
    )


def _moon_pada(moon) -> int:
    """The Moon's pada within its nakshatra (1-4).

    Reads the field rather than recomputing it. `PlanetPosition.pada` is
    populated at construction by `chart._pada_of`, so every consumer sees one
    number from one implementation.

    This function used to carry its own copy of the arithmetic, in the form
    `int((abs_long % (360/27)) / (360/108)) + 1`. That form is wrong at every
    exact 10-degree multiple — 20.0 gives pada 2 where 3 is correct — and the
    same copy existed in `muhurat._child_moon_pada`, where a `min(pada, 4)`
    clamp hid the symptom without fixing the cause. Three copies of one fact,
    which is exactly what #176/#165/#166 were about, and the boundary fix in
    #209 landed in only one of them.
    """
    return moon.pada


def _nadi(g_moon, b_moon, g_nak: str, b_nak: str, g_rashi_idx: int, b_rashi_idx: int) -> KootaScore:
    """Nadi koota with classical cancellation rules.

    Base rule: different nadis = 8 (favourable), same nadi = 0 (Nadi Dosh).

    Classical cancellations (BPHS matching tradition) — silently omitting
    these was mislabelling many compatible couples as incompatible on the
    hardest-weighted koota. Applied when same nadi:
      - Same nakshatra + different pada → Nadi Dosh cancelled (full 8)
      - Same rashi + different nakshatra → Nadi Dosh softened (partial 4)
    """
    g_n = _NAKSHATRA_NADI[g_nak]
    b_n = _NAKSHATRA_NADI[b_nak]
    if g_n != b_n:
        return KootaScore(
            name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=8.0,
            note=f"Different nadis ({g_n} / {b_n}) — favourable",
        )
    # Same nadi — check cancellations.
    if g_nak == b_nak:
        g_pada = _moon_pada(g_moon)
        b_pada = _moon_pada(b_moon)
        if g_pada != b_pada:
            return KootaScore(
                name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=8.0,
                note=f"Same nadi ({g_n}) BUT same nakshatra with different padas "
                     f"({g_pada} vs {b_pada}) — Nadi Dosh cancelled per classical rule.",
            )
    if g_rashi_idx == b_rashi_idx and g_nak != b_nak:
        return KootaScore(
            name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=4.0,
            note=f"Same nadi ({g_n}) BUT same Moon rashi with different nakshatras — "
                 "Nadi Dosh softened per classical practice. Partial credit.",
        )
    return KootaScore(
        name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=0.0,
        note=f"Same nadi ({g_n}) — Nadi Dosha. No classical cancellation applies "
             "(different nakshatras + different rashis). Traditionally requires "
             "consultation before proceeding.",
    )
