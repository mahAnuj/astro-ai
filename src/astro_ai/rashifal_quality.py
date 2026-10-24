"""The rashifal output rules, in ONE place, checked by both paths (#513).

A prompt rule is a request. `llm._strip_inline_markdown` already says so in
this codebase -- "told not to, the model still bolded a term in 1 of 4 Hindi
generations" -- and the rashifal measurements say it louder: across 252
published readings over 21 days, the prompt's ban on naming planets was
violated in **31.0%** of them, while its ban on "may feel" openings held at
**2.0%**. Same prompt, same model. The rules are enforceable; one of them was
simply never checked.

So the checks live here, in `src/`, rather than in the publishing script:

- `scripts/publish_rashifal.py` runs them as a GATE. The nightly Claude job
  publishes all 24 readings or none, so a refusal costs nothing -- Groq
  generates the day at 01:00 UTC instead.
- `llm._generate_rashifal_single` runs them as a MEASUREMENT on the Groq
  fallback path, logging what it finds and serving the reading anyway.

**Why the runtime path does not block, which is a deliberate choice and not an
omission.** Blocking there trades a known, cosmetic rule violation for an
unknown availability risk, on the one route in this product with a 21-day
silent outage in its history (2026-08-01..08-21). A reading that names a planet
is worse than one that does not; a reader with no reading at all is worse than
both. Regenerating instead of blocking would cost a second LLM call per
violation on a free tier whose ceiling is the reason this path exists.

What would change that: if the logged rate stays high after the nightly job is
live, the fallback is being used more than expected and blocking-with-retry
becomes worth its cost. That is a product decision with a number behind it,
which is why this module measures first.

The split between the two severities is the important part:

- `grounding` violations are FALSEHOODS ABOUT THE SKY -- a tithi or nakshatra
  the day does not have. They are verifiable against Swiss Ephemeris and there
  is no reading of them that is merely stylistic.
- `style` violations break a rule the prompt states but do not make the reading
  untrue.
"""
from __future__ import annotations

import re

__all__ = ["check_reading", "GROUNDING_RULES", "STYLE_RULES", "TITHIS", "NAKSHATRAS"]

TITHIS: tuple[str, ...] = (
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima", "Amavasya",
)

NAKSHATRAS: tuple[str, ...] = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
)

# `Rahu` matches only when NOT followed by `Kaal`, so the window rule below
# reports it once rather than twice.
_PLANETS = re.compile(
    r"\b(Sun|Moon|Jupiter|Saturn|Mercury|Mars|Venus|Ketu)\b|\bRahu\b(?!\s+Kaal)")
# Hard clock times AND the soft clocks the pre-#513 prompt actively taught.
_CLOCK = re.compile(
    r"\b\d{1,2}\s*(?:[:.]\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\b"
    r"|\b(?:mid[- ]morning|near midday|before noon|after noon|midday)\b", re.I)
_WINDOWS = re.compile(r"\bRahu\s+Kaal\b|\bAbhijit\b", re.I)
_MARKDOWN = re.compile(r"\*\*|__|`")

#: Rule name -> pattern. A hit here breaks a stated prompt rule.
STYLE_RULES: dict[str, re.Pattern[str]] = {
    "names a planet": _PLANETS,
    "states a clock time": _CLOCK,
    "names a day window": _WINDOWS,
    "contains markdown": _MARKDOWN,
    "predicts a specific event": re.compile(
        r"\byou will (?:receive|get|meet|find|win|be given|hear from)\b"
        r"|\bis going to happen\b|\bexpect a (?:call|visit|offer|payment)\b", re.I),
    "makes an absolute claim": re.compile(
        r"\bguaranteed\b|\bcertainly will\b|\bdefinitely will\b"
        r"|\bwithout (?:a )?doubt\b|\bis sure to\b", re.I),
    "gives a health directive": re.compile(
        r"\b(?:stop|start) taking\b|\bsee a doctor\b|\bmedication\b"
        r"|\bdiagnos\w+\b|\bprescrib\w+\b", re.I),
    "gives a money directive": re.compile(
        r"\binvest in\b|\bsell your\b|\bbuy (?:shares|stock)\b|\btake a loan\b", re.I),
    "uses fear framing": re.compile(
        r"\bfatal\b|\bdisaster\b|\bcatastroph\w+\b|\bruinous\b|\bcursed?\b", re.I),
}

#: Documented for callers that want to name the severity; the grounding checks
#: need today's computed sky, so they are functions rather than patterns.
GROUNDING_RULES = ("names a tithi that is not today's",
                   "names a nakshatra that is not today's")


def check_reading(body: str, *, tithi: str = "", nakshatra: str = "") -> dict:
    """{"style": [...], "grounding": [...]} for one reading's body.

    `tithi` and `nakshatra` are TODAY's computed values. Pass "" and that check
    is skipped -- absence disables a check, it never invents a verdict. Never
    raises: a caller on the serving path must not be able to 500 on a linter.
    """
    style: list[str] = []
    grounding: list[str] = []
    try:
        for label, rx in STYLE_RULES.items():
            hit = rx.search(body or "")
            if hit:
                style.append(f"{label} — {hit.group(0)!r}")
        if tithi:
            for t in TITHIS:
                if re.search(rf"\b{t}\b", body or "", re.I) and t.lower() not in tithi.lower():
                    grounding.append(f"names tithi {t!r}, but today is {tithi!r}")
        if nakshatra:
            for n in NAKSHATRAS:
                if (re.search(rf"\b{re.escape(n)}\b", body or "", re.I)
                        and n.lower() != nakshatra.lower()):
                    grounding.append(
                        f"names nakshatra {n!r}, but the Moon is in {nakshatra!r}")
    except Exception:  # noqa: BLE001 - see docstring
        return {"style": style, "grounding": grounding}
    return {"style": style, "grounding": grounding}
