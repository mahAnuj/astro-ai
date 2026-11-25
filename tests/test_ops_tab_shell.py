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
    "overview": ["Goals and agent decisions", "Where the loop's time went"],
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
