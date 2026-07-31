"""Reading-generator functions — call providers.chat() with a per-feature prompt.

The system prompt is loaded from a file at request time (not module-import time)
so editing the prompt during development requires only a refresh — no restart.

Provider selection (Groq / Cerebras / Together / OpenAI / ...) and the
rate-limit fallback chain live in providers.py — every function here just
hands `messages` to providers.chat() and gets back text.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from astro_ai import providers
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


def _system_prompt(prompt_path: Path, lang: str) -> str:
    """Load the file prompt and tack the language suffix on the end."""
    base = prompt_path.read_text(encoding="utf-8")
    return base + _LANG_SUFFIX.get(lang, "")


@dataclass(frozen=True)
class BirthDetails:
    """Form-supplied seeker data. `name` is optional; everything else required."""

    name: str  # may be empty
    birth_date: str  # ISO YYYY-MM-DD
    birth_time: str  # HH:MM (24h, local)
    birth_place: str  # free-text city/country


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

    Conditional Manglik block: only emitted when the chart actually triggers
    the dosha — keeps the per-call prompt small for the ~70% of charts that
    aren't Manglik, while giving classical citations to the LLM when it matters.
    """
    name_line = f"Name: {details.name}" if details.name.strip() else "Name: (not provided)"
    manglik_block = format_manglik_for_prompt(compute_manglik_details(chart))
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


def generate_ask_answer(
    chart: Chart,
    dasha: DashaState | None,
    flags: VedicFlags | None,
    question: str,
    category: str,
    prompt_path: Path,
    lang: str = "en",
) -> str:
    """Personalised free-form Q&A grounded in the seeker's chart.

    Provides chart + current dasha + flags as context so the LLM can
    ground its answer in the actual placements rather than generic
    planetary meanings. Question and category come from the user form.
    """
    chart_block = format_for_prompt(chart)
    dasha_block = format_dasha_for_prompt(dasha) if dasha else "(no dasha state)"
    flags_block = format_flags_for_prompt(flags) if flags else ""
    user_message = (
        f"--- SEEKER'S NATAL CHART ---\n{chart_block}\n\n"
        f"--- CURRENT DASHA ---\n{dasha_block}\n\n"
        f"{('--- VEDIC FLAGS ---' + chr(10) + flags_block + chr(10) + chr(10)) if flags_block else ''}"
        f"--- QUESTION ---\n"
        f"Category hint: {category}\n"
        f"Question: {question.strip()}\n"
    )
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
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
# (English + Sanskrit name, ruling planet/Swami, element/Tattva, quality/Guna).
# Passing these per-rashi to the LLM prevents the failure mode where a single
# multi-rashi call outputs ~4 unique readings clustered by element — the LLM
# lazily groups Aries/Sagittarius (both fire), Taurus/Virgo/Capricorn (all
# earth), etc. Per-rashi calls guarantee 12 distinct outputs.
_RASHI_ANCHORS: tuple[dict[str, str], ...] = (
    {"en": "Aries",       "sa": "Mesha",       "lord": "Mars",    "element": "Fire",  "quality": "Movable"},
    {"en": "Taurus",      "sa": "Vrishabha",   "lord": "Venus",   "element": "Earth", "quality": "Fixed"},
    {"en": "Gemini",      "sa": "Mithuna",     "lord": "Mercury", "element": "Air",   "quality": "Dual"},
    {"en": "Cancer",      "sa": "Karka",       "lord": "Moon",    "element": "Water", "quality": "Movable"},
    {"en": "Leo",         "sa": "Simha",       "lord": "Sun",     "element": "Fire",  "quality": "Fixed"},
    {"en": "Virgo",       "sa": "Kanya",       "lord": "Mercury", "element": "Earth", "quality": "Dual"},
    {"en": "Libra",       "sa": "Tula",        "lord": "Venus",   "element": "Air",   "quality": "Movable"},
    {"en": "Scorpio",     "sa": "Vrishchika",  "lord": "Mars",    "element": "Water", "quality": "Fixed"},
    {"en": "Sagittarius", "sa": "Dhanu",       "lord": "Jupiter", "element": "Fire",  "quality": "Dual"},
    {"en": "Capricorn",   "sa": "Makara",      "lord": "Saturn",  "element": "Earth", "quality": "Movable"},
    {"en": "Aquarius",    "sa": "Kumbha",      "lord": "Saturn",  "element": "Air",   "quality": "Fixed"},
    {"en": "Pisces",      "sa": "Meena",       "lord": "Jupiter", "element": "Water", "quality": "Dual"},
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

    signals: list[str] = [f"Today's date: {today_iso}"]
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
    return signals


def _generate_rashifal_single(
    anchor: dict[str, str],
    day_signals_block: str,
    transit_block: str,
    prompt_path: Path,
    lang: str,
) -> str:
    """Generate a single rashi's daily reading — one LLM call, ~200 tokens output.

    Called 12× in parallel by generate_rashifal(). Each call is independent so
    the model can't lazily reuse phrasing across element-groups.
    """
    user_message = (
        f"RASHI TO WRITE FOR:\n"
        f"- Name: {anchor['en']} / {anchor['sa']}\n"
        f"- Ruling planet (Swami): {anchor['lord']}\n"
        f"- Element (Tattva): {anchor['element']}\n"
        f"- Quality (Guna): {anchor['quality']}\n"
        f"\n"
        f"TODAY'S SKY SIGNALS (use these to make the reading feel like TODAY):\n"
        f"{day_signals_block}\n"
        f"\n"
        f"Raw planetary positions (background context — do NOT recite):\n"
        f"{transit_block}\n"
        f"\n"
        f"Write ONLY the reading for {anchor['en']} / {anchor['sa']}. "
        f"Output must start with `## {anchor['en']} / {anchor['sa']}` then flowing prose."
    )
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": user_message},
    ], route="rashifal")
    return content.strip()


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

    # Capped-parallelism: 4 concurrent calls, so 12 calls run as ~3 waves of 4.
    # Rationale: 12-wide parallelism can burst-hit free-tier RPM limits on
    # individual providers (Groq/Cerebras cap ~30 RPM). Providers.chat() has
    # cross-provider fallback, but the fallback only fires on 429 after the
    # first attempt — if 12 calls all pick the same fast provider from the
    # random shuffle in the same second, that provider's per-second budget
    # is toast before fallback can help. 4-wide keeps peak RPS under any
    # free-tier limit while still being ~3× faster than sequential.
    #
    # Wall-clock: single call ~8-12s → 3 waves ~24-36s cold-cache. Warm-cache
    # (99% of daily requests) skips this entirely via _shared_three_tier.
    results: dict[int, str] = {}
    errors: dict[int, Exception] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_to_idx = {
            pool.submit(
                _generate_rashifal_single,
                anchor, day_signals_block, transit_block, prompt_path, lang,
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
