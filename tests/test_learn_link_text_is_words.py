"""A learn article's link text must be words, never a bare URL path — #594.

`/learn/rahu-mahadasha-ketu-antardasha/` — the top organic landing page — closed
its Dasha callout with `<a href="/dasha">/dasha</a>`, so a reader met a URL
fragment in the middle of a sentence. A scan of the 76 articles found it was the
only one. This pins both the source and the rendered page, so a new article or a
copy-paste cannot bring the shape back.
"""
from __future__ import annotations

import re
from pathlib import Path

LEARN = Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates" / "learn"
ARTICLE = "/learn/rahu-mahadasha-ketu-antardasha/"
# An anchor whose whole visible text is a site path: `>/dasha<`, `>/kundli<`.
PATH_TEXT = re.compile(r"<a\b[^>]*>\s*/[a-z][a-z0-9/-]*\s*</a>")


def test_no_learn_template_uses_a_bare_path_as_link_text():
    offenders = [
        f"{f.name}: {m.group(0)}"
        for f in sorted(LEARN.glob("*.html"))
        for m in PATH_TEXT.finditer(f.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


def test_the_rahu_ketu_article_links_dasha_with_words(client):
    html = client.get(ARTICLE).text
    assert not PATH_TEXT.search(html), PATH_TEXT.search(html).group(0)
    assert re.search(r'<a href="/dasha">The Dasha calculator</a>', html)
