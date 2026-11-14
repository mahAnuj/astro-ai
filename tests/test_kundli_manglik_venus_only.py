"""/kundli result page: the Venus-only grade drop is disclosed and the paragraph
describes the houses that actually qualify (#777).

`compute_manglik_details` drops the severity one grade, and caps the status at
"mitigated", when Mars qualifies ONLY when counted from Venus. Raman, *Muhurtha*
(vedic_reference.md §1.6.3), ranks the Venus frame the most powerful, so the drop
is Bhagya's own convention, and the grade is unchanged here (an owner call, act #4).
What was wrong on the page, measured before this change:

  * nothing said a step had been taken off, so "Moderate severity" read as the
    ladder's own grade for the house;
  * the paragraph under the badge was keyed on the DOWNGRADED grade, so Mars in the
    7th from Venus only was told "Mars in the 1st, 4th or 12th house counts toward
    Manglik here" -- the wrong houses.

The grades and the status cap are not touched; tests/test_manglik_severity_provenance.py
owns those.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone

import pytest

from astro_ai.routes import kundli as K

_NATAL = "## Personality\n" + "The chart favours patient, deliberate work this season. " * 10 + "\n"
_ABOUT = re.compile(r"(?:What this means|इसका अर्थ)</div>\s*<p[^>]*>(.*?)</p>", re.S)
_NOTE_KEY = "manglik_venus_only_note"


def _t(lang: str, key: str) -> str:
    from astro_ai.i18n import translate

    return translate(lang, key)


def _flat(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def test_note_says_the_step_down_is_bhagyas_own_convention_in_both_languages():
    en, hi = _t("en", _NOTE_KEY), _t("hi", _NOTE_KEY)
    assert "only when counted from your Venus" in en, en
    assert "one step lower" in en and "no stronger than mitigated" in en, en
    assert "Bhagya's own convention" in en and "not a classical rule" in en, en
    assert "more powerful" in en and "not the weaker" in en, en
    assert "शुभ भाग्य की अपनी परिपाटी" in hi and "शास्त्रीय नियम नहीं" in hi, hi
    assert "शुक्र" in hi and "एक स्तर" in hi, hi
    # A key that translate() cannot find returns the key itself.
    assert en != _NOTE_KEY and hi != _NOTE_KEY


def test_note_is_page_only_so_the_word_convention_cannot_echo_from_a_prompt():
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
    hits = sorted(p.relative_to(src).as_posix() for p in src.rglob("*")
                  if p.suffix in {".py", ".txt", ".html"} and _NOTE_KEY in p.read_text(encoding="utf-8"))
    assert hits == ["i18n.py", "templates/result.html"], hits


def _chart(mars_house: int, venus_house: int, moon_house: int):
    """Lagna Aries (house n = sign n), Mars/Venus/Moon in the given houses."""
    from astro_ai.chart import RASHIS as R, Chart, PlanetPosition

    def p(name, h, lon=15.0):
        return PlanetPosition(name=name, rashi=R[h - 1], house=h, longitude=lon,
                              nakshatra="Ashwini", retrograde=False, pada=1)

    return Chart(
        lagna_rashi=R[0], lagna_longitude=10.0,
        planets=[p("Mars", mars_house), p("Moon", moon_house), p("Venus", venus_house),
                 p("Sun", 5), p("Mercury", 6), p("Jupiter", 9), p("Saturn", 10),
                 p("Rahu", 11), p("Ketu", 5)],
        birth_lat=28.6, birth_lon=77.2, birth_tz="Asia/Kolkata",
        birth_utc=datetime(1990, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def render(client, saved_chart, stub_llm, monkeypatch):
    stub_llm(_NATAL)
    saved_chart()
    real = K.compute_manglik_details

    def _render(chart):
        details = real(chart)
        monkeypatch.setattr(K, "compute_manglik_details", lambda c: details)
        return details, {"en": client.get("/kundli").text, "hi": client.get("/kundli?lang=hi").text}

    return _render


def _about(page: str) -> str:
    found = _ABOUT.findall(page)
    assert len(found) == 1, f"expected one 'what this means' paragraph, found {len(found)}"
    return _flat(found[0])


def test_venus_only_7th_house_gets_the_note_and_the_7th_house_paragraph(render):
    # Mars 3rd from Lagna and from Moon (Moon in 1st) -> no qualifying house on
    # those axes; Venus in 9th puts Mars 7th from Venus.
    details, pages = render(_chart(mars_house=3, venus_house=9, moon_house=1))
    assert details.venus_axis_only and details.houses == (7,)
    assert details.severity == "moderate"            # the shipped one-grade drop, unchanged
    for lang in ("en", "hi"):
        assert _flat(_t(lang, _NOTE_KEY)) in _flat(pages[lang]), lang
        # The paragraph describes the 7th-house case that actually qualifies...
        assert _about(pages[lang]) == _flat(_t(lang, "manglik_about_high")), lang
        # ...while the badge still shows the (downgraded) shipped grade.
    assert _t("en", "manglik_severity_moderate") in pages["en"]
    assert "1st, 4th or 12th" not in _about(pages["en"])


def test_lagna_axis_chart_carries_no_venus_note(render):
    # Mars 7th from Lagna: Lagna axis fires, so no drop and nothing to disclose.
    details, pages = render(_chart(mars_house=7, venus_house=7, moon_house=7))
    assert not details.venus_axis_only and details.severity == "high"
    for lang in ("en", "hi"):
        assert _flat(_t(lang, _NOTE_KEY)) not in _flat(pages[lang]), lang
        assert _about(pages[lang]) == _flat(_t(lang, "manglik_about_high")), lang


def test_venus_only_2nd_house_keeps_the_low_paragraph_and_floors_at_low(render):
    # Mars 3rd from Lagna; Moon in 1st puts Mars 3rd from Moon; Venus in 2nd puts
    # Mars 2nd from Venus -> Venus-only, 2nd house, severity low (floor).
    details, pages = render(_chart(mars_house=3, venus_house=2, moon_house=1))
    assert details.venus_axis_only and details.houses == (2,) and details.severity == "low"
    assert _about(pages["en"]) == _flat(_t("en", "manglik_about_low"))
    assert _flat(_t("en", _NOTE_KEY)) in _flat(pages["en"])
