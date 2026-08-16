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
    # True when points were RESTORED by a classical cancellation rather than
    # RETIRED (#170). This flagged a koota whose points came from a dosha
    # cancellation rather than from passing its own test, so the page could
    # disclose it. Nothing sets it any more: cancellations and mitigations no
    # longer touch any score, which is what the flag existed to warn about.
    # Kept as a no-op field only so a stored or pickled KootaScore from before
    # the change still constructs; remove once nothing old can reach it.
    cancellation_applied: bool = False


@dataclass(frozen=True)
class BhakootDosha:
    """Bhakoot dosha and its parihāras, kept SEPARATE from the koota score.

    This separation IS the fix for #170. Muhurta Chintamani vv.32-33 says that
    when a parihāra holds, षट्काष्टकदोष नहीं होता — "the shadashtaka DOSHA does
    not occur". It never says the seven gunas are awarded; v.21 assigns those
    seven to भकूटमैत्री in a separate statement. So a parihāra is reported
    alongside the koota score and is not permitted to move it.
    """

    present: bool
    """Whether the Moon-rashi distance carries a classical Bhakoot dosha."""

    name: str
    """e.g. "Shadashtaka (6/8)"; empty when no dosha is present."""

    pariharas: tuple[str, ...]
    """Sourced parihāras that DO hold for this couple."""

    unevaluated: tuple[str, ...]
    """Parihāras we cannot test. Listed so silence is never read as absence."""

    cancelled: bool
    """True when at least one parihāra holds. Does NOT change any koota score."""

    nadi_shuddha: bool
    """Whether Nadi is clean. The text requires this regardless of any parihāra
    (परन्तु नाडी सभीमें होनी चाहिये), so a cancelled Bhakoot with an afflicted
    Nadi is NOT a clean chart."""

    note: str


@dataclass(frozen=True)
class NadiDosha:
    """Nadi dosha and its classical mitigations, kept SEPARATE from the score.

    Same separation as `BhakootDosha`, and for the same reason (#170). The
    difference is that Nadi has no parihāra list at all: the Bhakoot section
    ends परन्तु नाडी सभीमें होनी चाहिये — Nadi must be clean regardless. What
    the text offers instead is *gradation*, not cancellation.
    """

    present: bool
    nadi: str
    """The shared Nadi when afflicted; empty otherwise."""

    grave: bool
    """Both in Madhya Nadi — the text's gravest case (मृत्यु)."""

    alpa: bool
    """Nakshatra-Nadi collides but pada-Nadi does not. The text calls this
    दोष अल्प — the dosha is SLIGHT, not absent."""

    mitigations: tuple[str, ...]
    unevaluated: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class GunaMilan:
    """Full 8-koota Ashtakoot Guna Milan result + Mangal Dosh check + verdict."""

    kootas: tuple[KootaScore, ...]
    total_awarded: float
    total_max: int

    mangal_dosh_compatible: bool
    mangal_dosh_note: str

    bhakoot_dosha: BhakootDosha
    nadi_dosha: NadiDosha

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

    # Mangal Dosh compatibility — uses full compute_manglik_details() rather
    # than raw VedicFlags so cancellations (Jupiter aspects, own-sign Mars,
    # etc.) are properly reflected in the matching narrative.
    from astro_ai.chart import compute_manglik_details
    g_manglik = compute_manglik_details(groom)
    b_manglik = compute_manglik_details(bride)
    mangal = mangal_dosh_verdict(g_manglik, b_manglik)

    # Evaluated AFTER the kootas, because two of the parihāras are the Vashya
    # and Tara results. Deliberately does not feed back into `total` — see
    # `_bhakoot` and #170.
    bhakoot_dosha = _bhakoot_dosha(g_rashi_idx, b_rashi_idx, kootas)
    nadi_dosha = _nadi_dosha(g_moon, b_moon, g_nak, b_nak)

    verdict, label = _overall_verdict(total)
    return GunaMilan(
        kootas=kootas,
        total_awarded=total,
        total_max=36,
        mangal_dosh_compatible=mangal.compatible,
        mangal_dosh_note=mangal.note,
        bhakoot_dosha=bhakoot_dosha,
        nadi_dosha=nadi_dosha,
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

    SOURCED. Muhurta Chintamani, Vivaha prakarana, Hindi tika on vv. 27-28,
    which states the whole ladder in one sentence:

        मित्र तथा एकाधिपत्य   5.0   friend, or one planet lording both rashis
        सम + मित्र            4.0   neutral + friend
        सम + सम               3.0   neutral + neutral
        मित्र + शत्रु         2.0   friend + enemy
        सम + शत्रु            1.0   neutral + enemy
        शत्रु + शत्रु         0.0   enemy + enemy

    एकाधिपत्य (both rashis owned by the same graha) needs no separate branch:
    `_planet_relationship` already reports a planet as its own friend, so that
    case reaches the 5.0 row on its own.

    History, because the numbers moved twice. Before #174 the bottom two rows
    were transposed (friend+enemy 0.5, neutral+enemy 1.0), so holding one side
    at "enemy" and upgrading the other from neutral to friend made the score go
    DOWN. #174 fixed the inversion but had to invent the magnitudes — it said
    so, and said a sourced table would supersede it. This is that table, and it
    keeps the ordering #174 argued for while replacing the guessed 1.0/0.5 with
    the text's 2.0/1.0.

    31% of the 144 rashi pairs (44) land on these two rows, so this moves real
    scores — do not treat it as cosmetic.

    The tika also adds a judgement we deliberately do NOT encode: शत्रु शत्रुका
    मेल कहीं नहीं होता, मृत्युषट्काष्टक होता है — an enemy/enemy pairing is
    called categorically unfit. That is a verdict, not a point value, and the
    0.0 already carries it numerically.
    """
    pair = {a, b}
    if pair == {"friend"}:
        return 5.0, f"Lords {lord_a} & {lord_b} are mutual friends — full match"
    if "friend" in pair and "neutral" in pair:
        return 4.0, f"Lords {lord_a} & {lord_b}: one friend / one neutral"
    if pair == {"neutral"}:
        return 3.0, f"Lords {lord_a} & {lord_b} are mutually neutral"
    if "friend" in pair and "enemy" in pair:
        return 2.0, f"Lords {lord_a} & {lord_b}: mixed friend / enemy"
    if "neutral" in pair and "enemy" in pair:
        return 1.0, f"Lords {lord_a} & {lord_b}: one neutral / one enemy"
    return 0.0, f"Lords {lord_a} & {lord_b} are mutual enemies"


# Gana koota, 0-6. SOURCED: Muhurta Chintamani, Vivaha prakarana, Hindi tika
# on v.30, read at full page-image resolution.
#
#   इस कूटमें गणसाम्यमें ६ गुण, देव मनुष्य में ५, देव राक्षस एवं मनुष्य
#   राक्षसमें गुण (०) है, कन्या राक्षसी वर देवमें २, कन्या देव वर मनुष्यमें ४
#
# The tika states a general case and then two DIRECTIONAL exceptions, exactly
# as the Varna rule does (वर्णाधिक वर होनेमें गुण मिलता है — the groom ranking
# higher scores, the bride ranking higher does not). Read as unordered pairs
# the sentence contradicts itself: Deva/Rakshasa cannot be both 0 and 2. Read
# directionally it is consistent, and the consistent reading is the only one
# available:
#
#   groom   bride      pts
#   same    same        6    गणसाम्य
#   Deva    Manushya    5    the general देव-मनुष्य row
#   Manushya Deva       4    कन्या देव वर मनुष्य — the exception to it
#   Deva    Rakshasa    2    कन्या राक्षसी वर देव — the exception
#   Rakshasa Deva       0    the general देव-राक्षस row
#   Manushya Rakshasa   0    stated flatly, no exception either way
#   Rakshasa Manushya   0
#
# The prose above the table corroborates the asymmetry rather than the symmetry:
# वर राक्षस + कन्या मनुष्य gives वैर, while वर मनुष्य + कन्या राक्षस gives
# वरकी मृत्यु — the same unordered pair, two different verdicts.
#
# Two things changed here. Manushya/Rakshasa was 1.0 and is 0 — that value had
# no source. And the koota is now direction-dependent at all, which a set
# comparison could not express.
_GANA_POINTS: Final[dict[tuple[str, str], float]] = {
    ("Deva", "Manushya"): 5.0,
    ("Manushya", "Deva"): 4.0,
    ("Deva", "Rakshasa"): 2.0,
    ("Rakshasa", "Deva"): 0.0,
    ("Manushya", "Rakshasa"): 0.0,
    ("Rakshasa", "Manushya"): 0.0,
}


def _gana(g_nak: str, b_nak: str) -> KootaScore:
    """Score groom/bride gana temperament, 0-6. Order matters — see table."""
    g_g = _NAKSHATRA_GANA[g_nak]
    b_g = _NAKSHATRA_GANA[b_nak]
    if g_g == b_g:
        awarded, note = 6.0, f"Same gana ({g_g}) — full harmony"
    else:
        awarded = _GANA_POINTS[(g_g, b_g)]
        note = f"Groom {g_g} / bride {b_g}"
        if awarded >= 4.0:
            note += " — favourable"
        elif awarded > 0.0:
            note += " — tolerated, but the milder direction of this pair"
        else:
            note += " — opposed temperaments"
    return KootaScore(name="Gana", sanskrit="गण", max_points=6, awarded=awarded, note=note)


_BHAKOOT_DOSHA_NAMES: Final[dict[frozenset[int], str]] = {
    frozenset({6, 8}): "Shadashtaka (6/8)",
    frozenset({5, 9}): "Nava-panchama (5/9)",
    frozenset({2, 12}): "Dwirdwadasha (2/12)",
}


def _bhakoot_relation(g_idx: int, b_idx: int) -> tuple[int, int, str]:
    """Moon-rashi distances both ways, plus the dosha name ("" if none)."""
    d_g_to_b = ((b_idx - g_idx) % 12) + 1
    d_b_to_g = ((g_idx - b_idx) % 12) + 1
    name = _BHAKOOT_DOSHA_NAMES.get(frozenset({d_g_to_b, d_b_to_g}), "")
    return d_g_to_b, d_b_to_g, name


def _bhakoot(g_idx: int, b_idx: int) -> KootaScore:
    """Bhakoot koota: 7, or 0 when the Moon-rashi distance is 6/8, 5/9 or 2/12.

    POINTS TABLE ONLY. A parihāra no longer restores points here — that is the
    substance of #170, and the source agrees with the issue.

    Cancelling a dosha and awarding a koota its points are two different
    operations. The first is a judgement laid on top of the 36-point table; the
    second changes the total, and the total drives both the headline number and
    the Uttam/Madhyam/Avara band. Conflating them silently moved 43 of the 72
    dosha-carrying rashi pairs (60%) a whole verdict band upward.

    The classical text performs only the first operation. It says that when a
    parihāra holds, the shadashtaka DOSHA does not occur; it never says the
    seven gunas are awarded, and it assigns those seven to bhakoot-maitri in a
    separate statement listing all eight weights. See `_bhakoot_dosha` for the
    parihāras, which are reported alongside this score and cannot move it.

    The removed code also carried a citation naming a specific work for the
    cancellation, which #170 could not trace and which was not in fact its
    source. Provenance now lives in knowledge/matching.md.
    """
    d_g_to_b, d_b_to_g, dosha = _bhakoot_relation(g_idx, b_idx)
    if dosha:
        return KootaScore(
            name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=0.0,
            note=f"Bhakoot dosha — the {dosha} distance between the Moon signs is "
                 "classically an obstacle. Any cancellation is reported separately "
                 "and does not change this score.",
        )
    return KootaScore(
        name="Bhakoot", sanskrit="भकूट", max_points=7, awarded=7.0,
        note=f"No bhakoot dosha (Moon-rashi distance {d_g_to_b}/{d_b_to_g})",
    )


# The five parihāras for shad-ashtaka dosha, per the classical electional
# tradition (Muhurta Chintamani vv.32-33 — see knowledge/matching.md, and keep
# book names out of the user-facing `note` per CLAUDE.md).
#
#   1. मित्रषट्काष्टक      the Moon-sign lords are friends
#   2. एकाधिपत्य           one graha lords both signs (1&8 Mars, 2&7 Venus)
#   3. सबलांशेश मैत्री     the STRONG navamsha lords are friendly
#   4. राशिवश्यता          the Vashya relation holds
#   5. तारादि              Tara shuddhi
#
# "इनमेंसे एकके होनेमें भी षट्काष्टकदोष नहीं होता" — ANY ONE suffices.
# "परन्तु नाडी सभीमें होनी चाहिये" — but Nadi shuddhi is required regardless,
# and is never cancelled by this list. That is why `nadi_shuddha` is carried on
# the result rather than folded into `cancelled`.
#
# #3 is NOT evaluated. सबल means "strong", and we have no planetary-strength
# model — no shadbala anywhere in chart.py. Approximating it would make the
# parihāra fire more often than the text warrants, which is precisely the
# over-cancellation #170 exists to stop. It is reported as unevaluated instead,
# so its silence is never mistaken for its absence.
_PARIHARA_UNEVALUATED: Final[tuple[str, ...]] = (
    "Friendship of the strong Navamsha lords — not evaluated, as we do not "
    "compute planetary strength",
)


def _bhakoot_dosha(g_idx: int, b_idx: int, kootas: tuple[KootaScore, ...]) -> BhakootDosha:
    """Evaluate the Bhakoot dosha and its parihāras. Never changes a koota score."""
    _d1, _d2, dosha = _bhakoot_relation(g_idx, b_idx)
    by_name = {k.name: k for k in kootas}
    nadi = by_name["Nadi"]
    nadi_shuddha = nadi.awarded >= nadi.max_points

    if not dosha:
        return BhakootDosha(
            present=False, name="", pariharas=(), unevaluated=(), cancelled=False,
            nadi_shuddha=nadi_shuddha,
            note="No Bhakoot dosha between the Moon signs.",
        )

    g_lord, b_lord = _RASHI_LORD[g_idx], _RASHI_LORD[b_idx]
    applied: list[str] = []

    if g_lord == b_lord:
        applied.append(f"Both Moon signs are ruled by the same planet ({g_lord})")
    elif (_planet_relationship(g_lord, b_lord) == "friend"
          and _planet_relationship(b_lord, g_lord) == "friend"):
        applied.append(f"The Moon-sign lords ({g_lord} and {b_lord}) are natural friends")

    if by_name["Vashya"].awarded > 0:
        applied.append("The Vashya relation holds between the Moon signs")
    if by_name["Tara"].awarded > 0:
        applied.append("Tara (birth-star) compatibility is clean")

    cancelled = bool(applied)
    if cancelled:
        note = (
            f"{dosha} Bhakoot dosha is present, but the classical tradition cancels it "
            "when any one of five conditions holds. Here "
            + (f"{len(applied)} of them apply" if len(applied) > 1 else "one applies")
            + ". A cancellation removes the dosha; it does not add points to the "
            "score above."
        )
        if not nadi_shuddha:
            note += (
                " Note that the tradition still requires Nadi to be clean regardless of "
                "any cancellation, and it is not clean here."
            )
    else:
        note = (
            f"{dosha} Bhakoot dosha is present and none of the classical cancelling "
            "conditions apply."
        )

    return BhakootDosha(
        present=True, name=dosha, pariharas=tuple(applied),
        unevaluated=_PARIHARA_UNEVALUATED, cancelled=cancelled,
        nadi_shuddha=nadi_shuddha, note=note,
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


_NADI_NAMES: Final[tuple[str, ...]] = ("Vata", "Pitta", "Sleshma")


def _pada_nadi(nak_index: int, pada: int) -> str:
    """Nadi of a single pada, per Raman's pada table (#170).

    Raman gives Nadi at NAKSHATRA level first, then: "If Nadikuta is not
    present on the basis of the Nakshatras, then the same may be reckoned
    taking into account the Nakshatra Padas", with a printed table whose rule
    he states as "Beginning from Aswini 1, the counting should be done
    forwards and backwards in threes".

    So the 108 padas run Vata/Pitta/Sleshma, then reverse, then forward
    again — a boustrophedon in groups of three. Derived here and checked
    against all 15 cells he prints (Aswini 1-4, Bharani 1-4, Krittika 1-4,
    Rohini 1-3): 15/15.

    WHY THIS MATTERS. The code used to treat "same nakshatra, different pada"
    as automatic cancellation and award the full 8. Under Raman's own table
    that is wrong for 72 of the 324 such combinations (22%) — Aswini padas 3
    and 4 are different padas but BOTH Sleshma, so the dosha stands. The
    fallback he describes is a re-reckoning, not an amnesty.
    """
    p = nak_index * 4 + pada          # 1..108, absolute
    group, pos = (p - 1) // 3, (p - 1) % 3
    return _NADI_NAMES[pos if group % 2 == 0 else 2 - pos]


def _nadi(g_nak: str, b_nak: str) -> KootaScore:
    """Nadi koota: 8 for different Nadis, 0 for the same. POINTS TABLE ONLY.

    The restorations that used to live here are gone (#170). Two separate
    defects, and the source refutes both:

    **The full 8 for same-nakshatra-different-pada.** The text does address
    this case, and it does not cancel the dosha. जहां नक्षत्र नाडी हुएमें
    चरणनाडी न हो तहां दोष अल्प है — where the nakshatra-Nadi collides but the
    pada-Nadi does not, the dosha is SLIGHT. अल्प is a gradation, not an
    absence, so restoring all 8 points overstated what the text grants. It is
    now reported as a mitigation by `_nadi_dosha`.

    **The partial 4 for same-rashi-different-nakshatra.** Unsourced, and still
    unsourced after reading the Nadi section end to end: the text has no
    same-rashi clause and no half-credit anywhere. Classical Nadi is binary.
    Removed rather than rehomed, because there is nothing to rehome it to. It
    also carried a "BPHS matching tradition" provenance label that #170 could
    not verify and that this reading does not support.

    Unlike Bhakoot, Nadi has no parihāra list at all — the Bhakoot section ends
    परन्तु नाडी सभीमें होनी चाहिये, Nadi must be clean regardless. What the
    text offers here is gradation and shanti, never cancellation.
    """
    g_n = _NAKSHATRA_NADI[g_nak]
    b_n = _NAKSHATRA_NADI[b_nak]
    if g_n != b_n:
        return KootaScore(
            name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=8.0,
            note=f"Different nadis ({g_n} / {b_n}) — favourable",
        )
    return KootaScore(
        name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=0.0,
        note=f"Same nadi ({g_n}) — Nadi Dosha. Any classical mitigation is reported "
             "separately and does not change this score.",
    )


# Mitigations the text DOES grant for Nadi, none of which cancel it.
#
# Deliberately NOT auto-applied: मध्यनाडी छोड़के पार्श्वनाडियोंका दोष गोदावरीके
# दक्षिण अथवा क्षत्रिय आदिकोंको नहीं — outside Madhya, the side-Nadi dosha is
# waived south of the Godavari and for certain communities. Both halves are
# real and sourced, and we apply neither. Birthplace is not the same thing as
# the reckoning a family follows, and we will not infer someone's community
# from their chart in order to discount an affliction. They are disclosed as
# context a reader can apply themselves.
_NADI_UNEVALUATED: Final[tuple[str, ...]] = (
    "The tradition also scopes this dosha by region and community — outside the "
    "Madhya Nadi it is waived in parts of the south, and for some communities. "
    "We do not apply those exemptions automatically.",
)


def _nadi_dosha(g_moon, b_moon, g_nak: str, b_nak: str) -> NadiDosha:
    """Grade the Nadi dosha. Never changes a koota score."""
    g_n, b_n = _NAKSHATRA_NADI[g_nak], _NAKSHATRA_NADI[b_nak]
    if g_n != b_n:
        return NadiDosha(
            present=False, nadi="", grave=False, alpa=False, mitigations=(),
            unevaluated=(), note="The two Nadis differ — no Nadi dosha.",
        )

    grave = g_n == "Madhya"
    mitigations: list[str] = []
    alpa = False

    if g_nak == b_nak:
        g_pada, b_pada = _moon_pada(g_moon), _moon_pada(b_moon)
        # NOTE ON PROVENANCE: the CONCEPT of a pada-level Nadi (चरणनाडी) and
        # the "dosha is slight" grading are both from the same North Indian
        # text as the rest of this engine. The 108-pada MAPPING in
        # `_pada_nadi` is Raman's, which is South Indian. CLAUDE.md forbids
        # blending the two systems in one reading, and this is a blend. It is
        # tolerable only because it now moves no points — it decides the
        # wording of a mitigation note. Tracked; do not promote it back into
        # scoring without a mapping from this tradition.
        if g_pada != b_pada:
            g_pn = _pada_nadi(NAKSHATRAS.index(g_nak), g_pada)
            b_pn = _pada_nadi(NAKSHATRAS.index(b_nak), b_pada)
            if g_pn != b_pn:
                alpa = True
                mitigations.append(
                    f"Both Moons share the {g_n} Nadi, but reckoned at pada level they "
                    f"differ (padas {g_pada} and {b_pada}). The tradition calls the "
                    "dosha slight in this case — reduced, not removed."
                )

    if grave:
        note = (
            f"Both Moons fall in the {g_n} Nadi, which the tradition treats as the "
            "gravest form of this affliction rather than an ordinary one."
        )
    else:
        note = f"Both Moons share the {g_n} Nadi — Nadi dosha is present."
    if alpa:
        note += " One mitigation applies, below."
    note += (
        " Nadi has no cancelling conditions in this tradition: it is required to be "
        "clean regardless of how the other kootas score, and remedial measures rather "
        "than cancellation are what the classical texts prescribe."
    )

    return NadiDosha(
        present=True, nadi=g_n, grave=grave, alpa=alpa,
        mitigations=tuple(mitigations), unevaluated=_NADI_UNEVALUATED, note=note,
    )
