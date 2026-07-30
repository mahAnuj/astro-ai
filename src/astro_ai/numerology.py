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
        life_path_profile=_get_profile(lp),
        life_path_remedy=_get_remedy(lp),
        personal_year=py,
        personal_year_theme=_PERSONAL_YEAR_THEME.get(py, ""),
        personal_year_target=ty,
        karmic_debt_numbers=karmic,
        name_compound=name_compound,
        name_compound_meaning=name_compound_meaning,
    )
