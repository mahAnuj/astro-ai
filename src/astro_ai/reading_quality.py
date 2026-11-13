"""A deterministic verdict on a generated natal reading (#327 slice 1, #966).

`prompts/natal.txt` states a set of hard bans -- no planet names, no sign names,
no house numbers, no decimals, no classical-text names, 17 banned words -- and
seven sections. A prompt rule is a request, not a guarantee: `rashifal_quality`
measured its own planet ban broken in 31.0% of 252 published readings. Nothing
checked the natal reading at all, so a provider swapping its model underneath us
would have changed the rate and nobody would have known.

This module only MEASURES. The call site (`routes/kundli.py::_render_natal_for`)
records the result on the `form_kundli` event and logs it; it never blocks, never
regenerates and never changes what the seeker is served. A second generation is a
~7,800-token call against an 8,000 TPM per-model bucket, which is why
`rashifal_quality`'s docstring rules retry out until a logged rate exists.

What this deliberately does NOT claim, so nobody reads a rate as more than it is:

- **Latin-script only.** A Hindi reading is checked for its section count; its
  banned terms are English/Latin words, so `banned` UNDERCOUNTS there and a Hindi
  pass rate must not be published. `words` is None for `lang != "en"` for the same
  reason (the 920-1380 band is an English count).
- **Case-sensitive planets and signs.** "the moon" is missed. Matching `sun`
  case-insensitively would trip on ordinary prose; an undercount is the safer error.
- **The seeker's name is stripped before matching.** Meena, Tula, Kanya and Leo are
  real first names and the prompt tells the model to use the name naturally. Cost: a
  name that equals a banned term hides a genuine hit on that one token.
- **natal.txt contradicts itself** (#968): line 32 tells the model to write "Mars falls
  in the 4th house" for Manglik charts, which breaks the planet and house-number bans
  at once. A Manglik chart can fail here for a reason the model cannot fix, which is
  why the call site also records `q_manglik`.
- **No Surya/Mangal/Shani, no Saravali/Raman.** natal.txt names nine English planet
  words and a fixed list of texts; banning more would be inventing a rule.
"""
from __future__ import annotations

import re

from astro_ai.chart import RASHIS
from astro_ai.rashifal_quality import STYLE_RULES

__all__ = ["check_natal_reading", "banned_by_kind", "EXPECTED_SECTIONS"]

#: natal.txt: six sections plus Life Stages.
EXPECTED_SECTIONS = 7

# Same nine names as natal.txt's `DO NOT name specific planets:` line. Reused from
# the rashifal rule rather than restated; a drift test pins both to the prompt.
_PLANET_RULE = STYLE_RULES["names a planet"]

# "Aries (Mesha)" -> both names. Derived, not a third literal list.
_SIGN_RULE = re.compile(
    r"\b(" + "|".join(
        re.escape(part)
        for label in RASHIS
        for part in re.findall(r"[A-Za-z]+", label)
    ) + r")\b")

_ORDINALS = ("first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
             "eleventh|twelfth")
# "house of service" (natal.txt's own phrasing) must stay clean: every branch
# needs a number or an ordinal beside the word "house".
_HOUSE_RULE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)\s+house\b|\bhouse\s+\d|\b(?:" + _ORDINALS + r")\s+house\b",
    re.I)

# natal.txt: 'write "from 34 to 51" -- never introduce decimals'. An ISO date has
# no dot, so the sub-window sentence ("until 2027-03-15") is safe.
_DECIMAL_RULE = re.compile(r"\b\d{1,2}\.\d{1,2}\b")

# The names natal.txt lists, plus the chapter-citation pattern it forbids.
_TEXT_RULE = re.compile(
    r"\bJataka\s+Parijata\b|\bPhaladeepika\b|\bBPHS\b|\bParashara\b|\bMansagari\b"
    r"|\bRao\s+Ch\b|\bCh\.\s*\d|\bchapters?\s+\d", re.I)

# natal.txt's BANNED WORDS paragraph, "in any form" -- so stems. `favourability` is
# exact because `favourable` is a different word the prompt does not ban.
# scripts/verify_natal_prompt.BANNED_WORDS is the source copy; scripts are not
# importable from src/, so tests/test_reading_quality.py pins the two together.
_BANNED_WORD_RULE = re.compile(
    r"\b(?:navigat\w*|manifest\w*|amplif\w+|introspect\w*|consolidat\w+|favourability"
    r"|propensit\w+|endeavou?r\w*|facilitat\w+|delve\w*|unlock\w*|harness\w*"
    r"|empower\w*|leverag\w+|moreover|furthermore|intricac\w+)\b", re.I)

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("planet", _PLANET_RULE),
    ("sign", _SIGN_RULE),
    ("house_number", _HOUSE_RULE),
    ("decimal_age", _DECIMAL_RULE),
    ("classical_text", _TEXT_RULE),
    ("banned_word", _BANNED_WORD_RULE),
)


def _without_name(text: str, name: str) -> str:
    """Blank each name token so a seeker called Meena or Sunil is not flagged."""
    for token in re.findall(r"[^\W\d_]+", name or ""):
        if len(token) >= 3:
            text = re.sub(rf"\b{re.escape(token)}\b", " ", text, flags=re.I)
    return text


def check_natal_reading(text: str, *, n_sections: int, name: str = "",
                        lang: str = "en") -> dict:
    """Return `{"ok", "sections", "banned", "words"}` for one natal reading.

    `n_sections` is the caller's `len(parse_sectioned_reading(text))`: counting
    `## ` here would be a second definition of "section" that drifts from what the
    reader is served. `banned` is a list of `{"kind", "term"}`. Length is not part
    of `ok`: `words` is a plain int so the band can move without rewriting history.
    """
    scan = _without_name(text, name)
    banned = [
        {"kind": kind, "term": m.group(0)}
        for kind, rule in _RULES
        for m in rule.finditer(scan)
    ]
    return {
        "ok": n_sections == EXPECTED_SECTIONS and not banned,
        "sections": n_sections,
        "banned": banned,
        "words": len(text.split()) if lang == "en" else None,
    }


def banned_by_kind(verdict: dict) -> dict[str, int]:
    """`{kind: count}` -- the only form of `banned` that reaches the event log."""
    counts: dict[str, int] = {}
    for hit in verdict["banned"]:
        counts[hit["kind"]] = counts.get(hit["kind"], 0) + 1
    return counts
