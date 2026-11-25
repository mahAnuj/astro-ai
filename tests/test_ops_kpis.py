"""The four KPI cards on /admin/ops Overview (#1133 slice 2a, backend half).

`ops_kpis.build(ops)` derives Cycles shipped, First-pass QA rate, Cost per
successful outcome and PRs merged from rows `ops_data.snapshot()` already holds.
These tests build synthetic rows whose answers are written out by hand in the
module-level constants below (and recomputed a second, different way in
`_expect`), so a rule changed in the module fails here rather than moving the
expectation with it. Two tests at the end read the real committed files and skip
when they are absent.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from astro_ai import ops_data, ops_kpis  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "collect_loop_measurements_kpis", ROOT / "scripts" / "collect_loop_measurements.py")
cm = importlib.util.module_from_spec(_spec)
sys.modules["collect_loop_measurements_kpis"] = cm
_spec.loader.exec_module(cm)

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = "2026-11-25"           # current window 2026-11-18..24, previous 2026-11-11..17
PREV_TEXT = "2026-11-11 → 11-17"
_ids = itertools.count(1000)


def row(date, outcome, *, kind="ranked", pr=None, usd=1.0, measured=True, **extra):
    """A `ops["loop"]["rows"]` row: `date_ist` is what `_loop_view` adds."""
    r = {"run": next(_ids), "date_ist": date, "time_ist": "12:00",
         "started": f"{date}T06:30:00Z",          # 12:00 IST on `date`
         "outcome": outcome, "kind": kind, "pr": pr, "issue": None, "minutes": 5.0,
         "trigger": "schedule", "attribution": "receipt"}
    if measured:
        r.update(tokens_input=1, tokens_output=2, tokens_cache_read=3, tokens_cache_write=4,
                 cost_list_usd=usd)
    r.update(extra)
    return r


def ops(rows, rpi=None, *, loop_ok=True, agents_ok=True, today=TODAY):
    qa = {"qa": {"rounds_per_issue": rpi}} if rpi is not None else {}
    return {"today_ist": today,
            "loop": {"ok": loop_ok, "rows": rows},
            "agents": {"ok": agents_ok, "agents": qa},
            "ages": {"Delivery": {"text": "3h ago", "stale": False, "at_ist": "25 Nov 17:58"}}}


def base_rows(*, h_measured=True):
    """The dataset every hand-written expectation below refers to."""
    return [
        # --- current window, 2026-11-18..24
        row("2026-11-18", "shipped", pr=101, usd=2.0),
        row("2026-11-19", "shipped", pr=101, usd=1.0, kind="issue"),   # same PR, second cycle
        row("2026-11-20", "shipped", pr=102, usd=3.0),
        row("2026-11-21", "nothing", usd=0.5),
        row("2026-11-22", "failed", usd=0.5),
        row("2026-11-23", "judged", kind="qa-round", pr=101, usd=1.0),
        row("2026-11-24", "judged", kind="qa-round", pr=102, usd=1.0),
        row("2026-11-24", "shipped", pr=103, usd=1.0, measured=h_measured),
        # --- previous window, 2026-11-11..17
        row("2026-11-12", "shipped", pr=90, usd=2.0),
        row("2026-11-13", "shipped", pr=91, usd=2.0),
        row("2026-11-11", "nothing", usd=1.0),
        row("2026-11-17", "judged", kind="qa-round", pr=90, usd=1.0),
        # --- outside both windows: today (partial) and the day before the previous one
        row("2026-11-25", "shipped", pr=104, usd=50.0),
        row("2026-11-10", "shipped", pr=80, usd=50.0),
        # --- the first row of the data, so the previous window does not predate it
        row("2026-10-08", "unknown", kind="unknown", usd=0.1),
    ]


RPI = {"101": ["PASS", "FAIL"], "102": ["FAIL", "PASS"],      # first verdicts: PASS, FAIL
       "90": ["PASS"], "91": ["PASS", "FAIL", "PASS"]}        # previous: PASS, PASS


def card(k, key):
    return next(c for c in k["cards"] if c["key"] == key)


def _expect(rows, rpi, lo, hi):
    """A second computation, by plain loops over date strings. Returns
    (build cycles, shipped build cycles, distinct shipped PRs, first-pass PASS count,
    PRs with a verdict, list-price sum of measured runs, runs, measured runs)."""
    in_win = [r for r in rows if lo <= r["date_ist"] <= hi]
    builds = shipped = 0
    prs = set()
    usd = 0.0
    measured = 0
    for r in in_win:
        if r["kind"] != "qa-round":
            builds += 1
            if r["outcome"] == "shipped":
                shipped += 1
        if r["outcome"] == "shipped" and r["pr"]:
            prs.add(r["pr"])
        if "tokens_input" in r:
            measured += 1
            usd += r["cost_list_usd"]
    verdicts = [rpi[str(p)][0] for p in sorted(prs) if str(p) in rpi]
    return (builds, shipped, len(prs), verdicts.count("PASS"), len(verdicts),
            round(usd, 2), len(in_win), measured)


# --- the windows -------------------------------------------------------------------

@pytest.mark.parametrize("today", ["2026-11-25", "2027-01-02", "2026-03-01", "2028-03-01"])
@pytest.mark.parametrize("days", [1, 3, 7, 14])
def test_the_windows_are_equal_adjacent_and_end_yesterday(today, days):
    cur, prev = ops_kpis.windows(today, days)
    d = datetime.strptime(today, "%Y-%m-%d").date()
    assert len(cur) == len(prev) == days
    assert cur[-1] == (d - timedelta(days=1)).isoformat(), "the current window must end yesterday"
    assert today not in cur + prev, "today is partial and must be left out"
    assert prev[-1] == (datetime.strptime(cur[0], "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
    for w in (cur, prev):
        parsed = [datetime.strptime(x, "%Y-%m-%d").date() for x in w]
        assert [b - a for a, b in zip(parsed, parsed[1:])] == [timedelta(days=1)] * (days - 1)


def test_the_default_window_is_seven_days_and_the_card_names_it():
    assert ops_kpis.WINDOW_DAYS == 7
    k = ops_kpis.build(ops(base_rows(), RPI))
    assert k["window"]["text"] == "2026-11-18 → 11-24"
    assert k["window"]["previous_text"] == PREV_TEXT
    assert all(c["window_text"] == "2026-11-18 → 11-24" for c in k["cards"])


# --- the four values, against the hand-written dataset -------------------------------

def test_the_four_cards_come_in_the_owners_order():
    k = ops_kpis.build(ops(base_rows(), RPI))
    assert [c["key"] for c in k["cards"]] == ["cycles", "qa", "cost", "prs"]
    assert [c["label"] for c in k["cards"]] == [
        "Cycles shipped", "First-pass QA rate", "Cost per successful outcome", "PRs merged"]
    assert k["error"] is False


def test_the_four_values_match_the_hand_computed_answers():
    k = ops_kpis.build(ops(base_rows(), RPI))
    c = {x["key"]: x for x in k["cards"]}
    # 6 build cycles (the two QA rounds are not cycles), 4 shipped; 3 distinct PRs from 4 shipped rows.
    assert (c["cycles"]["value"], c["cycles"]["n"]) == (4, 6)
    assert c["cycles"]["n_text"].startswith("of 6 build cycles")
    assert c["prs"]["value"] == 3
    assert "from 4 shipped cycles" in c["prs"]["n_text"]
    # 101 passed first, 102 failed first, 103 has no verdict: 1 of 2, one PR without.
    assert c["qa"]["value"] == pytest.approx(50.0) and c["qa"]["display"] == "50.0%"
    assert c["qa"]["n"] == 2 and "1 of 2 PRs passed first time; 1 had no verdict" in c["qa"]["n_text"]
    # 10.00 of list price over every run (QA rounds and failures included) / 3 PRs, NOT / 6 cycles.
    assert c["cost"]["value"] == 3.33 and c["cost"]["display"] == "$3.33"
    assert "$10.00 list price over 3 PRs; 8 of 8 runs measured" in c["cost"]["n_text"]
    assert c["cost"]["floor"] is False


def test_the_values_agree_with_a_second_computation():
    rows = base_rows()
    builds, shipped, nprs, passed, nver, usd, runs, measured = _expect(
        rows, RPI, "2026-11-18", "2026-11-24")
    k = ops_kpis.build(ops(rows, RPI))
    assert (card(k, "cycles")["value"], card(k, "cycles")["n"]) == (shipped, builds)
    assert card(k, "prs")["value"] == nprs
    assert card(k, "qa")["value"] == pytest.approx(passed / nver * 100)
    assert card(k, "cost")["value"] == round(usd / nprs, 2)
    assert (runs, measured) == (8, 8)


def test_a_row_dated_today_or_before_both_windows_changes_nothing():
    k = ops_kpis.build(ops(base_rows(), RPI))
    assert card(k, "prs")["value"] == 3 and card(k, "cost")["value"] == 3.33
    assert all(r["date_ist"] != TODAY and "2026-11-18" <= r["date_ist"] <= "2026-11-24"
               for r in k["rows"])


def test_two_cycles_for_one_pr_count_once_in_prs_and_qa_and_twice_in_cycles():
    rows = [row("2026-11-20", "shipped", pr=1470, usd=2.0),
            row("2026-11-21", "shipped", pr=1470, usd=3.0, kind="fix-pr"),
            row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, {"1470": ["FAIL", "PASS"]}))
    assert card(k, "cycles")["value"] == 2 and card(k, "cycles")["n"] == 2
    assert card(k, "prs")["value"] == 1
    assert card(k, "qa")["n"] == 1 and card(k, "qa")["value"] == 0.0
    assert card(k, "cost")["value"] == 5.0      # both cycles' cost, over ONE PR


def test_qa_rounds_are_runs_for_cost_but_not_cycles():
    rows = [row("2026-11-20", "shipped", pr=7, usd=1.0),
            row("2026-11-20", "judged", kind="qa-round", pr=7, usd=4.0),
            row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, {"7": ["PASS"]}))
    assert card(k, "cycles")["n"] == 1
    assert card(k, "cost")["value"] == 5.0


# --- first-pass: the first verdict, and never a 0 for "unknown" ----------------------

def test_first_pass_reads_the_first_verdict_not_the_last():
    rows = [row("2026-11-20", "shipped", pr=1, usd=1.0), row("2026-11-20", "shipped", pr=2, usd=1.0),
            row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, {"1": ["FAIL", "PASS", "PASS"], "2": ["PASS", "FAIL"]}))
    assert card(k, "qa")["value"] == pytest.approx(50.0)
    k = ops_kpis.build(ops(rows, {"1": ["FAIL", "PASS"], "2": ["FAIL", "PASS"]}))
    assert card(k, "qa")["value"] == pytest.approx(0.0), "all failed first time is a real 0%"


@pytest.mark.parametrize("rpi", [{}, {"999": ["PASS"]}, {"1": []}, {"1": ["MAYBE"]}, {"x": ["PASS"]}])
def test_no_verdict_for_any_pr_is_unavailable_never_zero(rpi):
    rows = [row("2026-11-20", "shipped", pr=1), row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, rpi))
    c = card(k, "qa")
    assert k["error"] is False
    assert c["state"] == "unavailable" and c["value"] is None
    assert "0" not in c["display"] and c["display"] == "unavailable"
    assert "1 PRs" in c["n_text"] or "1 PR" in c["n_text"]


def test_a_missing_agents_file_makes_only_the_qa_card_unavailable():
    k = ops_kpis.build(ops(base_rows(), None, agents_ok=False))
    assert card(k, "qa")["state"] == "unavailable"
    assert "agents.json not read" in card(k, "qa")["n_text"]
    assert [card(k, x)["state"] for x in ("cycles", "cost", "prs")] == ["ok"] * 3


def test_agents_read_but_no_rounds_list_says_not_collected():
    k = ops_kpis.build(ops(base_rows(), None))
    assert "rounds_per_issue not collected" in card(k, "qa")["n_text"]


# --- the delta ----------------------------------------------------------------------

def test_the_deltas_are_computed_against_the_previous_window():
    k = ops_kpis.build(ops(base_rows(), RPI))
    # previous: 3 builds / 2 shipped; 2 PRs; first-pass 2 of 2 = 100%; 6.00 / 2 = 3.00
    d = {c["key"]: c["delta"] for c in k["cards"]}
    assert d["cycles"]["text"] == f"▲ up 100% vs {PREV_TEXT} (n=3)"
    assert d["cycles"]["amount"] == 100.0 and d["cycles"]["good"] is True
    assert d["prs"]["text"] == f"▲ up 50% vs {PREV_TEXT} (n=2)" and d["prs"]["good"] is True
    assert d["qa"]["text"] == f"▼ down 50.0 pp vs {PREV_TEXT} (n=2)"
    assert d["qa"]["amount"] == -50.0 and d["qa"]["good"] is False
    assert d["qa"]["previous_text"] == "100.0%"
    # 3.33 against 3.00: +11%, and for cost UP is bad.
    assert d["cost"]["text"] == f"▲ up 11% vs {PREV_TEXT} (n=2)"
    assert d["cost"]["good"] is False and d["cost"]["previous_text"] == "$3.00"
    assert all(x["state"] == "ok" for x in d.values())


def test_a_cost_that_falls_is_good():
    rows = [row("2026-11-20", "shipped", pr=1, usd=1.0), row("2026-11-14", "shipped", pr=2, usd=4.0),
            row("2026-10-08", "unknown", kind="unknown")]
    d = card(ops_kpis.build(ops(rows, {})), "cost")["delta"]
    assert d["direction"] == "down" and d["good"] is True and d["text"].startswith("▼ down 75%")


def test_an_unchanged_value_is_flat_with_no_judgement():
    rows = [row("2026-11-20", "shipped", pr=1), row("2026-11-14", "shipped", pr=2),
            row("2026-10-08", "unknown", kind="unknown")]
    d = card(ops_kpis.build(ops(rows, {})), "prs")["delta"]
    assert d["direction"] == "flat" and d["good"] is None and "flat" in d["text"]


def test_a_previous_window_of_zero_is_not_divided_by():
    rows = [row("2026-11-20", "shipped", pr=1), row("2026-11-14", "nothing"),
            row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, {"1": ["PASS"]}))
    assert k["error"] is False
    for key in ("cycles", "prs"):
        d = card(k, key)["delta"]
        assert d["state"] == "na" and d["text"] == "n/a: previous window had 0", key
    d = card(k, "cost")["delta"]
    assert d["state"] == "na" and d["text"] == "n/a: previous window had 0 PRs"
    # The rate has a previous of None (no verdict), not a division.
    assert card(k, "qa")["delta"]["state"] == "unavailable"


def test_a_previous_window_that_starts_before_the_data_has_no_delta():
    rows = [r for r in base_rows() if r["date_ist"] >= "2026-11-12"]       # data starts 11-12
    k = ops_kpis.build(ops(rows, RPI))
    for c in k["cards"]:
        assert c["delta"]["state"] == "unavailable", c["key"]
        assert c["delta"]["text"] == "unavailable: data starts 2026-11-12", c["key"]
        assert c["state"] == "ok", "the current value is still shown"


def test_a_previous_window_that_starts_exactly_on_the_first_row_is_comparable():
    rows = [r for r in base_rows() if r["date_ist"] >= "2026-11-11"]       # data starts 11-11
    k = ops_kpis.build(ops(rows, RPI))
    assert all(c["delta"]["state"] == "ok" for c in k["cards"])


def test_cost_shows_its_value_but_no_delta_when_a_window_is_partly_measured():
    k = ops_kpis.build(ops(base_rows(h_measured=False), RPI))
    c = card(k, "cost")
    assert c["state"] == "ok" and c["floor"] is True
    assert "7 of 8 runs measured" in c["n_text"] and "a floor" in c["n_text"]
    assert c["delta"]["state"] == "unavailable"
    assert "not fully measured in both windows" in c["delta"]["text"]
    assert card(k, "cycles")["delta"]["state"] == "ok", "counts do not depend on tokens"


def test_a_previous_window_with_an_unmeasured_run_also_blocks_the_cost_delta():
    rows = base_rows()
    rows.append(row("2026-11-15", "nothing", measured=False))
    c = card(ops_kpis.build(ops(rows, RPI)), "cost")
    assert c["delta"]["state"] == "unavailable" and "not fully measured" in c["delta"]["text"]


def test_a_small_sample_is_flagged_and_a_big_one_is_not():
    k = ops_kpis.build(ops(base_rows(), RPI))
    assert all(c["low_n"] and "too few to read" in c["n_text"] for c in k["cards"])
    rows = [row("2026-11-20", "shipped", pr=i, usd=1.0) for i in range(1, 13)]
    rows.append(row("2026-10-08", "unknown", kind="unknown"))
    k = ops_kpis.build(ops(rows, {str(i): ["PASS"] for i in range(1, 13)}))
    assert not any(c["low_n"] or "too few" in c["n_text"] for c in k["cards"])


def test_the_delta_text_never_relies_on_colour_alone():
    k = ops_kpis.build(ops(base_rows(), RPI))
    for c in k["cards"]:
        t = c["delta"]["text"]
        assert t[0] in "▲▼" and ("up" in t or "down" in t), t


# --- degraded input ------------------------------------------------------------------

def test_a_loop_file_that_was_not_read_makes_all_four_unavailable_not_zero():
    k = ops_kpis.build(ops([], RPI, loop_ok=False))
    assert k["error"] is False and k["rows"] == []
    assert len(k["cards"]) == 4
    for c in k["cards"]:
        assert c["state"] == "unavailable" and c["value"] is None
        assert c["n_text"] == "unavailable: loop.json not read"


def test_a_window_with_no_runs_is_empty_not_zero():
    k = ops_kpis.build(ops([row("2026-10-08", "unknown", kind="unknown")], RPI))
    assert [c["state"] for c in k["cards"]] == ["empty"] * 4
    assert all(c["value"] is None for c in k["cards"])


def test_a_window_with_runs_and_no_shipped_pr_has_no_cost_per_pr():
    rows = [row("2026-11-20", "nothing"), row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, RPI))
    assert card(k, "cost")["state"] == "unavailable"
    assert card(k, "cycles")["value"] == 0 and card(k, "prs")["value"] == 0, "a real 0, with n > 0"
    assert card(k, "qa")["state"] == "empty"


GARBAGE = [None, 5, "x", [], {}, {"date_ist": "2026-11-20"}, {"outcome": "shipped"},
           {"date_ist": 5, "outcome": "shipped"}, {"date_ist": "20 Nov", "outcome": "shipped"},
           {"date_ist": "2026-11-20", "outcome": None},
           row("2026-11-20", "shipped", pr=1, cost_list_usd="abc")]


@pytest.mark.parametrize("bad", [None, {}, [], "x", {"loop": None}, {"loop": {}},
                                 {"loop": {"ok": True, "rows": None}},
                                 {"loop": {"ok": True, "rows": [1]}},
                                 {"loop": {"ok": True, "rows": []}, "today_ist": "nonsense"},
                                 {"loop": {"ok": True, "rows": []}, "today_ist": None},
                                 {"loop": {"ok": True, "rows": []}, "today_ist": TODAY, "ages": 5},
                                 {"loop": {"ok": True, "rows": []}, "today_ist": TODAY, "agents": 5}])
def test_build_never_raises_and_always_returns_four_cards(bad):
    k = ops_kpis.build(bad)
    assert len(k["cards"]) == 4 and isinstance(k["rows"], list)


def test_build_reports_an_internal_failure_as_an_error_not_an_exception():
    k = ops_kpis.build(None)
    assert k["error"] is True and "could not be computed" in k["reason"]
    assert all(c["state"] == "unavailable" for c in k["cards"])


def test_garbage_rows_are_skipped_and_counted_and_the_good_row_still_counts():
    good = row("2026-11-20", "shipped", pr=9, usd=2.0)
    k = ops_kpis.build(ops(GARBAGE + [good, row("2026-10-08", "unknown", kind="unknown")], {"9": ["PASS"]}))
    assert k["error"] is False
    assert k["skipped"] == len(GARBAGE), "every garbage row, the bad-cost one included, is counted"
    assert card(k, "prs")["value"] == 1       # pr=1 (bad cost) is skipped; pr=9 counts
    assert card(k, "cost")["value"] == 2.0


def test_a_bool_or_negative_pr_is_not_a_pr():
    rows = [row("2026-11-20", "shipped", pr=True), row("2026-11-20", "shipped", pr=-3),
            row("2026-11-20", "shipped", pr=0), row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, {"1": ["PASS"]}))
    assert card(k, "prs")["value"] == 0 and card(k, "cycles")["value"] == 3


# --- parity with the collector, which is where "distinct PRs" and "measured" come from ---

def _collector_window(rows, today_ist, days, offset=0):
    """`_window_tokens` over the same IST days: [today-days-offset, today-offset) in IST."""
    end_day = datetime.strptime(today_ist, "%Y-%m-%d").replace(tzinfo=IST) - timedelta(days=offset)
    return cm._window_tokens(rows, end_day - timedelta(days=days), end_day)


def test_the_token_fields_are_the_collectors():
    assert ops_kpis._TOKEN_FIELDS == cm.TOKEN_FIELDS


def test_prs_and_cost_match_the_collectors_window_tokens_on_synthetic_rows():
    rows = base_rows()
    k = ops_kpis.build(ops(rows, RPI))
    cur, prev = _collector_window(rows, TODAY, 7), _collector_window(rows, TODAY, 7, offset=7)
    assert card(k, "prs")["value"] == cur["merged"] == 3
    assert card(k, "cost")["value"] == cur["usd_per_pr"]
    assert card(k, "cost")["delta"]["previous_text"] == f"${prev['usd_per_pr']:,.2f}"
    assert card(k, "prs")["delta"]["previous_n"] == prev["merged"] == 2
    assert len(cur["win"]) == 8 and len(cur["measured"]) == 8


# --- the drill rows ------------------------------------------------------------------

def test_drill_rows_are_the_current_window_only_with_the_whitelisted_keys():
    k = ops_kpis.build(ops(base_rows(), RPI))
    assert len(k["rows"]) == 8
    for r in k["rows"]:
        assert tuple(r) == ops_kpis.SLIM_KEYS
    assert {r["pr"] for r in k["rows"]} == {None, 101, 102, 103}


def test_a_drill_row_drops_every_key_that_is_not_whitelisted():
    r = row("2026-11-20", "shipped", pr=5, model="claude", turns=17, agents_called={"qa": 1},
            secret="x", owner_helped=True)
    k = ops_kpis.build(ops([r, row("2026-10-08", "unknown", kind="unknown")], {"5": ["PASS"]}))
    (drill,) = k["rows"]
    assert set(drill) == set(ops_kpis.SLIM_KEYS)
    assert not {"model", "turns", "agents_called", "secret", "tokens_input"} & set(drill)


def test_qa1_is_the_first_verdict_and_only_ever_pass_fail_or_none():
    rows = [row("2026-11-20", "shipped", pr=1), row("2026-11-20", "shipped", pr=2),
            row("2026-11-20", "shipped", pr=3), row("2026-11-20", "nothing"),
            row("2026-10-08", "unknown", kind="unknown")]
    k = ops_kpis.build(ops(rows, {"1": ["FAIL", "PASS"], "2": ["<script>alert(1)</script>"],
                                  "3": ["PASS"]}))
    assert [r["qa1"] for r in k["rows"]] == ["FAIL", None, "PASS", None]


def test_a_maximal_drill_row_fits_in_250_bytes():
    """Long strings are capped, so a hostile or odd row cannot swell the page blob. The numbers
    here are the largest realistic ones (12-digit run id, 4-digit PR and issue)."""
    r = row("2026-11-20", "o" * 80, kind="k" * 80, pr=9999, usd=99.99994,
            run=999999999999, minutes=999.94, issue=9999, trigger="t" * 80,
            attribution="a" * 80, time_ist="23:59" + "x" * 40)
    k = ops_kpis.build(ops([r, row("2026-10-08", "unknown", kind="unknown")], {"9999": ["FAIL"]}))
    (drill,) = k["rows"]
    assert len(json.dumps(drill)) <= 250, len(json.dumps(drill))
    assert len(drill["trigger"]) <= 17 and len(drill["kind"]) <= 8


def test_the_page_blob_for_a_real_sized_window_stays_small():
    rows = [row("2026-11-%02d" % (18 + i % 7), "shipped", pr=1000 + i) for i in range(171)]
    rows.append(row("2026-10-08", "unknown", kind="unknown"))
    k = ops_kpis.build(ops(rows, {}))
    assert len(k["rows"]) == 171 and len(json.dumps(k["rows"])) < 45_000


# --- zz-probe workflows are hidden (owner answer 7) ----------------------------------

def _loops(*names):
    return [{"workflow": n, "verdict": "on-demand"} for n in names]


def test_probe_workflows_are_removed_from_every_list(monkeypatch):
    doc = {"generated_at": "2026-11-25T00:00:00Z", "window_days": 7, "alerts": [],
           "loops": _loops("agent-work.yml", "zz-probe-dup.yml", "agent-merge.yml", "zz-probe-x0.yml")}
    monkeypatch.setattr(ops_data, "_fetch", lambda name: doc if name == "agents.json" else None)
    v = ops_data._agents_view()
    names = [lp["workflow"] for lp in v["loops"]]
    assert names == ["agent-merge.yml", "agent-work.yml"]
    assert [lp["workflow"] for lp in v["scheduled"]] == []
    assert not any("zz-probe" in lp["workflow"] for lp in v["loops"] + v["last_failed"])


def test_only_the_prefix_is_hidden_not_a_name_that_merely_contains_it(monkeypatch):
    doc = {"loops": _loops("agent-zz-probe-x.yml", "zz-probe-x.yml", "zz-probes.yml")}
    monkeypatch.setattr(ops_data, "_fetch", lambda name: doc)
    assert [lp["workflow"] for lp in ops_data._agents_view()["loops"]] == [
        "agent-zz-probe-x.yml", "zz-probes.yml"]


def test_the_hidden_prefix_is_the_one_the_owner_named():
    assert ops_data.HIDDEN_WORKFLOW_PREFIXES == ("zz-probe-",)


# --- through the route ---------------------------------------------------------------

@pytest.fixture
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _page(q):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def test_only_the_overview_tab_computes_the_cards(_offline, monkeypatch):
    calls = []
    real = ops_kpis.build
    monkeypatch.setattr(ops_kpis, "build", lambda o, **kw: calls.append(1) or real(o, **kw))
    for tab in ("agents", "workflows", "runs", "backlog", "analytics", "monitoring"):
        assert _page(f"?tab={tab}").status_code == 200
    assert calls == []
    assert _page("?tab=overview").status_code == 200 and calls == [1]


def test_the_overview_page_survives_the_cards_failing(_offline, monkeypatch):
    monkeypatch.setattr(ops_kpis, "_build_unsafe", lambda *a, **k: 1 / 0)
    assert _page("?tab=overview").status_code == 200


# --- the real committed files (skipped when absent) -----------------------------------

def _real():
    d = ops_data.measurements_dir()
    if d is None or not (d / "loop.json").exists() or not (d / "agents.json").exists():
        pytest.skip("measurements/loop.json or agents.json not present")
    loop = json.loads((d / "loop.json").read_text())
    agents = json.loads((d / "agents.json").read_text())
    rows = [r for r in loop["rows"] if r.get("started")]
    if not rows:
        pytest.skip("loop.json has no rows")
    # "Today" = the day after the newest row, so both windows sit inside the file.
    newest = max(ops_data._ist(r["started"]) for r in rows).strftime("%Y-%m-%d")
    today = (datetime.strptime(newest, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    view = ops_data._loop_view(loop, today)
    return {"today_ist": today, "loop": view, "agents": {"ok": True, "agents": agents.get("agents") or {}},
            "ages": {}}, loop


def test_the_cards_agree_with_the_collector_on_the_real_loop_file():
    o, loop = _real()
    k = ops_kpis.build(o)
    assert k["error"] is False and k["skipped"] == 0
    today = o["today_ist"]
    for offset, key in ((0, "cur"), (7, "prev")):
        w = _collector_window(loop["rows"], today, 7, offset)
        if key == "cur":
            assert card(k, "prs")["value"] == w["merged"]
            if w["merged"] and len(w["measured"]) == len(w["win"]):
                assert card(k, "cost")["value"] == w["usd_per_pr"]
        else:
            assert card(k, "prs")["delta"]["previous_n"] == w["merged"]


def test_most_prs_shipped_in_the_last_two_weeks_have_a_qa_verdict():
    """If the join key ever stops matching (`rounds_per_issue` keyed by issue, say), the
    first-pass card would quietly average a handful of PRs. 64 of 64 and 111 of 111 on
    2026-11-25; the floor is 80%."""
    o, _ = _real()
    cur, prev = ops_kpis.windows(o["today_ist"], 7)
    first, _why = ops_kpis._first_verdicts(o)
    rows, _ = ops_kpis._clean(o["loop"]["rows"])
    prs = {r["pr"] for r in rows if r["date"] in set(cur + prev) and r["outcome"] == "shipped" and r["pr"]}
    if len(prs) < 10:
        pytest.skip("fewer than 10 shipped PRs in the last 14 days of the file")
    covered = sum(1 for p in prs if p in first)
    assert covered / len(prs) >= 0.8, f"{covered} of {len(prs)} shipped PRs have a verdict"
