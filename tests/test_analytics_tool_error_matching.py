"""#1416 -- /matching declares a `tool_error` event on its error render, through the #1067
marker (#1070 slice 8, the failure half of `matching_completed`).

`routes/matching.py` catches `ChartError` (a bad date, or a place that will not geocode),
a 400 rendered through the shared `error.html`. So the vocabulary is the single word
`validation`. Params are exactly {tool, kind}. Never the error text (it echoes the typed
place), the names or the birth data.

`error.html` is shared by outlook, panchang, ask, rashifal, dasha, today, subscribe, kundli
and the main.py handlers, so the marker is OPT-IN: only a route that sets `tool_error_tool`
declares one, and today only /matching does. The metric counts error RENDERS, not seekers:
a reload re-fires it.

Mutation rows: scripts/mutations/2026_11_23_1416_tool_error_matching.py.
"""
from __future__ import annotations

import pytest

from test_analytics_tool_completion_events import B, G, PLACE_A, markers, match_llm, one  # noqa: F401

BAD_CITY = "Xyzzyville Nowhereland"
FIXED = {"tool": "matching", "kind": "validation"}


@pytest.fixture
def matching_route():
    from astro_ai.routes import matching as M

    return M


@pytest.fixture
def bad_city(matching_route, monkeypatch):
    """routes/matching.py binds its own `compute_chart`, which `failing_geocode` (it patches
    `deps`) does not reach, so the failure is installed on this module."""
    from astro_ai.chart import ChartError

    real = matching_route.compute_chart

    def stub(d, t, place):
        if BAD_CITY in place:
            raise ChartError(f"Could not find {place!r}")
        return real(d, t, place)

    monkeypatch.setattr(matching_route, "compute_chart", stub)


def _forced(module, monkeypatch, **extra):
    """Make `module.templates` add `extra` to every render context."""
    real = module.templates

    class Forced:
        def TemplateResponse(self, request, name, ctx, **kw):
            return real.TemplateResponse(request, name, {**ctx, **extra}, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(module, "templates", Forced())


def _marker_html(r) -> str:
    return r.text.split('data-analytics-event="tool_error"', 1)[1].split("</div>", 1)[0]


def test_a_refused_date_declares_tool_error_validation(client):
    r = client.post("/matching", data={**G, **B, "g_birth_date": "not-a-date"})
    assert r.status_code == 400, r.status_code
    assert len(markers(r)) == 1, markers(r)
    p = one(r, "tool_error")
    assert set(p) == {"tool", "kind"}, p
    assert p == FIXED, p


def test_a_refused_bride_date_declares_the_same_marker(client):
    r = client.post("/matching", data={**G, **B, "b_birth_date": "not-a-date"})
    assert r.status_code == 400
    assert markers(r) == [("tool_error", FIXED)]


def test_a_failed_geocode_declares_the_same_marker(client, bad_city):
    r = client.post("/matching", data={**G, **B, "b_birth_place": BAD_CITY})
    assert r.status_code == 400, r.status_code
    assert BAD_CITY in r.text, "the error banner is expected to echo the typed city"
    assert len(markers(r)) == 1, markers(r)
    assert one(r, "tool_error") == FIXED


def test_the_marker_carries_no_typed_text(client, bad_city):
    for data in ({**G, **B, "g_birth_date": "not-a-date"}, {**G, **B, "b_birth_place": BAD_CITY}):
        r = client.post("/matching", data=data)
        assert r.status_code == 400
        blob = repr(markers(r))
        for secret in ("Zorvathi", "Quillfeather", "Brontamir", "Wexlow", "Mumbai", "Delhi",
                       PLACE_A, "not-a-date", "Xyzzy", BAD_CITY, "14:35", "06:10", "1990",
                       "1992", "Could not", "Couldn't compute", "Invalid", "date", "place"):
            assert secret not in blob, f"the tool_error marker leaked {secret!r}: {blob}"


def test_no_marker_on_a_get_or_a_success(client, match_llm):
    assert markers(client.get("/matching"), "tool_error") == []
    ok = client.post("/matching", data={**G, **B})
    assert ok.status_code == 200
    assert markers(ok, "matching_completed") != []
    assert markers(ok, "tool_error") == []


def test_the_template_only_ever_emits_a_known_kind(client, matching_route, monkeypatch):
    _forced(matching_route, monkeypatch, tool_error_kind="<script>")
    r = client.post("/matching", data={**G, **B, "g_birth_date": "not-a-date"})
    assert r.status_code == 400
    assert one(r, "tool_error") == FIXED
    assert "<script>" not in _marker_html(r)


@pytest.mark.parametrize("tool", ["outlook", "<script>", "", None, "Matching"])
def test_only_the_matching_opt_in_declares_it(client, matching_route, monkeypatch, tool):
    """Any other value of the opt-in, forced through the same route, declares nothing: the
    template names the tool itself, so a route cannot send an arbitrary `tool`."""
    _forced(matching_route, monkeypatch, tool_error_tool=tool)
    r = client.post("/matching", data={**G, **B, "g_birth_date": "not-a-date"})
    assert r.status_code == 400
    assert markers(r, "tool_error") == [] and "tool_error" not in r.text


def test_the_route_context_sets_the_fixed_opt_in(client, matching_route, monkeypatch):
    """The template re-checks `tool_error_kind`, so a wrong word from the route is invisible
    in the rendered marker; this pins the route's own side."""
    seen = {}
    real = matching_route.templates

    class Spy:
        def TemplateResponse(self, request, name, ctx, **kw):
            seen.update(ctx)
            return real.TemplateResponse(request, name, ctx, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(matching_route, "templates", Spy())
    client.post("/matching", data={**G, **B, "g_birth_date": "not-a-date"})
    assert seen["tool_error_tool"] == "matching" and seen["tool_error_kind"] == "validation", seen


# -- every other error.html render stays silent --------------------------------
def test_other_error_renders_cannot_fire_it(client):
    """Cheapest real triggers of error.html from other routes: an unknown rashi (404), a bad
    panchang date (404) and an out-of-range one (400), and the main.py HTTPException handler
    (401 on /admin). Not reached here: outlook, dasha and today (they need a saved-chart
    cookie plus a failing geocode), ask's no-key and chart-error paths, subscribe and kundli;
    they set no `tool_error_tool`, which is what keeps them silent, and the forced-context
    tests above pin that any other value declares nothing."""
    triggered = [
        client.get("/rashifal/notarashi"),
        client.get("/hi/rashifal/notarashi"),
        client.get("/panchang/not-a-date"),
        client.get("/panchang/1850-01-01"),
        client.get("/admin"),
    ]
    reached = [r for r in triggered if "bg-rose-50 border border-rose-200" in r.text]
    assert len(reached) == len(triggered), [r.status_code for r in triggered]
    for r in reached:
        assert r.status_code >= 400
        assert all(p.get("tool") != "matching" for _, p in markers(r, "tool_error")), markers(r)
