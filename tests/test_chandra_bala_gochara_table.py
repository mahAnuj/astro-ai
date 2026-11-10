"""#715: Chandra Bala grades the Moon's house from the held Gochara table, in two grades.

`_chandra_bala` listed strong {1,3,6,7,10,11} and weak {4,8,12} and called the other three
houses (2, 5, 9) "neutral". `knowledge/vedic_reference.md` 2A (Raman, *Astrology for
Beginners* Ch. XII) classifies all twelve houses for the Moon -- benefic 1,3,6,7,10,11,
malefic 2,4,5,8,9,12 -- and says there is no neutral third category. `_couple_verdict`
let "neutral" pass, so a wedding day with a partner's Moon in the 2nd, 5th or 9th from the
natal Moon could read "good for both".

The expected sets below are typed from that table, not imported from `muhurat.py`: a test
that read `_CHANDRA_BALA_WEAK` back would pass for any value of it.

NOT pinned, deliberately: the muhurta-surface claim in #715 that the 6th house should be
unfavourable. It rests on a Raman Muhurtha passage that is not held, so the 6th stays strong.
"""
from __future__ import annotations

import pytest

from astro_ai import muhurat
from astro_ai.chart import RASHIS
from astro_ai.muhurat import PartnerFactors, _chandra_bala, _couple_verdict

# vedic_reference.md 2A, Moon row.
BENEFIC = {1, 3, 6, 7, 10, 11}
MALEFIC = {2, 4, 5, 8, 9, 12}


def _transit_in_house(house: int, natal: str = RASHIS[0]) -> str:
    return RASHIS[(RASHIS.index(natal) + house - 1) % 12]


def test_the_two_sets_cover_all_twelve_houses_exactly_once():
    # The REAL constants, not the table typed above: muhurat.py's import-time assert
    # only catches a set that stops partitioning 1..12, not a partition that is wrong.
    strong, weak = muhurat._CHANDRA_BALA_STRONG, muhurat._CHANDRA_BALA_WEAK
    assert strong | weak == set(range(1, 13))
    assert strong & weak == set()
    assert strong == BENEFIC
    assert weak == MALEFIC


@pytest.mark.parametrize("house", range(1, 13))
def test_each_house_takes_its_verdict_from_the_gochara_table(house):
    got_house, verdict = _chandra_bala(RASHIS[0], _transit_in_house(house))
    assert got_house == house
    assert verdict == ("strong" if house in BENEFIC else "weak")


@pytest.mark.parametrize("natal", RASHIS)
def test_no_neutral_grade_for_any_natal_and_transit_rashi(natal):
    grades = {_chandra_bala(natal, t)[1] for t in RASHIS}
    assert grades == {"strong", "weak"}


def test_the_rashifal_table_for_all_twelve_has_no_neutral():
    # The route behind /rashifal/<rashi>, the card and the email.
    for transit in RASHIS:
        table = muhurat.chandra_bala_by_rashi(transit)
        assert len(table) == 12
        assert {v for _, v in table.values()} <= {"strong", "weak"}


def test_an_unplaceable_rashi_still_returns_the_empty_verdict():
    assert _chandra_bala("not a rashi", RASHIS[0]) == (0, "")


def _partner(chandra: str) -> PartnerFactors:
    return PartnerFactors("excellent", "Ati-Mitra", chandra, "none", "", "")


def test_a_partner_with_the_moon_in_house_2_no_longer_passes_the_couple_verdict():
    _, verdict = _chandra_bala(RASHIS[0], _transit_in_house(2))
    assert verdict == "weak"
    assert _couple_verdict(_partner("strong"), _partner(verdict)) == "mixed"
    assert _couple_verdict(_partner(verdict), _partner("strong")) == "mixed"


@pytest.mark.parametrize("house", range(1, 13))
def test_the_couple_verdict_passes_only_when_both_houses_are_benefic(house):
    _, verdict = _chandra_bala(RASHIS[0], _transit_in_house(house))
    got = _couple_verdict(_partner("strong"), _partner(verdict))
    assert got == ("excellent-for-both" if house in BENEFIC else "mixed")


def test_the_couple_verdict_does_not_read_a_neutral_grade_as_a_pass():
    # Nothing produces "neutral" any more; if a value like it ever arrives it must fail closed.
    assert _couple_verdict(_partner("strong"), _partner("neutral")) == "mixed"
    assert _couple_verdict(_partner("neutral"), _partner("strong")) == "mixed"


def _render_finder(monkeypatch, **flags):
    from datetime import date

    from starlette.requests import Request

    from astro_ai import chart
    from astro_ai.routes.deps import templates

    monkeypatch.setattr(chart, "geocode_place", lambda place: (28.61, 77.21, "Asia/Kolkata"))
    start = date(2026, 12, 1)
    cands = muhurat.find_candidates("vivah", "Delhi", start, days=7)
    assert cands, "find_candidates returned nothing; the fixture is broken, not the code"
    request = Request({
        "type": "http", "method": "GET", "path": "/muhurat/vivah", "raw_path": b"/muhurat/vivah",
        "root_path": "", "headers": [], "query_string": b"", "scheme": "http",
        "server": ("testserver", 80), "client": ("test", 1234), "app": None,
    })
    return templates.env.get_template("muhurat_finder.html").render(
        lang="en", candidates=cands, event_type="vivah", event_label="Vivah",
        city="Delhi", start=start, days=7, personal_colors={}, results=True,
        request=request, **flags,
    )


@pytest.mark.parametrize("flags", [
    {"personal_active": True, "couple_active": False},
    {"personal_active": False, "couple_active": True},
])
def test_the_finder_states_the_source_of_the_chandra_grade(monkeypatch, flags):
    html = _render_finder(monkeypatch, **flags)
    assert "Raman's Gochara table" in html
    assert "houses 2, 4, 5, 8, 9 and 12 as unfavourable" in html
    assert "1/3/6/7/10/11" not in html and "4/8/12" not in html


def test_the_finder_claims_nothing_about_muhurta_traditions_in_the_chandra_note(monkeypatch):
    html = _render_finder(monkeypatch, personal_active=True, couple_active=False)
    note = html[html.index("<strong>Chandra Bala:</strong>"):].split("</p>", 1)[0]
    for phrase in ("muhurta", "muhurtha", "tradition", "differ", "BPHS", "Parashara"):
        assert phrase.lower() not in note.lower(), phrase


def test_the_note_is_absent_when_no_chandra_grade_is_shown(monkeypatch):
    html = _render_finder(monkeypatch, personal_active=False, couple_active=False)
    assert "<strong>Chandra Bala:</strong>" not in html
