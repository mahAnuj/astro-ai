"""#1411 -- the three dosha checks declare a `tool_error` event on their error branch,
through the #1067 marker (#1070 slice 7, the failure half of `dosha_check_completed`).

`dosha_check_form.html` serves /manglik-check, /sade-sati-check and /kaal-sarp-check, and
every error render comes from one place: `ChartError` on the POST (a bad date, or a place
that will not geocode), a 400. So the vocabulary is the single word `validation`, fixed by
the route and re-checked in the template. Params are exactly {tool, kind}. Never the error
text (it can echo the typed place), the name or the birth data. `tool` is the template's
own `_tool` (the #1226 `data-tool` value), which equals `dosha_check_completed`'s `check`.

The marker sits inside the existing `{% if error %}` branch, so a GET and a success render
cannot declare one. The metric counts error RENDERS, not seekers: a reload re-fires it.

Mutation rows: scripts/mutations/2026_11_23_1411_tool_error_dosha.py.
"""
from __future__ import annotations

import pytest

from test_analytics_tool_completion_events import BIRTH, PLACE_A, markers, one

BAD_CITY = "Xyzzyville Nowhereland"
CASES = [("/manglik-check", "manglik"), ("/sade-sati-check", "sade_sati"),
         ("/kaal-sarp-check", "kaal_sarp")]


@pytest.fixture
def dosha_route():
    from astro_ai.routes import dosha as R

    return R


@pytest.fixture
def bad_city(dosha_route, monkeypatch):
    """routes/dosha.py binds its own `compute_chart`, which `failing_geocode` (it patches
    `deps`) does not reach, so the failure is installed on this module."""
    from astro_ai.chart import ChartError

    real = dosha_route.compute_chart

    def stub(d, t, place):
        if BAD_CITY in place:
            raise ChartError(f"Could not find {place!r}")
        return real(d, t, place)

    monkeypatch.setattr(dosha_route, "compute_chart", stub)


@pytest.mark.parametrize("path,tool", CASES)
def test_a_refused_date_declares_tool_error_validation(client, path, tool):
    r = client.post(path, data={**BIRTH, "birth_date": "not-a-date"})
    assert r.status_code == 400, r.status_code
    assert len(markers(r)) == 1, markers(r)
    p = one(r, "tool_error")
    assert set(p) == {"tool", "kind"}, p
    assert p == {"tool": tool, "kind": "validation"}, p


@pytest.mark.parametrize("path,tool", CASES)
def test_a_failed_geocode_declares_the_same_marker(client, bad_city, path, tool):
    r = client.post(path, data={**BIRTH, "birth_place": BAD_CITY})
    assert r.status_code == 400, r.status_code
    assert BAD_CITY in r.text, "the error banner is expected to echo the typed city"
    assert len(markers(r)) == 1, markers(r)
    assert one(r, "tool_error") == {"tool": tool, "kind": "validation"}


@pytest.mark.parametrize("path,tool", CASES)
def test_the_error_tool_equals_the_completion_check(client, path, tool):
    ok = client.post(path, data=BIRTH)
    assert ok.status_code == 200
    check = one(ok, "dosha_check_completed")["check"]
    bad = client.post(path, data={**BIRTH, "birth_date": "not-a-date"})
    assert one(bad, "tool_error")["tool"] == check, (check, markers(bad))


@pytest.mark.parametrize("path,tool", CASES)
def test_the_marker_carries_no_typed_text(client, bad_city, path, tool):
    for data in ({**BIRTH, "birth_date": "not-a-date"}, {**BIRTH, "birth_place": BAD_CITY}):
        r = client.post(path, data=data)
        assert r.status_code == 400
        blob = repr(markers(r))
        for secret in ("Zorvathi", "Quillfeather", "Mumbai", PLACE_A, "not-a-date", "Xyzzy",
                       BAD_CITY, "14:35", "1990", "Could not", "Invalid", "date", "place"):
            assert secret not in blob, f"the tool_error marker leaked {secret!r}: {blob}"


@pytest.mark.parametrize("path,tool", CASES)
def test_no_marker_on_a_get_or_a_success(client, path, tool):
    assert markers(client.get(path), "tool_error") == []
    ok = client.post(path, data=BIRTH)
    assert ok.status_code == 200
    assert markers(ok, "dosha_check_completed") != []
    assert markers(ok, "tool_error") == []


@pytest.mark.parametrize("path,tool", CASES)
def test_the_template_only_ever_emits_a_known_kind(client, dosha_route, monkeypatch, path, tool):
    R = dosha_route
    real = R.templates

    class Forced:
        def TemplateResponse(self, request, name, ctx, **kw):
            return real.TemplateResponse(request, name, {**ctx, "error_kind": "<script>"}, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(R, "templates", Forced())
    r = client.post(path, data={**BIRTH, "birth_date": "not-a-date"})
    assert r.status_code == 400
    assert one(r, "tool_error") == {"tool": tool, "kind": "validation"}
    assert "<script>" not in r.text.split('data-analytics-event="tool_error"', 1)[1].split("</div>", 1)[0]


def test_an_unrecognised_form_action_declares_nothing_and_does_not_raise(client, dosha_route, monkeypatch):
    """The #1226 `_tool` lookup yields nothing for an action it does not know, so an error
    render for one must stay silent rather than send `tool=None`."""
    R = dosha_route
    real = R.templates

    class Forced:
        def TemplateResponse(self, request, name, ctx, **kw):
            return real.TemplateResponse(
                request, name, {**ctx, "form_action": "/x", "error": "e", "error_kind": "validation"}, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(R, "templates", Forced())
    r = client.get("/manglik-check")
    assert r.status_code == 200
    assert 'class="mb-4 p-3 bg-red-50' in r.text, "the error branch must have rendered"
    assert markers(r, "tool_error") == [] and "tool_error" not in r.text


def test_the_route_context_names_the_fixed_kind_only_on_an_error(dosha_route):
    """The template re-checks `error_kind` against its one-word whitelist, so a wrong word
    from the route is invisible in the rendered marker; this pins the route's own side."""
    args = dict(page_title="t", page_lead="l", form_action="/manglik-check",
                submit_label="s", meta_desc="m")
    assert dosha_route._dosha_form_ctx(**args, error="Could not find 'Xyzzy'")["error_kind"] == "validation"
    assert dosha_route._dosha_form_ctx(**args)["error_kind"] is None
