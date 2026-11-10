"""#714: the finder says what it does with Janma (Tara position 1), and nothing more.

`_TARA_BALA_NAMES[1]` grades the traveller's own birth star "ok", and `_couple_verdict`
counts "ok" as passing for either partner, for every event. No held text grades Janma per
event (knowledge/vedic_reference.md holds only Rao's "good tara from janma nakshatra"), and
the Raman Muhurtha passage #714 quotes is not in knowledge/. So chief ruled (Option A):
disclose, change no grade. The disclosure may state the code's behaviour and the lack of a
source; it may not cite Raman or say what any text holds.

The grades below are typed in, not read back from muhurat.py: a later change to either is a
deliberate act that has to edit this file, and #714 stays open for exactly that ruling.
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
    assert 'grades it "ok" and counts it as passing for either partner' in note
    assert "not varied by either" in note
    assert "same for every event" in note
    assert "not sourced to a text this site holds" in note


def test_the_janma_note_is_absent_when_no_tara_grade_is_shown(monkeypatch):
    html = _render_finder(monkeypatch, personal_active=False, couple_active=False)
    assert MARKER not in html


def test_the_janma_note_claims_nothing_about_what_any_text_says(monkeypatch):
    note = _note(_render_finder(monkeypatch, personal_active=True, couple_active=False))
    for phrase in ("raman", "classical", "tradition", "muhurtha", "muhurta", "texts say",
                   "according to", "BPHS", "Parashara"):
        assert phrase.lower() not in note.lower(), phrase


def test_janma_is_still_graded_ok():
    # Typed-in. Changing this grade is a sourced ruling on #714's remainder, not a patch.
    assert _tara_bala("Ashwini", "Ashwini") == (1, "Janma", "ok")


def _partner(tara: str, name: str) -> PartnerFactors:
    return PartnerFactors(tara, name, "strong", "none", "", "")


def test_a_groom_on_his_own_janma_still_passes_the_couple_verdict():
    # Measured at 018fce1: good-for-both. The disclosure above is true only while this holds.
    assert _couple_verdict(_partner("good", "Sampat"), _partner("ok", "Janma")) == "good-for-both"
    assert _couple_verdict(_partner("ok", "Janma"), _partner("ok", "Janma")) == "good-for-both"
