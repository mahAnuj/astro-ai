"""#908 -- Clarity's session replay must not record the visitor's details.

Clarity is loaded on every page when CLARITY_PROJECT_ID is set, and until #908 it
masked nothing: /kundli, /ask, /matching and /numerology all render birth details or
the question on screen, which a replay captures as text. `base.html` now puts
`data-clarity-mask="True"` on <body> by DEFAULT and exempts only a short list of
public-content paths where nothing personal renders. These tests render real pages
through the app and read the <body> tag the browser would receive.

The unmasked controls matter as much as the masked cases: a "fix" that masks the
whole site would pass the second half and quietly make every /learn replay useless.
"""
from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

CLARITY = "clarity908"
MASK = 'data-clarity-mask="True"'
SEEKER = "Zorbax Quillfeather"
LEARN_SLUG = "the-9-grahas-overview"       # a real article, see learn_registry.py


@pytest.fixture
def tracked_client(client):
    """Clarity configured (the id is env-driven and empty under test)."""
    from astro_ai.routes import deps

    env = deps.templates.env.globals
    saved = env.get("clarity_project_id")
    env["clarity_project_id"] = CLARITY
    try:
        yield client
    finally:
        env["clarity_project_id"] = saved


def _body_tag(html: str) -> str:
    m = re.search(r"<body\b[^>]*>", html)
    assert m, "no <body> tag in the response"
    return m.group(0)


def _masked(client, path: str, *, status: int = 200) -> bool:
    r = client.get(path)
    assert r.status_code == status, f"{path}: {r.status_code}"
    return MASK in _body_tag(r.text)


@pytest.mark.parametrize("path", ["/numerology", "/matching", "/muhurat", "/"])
def test_personal_form_pages_are_masked(tracked_client, path):
    assert _masked(tracked_client, path), path


@pytest.mark.parametrize("path", ["/kundli", "/ask", "/ask?q=will+it+rain&c=general"])
def test_pages_that_render_a_saved_chart_are_masked(tracked_client, saved_chart, stub_llm, path):
    # `saved_chart` is a FACTORY: without the call there is no chart cookie, /ask
    # redirects to the homepage and /kundli renders its signed-out landing page,
    # both of which are masked anyway -- so the test would pass on a page that
    # carries nothing personal and prove nothing.
    stub_llm("## Personality\n" + "The chart favours patient work. " * 12)
    saved_chart(name=SEEKER)
    r = tracked_client.get(path)
    assert r.status_code == 200, f"{path}: {r.status_code}"
    assert str(r.url).split("?")[0].endswith(path.split("?")[0]), (
        f"{path} redirected to {r.url}: the saved chart did not take")
    assert SEEKER in r.text, f"{path} never rendered the visitor's details"
    assert MASK in _body_tag(r.text), path


def test_an_unknown_path_is_masked(tracked_client):
    """The default is MASK, so a route nobody listed is masked, not exposed."""
    assert _masked(tracked_client, "/no-such-page-908", status=404)


@pytest.mark.parametrize("path", [
    f"/learn/{LEARN_SLUG}/", "/learn/", "/about", "/privacy", "/terms", "/festivals",
])
def test_public_content_pages_are_not_masked(tracked_client, path):
    assert not _masked(tracked_client, path), path


@pytest.mark.parametrize("path", ["/learnx", "/aboutus", "/privacy-policy", "/festivalsx"])
def test_the_allowlist_matches_a_path_segment_not_a_substring(tracked_client, path):
    """`/learnx` is not `/learn/...`; it must stay masked."""
    r = tracked_client.get(path)
    assert r.status_code == 404
    assert MASK in _body_tag(r.text), path


def test_a_hindi_prefixed_page_is_masked(tracked_client):
    """/hi/rashifal reaches base.html with the prefix intact (routes/hindi.py), so
    it is simply not on the allowlist."""
    assert _masked(tracked_client, "/hi/rashifal")


def test_the_signed_in_name_in_the_nav_is_masked_even_on_a_public_page(tracked_client):
    """_nav.html renders the visitor's first name on every page, /learn included, so
    the unmasked allowlist alone would let a replay read it."""
    from astro_ai.routes import deps

    env = deps.templates.env.globals
    real = env["load_current_user"]
    env["load_current_user"] = lambda request: SimpleNamespace(
        name="Zorbax Quillfeather", email="seeker7731@example.test")
    try:
        r = tracked_client.get(f"/learn/{LEARN_SLUG}/")
    finally:
        env["load_current_user"] = real
    assert r.status_code == 200
    assert MASK not in _body_tag(r.text), "the public page itself must stay unmasked"
    chip = re.search(r'<a href="/account"[^>]*>', r.text)
    assert chip, "the signed-in chip is not in the nav"
    assert MASK in chip.group(0)
    assert "Zorbax" in r.text, "the control is vacuous if the name never rendered"


def test_privacy_page_discloses_the_replay_only_when_clarity_is_configured(client):
    from astro_ai.routes import deps

    env = deps.templates.env.globals
    saved = env.get("clarity_project_id")
    try:
        env["clarity_project_id"] = ""
        off = client.get("/privacy").text
        env["clarity_project_id"] = CLARITY
        on = client.get("/privacy").text
    finally:
        env["clarity_project_id"] = saved
    assert "session replay" not in off
    assert "session replay" in on
