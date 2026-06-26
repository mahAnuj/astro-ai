"""OpenAI wrapper — single call producing a Vedic reading from birth details.

The system prompt is loaded from a file at request time (not module-import time)
so editing the prompt during development requires only a refresh — no restart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from astro_ai.chart import (
    Chart,
    DailyPanchang,
    GocharImpact,
    TransitSnapshot,
    VedicFlags,
    format_flags_for_prompt,
    format_for_prompt,
    format_panchang_for_prompt,
    format_transit_for_prompt,
)

DEFAULT_MODEL = "gpt-4o-mini"

# Appended to the system prompt to switch the LLM's output language.
# UI strings stay English (full i18n deferred); only the reading text translates.
_LANG_SUFFIX: dict[str, str] = {
    "en": "",
    "hi": (
        "\n\n"
        "IMPORTANT: Respond entirely in Hindi using Devanagari script. "
        "Translate the section headings into Hindi as well "
        "(## व्यक्तित्व, ## करियर और व्यवसाय, ## धन और समृद्धि, "
        "## संबंध और विवाह, ## स्वास्थ्य और कुशल-क्षेम, ## यात्रा और अवसर). "
        "Use Sanskrit Vedic terms naturally: राशि, लग्न, ग्रह, नक्षत्र, भाव, "
        "मंगल दोष, साढ़े साती, धन भाव, लाभ भाव. The seeker reads Hindi; do not include any English. "
        "Each section heading must still begin with `## ` on its own line."
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
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
) -> str:
    """Sectioned natal reading. Returns raw markdown-sectioned text from the LLM."""
    chosen_model = model or os.environ.get("ASTRO_AI_MODEL", DEFAULT_MODEL)
    api_base = os.environ.get("ASTRO_AI_API_BASE")
    client = OpenAI(base_url=api_base) if api_base else OpenAI()
    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": _system_prompt(prompt_path, lang)},
            {"role": "user", "content": _format_seeker_message(details, chart, flags)},
        ],
    )
    content = response.choices[0].message.content or ""
    return content.strip()


def _format_seeker_message(details: BirthDetails, chart: Chart, flags: VedicFlags) -> str:
    """Render birth details + chart + Vedic flags into the user message."""
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
    )


def generate_outlook_reading(
    details: BirthDetails,
    natal: Chart,
    transit: TransitSnapshot,
    flags: VedicFlags,
    gochar_impacts: list[GocharImpact],
    prompt_path: Path,
    model: str | None = None,
    lang: str = "en",
) -> str:
    """Multi-week or multi-month outlook (used by /monthly and /yearly).

    Shape mirrors generate_daily_reading but accepts no Panchang (irrelevant
    for windows >1 day) and adds the slow-mover gochar impacts list, which
    is the primary signal at these timescales.
    """
    chosen_model = model or os.environ.get("ASTRO_AI_MODEL", DEFAULT_MODEL)
    api_base = os.environ.get("ASTRO_AI_API_BASE")
    client = OpenAI(base_url=api_base) if api_base else OpenAI()
    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": _system_prompt(prompt_path, lang)},
            {
                "role": "user",
                "content": _format_outlook_message(details, natal, transit, flags, gochar_impacts),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return content.strip()


def _format_outlook_message(
    details: BirthDetails,
    natal: Chart,
    transit: TransitSnapshot,
    flags: VedicFlags,
    gochar_impacts: list[GocharImpact],
) -> str:
    """User-message block: seeker + natal + current transits + flags + gochar impacts."""
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
    )


def parse_sectioned_reading(text: str) -> list[tuple[str, str]]:
    """Split a `## Heading`-delimited reading into [(title, body), ...].

    Falls back to a single ("Reading", text) if no headings are found — keeps
    rendering robust against LLMs that occasionally ignore the format directive.
    """
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") and len(stripped) > 3:
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = stripped[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    if not sections:
        return [("Reading", text.strip())]
    return sections


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
    chosen_model = model or os.environ.get("ASTRO_AI_MODEL", DEFAULT_MODEL)
    api_base = os.environ.get("ASTRO_AI_API_BASE")
    client = OpenAI(base_url=api_base) if api_base else OpenAI()
    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": _system_prompt(prompt_path, lang)},
            {"role": "user", "content": _format_daily_message(details, natal, transit, flags, panchang)},
        ],
    )
    content = response.choices[0].message.content or ""
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
