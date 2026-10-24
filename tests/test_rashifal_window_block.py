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


def test_english_block_tells_the_model_the_windows_are_background_only():
    """The block names the two windows to STATE them, never to have them echoed.

    It used to read "Name them ('during Rahu Kaal', 'in the Abhijit window near
    midday')" — so the model was instructed to put them in the prose, and it
    did: `the abhijit muhurta` appeared in Aries on 21 of 21 consecutive days,
    and the exact 5-gram `the abhijit muhurta near midday` on 18 of 21 (#513).
    The email and page already render each reader their own computed times in a
    panel directly above the reading, so the prose was duplicating a table the
    reader can see and replacing an exact window ("9:15-10:39 AM") with a vaguer
    one ("mid-morning").

    The facts sentence is unchanged and still names both windows — the model
    needs them to know the day's shape. Only the directive flipped, from
    "say these" to "never say these". Exact text for one weekday (readable on
    failure) plus a digest across all seven.
    """
    assert _block("en", 8) == (  # Thursday: Rahu Kaal is segment 6
        "Today's inauspicious and auspicious windows. Rahu Kaal falls in the "
        "6th of the eight equal parts of daylight — mid-afternoon — "
        "and is the wrong time to begin anything, sign, or decide. Abhijit "
        "Muhurta is the ~48 minutes centred on LOCAL solar noon, and is the "
        "day's most favourable window for important action.\n"
        "BACKGROUND ONLY — never surface this. Do not name Rahu Kaal or "
        "Abhijit Muhurta, and do not paraphrase either window; the page and "
        "the email already show this reader their own times for both. State "
        "no clock time and no soft clock ('mid-morning', 'near midday') — "
        "across Indian cities these windows shift by up to 79 minutes. Use "
        "the shape above only to decide whether the day favours pushing or "
        "waiting."
    )
    digest = hashlib.sha256("".join(_week("en")).encode()).hexdigest()[:16]
    assert digest == "185ff1401795566a"


def test_no_language_tells_the_model_to_name_a_window():
    """The regression that #513 is about, pinned in every language we ship.

    An instruction to name the windows is what produced 21/21 days of
    `the abhijit muhurta`, so the ban has to hold for EN, HI and the
    English-fallback path alike — a directive that forbids it in English while
    still asking for it in Hindi would put it straight back on /hi/rashifal.
    """
    for lang in ("en", "hi", "ta"):
        directive = translate(lang, "rashifal_window_directive")
        assert "{rahu}" in directive and "{abhijit}" in directive, lang
        for banned in ("Name them", "के दौरान", "के आसपास"):
            assert banned not in directive, (lang, banned)


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


def test_hindi_block_forbids_naming_the_windows_and_any_clock_time():
    block = _block("hi")
    for key in ("rahu_kaal", "abhijit_muhurta"):
        # Still present — the model needs the names to read the facts line.
        assert translate("hi", key) in block
    # ...but no longer quoted as the exact spelling to reproduce: that framing
    # was the instruction to echo them (#513).
    for key in ("rahu_kaal", "abhijit_muhurta"):
        assert f'"{translate("hi", key)}"' not in block
    assert "79" in block and "48" in block
    # The anti-copy sentence for the English example phrases still living in
    # prompts/rashifal_single.txt (the second echo source).
    assert "अंग्रेज़ी उदाहरण" in block


def test_other_languages_still_receive_the_english_block():
    """translate() falls back to English for a language with no table; the
    refactor must not have changed what such a caller gets."""
    assert _block("ta") == _block("en")
