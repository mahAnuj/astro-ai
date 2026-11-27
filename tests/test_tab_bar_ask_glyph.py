"""#1530 -- the mobile tab bar's Ask glyph is ASCII `?`, not a fullwidth form.

U+2753 (the original) paints as a colour emoji; U+FF1F (its first replacement)
renders as an empty box on a device with no CJK fallback font. Plain U+003F is
in every font. The tab is found by its LABEL text, never its href: with no
saved chart the href is `/?needs_chart=ask` (#1177). Nothing here calls a model.
"""
from __future__ import annotations

from html.parser import HTMLParser

FULLWIDTH_QUESTION = chr(0xFF1F)


class _TabGlyphs(HTMLParser):
    """Maps tab label -> its first aria-hidden span's text, inside the quick nav."""

    def __init__(self):
        super().__init__()
        self._in_nav = False
        self._a_spans: list[dict] = []
        self._span: dict | None = None
        self._in_a = False
        self.tabs: list[list[dict]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "nav":
            self._in_nav = a.get("aria-label") == "Quick navigation"
        elif self._in_nav and tag == "a":
            self._in_a, self._a_spans = True, []
        elif self._in_nav and self._in_a and tag == "span":
            self._span = {"hidden": a.get("aria-hidden") == "true", "text": ""}
            self._a_spans.append(self._span)

    def handle_data(self, data):
        if self._span is not None:
            self._span["text"] += data

    def handle_endtag(self, tag):
        if tag == "span":
            self._span = None
        elif tag == "a" and self._in_nav and self._in_a:
            self.tabs.append(self._a_spans)
            self._in_a = False
        elif tag == "nav":
            self._in_nav = False


def _ask_glyph(html: str) -> str:
    p = _TabGlyphs()
    p.feed(html)
    assert p.tabs, "no <a> found inside the Quick navigation nav"
    for spans in p.tabs:
        label = next((s["text"].strip() for s in spans if not s["hidden"]), "")
        if label == "Ask":
            return next(s["text"] for s in spans if s["hidden"])
    raise AssertionError("no tab labelled 'Ask' in the Quick navigation nav")


def test_ask_tab_glyph_is_ascii_question_mark(client):
    r = client.get("/")
    assert r.status_code == 200
    assert FULLWIDTH_QUESTION not in r.text
    glyph = _ask_glyph(r.text).strip()
    assert glyph == "?"
    assert not any(ord(ch) >= 0xFF00 for ch in glyph)
