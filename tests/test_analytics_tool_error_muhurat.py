"""#1070 (events-table row 8, the muhurat finder) -- /muhurat declares a `tool_error` event
on its error banner, through the #1067 marker. The last slice after #1390, #1402, #1411.

Vocabulary, fixed and re-checked in the template: `validation` (unknown event type,
invalid start date, city too long, all 400) and `compute` (the search itself failed, 500;
and a personal or couple chart that failed on an otherwise successful 200 render, where
the candidates are still shown under the banner). There is no `geocode` kind: a city that
fails to geocode raises inside the search and lands in `compute`, indistinguishable from
an ephemeris failure at this seam. Params are exactly {tool, kind}. Never the error text
(it echoes the exception, which can carry the city or a partner's place), the city or the
date.

The marker sits inside the template's existing `{% if error %}` branch, so a success
render, a bare GET and a shareable GET result cannot declare one. The metric counts error
RENDERS, not seekers: a reload re-fires it.

Not covered, on purpose: `llm_degraded` (the finder has no LLM) and any client/JS change.
Mutation rows: scripts/mutations/2026_11_24_1070_muhurat_tool_error.py.
"""
from __future__ import annotations

import html
import json

import pytest

from test_analytics_tool_completion_events import markers, one

PLACE = "Mumbai, India"
SECRET_CITY = "Xyzzyville Quillfeather"
SECRET_MSG = "secret ephemeris meltdown"
DATE = "2026-12-01"
VIVAH_COUPLE = dict(
    bride_name="Brontamir Wexlow", bride_dob="1992-08-03", bride_time="06:10",
    bride_place="Delhi, India", groom_name="Zorvathi Quillfeather", groom_dob="1990-04-12",
    groom_time="14:35", groom_place=PLACE)


@pytest.fixture
def route():
    from astro_ai.routes import muhurat as R

    return R


def _post(client, **over):
    data = {"event_type": "griha_pravesh", "city": PLACE, "start_date": DATE,
            "days": "14", **over}
    return client.post("/muhurat", data=data)


def _only_error(r, kind):
    assert len(markers(r, "tool_error")) == 1, markers(r)
    p = one(r, "tool_error")
    assert set(p) == {"tool", "kind"}, p
    assert p == {"tool": "muhurat", "kind": kind}, p


def _boom(*a, **k):
    raise RuntimeError(SECRET_MSG)


# -- validation (400) -------------------------------------------------------
@pytest.mark.parametrize("label,over", [
    ("unknown event", {"event_type": "not_an_event"}),
    ("bad date", {"start_date": "2026-13-45"}),
    ("city too long", {"city": "c" * 101}),
])
def test_muhurat_a_refused_search_declares_tool_error_validation(client, route, label, over):
    assert len("c" * 101) > route.CITY_MAX_CHARS
    r = _post(client, **over)
    assert r.status_code == 400, (label, r.status_code)
    assert len(markers(r)) == 1, markers(r)
    _only_error(r, "validation")


def test_muhurat_a_bad_shared_link_declares_it_too(client):
    r = client.get("/muhurat", params={"event": "griha_pravesh", "city": PLACE,
                                       "start": "not-a-date", "days": 14})
    assert r.status_code == 400
    _only_error(r, "validation")


# -- compute (500, and the 200 with a failed personal/couple chart) ----------
def test_muhurat_a_failed_search_declares_tool_error_compute(client, route, monkeypatch):
    monkeypatch.setattr(route, "_search", _boom)
    r = _post(client)
    assert r.status_code == 500, r.status_code
    assert SECRET_MSG in r.text, "the banner is expected to echo the exception"
    assert len(markers(r)) == 1, markers(r)
    _only_error(r, "compute")


def test_muhurat_a_failed_personal_chart_declares_compute_and_still_shows_dates(
        client, saved_chart, route, monkeypatch):
    saved_chart()
    monkeypatch.setattr(route, "compute_chart", _boom)
    r = _post(client, use_personal="1")
    assert r.status_code == 200, r.status_code
    assert "Could not compute your chart" in r.text
    _only_error(r, "compute")
    one(r, "muhurat_searched")  # the candidates rendered: the search itself succeeded


def test_muhurat_a_failed_couple_chart_declares_compute_and_still_shows_dates(
        client, route, monkeypatch):
    monkeypatch.setattr(route, "compute_chart", _boom)
    r = _post(client, event_type="vivah", **VIVAH_COUPLE)
    assert r.status_code == 200, r.status_code
    assert "Couple mode disabled" in r.text
    _only_error(r, "compute")
    assert one(r, "muhurat_searched")["mode"] == "basic"


# -- no typed text, no error text -------------------------------------------
def test_muhurat_the_marker_carries_no_city_date_or_error_text(client, route, monkeypatch):
    real = route._search

    def stub(event_type, city, *a, **k):
        if SECRET_CITY in city:
            raise RuntimeError(f"{SECRET_MSG} for {city}")
        return real(event_type, city, *a, **k)

    monkeypatch.setattr(route, "_search", stub)
    r = _post(client, city=SECRET_CITY)
    assert r.status_code == 500
    assert SECRET_CITY in r.text and SECRET_MSG in r.text, "the banner is expected to echo both"
    _only_error(r, "compute")
    blob = repr(markers(r))
    for secret in (SECRET_CITY, "Xyzzy", "Quillfeather", SECRET_MSG, "meltdown", DATE, "2026"):
        assert secret not in blob, f"the tool_error marker leaked {secret!r}: {blob}"
    assert "'tool_error'" in blob and "griha" not in blob


def test_muhurat_the_raw_marker_attribute_is_exactly_tool_and_kind(client):
    r = _post(client, start_date="nope", city=SECRET_CITY)
    assert r.status_code == 400
    raw = r.text.split('data-analytics-event="tool_error"', 1)[1].split("</div>", 1)[0]
    params = json.loads(html.unescape(raw.split("data-analytics-params='", 1)[1].split("'", 1)[0]))
    assert params == {"tool": "muhurat", "kind": "validation"}, params
    assert "Xyzzy" not in raw and "nope" not in raw and "city" not in raw, raw


# -- success and bare renders carry none ------------------------------------
def test_muhurat_no_marker_on_a_success_a_shared_link_or_the_bare_form(client):
    post = _post(client)
    assert post.status_code == 200
    assert markers(post, "tool_error") == []
    assert len(markers(post, "muhurat_searched")) == 1
    get = client.get("/muhurat", params={"event": "griha_pravesh", "city": PLACE,
                                         "start": DATE, "days": 14})
    assert get.status_code == 200
    assert markers(get, "tool_error") == []
    bare = client.get("/muhurat")
    assert bare.status_code == 200
    assert markers(bare, "tool_error") == []


# -- the template's whitelist -----------------------------------------------
@pytest.mark.parametrize("hostile", ["<script>", "geocode", None, ""])
def test_muhurat_the_template_only_ever_emits_a_known_kind(client, route, hostile):
    ctx = {"candidates": None, "error": "Invalid start date.", "error_kind": hostile,
           "lang": "en", "prefill_city": "", "prefill_start": "",
           "event_types": [("vivah", "Vivah")], "selected_event": "vivah",
           "has_saved_chart": False, "use_personal": False, "via_get": False}
    from starlette.requests import Request

    scope = {"type": "http", "method": "POST", "path": "/muhurat", "headers": [],
             "query_string": b"", "app": client.app}
    resp = route.templates.TemplateResponse(Request(scope), "muhurat_finder.html", ctx,
                                            status_code=400)
    body = resp.body.decode()
    got = markers(type("R", (), {"text": body}), "tool_error")
    assert got == [("tool_error", {"tool": "muhurat", "kind": "validation"})], got
    assert "<script>" not in body.split('data-analytics-event="tool_error"', 1)[1].split("</div>", 1)[0]
