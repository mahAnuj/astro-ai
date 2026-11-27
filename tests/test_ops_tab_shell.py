"""The /admin/ops tab shell, template half (#1133 slice 1, step 2).

Step 1 (`tests/test_ops_tabs.py`) covers which tab is picked. These render the
real page and check what a visitor gets: seven rail links with exactly one
current, each panel on exactly one tab, the System Healthy block, and the page's
own CSS tokens (the last `:root` is complete, dark redefines all of it, no rule
carries a hex, and the text pairs clear WCAG AA arithmetic).
`scripts/verify_contrast.py` does not scan this page, so this file is the gate.
"""
from __future__ import annotations

import html
import os
import re
from datetime import date
from pathlib import Path

import pytest

from astro_ai import ops_data, ops_tabs, storage

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()
KEYS = [k for k, _ in ops_tabs.TABS]

# Every panel heading the page had before the tab shell, grouped by where each
# now lives. The union is the set that must never lose a member.
PANELS = {
    "overview": ["Results", "PRs shipped", "Key metrics", "Goals and agent decisions",
                 "Where the loop's time went"],
    "agents": ["Agents right now"],
    "workflows": ["Team"],
    "runs": ["The loop, day by day", "PR merge time"],
    "backlog": ["Issue flow", "Backlog"],
    "analytics": ["Claude tokens per shipped fix", "Google index status", "Traffic", "Cost"],
    "monitoring": ["Loop comment noise", "Token budget", "Rashifal generation", "App health"],
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _page(q: str = ""):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _body(html: str) -> str:
    return re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S)


def _h2s(html: str) -> list[str]:
    out = []
    for m in re.findall(r"<h2[^>]*>(.*?)</h2>", _body(html), flags=re.S):
        out.append(re.sub(r"<span.*", "", m, flags=re.S).strip())
    return [t for t in out if t != "—"]  # "—" is the drill-down sheet, page chrome


def _rail(html: str) -> str:
    i = html.index('<nav aria-label="Ops sections">')
    return html[i: html.index("</nav>", i)]


# --- routes ------------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_every_tab_renders(key):
    r = _page(f"?tab={key}")
    assert r.status_code == 200
    assert f'<h1 class="tab-h">{html.escape(dict(ops_tabs.TABS)[key])}</h1>' in r.text


@pytest.mark.parametrize("q", ["?tab=zzz", "?tab=governance", "?tab=", ""])
def test_an_unknown_tab_renders_overview(q):
    r = _page(q)
    assert r.status_code == 200
    assert '<h1 class="tab-h">Overview</h1>' in r.text
    assert _h2s(r.text) == PANELS["overview"]


# --- one panel, one tab ------------------------------------------------------------

def test_each_panel_is_on_exactly_one_tab_and_none_is_lost():
    seen: dict[str, list[str]] = {}
    for key in KEYS:
        for h in _h2s(_page(f"?tab={key}").text):
            seen.setdefault(h, []).append(key)
    twice = {h: t for h, t in seen.items() if len(t) != 1}
    assert not twice, f"a panel on more than one tab: {twice}"
    want = {h for hs in PANELS.values() for h in hs}
    assert set(seen) == want, f"lost {sorted(want - set(seen))}, new {sorted(set(seen) - want)}"
    for key, hs in PANELS.items():
        assert [h for h, t in seen.items() if t == [key]] == hs, key


def test_the_drill_down_sheet_is_on_every_tab():
    for key in KEYS:
        assert 'id="sheet"' in _page(f"?tab={key}").text, key


# --- the rail ----------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_the_rail_has_seven_links_and_exactly_one_is_current(key):
    rail = _rail(_page(f"?tab={key}").text)
    links = re.findall(r"<a [^>]*>", rail)
    assert len(links) == 7
    cur = [a for a in links if 'aria-current="page"' in a]
    assert len(cur) == 1 and f"tab={key}" in cur[0]
    assert "Governance" not in rail


def test_every_rail_link_keeps_the_window_or_the_picked_day():
    for l in re.findall(r'<a [^>]*href="([^"]+)"', _rail(_page("?tab=agents").text)):
        assert "window=7" in l, l
    day = date.today().isoformat()
    for l in re.findall(r'<a [^>]*href="([^"]+)"', _rail(_page(f"?tab=agents&day={day}").text)):
        assert f"day={day}" in l and "window" not in l, l


def test_the_window_and_day_controls_stay_on_their_tab():
    h = _page("?tab=monitoring").text
    assert 'name="tab" value="monitoring"' in h
    assert re.findall(r'href="\?window=\d+&amp;tab=monitoring"', h)


# --- health ------------------------------------------------------------------------

@pytest.mark.parametrize("key", KEYS)
def test_the_health_block_is_text_beside_a_dot_and_never_claims_operational(key):
    h = _page(f"?tab={key}").text
    m = re.search(r'<div class="rail-health h-(ok|watch|bad)"[^>]*>(.*?)</div>\s*</div>', h, re.S)
    assert m, "no System Healthy block"
    text = re.sub(r"<[^>]+>", " ", m.group(2))
    assert re.search(r"System healthy|Needs a look|Needs attention", text), text
    assert "operational" not in text.lower() and "operational" not in _rail(h).lower()
    assert 'class="hdot" aria-hidden="true"' in m.group(0)


# --- the page makes no writes ------------------------------------------------------

def test_every_tab_renders_with_every_storage_write_raising(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("/admin/ops must not write")
    for name in ("put", "put_json", "update_json", "delete"):
        monkeypatch.setattr(storage, name, boom)
    for key in KEYS:
        assert _page(f"?tab={key}").status_code == 200, key


# --- the inline script must not throw where an element is absent --------------------

def test_the_backlog_bars_are_only_drawn_where_they_exist():
    i = TPL.index("function drawBars(group)")
    assert 'if (!document.getElementById("bars")) return;' in TPL[i: i + 400]


# --- the data blob is cut per tab (#1133 step 3) -------------------------------------
# The blob was 438,553 B on every tab (`cycles` 364,803 B, `issues` 65,675 B) while
# only the drill-downs read them. The expectations below are written out, not read
# back from ops_tabs.BLOB_KEYS, so a table edited to ship everything fails here.

WANT_BLOB = {
    "overview": {"repo", "issues", "today_shipped", "today_failed", "today_live",
                 "filed_live", "filed_today", "kpi_rows"},
    "agents": {"repo"},
    "workflows": {"repo"},
    "runs": {"repo", "cycles"},
    "backlog": {"repo", "issues", "by_priority", "by_area", "by_type"},
    "analytics": {"repo"},
    "monitoring": {"repo"},
}


def _blob(html_text: str) -> dict:
    import json
    m = re.search(r'<script type="application/json" id="ops-data">(.*?)</script>', html_text, re.S)
    assert m, "no ops-data blob"
    return json.loads(m.group(1).replace("<\\/", "</"))


@pytest.mark.parametrize("key", KEYS)
def test_each_tab_ships_only_the_blob_keys_its_drill_downs_read(key):
    assert set(_blob(_page(f"?tab={key}").text)) == WANT_BLOB[key]


def test_cycles_ride_only_on_runs_and_issues_only_on_overview_and_backlog():
    for key in KEYS:
        b = _blob(_page(f"?tab={key}").text)
        assert ("cycles" in b) == (key == "runs"), key
        assert ("issues" in b) == (key in ("overview", "backlog")), key


def test_an_unknown_tab_ships_overviews_blob():
    assert set(_blob(_page("?tab=zzz").text)) == WANT_BLOB["overview"]


def test_the_cut_blob_makes_the_page_smaller_not_just_the_json():
    full = len(_page("?tab=runs").content)
    for key in ("agents", "workflows", "analytics", "monitoring"):
        r = _page(f"?tab={key}")
        assert len(r.text.split('id="ops-data">', 1)[1].split("</script>", 1)[0]) < 1024, key
        assert len(r.content) < full, key


def test_every_drill_down_that_a_tab_renders_has_its_data_on_that_tab():
    for key in KEYS:
        h = _page(f"?tab={key}").text
        body, b = _body(h), _blob(h)
        if "day-btn" in body:
            assert "cycles" in b and b["cycles"], f"{key}: .day-btn rows but no cycles"
            days = set(re.findall(r'data-day="([^"]+)"', body))
            assert days, key
        if 'id="bars"' in body:
            assert "issues" in b and {"by_priority", "by_area", "by_type"} <= set(b), key
        for tile, need in (("today-shipped", "today_shipped"), ("today-filed", "filed_today"),
                           ("today-failed", "today_failed"), ("backlog", "issues"),
                           ("kpi-cycles", "kpi_rows"), ("kpi-prs", "kpi_rows"),
                           ("kpi-qa", "kpi_rows"), ("kpi-cost", "kpi_rows"),
                           ("kpi-prs-day", "kpi_rows")):
            if f'data-drill="{tile}"' in body:
                assert need in b, f"{key}: tile {tile} but no {need}"


def test_the_runs_tab_has_day_rows_and_the_backlog_tab_has_bars_so_the_check_above_bites():
    assert "day-btn" in _body(_page("?tab=runs").text)
    assert 'id="bars"' in _body(_page("?tab=backlog").text)
    assert 'data-drill="backlog"' in _body(_page("?tab=overview").text)
    assert 'data-drill="kpi-cost"' in _body(_page("?tab=overview").text)


def test_the_script_guards_every_blob_key_that_a_tab_may_omit():
    script = TPL[TPL.index("var D = JSON.parse"): TPL.index("function esc(s)")]
    assert "D.cycles || []" in script and "D.issues || []" in script
    assert "D.kpi_rows || []" in script
    tail = TPL[TPL.index("function esc(s)"): TPL.index("Agents right now: re-read")]
    unguarded = re.findall(r"\bD\.(?:cycles|issues|today_shipped|today_failed|filed_today|kpi_rows)\b(?!\s*\|\|)", tail)
    assert not unguarded, f"unguarded read of an omittable key: {unguarded}"
    assert "D[GROUPS[group]] || {}" in tail


def test_blob_for_cuts_a_full_dict_and_unknown_falls_back_to_overview():
    full = {k: 1 for k in ("repo", "cycles", "issues", "today_shipped", "today_failed",
                           "today_live", "filed_live", "filed_today", "by_priority",
                           "by_area", "by_type", "kpi_rows")}
    assert set(ops_tabs.blob_for("runs", full)) == {"repo", "cycles"}
    assert set(ops_tabs.blob_for("nope", full)) == set(ops_tabs.blob_for("overview", full))
    assert "cycles" not in ops_tabs.blob_for("overview", full)
    assert "kpi_rows" in ops_tabs.blob_for("overview", full)
    assert all("kpi_rows" not in ops_tabs.blob_for(k, full) for k in KEYS if k != "overview")


# --- CSS tokens --------------------------------------------------------------------

def _css() -> str:
    return TPL[TPL.index("<style>"): TPL.index("</style>")]


def _blocks(css: str):
    """(light, dark): the LAST top-level :root, and the dark media :root."""
    no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    dark = re.search(r"@media \(prefers-color-scheme:dark\)\{\s*:root\{([^}]*)\}\s*\}", no_comments)
    assert dark, "no prefers-color-scheme:dark :root block"
    rest = no_comments.replace(dark.group(0), "")
    roots = re.findall(r":root\{([^}]*)\}", rest)
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", roots[-1])), \
        dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", dark.group(1)))


def test_the_last_root_is_complete_and_dark_redefines_all_of_it():
    light, dark = _blocks(_css())
    css = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    used = set(re.findall(r"var\((--[a-z0-9-]+)", css)) | set(re.findall(r"var\((--[a-z0-9-]+)", TPL))
    # --heat and --st are per-element properties (set inline / per state class), not theme tokens.
    used -= {"--heat", "--st"}
    assert not used - set(light), f"used but not in the last :root: {sorted(used - set(light))}"
    colour_only = {k for k in light if not k.startswith(("--ui", "--mono", "--r-"))}
    assert not colour_only - set(dark), f"dark does not redefine: {sorted(colour_only - set(dark))}"
    assert set(dark) <= set(light), f"token only in the dark block: {sorted(set(dark) - set(light))}"


def test_no_rule_carries_a_literal_colour():
    css = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    css = re.sub(r":root\{[^}]*\}", "", css)
    bad = re.findall(r"[^{};]*(?:#[0-9a-fA-F]{3,8}\b|rgba?\()[^;}]*", css)
    assert not bad, bad[:5]


def _lum(h: str) -> float:
    h = h.lstrip("#")
    v = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    v = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def _ratio(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _over(fg: str, bg: str) -> str:
    """Composite an rgba() token over an opaque hex."""
    m = re.match(r"rgba\((\d+),(\d+),(\d+),([\d.]+)\)", fg.replace(" ", ""))
    if not m:
        return fg
    a = float(m.group(4))
    c = [int(m.group(i)) for i in (1, 2, 3)]
    b = [int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(a * x + (1 - a) * y) for x, y in zip(c, b))


TEXT = ["ink", "ink-dim", "ink-mute", "shipped", "open", "failed", "judged", "nothing-text", "accent", "link"]
SURFACES = ["ground", "panel", "panel-2", "panel-3"]


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_text_token_clears_AA_on_every_surface(theme):
    light, dark = _blocks(_css())
    t = light if theme == "light" else {**light, **dark}
    low = []
    for name in TEXT:
        for s in SURFACES:
            r = _ratio(t[f"--{name}"], t[f"--{s}"])
            if r < 4.5:
                low.append((name, s, round(r, 2)))
    assert not low, f"{theme}: text under 4.5:1: {low}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_tinted_status_chips_and_alerts_clear_AA(theme):
    light, dark = _blocks(_css())
    t = light if theme == "light" else {**light, **dark}
    panel = t["--panel"]
    pairs = [
        ("red-sev", _over(t["--red-chip"], _over(t["--red-wash-a"], panel))),
        ("red-t", _over(t["--red-wash-a"], panel)),
        ("amber-t", _over(t["--amber-chip"], panel)),
        ("amber-t", _over(t["--amber-wash-a"], panel)),
        ("live-fg", _over(t["--live-bg"], panel)),
        ("failed", _over(t["--red-wash-a"], panel)),
    ]
    low = [(n, round(_ratio(t[f"--{n}"], bg), 2)) for n, bg in pairs if _ratio(t[f"--{n}"], bg) < 4.5]
    assert not low, f"{theme}: {low}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_fills_and_controls_clear_3_to_1_and_on_brand_text_clears_AA(theme):
    light, dark = _blocks(_css())
    t = light if theme == "light" else {**light, **dark}
    assert _ratio(t["--on-brand"], t["--brand"]) >= 4.5
    for s in ("panel", "panel-2"):
        assert _ratio(t["--control"], t[f"--{s}"]) >= 3, ("control", s)
        assert _ratio(t["--brand"], t[f"--{s}"]) >= 3, ("brand", s)
        for c in ("c2", "c3", "c4", "c5", "shipped", "open", "failed", "judged", "nothing"):
            assert _ratio(t[f"--{c}"], t[f"--{s}"]) >= 3, (c, s, theme)


def test_the_owners_violet_is_the_fill_and_never_the_text():
    light, _ = _blocks(_css())
    assert light["--brand"].lower() == "#6c5ce7"
    assert light["--accent"].lower() != "#6c5ce7"  # 4.09:1 on --panel-3, so text uses --accent
    assert light["--ground"].lower() == "#f8fafc"


# --- Gate 6 of scripts/verify_contrast.py (#1133 step 4) ---------------------------
# The gate is the same arithmetic as the tests above, run by the verify_* sweep.
# These pin that it passes on the real page and FAILS on each defect it names, so a
# gate that quietly matches nothing is caught here.

def _gate6():
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("verify_contrast_g6", root / "scripts" / "verify_contrast.py")
    vc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vc)
    return vc


def _gate6_on(monkeypatch, tmp_path, edit) -> list[str]:
    vc = _gate6()
    p = tmp_path / "admin_ops.html"
    edited = edit(TPL)
    assert edited != TPL, "the edit changed nothing, so this test proves nothing"
    p.write_text(edited)
    monkeypatch.setattr(vc, "OPS_HTML", p)
    return vc.gate_6_ops_tokens()


def _last(t: str, old: str, new: str) -> str:
    """Replace the LAST occurrence: the final :root and the dark block are the last."""
    i = t.rindex(old)
    return t[:i] + new + t[i + len(old):]


def test_gate_6_passes_on_the_real_page():
    assert _gate6().gate_6_ops_tokens() == []


def test_gate_6_fails_on_a_text_token_under_AA(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: _last(t, "--ink-dim:#475569", "--ink-dim:#aab4c3"))
    assert any("--ink-dim" in x and "4.5" in x for x in f), f


def test_gate_6_fails_on_a_dark_token_under_AA(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: _last(t, "--ink:#f1f3f7", "--ink:#2a3140"))
    assert any(x.startswith("dark:") and "--ink" in x for x in f), f


def test_gate_6_fails_on_a_fill_under_3_to_1(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: _last(t, "--control:#64748b", "--control:#dde3ea"))
    assert any("--control" in x and "3.0:1" in x for x in f), f


def test_gate_6_fails_on_a_var_missing_from_the_final_root(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: _last(t, " --link-hover:#3d2fa8;", ""))
    assert any("--link-hover" in x and "not defined" in x for x in f), f


def test_gate_6_fails_when_dark_stops_redefining_a_token(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: _last(t, " --failed:#f06a55;", ""))
    assert any("dark block does not redefine --failed" in x for x in f), f


def test_gate_6_fails_on_a_literal_colour_in_a_rule(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: t.replace(
        "html,body{background:var(--ground);color:var(--ink)}",
        "html,body{background:var(--ground);color:#123456}", 1))
    assert any("literal colour" in x for x in f), f


def test_gate_6_fails_when_the_dark_block_is_gone(monkeypatch, tmp_path):
    f = _gate6_on(monkeypatch, tmp_path, lambda t: t.replace(
        "@media (prefers-color-scheme:dark){\n  :root{", "@media (prefers-color-scheme:light){\n  :root{", 1))
    assert f and "prefers-color-scheme:dark" in f[0], f


def test_gate_6_is_registered_in_main_and_the_whole_script_passes(capsys, monkeypatch, tmp_path):
    vc = _gate6()
    assert vc.main() == 0
    out = capsys.readouterr().out
    assert "Gate 6 - /admin/ops tokens" in out and "PASS      Gate 6" in out
    # Registered, not just titled: a broken page must turn main() red.
    p = tmp_path / "admin_ops.html"
    p.write_text(_last(TPL, "--ink:#f1f3f7", "--ink:#2a3140"))
    monkeypatch.setattr(vc, "OPS_HTML", p)
    assert vc.main() == 1
    assert "FAIL      Gate 6" in capsys.readouterr().out


def test_main_exits_2_not_a_pass_when_the_ops_template_is_missing(capsys, monkeypatch, tmp_path):
    vc = _gate6()
    monkeypatch.setattr(vc, "OPS_HTML", tmp_path / "nope.html")
    assert vc.main() == 2
    assert "COULD NOT VERIFY" in capsys.readouterr().out
