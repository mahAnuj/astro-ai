"""The engineering-loop ring, Agent health and System health on /admin/ops Overview,
template half (#1133 slice 2c, step 2).

`tests/test_ops_loop_health.py` covers `ops_loop_health.build`. These render the real
page from a fixture whose answers are written out below by hand, then read what a
visitor gets: seven ring steps whose links are the rail's own and also sit in the
legend, a cadence caption and a state WORD for every step, an `role="img"` SVG with an
aria-label that lists the steps and a hidden table, and the three panels degrading to
"unavailable" rather than to a green or a zero.

What these cannot see, and nothing else here does either: the colours, the spacing and
whether the ring's text fits at 375px are browser-only. The CSS tests pin size and
shape; the look at 375px, 768px and 1280px, light and dark, the horizontal scroll
(`scrollWidth`), the effective SVG text size and the Tab order through the legend were
checked by hand in headless Chromium and are not in a gate.
"""
from __future__ import annotations

import html as htmllib
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import agent_status, ops_data, ops_loop_health, ops_tabs

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()
OTHER_TABS = [k for k, _ in ops_tabs.TABS if k != "overview"]
MARK = "/* ── The engineering loop, Agent health, System health (#1133 slice 2c)"
CSS_END = "/* ── PRs shipped and Key metrics (#1133 slice 2b)"
OVERVIEW_GROW_CAP = 15_000          # architect's plan: baseline + 15,000 B
SECTIONS_CAP = 12_000
CSS_CAP = 3_000
OVERVIEW_CAP = 250_000


def _stamp(hours: int = 3) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _loop(wf, health="green", concl="success", cadence=None, verdict="not-due-yet"):
    return {"workflow": wf, "verdict": verdict, "last_run": _stamp(5), "last_conclusion": concl,
            "last_run_health": health, "cadence": cadence}


# Written out by hand: expected state and word per ring step, from last_run_health alone.
LOOPS = [_loop("agent-measure.yml", cadence=["00 21 * * *", "23 09 * * *"]),
         _loop("agent-prioritise.yml", cadence=["00 17 * * 0"]),
         _loop("agent-discover.yml", "red", "failure", cadence=["00 20 * * 1"]),
         _loop("agent-work.yml", "running", "in_progress", cadence=["00 23 * * *"]),
         _loop("pr-gates.yml", cadence=["47 20 * * *"]),
         _loop("agent-merge.yml", verdict="on-demand"),
         _loop("verify-production.yml", cadence=["17 06 * * 1"]),
         _loop("loop-outcomes.yml", "amber", "failure", cadence=["30 03 * * 2"])]
HAND = [("Measure", "ok", "last run green"), ("Decide", "bad", "last run red"),
        ("Build", "running", "running at last collection"), ("Check", "ok", "last run green"),
        ("Merge", "ok", "last run green"), ("Ship & Verify", "ok", "last run green"),
        ("Score", "watch", "last run amber")]
CAPTIONS = ["daily", "weekly", "back to back", "each PR push", "every 30 min", "each deploy", "weekly"]
CRONS = ["cron 00 21 * * *; 23 09 * * * (UTC)", "cron 00 17 * * 0 (UTC)", "cron 00 23 * * * (UTC)",
         "cron 47 20 * * * (UTC)", "on events", "cron 17 06 * * 1 (UTC)", "cron 30 03 * * 2 (UTC)"]

CARDS = {"agents": [{"id": f"{g}{i}", "group": g, "state": s}
                    for g, st in {"build": ["building", "blocked", "standby"], "decide": ["done"],
                                  "measure": ["done", "idle"], "operate": ["done"]}.items()
                    for i, s in enumerate(st)],
         "groups": list(agent_status.GROUPS), "live": False, "counts": {}}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(agent_status, "snapshot", lambda *a, **k: CARDS)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _serve(monkeypatch, agents="default"):
    files = {}
    if agents == "default":
        files["agents.json"] = {"generated_at": _stamp(), "loops": LOOPS, "alerts": []}
    elif agents is not None:
        files["agents.json"] = agents
    monkeypatch.setattr(ops_data, "_fetch", lambda name: files.get(name))


def _page(q: str = "?tab=overview"):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _section(html: str, sid: str) -> str:
    i = html.index(f'id="{sid}"')
    return html[html.rindex("<section", 0, i): html.index("</section>", i)]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", htmllib.unescape(fragment))).strip()


def _rail_hrefs(html: str) -> set[str]:
    rail = html[html.index('<aside class="rail">'): html.index("</aside>")]
    return {htmllib.unescape(h) for h in re.findall(r'href="(\?tab=[^"]+)"', rail)}


def _ring(html: str):
    sec = _section(html, "loop-ring")
    svg = re.search(r"<svg class=\"lpr\".*?</svg>", sec, re.S).group(0)
    leg = re.search(r'<ol class="lp-leg">.*?</ol>', sec, re.S).group(0)
    return sec, svg, leg


def _legend_items(leg: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<li class="st-(\w+)">(.*?)</li>', leg, re.S):
        out.append({"state": m.group(1), "html": m.group(2), "text": _text(m.group(2))})
    return out


# --- the ring ---------------------------------------------------------------------------

def test_seven_steps_in_order_each_with_its_state_word_and_cadence_caption(monkeypatch):
    _serve(monkeypatch)
    items = _legend_items(_ring(_page().text)[2])
    assert len(items) == 7
    for it, (name, state, word), cap, cron in zip(items, HAND, CAPTIONS, CRONS):
        assert name in it["text"] and it["state"] == state, (name, it["state"])
        assert word in it["text"], (name, it["text"])            # the state is a WORD, not a colour
        assert f"· {cap}" in it["text"] and cron in it["text"], (name, it["text"])


def test_a_workflow_that_is_not_the_only_one_in_a_step_carries_its_own_state_word(monkeypatch):
    _serve(monkeypatch)
    decide = _legend_items(_ring(_page().text)[2])[1]["text"]
    # Decide is agent-prioritise (green) + agent-discover (red): the step is the worst, red.
    assert "agent-prioritise" in decide and "agent-discover" in decide
    assert "last run green" in decide and decide.count("last run red") == 2


def test_every_ring_link_is_in_the_legend_and_is_one_of_the_rails_own_hrefs(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    sec, svg, leg = _ring(h)
    rail = _rail_hrefs(h)
    ring_hrefs = [htmllib.unescape(x) for x in re.findall(r'<a href="([^"]+)" tabindex="-1">', svg)]
    leg_hrefs = [htmllib.unescape(x) for x in re.findall(r'<a href="([^"]+)">\d\. ', leg)]
    assert len(ring_hrefs) == 7 and len(leg_hrefs) == 7
    assert ring_hrefs == leg_hrefs
    assert set(ring_hrefs) <= rail, set(ring_hrefs) - rail
    assert {"?tab=runs&window=7", "?tab=workflows&window=7"} <= set(ring_hrefs)


def test_the_ring_is_an_image_with_an_aria_label_listing_every_step_and_a_hidden_table(monkeypatch):
    _serve(monkeypatch)
    sec, svg, _ = _ring(_page().text)
    tag = re.match(r"<svg[^>]*>", svg).group(0)
    assert 'role="img"' in tag
    assert re.findall(r'<text class="nn"[^>]*>(\d)</text>', svg) == [str(n) for n in range(1, 8)]
    label = htmllib.unescape(re.search(r'aria-label="([^"]*)"', tag).group(1))
    for n, (name, _s, word) in enumerate(HAND, start=1):
        assert f"Step {n}, {name}" in label and word in label, (n, label)
    tbl = re.search(r'<div class="vh"><table>(.*?)</table>', sec, re.S).group(1)
    rows = re.findall(r'<tr><th scope="row">(\d)</th><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td></tr>', tbl)
    assert [(r[0], htmllib.unescape(r[1]), r[3]) for r in rows] == [
        (str(n), name, word) for n, (name, _s, word) in enumerate(HAND, start=1)]


def test_a_node_is_not_coloured_alone_it_has_a_glyph_and_the_dot_is_hidden_from_readers(monkeypatch):
    _serve(monkeypatch)
    sec, svg, leg = _ring(_page().text)
    assert re.findall(r'<tspan class="gl" dx="5">(.*?)</tspan>', svg) == ["✓", "✕", "…", "✓", "✓", "✓", "!"]
    assert leg.count('class="ld" aria-hidden="true"') == 7
    assert "<title>" not in svg


def test_there_are_seven_arrows_with_a_marker_and_no_current_step_is_marked(monkeypatch):
    _serve(monkeypatch)
    _, svg, _ = _ring(_page().text)
    assert len(re.findall(r'<path class="ar"[^>]*marker-end="url\(#lp-ah\)"', svg)) == 7
    assert "current" not in svg and "aria-current" not in svg


def test_a_running_step_says_it_was_running_at_the_last_collection(monkeypatch):
    _serve(monkeypatch)
    build = _legend_items(_ring(_page().text)[2])[2]
    assert "running at last collection" in build["text"] and build["state"] == "running"


# --- Agent health and System health -------------------------------------------------------

def test_agent_health_lists_the_groups_from_the_data_with_failed_blocked_words(monkeypatch):
    _serve(monkeypatch)
    sec = _section(_page().text, "agent-health")
    txt = _text(sec)
    assert "7 cards · 4 groups" in txt
    for g in ("Build", "Decide", "Measure", "Operate"):
        assert f"{g} ·" in txt
    assert "1 building · 1 standby" in txt or "1 building" in txt
    assert "last known, GitHub not read" in txt        # live is False in the fixture
    assert "none failed" in txt


def test_a_fifth_group_appears_from_data_not_from_code(monkeypatch):
    _serve(monkeypatch)
    cards = dict(CARDS, agents=CARDS["agents"] + [{"id": "x", "group": "on request", "state": "failed"}])
    monkeypatch.setattr(agent_status, "snapshot", lambda *a, **k: cards)
    txt = _text(_section(_page().text, "agent-health"))
    assert "8 cards · 5 groups" in txt and "On request · 1 failed" in txt


def test_system_health_has_four_rows_each_with_a_state_word_and_a_link(monkeypatch):
    _serve(monkeypatch)
    sec = _section(_page().text, "system-health")
    rows = re.findall(r'<li class="st-(\w+)">\s*<span class="ld" aria-hidden="true"></span>\s*<div><b>(.*?)</b> · <span class="lw">(.*?)</span>(.*?)</div>', sec, re.S)
    assert [htmllib.unescape(r[1]) for r in rows] == [
        "LLM providers", "GitHub Actions", "Website (production)", "Monitoring & alerts"]
    assert all(r[2].strip() for r in rows)
    assert all('href="' in r[3] for r in rows)
    site = _text(rows[2][3])
    assert "not an uptime monitor" in site
    assert "not an uptime monitor" in _text(sec.split("</ul>")[1])     # the panel footnote says it too
    assert "operational" not in _text(sec).lower().replace("not an uptime monitor", "")
    assert "all healthy" not in _text(sec).lower()


def test_the_monitoring_row_says_what_the_rail_block_says(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    rail = re.search(r'<div class="rail-health h-(\w+)"[^>]*>(.*?)</div>', h, re.S)
    label = re.search(r"<b>(.*?)</b>", rail.group(2), re.S).group(1).strip()
    assert htmllib.unescape(label) in _text(_section(h, "system-health"))


# --- degraded renders -----------------------------------------------------------------------

@pytest.mark.parametrize("agents", [None, {}, {"loops": "x"}, {"generated_at": "x", "loops": [None, 3, {"workflow": 5}, {"verdict": []}]}])
def test_a_missing_or_garbage_agents_file_degrades_the_panels_never_a_green_or_a_500(monkeypatch, agents):
    _serve(monkeypatch, agents)
    r = _page()
    assert r.status_code == 200
    h = r.text
    sec = _section(h, "loop-ring")
    # Either the whole ring says why it is unavailable, or every step reads unavailable.
    items = _legend_items(_ring(h)[2]) if "lp-leg" in sec else []
    assert all(i["state"] == "unavailable" for i in items)
    assert "st-ok" not in sec and "st-watch" not in sec and "st-bad" not in sec
    assert "unavailable" in _text(sec)


def test_an_empty_agent_status_says_unavailable_not_zero_cards(monkeypatch):
    _serve(monkeypatch)
    for snap in ({}, {"agents": [{"group": None}]}, {"agents": [], "groups": ["build"]}):
        monkeypatch.setattr(agent_status, "snapshot", lambda *a, _s=snap, **k: _s)
        r = _page()
        assert r.status_code == 200
        sec = _section(r.text, "agent-health")
        assert "unavailable: agent_status returned no agents" in sec and 'role="status"' in sec
        assert "0 cards" not in _text(sec) and "<li" not in sec


def test_a_failed_build_renders_unavailable_everywhere_and_the_page_still_renders(monkeypatch):
    _serve(monkeypatch)
    from astro_ai.routes import admin
    monkeypatch.setattr(admin.ops_loop_health, "build", lambda *a: ops_loop_health._unavailable("unavailable: boom"))
    r = _page()
    assert r.status_code == 200
    h = r.text
    assert "unavailable: boom" in _section(h, "loop-ring") and "<svg" not in _section(h, "loop-ring")
    assert "unavailable: boom" in _section(h, "agent-health")
    assert _text(_section(h, "system-health")).count("unavailable") >= 4
    assert 'role="status"' in _section(h, "system-health")
    assert 'id="prs-shipped"' in h or 'class="panel kpis"' in h


def test_with_no_loop_health_at_all_the_page_still_renders(monkeypatch):
    _serve(monkeypatch)
    from astro_ai.routes import admin
    monkeypatch.setattr(admin.ops_loop_health, "build", lambda *a: None)
    r = _page()
    assert r.status_code == 200
    for sid in ("loop-ring", "agent-health", "system-health"):
        assert f'id="{sid}"' not in r.text
    assert 'class="panel kpis"' in r.text and 'id="goals"' in r.text


def test_a_hostile_string_in_agents_json_is_escaped_everywhere_it_lands(monkeypatch):
    evil = '"><script>alert(1)</script>'
    loops = [dict(l) for l in LOOPS]
    loops[0].update(last_conclusion=evil, cadence=[evil], last_run=evil, last_run_health=evil)
    loops[1]["workflow"] = evil
    _serve(monkeypatch, {"generated_at": _stamp(), "loops": loops, "alerts": []})
    r = _page()
    assert r.status_code == 200
    body = _section(r.text, "loop-ring") + _section(r.text, "system-health")
    assert "<script>alert" not in body and evil not in body


# --- one tab only; what the others pay --------------------------------------------------------

@pytest.mark.parametrize("tab", OTHER_TABS)
def test_no_other_tab_has_any_of_the_three_panels(tab):
    h = _page(f"?tab={tab}").text
    for marker in ('id="loop-ring"', 'id="agent-health"', 'id="system-health"', 'class="lpr"', "lp-duo\">"):
        assert marker not in h, (tab, marker)


def test_h2_order_on_overview_is_results_loop_agents_system_prs(monkeypatch):
    _serve(monkeypatch)
    body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", _page().text, flags=re.S)
    heads = [_text(m) for m in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)]
    heads = [h.split(" IST")[0] for h in heads]
    want = ["Results", "The engineering loop", "Agent health", "System health", "PRs shipped"]
    idx = [next(i for i, h in enumerate(heads) if h.startswith(w)) for w in want]
    assert idx == sorted(idx) and idx[-1] - idx[0] == 4, heads


def test_the_panels_add_no_drill_down_no_day_button_and_no_script(monkeypatch):
    _serve(monkeypatch)
    sec = _section(_page().text, "loop-ring") + _section(_page().text, "agent-health") + _section(_page().text, "system-health")
    for bad in ("data-drill", "day-btn", "<script", "onclick", "<button"):
        assert bad not in sec, bad
    block = TPL[TPL.index("{% if loop_health %}"): TPL.index("{# ── PRs shipped and Key metrics (#1133 slice 2b)")]
    assert "<script" not in block and "data-drill" not in block


# --- no arithmetic in the template; CSS shape -----------------------------------------------

def _block() -> str:
    i = TPL.index("{% if loop_health %}")
    return TPL[i: TPL.index("{# ── PRs shipped and Key metrics (#1133 slice 2b)", i)]


def test_the_new_block_has_no_arithmetic_and_no_literal_number_in_an_expression():
    exprs = re.findall(r"\{\{(.*?)\}\}|\{%(.*?)%\}", _block(), re.S)
    assert len(exprs) > 60
    for a, b in exprs:
        e = re.sub(r"'[^']*'|\"[^\"]*\"", "''", (a or b).strip(" -"))
        assert not re.search(r"\d", e), f"a literal number in an expression: {e!r}"
        assert not re.search(r"[+*/]|\|\s*(round|int|float|length|sum|abs|count)\b", e), f"arithmetic: {e!r}"


def test_the_block_sits_before_the_prs_panel_inside_the_span_the_results_test_scans():
    i = TPL.index("{% if kpis %}")
    span = TPL[i: TPL.index("{% endif %}\n\n  {# ── Goals and agent decisions", i)]
    assert span.index('id="loop-ring"') < span.index('id="agent-health"') < span.index('id="system-health"') \
        < span.index('id="prs-shipped"')
    assert _block().rstrip().endswith("{% endif %}")


def _css() -> str:
    css = TPL[TPL.index("<style>"): TPL.index("</style>")]
    return css[css.index(MARK): css.index(CSS_END)]


def test_the_added_css_is_under_its_cap_with_no_literal_colour_and_no_new_token():
    block = _css()
    assert len(block.encode()) <= CSS_CAP, len(block.encode())
    bare = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", bare)
    assert not re.search(r"--[a-z0-9-]+\s*:", bare), "a custom property was declared"
    assert set(re.findall(r"var\((--[a-z0-9-]+)", bare)) <= {
        "--ink", "--ink-dim", "--ink-mute", "--nothing-text", "--shipped", "--open", "--failed",
        "--st-running", "--panel", "--panel-2", "--line-2", "--ui", "--mono"}
    # a status colour used as TEXT stays on the tokens that clear AA on --panel; --st-* is a fill/stroke
    assert not re.search(r"(?<![-a-z])color:var\(--st-", bare)


def test_a_grid_has_no_padding_the_cells_carry_it():
    bare = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    for sel in (".lp-leg", ".lp-duo"):
        for rule in re.findall(r"(?m)^" + re.escape(sel) + r"\{([^}]*)\}", bare):
            assert "padding" not in rule, (sel, rule)


def test_no_tailwind_class_was_added_so_app_css_has_nothing_to_rebuild():
    classes = {c for m in re.findall(r'class="([^"{]*)', _block()) for c in m.split()}
    assert not {c for c in classes if re.match(r"(bg|text|border|p|m|flex|grid|w|h)-", c)}, classes


def test_the_ring_text_drops_its_cadence_line_under_640px_and_keeps_names_readable():
    bare = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    assert re.search(r"@media \(max-width:640px\)\{[^}]*\.lpr \.nc\{display:none\}", bare)
    assert re.search(r"@media \(min-width:768px\)\{\.lp-duo\{grid-template-columns:repeat\(2,", bare)


# --- size -----------------------------------------------------------------------------------

def _sections(h: str) -> int:
    i = h.rindex("<section", 0, h.index('id="loop-ring"'))
    j = h.rindex("<section", 0, h.index('id="prs-shipped"'))
    return len(h[i:j].encode())


def test_the_three_sections_and_the_css_stay_inside_their_caps(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    assert _sections(h) <= SECTIONS_CAP, _sections(h)
    assert len(_css().encode()) <= CSS_CAP
    assert len(h.encode()) <= OVERVIEW_CAP


def test_the_real_committed_data_stays_inside_the_same_caps():
    h = _page().text
    assert _sections(h) <= SECTIONS_CAP, _sections(h)
    assert len(h.encode()) <= OVERVIEW_CAP


@pytest.mark.parametrize("tab", OTHER_TABS)
def test_every_other_tab_grows_by_the_css_only_and_that_is_under_3_kb(tab):
    h = _page(f"?tab={tab}").text
    assert 'id="loop-ring"' not in h
    assert len(_css().encode()) <= 3_000


def test_overview_growth_is_the_sections_plus_the_css_and_at_most_15_kb(monkeypatch):
    _serve(monkeypatch)
    h = _page().text
    assert _sections(h) + len(_css().encode()) <= OVERVIEW_GROW_CAP


def test_overview_warm_render_is_under_300_ms(monkeypatch):
    _serve(monkeypatch)
    _page()
    took = []
    for _ in range(5):
        t = time.perf_counter()
        _page()
        took.append((time.perf_counter() - t) * 1000)
    assert sorted(took)[2] < 300, took
