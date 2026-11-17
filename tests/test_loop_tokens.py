"""Claude tokens per loop run (owner, 2026-11-17: "Measure tokens per cycle. The usage
numbers are already in every run's log but aren't collected").

Every test is a way the number could lie. The ones that matter most:

  * summing the per-message `usage` blocks or the subagents' running
    `total_tokens` instead of the session total -- the fixture carries one of each
    next to the result object, so a reader that picks them up gets the wrong sum;
  * a resumed session's second result object dropped (an undercount) or the same
    object printed twice counted twice (an overcount);
  * an unreadable log written as 0 tokens, which reads as a cheap run;
  * an old snapshot rejected because its rows predate the fields.

The fixture `claude_result_run44020807802.log` is a TRIMMED REAL LOG: agent-work run
44020807802, job 133837665489, fetched 2026-11-17. Kept verbatim: timestamps, one
`assistant` message with its per-call `usage`, one subagent `task_progress` with
its `usage.total_tokens`, and the final result object. Trimmed: the thinking
signature, `permission_denials` (emptied) and the `result` prose.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures" / "loop_measurements" / "claude_result_run44020807802.log"

_spec = importlib.util.spec_from_file_location("collect_loop_measurements_tokens",
                                               ROOT / "scripts" / "collect_loop_measurements.py")
cm = importlib.util.module_from_spec(_spec)
sys.modules["collect_loop_measurements_tokens"] = cm
_spec.loader.exec_module(cm)

_dspec = importlib.util.spec_from_file_location("detect_ops_regressions_tokens",
                                                ROOT / "scripts" / "detect_ops_regressions.py")
det = importlib.util.module_from_spec(_dspec)
sys.modules["detect_ops_regressions_tokens"] = det
_dspec.loader.exec_module(det)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
REAL = {"tokens_input": 305, "tokens_output": 103720, "tokens_cache_read": 13174859,
        "tokens_cache_write": 542749, "cost_list_usd": 3.8793, "model": "claude-sonnet-5-5",
        "turns": 26}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(self, *a, **k):
        raise AssertionError("a token test reached for the network")
    monkeypatch.setattr(cm.GhSource, "_run", refuse)


def log() -> str:
    return FIX.read_text()


def result_object(uuid: str, *, out: int, cr: int, usd: float, turns: int,
                  key: str = "model_usage_since_last_result", model="claude-sonnet-5-5",
                  stamp="2026-11-17T06:30:00.0000000Z") -> str:
    """A result object in the shape the action prints, one line per key."""
    body = {"type": "result", "subtype": "success", "num_turns": turns, "uuid": uuid,
            "total_cost_usd": usd,
            key: {model: {"inputTokens": 10, "outputTokens": out, "cacheReadInputTokens": cr,
                          "cacheCreationInputTokens": 1000, "costUSD": usd, "costBasis": "list"}}}
    return "\n".join(f"{stamp} {ln}" for ln in json.dumps(body, indent=2).splitlines()) + "\n"


# ------------------------------------------------------------- parse_usage

def test_the_real_log_reads_the_SESSION_TOTAL_not_a_per_message_usage():
    assert cm.parse_usage(log()) == REAL


def test_the_fixture_really_carries_the_fragments_a_naive_reader_would_sum():
    """Guards the test above: if the decoys were trimmed away, it would pass for
    a reader that sums every `output_tokens` it sees."""
    text = log()
    assert '"output_tokens": 7,' in text and '"total_tokens": 40345,' in text
    assert '"cache_read_input_tokens": 2293717,' in text      # the main agent alone


def test_a_log_with_no_result_object_is_None_never_zero():
    # The same real log with its result object no longer typed as one: the
    # assistant `usage` and subagent `total_tokens` are still there, and must
    # not be read as a fallback.
    no_result = log().replace('  "type": "result",', '  "type": "not-a-result",')
    assert '"output_tokens": 7,' in no_result
    assert cm.parse_usage(no_result) is None
    assert cm.parse_usage("") is None
    assert cm.parse_usage("2026-11-17T00:00:00.0000000Z ##[error]Process completed with exit code 1.") is None


def test_two_result_objects_from_a_resumed_session_are_SUMMED():
    two = log() + result_object("second-uuid", out=1000, cr=50000, usd=0.5, turns=4)
    got = cm.parse_usage(two)
    assert got["tokens_output"] == 103720 + 1000
    assert got["tokens_cache_read"] == 13174859 + 50000
    assert got["turns"] == 26 + 4
    assert got["cost_list_usd"] == round(3.8793418999999987 + 0.5, 4)


def test_the_same_result_object_printed_twice_counts_ONCE():
    twice = result_object("same", out=100, cr=10, usd=0.1, turns=1) * 2
    assert cm.parse_usage(twice)["tokens_output"] == 100


def test_a_result_mangled_by_the_runner_still_reads_its_usage():
    """The runner masks secrets after serialisation; `***` swallowing a closing quote
    makes the whole object invalid JSON (seen in 12 objects across 40 real runs)."""
    mangled = log().replace('(trimmed for the fixture).",',
                            '-H \\"Authorization: ***" https://api.github.com/repos",')
    assert 'Authorization: ***" https' in mangled
    with pytest.raises(ValueError):
        obj = cm._result_objects(mangled)[0]
        json.loads("\n".join(obj))
    assert cm.parse_usage(mangled) == REAL


def test_an_OLD_action_with_only_modelUsage_reads_when_there_is_one_result():
    old = result_object("u", out=500, cr=9000, usd=0.2, turns=3, key="modelUsage")
    assert cm.parse_usage(old)["tokens_output"] == 500


def test_several_OLD_results_cannot_be_combined_and_read_as_None():
    old = (result_object("a", out=500, cr=9000, usd=0.2, turns=3, key="modelUsage")
           + result_object("b", out=700, cr=9000, usd=0.2, turns=3, key="modelUsage"))
    assert cm.parse_usage(old) is None


def test_one_unreadable_result_makes_the_whole_run_unmeasured():
    """A partial sum would understate the run and look like a cheap one."""
    bad = result_object("x", out=1, cr=1, usd=0.0, turns=1, key="somethingElse")
    assert cm.parse_usage(log() + bad) is None


def test_two_models_are_summed_and_both_named():
    two = log() + result_object("h", out=10, cr=0, usd=0.01, turns=1, model="claude-haiku-5")
    got = cm.parse_usage(two)
    assert got["model"] == "claude-haiku-5+claude-sonnet-5-5"
    assert got["tokens_output"] == 103730


# ------------------------------------------------------------- rows

def _row(**kw):
    base = {"run": 1, "workflow": "agent-work", "date": "2026-11-17", "started": "2026-11-17T10:00:00Z",
            "trigger": "schedule", "conclusion": "success", "minutes": 20.0, "issue": 5, "pr": 42,
            "pr_merged": True, "outcome": "shipped", "attribution": "receipt", "kind": "issue",
            "owner_helped": False}
    return {**base, **kw}


def test_old_rows_without_token_fields_still_validate_and_new_ones_do_too():
    doc = {"generated_at": "x", "rows": [_row(), _row(run=2, **REAL)]}
    assert cm.validate_loop(doc) == []


def test_a_PARTIAL_reading_or_a_negative_count_is_rejected():
    partial = {k: v for k, v in REAL.items() if k != "tokens_cache_read"}
    assert cm.validate_loop({"generated_at": "x", "rows": [_row(**partial)]})
    assert cm.validate_loop({"generated_at": "x", "rows": [_row(**{**REAL, "tokens_output": -1})]})
    assert cm.validate_loop({"generated_at": "x", "rows": [_row(**{**REAL, "tokens_output": "7"})]})


class Fake(cm.Source):
    def __init__(self, data, logs=None):
        self.data, self.logs, self.calls = data, logs or {}, []

    def get(self, path, paginate=False):
        self.calls.append(path)
        for k, v in self.data.items():
            if path == k or (k.endswith("*") and path.startswith(k[:-1])):
                return v
        raise cm.ApiError(404, path, "no fake")

    def text(self, path):
        self.calls.append(path)
        job = path.split("/")[2]
        if job in self.logs:
            return self.logs[job]
        raise cm.ApiError(404, path, "no log")


def _run(id=1):
    return {"id": id, "status": "completed", "conclusion": "success", "event": "schedule",
            "created_at": "2026-11-17T05:00:00Z", "run_started_at": "2026-11-17T05:00:00Z",
            "updated_at": "2026-11-17T06:07:00Z"}


def _listing(*rs):
    return {"actions/workflows/agent-work.yml/runs*": {"workflow_runs": list(rs)},
            **{f"actions/runs/{r['id']}/jobs?per_page=100": {"jobs": [{"id": 70 + r["id"], "conclusion": "success"}]}
               for r in rs}}


RECEIPT = "2026-11-17T06:07:00.0000000Z LOOP-RECEIPT issue=1067 branch=issue/1067-x pr=1150\n"
MERGED = {"number": 1150, "state": "closed", "merged_at": "2026-11-17T07:00:00Z",
          "merged_by": {"login": "github-actions[bot]"}}


def test_a_new_run_gets_its_token_fields_from_the_SAME_log_fetch():
    src = Fake({**_listing(_run()), "pulls/1150": MERGED, "pulls/1150/commits*": []},
               logs={"71": log() + RECEIPT})
    doc, _ = cm.collect(src, None, NOW, "mahAnuj")
    (row,) = doc["rows"]
    assert {k: row[k] for k in REAL} == REAL and row["outcome"] == "shipped"
    assert sum(1 for c in src.calls if c.startswith("actions/jobs/")) == 1
    assert cm.validate_loop(doc) == []


def test_a_run_whose_log_has_no_result_has_NO_token_fields():
    src = Fake({**_listing(_run()), "pulls/1150": MERGED, "pulls/1150/commits*": []},
               logs={"71": RECEIPT})
    (row,) = cm.collect(src, None, NOW, "mahAnuj")[0]["rows"]
    assert not any(k in row for k in cm.USAGE_FIELDS)


def test_a_refreshed_open_PR_row_keeps_its_reading_without_re_reading_the_log():
    open_row = _row(run=1, issue=1067, pr=1150, pr_merged=False, outcome="pr open",
                    owner_helped=None, started="2026-11-17T05:00:00Z", **REAL)
    src = Fake({**_listing(_run()), "pulls/1150": MERGED, "pulls/1150/commits*": []})
    doc, stats = cm.collect(src, {"rows": [open_row], "tokens": {}}, NOW, "mahAnuj")
    assert stats["refreshed"] == 1
    assert {k: doc["rows"][0][k] for k in REAL} == REAL
    assert not any(c.startswith("actions/jobs/") for c in src.calls)


def test_a_snapshot_from_before_tokens_is_backfilled_ONCE_then_left_alone():
    settled = _row(run=1, issue=1067, pr=1150, started="2026-11-17T05:00:00Z")
    src = Fake({**_listing(_run())}, logs={"71": log() + RECEIPT})
    doc, stats = cm.collect(src, {"rows": [settled]}, NOW, "mahAnuj")
    assert stats["migrated"] == 1 and doc["rows"][0]["tokens_output"] == 103720
    assert "tokens" in doc
    # The next collection reads no log, even for a row the backfill found nothing in.
    bare = _row(run=1, issue=1067, pr=1150, started="2026-11-17T05:00:00Z")
    src2 = Fake({**_listing(_run())}, logs={"71": log()})
    doc2, stats2 = cm.collect(src2, {**doc, "rows": [bare]}, NOW, "mahAnuj")
    assert stats2["migrated"] == 0
    assert not any(c.startswith("actions/jobs/") for c in src2.calls)


# ------------------------------------------------------------- the summary

def _t(run, outcome, kind, tokens, usd, *, pr=None, hours_ago=1):
    started = (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = _row(run=run, started=started, date=started[:10], outcome=outcome, kind=kind, pr=pr,
               pr_merged=True if outcome == "shipped" else (False if pr else None),
               owner_helped=False if outcome == "shipped" else None)
    if tokens is not None:
        row.update(tokens_input=0, tokens_output=tokens, tokens_cache_read=0, tokens_cache_write=0,
                   cost_list_usd=usd, model="m", turns=1)
    return row


def test_the_summary_maths():
    rows = [
        _t(1, "shipped", "issue", 600, 3.0, pr=10),
        _t(2, "shipped", "ranked", 400, 2.0, pr=10),      # same PR: one merged PR, not two
        _t(3, "shipped", "issue", 1000, 4.0, pr=11),
        _t(4, "judged", "qa-round", 100, 0.5),
        _t(5, "judged", "qa-round", 300, 0.7),
        _t(6, "nothing", "ranked", 200, 0.3),
        _t(7, "failed", "ranked", None, None),             # unmeasured: counted as a run only
        _t(8, "shipped", "issue", 9999, 9.0, pr=99, hours_ago=24 * 9),   # previous window
    ]
    s = cm.token_summary(rows, NOW)
    assert (s["runs"], s["measured"], s["merged_prs"]) == (7, 6, 2)
    assert s["total"]["tokens"] == 2600 and s["total"]["output"] == 2600
    assert s["total"]["cost_list_usd"] == 10.5
    # EVERY measured run's tokens over the merged PRs: the waste is in the price.
    assert s["per_merged_pr"] == 1300 and s["cost_list_usd_per_merged_pr"] == 5.25
    assert s["median_by_outcome"]["shipped"] == {"runs": 3, "tokens": 600, "cost_list_usd": 3.0}
    assert s["median_by_outcome"]["judged"]["tokens"] == 200
    assert "failed" not in s["median_by_outcome"], "an unmeasured outcome has no median, not 0"
    assert s["median_cycle"] == 500 and s["median_qa_round"] == 200
    assert s["previous"] == {"runs": 1, "measured": 1, "merged_prs": 1, "per_merged_pr": 9999}


def test_a_window_with_no_merged_PR_has_no_per_PR_figure():
    s = cm.token_summary([_t(1, "nothing", "ranked", 200, 0.3)], NOW)
    assert s["per_merged_pr"] is None and s["median_qa_round"] is None


# ------------------------------------------------------------- the detector

def _det_loop(per, before, prs=10, prev_prs=10, measured=20, runs=20):
    return {"rows": [], "tokens": {"days": 7, "runs": runs, "measured": measured, "merged_prs": prs,
                                   "per_merged_pr": per,
                                   "previous": {"runs": 20, "measured": 20, "merged_prs": prev_prs,
                                                "per_merged_pr": before}}}


def _tokens_findings(tmp_path, monkeypatch, loop):
    m = tmp_path / "measurements"
    m.mkdir()
    (m / "loop.json").write_text(json.dumps(loop))
    monkeypatch.setattr(det, "MEASUREMENTS", m)
    monkeypatch.setattr(det, "ROOT", tmp_path)
    found, _ = det.find(now=NOW)
    return [f for f in found if f["kind"] == "cycle-tokens"]


def test_tokens_per_merged_PR_rising_over_half_is_a_finding(tmp_path, monkeypatch):
    (hit,) = _tokens_findings(tmp_path, monkeypatch, _det_loop(16_000_000, 10_000_000))
    assert "60%" in hit["title"] and "median_cycle" in hit["detail"]


def test_a_smaller_rise_is_no_finding(tmp_path, monkeypatch):
    assert _tokens_findings(tmp_path, monkeypatch, _det_loop(14_000_000, 10_000_000)) == []


def test_a_quiet_window_is_no_finding(tmp_path, monkeypatch):
    assert _tokens_findings(tmp_path, monkeypatch, _det_loop(30_000_000, 10_000_000, prs=2)) == []


def test_a_half_measured_window_is_no_finding(tmp_path, monkeypatch):
    assert _tokens_findings(tmp_path, monkeypatch,
                            _det_loop(30_000_000, 10_000_000, measured=10, runs=20)) == []


# ------------------------------------------------------------- /admin/ops

@pytest.fixture
def page(client, monkeypatch, tmp_path):
    from astro_ai import llm_stats, ops_data

    def render(files: dict):
        d = tmp_path / "m"
        d.mkdir(exist_ok=True)
        for name, doc in files.items():
            (d / name).write_text(json.dumps(doc))
        monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
        monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
        monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
        monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
        monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
        monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(d))
        ops_data._cache.clear()
        ops_data._app_cache.clear()
        try:
            r = client.get("/admin/ops", auth=("admin", "bhagya-dev"))
        finally:
            ops_data._cache.clear()
            ops_data._app_cache.clear()
        assert r.status_code == 200, r.text[:500]
        return r.text
    return render


def _loop_doc(tokens=None):
    rows = [_t(1, "shipped", "issue", 600, 3.0, pr=10), _t(4, "judged", "qa-round", 100, 0.5)]
    doc = {"generated_at": "2026-11-17T11:00:00Z", "rows": rows}
    if tokens is not None:
        doc["tokens"] = tokens
    return doc


SUMMARY = {"days": 7, "runs": 178, "measured": 178,
           "total": {"tokens": 961408024, "input": 21539, "output": 7189989, "cache_read": 907006147,
                     "cache_write": 47190349, "cost_list_usd": 306.92},
           "median_by_outcome": {"shipped": {"runs": 110, "tokens": 6592657, "cost_list_usd": 2.28},
                                 "judged": {"runs": 52, "tokens": 1343861, "cost_list_usd": 0.52}},
           "median_cycle": 6402269, "median_qa_round": 1343861, "merged_prs": 101,
           "per_merged_pr": 9518891, "cost_list_usd_per_merged_pr": 3.04,
           "previous": {"runs": 130, "measured": 127, "merged_prs": 49, "per_merged_pr": 11749890}}


def test_the_ops_page_shows_tokens_per_merged_PR_and_the_medians(page):
    html = page({"loop.json": _loop_doc(SUMMARY)})
    panel = html[html.index("Claude tokens per shipped fix"):]
    panel = panel[:panel.index("</section>")]
    assert "9.5M" in panel and "-19% vs the 7d before" in panel
    assert "6.4M" in panel and "1.3M" in panel and "961.4M" in panel and "$307 list" in panel
    assert "178 of 178 runs measured" in panel and "101 PRs merged" in panel
    assert "list price, covered by the Max subscription; the weekly quota is what binds" in panel


def test_an_old_loop_json_without_tokens_says_so_instead_of_zeros(page):
    html = page({"loop.json": _loop_doc()})
    panel = html[html.index("Claude tokens per shipped fix"):]
    panel = panel[:panel.index("</section>")]
    assert "carries no <code>tokens</code> block yet" in panel


def test_a_missing_loop_json_still_renders_the_panel_empty(page):
    html = page({})
    assert "Claude tokens per shipped fix" in html
    assert "carries no <code>tokens</code> block yet" in html


def test_a_partly_measured_window_is_called_a_floor(page):
    html = page({"loop.json": _loop_doc({**SUMMARY, "measured": 170})})
    assert "170 of 178 runs measured, so the totals are a floor" in html
