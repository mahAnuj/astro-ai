"""The learn-article sticky CTA must be able to sit on the mobile tab bar — #304.

The CTA was `fixed bottom-0 z-30` under a `z-40` tab bar, so it rendered, passed
review and was invisible and untappable. Geometry cannot be asserted from a
request path, so this pins the two markup facts the geometry depends on:

  * the tab bar carries the hook the CTA's script measures. Rename it and the
    script silently falls back to a hardcoded offset that is wrong at any root
    font size (Hindi is 1.08x: 3px of the CTA ends up under the bar).
  * the CTA starts hidden by CLASS, never an inline `display`. An inline
    `display:flex` outranks `md:hidden`, which put the mobile-only bar on desktop.
"""
from __future__ import annotations

import re

ARTICLE = "/learn/rahu-mahadasha-ketu-antardasha/"


def test_tab_bar_carries_the_hook_the_cta_measures(client):
    html = client.get(ARTICLE).text
    assert 'id="mobile-tab-bar"' in html
    assert "getElementById('mobile-tab-bar')" in html


def test_cta_is_hidden_by_class_not_inline_display(client):
    html = client.get(ARTICLE).text
    tag = re.search(r'<div id="learn-sticky-cta"[^>]*>', html).group(0)
    assert "display" not in tag, tag
    assert re.search(r'class="[^"]*\bhidden\b[^"]*\bmd:hidden\b', tag), tag
