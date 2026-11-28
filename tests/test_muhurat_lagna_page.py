"""#1026 step 2: what the finder page shows of the Vivah lagna windows.

Each Vivah row the page calls auspicious (excellent, good, acceptable) carries a collapsed
"Lagna windows (Rao's guideline)" block in its Notes cell: the windows, or the module's sentence
that none met the guideline, then the caveat. One disclosure below the tables says how the windows
are read. Every other event, every caution row and every avoid row carries nothing, and the day
rating on the page is the one it had before the block existed.

The windows and the wording are pinned in test_muhurat_lagna.py; this file reads the RENDERED page.
No network (geocoding is stubbed to New Delhi) and no LLM. Mutation rows:
scripts/mutations/2026_11_24_1026_muhurat_lagna.py.
"""
from __future__ import annotations

import html
import importlib.util
import logging
import re
import sys
from datetime import date
from pathlib import Path

import pytest

DELHI = (28.61, 77.21, "Asia/Kolkata")
TODAY = date(2026, 11, 24)
CITY = "Delhi, India"
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "astro_ai"
_cache: dict[tuple, str] = {}


@pytest.fixture(autouse=True)
def _pinned(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    monkeypatch.setattr(route, "reading_today", lambda: TODAY)


def _post(client, event: str, days: int) -> str:
    r = client.post("/muhurat", data={"event_type": event, "city": CITY,
                                      "start_date": TODAY.isoformat(), "days": str(days)})
    assert r.status_code == 200
    return r.text


def _page(client, event: str, days: int) -> str:
    key = (event, days)
    if key not in _cache:
        _cache[key] = _post(client, event, days)
    return _cache[key]


def _text(h: str) -> str:
    return re.sub(r" ([.,)])", r"\1", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))).strip()


def _tables(h: str) -> list[str]:
    return re.findall(r"<table.*?</table>", h, flags=re.S)


def _rows(table: str) -> list[str]:
    return re.findall(r"<tr class=\"border-b.*?</tr>", table, flags=re.S)


def _blocks(h: str) -> list[str]:
    return re.findall(r"<details class=\"mt-1\" data-lagna>.*?</details>", h, flags=re.S)


def _legends(h: str) -> list[str]:
    return re.findall(r"<details[^>]*data-lagna-legend[^>]*>.*?</details>", h, flags=re.S)


def _notes(row: str) -> str:
    return re.search(r'<td data-label="Notes" data-span[^>]*>(.*?)</td>\s*</tr>', row, flags=re.S).group(1)


def _windows_cell(row: str) -> str:
    return re.search(r'<td data-label="Windows"[^>]*>(.*?)</td>', row, flags=re.S).group(1)


def _ml():
    from astro_ai import muhurat_lagna

    return muhurat_lagna


# --- the real Vivah page ---------------------------------------------------------------------


def test_every_auspicious_vivah_row_with_a_sunrise_has_one_block_in_its_notes_cell(client):
    h = _page(client, "vivah", 180)
    auspicious = _rows(_tables(h)[0])
    assert len(auspicious) >= 10, "premise: a real vivah search has many auspicious rows"
    with_sun = [r for r in auspicious if "No sunrise-to-sunset span" not in r]
    assert with_sun, "premise: ordinary dates exist"
    assert len(_blocks(h)) == len(with_sun)
    for row in with_sun:
        assert len(_blocks(row)) == 1, "one block per row"
        assert "data-lagna" in _notes(row), "the block sits in the wide Notes cell"
        assert "data-lagna" not in _windows_cell(row), "not in the 220px Windows cell"


def test_the_block_follows_the_reason_and_the_why_list(client):
    h = _page(client, "vivah", 180)
    row = next(r for r in _rows(_tables(h)[0]) if "data-lagna" in r)
    notes = _notes(row)
    assert notes.split("<details")[0].strip(), "the reason text comes first"
    assert notes.index("Why this date") < notes.index("Lagna windows"), "the include order"


def test_a_block_shows_the_ruled_heading_caveat_and_the_unchanged_note(client):
    ml = _ml()
    h = _page(client, "vivah", 180)
    with_windows = [b for b in _blocks(h) if "<li>" in b]
    assert with_windows, "premise: some row has a window"
    t = _text(with_windows[0])
    assert t.startswith(ml.HEADING)
    assert ml.CAVEAT in t
    assert "The day rating is unchanged." in t
    assert re.search(r'<span class="tabular-nums">\d\d:\d\d-\d\d:\d\d</span> [A-Z][a-z]+', with_windows[0])


def test_caution_and_avoid_rows_and_the_restricted_table_carry_no_block(client):
    h = _page(client, "vivah", 180)
    tables = _tables(h)
    assert len(tables) >= 2 and "Use with caution" in h, "premise: this search has caution rows"
    assert "data-lagna" not in tables[1]
    restricted = re.search(r"<details class=\"mt-4 rounded[^>]*>\s*<summary[^>]*>\s*Show \d+ "
                           r"restricted dates.*?</details>", h, flags=re.S)
    assert restricted and "data-lagna" not in restricted.group(0)


def test_the_disclosure_appears_exactly_once_after_the_last_table(client):
    ml = _ml()
    h = _page(client, "vivah", 180)
    assert h.count("data-lagna-legend") == 1 and len(_legends(h)) == 1
    pos = h.index("data-lagna-legend")
    assert pos > h.rindex("</table>", 0, pos)
    assert pos > h.index("What these labels mean"), "after the factor legend"
    assert pos < h.index("One verdict, one moment")
    t = _text(_legends(h)[0])
    assert ml.BENEFIC_DISCLOSURE in t
    for note in ml.LEGEND_NOTES:
        assert note in t
    assert ml.CAVEAT in t and ml.UNCHANGED in t


@pytest.mark.parametrize("event", ["griha_pravesh", "namkaran", "business", "vidyarambh"])
def test_other_events_render_no_block_and_no_disclosure(client, event):
    h = _page(client, event, 60)
    assert "data-lagna" not in h and "Lagna windows" not in h and "Rao's guideline" not in h


def test_the_day_ratings_on_the_page_are_the_ones_it_had_without_the_includes(client, monkeypatch):
    # Drop both fragments from the page and what is left must equal the page rendered with the two
    # globals returning None: the block is additive, and nothing else on the page moved.
    ml = _ml()
    with_blocks = _post(client, "vivah", 60)
    assert "data-lagna" in with_blocks, "premise"
    stripped = re.sub(r"\s*<details class=\"mt-1\" data-lagna>.*?</details>", "", with_blocks, flags=re.S)
    stripped = re.sub(r"\s*<details[^>]*data-lagna-legend[^>]*>.*?</details>", "", stripped, flags=re.S)
    monkeypatch.setattr(ml, "lagna_view", lambda *a, **k: None)
    monkeypatch.setattr(ml, "legend", lambda *a, **k: None)
    without = _post(client, "vivah", 60)
    assert "data-lagna" not in without

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s)

    assert norm(stripped) == norm(without)


# --- the none and failure branches, made deterministic ---------------------------------------


def test_a_row_with_no_window_shows_the_ruled_sentence_verbatim(client, monkeypatch):
    ml = _ml()
    monkeypatch.setattr(ml, "_windows_for", lambda *a, **k: ())
    h = _post(client, "vivah", 60)
    blocks = _blocks(h)
    assert blocks, "premise"
    for b in blocks:
        assert "<li>" not in b and "<ul" not in b, "no empty list"
        t = _text(b)
        assert ml.NONE_TEXT in t and ml.CAVEAT in t
    assert "does not make the day unsuitable; the day rating is unchanged" in _text(blocks[0])


def test_a_failed_computation_renders_neither_windows_nor_the_none_sentence(client, monkeypatch):
    ml = _ml()

    def boom(*a, **k):
        raise RuntimeError("ephemeris unavailable")

    monkeypatch.setattr(ml, "_windows_for", boom)
    h = _post(client, "vivah", 60)
    assert "data-lagna>" not in h, "a failure draws no block"
    assert ml.NONE_TEXT not in html.unescape(h)
    assert "No lagna window met" not in h


def test_the_legend_is_keyed_on_a_block_produced_not_on_row_eligibility(client, monkeypatch):
    """#1457: every row is eligible and every computation fails, so no block draws and the legend
    explaining the blocks must not draw either. Then one failing date among working ones: the
    blocks that do draw bring the legend, once, below them."""
    ml = _ml()
    real = ml._windows_for

    def boom(*a, **k):
        raise RuntimeError("ephemeris unavailable")

    monkeypatch.setattr(ml, "_windows_for", boom)
    h = _post(client, "vivah", 120)
    assert "data-lagna>" not in h and "data-lagna-legend" not in h
    assert ml.NONE_TEXT not in html.unescape(h)

    failing: list = []

    def first_date_only(day, *a, **k):
        if not failing:
            failing.append(day)
        if day == failing[0]:
            raise RuntimeError("ephemeris unavailable")
        return real(day, *a, **k)

    monkeypatch.setattr(ml, "_windows_for", first_date_only)
    h = _post(client, "vivah", 120)
    assert failing, "premise: the page asked for windows"
    assert _blocks(h), "premise: the other dates still produced blocks"
    assert h.count("data-lagna-legend") == 1
    pos = h.index("data-lagna-legend")
    assert pos > h.rindex("data-lagna>"), "below every block"
    assert pos > h.rindex("</table>", 0, pos)


def test_a_failing_page_logs_one_skipped_warning_per_date_not_two(client, monkeypatch, caplog):
    """#1464: the legend probes every row and the row partial renders every row, so a page whose
    windows all fail used to log each date's warning twice. The probe is quiet; the row owns it."""
    ml = _ml()

    def boom(*a, **k):
        raise RuntimeError("ephemeris unavailable")

    monkeypatch.setattr(ml, "_windows_for", boom)
    with caplog.at_level(logging.WARNING, logger=ml.log.name):
        h = _post(client, "vivah", 120)
    msgs = [r.getMessage() for r in caplog.records if r.getMessage().startswith("lagna windows skipped")]
    dates = [re.search(r"skipped for (\S+):", m).group(1) for m in msgs]
    assert msgs, "premise: the failing page logged its skipped dates"
    assert len(dates) == len(set(dates)), f"a date logged more than once: {sorted(dates)}"
    assert "data-lagna>" not in h and "data-lagna-legend" not in h
    assert ml.NONE_TEXT not in html.unescape(h)


def test_a_none_view_renders_nothing_through_the_partial():
    from astro_ai.routes.deps import templates

    out = templates.env.get_template("_muhurat_lagna.html").render(
        c=object(), selected_event="vivah", city=CITY,
        muhurat_lagna=lambda *a: None)
    assert out.strip() == ""


# --- the words on the page -------------------------------------------------------------------


def test_no_fragment_names_a_claim_word_a_book_or_a_table(client):
    h = _page(client, "vivah", 180)
    shown = _text(" ".join(_blocks(h) + _legends(h)))
    assert shown
    for banned in (r"\bauspicious\b", r"\bsafe\b", r"\brecommended\b", r"\bVivah muhurat\b"):
        assert not re.search(banned, shown, re.I), banned
    for token in ("Table", "Chapter", "§", "Rao §", "Ch.", ".md", "knowledge/", "Brihat", "Chintamani",
                  "BPHS", "Parashara", "Phaladeepika"):
        assert token not in shown, token


def test_the_rendered_page_fragments_and_partials_name_no_unheld_book(client):
    spec = importlib.util.spec_from_file_location(
        "verify_rule_citations", ROOT / "scripts" / "verify_rule_citations.py")
    vrc = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    spec.loader.exec_module(vrc)
    h = _page(client, "vivah", 180)
    texts = {"rendered fragments": " ".join(_blocks(h) + _legends(h))}
    for name in ("_muhurat_lagna.html", "_muhurat_lagna_legend.html"):
        texts[name] = (SRC / "templates" / name).read_text(encoding="utf-8")
    for where, text in texts.items():
        assert text.strip(), where
        for label, pattern in vrc._MUHURAT_UNHELD:
            assert not re.search(pattern, text, re.I), (where, label)
        assert not re.search(r"Table\s*79|Rao\s*§", text, re.I), where


# --- the templates themselves ----------------------------------------------------------------


@pytest.mark.parametrize("name", ["_muhurat_lagna.html", "_muhurat_lagna_legend.html"])
def test_the_partials_keep_the_same_promises_as_the_why_partials(name):
    src = (SRC / "templates" / name).read_text()
    body = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    assert "|safe" not in body and "| safe" not in body and "Markup" not in body
    assert "title=" not in body, "a sentence in a title attribute has no hover on a phone"
    assert "colors" not in body
    assert "font-bold" not in body
    assert not re.search(r"text-bhagya-(gold|saffron)\b", body), "gold/saffron are not text on cream"
    # Static text only: `auspicious_candidates` is a variable the finder already defines.
    static = re.sub(r"\{[{%].*?[}%]\}", "", body, flags=re.S)
    assert not re.search(r"auspicious|recommended|\bsafe\b", static, re.I), "no claim word in a template"
    assert "t(lang" not in body, "English only, like _muhurat_why.html"


def test_the_finder_includes_each_lagna_partial_once_after_its_why_partial():
    src = (SRC / "templates" / "muhurat_finder.html").read_text()
    row = re.findall(r'\{%-? include "_muhurat_lagna\.html" -?%\}', src)
    legend = re.findall(r'\{%-? include "_muhurat_lagna_legend\.html" -?%\}', src)
    assert len(row) == 1 and len(legend) == 1
    assert src.index("_muhurat_why.html") < src.index("_muhurat_lagna.html")
    assert src.index("_muhurat_why_legend.html") < src.index("_muhurat_lagna_legend.html")
    assert src.count('{% include "_muhurat_why.html" %}') == 1
    assert src.count('{% include "_muhurat_why_legend.html" %}') == 1
