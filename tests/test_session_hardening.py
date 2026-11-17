"""The `__session` cookie is bounded and revocable on the SERVER (#1106).

Before this, `URLSafeSerializer` carried no timestamp, so a copied cookie worked
for ever, and sign-out only deleted the cookie on the device that clicked it.
Every test below pins one way that can regress. `time.time` is patched in the
direct-call tests because itsdangerous stamps with it too, so a cookie can be
signed "in the past" without sleeping; the route tests use the real clock.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from itsdangerous import URLSafeSerializer
from starlette.requests import Request
from starlette.responses import Response

from astro_ai import hot_cache, revocation, session as S

NOW = 1_800_000_000  # 2027-01-15, inside the legacy window (cutoff is 1826409600)
DAY = 86400
CHARTS = {"charts": [{"id": "ab12cd34", "name": "Asha", "birth_date": "1990-04-12",
                      "birth_time": "14:35", "birth_place": "Mumbai, India"}],
          "active_id": "ab12cd34", "lang": "hi"}


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")


def _user(since_epoch: int, sub: str = "sub-1") -> dict:
    return {"email": "a@example.test", "name": "A", "sub": sub, "since": _iso(since_epoch)}


def _req(cookie: str | None) -> Request:
    headers = [(b"cookie", f"{S.COOKIE_NAME}={cookie}".encode())] if cookie else []
    return Request({"type": "http", "method": "GET", "path": "/", "query_string": b"",
                    "headers": headers})


def _sign_at(data: dict, issued_at: float) -> str:
    """A v2 cookie as the app would have written it at `issued_at`."""
    with patch("time.time", return_value=issued_at):
        return S._serializer().dumps(data)


def _legacy(data: dict) -> str:
    """A cookie exactly as the code before #1106 wrote it: no timestamp."""
    return URLSafeSerializer(S.cookie_secret(), salt="birth-details").dumps(data)


def _load_at(cookie: str, now: float) -> dict:
    with patch("time.time", return_value=now):
        return S._load_session(_req(cookie))


def _user_at(cookie: str, now: float):
    with patch("time.time", return_value=now):
        return S.load_user(_req(cookie))


# ─── the cookie's own age ──────────────────────────────────────────────────


def test_a_v2_cookie_loads_while_it_is_young():
    assert _load_at(_sign_at(CHARTS, NOW), NOW + DAY)["lang"] == "hi"


def test_a_v2_cookie_older_than_the_browser_max_age_loads_signed_out():
    cookie = _sign_at(CHARTS, NOW)
    assert _load_at(cookie, NOW + S.COOKIE_MAX_AGE + S.CLOCK_SKEW_S + 5) == {}


def test_a_v2_cookie_just_inside_the_skew_allowance_still_loads():
    cookie = _sign_at(CHARTS, NOW)
    assert _load_at(cookie, NOW + S.COOKIE_MAX_AGE + S.CLOCK_SKEW_S - 5) != {}


def test_a_cookie_stamped_30s_in_the_future_loads_instance_clock_skew():
    # itsdangerous' own max_age= treats a negative age as expired, which would
    # sign people out whenever two Cloud Run instances disagree about the time.
    cookie = _sign_at(CHARTS, NOW + 30)
    assert _load_at(cookie, NOW)["lang"] == "hi"


def test_a_cookie_stamped_far_in_the_future_is_refused():
    cookie = _sign_at(CHARTS, NOW + 3600)
    assert _load_at(cookie, NOW) == {}


# ─── legacy (untimed) cookies ──────────────────────────────────────────────


def test_a_legacy_cookie_still_loads_before_the_cutoff():
    assert _load_at(_legacy(CHARTS), S.LEGACY_COOKIE_CUTOFF - 10)["lang"] == "hi"


def test_a_legacy_cookie_is_signed_out_after_the_cutoff():
    assert _load_at(_legacy(CHARTS), S.LEGACY_COOKIE_CUTOFF + 10) == {}


def test_the_cutoff_is_a_literal_instant_not_a_relative_bound():
    # 2027-11-17 00:00:00 UTC. A bound computed from `time.time()` would honour
    # an untimed cookie for ever, because its age cannot be known.
    assert S.LEGACY_COOKIE_CUTOFF == int(
        datetime(2027, 11, 17, tzinfo=timezone.utc).timestamp())


def test_a_legacy_cookie_with_a_bad_signature_is_signed_out():
    assert _load_at(_legacy(CHARTS)[:-3] + "AAA", NOW) == {}


def test_a_v2_token_through_the_legacy_serializer_does_not_raise():
    # BadPayload, which is not a BadSignature: the old `except BadSignature`
    # would have let this out as a 500.
    cookie = _sign_at(CHARTS, NOW)
    with pytest.raises(Exception):
        S._legacy_serializer().loads(cookie)
    assert _load_at(cookie, NOW)["lang"] == "hi"


def test_v2_cookies_are_signed_with_a_salt_the_legacy_serializer_does_not_share():
    cookie = _sign_at(CHARTS, NOW)
    from itsdangerous import BadData

    with pytest.raises(BadData):
        S._legacy_serializer().loads(cookie)


def test_garbage_in_the_cookie_is_signed_out_not_a_500():
    assert S._decode("not-a-cookie") == {}
    assert S._decode("") == {}


def test_a_get_carrying_a_legacy_cookie_sends_no_set_cookie(client):
    # privacy.html promises a visit that only reads does not extend the cookie,
    # so a legacy cookie is re-signed by the next WRITE, never by a read.
    client.cookies.set(S.COOKIE_NAME, _legacy(CHARTS))
    with patch("time.time", return_value=NOW):
        r = client.get("/", follow_redirects=False)
    assert r.status_code == 200
    assert not [v for k, v in r.headers.multi_items()
                if k.lower() == "set-cookie" and v.startswith(S.COOKIE_NAME + "=")]


def test_a_write_re_signs_a_legacy_cookie_as_v2():
    response = Response()
    with patch("time.time", return_value=NOW):
        S.save_lang(response, "en", _req(_legacy(CHARTS)))
    value = dict(response.raw_headers)[b"set-cookie"].decode().split("=", 1)[1].split(";")[0]
    with patch("time.time", return_value=NOW):
        assert S._serializer().loads(value)["charts"] == CHARTS["charts"]


# ─── the event-flag path shares the one parser ─────────────────────────────


def test_event_flags_round_trip_under_v2():
    cookie = _sign_at(CHARTS, NOW)
    response = Response()
    with patch("time.time", return_value=NOW):
        S._write_session(response, S._decode(cookie))
        S.set_event_flag(_req(cookie), response, "ask_answered")
        headers = [v for k, v in response.raw_headers if k == b"set-cookie"]
        assert len(headers) == 1
        raw = headers[0].decode().split("=", 1)[1].split(";")[0]
        data = S._decode(raw)
    assert data["lang"] == "hi"
    assert "ask_answered" in data["ev"]


# ─── identity: a bound on sign-in, and sign-out ────────────────────────────


def test_a_signed_in_cookie_is_a_user_while_young():
    cookie = _sign_at({"user": _user(NOW - DAY)}, NOW - DAY)
    assert _user_at(cookie, NOW).sub == "sub-1"


def test_a_sign_in_older_than_90_days_is_signed_out_even_with_a_young_cookie():
    # The cookie is re-stamped by every write, so its own age never reaches 90
    # days for an active reader; the identity has to carry its own fixed bound.
    cookie = _sign_at({"user": _user(NOW - 91 * DAY)}, NOW)
    assert _user_at(cookie, NOW) is None


def test_a_sign_in_just_inside_90_days_is_still_a_user():
    cookie = _sign_at({"user": _user(NOW - 89 * DAY)}, NOW)
    assert _user_at(cookie, NOW).sub == "sub-1"


def test_the_90_day_bound_applies_to_a_legacy_cookie_too():
    assert _user_at(_legacy({"user": _user(NOW - 91 * DAY)}), NOW) is None
    assert _user_at(_legacy({"user": _user(NOW - 10 * DAY)}), NOW).sub == "sub-1"


@pytest.mark.parametrize("since", ["", "not-a-date", "2026-13-45"])
def test_an_unusable_since_is_signed_out(since):
    u = _user(NOW)
    u["since"] = since
    assert _user_at(_sign_at({"user": u}, NOW), NOW) is None


def test_a_date_only_since_is_read_as_utc():
    u = _user(NOW)
    u["since"] = _iso(NOW - DAY)[:10]
    assert _user_at(_sign_at({"user": u}, NOW), NOW).sub == "sub-1"


def test_a_cookie_issued_before_sign_out_is_signed_out():
    cookie = _sign_at({"user": _user(NOW - 100)}, NOW - 100)
    assert _user_at(cookie, NOW).sub == "sub-1"
    with patch("time.time", return_value=NOW):
        revocation.revoke("sub-1")
    assert _user_at(cookie, NOW + 1) is None


def test_a_sign_in_in_the_same_second_as_the_sign_out_is_signed_out():
    # `since` has one-second resolution, so `<`, not `<=`, would let a cookie
    # issued in the very second of the sign-out survive it.
    cookie = _sign_at({"user": _user(NOW)}, NOW)
    with patch("time.time", return_value=NOW):
        revocation.revoke("sub-1")
    assert _user_at(cookie, NOW) is None


def test_a_cookie_issued_after_sign_out_is_signed_in():
    with patch("time.time", return_value=NOW):
        revocation.revoke("sub-1")
    cookie = _sign_at({"user": _user(NOW + 5)}, NOW + 5)
    assert _user_at(cookie, NOW + 6).sub == "sub-1"


def test_sign_out_revokes_only_that_user():
    with patch("time.time", return_value=NOW):
        revocation.revoke("sub-1")
    cookie = _sign_at({"user": _user(NOW - 50, sub="sub-2")}, NOW - 50)
    assert _user_at(cookie, NOW + 1).sub == "sub-2"


def test_a_revocation_another_instance_wrote_is_read_from_the_shared_blob():
    # The cache fills in a background thread, so seed the cache the way a
    # finished refresh would; `_read` is exercised separately below.
    hot_cache._store(revocation.CACHE_KEY, {"sub-1": NOW}, None, 300)
    cookie = _sign_at({"user": _user(NOW - 50)}, NOW - 50)
    assert _user_at(cookie, NOW + 1) is None


def test_read_parses_the_blob_and_ignores_junk(monkeypatch):
    monkeypatch.setattr(revocation.storage, "get_json", lambda k: {
        "revoked_before": {"a": 5, "b": "x", "c": True, "d": 7.9}})
    assert revocation._read() == {"a": 5, "d": 7}
    monkeypatch.setattr(revocation.storage, "get_json", lambda k: ["not", "a", "dict"])
    assert revocation._read() == {}
    monkeypatch.setattr(revocation.storage, "get_json", lambda k: None)
    assert revocation._read() == {}


def test_revoke_writes_the_blob_and_prunes_entries_older_than_the_signin_bound(monkeypatch):
    seen = {}

    def fake_update(key, mutate, *, default=None, max_retries=5):
        seen["key"] = key
        seen["out"] = mutate({"revoked_before": {
            "old": NOW - S.SIGNIN_MAX_AGE - 10, "recent": NOW - DAY}})
        return seen["out"]

    monkeypatch.setattr(revocation.storage, "update_json", fake_update)
    with patch("time.time", return_value=NOW):
        revocation.revoke("sub-1")
    assert seen["key"] == "session_revocations.json"
    assert seen["out"] == {"revoked_before": {"recent": NOW - DAY, "sub-1": NOW}}


def test_sign_out_on_one_client_revokes_a_copied_cookie_on_another(client):
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    now = int(time.time())
    cookie = _sign_at({"user": _user(now - 120)}, now - 120)
    stolen = TestClient(app)
    client.cookies.set(S.COOKIE_NAME, cookie)
    stolen.cookies.set(S.COOKIE_NAME, cookie)
    assert stolen.get("/account", follow_redirects=False).status_code == 200

    assert client.post("/auth/logout").json() == {"ok": True}

    assert stolen.get("/account", follow_redirects=False).status_code == 303


# ─── storage down: fail open ───────────────────────────────────────────────


def test_storage_down_keeps_a_valid_cookie_signed_in(monkeypatch):
    # storage.get cannot tell "missing" from "unavailable", so failing closed
    # would sign every reader out on a GCS blip, and local dev with no bucket.
    def boom(*a, **k):
        raise RuntimeError("gcs down")

    monkeypatch.setattr(revocation.storage, "get_json", boom)
    monkeypatch.setattr(revocation.storage, "update_json", boom)
    cookie = _sign_at({"user": _user(NOW - 100)}, NOW - 100)
    assert _user_at(cookie, NOW).sub == "sub-1"
    assert _user_at(cookie, NOW).sub == "sub-1"  # and again, with the failure cached


def test_storage_returning_nothing_keeps_a_valid_cookie_signed_in(monkeypatch):
    monkeypatch.setattr(revocation.storage, "get_json", lambda k: None)
    cookie = _sign_at({"user": _user(NOW - 100)}, NOW - 100)
    assert _user_at(cookie, NOW).sub == "sub-1"


def test_revoke_with_storage_down_still_revokes_on_this_instance(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("gcs down")

    monkeypatch.setattr(revocation.storage, "update_json", boom)
    cookie = _sign_at({"user": _user(NOW - 100)}, NOW - 100)
    with patch("time.time", return_value=NOW):
        revocation.revoke("sub-1")  # must not raise
    assert _user_at(cookie, NOW + 1) is None


def test_logout_clears_the_device_cookie_even_if_revoke_raises(client, monkeypatch):
    def boom(sub):
        raise RuntimeError("revoke exploded")

    monkeypatch.setattr(revocation, "revoke", boom)
    now = int(time.time())
    client.cookies.set(S.COOKIE_NAME, _sign_at({"user": _user(now - 60)}, now - 60))
    r = client.post("/auth/logout")
    assert r.status_code == 200 and r.json() == {"ok": True}
    header = next(v for k, v in r.headers.multi_items()
                  if k.lower() == "set-cookie" and v.startswith(S.COOKIE_NAME + "="))
    assert "user" not in S._decode(header.split("=", 1)[1].split(";")[0])
