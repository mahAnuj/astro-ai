"""#1390 -- the two numerology tools declare a `tool_error` event when a seeker's
submit comes back as an error, through the #1067 marker.

#1226 counts submits and #1217 counts completions; without this the gap between
them cannot be told apart into "mistyped a field" and "our maths raised". `kind`
is that split: `validation` (the seeker's input was refused) or `compute` (the
`except Exception` branch, the one that pages us through `_fire_error_alert`).

Params are exactly {tool, kind}, a fixed vocabulary. Never the error text: the
`compute` message is `f"Couldn't compute: {err}"` and a rejected-date message
echoes what was typed, so either would carry a name or a birth date into GA4.

Only these two tools are wired. matching, muhurat and the dosha checks render
their errors differently and are not covered here, and `llm_degraded` is not
declared at all: both numerology pages are pure maths, no LLM, so it could never
fire. Mutation rows: scripts/mutations/2026_11_22_1390_tool_error.py.
"""
from __future__ import annotations

import pytest

from test_analytics_tool_completion_events import markers, one

NAME_A, NAME_B = "Zorvathi Quillfeather", "Brontamir Wexlow"

NUM = {"name": NAME_A, "birth_date": "1990-04-12"}
COMPAT = {"name_a": NAME_A, "birth_date_a": "1990-04-12",
          "name_b": NAME_B, "birth_date_b": "1992-08-03", "context": "marriage"}

NUM_URL = "/numerology"
COMPAT_URL = "/numerology/compatibility"

# (label, url, form, expected tool) -- the branches whose kind is `validation`.
VALIDATION = [
    ("num short name", NUM_URL, {**NUM, "name": "A"}, "numerology"),
    ("num mixed script", NUM_URL, {**NUM, "name": "Zorvathi अनुज"}, "numerology"),
    ("num impossible date", NUM_URL, {**NUM, "birth_date": "1990-02-31"}, "numerology"),
    ("num not a date", NUM_URL, {**NUM, "birth_date": "not-a-date"}, "numerology"),
    ("compat short name", COMPAT_URL, {**COMPAT, "name_a": "A"}, "numerology_compat"),
    ("compat non-latin", COMPAT_URL, {**COMPAT, "name_b": "अनुज"},
     "numerology_compat"),
    ("compat impossible date", COMPAT_URL, {**COMPAT, "birth_date_a": "1990-02-31"},
     "numerology_compat"),
    ("compat not a date", COMPAT_URL, {**COMPAT, "birth_date_b": "not-a-date"},
     "numerology_compat"),
]


def _assert_only_tool_error(r, tool: str, kind: str) -> None:
    assert r.status_code == 400, r.status_code
    p = one(r, "tool_error")
    assert set(p) == {"tool", "kind"}, p
    assert p == {"tool": tool, "kind": kind}, p
    assert markers(r, "numerology_completed") == [], "an error render also claimed a completion"
    assert len(markers(r)) == 1, f"an error render declared more than tool_error: {markers(r)}"


@pytest.mark.parametrize("label,url,form,tool", VALIDATION, ids=[v[0] for v in VALIDATION])
def test_a_refused_input_declares_tool_error_validation(client, label, url, form, tool):
    _assert_only_tool_error(client.post(url, data=form), tool, "validation")


def test_an_exception_in_the_maths_declares_tool_error_compute_without_the_text(client, monkeypatch):
    from astro_ai import numerology as _num

    def boom(*a, **k):
        raise RuntimeError("secret NAME_A")

    monkeypatch.setattr(_num, "compute", boom)
    monkeypatch.setattr(_num, "compute_compatibility", boom)
    for url, form, tool in ((NUM_URL, NUM, "numerology"), (COMPAT_URL, COMPAT, "numerology_compat")):
        r = client.post(url, data=form)
        _assert_only_tool_error(r, tool, "compute")
        # The page itself shows the message; the MARKER must not.
        assert "secret NAME_A" in r.text
        blob = repr(markers(r))
        for secret in ("secret", "NAME_A", "RuntimeError", "Couldn't compute", NAME_A, NAME_B,
                       "Zorvathi", "Brontamir", "1990", "1992"):
            assert secret not in blob, f"the tool_error marker leaked {secret!r}: {blob}"


def test_a_success_render_and_a_get_declare_no_tool_error(client):
    for url, form in ((NUM_URL, NUM), (COMPAT_URL, COMPAT)):
        ok = client.post(url, data=form)
        assert ok.status_code == 200
        assert markers(ok, "tool_error") == []
        assert len(markers(ok, "numerology_completed")) == 1
        assert markers(client.get(url), "tool_error") == []


@pytest.mark.parametrize("url,form,tool", [(NUM_URL, {**NUM, "name": "A"}, "numerology"),
                                           (COMPAT_URL, {**COMPAT, "name_a": "A"}, "numerology_compat")])
def test_the_template_only_ever_emits_a_known_kind(client, monkeypatch, url, form, tool):
    """The route's word is re-checked in the template: anything outside the two-word
    vocabulary reads as 'compute', and nothing in it can break out of the attribute."""
    from astro_ai.routes import numerology as R

    real = R.templates

    class Forced:
        def TemplateResponse(self, request, name, ctx, **kw):
            return real.TemplateResponse(request, name, {**ctx, "error_kind": "<script>"}, **kw)

        def __getattr__(self, attr):
            return getattr(real, attr)

    monkeypatch.setattr(R, "templates", Forced())
    r = client.post(url, data=form)
    assert r.status_code == 400
    assert one(r, "tool_error") == {"tool": tool, "kind": "compute"}
    assert "<script>" not in r.text.split("data-analytics-event=\"tool_error\"", 1)[1].split("</div>", 1)[0]
