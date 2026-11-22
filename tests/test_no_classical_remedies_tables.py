"""#1386: no reader-facing string calls a modern textbook's remedy tables "classical".

knowledge/remedies.md is sourced primarily from one modern textbook's planet-by-planet remedy tables
(its Ch. 34); it is not a classical ranking (#1321 ruled the wording on manglik-remedies, #1370 and #1380
on the grain table). /learn/debilitated-sun-career still called them "the classical remedies tables we
hold". The ruled wording is the one /learn/surya-sun-remedies already uses: "one modern textbook's
planet-by-planet remedy table".

A phrase test: it catches the wording it names (English and Devanagari), not every possible rewording.
It matches the plural "remedies tables" only. The singular shape, "the classical remedy tables" on
/learn/career-during-sade-sati, is #1380's (open on its own branch, tests/test_classical_grain_label.py);
widen this to remed(?:y|ies) once that has merged.
"""
from __future__ import annotations

import html
import pathlib
import re

import pytest

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "astro_ai"
_BAD = re.compile(
    r"classical\s+(?:\w+\s+){0,2}remedies\s+tables?"
    r"|शास्त्रीय\s+उपाय\s+(?:तालिका|सारणी)",
    re.I,
)

_PAGES = ("/learn/debilitated-sun-career/", "/learn/surya-sun-remedies/")
_RULED = "one modern textbook's planet-by-planet remedy tables"


def _text(page: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))


def test_no_source_file_calls_a_remedy_table_classical():
    files = list((_SRC / "templates").rglob("*.html"))
    files += [_SRC / n for n in ("numerology.py", "learn_registry.py", "i18n.py")]
    files += list((_SRC / "prompts").glob("*.txt"))
    assert len(files) > 50, "template scan found almost nothing; the glob is wrong"
    hits = [str(f.relative_to(_SRC)) for f in files if _BAD.search(f.read_text(encoding="utf-8"))]
    assert not hits, hits


@pytest.mark.parametrize("path", _PAGES)
def test_rendered_pages_do_not_call_a_remedy_table_classical(client, path):
    r = client.get(path)
    assert r.status_code == 200
    t = _text(r.text)
    assert not _BAD.search(t), path


def test_debilitated_sun_page_names_the_textbook_tables_plainly(client):
    t = _text(client.get("/learn/debilitated-sun-career/").text)
    assert _RULED in t
