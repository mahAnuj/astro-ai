"""#308 -- the feedback FAB must not sit on the first-fold CTA below md.

SCOPE, STATED PLAINLY: a request-path test sees markup and script text, not
layout. These tests pin the facts the fix is made of -- the FAB ships `fab-away`,
the away CSS exists only under max-width: 767px, sync() is one live condition made
of the 0.4 fold gate AND the scroll-up direction (plus the barely-scrolls
exception), and the script removes its previous listeners before adding new ones.
They do NOT prove the FAB stays off the home submit button at 375x667, or that it
returns on a scroll-up; that was measured in headless Chromium (see the issue)
and no gate in this repo can see it. A rendered-layout change that keeps every
string below would pass.
"""
from __future__ import annotations

import re


def _home(client) -> str:
    r = client.get("/")
    assert r.status_code == 200
    return r.text


def _script(html: str) -> str:
    """The widget's <script> -- the one that owns __fbFabSync."""
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    hits = [b for b in blocks if "__fbFabSync" in b]
    assert len(hits) == 1, len(hits)
    return hits[0]


def _sync_body(js: str) -> str:
    m = re.search(r"function sync\(\) \{(.*?)\n    \}", js, re.S)
    assert m, "sync() missing"
    return m.group(1)


def _fab_classes(html: str) -> list[str]:
    tag = re.search(r'<button id="feedback-fab" type="button"\s+class="([^"]*)"', html)
    assert tag, "FAB markup missing"
    return tag.group(1).split()


def test_fab_ships_away(client):
    assert "fab-away" in _fab_classes(_home(client))


def test_desktop_classes_are_unchanged(client):
    classes = _fab_classes(_home(client))
    for c in ("fixed", "bottom-24", "md:bottom-4", "right-4", "z-30"):
        assert c in classes, c


def test_away_css_applies_only_below_md(client):
    html = _home(client)
    at = html.find("#feedback-fab.fab-away {")
    assert at != -1, "away rule missing"
    opener = html.rfind("@media", 0, at)
    assert html[opener:at].startswith("@media (max-width: 767px)")
    # Still inside that block, not after its closing brace.
    between = html[opener:at]
    assert between.count("{") - between.count("}") == 1
    rule = re.match(r"[^{]*\{([^}]*)\}", html[at:]).group(1)
    for decl in ("opacity: 0", "visibility: hidden", "pointer-events: none"):
        assert decl in rule, decl
    # No hex colours in the widget's CSS (verify_redesign_tokens' rule).
    style = next(b for b in re.findall(r"<style>(.*?)</style>", html, re.S) if "fab-away" in b)
    assert "#" not in style.replace("#feedback-fab", ""), "a hex colour in the widget CSS"


def test_reduced_motion_removes_the_transition(client):
    html = _home(client)
    # base.html has its own global reduced-motion rule; this is the widget's.
    at = html.find("(max-width: 767px) and (prefers-reduced-motion: reduce)")
    assert at != -1
    block = html[at:html.index("</style>", at)]
    assert "transition: none" in block


def test_sync_is_the_fold_gate_and_the_scroll_up_direction(client):
    body = _sync_body(_script(_home(client)))
    assert "y > window.innerHeight * 0.4" in body
    assert "goingUp" in body.split("var show")[1].split(";")[0]
    assert "fab.classList.toggle('fab-away', !show)" in body
    # ~4px hysteresis on both directions so jitter does not flip it.
    assert "y > lastY + 4" in body and "y < lastY - 4" in body
    # A live condition, never a one-way latch.
    assert "removeEventListener" not in body


def test_a_page_that_barely_scrolls_keeps_the_fab(client):
    body = _sync_body(_script(_home(client)))
    assert "document.documentElement.scrollHeight - window.innerHeight < 40" in body
    show = body.split("var show")[1].split(";")[0]
    assert "barelyScrolls ||" in show


def test_previous_listeners_are_removed_before_new_ones_are_added(client):
    js = _script(_home(client))
    for ev in ("scroll", "resize", "pageshow"):
        rm = f"window.removeEventListener('{ev}', window.__fbFabSync)"
        add = f"window.addEventListener('{ev}', sync"
        assert rm in js and add in js, ev
        assert js.index(rm) < js.index(add), f"{ev}: add precedes remove (listeners stack)"
    assert "window.addEventListener('scroll', sync, { passive: true })" in js
    assert "window.__fbFabSync = sync;" in js


def test_sync_runs_once_at_start(client):
    js = _script(_home(client))
    assert js.index("window.addEventListener('pageshow', sync);") < js.index("\n    sync();")


def test_learn_sticky_lift_rule_still_exists(client):
    r = client.get("/learn/rahu-mahadasha-ketu-antardasha/")
    assert r.status_code == 200
    assert "body.learn-sticky-cta-visible #feedback-fab {" in r.text
