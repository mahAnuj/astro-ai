"""#1217 -- matching, numerology, muhurat and the three dosha checks declare a
completion event (#1070 rows 3-6), through the #1067 marker.

Unlike kundli_generated and ask_answered (#1068), none of these results has a GET
that re-shows it: each is the body of the POST that computed it, so the success
render IS the completion and no one-shot flag is needed. What has to hold is the
other half -- an error, validation or empty render carries NO marker, or the
event stops being a completion count.

Each test drives the real route through TestClient (geocoding is stubbed by
conftest, the LLM by `stub_llm`) and reads the marker out of the HTML the way
analytics.js does: the attribute value is HTML-unescaped, then JSON-parsed.

Not covered: that GA4 receives the event (test_analytics_declared_events covers
declare -> fire under Node) or that the custom dimensions are registered (owner
admin step on #1070).

Mutation rows: scripts/mutations/2026_11_18_1217_completion_events.py.
"""
from __future__ import annotations

import html
import json
import re

import pytest

_MARKER = re.compile(
    r'<div hidden data-analytics-event="(?P<name>[a-z_]+)" '
    r"data-analytics-params='(?P<params>[^']*)'></div>"
)

# Distinctive strings, so a leak cannot be mistaken for a vocabulary word.
NAME_A, NAME_B = "Zorvathi Quillfeather", "Brontamir Wexlow"
PLACE_A, PLACE_B = "Mumbai, India", "Delhi, India"
G = {"g_name": NAME_A, "g_birth_date": "1990-04-12", "g_birth_time": "14:35",
     "g_birth_place": PLACE_A}
B = {"b_name": NAME_B, "b_birth_date": "1992-08-03", "b_birth_time": "06:10",
     "b_birth_place": PLACE_B}
BIRTH = {"name": NAME_A, "birth_date": "1990-04-12", "birth_time": "14:35",
         "birth_place": PLACE_A}


def markers(resp, name: str | None = None) -> list[tuple[str, dict]]:
    found = [(m["name"], json.loads(html.unescape(m["params"])))
             for m in _MARKER.finditer(resp.text)]
    return [f for f in found if name is None or f[0] == name]


def one(resp, name: str) -> dict:
    got = markers(resp, name)
    assert len(got) == 1, f"expected exactly one {name} marker, got {got}"
    return got[0][1]


@pytest.fixture
def match_llm(stub_llm):
    filler = "The two charts support steady, deliberate partnership. "
    stub_llm("## Overview\n" + filler * 10 + "\n\n## Detail\n" + filler * 10 + "\n")


@pytest.fixture
def results(client, match_llm):
    """One successful response per route, keyed by a short label."""
    return {
        "matching": client.post("/matching", data={**G, **B}),
        "numerology": client.post("/numerology", data={"name": NAME_A, "birth_date": "1990-04-12"}),
        "compat": client.post("/numerology/compatibility", data={
            "name_a": NAME_A, "birth_date_a": "1990-04-12",
            "name_b": NAME_B, "birth_date_b": "1992-08-03", "context": "marriage"}),
        "manglik": client.post("/manglik-check", data=BIRTH),
        "sade_sati": client.post("/sade-sati-check", data=BIRTH),
        "kaal_sarp": client.post("/kaal-sarp-check", data=BIRTH),
    }


# -- success renders carry exactly one marker ---------------------------------
def test_matching_success_carries_one_marker_with_a_band(results):
    r = results["matching"]
    assert r.status_code == 200
    p = one(r, "matching_completed")
    assert set(p) == {"lang", "score_band"}
    assert p["score_band"] in {"0-17", "18-24", "25-36"}
    assert p["lang"] in {"en", "hi"}


@pytest.mark.parametrize("total,band", [
    (0, "0-17"), (17, "0-17"), (17.5, "0-17"), (18, "18-24"), (24, "18-24"),
    (24.5, "18-24"), (25, "25-36"), (36, "25-36"),
])
def test_the_band_follows_the_36_point_total(client, match_llm, monkeypatch, total, band):
    from astro_ai.routes import matching as M

    real = M.compute_guna_milan

    def fixed(*a, **k):
        g = real(*a, **k)
        object.__setattr__(g, "total_awarded", total)
        return g

    monkeypatch.setattr(M, "compute_guna_milan", fixed)
    r = client.post("/matching", data={**G, **B})
    assert r.status_code == 200
    assert one(r, "matching_completed")["score_band"] == band


def test_numerology_reading_and_compat_carry_distinct_kinds(results):
    assert one(results["numerology"], "numerology_completed")["kind"] == "reading"
    assert one(results["compat"], "numerology_completed")["kind"] == "compat"
    for key in ("numerology", "compat"):
        assert set(one(results[key], "numerology_completed")) == {"lang", "kind"}


@pytest.mark.parametrize("key,check", [("manglik", "manglik"), ("sade_sati", "sade_sati"),
                                       ("kaal_sarp", "kaal_sarp")])
def test_each_dosha_check_carries_its_own_marker(results, key, check):
    r = results[key]
    assert r.status_code == 200
    p = one(r, "dosha_check_completed")
    assert p["check"] == check and set(p) == {"check", "lang"}
    assert len(markers(r)) == 1, "a result page must declare only its own event"


def _muhurat(client, **over):
    data = {"event_type": "griha_pravesh", "city": PLACE_A, "start_date": "2026-12-01",
            "days": "14", **over}
    return client.post("/muhurat", data=data)


def test_muhurat_search_with_candidates_carries_counts_and_mode(client):
    r = _muhurat(client)
    assert r.status_code == 200
    p = one(r, "muhurat_searched")
    assert set(p) == {"event_type", "days", "valid_count", "mode"}
    assert p["event_type"] == "griha_pravesh" and p["mode"] == "basic"
    assert p["days"] == 14 and isinstance(p["valid_count"], int)
    assert 0 <= p["valid_count"] <= p["days"]
    # #1322: the headline counts only excellent/good/acceptable; valid_count keeps the #1218
    # meaning (every non-avoid date, caution included), so it can only be >= the headline.
    from datetime import date

    from astro_ai import muhurat as MU
    rows = MU.find_candidates("griha_pravesh", PLACE_A, date(2026, 12, 1), 14)
    auspicious = sum(c.rating in ("excellent", "good", "acceptable") for c in rows)
    shown = re.search(r"(\d+) auspicious dates?</span>", r.text)
    assert shown, "the headline count did not render"
    assert int(shown.group(1)) == auspicious
    assert p["valid_count"] >= int(shown.group(1))
    assert p["valid_count"] == sum(c.rating != "avoid" for c in rows)


def test_muhurat_modes_are_derived_from_the_inputs_actually_used(client):
    couple = _muhurat(client, event_type="vivah",
                      bride_name=NAME_B, bride_dob="1992-08-03", bride_time="06:10",
                      bride_place=PLACE_B, groom_name=NAME_A, groom_dob="1990-04-12",
                      groom_time="14:35", groom_place=PLACE_A)
    assert one(couple, "muhurat_searched")["mode"] == "couple"
    namkaran = _muhurat(client, event_type="namkaran", child_dob="2026-10-01",
                        child_time="09:30", child_place=PLACE_A)
    assert one(namkaran, "muhurat_searched")["mode"] == "namkaran"
    # namkaran WITHOUT the child's details is a plain search, not the namkaran flow
    plain = _muhurat(client, event_type="namkaran")
    assert one(plain, "muhurat_searched")["mode"] == "basic"


def test_muhurat_personal_mode_needs_a_saved_chart(client, saved_chart):
    saved_chart()
    r = _muhurat(client, use_personal="1")
    assert one(r, "muhurat_searched")["mode"] == "personal"
    # Asking for it without a chart in the session is not personal mode.
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    r2 = _muhurat(TestClient(app), use_personal="1")
    assert one(r2, "muhurat_searched")["mode"] == "basic"


# -- error, validation and empty renders carry none ---------------------------
def test_the_get_forms_carry_no_marker(client):
    for path in ("/matching", "/numerology", "/numerology/compatibility", "/muhurat",
                 "/manglik-check", "/sade-sati-check", "/kaal-sarp-check"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert markers(r) == [], f"{path} declared an event with nothing computed"


def test_error_renders_carry_no_marker(client, match_llm):
    bad_matching = client.post("/matching", data={**G, **B, "g_birth_date": "not-a-date"})
    bad_numerology = client.post("/numerology", data={"name": "A", "birth_date": "1990-04-12"})
    bad_num_date = client.post("/numerology", data={"name": NAME_A, "birth_date": "1990-02-31"})
    bad_compat = client.post("/numerology/compatibility", data={
        "name_a": "A", "birth_date_a": "1990-04-12", "name_b": NAME_B, "birth_date_b": "1992-08-03"})
    bad_compat_date = client.post("/numerology/compatibility", data={
        "name_a": NAME_A, "birth_date_a": "1990-02-31", "name_b": NAME_B, "birth_date_b": "1992-08-03"})
    bad_event = _muhurat(client, event_type="nonsense")
    bad_date = _muhurat(client, start_date="not-a-date")
    bad_dosha = [client.post(p, data={**BIRTH, "birth_date": "not-a-date"})
                 for p in ("/manglik-check", "/sade-sati-check", "/kaal-sarp-check")]
    # #1390: the two numerology tools now declare `tool_error` on a refused submit, so for
    # them the rule is "no COMPLETION marker, and tool_error is the only one" (the tool_error
    # contract itself is tests/test_analytics_tool_error.py). The rest still carry nothing.
    # #1411: the three dosha checks join them (tests/test_analytics_tool_error_dosha.py).
    # #1416: so does /matching (tests/test_analytics_tool_error_matching.py).
    numerology_errors = [bad_numerology, bad_num_date, bad_compat, bad_compat_date,
                         bad_matching, *bad_dosha]
    others = [bad_event, bad_date]
    for r in [*numerology_errors, *others]:
        assert r.status_code >= 400, r.status_code
    for r in numerology_errors:
        assert markers(r, "numerology_completed") == [], "an error render declared a completion"
        assert markers(r, "dosha_check_completed") == [], "an error render declared a completion"
        assert [n for n, _ in markers(r)] == ["tool_error"], markers(r)
    for r in others:
        assert markers(r) == [], f"an error render declared {markers(r)}"


def test_a_failed_search_and_an_empty_one_carry_no_marker(client, monkeypatch):
    from astro_ai import muhurat as MU

    def boom(*a, **k):
        raise RuntimeError("ephemeris down")

    monkeypatch.setattr(MU, "find_candidates", boom)
    failed = _muhurat(client)
    assert failed.status_code == 500 and markers(failed) == []

    monkeypatch.setattr(MU, "find_candidates", lambda *a, **k: [])
    empty = _muhurat(client)
    assert empty.status_code == 200 and markers(empty) == []


# -- PII ----------------------------------------------------------------------
def test_no_marker_carries_a_name_place_date_or_free_text(results, client):
    pages = [*results.values(), _muhurat(client)]
    allowed = {
        "matching_completed": {"lang": {"en", "hi"}, "score_band": {"0-17", "18-24", "25-36"}},
        "numerology_completed": {"lang": {"en", "hi"}, "kind": {"reading", "compat"}},
        "dosha_check_completed": {"lang": {"en", "hi"},
                                  "check": {"manglik", "sade_sati", "kaal_sarp"}},
    }
    seen = set()
    for r in pages:
        for name, params in markers(r):
            seen.add(name)
            blob = json.dumps(params)
            for secret in (NAME_A, NAME_B, "Zorvathi", "Brontamir", "Mumbai", "Delhi",
                           "1990", "1992", "14:35", "06:10"):
                assert secret not in blob, f"{name} leaked {secret!r}: {blob}"
            if name == "muhurat_searched":
                assert all(isinstance(v, (int, str)) for v in params.values())
                assert params["mode"] in {"basic", "personal", "couple", "namkaran"}
                assert re.fullmatch(r"[a-z_]+", params["event_type"])
                continue
            for k, v in params.items():
                assert v in allowed[name][k], f"{name}.{k}={v!r} is outside its vocabulary"
    assert seen == {"matching_completed", "numerology_completed", "dosha_check_completed",
                    "muhurat_searched"}
