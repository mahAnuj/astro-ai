"""#1017 R3, step 2: what the finder page shows of the factor registry.

Each auspicious row carries a collapsed "Why this date" list: what counted, and what was checked
and not excluded at local noon, every item labelled `site convention` or `traditions differ`
unless a held book states it. One legend below the table gives each factor's sentence once. An
avoid row, a caution row and the restricted-dates table carry no list. An Abujha row carries its
own disclosure AND the cleared list: since #1346 the exclusions run first, so a date that fails one
is an ordinary restricted row and one that passes has a true cleared list.

The registry itself and its parity with the scorer are pinned in test_muhurat_factor_registry.py and
test_muhurat_factor_parity.py; this file reads the RENDERED page. No network (geocoding is stubbed
to New Delhi) and no LLM. Mutation rows: scripts/mutations/2026_11_21_1017_r3_factor_registry.py.
"""
from __future__ import annotations

import dataclasses
import html
import re
from datetime import date
from pathlib import Path

import pytest

DELHI = (28.61, 77.21, "Asia/Kolkata")
TODAY = date(2026, 11, 21)
CITY = "Delhi, India"
SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
ABUJHA_OPENING = "Listed as an Abujha date, a regional almanac custom this finder includes"
# A real date the rule table computes (asserted below, never assumed) on which the Abujha lift
# applies: it clears every business exclusion and goes acceptable -> excellent. It is outside the
# page's usual 2026 window, which the route allows (no clamp on start_date).
ABUJHA_PASS_DAY = date(2028, 4, 27)
SCORED = "What counted for this date"
CLEARED = "Checked and not excluded at local noon"
LEGEND = "What these labels mean"
_cache: dict[tuple, str] = {}


@pytest.fixture(autouse=True)
def _pinned(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    monkeypatch.setattr(route, "reading_today", lambda: TODAY)


def _page(client, event: str, days: int, start: date = TODAY) -> str:
    key = (event, days, start)
    if key not in _cache:
        r = client.post("/muhurat", data={"event_type": event, "city": CITY,
                                          "start_date": start.isoformat(), "days": str(days)})
        assert r.status_code == 200
        _cache[key] = r.text
    return _cache[key]


def _text(h: str) -> str:
    return re.sub(r" ([.,)])", r"\1", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))).strip()


def _tables(h: str) -> list[str]:
    return re.findall(r"<table.*?</table>", h, flags=re.S)


def _rows(table: str) -> list[str]:
    return re.findall(r"<tr class=\"border-b.*?</tr>", table, flags=re.S)


def _whys(h: str) -> list[str]:
    return re.findall(r"<details class=\"mt-1\">\s*<summary[^>]*>Why this date.*?</details>", h,
                      flags=re.S)


def _legend(h: str) -> str:
    return re.search(r"<details[^>]*>\s*<summary[^>]*>\s*" + LEGEND + r".*?</details>", h,
                     flags=re.S).group(0)


def _first(event: str, **overrides):
    """A real auspicious candidate for `event`, optionally changed (a synthetic row)."""
    from astro_ai import muhurat

    rows = muhurat.find_candidates(event, CITY, TODAY, 60)
    c = next(c for c in rows if c.rating in muhurat.AUSPICIOUS_RATINGS
             and "abujha_muhurat" not in c.flags)
    return dataclasses.replace(c, **overrides)


def _render_why(c, event: str) -> str:
    from astro_ai.routes.deps import templates

    return templates.env.get_template("_muhurat_why.html").render(c=c, selected_event=event)


# --- the real page -------------------------------------------------------------------------


def test_every_auspicious_row_has_why_this_date_with_both_headings(client):
    h = _page(client, "vivah", 180)
    auspicious = _rows(_tables(h)[0])
    assert len(auspicious) >= 10, "premise: a real vivah search has many auspicious rows"
    assert len(_whys(h)) == len(auspicious)
    for row in auspicious:
        why = _whys(row)
        assert len(why) == 1, "one disclosure per row"
        t = _text(why[0])
        assert t.startswith("Why this date")
        assert SCORED in t
        assert CLEARED in t
        assert t.index(SCORED) < t.index(CLEARED)


def test_the_why_list_sits_in_the_notes_cell_after_the_reason(client):
    h = _page(client, "griha_pravesh", 60)
    row = _rows(_tables(h)[0])[0]
    notes = re.search(r'<td data-label="Notes" data-span[^>]*>(.*?)</td>\s*</tr>', row, flags=re.S)
    assert notes and "Why this date" in notes.group(1)
    assert notes.group(1).split("<details")[0].strip(), "the reason text comes first"


def test_a_real_row_lists_what_counted_and_what_was_checked(client):
    h = _page(client, "griha_pravesh", 60)
    t = _text(_whys(h)[0])
    assert re.search(r"Good (tithi|star|weekday):", t), "a scored item names its value"
    assert "Not a Tuesday" in t and "Not in Chaturmas" in t, "cleared items name the checks run"


def test_the_restricted_dates_table_has_no_list(client):
    h = _page(client, "vivah", 180)
    restricted = re.search(r"<details class=\"mt-4 rounded[^>]*>\s*<summary[^>]*>\s*Show \d+ "
                           r"restricted dates.*?</details>", h, flags=re.S)
    assert restricted, "premise: the search has restricted dates"
    assert "Why this date" not in restricted.group(0)
    assert "<ul" not in restricted.group(0)


def test_caution_rows_have_no_list(client):
    h = _page(client, "vivah", 180)
    tables = _tables(h)
    assert len(tables) >= 2 and "Use with caution" in h, "premise: this search has caution rows"
    caution_rows = _rows(tables[1])
    assert caution_rows
    assert "Why this date" not in tables[1] and "<ul" not in tables[1]
    # And the same through the partial, for a candidate rated caution.
    assert _render_why(_first("vivah", rating="caution"), "vivah").strip() == ""
    assert _render_why(_first("vivah", rating="avoid"), "vivah").strip() == ""


def _abujha_pass_row(client) -> str:
    from astro_ai import muhurat

    assert ABUJHA_PASS_DAY in muhurat._abujha_days(2028), "premise: the rule table names this date"
    h = _page(client, "business", 1, start=ABUJHA_PASS_DAY)
    rows = _rows(_tables(h)[0])
    assert len(rows) == 1 and "Apr 27, 2028" in rows[0], "premise: the one row is the Abujha date"
    return rows[0]


def test_an_abujha_row_shows_the_disclosure_and_the_cleared_list(client):
    row = _abujha_pass_row(client)
    why = _text(_whys(row)[0])
    assert ABUJHA_OPENING in why
    assert "The finder's usual exclusion checks were run for this date and none excluded it" in why
    assert "were not run" not in why and "universally auspicious" not in why
    assert SCORED in why and CLEARED in why and why.index(SCORED) < why.index(CLEARED)
    # Abujha is the first scored item, then the soft points that really counted
    assert why.index("Abujha date") < why.index("Good tithi")
    assert "site convention" in why
    # the cleared list names the checks business runs, so it is the scorer's list, not a blank
    assert "Not a Tuesday" in why and "Budh not combust" in why and "Not in Adhik Maas" in why


def test_an_abujha_row_with_a_real_booster_shows_it_after_the_abujha_item():
    from astro_ai import muhurat

    [ab] = muhurat.find_candidates("business", CITY, ABUJHA_PASS_DAY, 1)
    assert "abujha_muhurat" in ab.flags, "premise: the date passes and carries the flag"
    c = dataclasses.replace(ab, boosters=["Amrit Siddhi (Wed + Hasta)", "Ravi Yoga"])
    t = _text(_render_why(c, "business"))
    assert ABUJHA_OPENING in t and CLEARED in t
    assert t.index("Abujha date") < t.index("Amrit Siddhi present") < t.index("Ravi Yoga present")


def test_an_abujha_date_that_fails_an_exclusion_is_an_ordinary_restricted_row(client):
    """2026-11-21 (Tulsi Vivah, Moon in Revati = Panchak) used to be rated excellent (#1346). It is
    now an `avoid` row in the restricted table with the Panchak reason plus the finder's sentence
    that it does not waive the exclusion, and it has no 'Why this date' block."""
    h = _page(client, "vivah", 180)
    restricted = re.search(r"<details class=\"mt-4 rounded[^>]*>\s*<summary[^>]*>\s*Show \d+ "
                           r"restricted dates.*?</details>", h, flags=re.S).group(0)
    row = next(r for r in _rows(restricted) if "Nov 21, 2026" in r)
    t = _text(row)
    assert "Panchak day (Revati) — inauspicious." in t
    assert ("Tulsi Vivah is listed as an Abujha date, a regional almanac custom; this finder "
            "does not waive this exclusion for it.") in t
    assert "Why this date" not in row and ABUJHA_OPENING not in t
    assert not any("Nov 21, 2026" in r for r in _rows(_tables(h)[0])), "not in the auspicious table"


def test_a_site_convention_item_carries_the_visible_words_site_convention():
    c = _first("vivah", boosters=["Sarvartha Siddhi (Mon + Mrigashira)"])
    out = _render_why(c, "vivah")
    assert re.search(r"Sarvartha Siddhi present\s*<span[^>]*>site convention</span>", out)
    # Visible text, not a hover: no sentence in a title attribute.
    assert "title=" not in out


def test_a_contested_item_and_a_deduction_are_tagged_in_their_own_words():
    from astro_ai import muhurat
    from astro_ai.muhurat_factors import explain

    rows = muhurat.find_candidates("vidyarambh", CITY, TODAY, 180)
    c = next(c for c in rows if any(i.against for i in explain(c, "vidyarambh").scored)
             and c.rating in muhurat.AUSPICIOUS_RATINGS)
    out = _render_why(c, "vidyarambh")
    assert re.search(r"<span[^>]*bg-rose-100 text-rose-800[^>]*>counted against</span>", out)
    g = _render_why(_first("griha_pravesh"), "griha_pravesh")
    assert re.search(r"Guru not combust\s*<span[^>]*bg-amber-100 text-amber-800[^>]*>"
                     r"traditions differ</span>", g)


def test_an_empty_scored_list_says_so_instead_of_an_empty_ul():
    from astro_ai.muhurat import EVENT_RULES

    rules = EVENT_RULES["vivah"]
    day = next(d for d in ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                           "Saturday") if d not in rules["good_days"] | rules["avoid_days"])
    c = _first("vivah", tithi="Pratipada", nakshatra="Ardra", weekday=day, boosters=[])
    assert "Pratipada" not in rules["good_tithis"] and "Ardra" not in rules["good_nakshatras"]
    out = _render_why(c, "vivah")
    assert "No tithi, star or weekday point scored for this date" in _text(out)
    for ul in re.findall(r"<ul.*?</ul>", out, flags=re.S):
        assert "<li>" in ul


def test_the_legend_appears_exactly_once_and_after_the_last_table(client):
    for event in ("vivah", "griha_pravesh"):
        h = _page(client, event, 60 if event != "vivah" else 180)
        assert h.count(LEGEND) == 1
        assert h.index(LEGEND) > h.rindex("</table>", 0, h.index(LEGEND))
        assert h.index(LEGEND) < h.index("One verdict, one moment")
        assert "Widely followed conventions this finder applies" in h
        assert "Combustion (asta):" in h


def test_the_legend_carries_the_noon_sentence_and_the_scoring_weights_once(client):
    lg = _text(_legend(_page(client, "vivah", 180)))
    assert lg.count("Checked at local noon on this date") == 1
    assert lg.count("How the grade is counted") == 1
    assert "5 or more is excellent, 4 good, 3 acceptable" in lg


def test_each_legend_entry_is_listed_once_with_a_status_tag(client):
    leg = _legend(_page(client, "vivah", 180))
    labels = re.findall(r'<span class="font-semibold text-bhagya-ink-soft">(.*?)</span>', leg)
    assert len(labels) > 10 and len(labels) == len(set(labels))
    items = re.findall(r"<li>.*?</li>", leg, flags=re.S)
    assert len(items) == len(labels)
    for li in items:
        assert re.search(r">(sourced|site convention|traditions differ)</span>", li)
    assert "title=" not in leg


def test_no_legend_and_no_list_when_the_window_has_no_auspicious_date(client):
    h = _page(client, "griha_pravesh", 20, start=date(2026, 12, 20))
    assert "No auspicious dates found in this window" in h, "premise: a Kharmas window"
    assert LEGEND not in h and "Why this date" not in h


@pytest.mark.parametrize("event,days,present,absent", [
    ("vivah", 180, ("Guru not combust", "Shukra not combust"), ("Budh not combust",)),
    ("griha_pravesh", 60, ("Guru not combust",), ("Shukra not combust", "Budh not combust")),
    ("vidyarambh", 60, ("Guru not combust",), ("Shukra not combust", "Budh not combust")),
    ("business", 60, ("Budh not combust",), ("Guru not combust", "Shukra not combust")),
    ("namkaran", 60, (), ("Guru not combust", "Shukra not combust", "Budh not combust")),
])
def test_the_legend_labels_the_combustions_the_searched_event_checks(client, event, days,
                                                                     present, absent):
    leg = _text(_legend(_page(client, event, days)))
    for label in present:
        assert label in leg
        entry = leg.split(label, 1)[1]
        # The status tag follows the label, and the sentence names whose rule it is.
        assert re.match(r" (site convention|traditions differ)", entry), (event, label)
        assert "convention" in entry[:300] or "differ" in entry[:300] or "tradition" in entry[:300]
    for label in absent:
        assert label not in leg


def test_guru_combustion_for_griha_pravesh_and_vidyarambh_is_the_finders_own_choice(client):
    for event in ("griha_pravesh", "vidyarambh"):
        leg = _text(_legend(_page(client, event, 60)))
        entry = leg.split("Guru not combust", 1)[1]
        assert "this finder's own convention" in entry[:400], event


def test_the_vidyarambh_legend_carries_the_second_ruling_wording(client):
    leg = _text(_legend(_page(client, "vidyarambh", 180)))
    assert "not both" not in leg
    assert "the Muhurtha tradition rejects only Tuesday, Saturday and Sunday" in leg
    assert "Vedic table's list for Vidyarambh (Starting Education)" in leg


def test_no_source_reference_reaches_the_rendered_lists_or_legend(client):
    for event, days in (("vivah", 180), ("griha_pravesh", 60), ("vidyarambh", 180),
                        ("business", 60), ("namkaran", 60)):
        h = _page(client, event, days)
        shown = _text(" ".join(_whys(h)) + _legend(h))
        for bad in ("§", "Ch.", ".md", "knowledge/", "Chintamani", "BPHS", "Phaladeepika"):
            assert bad not in shown, (event, bad)


def test_the_polar_and_window_strings_are_still_there(client):
    h = _page(client, "vivah", 180)
    assert 'data-label="Windows"' in h
    assert "Abhijit </div>" not in h and "Rahu Kaal </div>" not in h
    assert h.count('data-label="Notes"') == len(_rows(_tables(h)[0])) + len(_rows(_tables(h)[1]))


# --- the templates themselves --------------------------------------------------------------


@pytest.mark.parametrize("name", ["_muhurat_why.html", "_muhurat_why_legend.html"])
def test_the_partials_keep_their_three_promises(name):
    src = (SRC / "templates" / name).read_text()
    body = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    assert "|safe" not in body and "| safe" not in body and "Markup" not in body
    assert "title=" not in body, "a sentence in a title attribute has no hover on a phone"
    assert "colors" not in body, "the finder's `colors` moves in #1342; the partial owns its pairs"
    assert "font-bold" not in body
    assert not re.search(r"text-bhagya-(gold|saffron)\b", body), "gold/saffron are not text on cream"


def test_the_finder_includes_each_partial_once_and_keeps_its_anchors():
    src = (SRC / "templates" / "muhurat_finder.html").read_text()
    assert src.count('{% include "_muhurat_why.html" %}') == 1
    assert src.count('{% include "_muhurat_why_legend.html" %}') == 1
    assert src.index("_muhurat_why.html") < src.index("_muhurat_why_legend.html")
    assert 'data-label="Windows"' in src
