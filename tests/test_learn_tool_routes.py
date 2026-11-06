"""Learn articles must hand the reader to a tool while they are still reading — #518.

#518 measured that /learn/* is the front door (56% of sessions, 1.32 pages/session
against 3.75 on the homepage) and that almost no article offers a route to a tool
before the very bottom of the page. Slices 1-4 add one `callout-tip` straight after
the "In short" callout. This pins the things a later edit can silently undo:

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

import re
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

# Slice 4's articles (the highest-impression pages whose first tool link was deep), each
# mapped to the tool its tip must reach in the first screen. The tool differs per article,
# so these are (slug, href) pairs; slice 3 is always /kundli.
SLICE_4 = [
    ("rahu-mahadasha-ketu-antardasha", "/dasha"),
    ("sade-sati", "/sade-sati-check"),
    ("manglik-dosh", "/manglik-check"),
    ("kundali-matching-ashtakoot-guna-milan", "/matching"),
    ("saturn-in-10th-house-career", "/kundli"),
    ("gochar-2026-planetary-transits", "/sade-sati-check"),
]

# Slice 5 — the last 30 zero-route articles, which closes #518's "0 articles with no route"
# criterion. (slug, tool) pairs. Life-question articles go to /dasha only where the
# question is WHEN (marriage-timing-kundli); the rest are about placement, so /kundli.
# karva-chauth-2026 is outside the issue's table: its one tool-shaped question is "when
# does the Moon rise in my city", which only /panchang's Moonrise / Moonset tile answers.
SLICE_5 = (
    [(f"{n}-nakshatra", "/kundli") for n in (
        "ardra", "ashlesha", "bharani", "chitra", "hasta", "krittika", "magha",
        "mrigashira", "punarvasu", "purva-phalguni", "rohini", "swati", "uttara-phalguni")]
    + [(s, "/kundli") for s in (
        "budha-mercury-in-vedic-astrology", "ketu-in-vedic-astrology",
        "rahu-in-vedic-astrology", "surya-sun-in-vedic-astrology", "the-9-grahas-overview",
        "chandra-moon-remedies", "surya-sun-remedies", "pitru-dosh-remedies",
        "11th-lord-placement-gains-guide", "2nd-lord-placement-wealth-guide",
        "foreign-career-yoga-kundli", "job-or-business-kundli-guide",
        "love-vs-arranged-marriage-kundli", "second-marriage-yoga-kundli",
        "dhana-yoga-wealth-combinations")]
    + [("marriage-timing-kundli", "/dasha"), ("karva-chauth-2026", "/panchang")]
)

# Every article this file pins, with its expected tool.
ROUTED = [(slug, "/kundli") for slug in SLICE_3] + SLICE_4 + SLICE_5

# The tool pages an in-body route may point at (the same set #518 counts).
TOOL_HREF = re.compile(
    r'href="/(kundli|matching|dasha|ask|rashifal|numerology|muhurat|panchang|'
    r'manglik-check|kaal-sarp-check|sade-sati-check)\b'
)

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


@pytest.mark.parametrize("slug,href", SLICE_4)
def test_slice4_first_tool_link_is_in_the_first_screen(slug, href):
    src = (LEARN / f"{slug}.html").read_text()
    pos = src.find(f'href="{href}"')
    assert pos != -1, f"{slug}: no link to {href}"
    assert pos / len(src) <= FIRST_SCREEN_SHARE, (
        f"{slug}: first {href} link at {pos / len(src):.0%} of the article"
    )


@pytest.mark.parametrize("slug,href", SLICE_4)
def test_slice4_article_renders_with_the_callout(client, slug, href):
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    assert 'callout callout-tip' in r.text
    assert f'href="{href}"' in r.text


@pytest.mark.parametrize("slug,href", SLICE_5)
def test_slice5_first_tool_link_is_in_the_first_screen(slug, href):
    src = (LEARN / f"{slug}.html").read_text()
    pos = src.find(f'href="{href}"')
    assert pos != -1, f"{slug}: no link to {href}"
    assert pos / len(src) <= FIRST_SCREEN_SHARE, (
        f"{slug}: first {href} link at {pos / len(src):.0%} of the article"
    )


@pytest.mark.parametrize("slug,href", SLICE_5)
def test_slice5_article_renders_with_the_callout(client, slug, href):
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    assert 'callout callout-tip' in r.text
    assert f'href="{href}"' in r.text


def test_slice5_is_the_thirty_articles_the_issue_names():
    slugs = [s for s, _ in SLICE_5]
    assert len(slugs) == 30 and len(set(slugs)) == 30
    for s in slugs:
        assert (LEARN / f"{s}.html").exists(), s


def test_every_learn_article_routes_to_a_tool():
    """#518's target: 0 articles with no in-body route to a tool. This walks the directory,
    so it also fires on any FUTURE article that ships without one — that is intended."""
    bare = sorted(p.stem for p in LEARN.glob("*.html") if not TOOL_HREF.search(p.read_text()))
    assert not bare, f"{len(bare)} learn article(s) with no link to any tool: {bare}"


def test_saturn_in_10th_links_the_tool_not_the_homepage():
    """PR #680 left three links to `/` (the homepage) on this article. Each said 'Generate
    your free Janma Kundli'; they now go to /kundli. The 'aspects' promise beside one of them
    is gone too: a rendered /kundli lists sign, house and nakshatra, not aspects."""
    src = (LEARN / "saturn-in-10th-house-career.html").read_text()
    assert 'href="/"' not in src
    assert src.count('href="/kundli"') >= 4  # the tip + the three retargeted links
    assert "exact placement, sign, and aspects" not in src


def test_rahu_tip_was_moved_not_copied():
    """Rahu already carried this exact tip after "What the texts say"; slice 4 MOVES it to
    sit after "In short". One copy, and it is ahead of the classical callout."""
    src = (LEARN / "rahu-mahadasha-ketu-antardasha.html").read_text()
    tip = "Enter your birth details in the free Dasha calculator"
    assert src.count(tip) == 1
    assert src.count('<div class="callout-label">Find your own dates</div>') == 1
    assert src.index(tip) < src.index("What the texts say")


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
        # the insight callout OPENED before the tip did (an insight that appears only
        # after the tip would still leave the two "siblings", and still be wrong)
        self.insight_seen_before_tip = False
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
            self.insight_seen_before_tip = self._insight_id is not None
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


def _assert_tip_follows_insight_as_sibling(client, slug):
    p = _Nesting()
    p.feed(client.get(f"/learn/{slug}/").text)
    assert p.insight_parent is not None and p.tip_parent is not None
    assert p.insight_seen_before_tip, f"{slug}: the first tip precedes the insight callout"
    assert p.insight_closed_before_tip, f"{slug}: tip is nested inside the insight callout"
    assert p.tip_parent == p.insight_parent, f"{slug}: tip is not a sibling of the insight callout"


@pytest.mark.parametrize("slug", SLICE_3)
def test_tip_is_a_sibling_after_the_insight_callout_not_nested_in_it(client, slug):
    """QA round 1 on PR #658: the first draft put the tip INSIDE the 'In short' box,
    between its label and its summary. Byte position could not see that. Slice 3's QA
    also asked for the ORDER to be asserted: the insight callout comes first."""
    _assert_tip_follows_insight_as_sibling(client, slug)


@pytest.mark.parametrize("slug,href", SLICE_4)
def test_slice4_tip_is_a_sibling_after_the_insight_callout_not_nested_in_it(client, slug, href):
    _assert_tip_follows_insight_as_sibling(client, slug)


@pytest.mark.parametrize("slug,href", ROUTED)
def test_the_first_tip_is_the_one_that_routes_to_the_tool(client, slug, href):
    """The tip the nesting test finds is the FIRST `callout-tip`. Pin that it is the one
    carrying the tool link, so an older tip further down cannot satisfy the test while the
    first screen carries something else."""
    html = client.get(f"/learn/{slug}/").text
    start = html.index("callout callout-tip")
    assert f'href="{href}"' in html[start:start + 1500], f"{slug}: first tip does not link {href}"


@pytest.mark.parametrize("slug,href", SLICE_5)
def test_slice5_tip_is_a_sibling_after_the_insight_callout_not_nested_in_it(client, slug, href):
    _assert_tip_follows_insight_as_sibling(client, slug)


def test_pitru_dosh_tip_does_not_promise_a_pitru_dosh_check():
    """The render shows positions; chart.py has no Pitru Dosh detection (its only 'Pitru'
    is an amavasya note). The tip must not read as a detector."""
    src = (LEARN / "pitru-dosh-remedies.html").read_text()
    start = src.index("callout callout-tip")
    tip = src[start:src.index("</p>", start)]
    assert "does not run a Pitru Dosh test" in tip
    chart = (ROOT / "src" / "astro_ai" / "chart.py").read_text().lower()
    assert "pitru_dosh" not in chart and "pitru dosh" not in chart


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
