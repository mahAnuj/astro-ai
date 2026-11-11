"""#714: the finder says what it does with Janma (Tara position 1), and what it follows.

`_TARA_BALA_NAMES[1]` still grades the person's own birth star "ok" and the single-user
personal match shows it unchanged. The Vivah couple verdict reads it further: a groom on his own
Janma day counts as avoid for the Tara test, a bride's still passes, following Raman, Muhurtha
(1948), knowledge/vedic_reference.md 2A-ter. This file pins what the page SAYS about that; the
verdicts themselves are pinned in tests/test_janma_vivah_groom.py. It began as a disclosure-only
file (chief's Option A: change no grade); the groom pin below was flipped deliberately when the
ruling on #714's remainder landed, so it is an edit to a marker, not a patch around one.

The grades below are typed in, not read back from muhurat.py.
"""
from __future__ import annotations

import pytest

from astro_ai import muhurat
from astro_ai.muhurat import PartnerFactors, _couple_verdict, _tara_bala

MARKER = "<strong>Tara Bala, Janma:</strong>"


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


def _note(html: str) -> str:
    return html[html.index(MARKER):].split("</p>", 1)[0]


@pytest.mark.parametrize("flags", [
    {"personal_active": True, "couple_active": False},
    {"personal_active": False, "couple_active": True},
])
def test_the_finder_discloses_how_janma_is_graded(monkeypatch, flags):
    note = _note(_render_finder(monkeypatch, **flags))
    assert 'the personal match still shows "ok"' in note
    assert "not varied by event" in note
    assert "a groom on the day ruled by his own birth star is no longer counted as a pass" in note
    assert "a bride on her own birth-star day still passes" in note
    assert "does not apply the exception Raman allows only in urgent cases" in note
    assert "not sourced to a text this site holds" in note


def test_the_janma_note_is_absent_when_no_tara_grade_is_shown(monkeypatch):
    html = _render_finder(monkeypatch, personal_active=False, couple_active=False)
    assert MARKER not in html


def test_the_janma_note_names_one_book_and_does_not_lean_on_the_nuptials_sentence(monkeypatch):
    note = _note(_render_finder(monkeypatch, personal_active=True, couple_active=False))
    assert "Muhurtha or Electional Astrology" in note
    # Raman contradicts himself on "nuptials" in the same passage; the page says so and no more.
    assert 'unclear on "nuptials", so that sentence is not used' in note
    assert "without exception" not in note
    for phrase in ("classical", "tradition", "texts say", "according to", "BPHS", "Parashara",
                   "Muhurta Chintamani", "Phaladeepika"):
        assert phrase.lower() not in note.lower(), phrase


def test_janma_is_still_graded_ok():
    # Typed-in. Changing this grade is a sourced ruling on #714's remainder, not a patch.
    assert _tara_bala("Ashwini", "Ashwini") == (1, "Janma", "ok")


def _partner(tara: str, name: str) -> PartnerFactors:
    return PartnerFactors(tara, name, "strong", "none", "", "")


def test_a_groom_on_his_own_janma_no_longer_passes_the_couple_verdict():
    # FLIPPED DELIBERATELY (#714). Measured at 018fce1: good-for-both. The page above says a
    # groom on his Janma day is "no longer counted as a pass"; that is true only while this holds.
    assert _couple_verdict(_partner("good", "Sampat"), _partner("ok", "Janma")) == "mixed"
    assert _couple_verdict(_partner("ok", "Janma"), _partner("ok", "Janma")) == "mixed"


def test_a_bride_on_her_own_janma_still_passes_the_couple_verdict():
    assert _couple_verdict(_partner("ok", "Janma"), _partner("good", "Sampat")) == "good-for-both"
