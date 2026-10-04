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
