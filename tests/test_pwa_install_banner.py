"""#310 -- the PWA install banner must not cover the first-fold CTA.

SCOPE, STATED PLAINLY: a request-path test sees markup and script text, not
layout. These tests pin the facts the fix is made of -- the banner ships
`hidden`, both reveal paths go through one scroll gate, the gate is released on
dismiss, and the /learn stacking rule exists. They do NOT prove that the banner
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
    # banner.classList.remove('hidden') themselves. Now exactly one place may.
    js = _script(_home(client))
    assert js.count("banner.classList.remove('hidden')") == 1
    assert js.count("want();") == 2, "both reveal paths must go through want()"


def test_the_one_reveal_is_gated_on_scroll_depth(client):
    js = _script(_home(client))
    m = re.search(r"function maybeShow\(\) \{(.*?)\n      \}", js, re.S)
    assert m, "maybeShow() missing"
    body = m.group(1)
    assert "window.scrollY > window.innerHeight * 0.4" in body
    assert body.index("window.scrollY") < body.index("banner.classList.remove('hidden')")


def test_the_scroll_listener_is_removed_when_shown_or_dismissed(client):
    js = _script(_home(client))
    assert "window.addEventListener('scroll', maybeShow, { passive: true })" in js
    assert "window.removeEventListener('scroll', maybeShow)" in js
    stop = re.search(r"function stopWatching\(\) \{(.*?)\n      \}", js, re.S).group(1)
    assert "removeEventListener('scroll', maybeShow)" in stop
    for fn in ("maybeShow", "dismiss"):
        body = re.search(r"function %s\(\) \{(.*?)\n      \}" % fn, js, re.S).group(1)
        assert "stopWatching();" in body, fn


def test_dismiss_persists_and_closes_the_gate(client):
    js = _script(_home(client))
    body = re.search(r"function dismiss\(\) \{(.*?)\n      \}", js, re.S).group(1)
    assert "gone = true" in body
    assert "localStorage.setItem(DISMISS_KEY, '1')" in body
    # maybeShow() must honour it, or a dismissed banner could come back on scroll.
    assert "if (gone || shown || !wanted) return;" in js


def test_eligibility_checks_still_precede_any_reveal(client):
    js = _script(_home(client))
    i = js.index("localStorage.getItem(DISMISS_KEY) === '1'")
    assert i < js.index("display-mode: standalone") < js.index("function maybeShow")


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
