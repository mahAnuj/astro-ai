"""#1177 -- a no-chart visitor's nav must not link to URLs that answer 303.

`/today`, `/monthly`, `/yearly` and `/ask` each 303 to `/?needs_chart=<key>` when
the session has no saved chart, and the nav carried them on every page, so crawlers
and no-chart visitors met four redirecting links per page. `_nav.html` and
`_tab_bar.html` now link a no-chart visitor to the destination directly, via the
`has_chart(request)` template global (the redirects' own predicate).

The hrefs are parsed out of the RENDERED `<nav aria-label="Main">` and
`<nav aria-label="Quick navigation">`, not read from a hard-coded list, so a link
added to either nav later is checked too. Nothing here calls a model.
"""
from __future__ import annotations

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from astro_ai.session import COOKIE_NAME, _serializer

GATED = {"today", "monthly", "yearly", "ask"}
NAV_LABELS = {"Main", "Quick navigation"}

# Nav hrefs that are NOT #1177's, excluded by name. The nav spells it `/learn/`
# (200), so `/learn` (308) is not in it today; the slash-redirect class is
# #1176's scope and this test must not start failing on it if a nav link ever
# regresses to that spelling. Add a path here only with the issue that owns it.
OTHER_ISSUES_REDIRECTS = {"/learn"}  # #1176: trailing-slash 308s


class _NavHrefs(HTMLParser):
    """Collects (nav label, href) for every <a href> inside the two site navs."""

    def __init__(self):
        super().__init__()
        self._label = None
        self.found: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "nav":
            self._label = a.get("aria-label") if a.get("aria-label") in NAV_LABELS else None
        elif tag == "a" and self._label and a.get("href"):
            self.found.append((self._label, a["href"]))

    def handle_endtag(self, tag):
        if tag == "nav":
            self._label = None


def _nav_hrefs(html: str) -> list[tuple[str, str]]:
    p = _NavHrefs()
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


def _internal(hrefs):
    return sorted({h for _, h in hrefs if h.startswith("/") and not h.startswith("//")})


@pytest.mark.parametrize("page", ["/", "/learn/"])
def test_no_chart_nav_has_no_gated_redirect_links(page):
    r = _client(False).get(page)
    assert r.status_code == 200
    hrefs = _nav_hrefs(r.text)
    # both navs were actually found, or the assertions below are vacuous
    assert {lbl for lbl, _ in hrefs} == NAV_LABELS
    for _, h in hrefs:
        assert h not in {"/today", "/monthly", "/yearly", "/ask"}, h
    wanted = {f"/?needs_chart={k}" for k in GATED}
    assert wanted <= {h for lbl, h in hrefs if lbl == "Main"}
    assert "/?needs_chart=ask" in {h for lbl, h in hrefs if lbl == "Quick navigation"}


def test_no_chart_every_internal_nav_href_answers_without_a_redirect():
    c = _client(False)
    internal = _internal(_nav_hrefs(c.get("/").text))
    assert internal, "no internal nav hrefs parsed"
    bad = {}
    for h in internal:
        if h in OTHER_ISSUES_REDIRECTS:
            continue
        status = c.get(h).status_code
        if 300 <= status < 400:
            bad[h] = status
    assert not bad, f"nav links that redirect for a no-chart visitor: {bad}"


def test_nav_chart_gated_hrefs_are_the_ones_the_routes_redirect_on():
    # The rewrite is only correct while the redirect still exists: if a route
    # stopped gating, the direct link is what the nav should carry again.
    c = _client(False)
    for key in GATED:
        r = c.get(f"/{key}")
        assert r.status_code == 303 and r.headers["location"] == f"/?needs_chart={key}"


def test_visitor_with_a_chart_keeps_the_direct_links():
    c = _client(True)
    for page in ("/", "/learn/"):
        hrefs = _nav_hrefs(c.get(page).text)
        main = {h for lbl, h in hrefs if lbl == "Main"}
        tabs = {h for lbl, h in hrefs if lbl == "Quick navigation"}
        assert {"/today", "/monthly", "/yearly", "/ask"} <= main
        assert "/ask" in tabs
        assert not any("needs_chart" in h for _, h in hrefs)


def test_active_tab_is_derived_from_the_direct_path():
    # A visitor with a chart on /ask: the Ask tab is current AND still links /ask.
    r = _client(True).get("/ask")
    assert r.status_code == 200
    assert 'aria-current="page"' in r.text
    tab = r.text.split('aria-label="Quick navigation"')[1]
    ask_a = tab.split('<a href="/ask"')[1].split(">")[0]
    assert 'aria-current="page"' in ask_a
    # and with no chart, /kundli stays current while the Ask tab is the rewrite
    r = _client(False).get("/kundli")
    assert r.status_code == 200
    tab = r.text.split('aria-label="Quick navigation"')[1]
    assert 'href="/?needs_chart=ask"' in tab
    assert tab.split('href="/kundli"')[1].split(">")[0].count('aria-current="page"') == 1


def test_needs_chart_page_canonicalises_to_the_homepage():
    # The four rewritten links are now crawler-visible URLs; they must not mint
    # duplicate documents. base.html's canonical is site_url + request.url.path,
    # which drops the query, so /?needs_chart=today canonicalises to "/".
    import re

    def canonical(url):
        r = _client(False).get(url)
        assert r.status_code == 200
        return re.search(r'<link rel="canonical" href="([^"]*)"', r.text).group(1)

    assert canonical("/?needs_chart=today") == canonical("/")
