"""The four Results cards on /admin/ops Overview, template half (#1133 slice 2a, step 2).

`tests/test_ops_kpis.py` covers the arithmetic in `ops_kpis.build`. These render
the real page from a fixture whose answers are written out below BY HAND and
recomputed a second, different way in `_recompute`, then read what a visitor
sees: four cards in the owner's order, each with its n and BOTH windows, a delta
that is words and an arrow, no 0 where the honest answer is "unavailable", no KPI
markup on any other tab, and a drill-down whose rows agree with the headline.

Fixture rows are dated RELATIVE TO TODAY (IST), so the fixed window "last 7
complete IST days, ending yesterday" always lands on them. A test that straddles
IST midnight can see a different day; that is a once-a-day, one-second window.

What these cannot see, and nothing else here does either: the drill-down script
(`TILES["kpi-*"]`) runs in a browser. The structural tests at the end pin that
each card's entry reads `KPI_ROWS` and that the PR drill de-duplicates; the
behaviour was exercised in headless Chromium by hand and is not in a gate.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import ops_data, ops_kpis, ops_tabs

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()
IST = timezone(timedelta(hours=5, minutes=30))
OTHER_TABS = [k for k, _ in ops_tabs.TABS if k != "overview"]
LABELS = ["Cycles shipped", "First-pass QA rate", "Cost per successful outcome", "PRs merged"]
DRILLS = ["kpi-cycles", "kpi-qa", "kpi-cost", "kpi-prs"]


def _today() -> datetime:
    return datetime.now(IST).replace(hour=12, minute=0, second=0, microsecond=0)


def _row(offset: int, outcome: str, *, kind: str = "ranked", pr: int | None = None,
         usd: float = 1.0) -> dict:
    """A loop.json row on the IST day `offset` days from today, at 12:00 IST."""
    when = _today() + timedelta(days=offset)
    return {"run": 5000 + abs(offset) * 10 + (pr or 0) % 10, "workflow": "agent-work",
            "date": when.strftime("%Y-%m-%d"),
            "started": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": "schedule", "conclusion": "success", "minutes": 5.0, "issue": None,
            "pr": pr, "outcome": outcome, "attribution": "receipt", "kind": kind,
            "tokens_input": 1, "tokens_output": 2, "tokens_cache_read": 3,
            "tokens_cache_write": 4, "cost_list_usd": usd}


# Current window = today-7 .. today-1; previous = today-14 .. today-8.
ROWS = [
    _row(-7, "shipped", pr=201, usd=2.0),
    _row(-6, "shipped", pr=201, usd=1.0, kind="issue"),      # a second cycle on the same PR
    _row(-5, "shipped", pr=202, usd=3.0),
    _row(-4, "nothing", usd=0.5),
    _row(-3, "failed", usd=0.5),
    _row(-2, "judged", kind="qa-round", pr=201, usd=1.0),
    _row(-1, "shipped", pr=203, usd=1.0),
    _row(-12, "shipped", pr=190, usd=2.0),                  # previous window
    _row(-11, "shipped", pr=191, usd=2.0),
    _row(-10, "nothing", usd=1.0),
    _row(-9, "judged", kind="qa-round", pr=190, usd=1.0),
    _row(0, "shipped", pr=204, usd=50.0),                   # today: partial, in neither window
    _row(-30, "unknown", kind="unknown", usd=0.1),          # the file's first row
]
RPI = {"201": ["PASS", "FAIL"], "202": ["FAIL", "PASS"], "203": ["PASS"],
       "190": ["PASS"], "191": ["PASS"]}

# Written out by hand from the rows above:
#   cycles    4 shipped of 6 build cycles          previous 2 of 3          up 100%
#   QA        2 of 3 PRs passed first time = 66.7% previous 2 of 2 = 100%    down 33.3 pp
#   cost      $9.00 over 3 PRs = $3.00             previous $6.00 / 2 = $3.00  flat
#   PRs       3 distinct (201, 202, 203)           previous 2                up 50%
HAND = {"cycles": ("4", 6), "qa": ("66.7%", 3), "cost": ("$3.00", 3), "prs": ("3", 3)}


def _recompute(rows: list[dict], rpi: dict, today: str) -> dict:
    """Same answers, derived differently from `ops_kpis`: dates as a sorted range, set algebra."""
    from datetime import date
    t = date.fromisoformat(today)
    cur = {(t - timedelta(days=i)).isoformat() for i in range(1, 8)}
    inside = [r for r in rows if r["date"] in cur]
    builds = [r for r in inside if r["kind"] != "qa-round"]
    ship = [r for r in builds if r["outcome"] == "shipped"]
    prs = sorted({r["pr"] for r in inside if r["outcome"] == "shipped"} - {None})
    firsts = [rpi[str(p)][0] for p in prs if str(p) in rpi]
    return {"cycles": (str(len(ship)), len(builds)),
            "qa": (f"{firsts.count('PASS') / len(firsts) * 100:.1f}%", len(firsts)),
            "cost": (f"${sum(r['cost_list_usd'] for r in inside) / len(prs):,.2f}", len(prs)),
            "prs": (str(len(prs)), len(prs)),
            "rows": len(inside)}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _serve(monkeypatch, *, loop=True, agents=True, rows=None, rpi=None):
    """Make `ops_data._fetch` return only the files asked for; everything else is absent."""
    stamp = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    files = {}
    if loop:
        files["loop.json"] = {"generated_at": stamp, "rows": ROWS if rows is None else rows}
    if agents:
        files["agents.json"] = {"generated_at": stamp, "loops": [], "agents": {
            "qa": {"rounds_per_issue": RPI if rpi is None else rpi}}}
    monkeypatch.setattr(ops_data, "_fetch", lambda name: files.get(name))


def _page(q: str = ""):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _cards(html: str) -> list[dict]:
    """Each Results card as {key, state, aria, text, num, n, delta, drill}."""
    out = []
    for m in re.finditer(r'<button type="button" class="tile kpi k-(\w+) st-(\w+)" data-drill="([^"]+)"'
                         r'\s+title="([^"]*)" aria-label="([^"]*)">(.*?)</button>', html, re.S):
        key, state, drill, title, aria, inner = m.groups()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner)).strip()
        num = re.search(r'<span class="num[^"]*">([^<]*)</span>', inner).group(1)
        n = re.search(r"<b>n=(\d+)</b>", inner)
        delta = re.search(r'<span class="dl[^"]*">([^<]*)</span>', inner).group(1)
        out.append({"key": key, "state": state, "drill": drill, "title": title, "aria": aria,
                    "text": text, "num": num, "n": int(n.group(1)) if n else None,
                    "delta": delta.strip(), "inner": inner})
    return out


def _body(html: str) -> str:
    return re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S)


def _blob(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="ops-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def _days(span: str) -> list[str]:
    """'2026-11-18 → 11-24' (or with a year on the right) as a list of ISO dates."""
    from datetime import date
    m = re.fullmatch(r"(\d{4})-(\d{2}-\d{2}) → (?:(\d{4})-)?(\d{2}-\d{2})", span.strip())
    assert m, span
    a = date.fromisoformat(f"{m.group(1)}-{m.group(2)}")
    b = date.fromisoformat(f"{m.group(3) or m.group(1)}-{m.group(4)}")
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


# --- the cards ---------------------------------------------------------------------

def test_the_fixture_matches_the_hand_computed_answers():
    """Guards the guard: the second derivation and the hand-written table must agree."""
    got = _recompute(ROWS, RPI, _today().strftime("%Y-%m-%d"))
    assert {k: got[k] for k in HAND} == HAND
    assert got["rows"] == 7


def test_four_cards_in_the_owners_order_between_the_objective_and_goals(monkeypatch):
    _serve(monkeypatch)
    h = _page("?tab=overview").text
    cards = _cards(h)
    assert [c["drill"] for c in cards] == DRILLS
    assert [re.search(r'<span class="lbl">([^<]+)</span>', c["inner"]).group(1) for c in cards] == LABELS
    assert h.index('<section class="obj">') < h.index('<section class="panel kpis"') < h.index('id="goals"')
    assert re.search(r"<h2 id=\"kpi-h\">Results\b", h)
    assert h.count('class="panel kpis"') == 1


def test_every_number_shown_equals_an_independent_recompute(monkeypatch):
    _serve(monkeypatch)
    want = _recompute(ROWS, RPI, _today().strftime("%Y-%m-%d"))
    for c in _cards(_page("?tab=overview").text):
        assert c["state"] == "ok", c
        assert (c["num"], c["n"]) == want[c["key"]] == HAND[c["key"]], c["key"]


def test_the_deltas_are_arrows_and_words_and_the_right_way_round(monkeypatch):
    _serve(monkeypatch)
    by = {c["key"]: c for c in _cards(_page("?tab=overview").text)}
    assert by["cycles"]["delta"].startswith("▲ up 100% vs ")
    assert by["prs"]["delta"].startswith("▲ up 50% vs ")
    assert by["qa"]["delta"].startswith("▼ down 33.3 pp vs ")
    assert by["cost"]["delta"].startswith("▬ flat vs ")
    # Colour is the second signal: a fall in first-pass QA is painted bad, a rise in PRs good,
    # an unchanged cost neither.
    assert 'class="dl bad"' in by["qa"]["inner"] and 'class="dl good"' in by["prs"]["inner"]
    assert 'class="dl"' in by["cost"]["inner"]
    for c in by.values():
        assert re.match(r"[▲▼▬] (up|down|flat)\b", c["delta"]), c["delta"]
        assert re.search(r'>was \S+<', c["inner"]), c["key"]


def test_a_rising_cost_is_painted_bad_and_a_falling_one_good(monkeypatch):
    """Cost is the one metric where up is bad, so the page must read `good`, not the direction."""
    cheap_before = [dict(r, cost_list_usd=0.5) if r["date"] < _row(-8, "x")["date"] else r for r in ROWS]
    _serve(monkeypatch, rows=cheap_before)
    cost = {c["key"]: c for c in _cards(_page("?tab=overview").text)}["cost"]
    assert cost["delta"].startswith("▲ up ") and 'class="dl bad"' in cost["inner"]
    dear_before = [dict(r, cost_list_usd=9.0) if r["date"] < _row(-8, "x")["date"] else r for r in ROWS]
    _serve(monkeypatch, rows=dear_before)
    cost = {c["key"]: c for c in _cards(_page("?tab=overview").text)}["cost"]
    assert cost["delta"].startswith("▼ down ") and 'class="dl good"' in cost["inner"]


def test_every_card_carries_n_and_both_windows_of_equal_length(monkeypatch):
    _serve(monkeypatch)
    today = _today().date()
    span = r"\d{4}-\d{2}-\d{2} → (?:\d{4}-)?\d{2}-\d{2}"
    for c in _cards(_page("?tab=overview").text):
        assert c["n"] is not None and c["n"] > 0, c["key"]
        windows = re.findall(span, c["text"])
        assert len(windows) == 2, (c["key"], windows)       # the window line, then the delta's
        cur, prev = _days(windows[0]), _days(windows[-1])
        assert len(cur) == len(prev) == ops_kpis.WINDOW_DAYS == 7, c["key"]
        assert cur[-1] == (today - timedelta(days=1)).isoformat(), "the window ends yesterday"
        assert (prev[-1], cur[0]) == ((today - timedelta(days=8)).isoformat(),
                                      (today - timedelta(days=7)).isoformat()), "adjacent"
        # the title and aria-label carry the same summary
        assert c["title"] in c["aria"] and "Opens the rows behind it" in c["aria"]
        assert c["num"] in c["aria"] and windows[0] in c["aria"]


def test_the_cost_card_says_list_price_and_never_spend_and_prs_say_loop_cycles(monkeypatch):
    _serve(monkeypatch)
    by = {c["key"]: c for c in _cards(_page("?tab=overview").text)}
    assert "list price" in by["cost"]["text"]
    assert len(re.findall(r"spend", by["cost"]["text"])) == len(re.findall(r"not spend", by["cost"]["text"]))
    assert "shipped by loop cycles" in by["prs"]["text"]
    assert "build cycles shipped" in by["cycles"]["text"]


def test_the_captions_name_the_fixed_window_and_the_panel_that_differs(monkeypatch):
    _serve(monkeypatch)
    h = _body(_page("?tab=overview").text)
    i = h.index('<section class="panel kpis"')
    sec = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h[i: h.index("</section>", i)]))
    assert ops_kpis.build({"today_ist": "2026-11-25", "loop": {"ok": False},
                           "agents": {}})["caption"] == ""        # the unavailable shape has none
    assert "complete IST days, ending yesterday" in sec and "range picker does not move" in sec
    assert "Where the loop's time went" in sec and "rolling week" in sec
    assert "measurements/loop.json" in sec and "measurements/agents.json" in sec
    assert "cycle data" in sec


# --- states: unavailable is never a 0 ------------------------------------------------

def test_without_agents_json_the_qa_card_says_unavailable_and_prints_no_zero_percent(monkeypatch):
    _serve(monkeypatch, agents=False)
    r = _page("?tab=overview")
    assert r.status_code == 200
    by = {c["key"]: c for c in _cards(r.text)}
    qa = by["qa"]
    assert qa["state"] == "unavailable" and qa["num"] == "unavailable" and qa["n"] is None
    assert "unavailable: agents.json not read" in qa["text"]
    assert "0%" not in qa["text"] and "0.0%" not in qa["text"]
    assert [k for k, c in by.items() if c["state"] != "ok"] == ["qa"]     # the other three still read


def test_without_loop_json_the_page_renders_four_unavailable_cards_and_the_footer_names_the_file(monkeypatch):
    _serve(monkeypatch, loop=False)
    r = _page("?tab=overview")
    assert r.status_code == 200
    cards = _cards(r.text)
    assert [c["drill"] for c in cards] == DRILLS
    for c in cards:
        assert c["state"] == "unavailable" and c["num"] == "unavailable" and c["n"] is None
        assert "unavailable: loop.json not read" in c["text"]
        assert not re.search(r"(?<![\w.])0(?![\w.])", c["text"].replace("loop.json", "")), c["text"]
    foot = re.search(r'<footer class="prov">(.*?)</footer>', r.text, re.S).group(1)
    assert re.search(r"Unavailable:[^<]*loop\.json", foot)
    assert 'role="status"' in r.text and "The four cards are unavailable, not zero" in r.text


def test_an_unavailable_or_empty_card_never_prints_a_bare_zero(monkeypatch):
    # no PR shipped in the window: PRs is a measured 0, cost and QA have nothing to divide
    rows = [r for r in ROWS if r["outcome"] != "shipped"]
    _serve(monkeypatch, rows=rows)
    by = {c["key"]: c for c in _cards(_page("?tab=overview").text)}
    for key in ("qa", "cost"):
        assert by[key]["state"] != "ok", key
        assert by[key]["num"] in ("no PRs", "unavailable"), (key, by[key]["num"])
        assert by[key]["n"] is None and "0%" not in by[key]["text"]
    assert by["prs"]["state"] == "ok" and by["prs"]["num"] == "0" and by["prs"]["n"] == 0  # a measured zero
    assert by["cycles"]["num"] == "0"


def test_a_window_with_no_runs_is_empty_not_zero(monkeypatch):
    _serve(monkeypatch, rows=[_row(-30, "unknown", kind="unknown")])
    for c in _cards(_page("?tab=overview").text):
        assert c["state"] == "empty" and c["num"] in ("no runs", "no PRs"), c
        assert c["n"] is None


# --- one tab only -------------------------------------------------------------------

@pytest.mark.parametrize("tab", OTHER_TABS)
def test_no_other_tab_has_a_results_section(tab):
    # The committed measurement files, not `_serve`: the Team panel needs a whole agents.json.
    r = _page(f"?tab={tab}")
    assert r.status_code == 200
    body = _body(r.text)
    assert 'class="panel kpis"' not in body and 'class="tile kpi' not in body
    assert not re.search(r'data-drill="kpi-', body)
    assert "kpi_rows" not in _blob(r.text)


def test_kpi_rows_ride_in_overviews_blob_only_and_agree_with_the_cards(monkeypatch):
    _serve(monkeypatch)
    h = _page("?tab=overview").text
    rows = _blob(h)["kpi_rows"]
    want = _recompute(ROWS, RPI, _today().strftime("%Y-%m-%d"))
    by = {c["key"]: c for c in _cards(h)}
    # the same predicates the drill-down script applies
    cycles = [r for r in rows if r["outcome"] == "shipped" and r["kind"] != "qa-round"]
    prs = {r["pr"] for r in rows if r["outcome"] == "shipped" and r["pr"]}
    assert len(rows) == want["rows"] == 7
    assert str(len(cycles)) == by["cycles"]["num"]
    assert str(len(prs)) == by["prs"]["num"] and len(prs) == by["qa"]["n"] == by["cost"]["n"]
    assert {r["pr"]: r["qa1"] for r in rows if r["pr"] in prs} == {201: "PASS", 202: "FAIL", 203: "PASS"}
    assert len(rows) == 7 and all(set(r) == set(ops_kpis.SLIM_KEYS) for r in rows)


# --- the template carries no arithmetic and no literal number ---------------------------

def test_the_results_block_has_no_arithmetic_and_no_literal_number():
    i = TPL.index("{% if kpis %}")
    block = TPL[i: TPL.index("{% endif %}\n\n  {# ── Goals and agent decisions", i)]
    exprs = re.findall(r"\{\{(.*?)\}\}|\{%(.*?)%\}", block, re.S)
    assert len(exprs) > 20
    for a, b in exprs:
        e = re.sub(r"'[^']*'|\"[^\"]*\"", "''", (a or b).strip(" -"))
        assert not re.search(r"\d", e), f"a literal number in the Results block: {e!r}"
        assert not re.search(r"[+*/]|\|\s*(round|int|float|length|sum|abs)\b", e), f"arithmetic: {e!r}"


# --- CSS and script structure (what a gate can say about a browser-only change) ------------

def _css() -> str:
    return TPL[TPL.index("<style>"): TPL.index("</style>")]


def _rule(sel: str) -> str:
    m = re.search(r"(?m)^" + re.escape(sel) + r"\{([^}]*)\}", _css())
    assert m, f"no rule for {sel}"
    return m.group(1)


def test_the_visually_hidden_class_exists_for_slice_2b():
    body = _rule(".vh")
    assert "position:absolute" in body and "clip:rect(0 0 0 0)" in body and "overflow:hidden" in body


def test_the_card_grid_has_no_padding_and_wraps_by_width():
    body = _rule(".kpi-grid")
    assert "padding" not in body and "margin:" in body
    assert "minmax(min(100%,220px),1fr)" in body          # one column on a phone, never wider than it
    assert "padding:16px" in _rule(".tile.kpi") or "padding:16px" in re.sub(r"\s+", "", _rule(".tile.kpi"))


def test_the_added_css_is_under_3_kb_and_uses_tokens_only():
    css = _css()
    block = css[css.index("/* ── Results: the four KPI cards"):]
    assert len(block.encode()) <= 3 * 1024, len(block.encode())
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", re.sub(r"/\*.*?\*/", "", block, flags=re.S))


def _tiles_block() -> str:
    i = TPL.index('"kpi-cycles":')
    return TPL[i: TPL.index("Array.prototype.forEach.call(document.querySelectorAll(\"[data-drill]\")", i)]


@pytest.mark.parametrize("key", DRILLS)
def test_each_kpi_card_has_a_drill_entry_that_reads_the_kpi_rows(key):
    block = _tiles_block()
    entry = re.search(rf'"{key}":(.*?)(?=\n    "kpi-|\n  \}};)', block, re.S).group(1)
    assert "KPI_ROWS" in entry or "kpiPrs" in entry, entry
    assert '"cycle"' in entry                       # the renderer that prints first QA and list cost


def test_the_pr_drill_has_one_row_per_pr_and_the_cost_drill_has_every_row():
    block = _tiles_block()
    fn = block[block.index("function kpiPrs()"):]
    assert "|| seen[r.pr]) return false;" in fn and 'r.outcome !== "shipped"' in fn
    cost = re.search(r'"kpi-cost":(.*?)\n  \};', block, re.S).group(1)
    assert "return KPI_ROWS;" in cost and "filter" not in cost


def test_the_cycle_renderer_adds_first_qa_and_list_cost_without_touching_other_rows():
    i = TPL.index('if (kind === "cycle") {')
    seg = TPL[i: i + 900]
    assert 'bits.push("first QA " + r.qa1)' in seg and 'r.kind !== "qa-round"' in seg
    assert 'r.usd != null' in seg and '" list"' in seg


# --- size ---------------------------------------------------------------------------

def test_the_real_overview_render_stays_under_the_issues_cap():
    """418,318 B is the cap the issue set for the whole page. Overview is about 230 KB with
    the committed files; the per-tab figures are measured and reported, not pinned."""
    assert len(_page("?tab=overview").content) <= 418_318
