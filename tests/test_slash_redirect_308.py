"""#1176 -- the trailing-slash redirect is 308, not Starlette's 307.

`redirect_slashes` answers /kundli/ -> /kundli and /learn/x -> /learn/x/ with 307
(temporary), so Search Console kept both URLs in play. `_SlashRedirect308Middleware`
rewrites that one case to 308. The Location is Starlette's own, untouched.

Two layers: the real app over TestClient (the routes the issue names), and the
middleware alone over a tiny ASGI app, because a 307 that is NOT a slash toggle
has to be provoked, and no real route is a stable place to find one. Nothing here
calls a model.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from astro_ai.main import _SlashRedirect308Middleware, app


@pytest.fixture(scope="module")
def client():
    return TestClient(app, follow_redirects=False)


def _path(location: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(location).path


def test_get_trailing_slash_is_308_to_the_bare_path(client):
    r = client.get("/kundli/")
    assert r.status_code == 308
    assert _path(r.headers["location"]) == "/kundli"


def test_get_missing_slash_is_308_to_the_slashed_path(client):
    r = client.get("/learn/kaal-sarp-dosh")
    assert r.status_code == 308
    assert _path(r.headers["location"]) == "/learn/kaal-sarp-dosh/"


def test_head_is_308_too(client):
    assert client.head("/kundli/").status_code == 308
    assert client.head("/learn/kaal-sarp-dosh").status_code == 308


def test_location_is_the_starlette_one_with_the_forwarded_host(client):
    r = client.get("/learn/kaal-sarp-dosh", headers={"x-forwarded-host": "shubhagya.com"})
    assert r.status_code == 308
    assert r.headers["location"] == "http://shubhagya.com/learn/kaal-sarp-dosh/"


def test_the_query_string_rides_through_the_308(client):
    r = client.get("/learn/kaal-sarp-dosh?x=1")
    assert r.status_code == 308
    assert r.headers["location"].endswith("/learn/kaal-sarp-dosh/?x=1")


def test_post_to_a_slash_variant_stays_307(client):
    # 308 and 307 both keep the method; the issue scopes the change to GET/HEAD.
    r = client.post("/kundli/")
    assert r.status_code == 307


def test_the_hindi_slash_variant_resolves_in_at_most_two_hops(client):
    url = "/hi/learn/kaal-sarp-dosh/"
    codes = []
    for _ in range(3):
        r = client.get(url)
        codes.append(r.status_code)
        if r.status_code < 300 or r.status_code >= 400:
            break
        url = r.headers["location"]
        if url.startswith("http"):
            from urllib.parse import urlsplit

            url = urlsplit(url).path
    assert codes[0] == 301, codes  # routes/hindi.py's own redirect is untouched
    assert len(codes) <= 3 and codes[-1] not in (301, 307, 308), codes
    assert len(codes) - 1 <= 2, codes


# ── the middleware alone ───────────────────────────────────────────────────

def _run(method, path, status, location, query=b""):
    """Drive the middleware over a stub app that answers `status` + `location`."""
    import asyncio

    seen = []

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"location", location.encode())]})
        await send({"type": "http.response.body", "body": b""})

    async def send(message):
        seen.append(message)

    scope = {"type": "http", "method": method, "path": path, "query_string": query,
             "headers": []}
    asyncio.run(_SlashRedirect308Middleware(inner)(scope, None, send))
    return seen[0]["status"], dict(seen[0]["headers"])[b"location"].decode()


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize("path,location", [
    ("/a", "/a/"),
    ("/a/", "/a"),
    ("/a", "https://shubhagya.com/a/"),
    ("/a/", "http://x.example/a"),
])
def test_a_slash_toggle_307_becomes_308_and_the_location_is_kept(method, path, location):
    assert _run(method, path, 307, location) == (308, location)


@pytest.mark.parametrize("path,location", [
    ("/a", "/b"),            # a handler's own redirect
    ("/a", "/a"),            # no toggle at all
    ("/a", "/a//"),          # more than one slash
    ("/a/b", "/a/"),         # a prefix, not the same path
    ("/a", "/a/?x=1"),       # query the request did not carry
    ("/", "//"),
])
def test_a_307_that_is_not_a_slash_toggle_is_untouched(path, location):
    assert _run("GET", path, 307, location) == (307, location)


def test_the_query_must_match_for_the_toggle_to_count():
    assert _run("GET", "/a", 307, "/a/?x=1", b"x=1") == (308, "/a/?x=1")
    assert _run("GET", "/a", 307, "/a/?x=2", b"x=1") == (307, "/a/?x=2")


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_other_methods_are_never_rewritten(method):
    assert _run(method, "/a", 307, "/a/") == (307, "/a/")


@pytest.mark.parametrize("status", [301, 302, 303, 308, 200])
def test_only_a_307_is_rewritten(status):
    assert _run("GET", "/a", status, "/a/")[0] == status
