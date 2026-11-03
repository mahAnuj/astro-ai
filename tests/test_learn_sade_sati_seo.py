"""/learn/sade-sati/ title and meta description name the three Moon signs in Sade Sati — #685.

The page's old title was evergreen and named no sign, while the queries that reach it ask
"which rashi has sade sati now". The new pair names Aquarius, Pisces and Aries. Those
strings are true only while Saturn is in Pisces (until 2027-06-03, Lahiri); the dated
comment in learn_registry.py says so. This pins what a later edit can silently undo:

  * the length bounds (the template appends no site suffix, so seo_title IS the <title>);
  * the three signs, and "now", in the title;
  * the phase names Arambha / Madhya / Uttara stay out of both strings, because
    knowledge/SOURCES.md records them as UNSOURCED. The setting/peak/rising position
    words are what the engine and vedic_reference.md section 2.1 use;
  * the rendered page actually carries both strings.
"""
from __future__ import annotations

import html
import re

import pytest

from astro_ai.learn_registry import get_article

UNSOURCED_PHASE_NAMES = ("arambha", "madhya", "uttara")


@pytest.fixture(scope="module")
def article():
    art = get_article("sade-sati")
    assert art is not None
    return art


def test_title_length_and_signs(article):
    t = article.seo_title
    assert 0 < len(t) <= 60, f"{len(t)} chars: {t!r}"
    for sign in ("Aquarius", "Pisces", "Aries"):
        assert sign in t, f"{sign} missing from {t!r}"
    assert "now" in t.lower()


def test_description_length_and_phases(article):
    d = article.seo_description
    assert 0 < len(d) <= 155, f"{len(d)} chars: {d!r}"
    low = d.lower()
    for word in ("aquarius", "pisces", "aries", "setting", "peak", "rising"):
        assert word in low, f"{word} missing from {d!r}"
    # each sign is paired with the phase the page body gives it
    assert low.index("aquarius") < low.index("setting") < low.index("pisces") \
        < low.index("peak") < low.index("aries") < low.index("rising")


@pytest.mark.parametrize("field", ["seo_title", "seo_description"])
def test_unsourced_phase_names_absent(article, field):
    text = getattr(article, field).lower()
    for name in UNSOURCED_PHASE_NAMES:
        assert name not in text, f"{name} in {field}: SOURCES.md records it UNSOURCED"


def test_rendered_page_carries_both_strings(client, article):
    r = client.get("/learn/sade-sati/")
    assert r.status_code == 200
    title = re.search(r"<title>(.*?)</title>", r.text, re.S).group(1).strip()
    desc = re.search(r'<meta name="description" content="(.*?)">', r.text, re.S).group(1)
    assert html.unescape(title) == article.seo_title
    assert html.unescape(desc) == article.seo_description
