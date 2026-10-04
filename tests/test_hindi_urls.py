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


def _switch(client, page, to):
    """Click the picker's `to` control on `page` and follow where it lands.

    Returns (location, resolved_lang). This helper exists because the previous
    version of this test asserted the anchor's HREF and never followed it —
    so it passed while the control was dead. QA 2026-10-04: "its name claims
    a property it does not test."
    """
    html = client.get(page).text
    nxt = re.search(r'name="next" value="([^"]*)"', html).group(1)
    r = client.post("/lang", data={"lang": to, "next": nxt})
    loc = r.headers["location"]
    final = client.get(loc)
    return loc, re.search(r'<html[^>]*lang="([^"]*)"', final.text).group(1)


@pytest.mark.parametrize("start_lang", [None, "en", "hi"])
@pytest.mark.parametrize("page", ["/rashifal", "/hi/rashifal", "/rashifal/aries"])
def test_language_switch_works_from_every_starting_state(hindi_client, start_lang, page):
    """FAIL 3, and the regression that replaced it.

    v1 (a <select> posting request.url.path) wrote lang=en then bounced the
    reader back to /hi/rashifal, which forces Hindi: dead control, and it
    silently changed their saved language.

    v2 (plain anchors, mine) fixed the silent write and broke it differently —
    with a saved `hi` preference the ENGLISH url renders Hindi too, so the
    "English" anchor pointed at a page that served Hindi. Dead again, on
    exactly the 13 pages where the anchors appeared, and a functional
    regression against both main and v1.

    So the only assertion worth making is the end-to-end one: from any
    starting state, asking for a language gets you that language. This is
    parametrised over all three cookie states because v2 was correct in two
    of them and broken in the third.
    """
    if start_lang:
        hindi_client.post("/lang", data={"lang": start_lang, "next": "/panchang"})

    _, got_en = _switch(hindi_client, page, "en")
    assert got_en == "en", f"asked for English from {start_lang!r} on {page}, got {got_en}"

    loc_hi, got_hi = _switch(hindi_client, page, "hi")
    assert got_hi == "hi", f"asked for Hindi from {start_lang!r} on {page}, got {got_hi}"
    assert loc_hi.startswith("/hi/"), (
        f"Hindi was served at {loc_hi}, not at the published Hindi URL — the "
        "reader ends up at a URL whose language it is not"
    )


def test_language_control_marks_state_not_location(hindi_client):
    """FAIL 2 — aria-current said the reader was on /hi/rashifal while they
    were on /rashifal, whenever a `hi` cookie disagreed with the path.

    It is a preference toggle, so the correct semantic is aria-pressed on the
    chosen option, not aria-current on a URL.
    """
    hindi_client.post("/lang", data={"lang": "hi", "next": "/panchang"})
    html = hindi_client.get("/rashifal").text
    assert 'aria-current' not in html.split("<footer")[0], (
        "aria-current makes a location claim; this control sets a preference"
    )
    pressed = re.findall(r'value="(\w+)"[^>]*aria-pressed="true"', html)
    assert pressed == ["hi"], f"aria-pressed should mark the active language, got {pressed}"


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


# --- QA round 2: the four defects found in the round-1 fixes ---------------

def test_hindi_card_fragment_stays_in_hindi(hindi_client):
    """QA F3. Making the hub tiles fetch Hindi CREATED this path, and the
    fragment they swap in built both its "open full page" link and its
    WhatsApp share text from a hardcoded /rashifal/{slug} permalink — so a
    Hindi reading arrived wrapped in chrome whose two links ejected the
    reader to English, and shared the English URL.

    Round 1 verified this fix by measuring "prompt_lang=hi, 780 Devanagari
    chars" — the BODY only. conftest's docstring opens by warning about
    exactly that: measuring the thing that just improved rather than the
    thing the code exists to do.
    """
    frag = hindi_client.get("/hi/rashifal/aries",
                            headers={"HX-Rashifal-Fragment": "1"}).text
    links = set(re.findall(r'href="((?:/hi)?/rashifal/[a-z]+)"', frag))
    assert links == {"/hi/rashifal/aries"}, f"Hindi fragment links out to English: {links}"
    share = re.search(r"wa\.me/\?text=([^\"]*)", frag)
    assert share, "no share link in the fragment"
    assert "%2Fhi%2Frashifal" in share.group(1) or "/hi/rashifal" in share.group(1), \
        "the Hindi card shares the English URL"

    en = hindi_client.get("/rashifal/aries", headers={"HX-Rashifal-Fragment": "1"}).text
    assert set(re.findall(r'href="((?:/hi)?/rashifal/[a-z]+)"', en)) == {"/rashifal/aries"}, \
        "the English fragment acquired Hindi links"


def test_hindi_hub_breadcrumbs_are_hindi(hindi_client):
    """QA F4. The single rashi page was fixed for exactly this and the hub was
    missed — in the same commit that set `lang_prefix` two lines above the
    hardcoded breadcrumb. /hi/rashifal shipped a BreadcrumbList byte-identical
    to the English hub's, English name and English URL, under a canonical
    pointing at the Hindi URL.
    """
    import json

    for path, want_hi in (("/hi/rashifal", True), ("/rashifal", False)):
        blobs = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                           hindi_client.get(path).text, re.S)
        crumbs = None
        for b in blobs:
            d = json.loads(b)          # must also PARSE
            if d.get("@type") == "BreadcrumbList":
                crumbs = [(i["name"], i["item"]) for i in d["itemListElement"]]
        assert crumbs, f"no BreadcrumbList on {path}"
        terminal_url = crumbs[-1][1]
        assert ("/hi/" in terminal_url) is want_hi, f"{path} terminal crumb: {terminal_url}"
        if want_hi:
            assert any("ऀ" <= ch <= "ॿ" for ch in crumbs[-1][0]), \
                f"Hindi hub breadcrumb name is English: {crumbs[-1][0]!r}"


def test_hindi_labelled_links_stay_in_hindi(hindi_client):
    """QA F5. Two visible anchors on the Hindi reading page carried Hindi
    LABELS and pointed at the English hub, so "सभी 12 राशियाँ" landed a Hindi
    reader in English even though /hi/rashifal exists.

    The footer is excluded: it is entirely English by design, and its
    "Daily Rashifal" link is correct.
    """
    html = hindi_client.get("/hi/rashifal/aries").text
    body = html.split("<footer")[0]
    for m in re.finditer(r'<a href="(/rashifal[^"]*)"[^>]*>(.*?)</a>', body, re.S):
        label = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        assert not any("ऀ" <= ch <= "ॿ" for ch in label), (
            f"Hindi label {label!r} points at the English URL {m.group(1)}"
        )


@pytest.mark.parametrize("path", ["/rashifal/ARIES", "/hi/rashifal/ARIES", "/rashifal/Aries"])
def test_noncanonical_url_emits_no_hreflang(hindi_client, path):
    """QA secondary 3, which QA judged worth fixing rather than noise.

    `_normalise` lowercases, so a mixed-case URL was treated as published and
    got the full triple — whose three hrefs are all lowercase, so NONE of them
    is the URL being served. A one-sided annotation on an indexable 200 page
    is the exact mechanism hreflang_alternates' own docstring says makes
    Google discard hreflang site-wide, which would poison the 26 annotations
    the whole issue rests on. `main` emits nothing there, so #124 introduced it.
    """
    r = hindi_client.get(path)
    assert r.status_code == 200, f"{path} stopped serving"
    assert _alternates(r.text) == [], f"{path} claims alternates that do not include itself"


def test_degraded_hindi_page_is_in_hindi(hindi_client, monkeypatch):
    """QA F9. With every provider exhausted, the Hindi URL served an English
    error page under <html lang="en"> at a self-canonical, sitemapped,
    hi-IN-annotated URL. The 503 keeps it out of the index, so the cost was
    to the reader.
    """
    from astro_ai.providers import AllProvidersExhausted
    import astro_ai.llm as llm

    def boom(*a, **k):
        raise AllProvidersExhausted("all providers down")

    monkeypatch.setattr(llm.providers, "chat", boom)

    hi = hindi_client.get("/hi/rashifal/aries")
    assert hi.status_code == 503
    assert re.search(r'<html[^>]*lang="hi"', hi.text), "the Hindi error page declares lang=en"
    title = re.search(r"<title>([^<]*)", hi.text).group(1)
    assert any("ऀ" <= ch <= "ॿ" for ch in title), f"English title on the Hindi page: {title!r}"

    en = hindi_client.get("/rashifal/aries")
    assert en.status_code == 503
    en_title = re.search(r"<title>([^<]*)", en.text).group(1)
    assert not any("ऀ" <= ch <= "ॿ" for ch in en_title), f"Devanagari leaked into English: {en_title!r}"


def test_lang_prefix_is_keyed_on_path_not_language_alone(hindi_client):
    """QA F7 — the condition `lang_prefix_for` exists for had zero coverage.

    With a `hi` cookie, /rashifal/aries renders Hindi at an ENGLISH url, and
    its links and structured data must stay English because that is the URL
    it is published at. Keying the prefix on `lang == "hi"` alone reproduces
    FAIL 4 completely, and escaped the entire suite until this test.
    """
    hindi_client.post("/lang", data={"lang": "hi", "next": "/panchang"})
    html = hindi_client.get("/rashifal/aries").text

    canonical = re.search(r'<link rel="canonical" href="([^"]*)', html).group(1)
    assert canonical.endswith("/rashifal/aries") and "/hi/" not in canonical, canonical
    for got in re.findall(r'"(?:@id|url)": "([^"]*rashifal[^"]*)"', html):
        assert "/hi/" not in got, (
            f"Hindi-by-cookie at an English URL claims the Hindi identity: {got}"
        )


# --- QA round 3 ------------------------------------------------------------
# One of round 3's three defects (hx-boost eating the submit) is NOT here and
# cannot be: TestClient posts the form server-side and cannot run htmx, which
# is exactly why three rounds of server-side verification missed it.
# scripts/verify_lang_switch_browser.py covers it in Chromium.

def test_picker_form_opts_out_of_hx_boost(hindi_client):
    """The one server-visible half of that defect: the attribute's presence.

    This is a weak proxy for the real property and is here only so a careless
    edit trips something in the fast suite. The behaviour — that
    document.documentElement.lang and the 108% rule follow the control — is
    only checkable in a browser, and the gate is the real guard.
    """
    html = hindi_client.get("/rashifal").text
    form = re.search(r'<form[^>]*action="/lang"[^>]*>', html)
    assert form, "the language form is gone"
    assert 'hx-boost="false"' in form.group(0), (
        "the picker form must opt out of hx-boost: boosting swaps the body and "
        "leaves <html lang> stale, so the Hindi 108% rule never applies and a "
        "screen reader keeps the English voice. See "
        "scripts/verify_lang_switch_browser.py"
    )


def test_cooldown_degraded_page_is_localised(hindi_client, stub_llm, monkeypatch):
    """QA round 3. rashifal.py has THREE English-only degraded exits and round
    2 localised one. This is the most reachable of them: _REGEN_COOLDOWN_S is
    300, so a single quality-gate failure sends every request for that
    rashi+lang here for five minutes.
    """
    from astro_ai.routes import rashifal

    rashifal._regen_failures.clear()
    # raw passes the gate, the first section does not -> arms the cooldown
    stub_llm(lambda _n: "## Aries / Mesha\nToo short.\n\n## Taurus / Vrishabha\n" + "x" * 1200)

    hindi_client.get("/hi/rashifal/aries")          # arm
    hi = hindi_client.get("/hi/rashifal/aries")     # cooled
    assert hi.status_code == 503
    assert re.search(r'<html[^>]*lang="hi"', hi.text), "the cooled Hindi page declares lang=en"
    title = re.search(r"<title>([^<]*)", hi.text).group(1)
    assert any("ऀ" <= ch <= "ॿ" for ch in title), f"English title on the Hindi page: {title!r}"

    rashifal._regen_failures.clear()
    hindi_client.get("/rashifal/aries")
    en = hindi_client.get("/rashifal/aries")
    en_title = re.search(r"<title>([^<]*)", en.text).group(1)
    assert not any("ऀ" <= ch <= "ॿ" for ch in en_title), f"Devanagari leaked: {en_title!r}"


def test_degraded_card_retry_stays_in_hindi(hindi_client, stub_llm):
    """QA round 3, and it is round-1 F2 returning by another door.

    `_reading_error_fragment` hardcoded /rashifal/{slug}, and this branch is
    what pointed the Hindi hub's tiles at /hi/ — so a Hindi reader whose card
    failed pressed "Try again", the retry fetched the ENGLISH fragment, and an
    English reading was swapped into the Hindi hub. It also burns an English
    generation the reader cannot use, on the path G1 says will 429.
    """
    from astro_ai.routes import rashifal

    rashifal._regen_failures.clear()
    stub_llm(lambda _n: "## Aries / Mesha\nToo short.\n\n## Taurus / Vrishabha\n" + "x" * 1200)

    hindi_client.get("/hi/rashifal/taurus")
    frag = hindi_client.get("/hi/rashifal/taurus",
                            headers={"HX-Rashifal-Fragment": "1"}).text

    retries = re.findall(r'hx-get="([^"]*)"', frag)
    opens = re.findall(r'href="((?:/hi)?/rashifal/[a-z]+)"', frag)
    assert retries and all(r.startswith("/hi/") for r in retries), \
        f"the Hindi card retries into English: {retries}"
    assert opens and all(o.startswith("/hi/") for o in opens), \
        f"the Hindi card opens the English page: {opens}"
    assert any("ऀ" <= ch <= "ॿ" for ch in frag), "the Hindi card has no Devanagari at all"


def test_fragment_permalink_agrees_with_the_url_it_was_fetched_from(hindi_client, stub_llm, rashi_body):
    """QA round 3, finding 3: the comment claimed a path-keyed condition while
    the code was language-keyed, so at /rashifal/aries with a `hi` cookie the
    fragment's permalink was /hi/rashifal/aries while the page's own self_path
    was /rashifal/aries — two parts of one page disagreeing about its URL.
    """
    stub_llm(lambda _n: rashi_body(heading="Aries / Mesha"))
    hindi_client.post("/lang", data={"lang": "hi", "next": "/panchang"})

    frag = hindi_client.get("/rashifal/aries",
                            headers={"HX-Rashifal-Fragment": "1"}).text
    links = set(re.findall(r'href="((?:/hi)?/rashifal/[a-z]+)"', frag))
    assert links == {"/rashifal/aries"}, (
        f"fragment fetched at the ENGLISH url claims {links}; it must match the "
        "URL it was fetched from, which is the one it is published at"
    )
