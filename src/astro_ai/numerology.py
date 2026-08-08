"""Numerology calculator — Chaldean + Pythagorean systems (Issue #112).

Positioned as COMPLEMENTARY to Vedic astrology, not a replacement. Numerology
reads name + birth date; Vedic reads the full birth chart. Two lenses on
the same person. When they agree, the signal is stronger.

Design:
- Pure math + fixed interpretation strings. NO LLM call.
- Two systems: Chaldean (traditional, more accurate per numerology tradition)
  + Pythagorean (Western simpler mapping).
- 5 numbers computed:
    Life Path       — sum of ALL birth-date digits, reduced to 1-9 or master
                      11/22/33 (Johari method; see _life_path)
    Destiny         — from all letters of full name
    Soul Urge       — from vowels of full name
    Personality     — from consonants of full name
    Name Number     — Chaldean-sum of full name (used for "lucky name" analysis)
- Interpretation strings hand-written honestly — no scam claims, no lucky-name
  upsell, no "wear this gem for your number" pitch.

Reduction policy:
    `_reduce` takes a keyword-only `preserve_masters` with no default, because
    the four call sites in this module do not agree. Whether 11/22/33 survive
    is a per-number editorial decision, not a module-wide constant (#162, #164,
    #169, #179):

      _personal_year    preserve_masters=False   -> 1-9 only (§12.8; the panel
                                                   captions itself "Cycles 1-9")
      _birthday_number  preserve_masters=False   -> 1-9 only (§2.1; Johari's
                                                   own birthday lists file 11
                                                   under 2 and 22 under 4)
      _sum_letters      preserve_masters=True    -> Destiny / Soul Urge /
                                                   Personality / Name Number
      _life_path        preserve_masters=True    -> masters kept on the final
                                                   all-digits total

    Consequence: `_PERSONAL_YEAR_THEME` and `_BIRTHDAY_MEANING` carry keys 1-9
    only. `_LIFE_PATH`, `_DESTINY`, `_SOUL_URGE`, `_PERSONALITY`, `_NAME_NUMBER`
    and `_REMEDIES` still need their 11/22/33 rows — those remain reachable.
    `scripts/verify_numerology_reduction.py` is the executable check that the
    table keys and the policy above still agree; run it after touching either.

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

# ─── Rules version ────────────────────────────────────────────────────
# Baked into the ask-cache key for ctx=numerology. LLM prose is written
# against whatever the numbers were at generation time, so a cached answer
# from before a rule change describes a reading we no longer compute —
# bumping this makes those entries unreachable instead of silently served.
#
# v1 → v2: reduction policy made explicit per call site, and Life Path
# switched from the reduce-parts-then-sum method to Johari's all-digits
# method (issues #162, #164, #169, #179). ~13.5% of birth dates change
# Life Path, so v1 prose can contradict v2 numbers.
NUMEROLOGY_RULES_VERSION = "2"


@dataclass(frozen=True)
class LifePathProfile:
    """Rich per-Life-Path descriptive profile from Johari §4.

    Everything a real numerologist would tell a client — not just a
    one-line archetype but character, strengths, weaknesses, health
    tendencies, career direction, compatibility, and timing.
    """
    number: int
    planet: str
    planet_sanskrit: str
    character: str                    # 2-3 sentence descriptive paragraph
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    health: str
    career: str                       # narrative paragraph
    career_fields: tuple[str, ...]
    best_partners: tuple[int, ...]
    worst_partners: tuple[int, ...]
    peak_period: str                  # age-window when this number peaks
    strong_months: str                # e.g. "Mar 21 – Apr 28; Jul 10 – Aug 20"
    weak_months: str
    good_dates: tuple[int, ...]       # dates 1-31 in any month
    exalted_dates: tuple[int, ...]    # Johari's most-fortunate birthdates
    best_day: str                     # weekday
    life_challenges: str              # honest paragraph about what this number struggles with


@dataclass(frozen=True)
class NumerologyRemedy:
    """Per-number remedy recommendations from Johari's Vedic-integrated system.

    Every remedy corresponds to the number's ruling planet — gemstone is
    the loudest lever (needs chart consultation), rudraksha is the safest
    practical lever (no chart consult needed), charity/puja/plants/yantra
    are behavioural remedies that anyone can start today.
    """
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
    # ─── Classical Vedic remedies added in cycle 10 (per Johari §3 + §4) ──
    # These are the safe, behavioural remedies traditionally recommended
    # ALONGSIDE (not instead of) chart-consulted gemstones.
    rudraksha: str             # mukhi count + wearing note; e.g. "1-mukhi (or 12-mukhi) on red thread"
    yantra: str                # geometric symbol traditionally worshipped for this planet
    charity: str               # dan/donation — what to give, to whom, when
    sacred_plants: str         # trees/herbs sacred to this planet (grow, worship, or use)
    puja: str                  # specific ritual practice


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

    # Rich Life Path profile — character, strengths, health, career, timing
    life_path_profile: LifePathProfile | None = None

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

    # Lo Shu 3×3 birth-number matrix — user's DOB digits plotted on the
    # classical magic-square grid. Reveals present/absent number patterns
    # ('arrows') for a real-numerologist-style visual reading. Sourced
    # from Cheiro's Book of Numbers per knowledge/numerology.md §13.3
    # (this is outside Johari + Kumar's Chaldean/Vedic scope).
    lo_shu: "LoShuGrid | None" = None


# ─── Lo Shu (birth-number matrix) — Cheiro / Chinese classical ────────
# The 3×3 grid used by traditional numerologists to visualise a person's
# birth-number pattern. Each cell holds the digit that sits there in the
# Lo Shu magic square (rows + columns + diagonals all sum to 15):
#
#     4 | 9 | 2
#     3 | 5 | 7
#     8 | 1 | 6
#
# For a person's chart we count how many times each of digits 1..9
# appears in their DOB (zeros excluded per Cheiro). Cells with count > 0
# are 'present'; missing digits are 'life lessons'. Fully-present or
# fully-missing rows / columns / diagonals form the 8 classical
# 'arrows' — named patterns with known character interpretations.
#
# Source: Cheiro (Count Louis Hamon), *Cheiro's Book of Numbers* (Singh,
# Rakesh Publisher edition, 1926 original). Cross-referenced with
# standard Indian numerology practice. Marked separately from Johari +
# Kumar (see knowledge/numerology.md §13.3).

@dataclass(frozen=True)
class LoShuArrow:
    """A row / column / diagonal in the Lo Shu grid — fully present or fully missing."""
    name: str                                # e.g. 'Arrow of Willpower'
    digits: tuple[int, int, int]              # the 3 digits forming this arrow
    kind: str                                 # 'present' | 'missing'
    meaning: str                              # classical interpretation


@dataclass(frozen=True)
class LoShuDigitMeaning:
    """Per-digit theme for the grid tooltip / cell caption."""
    digit: int
    theme: str            # short theme e.g. 'Ego', 'Sensitivity'
    planet: str           # ruling planet in the Vedic-integrated system
    if_present: str       # what having this digit means
    if_missing: str       # what missing this digit means


@dataclass(frozen=True)
class LoShuGrid:
    """The complete Lo Shu reading for one person."""
    dob_digits: str                          # source digits used (e.g. '19880514')
    counts: dict[int, int]                    # digit 1..9 → count in DOB
    present_arrows: tuple[LoShuArrow, ...]   # rows/cols/diagonals fully present
    missing_arrows: tuple[LoShuArrow, ...]   # rows/cols/diagonals fully absent
    digit_meanings: tuple[LoShuDigitMeaning, ...]   # for template tooltips (all 9)


# Physical layout of the grid — rows × cols → the digit at that cell.
LO_SHU_LAYOUT: tuple[tuple[int, ...], ...] = (
    (4, 9, 2),   # top row
    (3, 5, 7),   # middle row
    (8, 1, 6),   # bottom row
)


# Classical digit themes (per Cheiro + standard Vedic-numerology practice).
_DIGIT_MEANINGS: tuple[LoShuDigitMeaning, ...] = (
    LoShuDigitMeaning(
        digit=1, theme="Ego & self-expression", planet="Sun",
        if_present="Confident individuality, willingness to lead, clear sense of self.",
        if_missing="Struggles with self-assertion; may hide behind others' opinions. Practice speaking your own view first.",
    ),
    LoShuDigitMeaning(
        digit=2, theme="Sensitivity & intuition", planet="Moon",
        if_present="Emotionally attuned to others, receptive, diplomatic in conflict.",
        if_missing="Can appear cold or insensitive without meaning to. Practice naming what others feel out loud.",
    ),
    LoShuDigitMeaning(
        digit=3, theme="Imagination & communication", planet="Jupiter",
        if_present="Creative mind, expressive with words or art, quick with ideas.",
        if_missing="Prefers concrete facts over metaphor; may need to consciously make time for play / art.",
    ),
    LoShuDigitMeaning(
        digit=4, theme="Order & practical skill", planet="Rahu",
        if_present="Methodical, hands-on, good with detail and structure.",
        if_missing="Impatient with routine detail; delegate paperwork or use systems that don't need you to remember.",
    ),
    LoShuDigitMeaning(
        digit=5, theme="Balance & freedom (grid centre)", planet="Mercury",
        if_present="Balanced perspective, adaptable, natural mediator (nearly everyone has this — grid centre).",
        if_missing="Rare — usually indicates a very unusual DOB. When absent, seek middle-path answers explicitly.",
    ),
    LoShuDigitMeaning(
        digit=6, theme="Love, home & family", planet="Venus",
        if_present="Warm with family, generous host, aesthetic sense.",
        if_missing="Home life may feel like effort more than nourishment; practice small rituals that make house feel like home.",
    ),
    LoShuDigitMeaning(
        digit=7, theme="Sacrifice & inner life", planet="Ketu",
        if_present="Philosophical, comfortable with solitude, drawn to spiritual questions.",
        if_missing="Very worldly focus; deliberate quiet time or study of a classical text balances the material push.",
    ),
    LoShuDigitMeaning(
        digit=8, theme="Business & material world", planet="Saturn",
        if_present="Naturally organised with money and systems, patient with long-timeline goals.",
        if_missing="May struggle with saving / structure; simple habits (fixed savings %, weekly review) close this gap.",
    ),
    LoShuDigitMeaning(
        digit=9, theme="Ambition & universality", planet="Mars",
        if_present="Drive, courage, willingness to fight for a cause bigger than the self.",
        if_missing="Rare after year 1000 (calendar digit forces it in most cases). If absent, look for what you'd fight for.",
    ),
)


# The 8 classical arrows — 3 rows + 3 columns + 2 diagonals. Each has a
# 'present' interpretation (all 3 digits appear in the DOB) and a
# 'missing' interpretation (all 3 digits absent). Names cross-referenced
# from Cheiro + modern Indian-numerology practice (both use the same
# vocabulary — inherited from a common Chinese/Chaldean source).
_LO_SHU_ARROW_DEFS: tuple[dict, ...] = (
    # Rows
    dict(digits=(4, 9, 2),
         present_name="Arrow of Intellect",
         present_meaning="Sharp mind + strong memory + clear reasoning. Natural teachers, writers, analysts.",
         missing_name="Arrow of Poor Memory",
         missing_meaning="Tendency to forget names and details. Remedy: keep a written journal; verify important facts twice."),
    dict(digits=(3, 5, 7),
         present_name="Arrow of Emotional Balance",
         present_meaning="Steady inner life, well-grounded in the middle path. Doesn't swing to extremes.",
         missing_name="Arrow of Emotional Instability",
         missing_meaning="Emotions may swing high/low quickly. Regular meditation or breath practice stabilises."),
    dict(digits=(8, 1, 6),
         present_name="Arrow of Practicality",
         present_meaning="Gets things done. Bridges vision and execution — rare and valuable in any team.",
         missing_name="Arrow of the Impractical",
         missing_meaning="Ideas outrun execution. Partner with a doer or use rigorous checklists to close the gap."),
    # Columns
    dict(digits=(4, 3, 8),
         present_name="Arrow of the Planner",
         present_meaning="Excellent long-range planner + organiser. Builds systems that outlast you.",
         missing_name="Arrow of Poor Planner",
         missing_meaning="Struggles with sequencing multi-step plans. Break work into 3-step chunks; write them down."),
    dict(digits=(9, 5, 1),
         present_name="Arrow of Willpower & Determination",
         present_meaning="Iron will, follows through even when interested parties fall away. Marathon endurance."),
    dict(digits=(2, 7, 6),
         present_name="Arrow of the Active",
         present_meaning="Physically and emotionally engaged with the world. Rarely idle.",
         missing_name="Arrow of Sensitivity",
         missing_meaning="Prefers a calmer, quieter pace. Choose environments that respect this — noisy open-plan offices drain you."),
    # Diagonals
    dict(digits=(4, 5, 6),
         present_name="Arrow of Prosperity",
         present_meaning="Natural flow of material and emotional abundance. Money and love arrive without desperate chase.",
         missing_name="Arrow of the Skeptic",
         missing_meaning="Questions everything, sometimes to the point of rejecting real opportunity. Trust a mentor's judgement more than yours in unfamiliar domains."),
    dict(digits=(2, 5, 8),
         present_name="Arrow of Determination",
         present_meaning="Deep resolve — chooses a hard path and does not turn back. Founders, athletes, revolutionaries.",
         missing_name="Arrow of Hyper-sensitivity",
         missing_meaning="Small setbacks can feel like personal attacks. Build a small circle of trusted feedback so you can hear criticism without collapse."),
)
# Fill in the Willpower arrow's 'missing' variant separately since it has
# an asymmetric handling in traditional readings — the missing case is
# sometimes not explicitly named. Add for consistency.
_LO_SHU_ARROW_DEFS[4]["missing_name"] = "Arrow of Weak Will"
_LO_SHU_ARROW_DEFS[4]["missing_meaning"] = "Difficulty pushing through when motivation flags. Public commitments (announce goals to friends) create external pressure that substitutes for internal will."


# ─── Numerology Bhagya Score ──────────────────────────────────────────
# Same 0-100 gamified 'current chapter weather' concept as the Kundli
# Bhagya Score in chart.py, but computed from numerology signals only.
# Framed identically ('weather not destiny'). Shown on /numerology
# result so users who compute numerology-first (without a Kundli) still
# get a headline number to anchor the reading.
#
# Numerology signals move much more slowly than chart signals — the only
# annually-shifting one is Personal Year. So this score is more of a
# 'core disposition' snapshot than a daily reading. Copy on the template
# calls this out honestly.

@dataclass(frozen=True)
class NumBhagyaDriver:
    """One signal feeding the numerology Bhagya Score."""
    weight: int
    note: str
    kind: str   # 'boost' | 'reduce'


@dataclass(frozen=True)
class NumBhagyaScore:
    """0-100 numerology-only Bhagya Score."""
    value: int
    label: str
    label_class: str    # 'emerald' | 'astro' | 'amber' | 'rose'
    drivers: tuple[NumBhagyaDriver, ...]

    @property
    def top_drivers(self) -> tuple[NumBhagyaDriver, ...]:
        return self.drivers[:3]


# Life-Path-to-Destiny friend-pair map (per Johari §7). Same as the
# friend-pair used by compute_compatibility() but re-declared here to
# avoid coupling this score to that helper's private module vars.
_LP_DESTINY_FRIENDS: set[tuple[int, int]] = {
    (1, 1), (1, 3), (1, 5), (1, 9),
    (2, 2), (2, 7), (2, 9),
    (3, 3), (3, 6), (3, 9),
    (4, 4), (4, 8),
    (5, 5), (5, 6),
    (6, 6), (6, 9),
    (7, 7),
    (8, 8),
    (9, 9),
}
_LP_DESTINY_ENEMIES: set[tuple[int, int]] = {
    (1, 8), (2, 5), (3, 5), (4, 3), (4, 5), (6, 7), (6, 8), (7, 3), (7, 8), (8, 9),
}


def compute_numerology_bhagya_score(reading: NumerologyReading, lang: str = "en") -> NumBhagyaScore:
    """Compute the numerology-only Bhagya Score.

    All signals sourced from the NumerologyReading dataclass; no external
    LLM or chart data required. Master numbers (11/22/33) route through
    their reduced base for pair lookups but keep their own boost bonus.

    `lang` selects driver-note + label language (i18n follow-up
    2026-08-04 after Shyamasundara audit surfaced that these were
    English-only regardless of user language).
    """
    from astro_ai.i18n import translate

    drivers: list[NumBhagyaDriver] = []
    score = 50

    def _add(delta: int, key: str, **kwargs) -> None:
        nonlocal score
        score += delta
        drivers.append(NumBhagyaDriver(
            weight=delta, note=translate(lang, key, **kwargs),
            kind="boost" if delta > 0 else "reduce",
        ))

    lp = int(reading.life_path)
    lp_base = {11: 2, 22: 4, 33: 6}.get(lp, lp)

    # Master number Life Path — rare and spiritually potent per Kumar
    if lp in (11, 22, 33):
        _add(+8, "nbs_master_lp", lp=lp, base=lp_base)
    # Naturally auspicious Life Paths per Johari §4 (Sun / Jupiter / Mercury / Venus rulers)
    elif lp_base in (1, 3, 5, 6):
        planet = {1: "Sun", 3: "Jupiter", 5: "Mercury", 6: "Venus"}[lp_base]
        _add(+5, "nbs_supportive_lp", lp=lp, planet=planet)

    # Karmic Debt Numbers (Kumar Ch.1) — each is soul-work
    if reading.karmic_debt_numbers:
        n = len(reading.karmic_debt_numbers)
        pts = -min(n * 3, 12)   # cap -12
        names = "/".join(str(k) for k in reading.karmic_debt_numbers)
        _add(pts, "nbs_karmic_debt", names=names)

    # Life Path × Destiny harmony
    d = int(reading.destiny)
    d_base = {11: 2, 22: 4, 33: 6}.get(d, d)
    pair = (min(lp_base, d_base), max(lp_base, d_base))
    if pair in _LP_DESTINY_FRIENDS:
        _add(+5, "nbs_lp_dest_friend", lp=lp, d=d)
    elif pair in _LP_DESTINY_ENEMIES:
        _add(-3, "nbs_lp_dest_enemy", lp=lp, d=d)

    # Personal Year — the ONLY annually-shifting signal in this score.
    # Dynamic years (1, 3, 5, 9) boost; grinding years (4, 7, 8) reduce.
    # py is now guaranteed 1-9 (#169), so a py of 11/22/33 can no longer slip
    # past all three branches — that was the silent dropout, and it cost the
    # score its only time-varying term for 9.58% of birth dates (2,555 of the
    # 26,664 dates from 1940-01-01 to 2012-12-31, scored against target year
    # 2026 under the old master-preserving reduction; re-measured 2026-08-09).
    # The branches still do not cover every value: py == 2 matches none of
    # them and is deliberately unscored as a neutral year — that is 10.68% of
    # dates (2,379 of the 22,280 from 1950-01-01 to 2010-12-31, target year
    # 2026, measured 2026-08-09). Adding a py == 2 branch would move the
    # Bhagya score and so belongs with #161, not here.
    py = int(reading.personal_year)
    if py in (1, 3, 5, 9):
        _add(+3, "nbs_py_dynamic", py=py)
    elif py in (4, 7, 8):
        _add(-2, "nbs_py_grind", py=py)
    elif py == 6:
        _add(+2, "nbs_py_harmony")

    # Compound Name number in Johari's most-fortunate 4-tier compounds
    # (10, 19, 23, 27, 28, 37, 46, 49): +2. The exalted 1s per §5.
    if reading.name_compound in (10, 19, 23, 27, 28, 37, 46, 49):
        _add(+2, "nbs_compound_good", n=reading.name_compound)
    elif reading.name_compound in (13, 14, 16, 26, 43):
        _add(-2, "nbs_compound_challenge", n=reading.name_compound)

    # Clamp + bucket label
    score = max(0, min(100, score))
    if score >= 75:
        label = translate(lang, "nbs_label_strong")
        label_class = "emerald"
    elif score >= 50:
        label = translate(lang, "nbs_label_steady")
        label_class = "astro"
    elif score >= 25:
        label = translate(lang, "nbs_label_patience")
        label_class = "amber"
    else:
        label = translate(lang, "nbs_label_deep")
        label_class = "rose"

    drivers.sort(key=lambda x: abs(x.weight), reverse=True)
    return NumBhagyaScore(
        value=score,
        label=label,
        label_class=label_class,
        drivers=tuple(drivers),
    )


def compute_lo_shu_grid(birth_date_iso: str) -> LoShuGrid:
    """Compute the Lo Shu 3×3 grid from an ISO birth date (YYYY-MM-DD).

    Zeros in the DOB are excluded per Cheiro's classical rule. Life Path
    and Destiny numbers are NOT added — this is the pure DOB-only grid
    (some modern traditions extend by adding these; Bhagya sticks with
    the classical version because it gives cleaner, more repeatable
    interpretations across sources).
    """
    digits_str = "".join(ch for ch in birth_date_iso if ch.isdigit() and ch != "0")
    counts = {n: 0 for n in range(1, 10)}
    for ch in digits_str:
        counts[int(ch)] += 1
    present_arrows: list[LoShuArrow] = []
    missing_arrows: list[LoShuArrow] = []
    for a in _LO_SHU_ARROW_DEFS:
        cells = a["digits"]
        all_present = all(counts[c] > 0 for c in cells)
        all_missing = all(counts[c] == 0 for c in cells)
        if all_present:
            present_arrows.append(LoShuArrow(
                name=a["present_name"], digits=cells, kind="present",
                meaning=a["present_meaning"],
            ))
        elif all_missing:
            missing_arrows.append(LoShuArrow(
                name=a["missing_name"], digits=cells, kind="missing",
                meaning=a["missing_meaning"],
            ))
    return LoShuGrid(
        dob_digits=digits_str,
        counts=counts,
        present_arrows=tuple(present_arrows),
        missing_arrows=tuple(missing_arrows),
        digit_meanings=_DIGIT_MEANINGS,
    )


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

# Softened from a deterministic "Destined to..." voice (which read as
# fate-predictions) to a reflective "traditionally associated with..."
# voice matching the framework-honest tone of the /numerology caveat.
# Content unchanged — same career/role themes; language now invites
# self-reflection rather than asserting an outcome.
_DESTINY = {
    1: "Traditionally associated with leadership themes — original ventures, entrepreneurship, being first at something. Use as a prompt for what shape of work you're drawn to, not a prediction.",
    2: "Traditionally associated with partnership work — mediation, diplomacy, supporting roles that hold things together.",
    3: "Traditionally associated with communication — writing, speaking, teaching, art. Your voice may be a key instrument.",
    4: "Traditionally associated with building — real estate, engineering, systems, long-term structures.",
    5: "Traditionally associated with variety and movement — sales, travel, marketing, roles requiring adaptability.",
    6: "Traditionally associated with caring roles — teaching, medicine, family businesses, community work.",
    7: "Traditionally associated with depth — research, spiritual work, specialised expertise, deep analysis.",
    8: "Traditionally associated with material achievement — business, finance, executive leadership.",
    9: "Traditionally associated with humanitarian work — non-profits, healing arts, global-impact roles.",
    11: "Traditionally associated with visionary work — psychic/spiritual leadership, inspirational teaching.",
    22: "Traditionally associated with large-scale building — architecture, foundational institutions, movements.",
    33: "Traditionally associated with enlightened service — spiritual teaching, deep healing, exceptional care.",
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
    # No 11/22/33 rows: _birthday_number reduces fully to 1-9 (knowledge/
    # numerology.md §2.1, issue #164), so those keys were unreachable. Do not
    # re-add them — an unreachable interpretation row is how #146's abujha
    # table rotted. #164 §5 suggests surfacing "born on an 11/22 day" as a
    # compound-number annotation instead; deliberately NOT done here.
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
        rudraksha="1-mukhi (Ek-mukhi) — rarest and most powerful; 12-mukhi acceptable alternative. Wear on red thread on Sunday sunrise after chanting the Surya mantra 108 times.",
        yantra="Surya Yantra — engraved on copper or gold plate, installed facing east and worshipped at sunrise with red flowers and jaggery-water.",
        charity="Wheat, jaggery, copper vessels, red cloth, red sandalwood. Offer to father-figures, elder males, or Surya temples on Sunday morning.",
        sacred_plants="Bilva (bael), red hibiscus, sunflower, Arka (calotropis). Grow bilva at home; offer bilva leaves or red hibiscus to Surya at sunrise.",
        puja="Surya Namaskar 12 rounds daily facing east; offer arghya (water with red flowers) at sunrise; Aditya Hridaya Stotra weekly, ideally on Sunday.",
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
        rudraksha="2-mukhi (Do-mukhi) — sacred to Shiva-Parvati (Ardhanarishwara). Wear on white silk thread Monday sunrise after Chandra mantra.",
        yantra="Chandra Yantra — engraved on silver, worshipped Monday evening facing north-west with white flowers and cow milk.",
        charity="Rice, milk, curd, white cloth, silver, camphor, sugar. Offer to mothers, elderly women, or nursing wards on Monday evening.",
        sacred_plants="Palasha (butea), white lotus, jasmine, sandalwood, Tulsi. Tulsi worship at dusk strengthens Moon; offer white lotus in Shiva puja.",
        puja="Shiva abhishek every Monday with cow milk + gangajal; offer white flowers + bilva leaves; recite Chandra bija mantra 108 times before sleep.",
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
        rudraksha="5-mukhi (Panch-mukhi) — sacred to Guru; the most common Rudraksha, safe for all natives. Wear on yellow thread Thursday sunrise.",
        yantra="Guru Yantra — engraved on gold or copper, worshipped Thursday sunrise facing north-east with yellow flowers and turmeric.",
        charity="Yellow cloth, turmeric, yellow gram (chana daal), jaggery, gold jewellery, ghee, books. Offer to teachers, priests, or students on Thursday.",
        sacred_plants="Peepal (sacred fig), banana tree, Rasala (mango). Water peepal daily; circumambulate 108 times on Thursday morning.",
        puja="Vishnu Sahasranama recitation Thursday morning; Guru Namaskar; offer yellow flowers + jaggery to Vishnu; Satyanarayan katha on Purnima days.",
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
        rudraksha="8-mukhi (Ath-mukhi) — sacred to Ganesha, Rahu's remedy deity. Wear on grey/black thread Saturday sunrise after Ganesha mantra.",
        yantra="Rahu Yantra — engraved on panch-dhatu (5-metal alloy), worshipped Saturday facing south-west with blue flowers and black sesame.",
        charity="Mustard oil, blue-black cloth, coconut, sesame seeds, blanket. Offer to lepers, outcasts, or homeless on Saturday sunset.",
        sacred_plants="Chandan (sandalwood), Durva grass, blue lotus. Feed dogs (Rahu's animal) with roti and mustard oil on Saturdays.",
        puja="Ganesha puja every Wednesday morning (the classical Rahu antidote); Durga Saptashati during Rahu dasha; Kaal Bhairav worship at dusk.",
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
        rudraksha="4-mukhi (Chatur-mukhi) — sacred to Brahma (Mercury's overlord). Wear on green thread Wednesday sunrise after Budha mantra.",
        yantra="Budha Yantra — engraved on bronze or silver, worshipped Wednesday facing north with green flowers and durva grass.",
        charity="Green vegetables, moong daal, bronze utensils, green cloth, books, pens. Offer to young students, scholars, or schools on Wednesday.",
        sacred_plants="Doob grass (durva), apamarga (chirchita), green tulsi, Vishnukranti (dwarf morning glory). Feed grass to cows on Wednesdays.",
        puja="Vishnu-Lakshmi worship Wednesday; Vishnu Sahasranama with tulsi leaf offering; feed green fodder to cows; recite Budha stotra 108 times.",
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
        rudraksha="6-mukhi (Chha-mukhi) — sacred to Kartikeya (Venus's disciple); 13-mukhi acceptable for luxury and charm. Wear on white silk Friday morning.",
        yantra="Shukra Yantra — engraved on silver, worshipped Friday morning facing south-east with white/pink flowers and kheer offering.",
        charity="Sugar, curd, white silk cloth, silver, cosmetics, perfume, jasmine flowers. Offer to young women or newly-married girls on Friday.",
        sacred_plants="Rose, jasmine (chameli), cardamom, lotus, jai. Grow white/pink flowers at home; offer to Lakshmi during her puja.",
        puja="Lakshmi puja Friday evening with 108 white lotus/jasmine flowers; Shri Suktam recitation; offer sweet kheer to Lakshmi; Kanya-bhojan monthly.",
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
        rudraksha="9-mukhi (Nau-mukhi) — sacred to Durga (Ketu's remedy deity). Wear on mixed multicoloured thread Tuesday morning after Ketu mantra.",
        yantra="Ketu Yantra — engraved on panch-dhatu, worshipped Tuesday facing south-west with sesame seeds and black lentils.",
        charity="Black sesame, iron, black blanket, ash-grey cloth, blankets. Offer to sadhus, ascetics, sanyasis on Tuesday or Saturday.",
        sacred_plants="Kusha grass, ashwagandha, ash-coloured tree bark. Feed dogs; offer sesame + black lentils under peepal tree on Saturdays.",
        puja="Ganesha Sankashti Chaturthi vrat monthly (4th day of Krishna Paksha); Narasimha worship Tuesday morning; Kaal Bhairav puja at dusk.",
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
        rudraksha="7-mukhi (Sapt-mukhi) — sacred to Saptamatrika; 14-mukhi (Chaudah-mukhi) for accelerated Shani-remediation. Wear on black thread Saturday sunset.",
        yantra="Shani Yantra — engraved on iron or panch-dhatu, worshipped Saturday facing west with mustard oil lamp and black sesame.",
        charity="Iron, mustard oil, black clothes, urad daal, black sesame, iron nails, blankets. Offer to poor, aged, disabled on Saturday. Feed crows daily.",
        sacred_plants="Shami (khejri) — most sacred to Shani; light mustard-oil lamp under it on Saturday. Peepal for shani parikrama; sesame plant.",
        puja="Hanuman Chalisa daily (Hanuman is Shani's protector); Shani Chalisa every Saturday; peepal-parikrama 7 times Saturday morning; Shani-tail-abhishek at Shani temple.",
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
        rudraksha="3-mukhi (Tri-mukhi) — sacred to Agni (Mars's fire element). Wear on red thread Tuesday sunrise after Mars mantra.",
        yantra="Mangal Yantra — engraved on copper plate, worshipped Tuesday morning facing south with red hibiscus and sindoor.",
        charity="Red lentils (masoor), copper vessels, red cloth, red flowers, jaggery, sindoor. Offer to soldiers, security guards, brothers on Tuesday.",
        sacred_plants="Khejri (shami), red hibiscus, arjuna, khadira (catechu). Offer red hibiscus garland to Hanuman on Tuesday.",
        puja="Hanuman Chalisa 5 or 11 times Tuesday morning; sindoor tilak to Hanuman-ji; Sundara Kanda recitation weekly; feed monkeys on Tuesdays.",
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


# ─── Rich Life Path profiles (Johari §4 per-planet chapters) ─────────
# What a real numerologist would say to a client after computing their
# Life Path number. Extracted from knowledge/numerology.md §4.
_PROFILES: dict[int, LifePathProfile] = {
    1: LifePathProfile(
        number=1, planet="Sun", planet_sanskrit="Surya",
        character="Kingly and mission-driven. You need to lead and to build something original — following someone else's path will always feel wrong. You have clear opinions and defend them fiercely; the very traits that make you a natural leader also make you difficult to compromise with. Attention and respect matter to you, and you're willing to work hard to earn both.",
        strengths=("Natural leadership", "Clear decision-making", "Hardworking and creative", "Positive outlook",
                    "Enthusiasm for mission", "Ability to originate ventures"),
        weaknesses=("Irritability when crossed", "Deep dislike of criticism", "Obstinacy", "Needs praise to feel seen",
                     "Can dominate rooms without meaning to", "Spendthrift tendencies (luxurious tastes)"),
        health="Sun rules circulation and the heart — expect blood pressure concerns after 50, eye strain, occasional hospitalisation after 56. Pitta-dominant constitution: avoid excessive heat, spicy food, and long fasts. Cooling foods (coconut water, ghee, sweet fruits) balance the fire.",
        career="You do best when you own or lead — starting something, running a department, being the visible face of a project. Employment under someone with weak leadership drains you fast. Career peaks between ages 35-49 when authority naturally comes to you.",
        career_fields=("Politics", "Government leadership", "Business ownership", "Executive roles",
                       "Public speaking / broadcasting", "Gold / jewellery trades",
                       "Any role that puts you in front of others as authority"),
        best_partners=(1, 2, 4, 7),
        worst_partners=(6, 8, 5),  # 6=deceptively-friendly, 8=Saturn slows, 5=unstable
        peak_period="35–49 years (Sun's own dasha equivalent — authority and recognition naturally arrive)",
        strong_months="Mar 21 – Apr 28 (Sun-in-Aries strength); Jul 10 – Aug 20 (Sun-in-Cancer/Leo)",
        weak_months="Dec 21 – Feb 19 (Sun-in-Sagittarius/Capricorn is heavier; avoid launching new ventures)",
        good_dates=(1, 4, 10, 13, 19, 22, 28, 31),
        exalted_dates=(28,),   # Compound 28 is exalted 1 per Johari §5
        best_day="Sunday (or Monday if it falls on the 19th or 28th)",
        life_challenges="Your biggest lifelong lesson is learning to receive criticism without collapsing into defensiveness. The Sun burns brightest but also burns out — you'll cycle through periods of pushing too hard and needing to rest. Marriage often carries friction because you don't compromise easily; women with Life Path 1 particularly may face difficulty finding partners who don't feel threatened by their strength.",
    ),
    2: LifePathProfile(
        number=2, planet="Moon", planet_sanskrit="Chandra",
        character="Gentle, tender, and deeply emotional — you feel what others feel, often before they say it out loud. Queen-like attractiveness regardless of gender; a magnetic softness that draws people in. You do your best work in cooperation, not competition, and your instinctive intelligence is emotional rather than logical.",
        strengths=("Deep empathy", "Aesthetic sense", "Adaptability", "Natural mediator",
                    "Intuitive with people", "Excellent memory for feelings and relationships"),
        weaknesses=("Indecisiveness (weighing everyone's needs)", "Moodiness tied to lunar cycles",
                     "Dependency on partners", "Timidity in confrontation", "Worry and rumination",
                     "Quick-changing states"),
        health="Water-retention, breathing/lung sensitivity, mental strain, insomnia. Kapha-dominant with lunar sensitivity — full-moon days often bring emotional intensity or sleep disruption. Rudraksha bead traditionally supports.",
        career="You thrive in supportive, collaborative, or artistic work. Solo hustle grinds you down; the right partner or team amplifies you. Career unfolds gradually — you're a slow-blooming steady-across-life type, not a burst-early type.",
        career_fields=("Nursing / caregiving", "Counselling / therapy", "Diplomacy / mediation",
                       "Interior design / aesthetics", "Music / dance / poetry", "Hospitality",
                       "Anything involving water — sailing, coastal work, hydrology"),
        best_partners=(1, 2, 7, 8, 9),
        worst_partners=(3, 5),  # 3=advice-givers not partners, 5=Moon-Mercury enmity
        peak_period="Slow blooming; steady influence across life. No sharp peak — more a long even glow.",
        strong_months="Jul 20 – Aug 20 (Moon-in-Cancer's own house); full-moon periods generally",
        weak_months="New-moon periods and Krishna Paksha late-week may feel draining",
        good_dates=(2, 11, 20, 29),
        exalted_dates=(29,),
        best_day="Monday",
        life_challenges="You'll spend your life learning to say NO without crushing yourself with guilt. Moods that feel eternal at the time actually track the moon — you may need to structure life around your rhythms rather than fight them. Independence is hard-won because partnership feels so natural; the mid-life task is learning to stand alone without loneliness.",
    ),
    3: LifePathProfile(
        number=3, planet="Jupiter", planet_sanskrit="Guru / Brihaspati",
        character="Wise, spiritual, counsellor-natured. People come to you for advice and you rarely disappoint — you have a natural sense of the right thing to say. Expansive and generous, sometimes to your detriment (you say 'yes' to too many people and burn out fulfilling promises).",
        strengths=("Teaching gift", "Philosophical clarity", "Guidance", "Ethical instinct",
                    "Ability to see the bigger picture", "Natural authority in wisdom contexts"),
        weaknesses=("Self-centered when unchecked", "Over-committing (disappoints friends)",
                     "Preachy under stress", "Difficulty saying no", "Weight gain from Jupiter's expansive nature"),
        health="Wind/air disorders — gas, bloating, arthritis in later life. Heart trouble possible in old age. Vata-mixed-Pitta constitution. Rudraksha protective; regular oil massage recommended.",
        career="You do best in roles where wisdom + ethics matter more than raw execution — teaching, law, medicine, priesthood, publishing, higher education. Business works if it aligns with your values; purely profit-driven roles drain you.",
        career_fields=("Teaching / academia", "Law", "Medicine", "Priesthood / religious teaching",
                       "Publishing / editorial", "Higher education administration", "Ethics/compliance roles",
                       "Advisory consulting"),
        best_partners=(1, 3, 6, 9),
        worst_partners=(7, 5),  # 7=Jupiter-Ketu enmity; 5=Mercury-Jupiter tension
        peak_period="30s onward — Jupiter's wisdom compounds with age; Guru bala grows over decades",
        strong_months="Nov 22 – Dec 20 (Sun-in-Sagittarius); Feb 20 – Mar 20 (Sun-in-Pisces)",
        weak_months="May 21 – Jun 20 (Sun-in-Gemini stresses Jupiter's own dignity)",
        good_dates=(3, 6, 9, 12, 15, 18, 21, 24, 27, 30),
        exalted_dates=(12,),
        best_day="Thursday",
        life_challenges="Your challenge is boundary-setting. Because you genuinely care about everyone's growth, you take on too many mentees, students, friends-who-need-advice — and eventually you resent them for the very help you offered. Marriage works when your partner respects your teaching role rather than competing with it. Later in life, watch for the shift from wise-guide to preachy-authority — Jupiter's shadow.",
    ),
    4: LifePathProfile(
        number=4, planet="Rahu", planet_sanskrit="Rahu (North Node)",
        character="Rebellious, impulsive, secretive. You don't accept conventional wisdom easily — 'because that's how it's done' has never been a good reason for you. Revolutionary tendencies; you're drawn to what's forbidden or misunderstood, and sometimes society misunderstands YOU in return.",
        strengths=("Originality", "Resilience under criticism", "Independent thought",
                    "Reformer's zeal", "Ability to see what others miss", "Perseverance through opposition"),
        weaknesses=("Suspicion of others' motives", "Social isolation", "Short temper",
                     "Poor social circle if unchecked", "Tendency to violence if very angered (esp. birth-date 31)"),
        health="Nervous system sensitivity, unexpected accidents, chronic conditions with sudden onset. Vata-dominant. Extra care with electrical/mechanical safety. Yoga and grounding practices (walking barefoot on earth) crucial.",
        career="You do best in roles that break convention — technology innovation, unconventional research, foreign markets, work with marginalised communities. Government/traditional-corporate ladders frustrate you.",
        career_fields=("Technology / R&D", "Foreign services / international business", "Investigative journalism",
                       "Social reform / activism", "Occult / alternative healing", "Aviation",
                       "Chemical / photographic / electrical industries"),
        best_partners=(1, 6, 4),
        worst_partners=(3, 5, 9),  # 9 Mars-enemy
        peak_period="Later life — Rahu's rewards come after age 40, often after significant early struggle",
        strong_months="Late January – early February (Rahu's own transit windows vary; ephemeris-dependent)",
        weak_months="Periods immediately following an eclipse are personally destabilising for Rahu-natives",
        good_dates=(4, 13, 22, 31),
        exalted_dates=(31,),
        best_day="Saturday",
        life_challenges="Your central challenge is trust. Rahu creates a lifelong pull between wanting deep connection and never quite believing others' motives. Marriage takes work — you often unconsciously choose partners who confirm your suspicions rather than dissolve them. Life-lesson: distinguish between healthy scepticism and self-isolating paranoia. Number 13 births especially need active non-violence practice.",
    ),
    5: LifePathProfile(
        number=5, planet="Mercury", planet_sanskrit="Budha",
        character="Intelligent, mercurial, quick-witted — you process information faster than most, and you love learning for its own sake. Princely quality; comfortable in many worlds. You take risks that feel calculated to you but reckless to observers.",
        strengths=("Communication skills", "Adaptability", "Rapid learning",
                    "Business acumen", "Social intelligence", "Comfort in media / writing / trading"),
        weaknesses=("Anxiety spikes", "Low-confidence periods", "Over-thinking",
                     "Restlessness that becomes distraction", "Nervous energy that exhausts self and others"),
        health="Nervous exhaustion, digestive issues (Mercury rules the digestive tract in Kalapurusha). Often 'feels weak and sad' because Mercury sits close to Sun in the zodiac — you're pulled by other people's stronger energies. Regular grounding + adequate sleep are non-negotiable.",
        career="You thrive in communication + intellectual work. Sales, media, tech, teaching all work. Anything requiring long stretches of focused single-task attention (like manual labour or dense back-office work) drains you.",
        career_fields=("Writing / journalism / editing", "Teaching / training", "Communications / PR",
                       "Trading / stock markets", "Media / broadcasting", "Sales", "Technology",
                       "Publishing", "Business analysis"),
        best_partners=(1, 3, 5, 6),
        worst_partners=(2, 7, 8),  # 2 Moon-Mercury enmity; 7 Ketu weakens; 8 slows
        peak_period="Career often peaks in 30s-40s once nervous energy is channelled into focused output",
        strong_months="May 21 – Jun 20; Aug 23 – Sep 22 (Sun-in-Gemini/Virgo — Mercury's own dignity)",
        weak_months="Feb 20 – Mar 20 (Sun-in-Pisces where Mercury debilitates)",
        good_dates=(5, 14, 23),
        exalted_dates=(23, 32),
        best_day="Wednesday",
        life_challenges="Your challenge is nervous-system regulation. The same quick-processing that makes you brilliant also makes you prone to anxiety spirals. Marriage/partnership often struggles because you get bored easily and change directions faster than partners can follow. Life-work: develop a body-based practice (yoga, dance, martial arts, running) — your mind alone will not save you.",
    ),
    6: LifePathProfile(
        number=6, planet="Venus", planet_sanskrit="Shukra",
        character="Romantic, sensual, sweet-spoken, diplomatic. Slow to act but graceful when you do. Deeply aesthetic — you notice beauty and craftsmanship others miss. The 'universal friend' number — you can bridge groups that don't naturally get along.",
        strengths=("Relationship-building genius", "Aesthetic taste", "Harmony-creation",
                    "Artistic ability", "Comfort in luxury-industries", "Diplomacy under conflict"),
        weaknesses=("Slow to act when action is needed", "Over-indulgence in comfort/food/pleasure",
                     "Manipulative when insecure", "Procrastinates decisions",
                     "Can become overly attached to sensual pleasure"),
        health="Kidneys, reproductive system, throat sensitivity, weight gain from over-indulgence in sweet/rich food. Kapha-with-Pitta. Ayurvedic recommendation: bitter greens + fasting one day per week to counter Venus's love of sweetness.",
        career="You excel where beauty, harmony, and human relationships intersect. Design, arts, entertainment, jewellery, fashion, cosmetics, luxury goods all resonate. Cold analytical roles (accounting, hard science, engineering) drain your spirit.",
        career_fields=("Interior design", "Fashion / cosmetics / beauty industry", "Arts / entertainment",
                       "Jewellery / luxury goods", "Hospitality / hotel management", "Relationship counselling",
                       "Wedding planning", "Perfumery"),
        best_partners=(4, 8, 9, 3),
        worst_partners=(5, 7),  # 5=both moody, 7=introversion clash
        peak_period="Steady arc — Venus never has a single peak, but 40s often bring the material rewards of earlier relationship-building",
        strong_months="Apr 20 – May 20; Sep 23 – Oct 22 (Sun-in-Taurus/Libra — Venus's own signs)",
        weak_months="Aug 23 – Sep 22 (Sun-in-Virgo where Venus debilitates)",
        good_dates=(3, 6, 9, 12, 15, 18, 21, 24, 27, 30),
        exalted_dates=(24, 33),
        best_day="Friday",
        life_challenges="Your challenge is self-discipline around comfort. Venus loves ease, and 6-natives often let promising ventures die by delaying difficult decisions. Marriage brings both your greatest joy and your greatest complications — you attract partners easily but sometimes fail to choose consciously. Later-life lesson: pleasure is fine, but life-force flows through what you build, not what you consume.",
    ),
    7: LifePathProfile(
        number=7, planet="Ketu", planet_sanskrit="Ketu (South Node)",
        character="Mystical, dreamlike, intuitive, inventive. You've always felt slightly out of step with the material world — like part of you is somewhere else. Drawn to spirituality, healing arts, occult sciences, or research; happier alone than in a crowd.",
        strengths=("Psychic sensitivity", "Research/analytical depth", "Spiritual capacity",
                    "Meditation aptitude", "Inventive intelligence", "Ability to see hidden patterns"),
        weaknesses=("Dreamy escapism when reality is hard", "Difficulty grounding into practical action",
                     "Frequent misunderstandings with others (you speak a different language)",
                     "Isolation that curdles into loneliness", "Indecision from seeing too many possibilities"),
        health="Nervous system, environmental allergies, insomnia. Sensitive to noise, crowds, artificial light. Vata-dominant. Regular time in nature is medicine; screens and cities drain you faster than they drain most people.",
        career="You do best in solitary intellectual/spiritual work. Research, philosophy, healing, occult sciences, priesthood/monastic life, writing all fit. High-social sales/marketing roles will exhaust you within years.",
        career_fields=("Research / R&D", "Philosophy / academic writing", "Healing arts (Ayurveda, Reiki, energy work)",
                       "Astrology / occult", "Priesthood / monastic life", "Writing / poetry",
                       "Contemplative photography / documentary work"),
        best_partners=(1, 2, 3, 9),
        worst_partners=(4, 7),  # 4=mutual attraction with instability; 7=troublesome with self
        peak_period="Later life — 40s and beyond when spiritual maturity is respected rather than dismissed",
        strong_months="Sun in Ketu-friendly windows varies year-to-year (ephemeris-dependent)",
        weak_months="Sun-in-Cancer / Leo periods when material demands feel heaviest",
        good_dates=(7, 16, 25),
        exalted_dates=(25, 34),
        best_day="Tuesday (some traditions Sunday)",
        life_challenges="Your challenge is grounding without losing your gift. Society pushes 7-natives toward more 'productive' work, and many spend their 20s-30s trying to be someone they're not before returning to their true nature. Marriage is complicated — you need a partner who respects your solitude and doesn't try to 'fix' your introversion. Number 16 births especially need active accident-awareness (falls, height, water).",
    ),
    8: LifePathProfile(
        number=8, planet="Saturn", planet_sanskrit="Shani",
        character="Wise-through-struggle, laborious, disciplined. Nothing comes easy to you — everything worth having has to be earned twice. Slow-burning success; early life often carries poverty or hardship, and by mid-life you've built structures that outlast most people's careers.",
        strengths=("Endurance beyond most people's imagination", "Rock-solid work ethic",
                    "Ability to withstand major loss without breaking",
                    "Long-term strategic thinking", "Service orientation toward the downtrodden"),
        weaknesses=("Melancholy that lingers", "Slow progress that others take as failure",
                     "Poverty in early decades common", "Feels victim of others' cruelty",
                     "Stigmatised — often the person society misjudges"),
        health="Joints, bones, teeth, digestive-blocking. Chronic conditions common — arthritis, osteoporosis, dental issues. Vitamin A/D/E, calcium, iron supplementation traditionally advised. Vata-dominant. Ayurvedic gem-powders (pearl-powder, Neelam-pishti) supportive.",
        career="You do best in politics, social work, iron/steel/mining, law enforcement, hard sciences, real estate, agriculture, and service-oriented professions. Anything requiring you to grind through years of unappreciated work before recognition arrives.",
        career_fields=("Politics", "Social work / NGO leadership", "Iron / steel / mining industries",
                       "Law enforcement / judiciary", "Hard sciences (physics, chemistry, geology)",
                       "Real estate", "Agriculture / farming", "Servitude professions where dedication matters more than credentials"),
        best_partners=(1, 3, 5, 6),
        worst_partners=(4, 8, 9),  # avoid for marriage per Johari
        peak_period="After age 40 — fame and wealth typically arrive late. Anything before 35 is preparation, not payoff.",
        strong_months="Jan 21 – Feb 19 (Sun-in-Capricorn/Aquarius — Saturn's own signs)",
        weak_months="Apr 20 – May 20 (Sun-in-Taurus where Saturn's influence weakens for 8-natives)",
        good_dates=(8, 17, 26),
        exalted_dates=(26, 35),
        best_day="Saturday",
        life_challenges="Your central challenge is not internalising society's dismissal of you. 8-natives are frequently misjudged as 'unlucky' or 'behind schedule' when in fact they're playing a longer game. Marriage requires exceptional care — Johari specifically warns 26-borns to avoid marrying 4, 8, or 9. The mid-life shift from being misunderstood to being respected is your reward for patience.",
    ),
    9: LifePathProfile(
        number=9, planet="Mars", planet_sanskrit="Mangal",
        character="Warlike, strong, martial, doubting, perfectionist. You have a warrior's spirit — competitive, courageous, protective. Discriminating: quick to identify problems and quick to want to fix them. Anger management is your lifelong practice.",
        strengths=("Courage under pressure", "Protective instinct toward family/team",
                    "Athletic ability", "Leadership in crisis", "Ability to make hard decisions"),
        weaknesses=("Anger that flashes and burns", "Self-doubt paradoxically alongside confidence",
                     "Alienates people through directness", "Restlessness",
                     "Difficult marriage (especially Mars-Venus tension) — needs careful partner selection"),
        health="Bile-dominated. Prone to fevers of all kinds, blood disorders, accidents, burns. Pitta strong. Cooling practices essential — regular swimming, coconut water, ghee, less spicy food than you naturally crave.",
        career="You do best in sports/military/rescue — anywhere physical courage is rewarded. Also engineering and mechanical trades. Corporate desk-jobs make you into a tense, angry version of yourself.",
        career_fields=("Military / defence", "Police / law enforcement", "Surgery", "Athletics / sports",
                       "Engineering (mechanical, civil)", "Fire service / first responder",
                       "Metal / weapons trades", "Rescue / emergency services"),
        best_partners=(1, 3, 6),  # 6 women ideal for 9 men per Johari
        worst_partners=(5, 7, 9),
        peak_period="Late 20s to late 40s — Mars energy peaks and channels into achievement. Rise after 40 especially strong for 18-borns.",
        strong_months="Mar 21 – Apr 28 (Sun-in-Aries — Mars's own sign); Oct 23 – Nov 22 (Sun-in-Scorpio)",
        weak_months="Jun 21 – Jul 22 (Sun-in-Cancer where Mars debilitates)",
        good_dates=(9, 18, 27),
        exalted_dates=(27, 36),
        best_day="Tuesday",
        life_challenges="Your lifelong practice is anger management. Not suppressing it — Mars energy suppressed becomes illness — but channeling it into constructive action rather than corrosive reactions. Marriage is complicated: you attract partners who challenge you, and you need to distinguish between challenges that grow you and dynamics that destroy you. Number 6 women (Venus) are Johari's ideal partner for 9-men; number 3 men (Jupiter) for 9-women.",
    ),
}


# ─── Number compatibility (Johari §7 per-pair rules) ─────────────────
# Reduced to 3-tier per-pair table: 'friend' / 'enemy' / 'neutral'.
# Friend pairs have flowing energy but sometimes lack the friction to
# grow; enemy pairs feel abrasive but produce growth-through-alertness.
# Johari's framing: "friend numbers relax and stop progress; enemy
# numbers create alertness and activity — enemies are actually friends
# for growth." Take these as descriptions of dynamic, not verdicts.
_FRIEND_PAIRS: set[frozenset[int]] = {
    frozenset({1, 1}), frozenset({1, 2}), frozenset({1, 4}),
    frozenset({2, 7}), frozenset({2, 8}), frozenset({2, 9}),
    frozenset({3, 3}), frozenset({3, 6}), frozenset({3, 9}),
    frozenset({4, 6}), frozenset({4, 8}),
    frozenset({5, 5}), frozenset({5, 6}), frozenset({1, 3}),
    frozenset({6, 6}), frozenset({6, 8}), frozenset({6, 9}),
    frozenset({1, 7}), frozenset({3, 7}), frozenset({7, 9}),
    frozenset({1, 8}), frozenset({3, 8}), frozenset({5, 8}),
    frozenset({1, 9}), frozenset({1, 5}),
}
_ENEMY_PAIRS: set[frozenset[int]] = {
    frozenset({1, 6}),  # deceptive friendship
    frozenset({2, 3}), frozenset({2, 5}),
    frozenset({3, 5}),
    frozenset({4, 3}), frozenset({4, 5}), frozenset({4, 9}),
    frozenset({5, 2}), frozenset({5, 7}),
    frozenset({6, 5}), frozenset({6, 7}),
    frozenset({7, 4}), frozenset({7, 7}), frozenset({7, 8}),
    frozenset({8, 8}), frozenset({8, 9}),
    frozenset({9, 5}), frozenset({9, 9}),
}
_MARRIAGE_BEST = {frozenset({1, 2}), frozenset({1, 4}), frozenset({3, 6}),
                    frozenset({3, 9}), frozenset({6, 9}), frozenset({2, 7})}
_MARRIAGE_AVOID = {frozenset({1, 8}), frozenset({4, 9}), frozenset({5, 7}),
                     frozenset({7, 7}), frozenset({8, 9}), frozenset({9, 9})}


def _pair_verdict(a: int, b: int) -> str:
    """Return 'friend' / 'enemy' / 'neutral' for two single-digit numbers.

    Master numbers (11/22/33) reduce to base for pair lookup.
    """
    if a in (11, 22, 33):
        a = {11: 2, 22: 4, 33: 6}[a]
    if b in (11, 22, 33):
        b = {11: 2, 22: 4, 33: 6}[b]
    pair = frozenset({a, b})
    if pair in _FRIEND_PAIRS:
        return "friend"
    if pair in _ENEMY_PAIRS:
        return "enemy"
    return "neutral"


def _marriage_verdict(a: int, b: int) -> str:
    """Return 'best' / 'avoid' / '' for the specific marriage context."""
    if a in (11, 22, 33):
        a = {11: 2, 22: 4, 33: 6}[a]
    if b in (11, 22, 33):
        b = {11: 2, 22: 4, 33: 6}[b]
    pair = frozenset({a, b})
    if pair in _MARRIAGE_BEST:
        return "best"
    if pair in _MARRIAGE_AVOID:
        return "avoid"
    return ""


@dataclass(frozen=True)
class CompatibilityReading:
    """Two-person numerological compatibility per Johari §7."""
    person_a_name: str
    person_a_life_path: int
    person_a_birthday: int
    person_a_destiny: int
    person_b_name: str
    person_b_life_path: int
    person_b_birthday: int
    person_b_destiny: int

    life_path_verdict: str      # 'friend' / 'enemy' / 'neutral'
    birthday_verdict: str
    destiny_verdict: str

    marriage_verdict: str       # 'best' / 'avoid' / ''
    overall_score: int          # 0-100, weighted
    overall_summary: str        # human paragraph


def compute_compatibility(name_a: str, birth_date_a: str,
                            name_b: str, birth_date_b: str,
                            context: str = "general") -> CompatibilityReading:
    """Compute numerological compatibility between two people per Johari §7.

    Context = "general" | "marriage" | "business". Marriage context
    additionally consults Johari's marriage-specific pair table (§7 end).
    """
    from datetime import date as _date  # noqa: F401
    r_a = compute(name_a, birth_date_a)
    r_b = compute(name_b, birth_date_b)

    lp_v = _pair_verdict(r_a.life_path, r_b.life_path)
    bd_v = _pair_verdict(r_a.birthday, r_b.birthday)
    d_v = _pair_verdict(r_a.destiny, r_b.destiny)

    marriage_v = _marriage_verdict(r_a.life_path, r_b.life_path) if context == "marriage" else ""

    # Overall score — Life Path is weighted most (main theme), then Birthday,
    # then Destiny. Friend = full points; neutral = half; enemy = quarter.
    def _score(v: str, weight: int) -> int:
        return {"friend": weight, "neutral": weight // 2, "enemy": weight // 4}.get(v, 0)
    total = _score(lp_v, 50) + _score(bd_v, 30) + _score(d_v, 20)

    # Marriage-specific adjustments
    if context == "marriage":
        if marriage_v == "best":
            total = min(100, total + 15)
        elif marriage_v == "avoid":
            total = max(0, total - 25)

    # Summary paragraph
    tone = ("This is a supportive pairing — energies flow easily between you. "
            "Johari's caveat: friend-pairings can be TOO comfortable and stop growth. Introduce healthy challenge."
            if lp_v == "friend" else
            "This is a growth-through-friction pairing. Not easy, but productive. "
            "Enemy numbers force you both awake — Johari sees this as more valuable than comfort in the long run."
            if lp_v == "enemy" else
            "This is a neutral pairing — cooperation possible but requires conscious effort from both sides.")
    if context == "marriage":
        if marriage_v == "best":
            tone += " Classical marriage-favourable pair per Johari — one of the six pairings the text specifically endorses."
        elif marriage_v == "avoid":
            tone += " Classical marriage-avoid pair per Johari — extra care with communication, patience, and mutual respect required. Not impossible; just harder."

    return CompatibilityReading(
        person_a_name=r_a.name, person_a_life_path=r_a.life_path,
        person_a_birthday=r_a.birthday, person_a_destiny=r_a.destiny,
        person_b_name=r_b.name, person_b_life_path=r_b.life_path,
        person_b_birthday=r_b.birthday, person_b_destiny=r_b.destiny,
        life_path_verdict=lp_v, birthday_verdict=bd_v, destiny_verdict=d_v,
        marriage_verdict=marriage_v,
        overall_score=total,
        overall_summary=tone,
    )


def _get_profile(n: int) -> LifePathProfile | None:
    """Return LifePathProfile for n. Master numbers fall back to base."""
    if n in (11, 22, 33):
        n = {11: 2, 22: 4, 33: 6}[n]
    return _PROFILES.get(n)


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
# year for the person. Cycles 1-9. Fully reduced — never 11/22/33, per
# knowledge/numerology.md §12.8 and the page's own "Cycles 1-9" caption
# (issue #169).
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
    # No 11/22/33 rows: _personal_year reduces fully to 1-9 (knowledge/
    # numerology.md §12.8, issue #169), so those keys were unreachable. Do not
    # re-add them — an unreachable interpretation row is how #146's abujha
    # table rotted. If a master-year reading is ever wanted, it needs a
    # decision on the caption and on the score's branches first, not a
    # silently restored row.
}


def _personal_year(birth_date: str, target_year: int) -> int:
    """Compute Personal Year Number for a given target year (Kumar Ch.1).

    Formula: (birth month digits sum) + (birth day digits sum) +
             (target year digits sum), then reduce fully to 1-9.

    Masters are NOT preserved: the corpus gives the personal year cycle a
    range of 1-9 (§12.8), and the panel that renders this captions itself
    "Cycles 1-9" — so an 11 or 22 escaping into it labels a row the caption
    says cannot exist, and matches no branch of the scoring term (#169).

    Note on the variant used here: Kumar writes the formula with the literal
    month and day, `int(mo) + int(d) + year`, where this code sums their
    digits. Digit-summing preserves value mod 9, so under full reduction the
    two forms always give the same answer — an equivalence that holds only
    because masters are dropped. Preserve them and the forms diverge.
    """
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
    if not m:
        return 0
    _, mo, d = m.groups()
    month_sum = sum(int(x) for x in mo)
    day_sum = sum(int(x) for x in d)
    year_sum = sum(int(x) for x in str(target_year))
    return _reduce(month_sum + day_sum + year_sum, preserve_masters=False)


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
        # NOTE (#162 -> #161): this expression matches neither _life_path's
        # intermediate (now the sum of ALL DOB digits) nor the old one. It already
        # matched neither before this change — that is issue #161 defect (c),
        # which owns the reconciliation. Deliberately left alone here so this
        # bundle's Bhagya-score movement stays measurable to the Life Path and
        # Personal Year terms only. Do not "fix" it in passing.
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
    """Reduce day-of-month to 1-9 (Kumar Birthday / Johari Psychic / Mulank).

    Masters are NOT preserved. The corpus states the range as 1-9 outright
    (§2.1), and Johari ch.2 defines it as "obtained by making a simple whole
    number of the date of birth" (plain `pdftotext` lines 273-275) — a simple
    whole number, with no master exception attached.

    So days 11, 22 and 29 give 2, 4 and 2. That matches §4's own birthday
    lists, which file 11 and 29 under psychic number 2 and 22 under 4; keeping
    the masters here produced numbers that appear in no list on the page and
    had nothing to render against (#164).
    """
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", birth_date or "")
    if not m:
        return 0
    _, _, d = m.groups()
    return _reduce(int(d), preserve_masters=False)


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


def _reduce(n: int, *, preserve_masters: bool) -> int:
    """Reduce to a single digit, optionally stopping at 11, 22 or 33.

    `preserve_masters` is keyword-only and has NO default on purpose. The four
    call sites in this module do not agree: personal year and birthday number
    must land in 1-9 (their own tables and captions say so), letter-value
    numbers keep the masters, and Life Path keeps them only on the final
    total. A default would silently hand the next call site whatever policy
    happened to be written here — which is exactly the defect issues #162,
    #164, #169 and #179 are about. Making it explicit forces the choice to be
    made and named at each site.
    """
    while n > 9 and not (preserve_masters and n in (11, 22, 33)):
        n = sum(int(d) for d in str(n))
    return n


def _sum_letters(letters: str, table: dict[str, int]) -> int:
    """Sum letter values, then reduce — master numbers KEPT.

    These are Chaldean/Pythagorean letter-value numbers (Destiny, Soul Urge,
    Personality, Name), where 11/22/33 are part of the framework rather than
    an unreduced intermediate, so they survive the reduction. The page states
    this convention so the reader knows which one produced their number.

    §8's suggested "let the user choose whether to keep master numbers" toggle
    is deliberately NOT shipped (#179): a reader has no basis on which to pick
    a reduction convention, and offering the choice makes the site look
    uncertain about its own method. One convention, applied to everyone, named
    on the page. `preserve_masters` still exists as a parameter so adding a
    toggle later stays a call-site change rather than a rewrite.
    """
    total = sum(table.get(c, 0) for c in letters)
    return _reduce(total, preserve_masters=True) if total else 0


def _life_path(birth_date: str) -> int:
    """Life Path = sum of every digit in YYYYMMDD, reduced, masters kept.

    What the body does: take all eight digits of the date, add them, reduce
    to 1-9 unless the total settles on 11, 22 or 33. Previously the docstring
    said "sum of all digits" while the body reduced year, month and day
    separately and then summed those — the two are different methods, and
    that mismatch is half of #162.

    Source: Johari, *Numerology: With Tantra, Ayurveda, and Astrology*, ch.2
    "Destiny Number" — "The single whole number obtained from the addition of
    the date, month, and year of birth is called the destiny number" (plain
    `pdftotext` lines 299-300), with the worked example
    `5 + 1 + 2 + 1 + 9 + 3 + 4 = 25 = 7` at line 302, i.e. 1934-05-12 → 7.

    The tension, recorded rather than smoothed over: Goodwin, *Numerology:
    The Complete Guide, Vol. 1*, ch.3 "The Life Path" (lines 1861-1865, 1989-1991)
    teaches the reduce-parts-then-sum method we are leaving, and annotates the
    all-digits result "Incorrect. The master number has been lost."
    (lines 2026-2028). So the old code was legitimate mainstream *Western*
    practice, and by Goodwin's own lights the method we now use is wrong.
    This is a Vedic site, so it follows the Vedic corpus; Goodwin is cited
    here only as evidence that the previous behaviour was not a bug of
    ignorance.

    Masters ARE kept on the final total, so 1990-01-11 sums to 22 and stays
    22 (the old method gave 4).

    Scope of the change: a digit sum is congruent to its value mod 9, and
    11/22/33 ≡ 2/4/6, so the two methods can only ever differ by master-vs-
    base — never by which base number you land on. Profiles, remedies and
    compatibility verdicts key off the base number and are therefore
    unaffected.
    """
    digits = re.sub(r"[^0-9]", "", birth_date or "")
    if not digits:
        return 0
    return _reduce(sum(int(d) for d in digits), preserve_masters=True)


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
        life_path_profile=_get_profile(lp),
        life_path_remedy=_get_remedy(lp),
        personal_year=py,
        personal_year_theme=_PERSONAL_YEAR_THEME.get(py, ""),
        personal_year_target=ty,
        karmic_debt_numbers=karmic,
        name_compound=name_compound,
        name_compound_meaning=name_compound_meaning,
        lo_shu=compute_lo_shu_grid(birth_date),
    )
