"""The PRs-shipped bars and Key metrics rows on /admin/ops Overview, template half
(#1133 slice 2b, step 2).

`tests/test_ops_trends.py` covers the arithmetic in `ops_trends.build`. These render
the real page from a fixture whose answers are written out below BY HAND and
recomputed a second, different way (`_bars_again`), then read what a visitor gets:
seven bars that add up to the PRs-merged card, a drill-down whose rows agree with the
bar, four metric rows each with its own window, no number where the honest answer is
"unavailable", and neither panel on any other tab.

What these cannot see, and nothing else here does either: the colours, the spacing and
the hover tooltip are browser-only. The CSS and script tests pin their size and shape;
the look at 375px and 1280px, light and dark, and the click on a bar, were exercised in
headless Chromium by hand and are not in a gate.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import ops_data, ops_tabs, ops_trends

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()
IST = timezone(timedelta(hours=5, minutes=30))
OTHER_TABS = [k for k, _ in ops_tabs.TABS if k != "overview"]


def _today() -> datetime:
    return datetime.now(IST).replace(hour=12, minute=0, second=0, microsecond=0)


def _iso(offset: int) -> str:
    return (_today() + timedelta(days=offset)).strftime("%Y-%m-%d")


def _row(offset: int, outcome: str, *, kind: str = "ranked", pr: int | None = None) -> dict:
    when = _today() + timedelta(days=offset)
    return {"run": 7000 + abs(offset) * 10 + (pr or 0) % 10, "workflow": "agent-work",
            "date": when.strftime("%Y-%m-%d"),
            "started": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": "schedule", "conclusion": "success", "minutes": 5.0, "issue": None,
            "pr": pr, "outcome": outcome, "attribution": "receipt", "kind": kind,
            "tokens_input": 1, "tokens_output": 2, "tokens_cache_read": 3,
            "tokens_cache_write": 4, "cost_list_usd": 1.0}


# Current window = today-7 .. today-1. Offset -4 has NO row at all: "no runs".
ROWS = [
    _row(-7, "shipped", pr=201),
    _row(-6, "shipped", pr=201),                      # the same PR again: counts on -7 only
    _row(-5, "shipped", pr=202), _row(-5, "shipped", pr=205),
    _row(-3, "failed"),                               # ran, shipped nothing: a real 0
    _row(-2, "judged", kind="qa-round", pr=201),
    _row(-1, "shipped", pr=203),
    _row(0, "shipped", pr=204),                       # today: partial, in neither window
    _row(-12, "shipped", pr=190),                     # previous window
]
RPI = {"201": ["PASS"], "202": ["PASS"], "205": ["FAIL"], "203": ["PASS"], "190": ["PASS"]}

# Written out by hand from the rows above, oldest day first:
#   -7: 1 (201)   -6: 0 (201 already counted)   -5: 2 (202, 205)   -4: no runs
#   -3: 0         -2: 0 (a judged row is not a ship)   -1: 1 (203)         total 4
HAND = [("201", 1), ("", 0), ("202,205", 2), (None, None), ("", 0), ("", 0), ("203", 1)]
HAND_TOTAL = 4

# GSC trails the present by 3 days: its window is today-9 .. today-3, 14 rows from today-16.
GSC_END = -3
SELF_CLICKS = [10, 20, 30, 40, 50, 60, 70]            # the current 7, oldest first
ISSUES_CLOSED = [3, 4, 5, 6, 7, 8, 9]                 # the current 7 UTC days, oldest first


def _gsc(rows_missing: set[int] = frozenset(), days: int = 14) -> list[dict]:
    out = []
    for i in range(days):
        off = GSC_END - (days - 1 - i)
        if off in rows_missing:
            continue
        clicks = SELF_CLICKS[i - (days - 7)] if i >= days - 7 else 5
        out.append({"date": _iso(off), "clicks": clicks, "impressions": 100})
    return out


def _issues_doc() -> dict:
    """15 UTC days, newest = today (UTC), which is the collector's partial day."""
    newest = datetime.now(timezone.utc).date()
    days = []
    for i in range(15):
        d = newest - timedelta(days=14 - i)
        closed = ISSUES_CLOSED[i - 7] if 7 <= i <= 13 else 2 if i < 7 else 99
        days.append({"date": d.isoformat(), "opened": 1, "closed": closed, "net": 1 - closed,
                     "open_end": 50, "closed_by": {"close-on-evidence": 1}})
    return {"generated_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trend": {"generated_at": (datetime.now(timezone.utc) - timedelta(hours=5))
                      .strftime("%Y-%m-%dT%H:%M:%SZ"), "days": days}}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _serve(monkeypatch, *, rows=None, gsc=True, issues=True, gsc_rows=None):
    stamp = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    files = {"loop.json": {"generated_at": stamp, "rows": ROWS if rows is None else rows},
             "agents.json": {"generated_at": stamp, "loops": [],
                             "agents": {"qa": {"rounds_per_issue": RPI}}}}
    if gsc:
        files["gsc-daily.json"] = {"rows": _gsc() if gsc_rows is None else gsc_rows}
    if issues:
        files["issues.json"] = _issues_doc()
    monkeypatch.setattr(ops_data, "_fetch", lambda name: files.get(name))


def _page(q: str = "?tab=overview"):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _body(html: str) -> str:
    return re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S)


def _blob(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="ops-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def _section(html: str, sid: str) -> str:
    i = html.index(f'id="{sid}"')
    return html[html.rindex("<section", 0, i): html.index("</section>", i)]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


def _bars(html: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<g class="dcol" data-drill="kpi-prs-day" data-day="([^"]+)" data-prs="([^"]*)"'
                         r'\s+data-tip="([^"]*)" tabindex="0" role="button">(.*?)</g>', html, re.S):
        day, prs, tip, inner = m.groups()
        label = re.search(r'<text class="ax bv"[^>]*>([^<]*)</text>', inner)
        out.append({"day": day, "prs": prs, "tip": tip, "inner": inner,
                    "label": label.group(1) if label else None,
                    "has_bar": 'class="pbar"' in inner, "title": re.search(r"<title>([^<]*)</title>", inner).group(1)})
    return out


def _rows(html: str) -> dict[str, dict]:
    """Each Key metrics row as {key: {class, text, num, svg, inner}}."""
    out = {}
    sec = _section(html, "key-metrics")
    for m in re.finditer(r'<li class="km st-(\w+)" id="km-(\w+)">(.*?)</li>', sec, re.S):
        state, key, inner = m.groups()
        num = re.search(r'<span class="num[^"]*">([^<]*)</span>', inner).group(1)
        out[key] = {"state": state, "inner": inner, "text": _text(inner), "num": num,
                    "svg": re.search(r"<svg.*?</svg>", inner, re.S)}
    return out


def _bars_again(rows: list[dict], today: str) -> dict[str, int | None]:
    """The bars derived a second way: first day each PR shipped, by set algebra."""
    t = date.fromisoformat(today)
    cur = [(t - timedelta(days=i)).isoformat() for i in range(7, 0, -1)]
    inside = [r for r in rows if r["date"] in cur]
    first: dict[int, str] = {}
    for r in sorted(inside, key=lambda r: r["date"]):
        if r["outcome"] == "shipped" and r["pr"] and r["pr"] not in first:
            first[r["pr"]] = r["date"]
    ran = {r["date"] for r in inside}
    per = Counter(first.values())
    return {d: (per.get(d, 0) if d in ran else None) for d in cur}


def _card_prs(html: str) -> str:
    m = re.search(r'class="tile kpi k-prs st-\w+".*?<span class="num[^"]*">([^<]*)</span>', html, re.S)
    return m.group(1)


# --- the bars ----------------------------------------------------------------------

def test_the_hand_table_and_the_second_derivation_agree():
    """Guards the guard."""
    again = _bars_again(ROWS, _iso(0))
    assert [again[_iso(o)] for o in range(-7, 0)] == [v for _, v in HAND]
    assert sum(v or 0 for v in again.values()) == HAND_TOTAL


def test_seven_bars_in_day_order_matching_the_hand_table_and_the_recompute(monkeypatch):
    _serve(monkeypatch)
    bars = _bars(_page().text)
    assert [b["day"] for b in bars] == [_iso(o) for o in range(-7, 0)]
    again = _bars_again(ROWS, _iso(0))
    for b, (prs, val) in zip(bars, HAND):
        assert b["label"] == (str(val) if val is not None else None)
        if prs is not None:
            assert b["prs"] == prs
        assert again[b["day"]] == val


def test_the_seven_bars_add_up_to_the_prs_merged_card(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    assert sum(int(b["label"]) for b in _bars(h) if b["label"]) == int(_card_prs(h)) == HAND_TOTAL


def test_the_sums_agree_on_the_real_committed_data_too():
    # No _serve: whatever loop.json is committed. The page, not the fixture, must add up.
    h = _page().text
    card = _card_prs(h)
    if card.isdigit():
        assert sum(int(b["label"]) for b in _bars(h) if b["label"]) == int(card)


def test_a_day_with_no_loop_rows_says_no_runs_not_zero_and_has_no_bar(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    b = {x["day"]: x for x in _bars(h)}
    gap, zero = b[_iso(-4)], b[_iso(-3)]
    assert gap["label"] is None and not gap["has_bar"]
    assert re.search(r">no</text>\s*<text[^>]*>runs</text>|>no</text><text[^>]*>runs</text>", gap["inner"])
    assert "no runs recorded" in gap["tip"] and gap["title"] == gap["tip"]
    assert zero["label"] == "0" and not zero["has_bar"] and "0 PRs shipped" in zero["tip"]
    assert "no runs" in _text(_section(h, "prs-shipped").split("<tbody>")[1].split("</tbody>")[0])


def test_each_bar_is_a_keyboard_button_with_a_hit_rect_and_a_title(monkeypatch):
    _serve(monkeypatch)
    for b in _bars(_page().text):
        assert 'class="hit"' in b["inner"] and b["title"]
        assert re.fullmatch(r"[\d,]*", b["prs"])


def test_the_tooltip_lives_in_the_same_wrap_so_the_existing_hover_handler_works(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    assert h.count('id="dtip"') == 1
    sec = _section(h, "prs-shipped")
    wrap = re.search(r'<div class="dchart-wrap[^"]*">(.*?)</div>\s*<div class="vh">', sec, re.S).group(1)
    assert '<div class="dtip" id="dtip" hidden></div>' in wrap and "<svg" in wrap


def test_the_bar_drill_rows_agree_with_the_bar(monkeypatch):
    """The script filters kpiPrs() by data-prs; apply the same predicate to the blob."""
    _serve(monkeypatch)
    h = _page().text
    rows = _blob(h)["kpi_rows"]
    seen, uniq = set(), []
    for r in rows:                                    # kpiPrs()
        if r["outcome"] == "shipped" and r["pr"] and r["pr"] not in seen:
            seen.add(r["pr"])
            uniq.append(r)
    for b in _bars(h):
        want = [p for p in b["prs"].split(",") if p]
        got = [r for r in uniq if str(r["pr"]) in want]
        assert len(got) == len(want) == (int(b["label"]) if b["label"] else 0), b["day"]
    assert {str(r["pr"]) for r in uniq} == {p for b in _bars(h) for p in b["prs"].split(",") if p}


# --- accessible names and the tables beneath the charts --------------------------------

def test_every_svg_has_role_img_and_an_aria_label_and_the_labels_list_the_values(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    svgs = re.findall(r"<svg\b[^>]*>", _section(h, "prs-shipped") + _section(h, "key-metrics"))
    assert len(svgs) == 3                              # the bars, organic, issues
    for tag in svgs:
        assert 'role="img"' in tag and re.search(r'aria-label="[^"]{20,}"', tag), tag
    bars_label = re.search(r'<svg class="dchart prs"[^>]*aria-label="([^"]*)"', h).group(1)
    assert "PRs" in bars_label and "IST day" in bars_label
    assert re.search(r"\d{4}-\d{2}-\d{2} → \d{2}-\d{2}", bars_label)
    for o, (_, val) in zip(range(-7, 0), HAND):
        assert f"{_iso(o)} {val if val is not None else 'no runs'}" in bars_label, o
    rows = _rows(h)
    for key, vals in (("organic", SELF_CLICKS), ("issues", ISSUES_CLOSED)):
        label = re.search(r'aria-label="([^"]*)"', rows[key]["svg"].group(0)).group(1)
        assert [int(v) for v in re.findall(r"\d{4}-\d{2}-\d{2} (\d+)", label)] == vals, key


def test_the_hidden_tables_carry_the_plotted_values(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    sec = _section(h, "prs-shipped")
    tbl = re.search(r'<div class="vh"><table>(.*?)</table>', sec, re.S).group(1)
    cells = re.findall(r'<tr><th scope="row">(\w+) (\S+)</th><td>([^<]*)</td><td>(\d+)</td><td>([^<]*)</td></tr>', tbl)
    assert [(c[1], c[2]) for c in cells] == [(_iso(o), str(v) if v is not None else "no runs")
                                            for o, (_, v) in zip(range(-7, 0), HAND)]
    rows = _rows(h)
    for key, vals in (("organic", SELF_CLICKS), ("issues", ISSUES_CLOSED)):
        t = re.search(r'<div class="vh"><table>(.*?)</table>', rows[key]["inner"], re.S).group(1)
        assert [int(v) for v in re.findall(r"<td>(\d+)</td>", t)] == vals, key
        titles = re.findall(r"<circle[^>]*><title>[^<]*: (\d+) (?:clicks|closed)</title></circle>", rows[key]["inner"])
        assert [int(v) for v in titles] == vals, key


def test_a_sparkline_has_seven_points_inside_its_box_and_the_line_ends_on_the_last(monkeypatch):
    _serve(monkeypatch)
    for key, r in _rows(_page().text).items():
        if key not in ("organic", "issues"):
            continue
        svg = r["svg"].group(0)
        pts = [(float(x), float(y)) for x, y in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)"', svg)]
        assert len(pts) == 7 and all(0 <= x <= 120 and 0 <= y <= 32 for x, y in pts), key
        line = re.search(r'<polyline class="sl" points="([^"]+)"', svg).group(1).split()
        assert len(line) == 7 and tuple(map(float, line[-1].split(","))) == pts[-1], key


# --- the rows ------------------------------------------------------------------------

def test_four_rows_in_the_owners_order_between_results_and_goals(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    assert list(_rows(h)) == ["organic", "issues", "content", "cycle_time"]
    heads = [h.index(x) for x in ('id="kpi-h"', 'id="prs-h"', 'id="km-h"', 'id="goals"')]
    assert heads == sorted(heads)
    assert [_text(m) for m in re.findall(r"<h2 id=\"(?:prs|km)-h\">(.*?)</h2>", h, re.S)][0].startswith("PRs shipped")


def test_every_row_prints_its_value_its_n_its_delta_its_window_and_its_source(monkeypatch):
    _serve(monkeypatch)
    rows = _rows(_page().text)
    for key, n in (("organic", sum(SELF_CLICKS)), ("issues", sum(ISSUES_CLOSED))):
        r = rows[key]
        assert r["state"] == "ok" and r["num"] == str(n), key
        assert f"n={n}" in r["text"] and "source: measurements/" in r["text"]
        assert re.search(r"[▲▼▬] (up|down|flat)\b", r["text"]), key
        assert re.search(r"\d{4}-\d{2}-\d{2} → \d{2}-\d{2}", r["text"])
        # Both rose against the week before, and for both a rise is good: colour is the second signal.
        assert 'class="dl good"' in r["inner"] and "▲ up" in r["text"], key
    assert "Open Traffic" in rows["organic"]["text"] and 'href="?tab=analytics&amp;window=7"' in rows["organic"]["inner"]
    assert "Open Issue flow" in rows["issues"]["text"] and 'href="?tab=backlog&amp;window=7"' in rows["issues"]["inner"]


def test_the_organic_row_has_its_own_window_and_says_no_agent_earned_it(monkeypatch):
    _serve(monkeypatch)
    rows = _rows(_page().text)
    o, i = rows["organic"], rows["issues"]
    want = f"{_iso(GSC_END - 6)} → {_iso(GSC_END)[5:]}"
    assert want in o["text"], (want, o["text"])
    assert "not attributed to any agent" in o["text"]
    bars_window = f"{_iso(-7)} → {_iso(-1)[5:]}"
    assert bars_window not in o["text"]                # not the Results window
    assert want in o["text"].split("vs")[0]            # the window line, before the delta's own
    assert "Search Console days" in o["text"]


def test_the_issues_row_is_labelled_utc_days_ends_before_the_partial_day_and_names_the_fixer(monkeypatch):
    _serve(monkeypatch)
    i = _rows(_page().text)["issues"]
    newest = datetime.now(timezone.utc).date()
    want = f"{(newest - timedelta(days=7)).isoformat()} → {(newest - timedelta(days=1)).isoformat()[5:]}"
    assert f"UTC days · {want}" in i["text"], i["text"]
    assert f"{sum(ISSUES_CLOSED)} closed in 7 days" in i["text"]
    assert "7 by close-on-evidence" in i["text"]       # one fix-path closure on each of the 7 days
    assert i["num"] == str(sum(ISSUES_CLOSED))         # the partial day (99 closed) is not in it


@pytest.mark.parametrize("key,label", [("content", "Content published"), ("cycle_time", "Average cycle time")])
def test_the_two_uncollected_rows_print_the_definition_and_no_number_and_no_sparkline(monkeypatch, key, label):
    _serve(monkeypatch)
    r = _rows(_page().text)[key]
    assert r["state"] == "unavailable" and label in r["text"] and r["svg"] is None
    assert not re.search(r"\d", r["num"])
    assert "unavailable: not collected" in r["text"]
    # nothing but the name of the slice that adds it may carry a digit
    assert not re.search(r"\d", r["text"].replace("slice 2e", "")), r["text"]
    assert 'class="dl' not in r["inner"] and "was " not in r["text"]


def test_with_no_gsc_or_issue_file_those_rows_are_unavailable_and_print_no_digit(monkeypatch):
    _serve(monkeypatch, gsc=False, issues=False)
    r = _page()
    assert r.status_code == 200
    rows = _rows(r.text)
    for key in ("organic", "issues"):
        assert rows[key]["state"] == "unavailable" and rows[key]["svg"] is None, key
        # The definition ("summed over 7 days") is the row's own wording, not a measured figure.
        measured = _text(re.sub(r'<span class="df">.*?</span>', "", rows[key]["inner"], flags=re.S))
        assert not re.search(r"\d", measured), (key, measured)
        assert "unavailable" in rows[key]["num"]
    assert rows["organic"]["num"] != "0" and "clicks" not in rows["organic"]["num"]


def test_a_missing_day_in_the_window_blanks_the_value_and_the_chart_never_a_sum_over_the_hole(monkeypatch):
    _serve(monkeypatch, gsc_rows=_gsc(rows_missing={-5}))
    o = _rows(_page().text)["organic"]
    assert o["state"] == "unavailable" and not re.search(r"\d", o["num"]) and o["svg"] is None
    assert "no data for 1 of 7 days" in o["text"] and f"first gap {_iso(-5)}" in o["text"]
    assert str(sum(SELF_CLICKS)) not in o["text"]


def test_a_refused_delta_prints_no_was_value(monkeypatch):
    """#1490 on the page: only 10 days of GSC, so the previous window has a hole."""
    _serve(monkeypatch, gsc_rows=_gsc(days=10))
    o = _rows(_page().text)["organic"]
    assert o["state"] == "ok" and o["num"] == str(sum(SELF_CLICKS))
    assert "unavailable: no data for" in o["text"] and "was " not in o["text"]
    assert re.search(r'class="dl[^"]*">▲|class="dl[^"]*">▼', o["inner"]) is None


def test_a_failed_build_renders_unavailable_everywhere_and_says_so(monkeypatch):
    _serve(monkeypatch)
    monkeypatch.setattr(ops_trends, "build",
                        lambda *a: ops_trends._unavailable("unavailable: boom", error=True))
    r = _page()
    assert r.status_code == 200
    h = r.text
    bars = _section(h, "prs-shipped")
    assert "unavailable: boom" in bars and "dcol" not in bars
    assert 'role="status"' in bars and "The bars are unavailable, not zero" in bars
    rows = _rows(h)
    assert len(rows) == 4 and all(x["state"] == "unavailable" and x["svg"] is None for x in rows.values())
    assert 'role="status"' in _section(h, "key-metrics")
    assert _card_prs(h)                                  # Results is untouched


def test_with_no_trends_at_all_the_page_still_renders_results(monkeypatch):
    _serve(monkeypatch)
    from astro_ai.routes import admin
    monkeypatch.setattr(admin.ops_trends, "build", lambda *a: None)
    h = _page().text
    assert 'id="prs-shipped"' not in h and 'id="key-metrics"' not in h and 'class="panel kpis"' in h


# --- one tab only -------------------------------------------------------------------

@pytest.mark.parametrize("tab", OTHER_TABS)
def test_no_other_tab_has_either_panel(tab):
    r = _page(f"?tab={tab}")
    assert r.status_code == 200
    body = _body(r.text)
    for marker in ('id="prs-shipped"', 'id="key-metrics"', 'data-drill="kpi-prs-day"',
                   'class="dchart prs"', 'class="spark"', 'class="km '):
        assert marker not in body, (tab, marker)


def test_overview_has_both_panels_once(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    assert h.count('id="prs-shipped"') == 1 and h.count('id="key-metrics"') == 1
    assert 'data-drill="kpi-prs-day"' in _body(h)       # makes the drill check in test_ops_tab_shell bite
    assert "kpi_rows" in _blob(h)


# --- no arithmetic in the template ----------------------------------------------------

def _trends_block() -> str:
    i = TPL.index("{% if trends %}")
    j = TPL.index("{# ── Goals and agent decisions", i)
    return TPL[i:j]


def test_the_new_block_has_no_arithmetic_and_no_literal_number_in_an_expression():
    block = _trends_block()
    exprs = re.findall(r"\{\{(.*?)\}\}|\{%(.*?)%\}", block, re.S)
    assert len(exprs) > 60
    for a, b in exprs:
        e = re.sub(r"'[^']*'|\"[^\"]*\"", "''", (a or b).strip(" -"))
        assert not re.search(r"\d", e), f"a literal number in an expression: {e!r}"
        assert not re.search(r"[+*/]|\|\s*(round|int|float|length|sum|abs|count)\b", e), f"arithmetic: {e!r}"


def test_the_block_sits_inside_the_span_the_results_test_scans_and_ends_on_its_marker():
    i = TPL.index("{% if kpis %}")
    span = TPL[i: TPL.index("{% endif %}\n\n  {# ── Goals and agent decisions", i)]
    assert 'id="prs-shipped"' in span and 'id="key-metrics"' in span
    assert _trends_block().rstrip().endswith("{% endif %}")


# --- CSS and script structure (what a gate can say about a browser-only change) -----------

CSS_START = "/* ── PRs shipped and Key metrics (#1133 slice 2b)"
CSS_END = "/* ── Results: the four KPI cards"


def _css() -> str:
    return TPL[TPL.index("<style>"): TPL.index("</style>")]


def _css_block() -> str:
    css = _css()
    assert css.index(CSS_START) < css.index(CSS_END), "2b's CSS must come BEFORE 2a's marker"
    return css[css.index(CSS_START): css.index(CSS_END)]


def test_the_added_css_is_at_most_2_5_kb_with_no_literal_colour_and_no_new_token():
    block = _css_block()
    assert len(block.encode()) <= 2560, len(block.encode())
    bare = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", bare)
    assert set(re.findall(r"var\((--[a-z0-9-]+)", bare)) <= {
        "--brand", "--ink", "--ink-dim", "--ink-mute", "--line-2", "--panel", "--panel-2", "--panel-3",
        "--open", "--shipped", "--failed", "--mono"}
    assert not re.search(r"--[a-z0-9-]+\s*:", bare), "a new custom property was declared"


def test_no_tailwind_class_was_added_so_app_css_has_nothing_to_rebuild():
    block = _trends_block()
    classes = {c for m in re.findall(r'class="([^"{]*)', block) for c in m.split()}
    assert not {c for c in classes if re.match(r"(bg|text|border|p|m|flex|grid|w|h)-", c)}, classes


def _js_added() -> str:
    a = TPL[TPL.index("/* A PRs-shipped bar (#1133 slice 2b)"): TPL.index("/* The four Results cards.")]
    i = TPL.index("/* A bar names its day")
    return a + TPL[i: TPL.index("\n", TPL.index("if (t) open(t[0], day", i))]   # the handler's changed lines, whole


def test_the_added_script_is_at_most_1_kb_and_sits_before_kpi_cycles():
    assert len(_js_added().encode()) <= 1024, len(_js_added().encode())
    assert TPL.index('"kpi-prs-day":') < TPL.index('"kpi-cycles":')
    entry = re.search(r'"kpi-prs-day":(.*?)\n    /\*', TPL, re.S).group(1)
    assert "kpiPrs()" in entry and "data-prs" in entry and "function (el)" in entry and '"cycle"' in entry
    assert "want.indexOf(String(r.pr)) >= 0" in entry     # keeps the PRs listed on the bar, not the others
    assert "t[2](el)" in TPL and "t[2]()" not in TPL


def test_the_bars_do_not_use_day_btn_which_would_demand_cycles_in_overviews_blob(monkeypatch):
    _serve(monkeypatch)
    assert "day-btn" not in _section(_page().text, "prs-shipped")


# --- size ---------------------------------------------------------------------------

# The page ceiling is the issue's own 418,318 B, one constant in ops_tabs (#1562). It was a
# 245,000 then a 250,000 literal that the open-issue count kept outgrowing.
from astro_ai.ops_tabs import OVERVIEW_MAX_BYTES as OVERVIEW_CAP  # noqa: E402


def test_overview_grows_by_at_most_18_kb_and_stays_under_245_kb(monkeypatch):
    """The name keeps its history: renaming a test reads as a deletion to verify_test_floor.
    The absolute cap is OVERVIEW_CAP, ops_tabs.OVERVIEW_MAX_BYTES (418,318). Baseline is not pinned (the committed measurement files move it): the growth is
    counted from the template's own parts, and the absolute cap is the architect's."""
    _serve(monkeypatch)
    h = _page().text
    grew = (len(_section(h, "prs-shipped")) + len(_section(h, "key-metrics"))
            + len(_css_block().encode()) + len(_js_added().encode()))
    assert grew <= 18_000, grew
    assert len(h.encode()) <= OVERVIEW_CAP


def test_the_real_committed_data_stays_inside_the_same_caps():
    h = _page().text
    grew = (len(_section(h, "prs-shipped")) + len(_section(h, "key-metrics"))
            + len(_css_block().encode()) + len(_js_added().encode()))
    assert grew <= 18_000, grew
    assert len(h.encode()) <= OVERVIEW_CAP


@pytest.mark.parametrize("tab", OTHER_TABS)
def test_every_other_tab_grows_by_the_css_and_script_only_and_that_is_under_3_5_kb(tab):
    h = _page(f"?tab={tab}").text
    assert 'id="prs-shipped"' not in h and 'id="key-metrics"' not in h
    assert len(_css_block().encode()) + len(_js_added().encode()) <= 3_500


def test_overview_warm_render_is_under_300_ms(monkeypatch):
    _serve(monkeypatch)
    _page()                                              # warm the caches
    took = []
    for _ in range(5):
        t = time.perf_counter()
        _page()
        took.append((time.perf_counter() - t) * 1000)
    assert sorted(took)[2] < 300, took
