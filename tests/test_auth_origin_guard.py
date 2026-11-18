"""`POST /auth/google` refuses a cross-site post (#1106, sign-in CSRF).

The check is on `Sec-Fetch-Site` / `Origin`, not a `g_csrf_token` double-submit:
base.html runs Google Identity Services in callback mode, where Google never sets
that cookie, and Firebase strips every cookie but `__session`. A token check would
403 every real sign-in. See `origin_guard`'s docstring.

An allowed request is asserted as "not 403": with GOOGLE_CLIENT_ID unset the route
answers 503 after the guard, which proves the guard let it through without a
network call to Google.
"""
from __future__ import annotations

import pytest

from astro_ai import origin_guard

CRED = {"credential": "x"}


@pytest.fixture(autouse=True)
def _no_google(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("BHAGYA_SITE_URL", raising=False)


def _post(client, **headers):
    return client.post("/auth/google", data=CRED, headers=headers)


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example"},
    {"Origin": "null"},
    {"Origin": "https://shubhagya.com.evil.example"},
    {"Sec-Fetch-Site": "cross-site"},
    {"Sec-Fetch-Site": "same-site"},
    {"Sec-Fetch-Site": "none"},
    # Sec-Fetch-Site is decisive: a matching Origin does not rescue it.
    {"Sec-Fetch-Site": "cross-site", "Origin": "https://shubhagya.com"},
])
def test_a_cross_site_post_is_refused_with_json_403(client, headers):
    r = _post(client, **headers)
    assert r.status_code == 403
    body = r.json()  # the sign-in modal calls r.json() on every response
    assert body["ok"] is False and body["error"]


@pytest.mark.parametrize("headers", [
    {"Sec-Fetch-Site": "same-origin"},
    {"Origin": "http://testserver"},                 # equals the request Host
    {"Origin": "https://shubhagya.com"},
    {"Origin": "https://www.shubhagya.com"},
    {},                                              # non-browser client
])
def test_a_same_origin_or_headerless_post_gets_past_the_guard(client, headers):
    r = _post(client, **headers)
    assert r.status_code == 503, r.text  # past the guard, stopped by "not configured"


def test_a_refused_post_never_reaches_google(client, monkeypatch):
    from google.oauth2 import id_token

    def boom(*a, **k):
        raise AssertionError("the credential was verified for a cross-site post")

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(id_token, "verify_oauth2_token", boom)
    assert _post(client, Origin="https://evil.example").status_code == 403


def test_a_refused_post_sets_no_session_cookie(client):
    r = _post(client, Origin="https://evil.example")
    assert not [v for k, v in r.headers.multi_items() if k.lower() == "set-cookie"]


def test_the_configured_site_url_is_an_allowed_origin(client, monkeypatch):
    monkeypatch.setenv("BHAGYA_SITE_URL", "https://staging.example/")
    assert _post(client, Origin="https://staging.example").status_code == 503


def test_origin_is_compared_by_netloc_not_by_prefix():
    class R:
        headers = {"origin": "https://shubhagya.com@evil.example", "host": "testserver"}

    assert origin_guard.is_same_origin(R()) is False


def test_logout_revokes_the_user_through_the_route(client, monkeypatch):
    import time

    from astro_ai import revocation, session as S

    revoked = []
    monkeypatch.setattr(revocation, "revoke", revoked.append)
    now = int(time.time())
    cookie = S._serializer().dumps({"user": {
        "email": "a@example.test", "name": "A", "sub": "sub-9",
        "since": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(now - 60))}})
    client.cookies.set(S.COOKIE_NAME, cookie)
    assert client.post("/auth/logout").status_code == 200
    assert revoked == ["sub-9"]


def test_logout_without_a_user_revokes_nothing(client, monkeypatch):
    from astro_ai import revocation

    revoked = []
    monkeypatch.setattr(revocation, "revoke", revoked.append)
    assert client.post("/auth/logout").json() == {"ok": True}
    assert revoked == []
