"""The `/hi/{path}` URL surface — #124.

The defect this suite guards is not "Hindi looks wrong". It is that Hindi had
NO INDEXABLE SURFACE: `?lang=hi` rendered Hindi prose while `base.html`
canonicalised on `request.url.path`, which drops the query string, so every
Hindi page declared the English URL as its canonical. Google was told, on
every Hindi pageview, that the page it was looking at was a duplicate.

Two things here are easy to break and invisible when broken:

  * A canonical that points at the OTHER language. Both the path-stripping
    middleware (rejected) and a mis-ordered catch-all produce it, from
    opposite directions, and the page looks perfect in a browser either way.

  * hreflang reciprocity. Google validates annotations by comparing the two
    pages' sets, and discards hreflang SITE-WIDE when they disagree — so a
    one-sided annotation does not degrade one page, it silently disables the
    feature for all 13.

Neither is visible to a status-code check, which is why they are asserted
here rather than left to the gate.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture
def hindi_client(client, stub_llm):
    stub_llm(lambda _n: "## Aries / Mesha\n" + "आज का दिन शुभ है। " * 60)
    client.follow_redirects = False
    return client


def _canonical(html: str) -> str:
    return re.search(r'<link rel="canonical" href="([^"]*)', html).group(1)


def _alternates(html: str) -> list[tuple[str, str]]:
    return re.findall(r'<link rel="alternate" hreflang="([^"]*)" href="([^"]*)"', html)


# --- the defect itself ------------------------------------------------------

@pytest.mark.parametrize("path", ["/hi/rashifal", "/hi/rashifal/aries"])
def test_hindi_url_is_self_canonical(hindi_client, path):
    """THE #124 defect. A Hindi page must not canonicalise onto English."""
    r = hindi_client.get(path)
    assert r.status_code == 200
    assert _canonical(r.text).endswith(path), (
        f"{path} canonicalises to {_canonical(r.text)} — a cross-language "
        "canonical tells Google the Hindi page is a duplicate of the English one"
    )


def test_english_url_is_still_self_canonical(hindi_client):
    """And the fix must not invert the bug."""
    r = hindi_client.get("/rashifal")
    assert _canonical(r.text) .endswith("/rashifal")
    assert "/hi/" not in _canonical(r.text)


def test_hi_prefix_actually_serves_hindi(hindi_client):
    """A 200 is not enough: the catch-all could match first and serve English
    at the Hindi URL, which is the same bug from the other side."""
    title = re.search(r"<title>([^<]*)", hindi_client.get("/hi/rashifal/aries").text).group(1)
    assert sum(1 for ch in title if "ऀ" <= ch <= "ॿ") >= 10, (
        f"/hi/ served a non-Devanagari title: {title!r}"
    )


# --- hreflang --------------------------------------------------------------

def test_hreflang_is_reciprocal_and_identical(hindi_client):
    """Google compares the two pages' annotation sets and discards hreflang
    site-wide when they disagree, so the twins must emit the SAME tags."""
    en = _alternates(hindi_client.get("/rashifal").text)
    hi = _alternates(hindi_client.get("/hi/rashifal").text)
    assert en == hi, f"annotation sets differ:\n  en={en}\n  hi={hi}"
    assert dict(en).keys() == {"en-IN", "hi-IN", "x-default"}


def test_unpublished_pages_emit_no_hreflang(hindi_client):
    """A hi-IN pointing at a page with no Hindi content poisons the feature
    for the 13 URLs that do have it. Emitting nothing is the correct answer,
    not a degradation."""
    for path in ("/matching", "/panchang", "/learn/"):
        assert _alternates(hindi_client.get(path).text) == [], (
            f"{path} has no Hindi twin but claims an alternate"
        )


# --- the catch-all ---------------------------------------------------------

@pytest.mark.parametrize("path,target", [
    ("/hi/matching", "/matching"),
    ("/hi/panchang", "/panchang"),
])
def test_unpublished_hi_path_redirects_to_english(hindi_client, path, target):
    """Not a 404: the page demonstrably exists, so a 404 is a soft-404 risk
    and hostile to anyone who hand-types the prefix."""
    r = hindi_client.get(path)
    assert r.status_code == 301
    assert r.headers["location"] == target


@pytest.mark.parametrize("path,target", [
    ("/hi/rashifal/", "/hi/rashifal"),
    ("/hi/rashifal/aries/", "/hi/rashifal/aries"),
    ("/hi/RASHIFAL", "/hi/rashifal"),
])
def test_noncanonical_published_path_keeps_hindi(hindi_client, path, target):
    """Regression: the catch-all first sent these to ENGLISH, so a trailing
    slash silently dropped the language — the #124 defect reached via a slash."""
    r = hindi_client.get(path)
    assert r.status_code == 301
    assert r.headers["location"] == target, (
        f"{path} -> {r.headers['location']}; a published Hindi path must stay Hindi"
    )


def test_unknown_rashi_fails_the_same_in_both_languages(hindi_client):
    """`/hi/rashifal/foo` must not diverge from `/rashifal/foo` — a redirect
    on one and a 404 on the other is how a crawler finds an infinite space."""
    assert (hindi_client.get("/hi/rashifal/nonsense").status_code
            == hindi_client.get("/rashifal/nonsense").status_code == 404)


def test_hi_redirect_chains_terminate(hindi_client):
    """A catch-all that redirects to a path it also matches is a loop, and a
    loop here takes out every Hindi URL at once."""
    for start in ("/hi", "/hi/", "/hi/rashifal/", "/hi/matching"):
        path, hops = start, 0
        while hops < 5:
            r = hindi_client.get(path)
            if r.status_code not in (301, 302, 307, 308):
                break
            path = r.headers["location"].replace("http://testserver", "")
            hops += 1
        else:
            pytest.fail(f"{start} did not settle within 5 hops (last: {path})")
        assert r.status_code == 200, f"{start} settled on {r.status_code} at {path}"


# --------------------------------------------------------------------------
# QA 2026-10-04 found five defects in the first cut of this feature. Each one
# below is one of them. They are grouped here rather than merged into the
# tests above because every one was invisible to the assertions above —
# which all passed while all five were live.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/hi//evil.example.com/pwn",
    "/hi/%2F%2Fevil.example.com",
    "/hi///evil.example.com",
    "/hi//evil.example.com:80/x",
])
def test_hi_catchall_cannot_redirect_off_site(hindi_client, path):
    """FAIL 1 — open redirect to an arbitrary external host.

    `{path:path}` captures everything after /hi/, so /hi//evil.example.com
    arrives as path="/evil.example.com"; english_url() strips the "/hi" and
    returns "//evil.example.com". A Location header of "//host" is a
    PROTOCOL-RELATIVE URL, so the browser fetches http://host — a cacheable
    301 off shubhagya.com to an attacker's site. Both paths 404'd before this
    branch, so the branch introduced it.
    """
    r = hindi_client.get(path)
    loc = r.headers.get("location", "")
    assert not loc.startswith("//"), f"protocol-relative redirect to {loc!r}"
    assert "evil.example.com" not in loc, f"redirect leaks the attacker host: {loc!r}"
    assert loc.startswith("/"), f"redirect target is not same-origin: {loc!r}"


def test_hindi_hub_tiles_fetch_hindi_readings(hindi_client):
    """FAIL 2 — every tile on /hi/rashifal fetched the ENGLISH fragment.

    /hi/* deliberately writes no cookie, so an hx-get to /rashifal/{slug}
    carries no language signal and generation defaults to en. A Hindi
    searcher landed on a fully Hindi page, tapped मेष, and got an English
    reading — on the flagship URL this issue exists to publish.
    """
    hi = re.findall(r'hx-get="([^"]*rashifal/[a-z]+)"', hindi_client.get("/hi/rashifal").text)
    en = re.findall(r'hx-get="([^"]*rashifal/[a-z]+)"', hindi_client.get("/rashifal").text)
    assert len(hi) == len(en) == 12, (len(hi), len(en))
    assert all(h.startswith("/hi/") for h in hi), f"Hindi hub tiles target English URLs: {hi[:2]}"
    assert not any(e.startswith("/hi/") for e in en), f"English hub tiles target Hindi URLs: {en[:2]}"


def test_hindi_page_asserts_its_own_identity_in_structured_data(hindi_client):
    """FAIL 4 — canonical and og:url were right, JSON-LD was not.

    The template hardcoded {{ site_url }}/rashifal/{{ rashi_slug }}, so both
    pages asserted the SAME Article @id with different inLanguage — the same
    cross-language duplicate claim #124 removes from rel=canonical — and the
    breadcrumbs and WhatsApp share link routed Hindi readers back out to
    English.
    """
    html = hindi_client.get("/hi/rashifal/aries").text
    ids = re.findall(r'"(?:@id|url)": "([^"]*rashifal[^"]*)"', html)
    assert ids, "no JSON-LD rashifal URL found at all"
    for got in ids:
        assert "/hi/rashifal/aries" in got, f"Hindi page claims English identity: {got}"
    crumbs = re.findall(r'"item": "([^"]*rashifal[^"]*)"', html)
    for got in crumbs:
        assert "/hi/" in got, f"Hindi breadcrumb points at English: {got}"
    share = re.search(r"wa\.me/\?text=([^\"]*)", html)
    assert share and "%2Fhi%2Frashifal" in share.group(1) or "/hi/rashifal" in (share.group(1) if share else ""), \
        "the share link sends readers to the English URL"


def test_english_page_keeps_its_own_identity(hindi_client):
    """And the FAIL 4 fix must not invert itself."""
    html = hindi_client.get("/rashifal/aries").text
    for got in re.findall(r'"(?:@id|url)": "([^"]*rashifal[^"]*)"', html):
        assert "/hi/" not in got, f"English page claims the Hindi URL: {got}"


def test_language_switch_is_a_working_control(hindi_client):
    """FAIL 3 — a dead control that mutated stored state.

    The picker posted `next = request.url.path`, i.e. /hi/rashifal, and
    /hi/* forces Hindi regardless of cookie. Choosing English wrote lang=en
    into __session, bounced back to /hi/rashifal and re-rendered Hindi: no
    visible effect, and the reader's SAVED language silently changed.

    Where a /hi twin exists the switch is now a pair of real anchors, which
    is also acceptance item 4 of the issue.
    """
    html = hindi_client.get("/hi/rashifal").text
    pairs = dict((h, href) for href, h in
                 re.findall(r'<a href="([^"]*)" rel="alternate" hreflang="([^"]*)"', html))
    assert pairs.get("en-IN") == "/rashifal", f"no working English anchor: {pairs}"
    assert pairs.get("hi-IN") == "/hi/rashifal", f"no working Hindi anchor: {pairs}"

    # and following it must actually arrive in English
    r = hindi_client.get(pairs["en-IN"])
    assert re.search(r'<html[^>]*lang="en"', r.text), "the English anchor still renders Hindi"


def test_language_switch_falls_back_to_a_preference_without_a_twin(hindi_client):
    """A page with no Hindi URL has nothing to link to, so the cookie form
    stays — but its `next` must not be a /hi path, or it strands the reader."""
    html = hindi_client.get("/matching").text
    assert 'action="/lang"' in html, "the preference form vanished from a page with no twin"
    nxt = re.search(r'name="next" value="([^"]*)"', html).group(1)
    assert not nxt.startswith("/hi"), f"preference form posts a forced-Hindi path: {nxt}"


# --- the blind spot QA found in my own mutation testing --------------------

def test_hreflang_hrefs_point_at_the_right_urls(hindi_client):
    """QA's M7: my tests asserted the hreflang CODES and their reciprocity,
    but never the HREFS. So a mutation making hi-IN point at the ENGLISH URL
    — which destroys the annotation's entire purpose — was MISSED. Codes
    matching is not the property that matters.
    """
    for en_path, hi_path in [("/rashifal", "/hi/rashifal"),
                             ("/rashifal/aries", "/hi/rashifal/aries")]:
        got = dict((h, href) for h, href in
                   re.findall(r'hreflang="([^"]*)" href="([^"]*)"',
                              hindi_client.get(en_path).text))
        # EXACT comparison, not endswith. endswith was the first version and
        # it could not see x-default being pointed at the Hindi URL, because
        # "https://host/hi/rashifal".endswith("/rashifal") is True. A test
        # that cannot distinguish a path from its own /hi/ prefix is no test
        # of this property at all.
        base = got["en-IN"].rsplit(en_path, 1)[0]
        assert got["en-IN"] == base + en_path, f"en-IN -> {got['en-IN']}"
        assert got["hi-IN"] == base + hi_path, f"hi-IN -> {got['hi-IN']}"
        assert got["x-default"] == base + en_path, (
            f"x-default -> {got['x-default']}; it must point at the ENGLISH URL "
            f"({base + en_path}), which is what a reader whose locale matches "
            "neither tag should be served"
        )
        assert got["hi-IN"] != got["en-IN"], "hi-IN and en-IN point at the same URL"


# --- S8: ?lang=hi must not remain a second URL for the same Hindi content ---

@pytest.mark.parametrize("path,target", [
    ("/rashifal?lang=hi", "/hi/rashifal"),
    ("/rashifal/aries?lang=hi", "/hi/rashifal/aries"),
])
def test_lang_param_redirects_to_the_hindi_url(hindi_client, path, target):
    """The other half of the original defect, live until S8.

    /hi/... being self-canonical does not help while the same Hindi content is
    still served at /rashifal?lang=hi under canonical=/rashifal — and those
    links are in the wild, because ?lang=hi was the ONLY way to get Hindi
    before this branch.
    """
    r = hindi_client.get(path)
    assert r.status_code == 301, f"{path} still renders Hindi at an English canonical"
    assert r.headers["location"] == target


@pytest.mark.parametrize("path", ["/matching?lang=hi", "/panchang?lang=hi", "/learn/?lang=hi"])
def test_lang_param_still_works_where_there_is_no_hindi_url(hindi_client, path):
    """Unpublished pages have no /hi twin to redirect to, so ?lang=hi must
    keep doing exactly what it does today. Redirecting them to English would
    take Hindi chrome away from readers who asked for it."""
    r = hindi_client.get(path)
    assert r.status_code == 200, f"{path} was redirected; it has no Hindi URL to redirect to"
    assert re.search(r'<html[^>]*lang="hi"', r.text), f"{path} stopped honouring ?lang=hi"


def test_lang_param_redirect_preserves_other_query_params(hindi_client):
    """A redirect that silently drops state is worse than no redirect."""
    r = hindi_client.get("/rashifal?lang=hi&utm_source=wa&ref=x")
    assert r.status_code == 301
    loc = r.headers["location"]
    assert loc.startswith("/hi/rashifal?"), loc
    assert "utm_source=wa" in loc and "ref=x" in loc, f"params dropped: {loc}"
    assert "lang=" not in loc, f"lang survived the redirect and will loop: {loc}"


def test_post_lang_is_not_redirected(hindi_client):
    """`POST /lang` carries `lang` as a FORM field. Redirecting a POST drops
    the body, so the preference would silently never be saved."""
    r = hindi_client.post("/lang", data={"lang": "hi", "next": "/matching"})
    assert r.status_code == 303, f"POST /lang got {r.status_code}"
    assert "__session" in r.headers.get("set-cookie", ""), "the preference was not written"
