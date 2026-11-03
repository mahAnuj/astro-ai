"""/matching title and meta description — #508.

GSC 2026-09-23..10-20: /matching ranked 4.3 on 336 impressions with 0 clicks, and its
title was 91 characters (truncated in a result). The new pair leads with the query
phrase and stays inside the display budget. This pins what a later edit can silently undo:

  * the length bounds (the template appends no site suffix, so the block IS the <title>);
  * the title leads with the query phrase "Free Kundli Matching" and carries the 36 total,
    which matching.py fixes (eight kootas, maximums summing to 36);
  * the description still carries the claims the page backs: all 8 kootas, Manglik, Nadi;
  * the rendered page carries both strings, and og:title mirrors the title.
"""
from __future__ import annotations

import html
import re


def _head(client):
    r = client.get("/matching")
    assert r.status_code == 200
    title = html.unescape(re.search(r"<title>(.*?)</title>", r.text, re.S).group(1).strip())
    desc = html.unescape(
        re.search(r'<meta name="description" content="(.*?)">', r.text, re.S).group(1)
    )
    og = html.unescape(
        re.search(r'<meta property="og:title" content="(.*?)">', r.text, re.S).group(1)
    )
    return title, desc, og


def test_title_length_and_lead(client):
    title, _, _ = _head(client)
    assert 0 < len(title) <= 60, f"{len(title)} chars: {title!r}"
    assert title.startswith("Free Kundli Matching"), title
    assert "36" in title and "Guna Milan" in title, title


def test_description_length_and_claims(client):
    _, desc, _ = _head(client)
    assert 0 < len(desc) <= 155, f"{len(desc)} chars: {desc!r}"
    low = desc.lower()
    for word in ("8 kootas", "36", "manglik", "nadi", "no signup"):
        assert word in low, f"{word} missing from {desc!r}"


def test_og_title_mirrors_title(client):
    title, _, og = _head(client)
    assert og == title
