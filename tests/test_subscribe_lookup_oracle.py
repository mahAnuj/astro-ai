"""/subscribe/lookup must not say who is on the mailing list (#1159).

Before: any anonymous POST got `subscribed: true` plus the address's city and rashi
for a subscribed email and defaults for anything else -- an enumeration oracle that
also leaked two profile fields. The only consumer is the subscribe modal's prefill,
which exists so a returning subscriber's re-submit does not reset their prefs.

The fix has two halves and each is pinned, because either alone breaks something:

  * lookup answers only the signed-in user's OWN subscribed address; every other
    caller gets one identical default body and the blob is not read for them;
  * `/subscribe` stops overwriting an existing address's prefs unless the caller is
    signed in as that address. Without this half, removing the prefill would make
    the anonymous returning-subscriber reset worse, and anonymous callers could
    rewrite a stranger's lang / rashi / city.

Storage is an in-memory dict behind `storage.get_json` / `storage.update_json`; the
session is a real signed cookie, so `load_user` is the production code path.
"""
from __future__ import annotations

import json

import pytest

from astro_ai import notify, session, storage, subscribers
from astro_ai.routes import subscribe as subscribe_routes

SUBSCRIBED = "victim@example.com"
OTHER = "stranger@example.com"
NEW = "newcomer@example.com"

DEFAULT_BODY = {"ok": True, "subscribed": False, "lang": "en", "city": "", "rashi": "all"}


@pytest.fixture
def blob(monkeypatch):
    """In-memory subscribers.json. Returns the dict the fakes read and write."""
    state = {"subscribers": [
        {"email": SUBSCRIBED, "lang": "hi", "city": "Pune", "rashi": "leo",
         "subscribed_at": "2026-01-01T00:00:00+00:00"},
    ]}

    def get_json(key):
        return json.loads(json.dumps(state)) if key == subscribers.SUBSCRIBERS_KEY else None

    def update_json(key, mutator, *, default=None, max_retries=5):
        new = mutator(json.loads(json.dumps(state)))
        state.clear()
        state.update(new)
        return new

    monkeypatch.setattr(storage, "get_json", get_json)
    monkeypatch.setattr(storage, "update_json", update_json)
    monkeypatch.setattr(subscribe_routes, "_send_welcome_email", lambda *a, **k: True)
    monkeypatch.setattr(notify, "subscribed", lambda **k: None)
    return state


def _record(blob, email):
    return next((s for s in blob["subscribers"] if s["email"] == email), None)


def _sign_in(client, email):
    """A real signed session cookie for `email`, as the OAuth callback would set."""
    cookie = session._serializer().dumps(
        {"user": {"email": email, "name": "T", "sub": f"sub-{email}", "since": "2026-01-01"}})
    client.cookies.set(session.COOKIE_NAME, cookie)


def _lookup(client, email):
    r = client.post("/subscribe/lookup", data={"email": email})
    assert r.status_code == 200
    return r.json()


def _sub(client, email, **form):
    return client.post("/subscribe", data={"email": email, **form})


# --- a, d: the oracle ----------------------------------------------------------

def test_anonymous_lookup_returns_one_body_for_subscribed_and_unsubscribed(client, blob):
    subscribed = _lookup(client, SUBSCRIBED)
    unsubscribed = _lookup(client, NEW)
    assert subscribed == unsubscribed == DEFAULT_BODY
    assert len({json.dumps(b, sort_keys=True) for b in (subscribed, unsubscribed)}) == 1
    raw = client.post("/subscribe/lookup", data={"email": SUBSCRIBED}).text
    assert "Pune" not in raw and "leo" not in raw and '"hi"' not in raw


def test_anonymous_lookup_never_reads_the_subscriber_list(client, blob, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("storage was read for an unauthenticated lookup")
    monkeypatch.setattr(subscribers, "find_by_email", boom)
    monkeypatch.setattr(subscribers, "list_subscribers", boom)
    monkeypatch.setattr(storage, "get_json", boom)
    assert _lookup(client, SUBSCRIBED) == DEFAULT_BODY
    assert _lookup(client, "not-an-email") == DEFAULT_BODY


# --- b, c: the signed-in path --------------------------------------------------

def test_signed_in_user_gets_their_own_prefs_back(client, blob):
    _sign_in(client, SUBSCRIBED)
    assert _lookup(client, SUBSCRIBED) == {
        "ok": True, "subscribed": True, "lang": "hi", "city": "Pune", "rashi": "leo"}
    # case and padding must not split the match: the modal sends it lower-cased
    assert _lookup(client, f"  {SUBSCRIBED.upper()} ")["subscribed"] is True


def test_signed_in_user_cannot_look_up_someone_elses_address(client, blob):
    _sign_in(client, OTHER)
    assert _lookup(client, SUBSCRIBED) == DEFAULT_BODY


def test_signed_in_user_who_is_not_subscribed_gets_the_default_body(client, blob):
    _sign_in(client, OTHER)
    assert _lookup(client, OTHER) == DEFAULT_BODY


# --- e, f, g: /subscribe stops being a write oracle ----------------------------

def test_anonymous_resubscribe_keeps_the_stored_prefs_and_looks_like_a_new_signup(client, blob):
    before = dict(_record(blob, SUBSCRIBED))
    existing = _sub(client, SUBSCRIBED, lang="en", city="Delhi", rashi="aries")
    fresh = _sub(client, NEW, lang="en", city="Delhi", rashi="aries")
    assert _record(blob, SUBSCRIBED) == before, "an anonymous caller rewrote a stored record"
    assert (existing.status_code, existing.json()) == (fresh.status_code, fresh.json()) == (200, {"ok": True})
    assert existing.text == fresh.text


def test_signed_in_resubscribe_of_their_own_address_updates_the_prefs(client, blob):
    _sign_in(client, SUBSCRIBED)
    assert _sub(client, SUBSCRIBED, lang="en", city="Delhi", rashi="aries").json() == {"ok": True}
    rec = _record(blob, SUBSCRIBED)
    assert (rec["lang"], rec["city"], rec["rashi"]) == ("en", "Delhi", "aries")
    assert rec["subscribed_at"] == "2026-01-01T00:00:00+00:00"
    assert len([s for s in blob["subscribers"] if s["email"] == SUBSCRIBED]) == 1


def test_signed_in_resubscribe_of_someone_elses_address_does_not_update_it(client, blob):
    _sign_in(client, OTHER)
    _sub(client, SUBSCRIBED, lang="en", city="Delhi", rashi="aries")
    rec = _record(blob, SUBSCRIBED)
    assert (rec["lang"], rec["city"], rec["rashi"]) == ("hi", "Pune", "leo")


def test_a_brand_new_anonymous_subscribe_stores_the_posted_prefs(client, blob):
    assert _sub(client, NEW, lang="hi", city="Jaipur", rashi="virgo").json() == {"ok": True}
    rec = _record(blob, NEW)
    assert (rec["lang"], rec["city"], rec["rashi"]) == ("hi", "Jaipur", "virgo")


def test_subscribe_overwrite_default_is_unchanged_for_other_callers(blob):
    """`overwrite_prefs` defaults True: the signature change is opt-in."""
    ok, is_new, _ = subscribers.subscribe(SUBSCRIBED, "en", "Delhi", "aries")
    assert (ok, is_new) == (True, False)
    assert _record(blob, SUBSCRIBED)["rashi"] == "aries"
    ok, is_new, _ = subscribers.subscribe(SUBSCRIBED, "hi", "Pune", "leo", overwrite_prefs=False)
    assert (ok, is_new) == (True, False)
    assert _record(blob, SUBSCRIBED)["rashi"] == "aries"
