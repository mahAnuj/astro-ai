"""#1068 -- kundli_generated and ask_answered count COMPLETIONS, not renders.

Both events are declared by the template that shows the result, and that
template renders on every revisit: /kundli with a saved chart, a /r/<id> snapshot,
a reload of /ask?q=. So the POST's 303 sets a one-shot flag, the GET that follows
reads it, fires once and clears it.

THE FLAG LIVES INSIDE `__session`. Firebase Hosting forwards only that cookie
(session.py docstring), so a flag in a cookie of its own would be stripped before
Cloud Run saw it and the events would never fire on shubhagya.com while every
TestClient test stayed green. `_firebase` below is the guard: it replays a request
carrying ONLY the `__session` value out of the previous response.

What this file cannot see: that GA4 receives the event (test_analytics_declared_events
covers the declare -> fire half under Node) or Firebase's real behaviour; the
simulation reproduces the documented one.

Mutation rows: scripts/mutations/2026_11_17_1068_completion_events.py.
"""
from __future__ import annotations

import time

import pytest
from starlette.requests import Request
from starlette.responses import Response

from astro_ai import session as S

EVENT_KUNDLI = 'data-analytics-event="kundli_generated"'
EVENT_ASK = 'data-analytics-event="ask_answered"'
COOKIE = S.COOKIE_NAME
CHART = dict(name="Asha", birth_date="1990-08-15", birth_time="23:55",
             birth_place="Varanasi, India")


# -- helpers -----------------------------------------------------------------
def _session_headers(resp) -> list[str]:
    return [v for v in resp.headers.get_list("set-cookie") if v.startswith(COOKIE + "=")]


def _all_set_cookies(resp) -> list[str]:
    return resp.headers.get_list("set-cookie")


def _value(set_cookie: str) -> str:
    return set_cookie.split("=", 1)[1].split(";", 1)[0]


def _firebase(resp) -> dict:
    """The request headers Firebase Hosting would forward after `resp`: every
    cookie dropped except `__session`."""
    headers = _session_headers(resp)
    assert len(headers) == 1, f"expected exactly one __session Set-Cookie: {headers}"
    return {"Cookie": f"{COOKIE}={_value(headers[0])}"}


def _decode(resp) -> dict:
    return S._serializer().loads(_value(_session_headers(resp)[0]))


def _fresh_client():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    return TestClient(app)


@pytest.fixture
def kundli_llm(monkeypatch):
    from astro_ai.routes import kundli as K

    monkeypatch.setattr(K, "generate_reading", lambda *a, **k: "## Personality\n" + "Body. " * 60)


def _post_reading(client, **over):
    return client.post("/reading", data={**CHART, **over}, follow_redirects=False)


def _post_ask(client, headers, category="marriage", question="When will I get married?"):
    return client.post("/ask", headers=headers, follow_redirects=False,
                       data={"question": question, "category": category, "context": "chart"})


@pytest.fixture
def ask_llm(stub_llm):
    stub_llm("## Answer\n" + "A canned answer body. " * 30)


def _req(cookie_value: str | None) -> Request:
    raw = [] if cookie_value is None else [(b"cookie", f"{COOKIE}={cookie_value}".encode())]
    return Request({"type": "http", "headers": raw})


def _signed(data: dict) -> str:
    return S._serializer().dumps(data)


# -- kundli_generated --------------------------------------------------------
def test_reading_post_sets_one_flag_and_the_follow_up_get_fires_once(kundli_llm):
    c = _fresh_client()
    posted = _post_reading(c)
    assert posted.status_code == 303
    assert len(_session_headers(posted)) == 1, _all_set_cookies(posted)
    assert "kundli_generated" in _decode(posted)["ev"]
    assert _decode(posted)["charts"], "the chart save was lost to the flag write"

    # Firebase: only __session reaches the app, and nothing else rides along.
    hdr = _firebase(posted)
    got = c.get("/kundli", headers=hdr)
    assert got.status_code == 200
    assert got.text.count(EVENT_KUNDLI) == 1
    assert len(_session_headers(got)) == 1, "the flag must be consumed in ONE write"
    assert "ev" not in _decode(got)
    assert _decode(got)["charts"], "clearing the flag lost the chart"

    # The reload carries the cleared cookie: no event.
    again = c.get("/kundli", headers=_firebase(got))
    assert again.status_code == 200 and EVENT_KUNDLI not in again.text


def test_a_get_with_no_flag_fires_nothing_and_writes_no_cookie(kundli_llm):
    c = _fresh_client()
    posted = _post_reading(c)
    first = c.get("/kundli", headers=_firebase(posted))
    cleared = _firebase(first)
    for _ in range(2):
        r = c.get("/kundli", headers=cleared)
        assert EVENT_KUNDLI not in r.text
        # privacy.html: visits that only read the cookie do not extend it.
        assert _all_set_cookies(r) == [], _all_set_cookies(r)


def test_kundli_without_any_cookie_never_fires():
    r = _fresh_client().get("/kundli")
    assert EVENT_KUNDLI not in r.text and _all_set_cookies(r) == []


def test_a_snapshot_never_fires_even_with_the_flag_present(kundli_llm, monkeypatch):
    from astro_ai import snapshots
    from astro_ai.routes import kundli as K

    snap = snapshots.Snapshot(
        id="TESTSNAP", created_at="2026-11-01T00:00:00Z", expires_at="2099-01-01T00:00:00Z",
        lang="en", birth_details=dict(CHART), reading_text="## Overview\nA fixture reading.")
    monkeypatch.setattr(K.snapshots, "load", lambda short_id: snap)
    c = _fresh_client()
    posted = _post_reading(c)  # the flag is now pending in the cookie
    r = c.get("/r/TESTSNAP", headers=_firebase(posted))
    assert r.status_code == 200
    assert EVENT_KUNDLI not in r.text
    assert _all_set_cookies(r) == [], "a snapshot view must not consume or write the flag"
    # ... and the flag is still there for the GET that really follows the POST.
    assert EVENT_KUNDLI in c.get("/kundli", headers=_firebase(posted)).text


def test_a_rejected_reading_post_sets_no_flag():
    c = _fresh_client()
    bad = _post_reading(c, birth_date="not-a-date")
    assert bad.status_code == 400
    assert _session_headers(bad) == [], "a rejected submission must set no flag"
    assert _all_set_cookies(bad) == []


# -- ask_answered ------------------------------------------------------------
def test_ask_post_fires_once_then_a_reload_does_not(ask_llm, monkeypatch):
    c = _fresh_client()
    posted = _post_reading(c)
    base = _firebase(posted)
    ask = _post_ask(c, base)
    assert ask.status_code == 303
    assert len(_session_headers(ask)) == 1, _all_set_cookies(ask)
    assert "ask_answered" in _decode(ask)["ev"]

    hdr = _firebase(ask)
    got = c.get(ask.headers["location"], headers=hdr)
    assert got.status_code == 200 and got.text.count(EVENT_ASK) == 1
    # The reading POST's own flag is still pending (no /kundli visit in this
    # test): consuming ask_answered must leave it alone.
    assert len(_session_headers(got)) == 1
    assert "ask_answered" not in _decode(got).get("ev", {})
    assert "kundli_generated" in _decode(got)["ev"]

    reload_ = c.get(ask.headers["location"], headers=_firebase(got))
    assert reload_.status_code == 200
    assert "canned answer" in reload_.text, "the answer must still render on a reload"
    assert EVENT_ASK not in reload_.text
    assert _all_set_cookies(reload_) == []


def test_ask_get_without_the_flag_never_fires(ask_llm):
    c = _fresh_client()
    posted = _post_reading(c)
    ask = _post_ask(c, _firebase(posted))
    loc = ask.headers["location"]
    # The chart cookie from the reading POST carries no flag at all.
    r = c.get(loc, headers=_firebase(posted))
    assert EVENT_ASK not in r.text and _all_set_cookies(r) == []
    empty = c.get("/ask", headers=_firebase(posted))
    assert EVENT_ASK not in empty.text and _all_set_cookies(empty) == []


def test_ask_flag_is_not_consumed_by_a_get_that_shows_no_answer(ask_llm):
    """A bare /ask visit between the POST and its GET must not eat the flag."""
    c = _fresh_client()
    posted = _post_reading(c)
    ask = _post_ask(c, _firebase(posted))
    hdr = _firebase(ask)
    bare = c.get("/ask", headers=hdr)
    assert EVENT_ASK not in bare.text and _all_set_cookies(bare) == []
    assert EVENT_ASK in c.get(ask.headers["location"], headers=hdr).text


def test_ask_flag_and_quota_share_one_set_cookie(ask_llm, monkeypatch):
    """Off localhost the fresh answer also writes the daily quota. Both writers
    must leave ONE header carrying the flag AND the count."""
    from astro_ai.routes import deps

    monkeypatch.setattr(deps, "_is_localhost", lambda request: False)
    c = _fresh_client()
    posted = _post_reading(c)
    ask = _post_ask(c, _firebase(posted))
    assert len(_session_headers(ask)) == 1, _all_set_cookies(ask)
    data = _decode(ask)
    assert data["ask_count"] == 1 and data["ask_date"], "the quota write was clobbered"
    assert "ask_answered" in data["ev"], "the flag write was clobbered"
    assert data["charts"], "the chart was clobbered"


def test_a_cached_answer_writes_the_flag_alone_and_still_fires(ask_llm):
    c = _fresh_client()
    posted = _post_reading(c)
    first = _post_ask(c, _firebase(posted))
    c.get(first.headers["location"], headers=_firebase(first))
    again = _post_ask(c, _firebase(posted))  # same question: served from cache
    assert again.status_code == 303
    assert len(_session_headers(again)) == 1, _all_set_cookies(again)
    assert "ask_answered" in _decode(again)["ev"]
    r = c.get(again.headers["location"], headers=_firebase(again))
    assert r.text.count(EVENT_ASK) == 1


# -- the helper: nothing else in the session is lost --------------------------
FULL = {
    "charts": [{"id": "abc12345", "name": "A", "birth_date": "1990-01-01",
                "birth_time": "10:00", "birth_place": "Pune"}],
    "active_id": "abc12345",
    "lang": "hi",
    "user": {"email": "a@b.c", "name": "A", "sub": "s1", "since": "2026-01-01"},
    "ask_date": "2026-11-17", "ask_count": 2,
    "last_matching": {"groom_name": "G"},
}


def _others(data: dict) -> dict:
    return {k: v for k, v in data.items() if k != "ev"}


def test_setting_and_clearing_a_flag_preserves_every_other_session_key():
    req = _req(_signed(FULL))
    for name in sorted(S.EVENT_FLAG_NAMES):
        r = Response()
        S.set_event_flag(req, r, name)
        set_cookie = [v for k, v in r.raw_headers if k == b"set-cookie"]
        assert len(set_cookie) == 1
        after_set = S._serializer().loads(_value(set_cookie[0].decode()))
        assert _others(after_set) == FULL, f"set_event_flag({name}) lost session data"
        assert name in after_set["ev"]

        req2 = _req(_value(set_cookie[0].decode()))
        assert S.event_flag_present(req2, name)
        r2 = Response()
        S.clear_event_flag(req2, r2, name)
        set_cookie2 = [v for k, v in r2.raw_headers if k == b"set-cookie"]
        assert len(set_cookie2) == 1
        after_clear = S._serializer().loads(_value(set_cookie2[0].decode()))
        assert after_clear == FULL, f"clear_event_flag({name}) lost session data or left ev"


def test_a_flag_write_merges_into_a_session_write_already_on_the_response():
    """Order-independence of the one-header rule: a `save_*` that ran first has
    put its data on the response, not in the request the flag write would read."""
    req = _req(_signed({"lang": "hi", "ask_count": 1, "ask_date": "2026-11-17"}))
    r = Response()
    S.save_ask_usage(r, req, "2026-11-17", 2)
    S.set_event_flag(req, r, "ask_answered")
    headers = [v for k, v in r.raw_headers if k == b"set-cookie"]
    assert len(headers) == 1, headers
    data = S._serializer().loads(_value(headers[0].decode()))
    assert data["ask_count"] == 2 and data["lang"] == "hi" and "ask_answered" in data["ev"]


def test_both_flags_coexist_and_clear_independently():
    req = _req(_signed(FULL))
    r = Response()
    S.set_event_flag(req, r, "kundli_generated")
    S.set_event_flag(req, r, "ask_answered")
    val = _value([v for k, v in r.raw_headers if k == b"set-cookie"][0].decode())
    req2 = _req(val)
    assert S.event_flag_present(req2, "kundli_generated")
    assert S.event_flag_present(req2, "ask_answered")
    r2 = Response()
    S.clear_event_flag(req2, r2, "kundli_generated")
    val2 = _value([v for k, v in r2.raw_headers if k == b"set-cookie"][0].decode())
    req3 = _req(val2)
    assert not S.event_flag_present(req3, "kundli_generated")
    assert S.event_flag_present(req3, "ask_answered")


def test_a_stale_flag_is_ignored(monkeypatch):
    req = _req(_signed({"ev": {"kundli_generated": int(time.time()) - 1}}))
    assert not S.event_flag_present(req, "kundli_generated")
    fresh = _req(_signed({"ev": {"kundli_generated": int(time.time()) + 60}}))
    assert S.event_flag_present(fresh, "kundli_generated")
    # Set stamps a lifetime of EVENT_FLAG_TTL, not the year `__session` lasts.
    r = Response()
    S.set_event_flag(_req(None), r, "kundli_generated")
    stamp = S._serializer().loads(_value(r.raw_headers[-1][1].decode()))["ev"]["kundli_generated"]
    assert time.time() < stamp <= time.time() + S.EVENT_FLAG_TTL + 1


@pytest.mark.parametrize("bad", ["", "x", "../session", "kundli_generated ", "ev"])
def test_only_the_two_fixed_names_are_accepted(bad):
    req = _req(None)
    with pytest.raises(ValueError):
        S.set_event_flag(req, Response(), bad)
    with pytest.raises(ValueError):
        S.event_flag_present(req, bad)
    with pytest.raises(ValueError):
        S.clear_event_flag(req, Response(), bad)


def test_a_forged_unknown_flag_key_is_ignored():
    req = _req(_signed({"ev": {"anything": int(time.time()) + 60}}))
    assert S._live_flags(S._load_session(req)) == {}


def test_a_tampered_cookie_carries_no_flag():
    good = _signed({"ev": {"kundli_generated": int(time.time()) + 60}})
    assert not S.event_flag_present(_req(good[:-2] + "xx"), "kundli_generated")
