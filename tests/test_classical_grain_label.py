"""#1370: no reader-facing string calls a modern textbook's grain table "classical".

knowledge/remedies.md holds the planet-to-grain table from a modern textbook (section 5.1); it is not
a classical ranking (#1321 ruled the wording on manglik-remedies, commit 0eaf9bd). Six more surfaces
still said "<Planet>'s classical grain". The ruled wording names no source in reader-facing text:
"the grain a modern textbook's table gives <Planet>".

#1380: three more wordings of the same overclaim, on /learn/sade-sati ("a classical Saturn grain"),
/learn/career-during-sade-sati ("Saturn's grain in the classical remedy tables") and
/learn/rahu-remedies ("Classical charity items for Rahu"); _BAD now matches all three shapes.

A phrase test: it catches the wording it names, not every possible rewording.
"""
from __future__ import annotations

import html
import pathlib
import re

import pytest

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "astro_ai"
_BAD = re.compile(
    r"classical\s+(?:\w+\s+)?grain|grain\s+in\s+the\s+classical|classical\s+charity", re.I)

_PAGES = (
    ("/learn/mars-remedies/", "Mars"),
    ("/learn/mercury-remedies/", "Mercury"),
    ("/learn/jupiter-remedies/", "Jupiter"),
    ("/learn/rahu-remedies/", "Rahu"),
    ("/learn/mangal-mars-in-vedic-astrology/", "Mars"),
    ("/learn/sade-sati/", "Saturn"),
    ("/learn/career-during-sade-sati/", "Saturn"),
)


def _text(page: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))


def test_no_source_file_calls_a_grain_classical():
    files = list((_SRC / "templates").rglob("*.html"))
    files += [_SRC / n for n in ("numerology.py", "learn_registry.py", "i18n.py")]
    assert len(files) > 50, "template scan found almost nothing; the glob is wrong"
    hits = [str(f.relative_to(_SRC)) for f in files if _BAD.search(f.read_text(encoding="utf-8"))]
    assert not hits, hits


@pytest.mark.parametrize("path,planet", _PAGES)
def test_remedy_pages_use_the_ruled_grain_wording(client, path, planet):
    r = client.get(path)
    assert r.status_code == 200
    t = _text(r.text)
    assert not _BAD.search(t), path
    assert f"the grain a modern textbook's table gives {planet}" in t, path


def test_numerology_mars_fasting_day_uses_the_ruled_wording():
    from astro_ai.numerology import _REMEDIES

    mars = [r for r in _REMEDIES.values() if r is not None and r.planet == "Mars"]
    assert mars, "no Mars numerology remedy found"
    for r in mars:
        assert "the grain a modern textbook's table gives Mars" in r.fasting_day
        assert not _BAD.search(r.fasting_day)
