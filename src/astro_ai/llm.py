"""Reading-generator functions — call providers.chat() with a per-feature prompt.

The system prompt is loaded from a file at request time (not module-import time)
so editing the prompt during development requires only a refresh — no restart.

Provider selection (Groq / Cerebras / Together / OpenAI / ...) and the
rate-limit fallback chain live in providers.py — every function here just
hands `messages` to providers.chat() and gets back text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from astro_ai import providers
from astro_ai.chart import (
    Chart,
    DailyPanchang,
    DashaState,
    GocharImpact,
    LifeChapter,
    TransitEvent,
    TransitSnapshot,
    VedicFlags,
    format_dasha_for_prompt,
    format_events_for_prompt,
    format_flags_for_prompt,
    format_for_prompt,
    format_life_chapters_for_prompt,
    format_panchang_for_prompt,
    format_transit_for_prompt,
)

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
) -> str:
    """Sectioned natal reading. The 7th 'Life Stages' section uses life_chapters
    (the Mahadasha sequence framed as age windows) to ground age-based predictions."""
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": _format_seeker_message(details, chart, flags, life_chapters)},
    ])
    return content.strip()


def _format_seeker_message(
    details: BirthDetails,
    chart: Chart,
    flags: VedicFlags,
    life_chapters: list[LifeChapter],
) -> str:
    """Render birth details + chart + flags + life chapters into the user message."""
    name_line = f"Name: {details.name}" if details.name.strip() else "Name: (not provided)"
    return (
        f"{name_line}\n"
        f"Birth date: {details.birth_date}\n"
        f"Birth time: {details.birth_time} (local time)\n"
        f"Birth place: {details.birth_place}\n"
        f"\n"
        f"{format_for_prompt(chart)}\n"
        f"\n"
        f"{format_flags_for_prompt(flags)}\n"
        f"\n"
        f"{format_life_chapters_for_prompt(life_chapters)}\n"
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
    ])
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
    ])
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
    ])
    return content.strip()


def generate_rashifal(
    transit: TransitSnapshot,
    today_iso: str,
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
) -> str:
    """Generate today's Rashifal — sectioned predictions for all 12 rashis.

    Generic across all users (not personalised by chart) so the caller can
    cache the result for 24 hours.
    """
    user_message = (
        f"Today's date: {today_iso}\n\n"
        f"Today's planetary positions (for your reasoning only — do NOT mention in output):\n"
        f"{format_transit_for_prompt(transit)}\n"
    )
    content = providers.chat(messages=[
        {"role": "system", "content": _system_prompt(prompt_path, lang)},
        {"role": "user", "content": user_message},
    ])
    return content.strip()


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
    ])
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
    ])
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
