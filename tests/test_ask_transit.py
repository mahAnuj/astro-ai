"""#402 AC3 — `/ask` carries the slow-planet transit block, and its cache key knows.

What these tests are, and are not. They assert on TEXT and KEYS: what the block
says, where it sits in the user message, which moment reaches the ephemeris, and
that GET and POST file an answer under one key. They do NOT verify what a model
does with the block — no provider is called anywhere here, and whether the
framing actually keeps answers honest is unmeasured until a live probe runs.

The two failure shapes this guards, both from this repo's history:

* a key that GET and POST derive differently (#181): POST writes an answer GET
  can never read, so the seeker lands on their own question with no answer;
* an answer generated WITH a sky and cached under a key that does not name it,
  so it is served after Saturn has changed sign.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from astro_ai import ask_transit, cache, chart, llm
from astro_ai.routes import ask as ask_route
from astro_ai.routes import deps
from astro_ai.session import SavedChart

QUESTION = "Will I clear my exam this year?"
SAVED = SavedChart(id="c1", name="Test", birth_date="1990-04-15",
                   birth_time="07:30", birth_place="New Delhi")


def _natal():
    return chart.compute_chart("1990-04-15", "07:30", "New Delhi")


def _moment(y, m, d):
    return chart.rashifal_day_moment(date(y, m, d))


# --------------------------------------------------------------------------
# the block's wording
# --------------------------------------------------------------------------


def test_the_block_names_the_four_slow_planets_and_the_base_rate():
    block = ask_transit.format_ask_transit(_natal(), _moment(2026, 10, 17))
    for planet in ("Saturn", "Jupiter", "Rahu", "Ketu"):
        assert len(re.findall(rf"^{planet} \d+(st|nd|rd|th) (challenging|favorable)$",
                              block, re.M)) == 1, planet
    assert "Base rate: challenging in 9 of 12 houses (Jupiter 7)." in block
    assert block.endswith("\n\n"), "must slot in ahead of --- QUESTION ---"


def test_the_base_rate_numbers_are_derived_from_the_gochara_table_not_typed():
    """Saturn/Rahu/Ketu are benefic in 3 houses, Jupiter in 5 -> challenging in
    12-3=9 and 12-5=7. Edit the table and the sentence must move with it."""
    t = chart._GOCHAR_BENEFIC_HOUSES
    assert 12 - len(t["Saturn"]) == 9 == 12 - len(t["Rahu"]) == 12 - len(t["Ketu"])
    assert 12 - len(t["Jupiter"]) == 7
    assert ask_transit._base_rate() == "challenging in 9 of 12 houses (Jupiter 7)"

    altered = {**t, "Jupiter": frozenset({2, 5, 7, 9, 11, 12}),
               "Saturn": frozenset({3, 6, 11, 1})}
    chart_table = "_GOCHAR_BENEFIC_HOUSES"
    orig = getattr(chart, chart_table)
    setattr(chart, chart_table, altered)
    try:
        # Rahu/Ketu stay at 9, Saturn 8, Jupiter 6: the modal group is still
        # first and the others follow.
        assert ask_transit._base_rate() == (
            "challenging in 9 of 12 houses (Jupiter 6; Saturn 8)")
    finally:
        setattr(chart, chart_table, orig)


def test_the_block_is_hedged_and_makes_no_demands_of_the_model():
    block = ask_transit.format_ask_transit(_natal(), _moment(2026, 10, 17))
    low = block.lower()
    assert "context only" in low
    assert "first approximation" in low
    assert "never whether a specific event will happen" in low
    # The wording that was rejected in the design (#402): a block that tells the
    # model what its answer must be, tiers its tone, or leans on a source.
    for banned in ("must agree", "say so plainly", "tone", "retrograde", "tier",
                   "raman", "gochara", "bphs", "according to"):
        assert banned not in low, banned


def test_the_block_does_not_ask_the_model_to_name_planets_or_signs():
    """ask.txt forbids naming them in the ANSWER, and this block puts their
    names in the user message. It must not read as an invitation to echo them."""
    low = ask_transit.format_ask_transit(_natal(), _moment(2026, 10, 17)).lower()
    for push in ("mention", "explain which", "name the", "cite", "tell the seeker which"):
        assert push not in low, push
    # and it states no sign: the verdict is the house count from the Moon.
    for sign in chart.RASHIS:
        assert sign.lower() not in low, sign


# --------------------------------------------------------------------------
# the pinned moment, and the fingerprint
# --------------------------------------------------------------------------


def test_the_moment_is_local_noon_on_the_ist_date_today_anchor_names():
    m = ask_transit.ask_transit_moment()
    assert (m.hour, m.minute) == (12, 0) and str(m.tzinfo) == "Asia/Kolkata"
    assert f"Today's date: {m.date().isoformat()} " in llm.today_anchor()
    # Kept equal by test rather than import: llm imports ask_transit.
    assert ask_transit._IST == llm._READING_TZ


def test_the_fingerprint_is_a_pure_function_of_the_date():
    a = ask_transit.transit_fingerprint(_moment(2026, 10, 17))
    assert a == ask_transit.transit_fingerprint(_moment(2026, 10, 17))
    assert re.fullmatch(r"[0-9a-f]{8}", a)


# One pair per hashed planet. The fingerprint hashes Saturn|Jupiter|Rahu, and a
# test spanning only a Saturn ingress lets a hand edit drop either of the others
# with the suite green (QA, PR #706) -- so each pair changes EXACTLY ONE planet
# (asserted below, so a wrong date cannot make a row vacuous), and `later` is a
# within-period control in which nothing has changed since `after`.
# Dates measured with chart.compute_transit_snapshot (sidereal, rashifal noon):
#   Saturn  2025-03-27 Kumbha -> 03-31 Meena   (control 04-10)
#   Jupiter 2025-05-14 Vrishabha -> 05-16 Mithuna (control 05-20)
#   Rahu    2025-05-29 Meena -> 05-31 Kumbha   (control 06-10)
@pytest.mark.parametrize("planet, before, after, later", [
    ("Saturn", (2025, 3, 27), (2025, 3, 31), (2025, 4, 10)),
    ("Jupiter", (2025, 5, 14), (2025, 5, 16), (2025, 5, 20)),
    ("Rahu", (2025, 5, 29), (2025, 5, 31), (2025, 6, 10)),
])
def test_the_fingerprint_changes_across_an_ingress_and_not_within_a_period(
    planet, before, after, later
):
    """The engine, not a published table, is the oracle: this only relies on it
    agreeing that `planet` alone changed sign between `before` and `after`."""
    before, after, later = _moment(*before), _moment(*after), _moment(*later)

    def signs(m):
        snap = chart.compute_transit_snapshot(SimpleNamespace(lagna_rashi=chart.RASHIS[0]), m)
        return {p.name: p.rashi for p in snap.planets if p.name in ("Saturn", "Jupiter", "Rahu")}

    sb, sa = signs(before), signs(after)
    assert [n for n in sb if sb[n] != sa[n]] == [planet], "fixture no longer isolates one planet"
    assert signs(after) == signs(later)
    fp = ask_transit.transit_fingerprint
    assert fp(before) != fp(after)
    assert fp(after) == fp(later)


def test_editing_the_blocks_wording_changes_the_fingerprint(monkeypatch):
    m = _moment(2026, 10, 17)
    before = ask_transit.transit_fingerprint(m)
    monkeypatch.setattr(ask_transit, "_FRAMING", ask_transit._FRAMING + " Edited.")
    assert ask_transit.transit_fingerprint(m) != before


def test_the_pinned_moment_is_what_reaches_the_ephemeris(monkeypatch):
    """Spy on the call, not the result: the block and the key must read ONE sky."""
    seen: list = []
    real = chart.compute_transit_snapshot
    monkeypatch.setattr(chart, "compute_transit_snapshot",
                        lambda natal, when=None: seen.append(when) or real(natal, when))
    moment = _moment(2026, 10, 17)
    ask_transit.format_ask_transit(_natal(), moment)
    ask_transit.transit_fingerprint(moment)
    assert seen == [moment, moment]

    seen.clear()
    monkeypatch.setattr(llm.providers, "chat", lambda messages, route=None, **kw: "x")
    llm.generate_ask_answer(_natal(), None, None, QUESTION, "career",
                            deps.ASK_PROMPT_PATH, transit_moment=moment)
    assert seen == [moment]
    seen.clear()
    llm.generate_ask_answer(_natal(), None, None, QUESTION, "career", deps.ASK_PROMPT_PATH)
    assert len(seen) == 1 and seen[0].hour == 12 and seen[0].tzinfo is not None


# --------------------------------------------------------------------------
# where the block sits in the message
# --------------------------------------------------------------------------


def _user_message(monkeypatch, **kw):
    cap: dict = {}
    monkeypatch.setattr(llm.providers, "chat",
                        lambda messages, route=None, **k: cap.update(m=messages) or "x")
    natal = _natal()
    llm.generate_ask_answer(natal, chart.compute_dasha_state(natal),
                            chart.compute_vedic_flags(natal), QUESTION, "career",
                            deps.ASK_PROMPT_PATH, **kw)
    return cap["m"][1]["content"]


def test_the_block_appears_once_after_the_other_blocks_and_before_the_question(monkeypatch):
    partner = chart.compute_chart("1988-05-20", "10:15", "Mumbai")
    from astro_ai.matching import compute_guna_milan
    msg = _user_message(monkeypatch, partner_chart=partner,
                        guna_milan=compute_guna_milan(_natal(), partner),
                        guna_pair_label="A & B")
    assert msg.count("SLOW PLANETS") == 1
    at = msg.index("--- SLOW PLANETS")
    for earlier in ("--- SEEKER'S NATAL CHART", "--- CURRENT DASHA", "--- VEDIC FLAGS",
                    "--- PARTNER", "--- ASHTAKOOTA"):
        assert msg.index(earlier) < at, earlier
    assert at < msg.index("--- QUESTION ---")
    assert msg.index("--- QUESTION ---") - at < 600, "nothing else sits between them"


def test_a_failure_computing_the_block_fails_the_request_instead_of_caching_without_it(
    monkeypatch
):
    """A swallowed error would generate a no-transit answer, which the route
    would then cache under a key that says it has a transit."""
    called: list = []
    monkeypatch.setattr(llm.providers, "chat", lambda *a, **k: called.append(1) or "x")

    def boom(natal, when=None):
        raise RuntimeError("ephemeris unavailable")

    monkeypatch.setattr(chart, "compute_gochar_impacts", boom)
    with pytest.raises(RuntimeError):
        llm.generate_ask_answer(_natal(), None, None, QUESTION, "career", deps.ASK_PROMPT_PATH)
    assert called == []


# --------------------------------------------------------------------------
# the cache key
# --------------------------------------------------------------------------


def _key(**kw):
    return ask_route._ask_cache_key(SAVED, QUESTION, "career", "en", **kw)


@pytest.mark.parametrize("kw", [
    {},
    {"context": "numerology"},
    {"context": "matching", "pair_fp": "g~b", "role": "groom"},
    {"context": "matching", "pair_fp": "g~b", "role": "other"},
    {"context": "matching", "pair_fp": None},      # the fallback branch builds its own string
])
def test_every_key_shape_carries_the_transit_fingerprint(kw):
    tr = ask_transit.transit_fingerprint(ask_transit.ask_transit_moment())
    assert f":tr={tr}" in _key(**kw)


def test_the_matching_fallback_key_is_the_chart_key():
    """No pair fingerprint downgrades to chart; it must do so INCLUDING `tr`, or
    it is a third keyspace that survives a transit change."""
    assert _key(context="matching", pair_fp=None) == _key()


def test_the_key_moves_with_the_sky_and_not_with_the_calendar():
    a = _key(transit_moment=_moment(2025, 3, 27))
    b = _key(transit_moment=_moment(2025, 3, 31))
    c = _key(transit_moment=_moment(2025, 4, 10))
    assert a != b and b == c


def test_the_default_key_is_the_one_a_post_would_derive():
    assert _key() == _key(transit_moment=ask_transit.ask_transit_moment())


def test_get_finds_the_answer_post_stored_under_its_key(monkeypatch):
    """End to end through both handlers: POST generates and caches, the redirect
    target (GET) renders it. A GET key that differed from POST's by one segment
    would show the question typed back with no answer (#181)."""
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    monkeypatch.setattr(ask_route, "load_collection",
                        lambda request: SimpleNamespace(active=SAVED))
    monkeypatch.setattr(ask_route.events, "record", lambda **k: None)
    monkeypatch.setattr(ask_route.notify, "ask_submitted", lambda **k: None)
    seen: dict = {}

    def fake_generate(**kw):
        seen.update(kw)
        return "STORED-ANSWER-402"

    monkeypatch.setattr(ask_route, "generate_ask_answer", fake_generate)
    client = TestClient(app)
    r = client.post("/ask", data={"question": QUESTION, "category": "career"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text[:200]
    # POST handed the generator the moment it keyed on.
    assert seen["transit_moment"] == ask_transit.ask_transit_moment()
    # NOT asserted: cache.get(_key(...)) from THIS thread. Swiss Ephemeris holds
    # its sidereal mode per thread, so a thread that did not import `chart`
    # computes Saturn with a different ayanamsa (measured: 24.2187 vs 25.1019 deg
    # at JD 2461000) and can fingerprint a different sign. TestClient serves each
    # request on its own thread, the test body is on another, so the key would
    # differ here for a reason production does not have. GET rendering the answer
    # below is the claim that matters; the guard for production is the next test.
    page = client.get(r.headers["location"])
    assert page.status_code == 200
    assert "STORED-ANSWER-402" in page.text


def test_both_handlers_stay_on_the_event_loop_thread():
    """The fingerprint and the block read the ephemeris, whose sidereal mode is
    set once at `chart` import and is per-thread in pyswisseph. A plain `def`
    handler would run in a worker thread, compute a different ayanamsa and could
    derive a different `tr` than the other handler. Both are `async def`; if one
    is made sync, move the transit read back onto the loop thread first."""
    import inspect
    assert inspect.iscoroutinefunction(ask_route.ask_form)
    assert inspect.iscoroutinefunction(ask_route.ask_submit)
