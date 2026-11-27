"""#1546 -- footer and body CTAs must not link the four URLs that answer 303.

#1177 fixed the two navs. For a visitor with no saved chart `/today`, `/monthly`,
`/yearly` and `/ask` still 303 to `/?needs_chart=<key>`, and the footer Readings
group (base.html), the homepage feature cards (index.html) and the `/ask` CTAs in
/learn (learn_article_base.html and twelve article bodies) still linked them, so a
crawler met 3 to 7 redirecting links per page. They now go through the
`chart_href(request, path)` template global.

Every assertion reads the `<a href>` values out of the whole RENDERED document,
never a substring count: `/ask?ctx=matching` is a legitimate link that a substring
match on `/ask` would trip. Nothing here calls a model or reads storage.
"""
from __future__ import annotations

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from astro_ai import learn_registry
from astro_ai.session import COOKIE_NAME, _serializer

DIRECT = {"/today", "/monthly", "/yearly", "/ask"}
PAGES = ["/", "/kundli", "/panchang", "/muhurat", "/learn/sade-sati/"]


class _Hrefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.found.append(a["href"])


def _hrefs(html: str) -> list[str]:
    p = _Hrefs()
    p.feed(html)
    return p.found


def _client(with_chart: bool) -> TestClient:
    from astro_ai.main import app

    c = TestClient(app, follow_redirects=False)
    if with_chart:
        # The real signed session cookie, the same payload save_collection writes.
        c.cookies.set(COOKIE_NAME, _serializer().dumps({
            "charts": [{"id": "c1", "name": "Test", "birth_date": "1990-04-15",
                        "birth_time": "07:30", "birth_place": "New Delhi"}],
            "active_id": "c1",
        }))
    return c


def _request(with_chart: bool):
    # A bare Request carrying the same cookie the TestClient would send.
    from starlette.requests import Request

    cookie = b""
    if with_chart:
        tok = _serializer().dumps({
            "charts": [{"id": "c1", "name": "Test", "birth_date": "1990-04-15",
                        "birth_time": "07:30", "birth_place": "New Delhi"}],
            "active_id": "c1",
        })
        cookie = f"{COOKIE_NAME}={tok}".encode()
    return Request({"type": "http", "method": "GET", "path": "/", "query_string": b"",
                    "headers": [(b"cookie", cookie)] if cookie else []})


@pytest.mark.parametrize("page", PAGES)
def test_no_chart_page_links_no_redirecting_url(page):
    r = _client(False).get(page)
    assert r.status_code == 200 and r.text
    hrefs = _hrefs(r.text)
    assert hrefs, "no <a href> parsed, the assertions below would be vacuous"
    assert not DIRECT & set(hrefs), sorted(DIRECT & set(hrefs))


def test_no_chart_footer_carries_the_destination_for_the_readings_links():
    # base.html's footer is on every page, so it is where the three readings links live.
    hrefs = set(_hrefs(_client(False).get("/panchang").text))
    assert {f"/?needs_chart={k}" for k in ("today", "monthly", "yearly")} <= hrefs


def test_no_chart_homepage_cards_and_learn_cta_carry_the_destination():
    assert "/?needs_chart=ask" in set(_hrefs(_client(False).get("/").text))
    assert "/?needs_chart=ask" in set(_hrefs(_client(False).get("/learn/sade-sati/").text))


def test_no_chart_every_learn_article_links_no_redirecting_url():
    # The twelve article bodies that name /ask are not on the sampled page, so walk the registry.
    c = _client(False)
    slugs = [a.slug for a in learn_registry.all_articles()]
    assert len(slugs) > 12
    bad = {}
    for slug in slugs:
        r = c.get(f"/learn/{slug}/")
        assert r.status_code == 200 and r.text, slug
        hit = DIRECT & set(_hrefs(r.text))
        if hit:
            bad[slug] = sorted(hit)
    assert not bad, bad


def test_visitor_with_a_chart_keeps_the_direct_links():
    c = _client(True)
    # /kundli is left out: with a chart cookie it renders the reading, a model call.
    for page in [p for p in PAGES if p != "/kundli"]:
        hrefs = _hrefs(c.get(page).text)
        assert not any("needs_chart" in h for h in hrefs), page
    assert {"/today", "/monthly", "/yearly", "/ask"} <= set(_hrefs(c.get("/").text))
    assert "/ask" in set(_hrefs(c.get("/learn/sade-sati/").text))


def test_chart_href_unit():
    from astro_ai.routes.deps import _chart_href

    assert _chart_href(_request(False), "/today") == "/?needs_chart=today"
    assert _chart_href(_request(True), "/today") == "/today"
    # outside the table: unchanged either way
    assert _chart_href(_request(False), "/learn/") == "/learn/"
    assert _chart_href(_request(False), "/kundli") == "/kundli"


def test_chart_gated_keys_are_the_ones_the_routes_redirect_on():
    # The rewrite is only correct while the redirect exists: a key added to
    # _CHART_GATED for a route that does not 303 would bounce visitors for nothing.
    from astro_ai.routes.deps import _CHART_GATED

    assert set(_CHART_GATED) == DIRECT
    c = _client(False)
    for path, key in _CHART_GATED.items():
        r = c.get(path)
        assert r.status_code == 303 and r.headers["location"] == f"/?needs_chart={key}", path


def test_chart_href_makes_no_storage_call(monkeypatch):
    # Cost claim of the issue: a cookie decode only, no GCS read.
    from astro_ai import storage
    from astro_ai.routes.deps import _chart_href

    def boom(*a, **k):
        raise AssertionError("chart_href touched storage")

    for name in dir(storage):
        if name.startswith(("read", "write", "load", "get", "list", "_client")) \
                and callable(getattr(storage, name)):
            monkeypatch.setattr(storage, name, boom)
    assert _chart_href(_request(False), "/ask") == "/?needs_chart=ask"
    assert _chart_href(_request(True), "/ask") == "/ask"
