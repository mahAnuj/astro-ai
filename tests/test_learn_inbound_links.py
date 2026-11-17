"""Every /learn article is reachable from something other than the index, and the
tool pages hand a reader to the articles on their own subject — #1175 (#1107 criteria 1-2).

The measurement behind it (2026-11-17): /learn/ articles are 93% of search
impressions and tools barely appear, yet /panchang, /festivals, /manglik-check,
/sade-sati-check, /kaal-sarp-check and /numerology linked no specific article at
all, and 10 of the 77 articles had no inbound link except the /learn/ index
(krittika-nakshatra, mercury-remedies, job-or-business-kundli-guide,
santan-prapti-children-in-kundli, chronic-health-issues-kundli,
surya-sun-remedies, manglik-remedies, diwali-muhurat-2026, karva-chauth-2026,
name-numerology-explained). Nothing fails when an article loses its last link: the
page still renders and still sits in the sitemap, it is just found by nobody.

Two checks, both offline:

  * the GRAPH: an edge is an `/learn/<slug>` href in a template other than the
    index and the article's own, or a `related` entry in the registry (rendered as
    the "Related reading" block on every article). Python-side registries
    (festival_registry, chart.py topic summaries) are deliberately NOT edges: they
    reach a page only on some dates or some charts, which is not an inbound link a
    crawler can rely on, and counting them hid diwali-muhurat-2026 and
    karva-chauth-2026 from the issue's own orphan list.
  * the RENDER: each of the eight tool pages, with <nav>, <header> and <footer>
    dropped, shows at least two distinct specific article hrefs.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "src" / "astro_ai" / "templates"

# `/learn/<slug>` followed by a slash, a quote, a query or whitespace; the bare
# `/learn/` index has no slug and never matches.
LEARN_HREF = re.compile(r"/learn/([a-z0-9][a-z0-9-]*)")
JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)

# Not part of the public body: the index is the thing being compared against,
# emails are not pages, admin pages are not seen by a visitor.
NOT_A_LINKING_PAGE = {"learn_index.html"}


def _registry():
    from astro_ai.learn_registry import ARTICLES

    return ARTICLES


def _inbound_edges() -> dict[str, set[str]]:
    slugs = {a.slug for a in _registry()}
    inbound: dict[str, set[str]] = {s: set() for s in slugs}
    for path in sorted(TEMPLATES.rglob("*.html")):
        rel = path.relative_to(TEMPLATES)
        if (
            path.name in NOT_A_LINKING_PAGE
            or rel.parts[0] == "email"
            or path.name.startswith("admin_")
        ):
            continue
        own = path.stem if rel.parts[0] == "learn" else None
        text = JINJA_COMMENT.sub("", path.read_text(encoding="utf-8"))
        for slug in set(LEARN_HREF.findall(text)) & slugs:
            if slug != own:
                inbound[slug].add(f"template:{rel.as_posix()}")
    for article in _registry():
        for target in article.related:
            if target in slugs and target != article.slug:
                inbound[target].add(f"related:{article.slug}")
    return inbound


def test_the_registry_has_the_77_articles_the_issue_counted():
    # If this moves, the issue's "every one of the 77" moved with it; the graph
    # test below still holds for any N, this only keeps the number honest.
    assert len(_registry()) == 77


def test_every_article_has_an_inbound_link_other_than_the_index():
    orphans = sorted(s for s, edges in _inbound_edges().items() if not edges)
    assert not orphans, f"{len(orphans)} article(s) linked from nothing but /learn/: {orphans}"


def test_the_ten_named_orphans_are_each_linked_from_somewhere_specific():
    edges = _inbound_edges()
    named = [
        "krittika-nakshatra", "mercury-remedies", "job-or-business-kundli-guide",
        "santan-prapti-children-in-kundli", "chronic-health-issues-kundli",
        "surya-sun-remedies", "manglik-remedies", "diwali-muhurat-2026",
        "karva-chauth-2026", "name-numerology-explained",
    ]
    assert [s for s in named if not edges[s]] == []


def test_a_related_entry_names_a_real_article():
    # related_articles() skips a missing slug silently, so a typo is an edge that
    # exists in the source and not on the page.
    slugs = {a.slug for a in _registry()}
    dangling = sorted(
        f"{a.slug} -> {t}" for a in _registry() for t in a.related if t not in slugs
    )
    # swati-nakshatra -> vishakha-nakshatra is a planned article; it was dangling
    # before #1175 and is left to the article that adds it. No NEW one may appear.
    assert set(dangling) <= {"swati-nakshatra -> vishakha-nakshatra"}, dangling


class _BodyLinks(HTMLParser):
    """Collect `/learn/<slug>/` hrefs, ignoring everything inside nav/header/footer."""

    SKIP = {"nav", "header", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.slugs: set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1
        elif tag == "a" and not self.depth:
            href = dict(attrs).get("href") or ""
            m = re.fullmatch(r"/learn/([a-z0-9][a-z0-9-]*)/?", href)
            if m:
                self.slugs.add(m.group(1))

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1


def _body_article_links(html: str) -> set[str]:
    parser = _BodyLinks()
    parser.feed(html)
    parser.close()
    return parser.slugs


TOOL_PAGES = [
    "/panchang",
    "/festivals",
    "/muhurat",
    "/manglik-check",
    "/sade-sati-check",
    "/kaal-sarp-check",
    "/numerology",
    "/kundli",
]


@pytest.mark.parametrize("path", TOOL_PAGES)
def test_each_tool_page_links_at_least_two_distinct_articles_in_its_body(client, path):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    real = {a.slug for a in _registry()}
    found = _body_article_links(response.text)
    assert found <= real, f"{path} links an article that does not exist: {sorted(found - real)}"
    assert len(found) >= 2, f"{path}: {len(found)} distinct article link(s) in the body: {sorted(found)}"


def test_the_body_scan_ignores_nav_header_and_footer():
    html = (
        '<nav><a href="/learn/sade-sati/">x</a></nav>'
        '<header><a href="/learn/manglik-dosh">x</a></header>'
        '<main><a href="/learn/kaal-sarp-dosh/">y</a><a href="/learn/">index</a></main>'
        '<footer><a href="/learn/shani-saturn/">z</a></footer>'
    )
    assert _body_article_links(html) == {"kaal-sarp-dosh"}


@pytest.mark.parametrize("path", ["/manglik-check", "/sade-sati-check", "/kaal-sarp-check"])
def test_a_dosha_form_that_fails_to_compute_still_carries_its_articles(client, monkeypatch, path):
    # The articles are keyed by form_action, not by the GET handler, so the
    # error re-render (a different code path) must carry them too.
    from astro_ai.routes import dosha

    def _boom(*_a, **_k):
        raise dosha.ChartError("no such place")

    monkeypatch.setattr(dosha, "compute_chart", _boom)
    response = client.post(
        path, data={"birth_date": "1990-01-01", "birth_time": "10:00", "birth_place": "Nowhere"}
    )
    assert response.status_code == 400
    assert len(_body_article_links(response.text)) >= 2
