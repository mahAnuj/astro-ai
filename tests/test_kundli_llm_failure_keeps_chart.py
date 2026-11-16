"""#1088: an LLM failure must not withhold the chart `/kundli` already computed.

`_render_natal_for` computes the lagna, planets, nakshatras, divisional charts,
yogas, Manglik, Sade Sati and the dasha strip before it asks a model for prose.
When generation raised (Groq quota exhausted, a 413, anything else) the route
returned `error.html` with a 503/502 and threw all of it away: during #266's
window every seeker got "High demand right now" and no chart, although
everything but the written chapters was ready.

Each test is a way the first fix could have been wrong:
  * the page is 200 and carries the chart, not just a prettier error;
  * the failure is not recorded as a generation (no owner alert, no
    `form_kundli` event) and is not saved to the seeker's history;
  * nothing is cached, so the next GET really does retry the model;
  * a structural 413 does not invite a retry that builds the same request;
  * share/email controls that need a reading are not offered without one.
"""
from __future__ import annotations

import pytest

from astro_ai import providers
from astro_ai.routes import kundli as K

# Varanasi 1990-08-15 23:55 — the issue's measured chart; Moon in Mrigashira.
BIRTH = dict(name="A", birth_date="1990-08-15", birth_time="23:55",
             birth_place="Varanasi, India")

READING = "## Personality\n" + ("The reading body. " * 40) + "\n"


def _raise(exc):
    def _fn(*a, **k):
        raise exc
    return _fn


@pytest.fixture
def spies(monkeypatch):
    """Count owner alerts and activity events fired from the render path."""
    seen = {"alerts": 0, "events": []}
    monkeypatch.setattr(K.notify, "kundli_generated",
                        lambda **kw: seen.__setitem__("alerts", seen["alerts"] + 1))
    monkeypatch.setattr(K.events, "record",
                        lambda **kw: seen["events"].append(kw.get("type")))
    return seen


def _page(client, saved_chart, path="/kundli"):
    saved_chart(**BIRTH)
    return client.get(path)


@pytest.mark.parametrize("exc", [
    providers.AllProvidersExhausted("x"),
    providers.RequestTooLarge("x"),
    ValueError("boom"),
])
def test_llm_failure_still_renders_the_computed_chart(client, saved_chart, monkeypatch, exc):
    monkeypatch.setattr(K, "generate_reading", _raise(exc))
    r = _page(client, saved_chart)

    assert r.status_code == 200, f"{r.status_code}: the computed chart was withheld"
    assert "Mrigashira" in r.text, "the Moon nakshatra, computed without the LLM, is missing"
    assert "data-reading-unavailable" in r.text, "no notice where the reading would sit"
    assert "High demand right now" not in r.text, "still rendering the error page"
    assert r.text.count("border-left: 3px solid #E4913C") == 1, (
        "exactly one left-ruled card (the notice) is expected, no reading chapters"
    )


def test_a_failed_generation_is_not_recorded_as_a_generation(
        client, saved_chart, monkeypatch, spies):
    monkeypatch.setattr(K, "generate_reading", _raise(providers.AllProvidersExhausted("x")))
    _page(client, saved_chart)

    assert spies["alerts"] == 0, "owner alert fired for a reading that was never generated"
    assert "form_kundli" not in spies["events"], "activity event fired for a failed generation"


def test_a_failed_generation_is_not_cached_so_the_next_get_retries(
        client, saved_chart, monkeypatch, spies):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            raise providers.AllProvidersExhausted("x")
        return READING

    monkeypatch.setattr(K, "generate_reading", flaky)
    saved_chart(**BIRTH)

    first = client.get("/kundli")
    second = client.get("/kundli")
    third = client.get("/kundli")

    assert calls["n"] == 3, f"{calls['n']} model calls for 3 GETs: a failure was cached"
    assert "data-reading-unavailable" in first.text
    assert "data-reading-unavailable" in second.text
    assert "data-reading-unavailable" not in third.text
    assert "The reading body." in third.text
    assert spies["alerts"] == 1 and spies["events"].count("form_kundli") == 1, (
        "the recovery render is the one fresh generation and fires once"
    )


def test_degraded_page_is_never_shared_cacheable(client, saved_chart, monkeypatch):
    monkeypatch.setattr(K, "generate_reading", _raise(providers.AllProvidersExhausted("x")))
    r = _page(client, saved_chart)
    assert "no-store" in r.headers.get("cache-control", "")


def test_retry_is_offered_for_congestion_but_not_for_a_413(client, saved_chart, monkeypatch):
    saved_chart(**BIRTH)
    monkeypatch.setattr(K, "generate_reading", _raise(providers.AllProvidersExhausted("x")))
    busy = client.get("/kundli")
    monkeypatch.setattr(K, "generate_reading", _raise(providers.RequestTooLarge("x")))
    too_large = client.get("/kundli")

    assert "data-reading-retry" in busy.text
    assert "data-reading-retry" not in too_large.text, (
        "a 413 builds the same request every time; inviting a retry cannot work"
    )
    assert "couple of minutes" not in too_large.text


def test_share_and_email_controls_are_not_offered_without_a_reading(
        client, saved_chart, monkeypatch):
    saved_chart(**BIRTH)
    monkeypatch.setattr(K, "generate_reading", lambda *a, **k: READING)
    ok = client.get("/kundli")
    client.cookies.clear()
    saved_chart(**BIRTH)
    monkeypatch.setattr(K, "generate_reading", _raise(providers.AllProvidersExhausted("x")))
    bad = client.get("/kundli")

    assert '<a href="#" data-whatsapp-share' in ok.text
    assert "<a href=\"#\" data-whatsapp-share" not in bad.text, (
        "WhatsApp share would POST a snapshot request that must regenerate the failed reading"
    )
    assert "Share on WhatsApp" not in bad.text


def test_the_notice_is_in_hindi_on_a_hindi_page(client, saved_chart, monkeypatch):
    saved_chart(**BIRTH)
    monkeypatch.setattr(K, "generate_reading", _raise(providers.AllProvidersExhausted("x")))
    r = client.get("/kundli?lang=hi")

    assert r.status_code == 200
    assert "data-reading-unavailable" in r.text
    assert "आपका लिखित पठन अभी तैयार नहीं है" in r.text
    # The retry keeps the language the seeker asked for.
    assert 'href="/kundli?lang=hi" data-reading-retry' in r.text
    assert "Your written reading isn't ready" not in r.text


def test_a_signed_in_seeker_gets_no_empty_reading_saved_to_history(
        client, saved_chart, monkeypatch):
    """History is the seeker's record of readings. An empty body saved on a
    failed generation would sit there as a reading that was never written."""
    from astro_ai.session import SessionUser

    saved = []
    user = SessionUser(email="a@example.com", name="A", sub="sub-1", since="2026-01-01")
    monkeypatch.setattr(K, "load_user", lambda request: user)
    monkeypatch.setattr(K.users, "save_reading", lambda **kw: saved.append(kw))
    monkeypatch.setattr(K, "generate_reading", _raise(providers.AllProvidersExhausted("x")))

    r = _page(client, saved_chart)

    assert r.status_code == 200
    assert saved == [], f"saved a reading to history for a failed generation: {saved}"
