"""#310 -- the PWA install banner must not cover the first-fold CTA.

SCOPE, STATED PLAINLY: a request-path test sees markup and script text, not
layout. These tests pin the facts the fix is made of -- the banner ships
`hidden`, both reveal paths go through one live scroll condition, the listener is
removed on dismiss, and the /learn stacking rule exists. They do NOT prove that the banner
stays off the button at 375x667; that was measured in headless Chrome (see the
issue) and no gate in this repo can see it. A rendered-layout change that keeps
every string below would pass.
"""
from __future__ import annotations

import re


def _home(client) -> str:
    r = client.get("/")
    assert r.status_code == 200
    return r.text


def _script(html: str) -> str:
    """The inline PWA bootstrap -- the <script> that owns DISMISS_KEY."""
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    hits = [b for b in blocks if "bhagya_pwa_install_dismissed" in b]
    assert len(hits) == 1, len(hits)
    return hits[0]


def test_banner_ships_hidden(client):
    tag = re.search(r'<div id="pwa-install-banner" class="([^"]*)"', _home(client))
    assert tag, "banner markup missing"
    assert "hidden" in tag.group(1).split()


def test_neither_reveal_path_unhides_the_banner_directly(client):
    # Both the beforeinstallprompt handler and the iOS branch used to call
    # banner.classList.remove('hidden') themselves. Now no code path may: the
    # only visibility write is sync()'s scroll-conditioned toggle.
    js = _script(_home(client))
    assert "banner.classList.remove('hidden')" not in js
    assert js.count("want();") == 2, "both reveal paths must go through want()"


def test_visibility_is_a_live_scroll_condition(client):
    js = _script(_home(client))
    m = re.search(r"function sync\(\) \{(.*?)\n      \}", js, re.S)
    assert m, "sync() missing"
    body = m.group(1)
    assert "banner.classList.toggle('hidden', !(window.scrollY > window.innerHeight * 0.4))" in body
    # QA on PR #891: a one-way latch left the banner on the CTA after the
    # visitor scrolled down and back up. sync() must therefore never stop
    # watching or latch a flag when it shows the banner.
    assert "stopWatching" not in body
    assert not re.search(r"\bshown\s*[=,;]", js), "a `shown` latch is back"


def test_the_scroll_listener_exists_and_dismiss_removes_it(client):
    js = _script(_home(client))
    assert "window.addEventListener('scroll', sync, { passive: true })" in js
    stop = re.search(r"function stopWatching\(\) \{(.*?)\n      \}", js, re.S).group(1)
    assert "removeEventListener('scroll', sync)" in stop
    body = re.search(r"function dismiss\(\) \{(.*?)\n      \}", js, re.S).group(1)
    assert "stopWatching();" in body


def test_dismiss_persists_and_closes_the_gate(client):
    js = _script(_home(client))
    body = re.search(r"function dismiss\(\) \{(.*?)\n      \}", js, re.S).group(1)
    assert "gone = true" in body
    assert "localStorage.setItem(DISMISS_KEY, '1')" in body
    # sync() must honour it, or a dismissed banner could come back on scroll.
    assert "if (gone || !wanted) return;" in js


def test_eligibility_checks_still_precede_any_reveal(client):
    js = _script(_home(client))
    i = js.index("localStorage.getItem(DISMISS_KEY) === '1'")
    assert i < js.index("display-mode: standalone") < js.index("function sync")


def test_learn_article_stacks_the_banner_above_the_sticky_cta(client):
    r = client.get("/learn/rahu-mahadasha-ketu-antardasha/")
    assert r.status_code == 200
    # The block that owns the rule: the nearest @media opener above it.
    at = r.text.find("body.learn-sticky-cta-visible #pwa-install-banner {")
    assert at != -1, "banner stacking rule missing"
    opener = r.text.rfind("@media", 0, at)
    assert r.text[opener:at].startswith("@media (max-width: 767px)"), \
        "banner stacking rule is outside the <768px media query"
    # Still inside that block (not after its closing brace): open braces == 1.
    between = r.text[opener:at]
    assert between.count("{") - between.count("}") == 1
    rule = re.match(r"[^{]*\{([^}]*)\}", r.text[at:])
    assert "bottom: var(--learn-fab-bottom, 9.5rem) !important" in rule.group(1)
