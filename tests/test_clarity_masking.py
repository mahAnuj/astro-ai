"""#908 -- Clarity's session replay must not record the visitor's details.

Clarity is loaded on every page when CLARITY_PROJECT_ID is set, and until #908 it
masked nothing: /kundli, /ask, /matching and /numerology all render birth details or
the question on screen, which a replay captures as text. `base.html` now puts
`data-clarity-mask="True"` on <body> on EVERY page, unconditionally.

Unconditionally, not "masked except public pages", because of hx-boost: htmx swaps
the body's CHILDREN and discards the response's <body> attributes, so an attribute
that varies by path is stale after a boosted click (/learn/ -> /kundli kept the
unmasked body it had been loaded with; QA round 1 on this PR). TestClient cannot run
htmx, so no test here can reproduce the swap. What these tests pin is the property
that makes the swap harmless: the tag is the same on every page, so whichever page
a visitor entered on, the live body carries the mask.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

CLARITY = "clarity908"
MASK = 'data-clarity-mask="True"'
SEEKER = "Zorbax Quillfeather"
LEARN_SLUG = "the-9-grahas-overview"       # a real article, see learn_registry.py
BASE_HTML = Path(__file__).resolve().parents[1] / "src/astro_ai/templates/base.html"


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


@pytest.mark.parametrize("path", [
    f"/learn/{LEARN_SLUG}/", "/learn/", "/about", "/privacy", "/terms", "/festivals",
    "/", "/kundli", "/matching", "/numerology", "/muhurat", "/panchang",
])
def test_the_body_is_masked_on_every_page_class(tracked_client, path):
    """Public content pages are masked too: the mask cannot vary by path (see the
    module docstring), so /learn is on the same footing as /kundli."""
    assert _masked(tracked_client, path), path


@pytest.mark.parametrize("path", ["/kundli", "/ask", "/ask?q=will+it+rain&c=general"])
def test_pages_that_render_a_saved_chart_are_masked(tracked_client, saved_chart, stub_llm, path):
    # `saved_chart` is a FACTORY: without the call there is no chart cookie, /ask
    # redirects to the homepage and /kundli renders its signed-out landing page,
    # which carries nothing personal -- so the test would prove nothing.
    stub_llm("## Personality\n" + "The chart favours patient work. " * 12)
    saved_chart(name=SEEKER)
    r = tracked_client.get(path)
    assert r.status_code == 200, f"{path}: {r.status_code}"
    assert str(r.url).split("?")[0].endswith(path.split("?")[0]), (
        f"{path} redirected to {r.url}: the saved chart did not take")
    assert SEEKER in r.text, f"{path} never rendered the visitor's details"
    assert MASK in _body_tag(r.text), path


@pytest.mark.parametrize("path", ["/no-such-page-908", "/learnx", "/hi/rashifal"])
def test_error_pages_and_the_hindi_prefix_are_masked(tracked_client, path):
    r = tracked_client.get(path)
    assert r.status_code in (200, 404), f"{path}: {r.status_code}"
    assert MASK in _body_tag(r.text), path


def test_the_body_tag_is_identical_on_every_path(tracked_client):
    """The property hx-boost depends on: if the tag differed between /learn/ and
    /kundli, a boosted click from one to the other would leave the live body with
    the first page's value."""
    paths = [f"/learn/{LEARN_SLUG}/", "/kundli", "/about", "/matching", "/no-such-page-908"]
    tags = {p: _body_tag(tracked_client.get(p).text) for p in paths}
    assert len(set(tags.values())) == 1, tags


def test_the_attribute_is_not_conditional_in_the_template_source():
    """Render-level equality above cannot see a condition keyed on something the
    test does not vary (the user, the language, a header). So also read the
    opening <body ...> tag in the source: it must carry the literal attribute and
    no Jinja statement inside the tag at all."""
    src = BASE_HTML.read_text()
    # line-anchored: the comments above it mention "<body>" in prose
    tag = re.search(r"^<body\b.*?>", src, re.S | re.M)
    assert tag, "no <body> tag in base.html"
    assert MASK in tag.group(0), tag.group(0)
    assert "{%" not in tag.group(0), (
        "the <body> tag holds a template statement; the mask must not be conditional "
        "(hx-boost discards a response's <body> attributes, so a varying value goes stale)")


def test_a_signed_in_page_shows_the_name_and_is_masked(tracked_client):
    """_nav.html renders the visitor's first name on every page. The body-wide mask
    is what covers it, so the chip carries no mask of its own."""
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
    assert re.search(r'<a href="/account"[^>]*>', r.text), "the signed-in chip is not in the nav"
    assert "Zorbax" in r.text, "the control is vacuous if the name never rendered"
    assert MASK in _body_tag(r.text)


def _privacy(client, clarity):
    from astro_ai.routes import deps

    env = deps.templates.env.globals
    saved = env.get("clarity_project_id")
    env["clarity_project_id"] = clarity
    try:
        return client.get("/privacy").text
    finally:
        env["clarity_project_id"] = saved


def test_privacy_page_discloses_the_replay_only_when_clarity_is_configured(client):
    assert "session replay" not in _privacy(client, "")
    on = _privacy(client, CLARITY)
    assert "session replay" in on
    # it must describe what was built: every page is masked, nothing is exempt
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", on))
    assert "On every page the on-screen text is masked" in flat
    assert "Clicks, scrolling and page layout may still be recorded" in flat
    assert "public information pages" not in flat


def test_privacy_page_says_the_request_log_holds_the_panchang_city(client):
    """/panchang's place box is a method="get" form pre-filled with the saved birth
    place (routes/panchang.py), so submitting it puts the place in the URL, which
    the request log records. The page must say so."""
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _privacy(client, "")))
    ops = flat[flat.index("Operational logs:"):]
    assert "/panchang?city=" in ops[:1400]
    assert "pre-filled with your saved birth place" in ops[:1400]
    # and the source it is true of: still a GET form carrying `city`
    panchang = (BASE_HTML.parent / "panchang.html").read_text()
    assert re.search(r'<form method="get" action="/panchang"', panchang)
    assert 'name="city"' in panchang
