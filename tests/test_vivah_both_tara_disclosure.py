"""#885: the Vivah couple verdict's "avoid only when BOTH partners are on an avoid Tara" rule is
the finder's own convention, and the page says so.

chief ruled Option A on 2026-11-11: keep the grades, disclose the convention. Raman's avoid-list
(Muhurtha, L1063-1066) names no person and his marriage chapter gives no combining rule
(knowledge/vedic_reference.md 2A-ter), so neither "both" nor "either" is sourced. This file pins
(1) that the verdicts did not move and (2) what the page SAYS. The grades are typed in, not read
back from muhurat.py.
"""
from __future__ import annotations

from datetime import date

import pytest

from astro_ai import muhurat
from astro_ai.muhurat import PartnerFactors, _couple_verdict

MARKER = "<strong>Tara Bala, two partners:</strong>"


def _p(grade: str, name: str, chandra: str = "strong") -> PartnerFactors:
    return PartnerFactors(grade, name, chandra, "none", "", "")


def _render_finder(monkeypatch, **flags):
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


def test_one_partner_on_an_avoid_tara_is_still_mixed_not_avoid():
    # The convention the page discloses: a lone avoid does not make the couple's day avoid.
    assert _couple_verdict(_p("avoid", "Vipat"), _p("good", "Sampat")) == "mixed"
    assert _couple_verdict(_p("good", "Sampat"), _p("avoid", "Vadha")) == "mixed"


def test_both_partners_on_an_avoid_tara_is_avoid():
    assert _couple_verdict(_p("avoid", "Vipat"), _p("avoid", "Vadha")) == "avoid"


def test_the_finder_says_the_both_rule_is_its_own_convention(monkeypatch):
    note = _note(_render_finder(monkeypatch, personal_active=False, couple_active=True))
    assert "only when both partners are on an avoid Tara" in note
    assert 'the day shows "mixed"' in note
    assert "is this finder's own convention, not a rule from a book" in note
    assert "without saying how a bride's and a groom's days combine" in note
    assert "still be an avoid day for one partner" in note
    assert "the 3rd, 5th or 7th Tara counted from the birth star, and the 1st for a groom" in note
    # The page shows each partner's Tara NAME, not a chip and not a grade (QA, round 1).
    assert "chip" not in note


def test_the_note_claims_no_source_for_the_both_rule(monkeypatch):
    note = _note(_render_finder(monkeypatch, personal_active=False, couple_active=True))
    assert "Muhurtha or Electional Astrology" in note
    for phrase in ("classical", "tradition", "texts say", "according to", "BPHS", "Parashara",
                   "Muhurta Chintamani", "Phaladeepika", "Raman says both"):
        assert phrase.lower() not in note.lower(), phrase


@pytest.mark.parametrize("flags", [
    {"personal_active": False, "couple_active": False},
    {"personal_active": True, "couple_active": False},
])
def test_the_note_is_absent_unless_a_couple_verdict_is_shown(monkeypatch, flags):
    assert MARKER not in _render_finder(monkeypatch, **flags)
