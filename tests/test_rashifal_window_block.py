"""The day-windows block handed to the rashifal model, per language (#270).

`format_day_windows_for_rashifal` localised only the two window NAMES. The rest
of the block — band, ordinal, directive prose, and the example phrases
('during Rahu Kaal', 'in the Abhijit window near midday') — went to the model in
English, and the Hindi reading echoed fragments of it into Devanagari prose
(live on /hi/rashifal/virgo: "in the Abhijit window near midday", "Rahu काल").
Measured at d6c570d: 168 English words left in the Hindi block once the two
names were stripped.

These assert what the MODEL is given, which is the only thing the function
produces: no LLM is called, so the suite stays hermetic.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from types import SimpleNamespace

from astro_ai.chart import _RAHU_KAAL_KEYS, format_day_windows_for_rashifal
from astro_ai.i18n import translate


def _block(lang: str, day: int = 8):
    # Only `sunrise` is read (for the weekday), so a namespace is enough.
    return format_day_windows_for_rashifal(
        SimpleNamespace(sunrise=datetime(2026, 10, day, 6, 10)), lang
    )


def _week(lang: str) -> list[str]:
    return [_block(lang, 5 + d) for d in range(7)]  # 2026-10-05 is a Monday


def _strip_names(text: str) -> str:
    for key in ("rahu_kaal", "abhijit_muhurta"):
        text = text.replace(translate("hi", key), "")
    return text


def test_english_block_is_byte_identical_to_the_pre_localisation_literals():
    """The refactor moved the English into i18n; it must not have moved a byte.

    Exact text for one weekday (readable on failure) plus a digest across all
    seven (the hash was taken from the code BEFORE #270, at d6c570d).
    """
    assert _block("en", 8) == (  # Thursday: Rahu Kaal is segment 6
        "Today's inauspicious and auspicious windows. Rahu Kaal falls in the "
        "6th of the eight equal parts of daylight — mid-afternoon — "
        "and is the wrong time to begin anything, sign, or decide. Abhijit "
        "Muhurta is the ~48 minutes centred on LOCAL solar noon, and is the "
        "day's most favourable window for important action.\n"
        "Write these two names EXACTLY as: \"Rahu Kaal\" and \"Abhijit Muhurta\". Do not "
        "transliterate them yourself, do not romanise them, and do not bold "
        "or otherwise mark them up.\n"
        "CRITICAL: state NEITHER as a clock time. Both are computed from the "
        "reader's own sunrise and sunset, and this one reading is published to "
        "the whole country — across Indian cities these windows shift by up to "
        "79 minutes, enough that two readers' Abhijit windows do not overlap at "
        "all. Name them ('during Rahu Kaal', 'in the Abhijit window near "
        "midday') and let the page show each reader their own times. Do not "
        "invent any other hour, minute, or 'after 4 pm'-style cutoff either — "
        "you have no clock for this reader."
    )
    digest = hashlib.sha256("".join(_week("en")).encode()).hexdigest()[:16]
    assert digest == "04118625184f5800"


def test_hindi_block_carries_no_english_once_the_two_names_are_removed():
    """The two names are localised by `rahu_kaal` / `abhijit_muhurta`; anything
    else Latin in the block is a word the model may copy into Devanagari
    prose. No allowlist: the block needs none."""
    for block in _week("hi"):
        leaked = re.findall(r"[A-Za-z]+", _strip_names(block))
        assert not leaked, f"English left in the Hindi window block: {leaked}"


def test_hindi_block_names_every_segment_and_band_distinctly():
    """Eight segments, eight ordinals, eight bands — none may collapse into a
    neighbour or fall back to the English text. (Segment 1 is not reachable
    from any weekday, so the keys are checked directly as well as via the
    rendered week.)"""
    assert sorted(_RAHU_KAAL_KEYS) == list(range(1, 9))
    for idx in (0, 1):  # ordinal, band
        hi = [translate("hi", _RAHU_KAAL_KEYS[n][idx]) for n in range(1, 9)]
        en = [translate("en", _RAHU_KAAL_KEYS[n][idx]) for n in range(1, 9)]
        assert len(set(hi)) == 8, f"Hindi strings collide: {hi}"
        assert all(h and h != e for h, e in zip(hi, en)), (hi, en)
    week = _week("hi")
    assert len(set(week)) == 7  # seven weekdays, seven different blocks


def test_hindi_block_still_gives_the_exact_names_and_forbids_clock_times():
    block = _block("hi")
    for key in ("rahu_kaal", "abhijit_muhurta"):
        assert f'"{translate("hi", key)}"' in block
    assert "79" in block and "48" in block
    # The anti-copy sentence for the English example phrases still living in
    # prompts/rashifal_single.txt (the second echo source).
    assert "अंग्रेज़ी उदाहरण" in block


def test_other_languages_still_receive_the_english_block():
    """translate() falls back to English for a language with no table; the
    refactor must not have changed what such a caller gets."""
    assert _block("ta") == _block("en")
