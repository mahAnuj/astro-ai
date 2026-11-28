"""The Recent activity panel on /admin/ops Overview, template half (#1133 slice 2d, step 2).

`tests/test_ops_activity.py` covers `ops_activity.build`. These render the real page and
read what a visitor gets: the panel on Overview only, four filter chips that are server
links (one `aria-current`), rows that carry a state WORD, a type chip and a `<time>`, every
link this repo's own, the three degraded states, and the bytes.

The hand-built shapes are injected at the one seam the route uses (`ops_activity.build`
receives them in place of `ops["loop"]`, `["agents"]`, `["issues"]`), so a garbage shape
reaches the template without first failing inside `snapshot()` (the #1554 class, out of
scope here). Absent files go the real way, through `ops_data._fetch`.

What these cannot see, and nothing else here does either: the colours, whether a row wraps
cleanly at 375px, the focus ring on a chip and the click landing on the panel are
browser-only. They were looked at in headless Chromium (375px and 1280px, light and dark)
and are not in a gate.
"""
from __future__ import annotations

import html as htmllib
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import agent_status, ops_activity, ops_data, ops_tabs
from astro_ai.ops_tabs import OVERVIEW_MAX_BYTES as OVERVIEW_CAP

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()
OTHER_TABS = [k for k, _ in ops_tabs.TABS if k != "overview"]
MARK = "/* ── Recent activity (#1133 slice 2d)"
CSS_END = "/* ── The engineering loop, Agent health, System health (#1133 slice 2c)"
SECTION_CAP = 6_500
CSS_CAP = 1_500
REPO = "https://github.com/mahAnuj/astro-ai/"
_KEEP = object()
_REAL_BUILD = ops_activity.build        # taken at import, so a second _inject never wraps the first
CARDS = {"agents": [], "groups": [], "live": False, "counts": {}}


def _stamp(hours: float = 3) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cycle(i, outcome="shipped", pr=None, run=None):
    return {"run": run, "workflow": "agent-work", "started": _stamp(i + 1), "outcome": outcome,
            "kind": "issue", "pr": pr, "issue": 100 + i, "minutes": 12.0}


def _wf(i, name=None, health="green"):
    wf = f"wf-{i}.yml"
    return {"workflow": wf, "display": name or f"Workflow {i}", "last_run": _stamp(i + 1),
            "last_conclusion": "success", "last_run_health": health}


def _issue(i, title=None, blocked=False):
    return {"number": 500 + i, "title": title or f"Issue number {i}", "created": _stamp(i + 1),
            "blocked": blocked, "type": "bug", "priority": "low"}


def _loop(rows, live=False):
    return {"ok": True, "rows": rows, "today_live": live, "today_shipped": [], "today_failed": []}


def _full(n=20):
    return dict(loop=_loop([_cycle(i, pr=2000 + i) for i in range(n)]),
                agents={"ok": True, "loops": [_wf(i) for i in range(n)]},
                issues={"ok": True, "rows": [_issue(i) for i in range(n)]})


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(agent_status, "snapshot", lambda *a, **k: CARDS)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _inject(monkeypatch, loop=_KEEP, agents=_KEEP, issues=_KEEP):
    real = _REAL_BUILD

    def wrapped(ops, links, active="all"):
        o = dict(ops)
        for k, v in (("loop", loop), ("agents", agents), ("issues", issues)):
            if v is not _KEEP:
                o[k] = v
        return real(o, links, active)
    monkeypatch.setattr(ops_activity, "build", wrapped)


def _page(q: str = "?tab=overview"):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _section(html: str, sid: str = "recent-activity") -> str:
    i = html.index(f'id="{sid}"')
    return html[html.rindex("<section", 0, i): html.index("</section>", i) + len("</section>")]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", htmllib.unescape(fragment))).strip()


def _chips(sec: str):
    return re.findall(r'<a class="win( on)?" href="([^"]+)"( aria-current="true")?>([^<]*)</a>', sec)


def _rows(sec: str):
    return re.findall(r'<li class="st-(\w+)">(.*?)</li>', sec, re.S)


def _rail_href(html: str, key: str) -> str:
    rail = html[html.index('<aside class="rail">'): html.index("</aside>")]
    return htmllib.unescape(re.search(rf'href="(\?tab={key}[^"]*)"', rail).group(1))


# --- where the panel is -----------------------------------------------------------------

def test_the_panel_is_on_overview_once_after_key_metrics_and_before_goals():
    h = _page().text
    assert h.count('id="recent-activity"') == 1
    assert h.index('id="key-metrics"') < h.index('id="recent-activity"') < h.index('id="goals"')
    assert _text(re.search(r'<h2 id="ra-h">(.*?)</h2>', h, re.S).group(1)).startswith("Recent activity")


@pytest.mark.parametrize("tab", OTHER_TABS)
def test_no_other_tab_has_the_panel(tab):
    r = _page(f"?tab={tab}")
    assert r.status_code == 200
    for marker in ('id="recent-activity"', 'class="ra-bar"', "ra-list"):
        assert marker not in re.sub(r"<style>.*?</style>", "", r.text, flags=re.S), (tab, marker)


# --- the chips --------------------------------------------------------------------------

def test_four_chips_are_links_labelled_in_order_and_exactly_one_is_current():
    chips = _chips(_section(_page().text))
    assert [c[3] for c in chips] == ["All", "Agents", "Workflows", "Issues"]
    assert [bool(c[0]) for c in chips] == [True, False, False, False]
    assert [bool(c[2]) for c in chips] == [True, False, False, False]    # class and aria agree


def test_chip_hrefs_are_the_overview_href_plus_the_filter_and_the_anchor():
    chips = _chips(_section(_page().text))
    assert [htmllib.unescape(c[1]) for c in chips] == [
        f"?tab=overview&window=7&activity={k}#recent-activity"
        for k in ("all", "agents", "workflows", "issues")]


def test_a_picked_day_is_kept_in_every_chip_href():
    day = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    h = _page(f"?tab=overview&day={day}").text
    hrefs = [htmllib.unescape(c[1]) for c in _chips(_section(h))]
    assert hrefs == [f"?tab=overview&day={day}&activity={k}#recent-activity"
                     for k in ("all", "agents", "workflows", "issues")]


@pytest.mark.parametrize("key,idx", [("agents", 1), ("workflows", 2), ("issues", 3), ("ALL", 0)])
def test_the_chosen_chip_is_the_current_one(key, idx):
    chips = _chips(_section(_page(f"?tab=overview&activity={key}").text))
    assert [bool(c[2]) for c in chips] == [i == idx for i in range(4)]


@pytest.mark.parametrize("q", ["?activity=zzz", "?tab=overview&activity=%3Cscript%3E", "?activity=",
                               "?tab=overview&activity=%00"])
def test_an_unknown_filter_is_a_200_with_all_current_and_is_never_echoed(q):
    r = _page(q)
    assert r.status_code == 200
    sec = _section(r.text)
    assert [bool(c[2]) for c in _chips(sec)] == [True, False, False, False]
    assert "zzz" not in r.text and "%3Cscript" not in sec and "&lt;script" not in sec


def test_another_tab_with_the_param_is_a_200():
    assert _page("?tab=agents&activity=issues").status_code == 200


def test_the_deployments_chip_is_not_offered_and_the_panel_does_not_mention_it():
    assert "deployment" not in _text(_section(_page().text)).lower()


# --- rows -------------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["all", "agents", "workflows", "issues"])
def test_at_most_eight_rows_in_every_view_on_the_real_committed_data(key):
    sec = _section(_page(f"?tab=overview&activity={key}").text)
    assert 1 <= len(_rows(sec)) <= 8


@pytest.mark.parametrize("key", ["all", "agents", "workflows", "issues"])
def test_exactly_eight_rows_from_a_sixty_row_fixture(monkeypatch, key):
    _inject(monkeypatch, **_full(20))
    assert len(_rows(_section(_page(f"?tab=overview&activity={key}").text))) == 8


@pytest.mark.parametrize("key", ["all", "agents", "workflows", "issues"])
def test_every_row_has_a_state_word_a_type_chip_a_time_and_a_repo_link(monkeypatch, key):
    _inject(monkeypatch, **_full(20))
    rows = _rows(_section(_page(f"?tab=overview&activity={key}").text))
    assert rows
    for state, body in rows:
        assert state in {"ok", "watch", "bad", "running", "info", "unavailable"}
        assert 'class="ld" aria-hidden="true"' in body                  # the dot is decoration
        word = re.search(r'<span class="lw">([^<]+)</span>', body)
        assert word and word.group(1).strip(), body                     # the state is a WORD
        assert re.search(r'<span class="chip">(Agent|Workflow|Issue)</span>', body)
        assert re.search(r'<time class="ra-t" datetime="\d{4}-\d\d-\d\dT[\d:]+Z" title="[^"]+ IST">[^<]+</time>', body)
        href = re.search(r'<a href="([^"]+)">', body)
        assert href and href.group(1).startswith(REPO), body


def test_the_state_words_are_written_out_for_each_kind_of_row(monkeypatch):
    _inject(monkeypatch,
            loop=_loop([_cycle(0, "shipped", pr=7), _cycle(1, "failed", run=9), _cycle(2, "pr open", pr=8)]),
            agents={"ok": True, "loops": []}, issues={"ok": True, "rows": [_issue(3, blocked=True)]})
    rows = _rows(_section(_page("?tab=overview&activity=all").text))
    got = [(s, re.search(r'<span class="lw">([^<]+)</span>', b).group(1)) for s, b in rows]
    assert got == [("ok", "shipped"), ("bad", "failed"), ("watch", "PR open"), ("watch", "blocked")]
    assert 'href="https://github.com/mahAnuj/astro-ai/pull/7"' in rows[0][1]
    assert 'href="https://github.com/mahAnuj/astro-ai/actions/runs/9"' in rows[1][1]
    assert 'href="https://github.com/mahAnuj/astro-ai/issues/503"' in rows[3][1]


def test_a_row_with_no_id_has_no_link_but_still_a_title(monkeypatch):
    _inject(monkeypatch, loop=_loop([_cycle(0, "nothing")]), agents={"ok": True, "loops": []},
            issues={"ok": True, "rows": []})
    (state, body), = _rows(_section(_page("?tab=overview&activity=agents").text))
    assert "<a href=" not in body and "Build cycle on issue #100" in body


# --- "View all" -------------------------------------------------------------------------

@pytest.mark.parametrize("key,tab", [("all", "runs"), ("agents", "runs"),
                                     ("workflows", "workflows"), ("issues", "backlog")])
def test_view_all_is_the_rails_own_href_for_that_kind_of_row(key, tab):
    h = _page(f"?tab=overview&activity={key}").text
    sec = _section(h)
    m = re.search(r'<a href="([^"]+)">View all &rarr;</a>', sec)
    assert m and htmllib.unescape(m.group(1)) == _rail_href(h, tab)


# --- the three degraded states ------------------------------------------------------------

def test_the_notes_say_closed_issues_are_not_listed_and_where_today_comes_from():
    t = _text(_section(_page().text))
    assert "Closed issues are not listed" in t
    assert "committed snapshot" in t                       # live is off in this suite


def test_empty_says_so_in_a_status_paragraph_and_unavailable_says_why(monkeypatch):
    _inject(monkeypatch, loop=_loop([]), agents={"ok": True, "loops": []}, issues={"ok": True, "rows": []})
    sec = _section(_page("?tab=overview&activity=agents").text)
    assert '<p class="sub" role="status">No agent activity in the data read.</p>' in sec and "<li" not in sec
    _inject(monkeypatch, loop=None, agents=None, issues=None)
    sec = _section(_page("?tab=overview&activity=all").text)
    assert "unavailable: loop.json not read" in sec and 'role="status"' in sec
    assert "<li" not in sec and "no activity in the data read" not in _text(sec).lower()


def test_every_tab_is_a_200_with_the_three_files_absent_and_the_panel_says_unavailable(monkeypatch):
    monkeypatch.setattr(ops_data, "_fetch",
                        lambda name: None if name in ("loop.json", "agents.json", "issues.json") else {})
    for tab in [k for k, _ in ops_tabs.TABS]:
        r = _page(f"?tab={tab}")
        assert r.status_code == 200, tab
    sec = _section(_page().text)
    assert "unavailable" in _text(sec) and "<li" not in sec


@pytest.mark.parametrize("shape", [None, {}, "x", [], {"ok": True, "rows": [None, 1, "x", []]},
                                   {"ok": True, "rows": "x", "loops": "y"},
                                   {"ok": True, "rows": [{"started": "<script>alert(1)</script>"}]}])
def test_garbage_shapes_never_500_and_the_page_still_renders(monkeypatch, shape):
    _inject(monkeypatch, loop=shape, agents=shape, issues=shape)
    for q in ("?tab=overview", "?tab=overview&activity=agents", "?tab=overview&activity=issues"):
        r = _page(q)
        assert r.status_code == 200, (q, shape)
        assert 'id="recent-activity"' in r.text and 'id="goals"' in r.text


def test_one_builder_failing_says_so_and_the_other_rows_still_render(monkeypatch):
    _inject(monkeypatch, **_full(3))

    def boom(ops, now):
        raise RuntimeError("boom")
    monkeypatch.setitem(ops_activity._BUILDERS, "workflows", boom)
    sec = _section(_page("?tab=overview&activity=all").text)
    t = _text(sec)
    assert "A source above could not be computed" in t and "Workflows: could not be computed" in t
    assert {re.search(r'class="chip">(\w+)<', b).group(1) for _, b in _rows(sec)} == {"Agent", "Issue"}


# --- hostile strings --------------------------------------------------------------------

def test_a_script_string_in_a_title_subtitle_or_workflow_name_is_escaped(monkeypatch):
    evil = '"><script>alert(1)</script>'
    _inject(monkeypatch,
            loop=_loop([dict(_cycle(0, pr=5), workflow=evil)]),
            agents={"ok": True, "loops": [dict(_wf(1, name=evil), workflow="../x.yml")]},
            issues={"ok": True, "rows": [_issue(2, title=evil)]})
    r = _page("?tab=overview&activity=all")
    assert r.status_code == 200
    sec = _section(r.text)
    assert "<script>alert" not in sec and evil not in sec and "&lt;script&gt;" in sec
    assert "../x.yml" not in sec


# --- the template's own shape -------------------------------------------------------------

def _block() -> str:
    i = TPL.index("{% if activity %}")
    return TPL[i: TPL.index("{# ── Goals and agent decisions", i)]


def test_the_block_has_no_arithmetic_and_no_literal_number_in_an_expression():
    exprs = re.findall(r"\{\{(.*?)\}\}|\{%(.*?)%\}", _block(), re.S)
    assert len(exprs) > 15
    for a, b in exprs:
        e = re.sub(r"'[^']*'|\"[^\"]*\"", "''", (a or b).strip(" -"))
        assert not re.search(r"\d", e), f"a literal number in an expression: {e!r}"
        assert not re.search(r"[+*/]|\|\s*(round|int|float|length|sum|abs|count)\b", e), f"arithmetic: {e!r}"


def test_the_block_has_no_script_no_drill_no_safe_and_no_tailwind_class():
    block = _block()
    for bad in ("<script", "data-drill", "|safe", "onclick", "<button"):
        assert bad not in block, bad
    classes = {c for m in re.findall(r'class="([^"{]*)', block) for c in m.split()}
    assert not {c for c in classes if re.match(r"(bg|text|border|p|m|flex|grid|w|h)-", c)}, classes


def test_the_block_sits_inside_the_span_the_other_slices_scan_and_ends_on_the_marker():
    i = TPL.index("{% if kpis %}")
    span = TPL[i: TPL.index("{% endif %}\n\n  {# ── Goals and agent decisions", i)]
    assert 'id="key-metrics"' in span and 'id="recent-activity"' in span
    assert span.index('id="key-metrics"') < span.index('id="recent-activity"')
    assert _block().rstrip().endswith("{% endif %}")


def _css() -> str:
    css = TPL[TPL.index("<style>"): TPL.index("</style>")]
    return css[css.index(MARK): css.index(CSS_END)]


def test_the_css_is_under_its_cap_with_no_literal_colour_no_new_token_and_sits_before_2c():
    block = _css()
    assert len(block.encode()) <= CSS_CAP, len(block.encode())
    bare = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", bare)
    assert not re.search(r"--[a-z0-9-]+\s*:", bare), "a custom property was declared"
    assert set(re.findall(r"var\((--[a-z0-9-]+)", bare)) <= {"--ink-mute", "--mono"}
    assert TPL.index(MARK) < TPL.index(CSS_END)
    assert not re.search(r"(?m)^\.ra(-list)?\{[^}]*padding", bare)       # a list has no padding


def test_the_row_wraps_under_640px_and_the_chip_keeps_its_size():
    bare = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    assert re.search(r"@media \(max-width:640px\)\{\.ra-list>li\{flex-wrap:wrap\}", bare)
    assert ".ra-list>li>div{flex:1 1 200px}" in bare and ".ra-list>li>.chip{flex:none}" in bare


# --- size -------------------------------------------------------------------------------

def test_the_section_is_bounded_on_a_worst_case_fixture_with_every_string_at_its_cap(monkeypatch):
    long_t, long_s = "W" * ops_activity.TITLE_MAX, "s" * 20
    loop = _loop([dict(_cycle(i, pr=2000 + i), workflow="x" * 60) for i in range(30)])
    agents = {"ok": True, "loops": [dict(_wf(i, name=long_t), workflow=f"{'w' * 50}{i}.yml") for i in range(30)]}
    issues = {"ok": True, "rows": [dict(_issue(i, title=long_t), type=long_s, priority=long_s) for i in range(30)]}
    _inject(monkeypatch, loop=loop, agents=agents, issues=issues)
    sizes = {k: len(_section(_page(f"?tab=overview&activity={k}").text).encode())
             for k in ("all", "agents", "workflows", "issues")}
    assert max(sizes.values()) <= SECTION_CAP, sizes


def test_the_section_and_the_page_on_the_real_committed_data_stay_inside_their_caps():
    h = _page().text
    assert len(_section(h).encode()) <= SECTION_CAP
    assert len(h.encode()) <= OVERVIEW_CAP


@pytest.mark.parametrize("tab", OTHER_TABS)
def test_every_other_tab_pays_for_the_css_only_and_that_is_small(tab):
    h = _page(f"?tab={tab}").text
    assert 'id="recent-activity"' not in re.sub(r"<style>.*?</style>", "", h, flags=re.S)
    assert len(_css().encode()) <= CSS_CAP


def test_overview_ships_no_new_blob_key():
    import json
    m = re.search(r'<script type="application/json" id="ops-data">(.*?)</script>', _page().text, re.S)
    keys = set(json.loads(m.group(1).replace("<\\/", "</")))
    assert keys == set(ops_tabs.BLOB_KEYS["overview"]), keys ^ set(ops_tabs.BLOB_KEYS["overview"])


def test_overview_warm_render_is_under_300_ms():
    _page()
    took = []
    for _ in range(5):
        t = time.perf_counter()
        _page()
        took.append((time.perf_counter() - t) * 1000)
    assert sorted(took)[2] < 300, took
