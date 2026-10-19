"""The Token budget panel takes a day / week / month window.

WHY THIS FILE EXISTS
--------------------
The panel was pinned to 7 days. `_app_view(days)` had always taken the
parameter; nothing offered it to the reader. Owner's request, 2026-10-18:
"we should have a filter on Token budget in ops dashboard to see daily,
weekly or monthly stats".

Three things are asserted because all three can go wrong quietly, and quiet is
the only way that matters on a page whose job is to be believed:

  1. 30 IS A CEILING, NOT A CHOICE. `events.EVENT_RETENTION_DAYS` is 30 and
     `events.recent()` clamps to it, so a larger window returns 30 days of
     data under a heading claiming more. The window is an explicit SET and an
     unknown value falls back to the default rather than being clamped.

  2. THE CACHE MUST BE KEYED BY WINDOW. `_app_cache` was a single slot, which
     was correct while `days` was hard-coded and becomes a bug the moment it
     is not: the first render populates it and every other window is served
     that same answer for 60 seconds, under its own heading. Found while
     building this, not in production.

  3. A MISTYPED URL MUST NOT TAKE THE PAGE DOWN. Declared as an `int`
     parameter, `?window=abc` answers 422 and the whole control room is a
     validation error page.

Hermetic: no network, per conftest. The GCS-backed figures are whatever the
local store yields; these tests assert on the WINDOW, never on a token count.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from astro_ai import events, ops_data  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    """No live fetches, and no cache carried between windows or tests."""
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _page(window: str | None = None):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    q = "" if window is None else f"?window={window}"
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


# --------------------------------------------------------------------------- #
# The window itself
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("days", [1, 7, 30])
def test_each_offered_window_is_honoured(days):
    assert ops_data.snapshot(app_days=days)["app"]["days"] == days


def test_the_default_is_unchanged_at_seven_days():
    """A filter that moved the default would make every figure on the page
    incomparable with the ones already recorded in ARCHITECTURE.md."""
    assert ops_data.DEFAULT_APP_DAYS == 7
    assert ops_data.snapshot()["app"]["days"] == 7


def test_the_offered_windows_stay_inside_the_retention_ceiling():
    """Any window above EVENT_RETENTION_DAYS would be labelled, not measured."""
    assert max(ops_data.APP_WINDOWS) <= events.EVENT_RETENTION_DAYS


@pytest.mark.parametrize("bad", [0, -1, 3650, 14, 365])
def test_an_unoffered_window_falls_back_rather_than_being_clamped(bad):
    """Clamping 3650 to 30 would render a month of data as a decade of it."""
    assert ops_data.snapshot(app_days=bad)["app"]["days"] == ops_data.DEFAULT_APP_DAYS


# --------------------------------------------------------------------------- #
# The cache — the bug this change would otherwise have introduced
# --------------------------------------------------------------------------- #

def test_two_windows_do_not_share_one_cache_slot():
    """The single-slot cache served window A's figures under window B's heading.

    Asserted on `days` rather than on a token count so the test says what it
    means: this is about which window answered, not how busy the app was.
    """
    a = ops_data._app_view(1)
    b = ops_data._app_view(30)
    assert a["days"] == 1 and b["days"] == 30
    assert ops_data._app_view(1)["days"] == 1, "the 1d entry was evicted by 30d"


def test_the_same_window_twice_is_served_from_cache():
    """The 60s TTL is what keeps a reload off GCS; without it the filter turns
    every click into a fresh bucket read."""
    first = ops_data._app_view(7)
    assert ops_data._app_view(7) is first


# --------------------------------------------------------------------------- #
# The page
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("q,expected", [("1", "1"), ("7", "7"), ("30", "30")])
def test_the_heading_states_the_window_it_is_showing(q, expected):
    h = _page(q).text
    assert re.search(rf"last {expected} d", h), f"heading does not say {expected}d"


@pytest.mark.parametrize("junk", ["abc", "", "-1", "3650", "7; DROP TABLE"])
def test_a_mistyped_window_renders_the_default_page_not_an_error(junk):
    """Declared as `int`, FastAPI answers 422 and the control room is gone."""
    r = _page(junk)
    assert r.status_code == 200, f"{junk!r} gave HTTP {r.status_code}"
    assert re.search(r"last 7 d", r.text)


def test_exactly_one_window_is_marked_selected():
    on = re.findall(r'class="win on"[^>]*>([a-z]+)<', _page("30").text)
    assert on == ["month"], on


def test_every_offered_window_has_a_link_on_the_page():
    h = _page().text
    for d in ops_data.APP_WINDOWS:
        assert f'href="?window={d}"' in h, f"no link for {d}d"


def test_the_template_offers_exactly_the_windows_the_module_declares():
    """The list is passed through, never written twice.

    A hardcoded list in the template is how a fourth window would appear on
    the page that `snapshot` then refuses and silently renders as 7.
    """
    h = _page().text
    assert len(re.findall(r'href="\?window=\d+"', h)) == len(ops_data.APP_WINDOWS)


# --------------------------------------------------------------------------- #
# The alert strip follows the window, and says so
# --------------------------------------------------------------------------- #

def test_an_app_alert_names_the_window_it_was_measured_over():
    """A rate is a rate OVER a window.

    A 30-day error rate sitting above a 1-day table is two different claims
    stacked on each other, and the reader has nothing to tell them apart.
    """
    alerts = ops_data.snapshot(app_days=1)["alerts"]
    app_alerts = [a for a in alerts
                  if "erroring" in a["title"] or "Error rate" in a["title"]
                  or "provider fail" in a["title"] or "size limit" in a["title"]]
    if not app_alerts:
        pytest.skip("no LLM activity in the local store, so no app alert to check")
    assert all("1d" in a["title"] or "1d" in a["detail"] or "1 days" in a["detail"]
               for a in app_alerts), app_alerts


# --------------------------------------------------------------------------- #
# The per-feature trend chart
#
# Owner's request, 2026-10-18: "would be great to see the token budget trend
# graph for last N days features wise".
#
# NO NEW INSTRUMENTATION: `call_by_route` has carried per-day input and output
# tokens since #355 and `range_summary` already reads every blob in the window.
# The figures below are therefore assertions about ARITHMETIC and ORDER, never
# about how busy the app was.
# --------------------------------------------------------------------------- #

def _rng(*days_):
    """A `range_summary`-shaped doc. NEWEST FIRST, as the real one returns.

    A route's value is either an int -- input tokens, no output -- or an
    `(input, output)` pair.

    THE PAIR FORM EXISTS BECAUSE THE INT FORM COULD NOT FAIL. Every fixture in
    this file wrote `"output_tokens": 0`, so nothing here covered the thing the
    panel is FOR: Groq's 8,000 TPM and 200,000 TPD both count input + output,
    and `_token_trend` sums both in two separate places. QA round 1 dropped the
    output term from each and the whole suite stayed green -- the same class as
    the tied sort keys below and as #418's `_pr` omitting `closed_at`: the
    fixture, not the assertion, was what could not fail.
    """
    def tok(v):
        i, o = v if isinstance(v, tuple) else (v, 0)
        return {"input_tokens": i, "output_tokens": o}
    return {"days": [{"date": d, "route_tokens": {
        r: tok(v) for r, v in routes.items()}}
        for d, routes in reversed(days_)]}


def test_the_stack_sums_to_the_underlying_blobs():
    """Grouping into "other" must never lose a token.

    A chart whose bars do not add up to the table beside it teaches the reader
    to distrust both.
    """
    rng = _rng(("2026-10-01", {"a": (10, 2), "b": (5, 1)}),
               ("2026-10-02", {"a": (7, 3), "c": (3, 4)}))
    tr = ops_data._token_trend(rng, 2)
    # 25 input + 10 output. Output is in the figure because the limit counts it;
    # an input-only total reads as headroom the budget does not have.
    assert sum(s["total"] for s in tr["series"]) == 35


def test_the_ranking_is_by_total_tokens_not_input():
    """The order of the legend must be the order of the BUDGET consumed.

    `_token_trend` sums input + output twice over -- once into `totals`, which
    ranks the features and assigns the colours, and once per day into
    `by_feature`, which draws them. Dropping the output term from the ranking
    pass changes nothing a fixture with `output_tokens: 0` can see, so this
    picks figures where the two orders DISAGREE: by input alone `b` (50) leads
    `a` (1); by total `a` (101) leads `b` (51). No tie anywhere, deliberately.
    """
    rng = _rng(("2026-10-01", {"a": (1, 100), "b": (50, 1)}))
    tr = ops_data._token_trend(rng, 1)
    assert tr["features"] == ["a", "b"]
    assert tr["series"][0]["by_feature"] == {"a": 101, "b": 51}


def test_days_read_left_to_right_oldest_first():
    """`range_summary` walks backwards from today; a chart does not."""
    rng = _rng(("2026-10-01", {"a": 1}), ("2026-10-02", {"a": 2}),
               ("2026-10-03", {"a": 3}))
    tr = ops_data._token_trend(rng, 3)
    assert [s["full_date"] for s in tr["series"]] == [
        "2026-10-01", "2026-10-02", "2026-10-03"]


def test_features_are_ranked_over_the_window_not_per_day():
    """A bar must keep its colour from one day to the next.

    The template colours a segment by its index in `features`. Ranking per day
    would recolour every bar daily and the chart would be unreadable as a
    trend, which is the only thing it is for.
    """
    # NAMES CHOSEN SO ALPHABETICAL ORDER IS THE WRONG ANSWER, and totals chosen
    # so they do not tie. The first version of this test used {a: 100, b: 1}
    # and {a: 1, b: 100} -- equal window totals, so a stable sort preserved
    # insertion order and `sorted(totals)` produced the SAME list. The
    # mutation harness reported MISSED: the assertion could not fail.
    #
    # Here zeta wins the window (110 vs 91) while alpha wins day two (90 vs
    # 10), so this one list distinguishes three implementations: ranked by
    # window total (correct), ranked alphabetically, and ranked per day.
    rng = _rng(("2026-10-01", {"zeta": 100, "alpha": 1}),
               ("2026-10-02", {"zeta": 10, "alpha": 90}))
    tr = ops_data._token_trend(rng, 2)
    assert tr["features"] == ["zeta", "alpha"]
    for s in tr["series"]:
        assert list(s["by_feature"]) == ["zeta", "alpha"], "order moved between days"


def test_beyond_the_top_n_features_are_grouped_never_dropped():
    routes = {f"r{i}": (100 - i) for i in range(10)}
    tr = ops_data._token_trend(_rng(("2026-10-01", routes)), 1)
    assert len(tr["features"]) == ops_data.TREND_TOP_N + 1
    assert tr["features"][-1] == "other"
    assert tr["series"][0]["total"] == sum(routes.values())
    named = sum(tr["series"][0]["by_feature"][f] for f in tr["features"][:-1])
    assert tr["series"][0]["by_feature"]["other"] == sum(routes.values()) - named
    assert tr["grouped"], "the grouped names must be listed on the page"


def test_no_bar_can_overflow_the_axis():
    """`top` is a rounded-up peak, so the tallest stack is <= 100% of it."""
    tr = ops_data._token_trend(_rng(("2026-10-01", {"a": 7, "b": 11})), 1)
    assert tr["top"] >= tr["peak"] > 0
    assert sum(tr["series"][0]["by_feature"].values()) / tr["top"] <= 1.0


def test_a_window_with_no_tokens_is_not_ok_rather_than_a_flat_zero_chart():
    """A chart of zeroes reads as "we spent nothing", not "nothing recorded"."""
    assert ops_data._token_trend(_rng(("2026-10-01", {})), 1)["ok"] is False
    assert ops_data._token_trend({"days": []}, 7)["ok"] is False


def test_the_tpd_reference_is_the_per_model_figure():
    tr = ops_data._token_trend(_rng(("2026-10-01", {"a": 500})), 1)
    assert tr["tpd"] == ops_data.TPD_PER_MODEL


def test_the_unmeasured_zero_state_still_carries_a_trend_key():
    """The template reads ops.app.trend.ok unconditionally.

    The same shape of omission 500'd the whole page from `_loop_view`'s zero
    state earlier today; it is not going to do it twice.
    """
    assert ops_data._app_view(7).get("trend") is not None


# --------------------------------------------------------------------------- #
# The TPD reference line — QA round 1, BUG-1
#
# The line was gated on `top >= TPD_PER_MODEL * 0.25` and its y was CLAMPED
# with `min(TPD_PER_MODEL / top, 1.0)`, which pins it to the top edge for every
# window whose peak is under one bucket — while the legend went on reading
# "200,000 TPD · one model". A 50,000-token day therefore drew a full-height
# bar touching a line labelled 200,000: a 4x overstatement, on the one panel
# whose entire job is to say how much of the budget a day spent.
#
# The existing fixture (peak 500) never drew the line at all, which is why two
# mutants of this arithmetic survived all 705 tests.
# --------------------------------------------------------------------------- #

def test_the_tpd_line_is_not_drawn_when_one_bucket_is_off_the_chart():
    """Below one bucket there is no honest place to put it, so it is absent.

    Nothing is lost by the absence: `peak` is in the legend either way and
    `peak_day_pct` states the same day as a percentage of one bucket in the
    panel above. A clamped line is not a reference, it is decoration carrying
    a number.
    """
    tr = ops_data._token_trend(
        _rng(("2026-10-01", {"a": ops_data.TPD_PER_MODEL // 4})), 1)
    assert tr["top"] < ops_data.TPD_PER_MODEL
    assert tr["tpd_visible"] is False


def test_the_tpd_line_is_drawn_at_the_height_its_label_claims():
    """The line and the bars must be on one scale, or the label is false.

    `top` is 400,000 here, so one bucket is exactly half the axis: a day that
    spent exactly TPD_PER_MODEL must have its bar top land ON the line. That
    equality is the whole property — it fails for any clamp, and it fails for
    a line placed by anything other than the same `top` the bars use.
    """
    tr = ops_data._token_trend(
        _rng(("2026-10-01", {"a": ops_data.TPD_PER_MODEL}),
             ("2026-10-02", {"a": ops_data.TPD_PER_MODEL * 2})), 2)
    assert tr["top"] == ops_data.TPD_PER_MODEL * 2
    assert tr["tpd_visible"] is True
    assert tr["tpd_y"] == 50.0
    day_one = tr["series"][0]
    bar_top = 100 - day_one["total"] / tr["top"] * 100
    assert bar_top == tr["tpd_y"]


# --------------------------------------------------------------------------- #
# The error rate — QA round 1, BUG-2
#
# `events.recent` is newest-first and stops dead at `limit`, so the NUMERATOR
# was capped at 500 while the denominator (`llm_stats` total_calls) grew with
# the window. Widening the window therefore lowered the reported rate on
# identical data, and past ~5,000 calls the 30-day view fell under
# ERROR_RATE_AMBER and the alert vanished entirely — the window with the most
# errors being the one that reported none.
# --------------------------------------------------------------------------- #

def _app_with(n_errors, calls, monkeypatch, days=7):
    """`_app_view` over a store holding `n_errors` errors and `calls` calls.

    `recent` HONOURS `limit` here, as the real one does. A mock that ignored it
    would make the saturation untestable — the defect lives in the cap, so a
    fixture that cannot be capped cannot see it.
    """
    from astro_ai import llm_stats
    store = [{"data": {"error_type": "APITimeoutError", "source": "chart:natal"}}
             for _ in range(n_errors)]
    monkeypatch.setattr(events, "recent",
                        lambda **kw: store[:kw.get("limit", 100)])
    monkeypatch.setattr(llm_stats, "usage_summary",
                        lambda d: {"days": d, "total_calls": calls, "cache_hits": 0,
                                   "cache_misses": calls, "hit_rate_pct": 0,
                                   "total_input_tokens": 0, "total_output_tokens": 0,
                                   "by_route": []})
    monkeypatch.setattr(llm_stats, "range_summary", lambda d: {"days": []})
    ops_data._app_cache.clear()
    return ops_data._app_view(days)


def test_an_unsaturated_read_still_reports_a_rate(monkeypatch):
    app = _app_with(50, 1000, monkeypatch)
    assert app["errors"] == 50
    assert app["errors_truncated"] is False
    assert app["error_rate"] == 5.0


def test_the_rate_is_withheld_rather_than_understated_when_the_read_saturates(monkeypatch):
    """600 errors against 10,000 calls is 6%. Capped at 500 it reads 5.0%.

    5.0% is not merely imprecise — it is the wrong side of ERROR_RATE_RED's
    boundary behaviour for a reader comparing windows, and it moves further
    from the truth the worse the incident gets. So there is no rate.
    """
    app = _app_with(600, 10_000, monkeypatch)
    assert app["errors_truncated"] is True
    assert app["errors"] == ops_data.ERROR_EVENT_LIMIT
    assert app["error_rate"] is None


def test_exactly_the_cap_is_not_reported_as_truncated(monkeypatch):
    """The off-by-one that `limit + 1` exists to settle.

    `len(errors) == limit` is ambiguous — it is the same result for a store
    holding exactly 500 and one holding 5,000 — so one extra is fetched and
    the flag is set on the overflow, not on the equality.
    """
    app = _app_with(ops_data.ERROR_EVENT_LIMIT, 10_000, monkeypatch)
    assert app["errors_truncated"] is False
    assert app["error_rate"] == 5.0


def test_a_saturated_read_alerts_rather_than_going_quiet(monkeypatch):
    """Silence is the failure mode this rate had: no number, no alert.

    The amber/red branches are driven by `rate`, which is None on saturation,
    so without a branch of its own the busiest window would be the calm one.
    """
    app = _app_with(5_000, 100_000, monkeypatch)
    alerts = ops_data._alerts({"ok": True, "rows": [], "today_failed": []},
                              {"ok": True}, {"ok": True}, app, {})
    hit = [a for a in alerts if "error events" in a["title"]]
    assert hit, f"a saturated read raised no alert: {[a['title'] for a in alerts]}"
    assert hit[0]["level"] == "red"
    assert "cannot be computed" in hit[0]["detail"]
