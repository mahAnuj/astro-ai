"""#219: the finder says how it judges combustion, and the sentence is true by construction.

The orbs in the sentence are read back from chart.COMBUSTION_ORBS and the event list from
EVENT_RULES, so changing either without the page fails here. The Namkaran waiver and the
every-weekday Mercury veto are pinned as typed-in facts: changing one is a deliberate act
that has to edit this file. The sentence cites Raman's Muhurtha for the orbs (held:
knowledge/grahas.md 12.1) and says nothing about what any other text's method is.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from astro_ai import chart, muhurat

MARKER = "<strong>Combustion (asta):</strong>"


def _render_finder(monkeypatch, **flags):
    from datetime import date

    from starlette.requests import Request

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


@pytest.fixture
def note(monkeypatch):
    return _note(_render_finder(monkeypatch, personal_active=False, couple_active=False))


def test_the_note_states_the_orbs_the_code_uses(note):
    orbs = chart.COMBUSTION_ORBS
    assert f"Guru {orbs['Jupiter'][0]:g}°" in note
    assert f"Shukra {orbs['Venus'][0]:g}° ({orbs['Venus'][1]:g}° when retrograde)" in note
    assert f"Budh {orbs['Mercury'][0]:g}° ({orbs['Mercury'][1]:g}° when retrograde)" in note
    assert orbs["Jupiter"][0] == orbs["Jupiter"][1]  # the note gives Guru no retrograde clause


def test_the_note_names_exactly_the_events_that_check_each_planet(note):
    checks = {
        ev: tuple(p for p in ("jupiter", "venus", "mercury") if r[f"check_{p}_combust"])
        for ev, r in muhurat.EVENT_RULES.items()
    }
    # Typed in: the sentence below is true only while this table holds.
    assert checks == {
        "vivah": ("jupiter", "venus"),
        "griha_pravesh": ("jupiter",),
        "namkaran": (),
        "vidyarambh": ("jupiter",),
        "business": ("mercury",),
    }
    assert "Guru for Vivah, Griha Pravesh and Vidyarambh; Shukra for Vivah; Budh for Business" in note
    assert "Namkaran checks none of them" in note


def test_the_note_discloses_the_model_and_the_extension(note):
    assert "within a fixed number of degrees of the Sun" in note
    assert "does not count days around a planet's rising or setting" in note
    assert 'only "combust" or "not combust"' in note
    assert "blocks every weekday, not only Wednesday" in note
    assert "this finder's own extension, not a rule we source" in note


def test_the_note_claims_nothing_about_any_other_texts_method(note):
    low = note.lower()
    for phrase in ("chintamani", "parashara", "bphs", "classical", "tradition", "texts say",
                   "according to", "heliacal", "balatva", "vriddhatva"):
        assert phrase not in low, phrase
    assert "raman" in low  # the one held source, for the orbs only


def test_the_note_shows_without_a_personal_or_couple_search(monkeypatch):
    assert MARKER in _render_finder(monkeypatch, personal_active=False, couple_active=False)


def _score(event, combust):
    panchang = SimpleNamespace(tithi_name="Dwitiya", weekday="x")
    return muhurat.score_event(event, panchang, "x", "Hasta", False, False, "", "", combust)


@pytest.mark.parametrize("weekday", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                                     "Saturday", "Sunday"])
def test_business_vetoes_mercury_combustion_on_every_weekday(weekday):
    # Typed in: the note says "every weekday". Raman's own Upanayana line is Wednesday only.
    panchang = SimpleNamespace(tithi_name="Dwitiya", weekday=weekday)
    rating, _, flags = muhurat.score_event(
        "business", panchang, weekday, "Ashwini", False, False, "", "",
        {"jupiter": False, "venus": False, "mercury": True})
    assert rating == "avoid" and "mercury_combust" in flags


def test_namkaran_still_waives_every_combustion_check():
    rating, _, flags = _score("namkaran", {"jupiter": True, "venus": True, "mercury": True})
    assert not any(f.endswith("_combust") for f in flags), flags
