"""#1402 -- /ask and /panchang declare a `tool_error` event on their error branch,
through the #1067 marker (#1070 slice 6, the templates #1390 left).

Vocabulary, fixed and re-checked in the template: ask `validation` (too short or too
long, both 400) and `quota` (429); panchang `geocode` (the requested city failed and
the Mumbai fallback was served, 200) and `compute` (the fallback failed too, so there
is no panchang at all). Params are exactly {tool, kind}. Never the error text, the
question or the city: the banner on /panchang echoes the typed city and the /ask page
echoes the question, so either would carry typed text into GA4.

The marker sits inside each template's existing `{% if error %}` branch, so a success
render and the `answer_expired` notice (not an error) cannot declare one. On /panchang
the metric counts error RENDERS, not seekers: a reload re-fires it.

Not covered, on purpose: ask's `error.html` paths (no key, ChartError, LLM failure),
muhurat and dosha. Mutation rows: scripts/mutations/2026_11_23_1402_tool_error_ask_panchang.py.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from test_analytics_tool_completion_events import markers, one

QUESTION = "Will Zorvathi Quillfeather find a job soon?"
BAD_CITY = "Xyzzyville Nowhereland"


def _ask(client, question=QUESTION):
    return client.post("/ask", data={"question": question, "category": "career"},
                       follow_redirects=False)


@pytest.fixture
def panchang_route():
    from astro_ai.routes import panchang as R

    return R


@pytest.fixture
def bad_city(panchang_route, monkeypatch):
    """routes/panchang.py binds its own `compute_chart`, which `failing_geocode` (it
    patches `deps`) does not reach, so the failure is installed on this module."""
    real = panchang_route.compute_chart

    def stub(d, t, place):
        if BAD_CITY in place:
            raise RuntimeError(f"geocode failed for {place!r}")
        return real(d, t, place)

    monkeypatch.setattr(panchang_route, "compute_chart", stub)


# -- /ask -----------------------------------------------------------------
@pytest.mark.parametrize("label,question", [("too short", "hi"), ("too long", "q" * 601)])
def test_ask_a_refused_question_declares_tool_error_validation(client, saved_chart, label, question):
    saved_chart()
    r = _ask(client, question)
    assert r.status_code == 400, r.status_code
    assert len(markers(r)) == 1, markers(r)
    p = one(r, "tool_error")
    assert set(p) == {"tool", "kind"}, p
    assert p == {"tool": "ask", "kind": "validation"}, p


def test_ask_a_spent_quota_declares_tool_error_quota(client, saved_chart, monkeypatch):
    from astro_ai.routes import ask as ask_route

    saved_chart()
    monkeypatch.setattr(ask_route, "_ask_quota_remaining", lambda request: 0)
    r = _ask(client)
    assert r.status_code == 429, r.status_code
    assert len(markers(r)) == 1, markers(r)
    assert one(r, "tool_error") == {"tool": "ask", "kind": "quota"}


def test_ask_the_marker_carries_no_typed_text(client, saved_chart, monkeypatch):
    from astro_ai.routes import ask as ask_route

    saved_chart()
    monkeypatch.setattr(ask_route, "_ask_quota_remaining", lambda request: 0)
    r = _ask(client)
    assert "Zorvathi" in r.text, "the page is expected to echo the question"
    blob = repr(markers(r))
    for secret in ("Zorvathi", "Quillfeather", "job", "used today", "Come back", "career"):
        assert secret not in blob, f"the tool_error marker leaked {secret!r}: {blob}"


def test_ask_no_marker_on_a_get_or_on_an_expired_answer(client, saved_chart, monkeypatch):
    from astro_ai.routes import ask as ask_route

    saved_chart()
    assert markers(client.get("/ask"), "tool_error") == []
    monkeypatch.setattr(ask_route, "_ask_lookup", lambda *a, **k: None)
    r = client.get("/ask", params={"q": QUESTION, "c": "career"})
    assert r.status_code == 200
    assert "data-ask-expired" in r.text
    assert markers(r, "tool_error") == []


def test_ask_the_template_only_ever_emits_a_known_kind(client, saved_chart, monkeypatch):
    from astro_ai.routes import ask as R

    saved_chart()
    real = R.templates

    class Forced:
        def TemplateResponse(self, request, name, ctx, **kw):
            return real.TemplateResponse(request, name, {**ctx, "error_kind": "<script>"}, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(R, "templates", Forced())
    r = _ask(client, "hi")
    assert r.status_code == 400
    assert one(r, "tool_error") == {"tool": "ask", "kind": "validation"}
    assert "<script>" not in r.text.split('data-analytics-event="tool_error"', 1)[1].split("</div>", 1)[0]


# -- /panchang ------------------------------------------------------------
def test_panchang_a_failed_city_declares_tool_error_geocode(client, bad_city):
    r = client.get("/panchang", params={"city": BAD_CITY})
    assert r.status_code == 200
    assert BAD_CITY in r.text, "the banner is expected to echo the typed city"
    assert len(markers(r)) == 1, markers(r)
    p = one(r, "tool_error")
    assert set(p) == {"tool", "kind"}, p
    assert p == {"tool": "panchang", "kind": "geocode"}, p
    assert BAD_CITY not in repr(markers(r)) and "Xyzzy" not in repr(markers(r))


def test_panchang_the_archive_route_declares_it_too(client, bad_city):
    r = client.get("/panchang/2026-01-01", params={"city": BAD_CITY})
    assert r.status_code == 200
    assert one(r, "tool_error") == {"tool": "panchang", "kind": "geocode"}
    assert len(markers(r)) == 1, markers(r)


def test_panchang_a_failed_fallback_declares_tool_error_compute(client, panchang_route, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret ephemeris failure")

    monkeypatch.setattr(panchang_route, "compute_panchang", boom)
    r = client.get("/panchang", params={"city": "Delhi, India"})
    assert r.status_code == 200
    assert len(markers(r)) == 1, markers(r)
    assert one(r, "tool_error") == {"tool": "panchang", "kind": "compute"}
    assert "secret" not in repr(markers(r))


def test_panchang_no_marker_on_a_good_city(client):
    for url in ("/panchang", "/panchang/2026-01-01"):
        r = client.get(url, params={"city": "Delhi, India"})
        assert r.status_code == 200
        assert markers(r, "tool_error") == [], url


def test_panchang_the_template_only_ever_emits_a_known_kind(client, bad_city, panchang_route, monkeypatch):
    R = panchang_route
    real = R.templates

    class Forced:
        def TemplateResponse(self, request, name, ctx, **kw):
            return real.TemplateResponse(request, name, {**ctx, "error_kind": "<script>"}, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(R, "templates", Forced())
    r = client.get("/panchang", params={"city": BAD_CITY})
    assert one(r, "tool_error") == {"tool": "panchang", "kind": "geocode"}
    assert "<script>" not in r.text.split('data-analytics-event="tool_error"', 1)[1].split("</div>", 1)[0]
