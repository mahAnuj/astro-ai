"""The matching page's severity sentence says the ladder is Bhagya's own (#429).

#579 made the /manglik-check page and the LLM line in `chart.py` disclose that the
Manglik severity ladder (7th/8th high; 1st/4th/12th moderate; 2nd alone low; one
grade lower when only the Venus axis qualifies) is Bhagya's weighting, not a
classical grade — no book held in `data/` states it. `matching.py`
`_SEVERITY_GRADING_SENTENCE` was left reading "Severity here is graded from the
houses Mars occupies ..." unqualified, and it is appended to all three Manglik
notes of `mangal_dosh_verdict`, which `matching_result.html` prints AND `llm.py`
sends to the model. So the two surfaces #579 corrected were contradicted, on the
same site, by the page that carries the pairing verdict.

Two things are pinned, deliberately separate (as in
test_manglik_severity_provenance.py):

  * the sentence discloses what the ladder is, in all three branches, without
    handing the model the word "editorial" (it would echo it into the reading) and
    without crediting a book nobody here holds;
  * the sentence still DESCRIBES the ladder `compute_manglik_details` computes, so
    moving a grade in chart.py without moving the sentence goes red here.

The request path through POST /matching is not exercised: it calls the LLM and the
geocoder, which a fresh clone does not have. The note is built by the same
`mangal_dosh_verdict` that route calls, and `compute_guna_milan` (the function the
route calls) is driven below to show the note reaches `GunaMilan.mangal_dosh_note`,
the field both the template and the LLM prompt read.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

# Books the pre-#579 checker paragraph named as the "classical basis". None is held.
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


def _manglik(severity: str, status: str = "present"):
    """A ManglikDetails whose only live fields are the two the verdict reads."""
    from astro_ai.chart import ManglikDetails

    return ManglikDetails(
        is_manglik=status != "none", houses=(7,), primary_house=7,
        severity=severity, cancellations=(), effective_status=status,
    )


def _notes() -> dict[str, str]:
    """One real note per branch that mentions severity, keyed by the branch the
    verdict itself reports — so a branch that stops existing fails the key check."""
    from astro_ai.matching import mangal_dosh_verdict

    cases = {
        "both_comparable": (_manglik("high"), _manglik("moderate")),
        "both_incomparable": (_manglik("high"), _manglik("low")),
        "one_sided": (_manglik("high"), _manglik("none", "none")),
    }
    out = {}
    for branch, (g, b) in cases.items():
        v = mangal_dosh_verdict(g, b)
        assert v.branch == branch, f"fixture no longer reaches {branch!r}: got {v.branch!r}"
        out[branch] = v.note
    return out


@pytest.mark.parametrize("branch", ["both_comparable", "both_incomparable", "one_sided"])
def test_every_severity_note_discloses_the_ladder_is_not_classical(branch):
    note = _notes()[branch]
    assert "not a classical grade" in note, note
    assert "graded from" not in note, note
    for book in _UNHELD:
        assert book not in note, note


@pytest.mark.parametrize("branch", ["both_comparable", "both_incomparable", "one_sided"])
def test_severity_note_does_not_invite_the_model_to_say_editorial(branch):
    """The note is sent to the LLM (llm.py). Handed the word, the model writes it
    into the reading as a disclaimer; the page paragraph owns that word."""
    assert "editorial" not in _notes()[branch].lower()


def test_neither_branch_mentions_severity_so_carries_no_disclosure():
    """Pinned so the three-branch list above is known to be complete: the fourth
    branch never discusses severity, and must not start without the disclosure."""
    from astro_ai.matching import mangal_dosh_verdict

    v = mangal_dosh_verdict(_manglik("none", "none"), _manglik("none", "none"))
    assert v.branch == "neither"
    assert "everity" not in v.note, v.note


def _sentence() -> str:
    from astro_ai.matching import _SEVERITY_GRADING_SENTENCE

    return _SEVERITY_GRADING_SENTENCE


def _claimed_ladder(sentence: str) -> dict[str, set[int]]:
    """Read the grade -> houses claims out of the sentence's own prose."""
    m = re.search(
        r"(\d+)(?:st|nd|rd|th) or (\d+)(?:st|nd|rd|th) is high, "
        r"(\d+)(?:st|nd|rd|th), (\d+)(?:st|nd|rd|th) or (\d+)(?:st|nd|rd|th) moderate, "
        r"(\d+)(?:st|nd|rd|th) alone low",
        sentence,
    )
    assert m, f"the sentence no longer states the ladder in the expected shape: {sentence!r}"
    n = [int(x) for x in m.groups()]
    return {"high": set(n[0:2]), "moderate": set(n[2:5]), "low": {n[5]}}


def test_sentence_ladder_agrees_with_compute_manglik_details():
    """Derived from the real function over single-house charts, not restated: if a
    grade moves in chart.py and the sentence does not, this fails."""
    from astro_ai.chart import compute_manglik_details

    derived: dict[str, set[int]] = {"high": set(), "moderate": set(), "low": set()}
    for house in (1, 2, 4, 7, 8, 12):
        d = compute_manglik_details(_single_house_chart(house))
        assert d.houses == (house,), f"chart not isolated: qualifying={d.houses}"
        derived[d.severity].add(house)
    assert _claimed_ladder(_sentence()) == derived


def test_sentence_still_states_the_venus_axis_downgrade_and_its_three_frames():
    s = _sentence()
    assert "Lagna, the Moon and Venus" in s, s
    assert "one grade lower when only the Venus-axis count qualifies" in s, s


def test_venus_axis_downgrade_the_sentence_claims_is_real():
    """Mars 7th from Venus only (3rd from the Lagna, 6th from the Moon): a 7th-house
    count that would be high on the Lagna axis grades one lower here."""
    import dataclasses

    from astro_ai.chart import RASHIS as R, compute_manglik_details

    chart = _single_house_chart(3)  # Mars 3rd from Lagna: does not qualify
    mars_i = R.index(next(p for p in chart.planets if p.name == "Mars").rashi)
    planets = [
        dataclasses.replace(p, rashi=R[(mars_i - 6) % 12]) if p.name == "Venus" else p
        for p in chart.planets
    ]
    d = compute_manglik_details(dataclasses.replace(chart, planets=planets))
    assert d.venus_axis_only and d.houses == (7,), (d.houses, d.venus_axis_only)
    assert d.severity == "moderate", d.severity


def test_compute_guna_milan_carries_the_disclosure_into_the_note_the_page_and_llm_read(
    monkeypatch,
):
    """`GunaMilan.mangal_dosh_note` is the field matching_result.html:103 prints and
    llm.py:584 / :1428 send. The details are injected because no fixture chart here
    stays uncancelled (each of the six trips at least one cancellation rule); the note path
    from there to the field is the real one."""
    import astro_ai.chart as chart_mod
    from astro_ai.matching import compute_guna_milan

    monkeypatch.setattr(chart_mod, "compute_manglik_details",
                        lambda _c: _manglik("high"))
    guna = compute_guna_milan(_single_house_chart(7), _single_house_chart(7))
    assert "not a classical grade" in guna.mangal_dosh_note, guna.mangal_dosh_note
    assert "graded from" not in guna.mangal_dosh_note, guna.mangal_dosh_note
    assert "editorial" not in guna.mangal_dosh_note.lower()
