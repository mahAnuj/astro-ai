"""Learn articles must hand the reader to a tool while they are still reading — #518.

#518 measured that /learn/* is the front door (56% of sessions, 1.32 pages/session
against 3.75 on the homepage) and that almost no article offers a route to a tool
before the very bottom of the page. Slices 1-3 add one `callout-tip` straight after
the "In short" callout. This pins the three things a later edit can silently undo:

  * the route is still in the FIRST screen's worth of the article, and points at the
    tool page (`/kundli`), not at `/` (the homepage, which is not a tool);
  * it is a SIBLING after the "In short" callout, not nested inside it;
  * gajakesari-yoga no longer says Kundali Matching "compares yogas across both
    charts". `matching.py` has no yoga code and a rendered /matching result shows
    none, so the sentence promised a feature the product does not have. The same
    sentence was fixed on panch-mahapurush-yoga in slice 2 (#615) and was left here
    as a named follow-up.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LEARN = ROOT / "src" / "astro_ai" / "templates" / "learn"

# Slice 3's articles, each of which must carry a first-screen route to /kundli. Slices
# 1-2 are not re-pinned here: their pages are owned by their own PRs.
SLICE_3 = [
    "gajakesari-yoga",
    "pushya-nakshatra",
    "ashwini-nakshatra",
    "guru-jupiter-in-vedic-astrology",
    "mangal-mars-in-vedic-astrology",
    "sun-in-10th-house-career",
]

# A route that sits past this share of the article body is the "92% depth" defect.
FIRST_SCREEN_SHARE = 0.15


@pytest.mark.parametrize("slug", SLICE_3)
def test_first_kundli_link_is_in_the_first_screen(slug):
    src = (LEARN / f"{slug}.html").read_text()
    pos = src.find('href="/kundli"')
    assert pos != -1, f"{slug}: no link to /kundli"
    assert pos / len(src) <= FIRST_SCREEN_SHARE, (
        f"{slug}: first /kundli link at {pos / len(src):.0%} of the article"
    )


@pytest.mark.parametrize("slug", SLICE_3)
def test_article_renders_with_the_callout(client, slug):
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    assert 'callout callout-tip' in r.text
    assert 'href="/kundli"' in r.text


class _Nesting(HTMLParser):
    """Records, for the first insight callout and the first tip callout, the id of the
    element that CONTAINS each (and the tip's immediately preceding sibling)."""

    VOID = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "path"}

    def __init__(self):
        super().__init__()
        self.stack: list[tuple[str, int]] = []
        self.n = 0
        self.insight_parent = self.tip_parent = None
        self.insight_closed_before_tip = False
        self._insight_id = None

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        self.n += 1
        cls = dict(attrs).get("class") or ""
        parent = self.stack[-1][1] if self.stack else None
        if tag == "div" and "callout-insight" in cls.split() and self.insight_parent is None:
            self.insight_parent, self._insight_id = parent, self.n
        if tag == "div" and "callout-tip" in cls.split() and self.tip_parent is None:
            self.tip_parent = parent
            # closed iff the insight callout is no longer on the open-element stack
            self.insight_closed_before_tip = not any(i == self._insight_id for _, i in self.stack)
        self.stack.append((tag, self.n))

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break


@pytest.mark.parametrize("slug", SLICE_3)
def test_tip_is_a_sibling_after_the_insight_callout_not_nested_in_it(client, slug):
    """QA round 1 on PR #658: the first draft put the tip INSIDE the 'In short' box,
    between its label and its summary. Byte position could not see that."""
    p = _Nesting()
    p.feed(client.get(f"/learn/{slug}/").text)
    assert p.insight_parent is not None and p.tip_parent is not None
    assert p.insight_closed_before_tip, f"{slug}: tip is nested inside the insight callout"
    assert p.tip_parent == p.insight_parent, f"{slug}: tip is not a sibling of the insight callout"


def test_gajakesari_does_not_claim_matching_compares_yogas():
    src = (LEARN / "gajakesari-yoga.html").read_text()
    assert "compares yogas" not in src
    # Its tool links must go to the tool, not the homepage.
    assert 'href="/">free Janma Kundli' not in src


def test_matching_module_still_has_no_yoga_code():
    """The premise behind the sentence above. If matching ever grows yoga output this
    fails, and the copy may be revisited on purpose rather than by drift."""
    matching = (ROOT / "src" / "astro_ai" / "matching.py").read_text().lower()
    assert "yoga" not in matching
