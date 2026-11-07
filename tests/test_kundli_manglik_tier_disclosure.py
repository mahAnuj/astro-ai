"""The /kundli result page stops presenting the Manglik tiers as classical (#429).

`result.html` renders `i18n.manglik_about_<severity>` under the badge. For the two
lower tiers it said "a moderate form of Manglik" / "the mildest form of Manglik" as
if a text graded them, in English and in Hindi. No book held in `data/` states the
ladder (vedic_reference.md §1.6.2); #579 disclosed that on `/manglik-check` and the
LLM line, #626 on `/matching`. This is the same disclosure on the main result page.

Two things are pinned, deliberately separate:

  * the grades are UNCHANGED (tests/test_manglik_severity_provenance.py owns the six
    values; this file checks the surface keeps keying off `manglik.severity`);
  * the text for the two ungraded-by-any-text tiers says the grade is Bhagya's own
    weighting, in both languages, and the old bare claims are gone.

`manglik_about_*` is page-only: nothing in `prompts/`, `llm.py` or `chart.py` reads
it, so the word "editorial" is not a prompt-echo risk here (test below pins that
this stays true, because if a prompt builder ever read it the answer changes).
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from astro_ai.routes import kundli as K

SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
_NATAL = "## Personality\n" + "The chart favours patient, deliberate work this season. " * 10 + "\n"

# Mars house -> the tier the shipped ladder gives it (chart.py). Owner's decision
# to move, not an engineer's.
_TIER = {7: "high", 4: "moderate", 12: "moderate", 1: "moderate", 2: "low"}

_OLD_CLAIMS_EN = ("moderate form of Manglik", "mildest form", "Often less severe")
_OLD_CLAIMS_HI = ("मध्यम स्वरूप", "सबसे हल्का स्वरूप", "प्रायः सप्तम/अष्टम से कम गंभीर")


def _t(lang: str, key: str) -> str:
    from astro_ai.i18n import translate

    return translate(lang, key)


@pytest.mark.parametrize("key", ["manglik_about_moderate", "manglik_about_low"])
def test_english_lower_tiers_say_the_grade_is_bhagyas_own_weighting(key):
    text = _t("en", key)
    assert "Bhagya's own weighting" in text, text
    assert "not a classical grade" in text, text
    assert "not drawn from the classical texts we hold" in text, text
    for claim in _OLD_CLAIMS_EN:
        assert claim not in text, (key, claim)


@pytest.mark.parametrize("key", ["manglik_about_moderate", "manglik_about_low"])
def test_hindi_lower_tiers_say_the_grade_is_bhagyas_own_weighting(key):
    text = _t("hi", key)
    assert "शुभ भाग्य का अपना भार-निर्धारण" in text, text
    assert "कोई शास्त्रीय श्रेणी नहीं" in text, text
    assert "शास्त्रीय ग्रंथों से नहीं ली गई" in text, text
    for claim in _OLD_CLAIMS_HI:
        assert claim not in text, (key, claim)


def test_the_2nd_house_text_no_longer_claims_traditions_exclude_it():
    """The old low-tier line said 'Some traditions exclude 2nd-house Manglik
    entirely'. Both held house lists (Vasudev, Raman) INCLUDE the 2nd, and no held
    text excludes it, so the sentence was an unsourced claim sitting beside the
    disclosure (vedic_reference.md §1.6.1/§1.6.3)."""
    assert "exclude" not in _t("en", "manglik_about_low").lower()
    assert "बाहर" not in _t("hi", "manglik_about_low")


def test_the_high_tier_still_renders_and_keeps_its_sourced_claim():
    en, hi = _t("en", "manglik_about_high"), _t("hi", "manglik_about_high")
    assert "7th or 8th" in en and "most-discussed" in en, en
    assert "सप्तम अथवा अष्टम" in hi, hi
    # Not a tier grade, so it carries no "own weighting" disclosure and must not
    # be turned into one by a careless edit of the shared wording.
    assert "own weighting" not in en


def test_manglik_about_is_not_read_by_any_prompt_builder():
    """Page-only text. If this fails, a prompt now reads it and the 'editorial'
    / token-cost reasoning in this file's header no longer holds."""
    hits = []
    for p in SRC.rglob("*"):
        if p.suffix in {".py", ".txt", ".html"} and "manglik_about" in p.read_text(encoding="utf-8"):
            hits.append(p.relative_to(SRC).as_posix())
    assert sorted(hits) == ["i18n.py", "templates/result.html"], hits


_ABOUT = re.compile(r"(?:What this means|इसका अर्थ)</div>\s*<p[^>]*>(.*?)</p>", re.S)


def _about_paragraph(page: str) -> str:
    found = _ABOUT.findall(page)
    assert len(found) == 1, f"expected one 'what this means' paragraph, found {len(found)}"
    return re.sub(r"\s+", " ", html.unescape(found[0])).strip()


@pytest.fixture
def render_for_house(client, saved_chart, stub_llm, monkeypatch):
    """GET /kundli (and ?lang=hi) with Manglik computed from a synthetic chart whose
    only qualifying house is `house`, so the tier shown is the ladder's own."""
    from astro_ai.chart import RASHIS as R, Chart, PlanetPosition

    def _single_house_chart(house: int) -> Chart:
        # Same construction as test_manglik_severity_provenance._single_house_chart
        # (tests/ is not a package, so it cannot be imported): Lagna Aries, Mars in
        # `house`, Moon and Venus parked 6th from Mars so no other axis fires.
        def p(name, rashi, h):
            return PlanetPosition(name=name, rashi=rashi, house=h, longitude=15.0,
                                  nakshatra="Ashwini", retrograde=False, pada=1)

        off = house - 1
        return Chart(
            lagna_rashi=R[0], lagna_longitude=10.0,
            planets=[p("Mars", R[off], house),
                     p("Moon", R[(off - 5) % 12], 1), p("Venus", R[(off - 5) % 12], 1),
                     p("Sun", R[4], 5), p("Mercury", R[5], 6),
                     p("Jupiter", R[8], 9), p("Saturn", R[9], 10),
                     p("Rahu", R[2], 3), p("Ketu", R[8], 9)],
            birth_lat=28.6, birth_lon=77.2, birth_tz="Asia/Kolkata",
            birth_utc=datetime(1990, 1, 1, tzinfo=timezone.utc),
        )

    stub_llm(_NATAL)
    saved_chart()
    real = K.compute_manglik_details

    def _render(house: int) -> dict[str, str]:
        details = real(_single_house_chart(house))
        assert details.houses == (house,) and details.severity == _TIER[house]
        monkeypatch.setattr(K, "compute_manglik_details", lambda chart: details)
        return {"en": client.get("/kundli").text, "hi": client.get("/kundli?lang=hi").text}

    return _render


@pytest.mark.parametrize("house", [1, 4, 12])
def test_result_page_moderate_tier_carries_the_disclosure_in_both_languages(render_for_house, house):
    pages = render_for_house(house)
    assert _about_paragraph(pages["en"]) == _t("en", "manglik_about_moderate")
    assert _about_paragraph(pages["hi"]) == _t("hi", "manglik_about_moderate")
    assert "not a classical grade" in _about_paragraph(pages["en"])
    for claim in _OLD_CLAIMS_EN:
        assert claim not in pages["en"]
    for claim in _OLD_CLAIMS_HI:
        assert claim not in pages["hi"]


def test_result_page_low_tier_carries_the_disclosure_in_both_languages(render_for_house):
    pages = render_for_house(2)
    assert _about_paragraph(pages["en"]) == _t("en", "manglik_about_low")
    assert _about_paragraph(pages["hi"]) == _t("hi", "manglik_about_low")
    assert "mildest" not in pages["en"]


def test_result_page_high_tier_is_unchanged(render_for_house):
    pages = render_for_house(7)
    assert _about_paragraph(pages["en"]) == _t("en", "manglik_about_high")
    assert _about_paragraph(pages["hi"]) == _t("hi", "manglik_about_high")


def test_knowledge_file_records_ramans_frame_strength_finding():
    """#429: Raman, Muhurtha, pp. 98-99, ranks the Venus frame STRONGEST, which is
    the opposite of chart.py's one-grade downgrade for the Venus-axis-only case.
    The finding lives in vedic_reference.md §1.6.3 and is pointed at from the
    §1.6.2 verdict row; if either goes, the downgrade is unsourced AND
    unremarked again."""
    text = (SRC / "knowledge" / "vedic_reference.md").read_text(encoding="utf-8")
    assert "#### 1.6.3 " in text
    flat = re.sub(r"\s+", " ", text.replace("> ", " "))
    assert "weak when it exists from Lagna, a little stronger from Moon and still more powerful from Venus" in flat
    assert "pp. **98–99**" in text and "venus_axis_only" in text
    row = next(ln for ln in text.splitlines() if ln.startswith("| **The severity ladder"))
    assert "counter-indicated by a held source" in row and "§1.6.3" in row
