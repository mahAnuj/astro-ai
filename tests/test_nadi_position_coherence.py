"""One Nadi position everywhere, not an absolute here and an exemption there (#397).

`/matching` rendered two sentences on one panel that could not both be true:
the note said Nadi "has no cancelling conditions in this tradition", and the
disclosure thirteen lines below said it is "waived in parts of the south, and
for some communities". The `/ask` overlays then enforced the absolute, so the
model was forbidden to acknowledge an exemption the page had just shown.

`knowledge/matching.md` v.34 is what decides it: Nadi is a precondition and not
among the Bhakoot parihāras (परन्तु नाडी सभीमें होनी चाहिये), the tika records a
regional/varna exemption (गोदावरीके दक्षिण अथवा क्षत्रिय आदिकोंको नहीं), a slight
grade where pada-Nadi differs (दोष अल्प है) and shanti. This product applies none
of the exemptions and awards no koota points for any mitigation. Every surface
must say that and nothing stronger.

Hermetic: charts are really computed (geocoding is stubbed by conftest), no LLM.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai import chart as C
from astro_ai import llm, matching as M
from astro_ai.i18n import _EN, _HI

SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
PROMPTS = SRC / "prompts"

# `(?:</?em>)?` because the learn article once wrote "<em>no</em> cancelling".
_ABSOLUTE = re.compile(
    r"no\s*(?:</?em>)?\s*cancell?ing\s+conditions|no\s+parih[aā]ras?\b",
    re.IGNORECASE,
)


def _nadi_pair():
    """1990-01-01 and 1990-01-04 at 10:00 share the Madhya Nadi (checked)."""
    g = C.compute_chart("1990-01-01", "10:00", "Mumbai")
    b = C.compute_chart("1990-01-04", "10:00", "Mumbai")
    guna = M.compute_guna_milan(g, b)
    assert guna.nadi_dosha.present, "fixture pair no longer shares a Nadi"
    return guna


def test_no_surface_asserts_nadi_has_no_cancelling_conditions():
    hits = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in {".py", ".txt", ".html"}:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _ABSOLUTE.search(line):
                hits.append(f"{path.relative_to(SRC)}:{n}: {line.strip()[:90]}")
    assert not hits, (
        "the unsourced Nadi absolute is back; matching.md v.34 records regional "
        "and community exemptions, so 'no cancelling conditions' / 'no parihāras' "
        "contradicts the disclosure rendered beside it:\n  " + "\n  ".join(hits)
    )


def test_both_ask_overlays_carry_the_identical_nadi_line():
    def nadi_lines(name):
        return [ln for ln in (PROMPTS / name).read_text(encoding="utf-8").splitlines()
                if ln.startswith("- Nadi ")]

    mine, third = nadi_lines("ask_matching.txt"), nadi_lines("ask_matching_third_party.txt")
    assert len(mine) == 1 and len(third) == 1, (mine, third)
    assert mine == third, "the two overlays' Nadi rules have drifted apart"
    assert "not among the Bhakoot parih" in mine[0]
    assert "exemptions" in mine[0], "the overlay must acknowledge the disclosed exemptions"


def test_engine_note_states_the_narrowed_position_and_keeps_the_disclosure():
    nd = _nadi_pair().nadi_dosha
    assert not _ABSOLUTE.search(nd.note), nd.note
    assert "not among the Bhakoot parih" in nd.note
    assert "exemptions" in nd.note and "which we do not apply" in nd.note
    # The disclosure the note points at ("shown below") must still be there.
    assert nd.unevaluated == M._NADI_UNEVALUATED and nd.unevaluated
    assert "region and community" in nd.unevaluated[0]


@pytest.mark.parametrize("table,needle", [
    (_EN, "no mitigation adds points"),
    (_HI, "अंक नहीं बढ़ते"),
])
def test_panel_footnote_still_says_no_points_and_not_the_absolute(table, needle):
    text = table["matching_nadi_nocancel"]
    assert needle in text, text
    assert not _ABSOLUTE.search(text)
    assert "कोई परिहार नहीं" not in text, "Hindi absolute is back"


def test_ask_context_names_the_exemptions_the_overlay_refers_to():
    out = llm.format_guna_milan_for_prompt(_nadi_pair(), "A and B")
    # nd.unevaluated is fed the way bd.unevaluated is, or the overlay names
    # exemptions the model cannot see.
    assert f"  not evaluated: {M._NADI_UNEVALUATED[0]}" in out
    assert "gains no points from any mitigation" in out
    assert "not among the Bhakoot parih" in out
    assert not _ABSOLUTE.search(out)
    assert "NO cancelling" not in out
