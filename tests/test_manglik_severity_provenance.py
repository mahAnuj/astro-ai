"""The Manglik severity ladder is Bhagya's editorial weighting, and says so (#429).

`compute_manglik_details` grades severity high (7th/8th) / moderate (1st/4th/12th)
/ low (2nd alone). No book held in `data/` states that ladder; only "7th and 8th
are the most serious" has any support (Vasudev's per-house prose,
`vedic_reference.md` §1.1 / §1.6). The standalone checker nevertheless printed
"Classical basis: ... Jataka Parijata, Phaladeepika, Jataka Chandrika, and
Muhurtha Chintamani" directly above the ladder, and the LLM line called it
"graded from the qualifying houses" with nothing to say it was not doctrine.

Two things are pinned here, and they are deliberately separate:

  * the six grades themselves are UNCHANGED — #429's tier decision (drop the 1st
    from moderate? collapse to 7/8 vs rest?) belongs to the owner, and a
    provenance edit must not move a grade as a side effect;
  * the two surfaces that carry the ladder disclose what it is.

The page is checked through the real route, scoped to the one paragraph the
reader sees (anchored on its Swiss Ephemeris sentence, which no rewording of the
provenance would drop), because the cancellation panel above it legitimately
prints rule sources that are out of this issue's slice.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

# Same chart as test_rule_citation_surfaces.py: Manglik on the Lagna axis, so the
# result page renders its full panel rather than the "not Manglik" branch.
_BIRTH = {
    "name": "Provenance Fixture",
    "birth_date": "1957-09-07",
    "birth_time": "01:05",
    "birth_place": "Mumbai",
}

# Books the old paragraph named as the "classical basis" of the rules. None is in
# data/ or in scripts/fetch_corpus.py's registry.
_UNHELD = ("Jataka Parijata", "Phaladeepika", "Jataka Chandrika", "Muhurtha Chintamani",
           "Jagannath Hora")


def _single_house_chart(house: int):
    """Lagna Aries, Mars in `house`; Moon and Venus parked 6th from Mars so neither
    other axis fires. Exactly one qualifying house, so the grade is the ladder's own."""
    from astro_ai.chart import RASHIS as R, Chart, PlanetPosition

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


# #429's repro table, as shipped on origin/main. Changing a value here is the
# owner's tier decision, not an engineer's edit.
_GRADES = {1: "moderate", 2: "low", 4: "moderate", 7: "high", 8: "high", 12: "moderate"}


@pytest.mark.parametrize("house,grade", sorted(_GRADES.items()))
def test_severity_grades_are_unchanged(house, grade):
    from astro_ai.chart import compute_manglik_details

    d = compute_manglik_details(_single_house_chart(house))
    assert d.houses == (house,), f"chart not isolated: qualifying={d.houses}"
    assert d.severity == grade


def _basis_paragraph() -> str:
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    r = TestClient(app).post("/manglik-check", data=_BIRTH)
    assert r.status_code == 200, r.status_code
    paras = [m for m in re.findall(r"<p>.*?</p>", r.text, flags=re.S) if "Swiss Ephemeris" in m]
    assert len(paras) == 1, (
        f"expected exactly one provenance paragraph (anchored on 'Swiss Ephemeris'), "
        f"found {len(paras)} — the assertions below would be vacuous"
    )
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", paras[0]))


def test_checker_page_discloses_that_the_ladder_is_editorial():
    text = _basis_paragraph()
    assert "editorial weighting" in text, text
    # The corroborated part is named as the only part.
    assert "7th and 8th" in text and "most serious" in text, text


def test_checker_page_names_no_unheld_book_as_the_basis():
    text = _basis_paragraph()
    for book in _UNHELD:
        assert book not in text, (
            f"the checker's provenance paragraph names {book!r}. It is not in data/, "
            f"so nobody can check that it states the rules, and the paragraph sits "
            f"next to a severity ladder no held book states (#429)."
        )
    assert "Classical basis" not in text, text


def _severity_line(chart) -> str:
    from astro_ai.chart import compute_manglik_details, format_manglik_for_prompt

    block = format_manglik_for_prompt(compute_manglik_details(chart))
    lines = [ln for ln in block.splitlines() if ln.startswith("Severity:")]
    assert len(lines) == 1, block
    return lines[0]


def test_llm_severity_line_does_not_present_the_ladder_as_classical():
    line = _severity_line(_single_house_chart(7))
    assert "not a classical grade" in line, line
    assert "graded from" not in line, line
    for book in _UNHELD:
        assert book not in line, line


def test_llm_severity_line_does_not_invite_the_model_to_say_editorial():
    """The disclosure belongs on the page. Handed the word, the model writes it
    into the reading as a disclaimer, so the prompt must not contain it."""
    assert "editorial" not in _severity_line(_single_house_chart(7)).lower()
