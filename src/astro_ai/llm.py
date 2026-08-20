"""Reading-generator functions — call providers.chat() with a per-feature prompt.

The system prompt is loaded from a file at request time (not module-import time)
so editing the prompt during development requires only a refresh — no restart.

Provider selection (Groq / Cerebras / Together / OpenAI / ...) and the
rate-limit fallback chain live in providers.py — every function here just
hands `messages` to providers.chat() and gets back text.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from astro_ai import providers

_log = logging.getLogger(__name__)
from astro_ai.chart import (
    Chart,
    DailyPanchang,  # used by daily reading + rashifal day-signal block
    DashaState,
    GocharImpact,
    LifeChapter,
    TransitEvent,
    TransitSnapshot,
    VedicFlags,
    compute_manglik_details,
    compute_yogas,
    format_dasha_for_prompt,
    format_events_for_prompt,
    format_flags_for_prompt,
    format_for_prompt,
    format_life_chapters_for_prompt,
    format_manglik_for_prompt,
    format_panchang_for_prompt,
    format_transit_for_prompt,
    format_yogas_for_prompt,
    format_topic_summaries_for_prompt,
    topic_summaries_for_chart,
    format_house_lords_for_prompt,
    format_planet_dignity_for_prompt,
    format_planet_nakshatras_for_prompt,
    format_aspects_for_prompt,
    format_navamsha_for_prompt,
    format_dashamsa_for_prompt,
)
from .learn_registry import ARTICLES

# Appended to the system prompt to switch the LLM's output language.
# UI strings stay English (full i18n deferred); only the reading text translates.
_LANG_SUFFIX: dict[str, str] = {
    "en": "",
    "hi": (
        "\n\n"
        "IMPORTANT: Respond entirely in Hindi using Devanagari script. "
        "Translate any section headings into Hindi as well "
        "(e.g. ## व्यक्तित्व, ## करियर और व्यवसाय, ## धन और समृद्धि, "
        "## संबंध और विवाह, ## स्वास्थ्य और कुशल-क्षेम, ## यात्रा और अवसर, "
        "## जीवन की अवस्थाएँ — and for outlooks, segment labels in Hindi). "
        "Use Sanskrit Vedic terms naturally: राशि, लग्न, ग्रह, नक्षत्र, भाव, "
        "मंगल दोष, साढ़े साती. The seeker reads Hindi; do not include any English. "
        "Any section heading must still begin with `## ` on its own line."
    ),
}


def _system_prompt(prompt_path: Path, lang: str, overlay_path: Path | None = None) -> str:
    """Load the file prompt, append an optional overlay, then the language suffix.

    `overlay_path` carries context-specific rules (see `ASK_OVERLAY_PATHS`) and
    is appended rather than substituted, so the shared voice/honesty/safety
    rules in the base prompt keep applying and live in only one file.

    The language suffix stays LAST. It instructs the model which language to
    answer in, and an overlay landing after it would bury that instruction in
    the middle of the system prompt.
    """
    base = prompt_path.read_text(encoding="utf-8")
    if overlay_path is not None:
        base += "\n" + overlay_path.read_text(encoding="utf-8")
    return base + _LANG_SUFFIX.get(lang, "")


@dataclass(frozen=True)
class BirthDetails:
    """Form-supplied seeker data. `name` is optional; everything else required."""

    name: str  # may be empty
    birth_date: str  # ISO YYYY-MM-DD
    birth_time: str  # HH:MM (24h, local)
    birth_place: str  # free-text city/country


_READING_TZ = ZoneInfo("Asia/Kolkata")


def today_anchor() -> str:
    """The line that tells the model what day it is. Put it in EVERY prompt.

    #192: this was in exactly one prompt builder — the per-rashi rashifal
    block — and absent from the other six. With a natal chart, a
    "CURRENT TRANSITS" section and a list of transit events but no statement
    of the date, the model falls back on its training prior and writes the
    reading for whatever year that prior lands in. `/yearly` was worst hit:
    a forward-looking twelve-month outlook anchored to a year already past.
    `_format_daily_message` even labelled sections "TODAY'S TRANSITS" while
    never saying what today was.

    The instruction is explicit rather than a bare date because a date alone
    is easy for a model to read as data rather than as the present moment;
    it needs telling that this supersedes what it thinks it knows.

    TIMEZONE: Asia/Kolkata, deliberately. The audience is Indian and the
    reading's "today" should be their today. `date.today()` would follow the
    server, which is UTC on Cloud Run — so for the ~5.5 hours between 18:30
    and midnight UTC it names yesterday from a Delhi reader's point of view.
    Every almanac module here (adhik_maas, lunar_observances, sankranti,
    lunar_dates) already uses Asia/Kolkata for exactly this reason; this
    matches them.
    """
    now = datetime.now(_READING_TZ)
    return (
        f"Today's date: {now.date().isoformat()} ({now.strftime('%A')}). "
        f"Treat this as the present moment. Do not rely on your training "
        f"cutoff to decide what year it is — this date is authoritative, and "
        f"any year you infer from your own priors is wrong."
    )


def generate_reading(
    details: BirthDetails,
    chart: Chart,
    flags: VedicFlags,
    life_chapters: list[LifeChapter],
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
    dasha_state: "DashaState | None" = None,
) -> str:
    """Sectioned natal reading. The 7th 'Life Stages' section uses life_chapters
    (the Mahadasha sequence framed as age windows) to ground age-based predictions.
    If `dasha_state` is passed, the current antardasha enriches the [NOW] chapter."""
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": _format_seeker_message(details, chart, flags, life_chapters, dasha_state)},
    ], route="natal")
    return content.strip()


def _format_seeker_message(
    details: BirthDetails,
    chart: Chart,
    flags: VedicFlags,
    life_chapters: list[LifeChapter],
    dasha_state: "DashaState | None" = None,
) -> str:
    """Render birth details + chart + flags + life chapters into the user message.

    Conditional Manglik block: the verdict is asserted exactly once, in the
    flags block; this block only adds supporting evidence (axes, cancellations,
    classical citations) and only when the chart actually triggers the dosha —
    keeping the per-call prompt small for the ~70% of charts that aren't Manglik.
    """
    name_line = f"Name: {details.name}" if details.name.strip() else "Name: (not provided)"
    # Reuse the details the flags were derived from so the two blocks can never
    # disagree. A hand-built VedicFlags may carry none (the field defaults), so
    # compute them once here and rebind `flags` to a copy carrying them: the
    # assertion in format_flags_for_prompt() below then reads the same object as
    # the evidence block, instead of seeing None and asserting "NO" over an
    # evidence block describing a real dosha. `replace` returns a new instance —
    # the caller's frozen VedicFlags is not mutated.
    if flags.manglik_details is None:
        flags = replace(flags, manglik_details=compute_manglik_details(chart))
    manglik_block = format_manglik_for_prompt(flags.manglik_details)
    yogas_block = format_yogas_for_prompt(compute_yogas(chart), chart=chart)
    # New chart-specific structured blocks (Issues #60 + #61 + #59) —
    # house-lord placements + planet dignity + nakshatra placements.
    # Deterministic per chart; cheap to compute.
    house_lords_block = format_house_lords_for_prompt(chart)
    dignity_block = format_planet_dignity_for_prompt(chart)
    nakshatras_block = format_planet_nakshatras_for_prompt(chart)
    aspects_block = format_aspects_for_prompt(chart)
    navamsha_block = format_navamsha_for_prompt(chart)
    dashamsa_block = format_dashamsa_for_prompt(chart)
    # Topic summaries — distilled article knowledge selected by chart features.
    # Cheap (~400 tokens for 3-5 summaries) and gives the LLM specific classical
    # depth PLUS cross-link destinations for the /learn/ articles.
    topic_summaries_block = ""
    if dasha_state is not None:
        summaries = topic_summaries_for_chart(chart, dasha_state, ARTICLES)
        topic_summaries_block = format_topic_summaries_for_prompt(summaries)
    optional_blocks = ""
    if house_lords_block:
        optional_blocks += f"\n\n{house_lords_block}"
    if dignity_block:
        optional_blocks += f"\n\n{dignity_block}"
    if nakshatras_block:
        optional_blocks += f"\n\n{nakshatras_block}"
    if aspects_block:
        optional_blocks += f"\n\n{aspects_block}"
    if navamsha_block:
        optional_blocks += f"\n\n--- D-9 NAVAMSHA ---\n{navamsha_block}"
    if dashamsa_block:
        optional_blocks += f"\n\n--- D-10 DASHAMSA ---\n{dashamsa_block}"
    if manglik_block:
        optional_blocks += f"\n\n{manglik_block}"
    if yogas_block:
        optional_blocks += f"\n\n{yogas_block}"
    if topic_summaries_block:
        optional_blocks += f"\n\n{topic_summaries_block}"
    return (
        f"{today_anchor()}\n"
        f"{name_line}\n"
        f"Birth date: {details.birth_date}\n"
        f"Birth time: {details.birth_time} (local time)\n"
        f"Birth place: {details.birth_place}\n"
        f"\n"
        f"{format_for_prompt(chart)}\n"
        f"\n"
        f"{format_flags_for_prompt(flags)}"
        f"{optional_blocks}\n"
        f"\n"
        f"{format_life_chapters_for_prompt(life_chapters, dasha_state.antardasha if dasha_state else None)}\n"
    )


def generate_outlook_reading(
    details: BirthDetails,
    natal: Chart,
    transit: TransitSnapshot,
    flags: VedicFlags,
    gochar_impacts: list[GocharImpact],
    events: list[TransitEvent],
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
) -> str:
    """Multi-week or multi-month outlook (used by /monthly and /yearly).

    Shape mirrors generate_daily_reading but accepts no Panchang (irrelevant
    for windows >1 day) and adds the slow-mover gochar impacts list, which
    is the primary signal at these timescales.
    """
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {
            "role": "user",
            "content": _format_outlook_message(details, natal, transit, flags, gochar_impacts, events),
        },
    ], route="outlook")
    return content.strip()


def _format_outlook_message(
    details: BirthDetails,
    natal: Chart,
    transit: TransitSnapshot,
    flags: VedicFlags,
    gochar_impacts: list[GocharImpact],
    events: list[TransitEvent],
) -> str:
    """User-message block: seeker + natal + transits + flags + gochar + events."""
    name_line = f"Name: {details.name}" if details.name.strip() else "Name: (not provided)"
    gochar_lines = ["Gochar impacts (slow movers, sign + house + favourability):"]
    for g in gochar_impacts:
        retro = " (retrograde)" if g.retrograde else ""
        gochar_lines.append(
            f"- {g.planet}{retro}: {g.sign} — natal house {g.house_from_lagna} from Lagna, "
            f"house {g.house_from_moon} from natal Moon. Favourability: {g.favorability}."
        )
    return (
        f"{today_anchor()}\n"
        f"{name_line}\n"
        f"Birth date: {details.birth_date}\n"
        f"Birth time: {details.birth_time} (local time)\n"
        f"Birth place: {details.birth_place}\n"
        f"\n"
        f"--- NATAL CHART ---\n"
        f"{format_for_prompt(natal)}\n"
        f"\n"
        f"--- CURRENT TRANSITS (start of window) ---\n"
        f"{format_transit_for_prompt(transit)}\n"
        f"\n"
        f"--- VEDIC FLAGS ---\n"
        f"{format_flags_for_prompt(flags)}\n"
        f"\n"
        f"--- GOCHAR IMPACTS ---\n"
        + "\n".join(gochar_lines) + "\n"
        f"\n"
        f"--- KEY TRANSIT EVENTS IN WINDOW ---\n"
        f"{format_events_for_prompt(events)}\n"
    )


def _format_numerology_for_prompt(reading) -> str:
    """Compact numerology summary for the /ask context block.

    Only surfaces the numbers + their names — the LLM's chart-based
    reasoning is still primary. This just lets it cross-reference when
    a user asks a numerology-flavoured follow-up.
    """
    # The name-derived numbers follow the reading's own letter table (#167),
    # so the label must come from the reading rather than being pinned.
    system_label = {"chaldean": "Chaldean"}.get(
        str(getattr(reading, "system", "") or "").lower()
    )
    name_number_line = (
        f"Name Number ({system_label}): {reading.name_number}"
        if system_label else f"Name Number: {reading.name_number}"
    )
    # The date-derived numbers are always valid. The name-derived four are
    # only valid if the name could be scored at all (#197) — for a saved
    # chart whose name is in Devanagari or any non-Latin script they are all
    # 0, and 0 is not a result, it is the absence of one. /ask takes the name
    # off the saved chart rather than a form, so unlike /numerology it can
    # reach that state, and it used to hand those zeros to the model as fact.
    parts = [
        f"Life Path: {reading.life_path} ({reading.life_path_meaning[:80]}…)"
        if reading.life_path_meaning else f"Life Path: {reading.life_path}",
        f"Birthday: {reading.birthday}",
    ]
    if getattr(reading, "name_scoreable", True):
        parts += [
            f"Destiny (Expression): {reading.destiny}",
            f"Soul Urge: {reading.soul_urge}",
            f"Personality: {reading.personality}",
            name_number_line,
        ]
    else:
        parts.append(
            "Name-derived numbers (Destiny, Soul Urge, Personality, Name "
            "Number): NOT AVAILABLE — the saved name is not written in the "
            "Latin alphabet, and these letter values are defined only over "
            "A-Z. Do not invent them, do not transliterate the name to "
            "produce them, and do not treat their absence as a result. The "
            "date-derived numbers above are unaffected and can be used."
        )
    parts.append(f"Personal Year: {reading.personal_year}")
    if reading.karmic_debt_numbers:
        parts.append(f"Karmic Debt numbers present: {', '.join(str(k) for k in reading.karmic_debt_numbers)}")
    parts.append("Framework note: these are modern-Western (Chaldean) constructs, not classical Vedic Jyotish.")
    return "\n".join(parts)


def _format_partner_chart_for_prompt(partner_chart) -> str:
    """Compact partner-chart summary for the /ask matching-context block."""
    return format_for_prompt(partner_chart)


def format_guna_milan_for_prompt(guna, pair_label: str | None = None) -> str:
    """Render a computed GunaMilan for the /ask matching block.

    Why this exists: `/matching` computed a full Ashtakoota analysis, showed it
    to the user, and then threw it away the moment they clicked Ask. The LLM
    received two raw charts and re-derived compatibility from planets alone,
    with none of the sourced koota scoring behind it — so the page and the
    answer could disagree about the same couple.

    The dosha objects are rendered with their parihāras BECAUSE the arithmetic
    is counter-intuitive and the model will otherwise "helpfully" correct it: a
    cancelled Bhakoot still scores 0, and no mitigation ever adds points. Both
    facts are stated inline so the prose cannot contradict the page.
    """
    lines = []
    if pair_label:
        # Name the couple inside the block. The seeker is not necessarily one
        # of them — they may have run a match for someone else — so an unlabelled
        # table of numbers invites the model to attribute them to whoever is
        # asking. Stating it removes the guess.
        lines.append(f"This is the Guna Milan for {pair_label}.")
    lines += [
        f"Total: {guna.total_awarded:g} / {guna.total_max} — "
        f"{guna.overall_verdict_label}",
        "Koota breakdown:",
    ]
    lines += [f"  - {k.name} ({k.sanskrit}): {k.awarded:g}/{k.max_points} — {k.note}"
              for k in guna.kootas]
    lines.append(
        f"Mangal Dosh: {'compatible' if guna.mangal_dosh_compatible else 'needs review'}"
        f" — {guna.mangal_dosh_note}"
    )

    bd = guna.bhakoot_dosha
    if bd.present:
        lines.append(f"Bhakoot dosha: {bd.name} — "
                     f"{'cancelled' if bd.cancelled else 'NOT cancelled'}")
        lines += [f"  parihara applying: {p}" for p in bd.pariharas]
        lines += [f"  not evaluated: {u}" for u in bd.unevaluated]
        if bd.cancelled:
            lines.append("  NOTE: a cancellation removes the dosha but does NOT add "
                         "points. The Bhakoot score above is already final.")
        if not bd.nadi_shuddha:
            lines.append("  NOTE: the tradition requires clean Nadi regardless of any "
                         "Bhakoot cancellation, and Nadi is not clean here.")

    nd = guna.nadi_dosha
    if nd.present:
        sev = "gravest form" if nd.grave else ("reduced" if nd.alpa else "present")
        lines.append(f"Nadi dosha: {nd.nadi} Nadi — {sev}")
        lines += [f"  mitigation: {m}" for m in nd.mitigations]
        lines.append("  NOTE: Nadi has NO cancelling conditions in this tradition and "
                     "gains no points from any mitigation.")

    return "\n".join(lines)


def generate_ask_answer(
    chart: Chart,
    dasha: DashaState | None,
    flags: VedicFlags | None,
    question: str,
    category: str,
    prompt_path: Path,
    lang: str = "en",
    numerology_reading=None,
    partner_chart: Chart | None = None,
    partner_label: str = "partner",
    guna_milan=None,
    guna_pair_label: str | None = None,
    overlay_path: Path | None = None,
) -> str:
    """Personalised free-form Q&A grounded in the seeker's chart.

    Provides chart + current dasha + flags as context so the LLM can
    ground its answer in the actual placements rather than generic
    planetary meanings. Question and category come from the user form.

    Optional context sources (each rendered as its own block when provided):
      - `numerology_reading` — NumerologyReading. Enables numerology-flavoured
        follow-ups from /numerology (a user asking "what does my Life Path
        say about career?" gets an answer that actually references their
        numbers, not just their chart).
      - `partner_chart` + `partner_label` — Chart of the second person in a
        Kundli match. Enables "is this a good match for career alignment?"
        style follow-ups from /matching that need BOTH charts.
    """
    chart_block = format_for_prompt(chart)
    dasha_block = format_dasha_for_prompt(dasha) if dasha else "(no dasha state)"
    flags_block = format_flags_for_prompt(flags) if flags else ""

    optional_blocks = ""
    if numerology_reading is not None:
        optional_blocks += (
            f"--- SEEKER'S NUMEROLOGY (modern Chaldean, NOT classical Jyotish — cross-reference only) ---\n"
            f"{_format_numerology_for_prompt(numerology_reading)}\n\n"
        )
    if partner_chart is not None:
        optional_blocks += (
            f"--- {partner_label.upper()}'S NATAL CHART ---\n"
            f"{_format_partner_chart_for_prompt(partner_chart)}\n\n"
        )
    if guna_milan is not None:
        optional_blocks += (
            f"--- ASHTAKOOTA COMPATIBILITY (already computed — quote these numbers, "
            f"do NOT recompute or estimate them) ---\n"
            f"{format_guna_milan_for_prompt(guna_milan, guna_pair_label)}\n\n"
        )

    user_message = (
        f"{today_anchor()}\n\n"
        f"--- SEEKER'S NATAL CHART ---\n{chart_block}\n\n"
        f"--- CURRENT DASHA ---\n{dasha_block}\n\n"
        f"{('--- VEDIC FLAGS ---' + chr(10) + flags_block + chr(10) + chr(10)) if flags_block else ''}"
        f"{optional_blocks}"
        f"--- QUESTION ---\n"
        f"Category hint: {category}\n"
        f"Question: {question.strip()}\n"
    )
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang, overlay_path)},
        {"role": "user", "content": user_message},
    ], route="ask")
    return content.strip()


def generate_dasha_deep_dive(
    chart: Chart,
    dasha: DashaState,
    prompt_path: Path,
    lang: str = "en",
) -> str:
    """Long-form personalised reading of the seeker's CURRENT (Maha + Antar) pair.

    The prompt asks the LLM to ground every interpretation in where the
    period lords actually sit in this seeker's chart — not generic
    "Saturn = discipline" boilerplate. Includes timeline + remedies.
    """
    user_message = (
        f"{today_anchor()}\n\n"
        f"--- SEEKER'S NATAL CHART ---\n"
        f"{format_for_prompt(chart)}\n"
        f"\n"
        f"--- CURRENT DASHA STATE ---\n"
        f"{format_dasha_for_prompt(dasha)}\n"
    )
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": user_message},
    ], route="dasha")
    return content.strip()


# 12 rashis in canonical order, each described with the classical facts
# (English + Sanskrit name, ruling planet/Swami, element/Tattva, quality/Guna)
# plus a per-rashi OPENING STYLE HINT — the second layer of the anti-
# convergence fix. Because the 12 LLM calls run in parallel and can't see
# each other's outputs, they all default to horoscope-boilerplate openings
# ("Today, you may feel..."). Passing each rashi a DIFFERENT opening-style
# instruction forces structural variety across the 12 outputs on the page.
# The style hint targets the rashi's own character — Aries opens with a
# body-image, Taurus with a sensory image, Gemini with a question, etc.
_RASHI_ANCHORS: tuple[dict[str, str], ...] = (
    {"en": "Aries",       "sa": "Mesha",       "lord": "Mars",    "element": "Fire",  "quality": "Movable",
     "opening_style": "This sign's day usually turns on MOMENTUM — what they start, push, or lose patience with. Lead the glance line with that."},
    {"en": "Taurus",      "sa": "Vrishabha",   "lord": "Venus",   "element": "Earth", "quality": "Fixed",
     "opening_style": "This sign's day usually turns on COMFORT AND MONEY — spending, saving, food, rest, pace. Lead the glance line with that."},
    {"en": "Gemini",      "sa": "Mithuna",     "lord": "Mercury", "element": "Air",   "quality": "Dual",
     "opening_style": "This sign's day usually turns on CONVERSATIONS AND CHOICES — messages, options, information they are sorting. Lead with that."},
    {"en": "Cancer",      "sa": "Karka",       "lord": "Moon",    "element": "Water", "quality": "Movable",
     "opening_style": "This sign's day usually turns on HOME AND FAMILY — who needs them, what the mood at home is. Lead the glance line with that."},
    {"en": "Leo",         "sa": "Simha",       "lord": "Sun",     "element": "Fire",  "quality": "Fixed",
     "opening_style": "This sign's day usually turns on RECOGNITION — being seen, credit, pride, how they carry themselves. Lead with that."},
    {"en": "Virgo",       "sa": "Kanya",       "lord": "Mercury", "element": "Earth", "quality": "Dual",
     "opening_style": "This sign's day usually turns on DETAIL AND HEALTH — what needs sorting, fixing, or looking after. Lead with that."},
    {"en": "Libra",       "sa": "Tula",        "lord": "Venus",   "element": "Air",   "quality": "Movable",
     "opening_style": "This sign's day usually turns on RELATIONSHIPS AND FAIRNESS — a person to balance, a decision between two goods. Lead with that."},
    {"en": "Scorpio",     "sa": "Vrishchika",  "lord": "Mars",    "element": "Water", "quality": "Fixed",
     "opening_style": "This sign's day usually turns on WHAT IS UNSAID — trust, privacy, something held back. Lead with that, plainly and without drama."},
    {"en": "Sagittarius", "sa": "Dhanu",       "lord": "Jupiter", "element": "Fire",  "quality": "Dual",
     "opening_style": "This sign's day usually turns on PLANS AND LEARNING — travel, study, belief, something opening up. Lead with that."},
    {"en": "Capricorn",   "sa": "Makara",      "lord": "Saturn",  "element": "Earth", "quality": "Movable",
     "opening_style": "This sign's day usually turns on WORK AND RESPONSIBILITY — what they are building, what they carry. Lead with that."},
    {"en": "Aquarius",    "sa": "Kumbha",      "lord": "Saturn",  "element": "Air",   "quality": "Fixed",
     "opening_style": "This sign's day usually turns on PEOPLE AND IDEAS — friends, groups, causes, being the different one. Lead with that."},
    {"en": "Pisces",      "sa": "Meena",       "lord": "Jupiter", "element": "Water", "quality": "Dual",
     "opening_style": "This sign's day usually turns on FEELING AND REST — intuition, tiredness, boundaries, absorbing others' moods. Lead with that."},
)


def _build_rashifal_day_signals(
    transit: TransitSnapshot,
    today_iso: str,
    lang: str,
    panchang: DailyPanchang | None,
    festival: dict | None,
) -> list[str]:
    """Compute the day-varying context block shared across all 12 per-rashi calls."""
    moon = next((p for p in transit.planets if p.name == "Moon"), None)
    # Rahu/Ketu are ALWAYS retrograde in Vedic convention — filter them out
    # so we only surface newsworthy retrogrades (Merc/Ven/Mars/Jup/Sat).
    retrogrades = [p.name for p in transit.planets
                    if p.retrograde and p.name not in ("Rahu", "Ketu")]

    # Uses the CALLER'S today_iso, not today_anchor(), on purpose (#192). The
    # transits and panchang in this same block were computed for that exact
    # date, so the prompt must name it or the reading would describe one day's
    # sky under another day's heading. today_anchor() derives its own date and
    # would desync here — it is for the builders that had no date at all.
    #
    # The instruction half is shared with today_anchor() because a bare date
    # reads as data; the model needs telling it supersedes its training prior.
    signals: list[str] = [
        f"Today's date: {today_iso}. Treat this as the present moment. "
        f"Do not rely on your training cutoff to decide what year it is — "
        f"this date is authoritative, and any year you infer from your own "
        f"priors is wrong."
    ]
    if panchang:
        signals.append(
            f"Weekday: {panchang.weekday} — ruled by {panchang.day_lord}. "
            f"Classical Vedic tradition treats this day's overall tone as "
            f"{panchang.day_lord}-coloured; that mood must shape today's reading."
        )
        tithi_note = (
            f"Today's tithi: {panchang.tithi_paksha} Paksha, {panchang.tithi_name}"
        )
        if panchang.tithi_significance:
            tithi_note += f" ({panchang.tithi_significance})"
        tithi_note += (
            ". Tithi shifts every ~24 hours and colours the day's karmic character."
        )
        signals.append(tithi_note)
    if moon:
        signals.append(
            f"Moon today: {moon.rashi} in {moon.nakshatra} nakshatra. "
            f"This is the fastest-changing sky signal — reference it if it fits."
        )
    if retrogrades:
        signals.append(
            f"Planets currently retrograde: {', '.join(retrogrades)}. "
            f"Their significations feel internal/reflective/second-look right now."
        )
    if festival:
        fname = festival.get(f"name_{lang}") or festival.get("name_en", "festival")
        fnote = festival.get(f"note_{lang}") or festival.get("note_en", "")
        signals.append(f"Today is {fname} — {fnote} Weave this in if it fits.")

    # Real clock windows, so the reading does not have to invent them.
    #
    # Both are already computed on the panchang this function receives and were
    # simply never forwarded — while the prompt instructed the model to "name a
    # specific part of the day when signing is best" and to close with a time
    # window. It could only do that by making a time up. An invented "after
    # 4 pm" traces to nothing, which is exactly what this repo's sourcing rule
    # exists to prevent.
    #
    # LOCATION IS STATED, NOT HIDDEN. The rashifal is one generic national
    # reading and its panchang is computed for Mumbai (routes/subscribe.py
    # builds a neutral Mumbai chart). Rahu Kaal shifts by tens of minutes
    # across India, so these are handed over as an IST reference to be given
    # approximately — never as an exact time for whoever is reading.
    if panchang is not None:
        rk_s = getattr(panchang, "rahu_kaal_start", None)
        rk_e = getattr(panchang, "rahu_kaal_end", None)
        ab_s = getattr(panchang, "abhijit_start", None)
        ab_e = getattr(panchang, "abhijit_end", None)
        if rk_s is not None and rk_e is not None:
            signals.append(
                f"Rahu Kaal today is roughly {rk_s.strftime('%-I:%M %p')} to "
                f"{rk_e.strftime('%-I:%M %p')} IST (Mumbai reference). Classically "
                "the window to avoid starting anything new. Give it approximately."
            )
        if ab_s is not None and ab_e is not None:
            signals.append(
                f"Abhijit Muhurat today is roughly {ab_s.strftime('%-I:%M %p')} to "
                f"{ab_e.strftime('%-I:%M %p')} IST (Mumbai reference). Classically the "
                "most auspicious window for starting or deciding. Give it approximately."
            )
    return signals


# Slug → canonical rashi index map. Accepts both English and Sanskrit
# spellings so URLs like /rashifal/aries and /rashifal/mesha both resolve.
RASHI_SLUG_TO_INDEX: dict[str, int] = {
    "aries": 0,       "mesha": 0,
    "taurus": 1,      "vrishabha": 1,   "vrish": 1,   "vrishab": 1,
    "gemini": 2,      "mithuna": 2,     "mithun": 2,
    "cancer": 3,      "karka": 3,       "kark": 3,
    "leo": 4,         "simha": 4,       "sinh": 4,
    "virgo": 5,       "kanya": 5,
    "libra": 6,       "tula": 6,
    "scorpio": 7,     "vrishchika": 7,  "vrischika": 7,
    "sagittarius": 8, "dhanu": 8,
    "capricorn": 9,   "makara": 9,      "makar": 9,
    "aquarius": 10,   "kumbha": 10,     "kumbh": 10,
    "pisces": 11,     "meena": 11,      "min": 11,
}

# Canonical URL slug for each rashi (lowercase English) — use in sitemap
# and hreflang building.  Index 0..11 = Mesha..Meena in classical order.
RASHI_CANONICAL_SLUGS: tuple[str, ...] = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)


def generate_rashifal_for_rashi(
    rashi_index: int,
    transit: TransitSnapshot,
    today_iso: str,
    prompt_path: Path,
    lang: str = "en",
    panchang: DailyPanchang | None = None,
    festival: dict | None = None,
) -> str:
    """Generate today's reading for ONE specific rashi.

    Fires exactly one LLM call using the per-rashi anchor + opening-style
    hint. Used by the on-demand flip-card flow (/rashifal/{rashi}) — the
    landing page renders 12 flip cards without any LLM traffic; when a
    user clicks a card, this fires the single call for that rashi and
    the result is cached for the rest of the day.

    Contrast with generate_rashifal() which fires all 12 in parallel — that
    path is kept for the email cron where all 12 must be pre-generated for
    a single subscriber blast.
    """
    if not 0 <= rashi_index < 12:
        raise ValueError(f"rashi_index must be in 0..11, got {rashi_index}")
    day_signals = _build_rashifal_day_signals(transit, today_iso, lang, panchang, festival)
    day_signals_block = "\n".join(f"- {s}" for s in day_signals)
    transit_block = format_transit_for_prompt(transit)
    return _generate_rashifal_single(
        _RASHI_ANCHORS[rashi_index], day_signals_block, transit_block, prompt_path, lang,
    )


def _generate_rashifal_single(
    anchor: dict[str, str],
    day_signals_block: str,
    transit_block: str,
    prompt_path: Path,
    lang: str,
    pacer: "_StartPacer | None" = None,
) -> str:
    """Generate a single rashi's daily reading — one LLM call, ~200 tokens output.

    Called 12× in parallel by generate_rashifal(). Each call is independent so
    the model can't lazily reuse phrasing across element-groups.

    `pacer` throttles the START of the call, not the call itself. It is None
    for the on-demand single-rashi path (`generate_rashifal_for_rashi`), where
    a user is waiting on one call and there is no burst to spread.
    """
    if pacer is not None:
        waited = pacer.wait()
        if waited > 0:
            _log.debug("rashifal pacer: waited %.1fs before %s", waited, anchor["en"])
    user_message = (
        f"RASHI TO WRITE FOR:\n"
        f"- Name: {anchor['en']} / {anchor['sa']}\n"
        f"- Ruling planet (Swami): {anchor['lord']}\n"
        f"- Element (Tattva): {anchor['element']}\n"
        f"- Quality (Guna): {anchor['quality']}\n"
        f"\n"
        f"OPENING STYLE HINT (CRITICAL — this is how you avoid opening with "
        f"'Today, you may feel...' like every other rashi will):\n"
        f"{anchor.get('opening_style', 'Open with a concrete image, not a generic feeling.')}\n"
        f"\n"
        f"TODAY'S SKY SIGNALS (use these to make the reading feel like TODAY):\n"
        f"{day_signals_block}\n"
        f"\n"
        f"Raw planetary positions (background context — do NOT recite):\n"
        f"{transit_block}\n"
        f"\n"
        f"Write ONLY the reading for {anchor['en']} / {anchor['sa']}. "
        f"Output must start with `## {anchor['en']} / {anchor['sa']}` then flowing prose. "
        f"Follow the opening-style hint above. Do not use any banned opening phrase."
    )
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": user_message},
    ], route="rashifal_single")
    return content.strip()


class _StartPacer:
    """Enforces a minimum gap between LLM call STARTS, across threads.

    Concurrency caps how many calls are in flight; this caps how fast they
    begin. Those are different controls and a token-per-minute limit needs the
    second one: two concurrent calls that each take 10s already respect a
    2-wide cap while starting 12 calls in 60s, which is far too fast for an
    8,000 TPM budget at ~3,587 tokens a call.

    Reserves its slot under the lock and sleeps OUTSIDE it, so N waiting
    threads queue up at N distinct times instead of all waking together — a
    sleep inside the lock would serialise the whole pool behind one waiter.
    Uses time.monotonic() so an NTP step cannot make a thread sleep for hours.
    """

    def __init__(self, min_interval_s: float) -> None:
        self._interval = max(0.0, min_interval_s)
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> float:
        """Block until this caller's slot. Returns the seconds actually slept."""
        if self._interval <= 0:
            return 0.0
        with self._lock:
            now = time.monotonic()
            due = max(now, self._next_at)
            self._next_at = due + self._interval
        delay = due - time.monotonic()
        if delay > 0:
            time.sleep(delay)
            return delay
        return 0.0


_RASHIFAL_CONCURRENCY = 2
"""Concurrent per-rashi LLM calls — how many may be IN FLIGHT at once."""

_RASHIFAL_MIN_INTERVAL_S = 10.0
"""Minimum seconds between per-rashi call STARTS. The other half of the TPM
budget, and the half concurrency cannot express.

The arithmetic, so the next person can re-derive it rather than trust it:
one rashifal call reserves ~3,587 tokens, so the 12-rashi job costs ~43,000.
Production runs four DISTINCT Groq models and Groq keys its free-tier quota per
model, so the ceiling is 4 x 8,000 = 32,000 tokens per minute. The job therefore
cannot complete in under 43,000/32,000 = ~81 seconds no matter how it is
scheduled. At 10s between starts it spans ~120s, which clears that with margin.

What this does NOT cover: the provider order is randomly shuffled per call, so
an unlucky run can land several calls on the same model and exceed that model's
individual 8,000. That case is caught by the retry-hint backoff in
providers.chat() — the two mechanisms are complementary, and removing either
re-opens the failure.

Set to 0.0 to disable (tests, or a paid tier with real headroom)."""


def generate_rashifal(
    transit: TransitSnapshot,
    today_iso: str,
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
    panchang: DailyPanchang | None = None,
    festival: dict | None = None,
) -> str:
    """Generate today's Rashifal — sectioned predictions for all 12 rashis.

    Generic across all users (not personalised by chart) so the caller can
    cache the result for 24 hours.

    Fires 12 parallel per-rashi LLM calls rather than one big-batch call. The
    big-batch approach failed reliability review — external audit found that
    a single-call generation produced ~4 unique readings clustered by element
    (Aries≈Sagittarius, Taurus≈Virgo≈Capricorn, Cancer≈Scorpio≈Pisces,
    Gemini≈Libra) because the LLM lazily reused phrasing across the same
    element group. Per-rashi calls make that failure mode impossible.

    `prompt_path` is the SINGLE-rashi prompt (rashifal_single.txt), not the
    old 12-rashi batch prompt. Callers should pass RASHIFAL_PROMPT_PATH; the
    module-level constant in main.py has been updated to point at the new
    single-rashi file.
    """
    day_signals = _build_rashifal_day_signals(transit, today_iso, lang, panchang, festival)
    day_signals_block = "\n".join(f"- {s}" for s in day_signals)
    transit_block = format_transit_for_prompt(transit)

    # Capped-parallelism. The cap is set by TOKENS per minute, not requests.
    #
    # It used to be 4, chosen against the wrong limit. The old rationale here
    # reasoned about REQUESTS per minute ("Groq/Cerebras cap ~30 RPM"), and
    # 4-wide is indeed safe for 30 RPM. But the binding constraint on this
    # route is TPM: Groq's free tier allows 8,000 tokens per minute per model,
    # and one rashifal call requests ~3,587. That is ~2.2 calls per minute of
    # budget — so 4 concurrent calls are ~14,300 tokens in a burst, over the
    # ceiling before the first one returns.
    #
    # Observed in production as AllProvidersExhausted on the daily send, with
    # Groq replying "Limit 8000, Used 5009, Requested 3587 ... try again in
    # 4.47s". The whole job is 12 x ~3,587 = ~43,000 tokens, i.e. five minutes
    # of budget spent in about thirty seconds.
    #
    # Two changes fix that together, and neither is sufficient alone:
    #   * this cap, now 2, matching the ~2.2 calls/min the budget allows;
    #   * providers.chat() honouring the "try again in Ns" hint instead of
    #     falling through the chain and giving up (see RETRY_AFTER_MAX_S).
    # The real headroom, though, is configuration: Groq quotas are keyed PER
    # MODEL, so listing the five Groq models in BHAGYA_LLM_PROVIDERS gives
    # 5 x 8,000 TPM from one key. See the PROVIDERS table in providers.py.
    #
    # Wall-clock: single call ~8-12s → 6 waves ~50-70s cold-cache, up from
    # ~24-36s. Acceptable: this runs in the nightly job, and warm-cache (99%
    # of daily requests) skips it entirely via _shared_three_tier. A slower
    # job that completes beats a faster one that raises.
    results: dict[int, str] = {}
    errors: dict[int, Exception] = {}
    pacer = _StartPacer(_RASHIFAL_MIN_INTERVAL_S)
    with ThreadPoolExecutor(max_workers=_RASHIFAL_CONCURRENCY) as pool:
        future_to_idx = {
            pool.submit(
                _generate_rashifal_single,
                anchor, day_signals_block, transit_block, prompt_path, lang,
                pacer,
            ): idx
            for idx, anchor in enumerate(_RASHI_ANCHORS)
        }
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            try:
                results[idx] = fut.result()
            except Exception as err:  # noqa: BLE001
                errors[idx] = err

    if errors:
        # Surface the first error — cache layer will treat it as a miss and retry.
        first_idx = min(errors)
        raise errors[first_idx]

    # Concatenate 12 sections in canonical order — same output shape the
    # existing parse_sectioned_reading() consumer expects.
    return "\n\n".join(results[i] for i in range(12))


def generate_matching_narrative(
    groom_name: str,
    bride_name: str,
    groom_chart: Chart,
    bride_chart: Chart,
    guna: object,           # GunaMilan — typed as object to avoid circular import
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
) -> str:
    """Sectioned LLM narrative interpreting a Kundali matching result.

    `guna` is a matching.GunaMilan — we type-erase to dodge an import cycle
    (matching imports from chart; we'd otherwise need llm → matching → chart).
    """
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {
            "role": "user",
            "content": _format_matching_message(groom_name, bride_name, groom_chart, bride_chart, guna),
        },
    ], route="matching")
    return content.strip()


def _format_matching_message(
    groom_name: str,
    bride_name: str,
    groom_chart: Chart,
    bride_chart: Chart,
    guna: object,
) -> str:
    """User-message block for matching narrative — both charts (slim) + koota scores."""
    def _seeker_block(label: str, name: str, chart: Chart) -> str:
        moon = next(p for p in chart.planets if p.name == "Moon")
        return (
            f"{label}: {name or '(unnamed)'}\n"
            f"  Lagna: {chart.lagna_rashi}\n"
            f"  Moon: {moon.rashi} ({moon.nakshatra} Nakshatra)\n"
        )

    g_block = _seeker_block("GROOM", groom_name, groom_chart)
    b_block = _seeker_block("BRIDE", bride_name, bride_chart)

    koota_lines = ["Koota-by-koota scores:"]
    for k in guna.kootas:  # type: ignore[attr-defined]
        koota_lines.append(f"- {k.name}: {k.awarded}/{k.max_points} — {k.note}")

    return (
        f"{today_anchor()}\n"
        f"{g_block}\n"
        f"{b_block}\n"
        f"--- KUNDALI MATCHING RESULT ---\n"
        + "\n".join(koota_lines) + "\n"
        + f"\nTotal: {guna.total_awarded}/{guna.total_max} ({guna.percent}%)\n"  # type: ignore[attr-defined]
        + f"Verdict: {guna.overall_verdict_label}\n"  # type: ignore[attr-defined]
        + f"Mangal Dosh compatibility: "
        + ("Compatible" if guna.mangal_dosh_compatible else "Needs review")  # type: ignore[attr-defined]
        + f"\nMangal Dosh note: {guna.mangal_dosh_note}\n"  # type: ignore[attr-defined]
    )


def parse_sectioned_reading(text: str) -> list[tuple[str, str]]:
    """Split a `## Heading`-delimited reading into [(title, body), ...].

    Drops any text before the first `## ` heading. Use this when the prompt
    instructs the LLM to start with a section heading (e.g. natal reading).
    Falls back to a single ("Reading", text) if no headings are found.
    """
    intro, sections = parse_intro_and_sections(text)
    if sections:
        return sections
    return [("Reading", intro)] if intro else [("Reading", text.strip())]


_BARE_HEADING_RE = re.compile(r"^#+\s*$")


def parse_intro_and_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Like `parse_sectioned_reading` but also returns text BEFORE the first
    `## ` heading as the `intro`.

    Use this for outlook readings (monthly/yearly) where the LLM produces
    flowing time-segmented prose first, then sectioned life-area blocks.
    Returns (intro_text, [(title, body), ...]); either may be empty.

    Robust against malformed LLM output: lines that are JUST hash marks with
    no heading text (e.g. a stray "##" between paragraphs) are dropped.
    """
    intro_lines: list[str] = []
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        # Drop lone heading markers — LLM sometimes emits a bare "##" as
        # paragraph separator. Treating these as content surfaces ugly artifacts.
        if _BARE_HEADING_RE.match(stripped):
            continue
        if stripped.startswith("## ") and len(stripped) > 3:
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped[3:].strip()
            current_lines = []
        else:
            if current_title is None:
                intro_lines.append(line)
            else:
                current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return ("\n".join(intro_lines).strip(), sections)


def generate_daily_reading(
    details: BirthDetails,
    natal: Chart,
    transit: TransitSnapshot,
    flags: VedicFlags,
    panchang: DailyPanchang,
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
) -> str:
    """Today's personalised Vedic reading — natal + transits + flags + Panchang."""
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": _format_daily_message(details, natal, transit, flags, panchang)},
    ], route="today")
    return content.strip()


def _format_daily_message(
    details: BirthDetails,
    natal: Chart,
    transit: TransitSnapshot,
    flags: VedicFlags,
    panchang: DailyPanchang,
) -> str:
    """Compose the user-message block: seeker, natal, transits, flags, Panchang."""
    name_line = f"Name: {details.name}" if details.name.strip() else "Name: (not provided)"
    return (
        f"{today_anchor()}\n"
        f"{name_line}\n"
        f"Birth date: {details.birth_date}\n"
        f"Birth time: {details.birth_time} (local time)\n"
        f"Birth place: {details.birth_place}\n"
        f"\n"
        f"--- NATAL CHART ---\n"
        f"{format_for_prompt(natal)}\n"
        f"\n"
        f"--- TODAY'S TRANSITS ---\n"
        f"{format_transit_for_prompt(transit)}\n"
        f"\n"
        f"--- VEDIC FLAGS ---\n"
        f"{format_flags_for_prompt(flags)}\n"
        f"\n"
        f"--- TODAY'S PANCHANG ---\n"
        f"{format_panchang_for_prompt(panchang)}\n"
    )
