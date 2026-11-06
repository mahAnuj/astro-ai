"""Every page exposes one <main id="main-content"> and a skip link to it — #731.

Before: `/` — the busiest landing page — had no <main> at all (it was the only
visitor-facing top-level template without one), and no page had a skip link, so
a keyboard user crossed 12-14 Tab stops of header before reaching the form
(WCAG 2.4.1 Bypass Blocks, 1.3.1). Nothing failed and nothing rendered wrong, so
no gate could see it; this file is the gate.

The link and its target are two halves of one claim: a skip link whose target id
is missing is a link that goes nowhere, and a <main> nobody links to is the
status quo. So each page is asserted on BOTH.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGES = ["/", "/kundli", "/matching", "/numerology", "/learn/"]
TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "templates"

SKIP_LINK = re.compile(r'<a\s+href="#main-content"[^>]*>\s*([^<]+?)\s*</a>')


@pytest.mark.parametrize("path", PAGES)
def test_skip_link_targets_exactly_one_main_landmark(client, path):
    html = client.get(path).text
    link = SKIP_LINK.search(html)
    assert link, f"{path}: no 'href=\"#main-content\"' skip link"
    assert len(re.findall(r'\bid="main-content"', html)) == 1, (
        f"{path}: the skip link's target id must exist exactly once"
    )
    assert len(re.findall(r"<main\b", html)) == 1, f"{path}: want exactly one <main>"
    assert re.search(r'<main\b[^>]*\bid="main-content"', html), (
        f"{path}: the id is not on the <main> element"
    )


@pytest.mark.parametrize("path", PAGES)
def test_skip_link_is_the_first_focusable_element(client, path):
    html = client.get(path).text
    body = html[html.index("<body"):]
    first = re.search(r"<(?:a|button|input|select|textarea|summary)\b[^>]*>", body)
    assert first and 'href="#main-content"' in first.group(0), (
        f"{path}: first focusable element is {first.group(0)[:80] if first else None!r}, "
        "not the skip link — the first Tab must offer the bypass"
    )


def test_skip_link_is_hidden_until_focused_and_not_printed(client):
    html = client.get("/").text
    opening = re.search(r'<a\s+href="#main-content"[^>]*>', html).group(0)
    assert re.search(r'class="(?:[^"]*\s)?sr-only\b', opening), opening
    assert "focus:not-sr-only" in opening, opening
    assert "no-print" in opening, opening


def test_skip_link_utilities_exist_in_the_committed_stylesheet():
    """Tailwind generates only the classes it sees. `focus:not-sr-only` was not
    in app.css before this change, so markup without a rebuild would ship a link
    that is hidden and STAYS hidden when focused — present, tabbable, invisible."""
    css = (TEMPLATES.parent / "static" / "css" / "app.css").read_text()
    for cls in (r"\.sr-only", r"\.focus\\:not-sr-only:focus", r"\.focus\\:fixed:focus"):
        assert re.search(cls, css), f"app.css has no rule for {cls}; run `npm run build:css`"


def test_skip_link_label_is_hindi_on_a_hindi_page(client):
    html = client.get("/hi/rashifal").text
    assert 'href="#main-content"' in html
    assert "Skip to content" not in html, "English skip label on a Hindi page"
    assert "मुख्य सामग्री पर जाएँ" in html


def test_every_page_level_main_carries_the_skip_target_id():
    """A new template with a bare <main> would re-open the gap on that page only,
    silently. Every top-level template that opens a <main> element must give it
    the id (comments that merely mention `<main>` do not open one)."""
    offenders = []
    for path in sorted(TEMPLATES.glob("*.html")):
        for m in re.finditer(r"^\s*<main\b[^>]*>", path.read_text(), re.M):
            if 'id="main-content"' not in m.group(0):
                offenders.append(f"{path.name}: {m.group(0)[:70]}")
    assert not offenders, offenders


def test_index_main_wraps_the_sections_but_not_the_nav_or_strip():
    src = (TEMPLATES / "index.html").read_text()
    assert src.count('<main id="main-content">') == 1 and src.count("</main>") == 1
    start, end = src.index('<main id="main-content">'), src.index("</main>")
    assert src.count('{% include "_panchang_strip.html" %}') == 1
    assert src.index('{% include "_nav.html" %}') < start
    assert src.index('{% include "_panchang_strip.html" %}') < start, (
        "the panchang strip must stay where index.html's note puts it, outside <main>"
    )
    assert "<section" in src[start:end] and src.count("<section") == src[start:end].count("<section")


def test_skip_target_clears_the_sticky_nav(client):
    """The nav is `sticky top-0` (65px at 375px). A bare #main-content scrolls
    flush to the viewport top and the nav covers the page heading (QA round 1,
    #731). The offset must be at least the nav height, i.e. >= 4.5rem."""
    html = client.get("/kundli").text
    m = re.search(r"#main-content\s*\{[^}]*scroll-margin-top:\s*([\d.]+)rem", html)
    assert m, "no #main-content scroll-margin-top rule in the rendered page"
    assert float(m.group(1)) >= 4.5, f"{m.group(1)}rem < 72px: the nav would cover the heading"
