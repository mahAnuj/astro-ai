"""The subscribe modal must not open over a tool result (#382).

Measured on production 2026-10-15, 10-29 and 11-06: on a fresh profile,
submitting /numerology or /matching renders the result, the page's own script
counts that load as "visit 2" (`SHOW_AT_VISITS = [2, 5]`) and 1.5 s later a
full-screen "Rashifal in your inbox" modal covers the score the visitor came for.

The fix is two halves, and each is pinned here because either alone is inert:

  * the result states of /matching, /numerology and /numerology/compatibility
    render `<span data-subscribe-defer hidden>`; the empty forms do not;
  * `_subscribe_modal.html` returns on that marker BEFORE it counts the visit, so
    the next ordinary load is the one that reaches the threshold (a marker check
    placed after the increment would skip visit 2 and wait for visit 5).

The JS itself has no browser test here, so the second half is an ordering check
on the template source, and the first half drives the real routes.
"""
from __future__ import annotations

import re
from pathlib import Path

_MODAL = Path(__file__).resolve().parents[1] / "src/astro_ai/templates/_subscribe_modal.html"
_MARK = "<span data-subscribe-defer hidden></span>"   # the element, not the attribute name: the modal script quotes the name


def _post_matching(client, stub_llm):
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)
    r = client.post("/matching", data={
        "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00",
        "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": "1990-01-10", "b_birth_time": "10:00",
        "b_birth_place": "Mumbai",
    })
    assert r.status_code == 200, r.status_code
    return r.text


def test_matching_result_carries_the_defer_marker(client, stub_llm):
    assert _MARK in _post_matching(client, stub_llm)


def test_matching_empty_form_does_not(client):
    r = client.get("/matching")
    assert r.status_code == 200
    assert _MARK not in r.text


def test_numerology_result_carries_the_defer_marker(client):
    r = client.post("/numerology", data={"name": "Asha Rao", "birth_date": "1990-05-17"})
    assert r.status_code == 200
    assert "Life Path" in r.text, "the reading did not render; the test proves nothing"
    assert _MARK in r.text


def test_numerology_empty_form_does_not(client):
    r = client.get("/numerology")
    assert r.status_code == 200
    assert _MARK not in r.text


def test_numerology_compat_form_does_not(client):
    r = client.get("/numerology/compatibility")
    assert r.status_code == 200
    assert _MARK not in r.text


def test_the_gate_checks_the_marker_before_it_counts_the_visit():
    src = _MODAL.read_text(encoding="utf-8")
    gate = src[src.index("Auto-show gate"):]
    marker = gate.index("data-subscribe-defer")
    assert re.search(r"if \(document\.querySelector\('\[data-subscribe-defer\]'\)\) return;",
                     gate), "the marker is not checked with an early return"
    assert marker < gate.index("localStorage.setItem(VISITS_KEY"), (
        "the marker is checked after the visit is counted: a result load would "
        "burn visit 2 and push the prompt out to visit 5")
    assert marker > gate.index("INTENT_KEY) !== '1') return"), (
        "the marker check must come after the intent gate, which it is a refinement of")
