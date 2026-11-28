"""One malformed row in agents.json `loops` degrades that row, never all 7 /admin/ops tabs
(#1133 slice 2c, step 1a; the #1492 / #1542 / #1554 class).

`_agents_view` ran from `snapshot()` ("never raises") outside any try and did
`r["verdict"]`, `r["workflow"]` on every row, and `_alerts` did `(lp.get("last_run") or
"")[:10]`, so a null row, a row with no `verdict`, `verdict: []` or `last_run: 5` was a 500
on every tab. These tests use the REAL `_fetch` against files in a tmp dir, as
test_ops_series_row_tolerance does; replacing `_fetch` would test nothing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from astro_ai import ops_data, ops_tabs

KEYS = [k for k, _ in ops_tabs.TABS]


@pytest.fixture(autouse=True)
def _offline(monkeypatch, tmp_path):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(tmp_path))
    for c in (ops_data._cache, ops_data._app_cache):
        c.clear()
    yield
    for c in (ops_data._cache, ops_data._app_cache):
        c.clear()


def _page(key: str):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app, raise_server_exceptions=False).get(
        f"/admin/ops?tab={key}", auth=("admin", pw))


# The Team panel reads `delivery.outcomes` and `agents.by_agent` / `agents.qa` unguarded, so
# the fixture carries the committed file's real blocks: this test is about ROWS, and a
# fixture with `delivery: {}` fails the Workflows tab for an unrelated reason.
_REAL = json.loads((Path(__file__).resolve().parent.parent / "measurements" / "agents.json").read_text())


def _write(tmp_path, loops, **extra):
    doc = {"generated_at": "2026-11-27T05:00:00Z", "window_days": 14, "loops": loops,
           "delivery": _REAL["delivery"], "agents": _REAL["agents"], "alerts": [], **extra}
    (tmp_path / "agents.json").write_text(json.dumps(doc))
    ops_data._cache.clear()
    ops_data._app_cache.clear()


def _good(wf="agent-measure.yml", **kw):
    return {"workflow": wf, "verdict": "not-due-yet", "last_run": "2026-11-27T01:00:00Z",
            "last_conclusion": "success", "last_run_health": "green", "cadence": ["0 1 * * *"],
            "display": "Agent measure", "runs_scheduled": 1, "slots_due": 1, **kw}


# the four rows the plan names: null, no verdict, list verdict, int last_run
BAD_ROWS = [None, 3, "x", [], {"workflow": "a.yml"}, {"verdict": "ok"},
            {"workflow": 5, "verdict": "ok"}, {"workflow": "a.yml", "verdict": []},
            {"workflow": "a.yml", "verdict": {"x": 1}}]


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("row", BAD_ROWS, ids=repr)
def test_a_garbage_loop_row_does_not_500_any_tab(tmp_path, key, row):
    _write(tmp_path, [_good(), row])
    assert _page(key).status_code == 200


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("field,value", [("last_run", 5), ("last_run", ["x"]),
                                         ("last_conclusion", 7), ("last_run_health", []),
                                         ("display", {}), ("schedule_since", 9),
                                         ("cadence", "x"), ("cadence", 5)])
def test_a_non_string_text_field_does_not_500_any_tab(tmp_path, key, field, value):
    # `verdict: broken` and `missing-slots` are the verdicts `_alerts` slices fields for
    rows = [_good(f"a{i}.yml", verdict=v, **{field: value})
            for i, v in enumerate(("broken", "missing-slots", "not-due-yet", "on-demand"))]
    _write(tmp_path, rows)
    assert _page(key).status_code == 200


def test_bad_rows_are_dropped_and_counted_and_good_rows_survive(tmp_path):
    _write(tmp_path, [_good("b.yml"), None, {"workflow": "a.yml"}, _good("a.yml"), 3,
                      {"workflow": "c.yml", "verdict": []}])
    v = ops_data._agents_view()
    assert v["ok"] is True
    assert [r["workflow"] for r in v["loops"]] == ["a.yml", "b.yml"]
    assert v["skipped_rows"] == 4


def test_a_non_string_field_is_blanked_and_the_row_with_its_real_verdict_is_kept(tmp_path):
    _write(tmp_path, [_good("a.yml", verdict="broken", last_run=5, last_conclusion=[],
                            last_run_health=7, display=3, cadence="x")])
    v = ops_data._agents_view()
    r = v["loops"][0]
    assert r["verdict"] == "broken"
    assert (r["last_run"], r["last_conclusion"], r["last_run_health"], r["display"],
            r["cadence"]) == (None, None, None, None, None)
    assert v["skipped_rows"] == 0
    alerts = ops_data._alerts({"ok": True}, {"ok": True, "rows": []}, v, {"ok": True}, {})
    assert any(a["title"] == "a.yml is broken" for a in alerts)


def test_a_cadence_list_keeps_only_its_strings(tmp_path):
    _write(tmp_path, [_good("a.yml", cadence=["0 1 * * *", 5, None])])
    assert ops_data._agents_view()["loops"][0]["cadence"] == ["0 1 * * *"]


def test_the_cached_source_row_is_not_mutated_by_blanking(tmp_path):
    # `_fetch` caches the parsed file and returns the same object, so blanking a field in
    # place would change what every later reader of agents.json sees (agent_status reads it).
    _write(tmp_path, [_good("a.yml", last_run=5)])
    ops_data._agents_view()
    assert ops_data._fetch("agents.json")["loops"][0]["last_run"] == 5


def test_a_clean_file_is_unchanged(tmp_path):
    rows = [_good("a.yml"), _good("b.yml", verdict="on-demand", cadence=None)]
    _write(tmp_path, rows)
    v = ops_data._agents_view()
    assert v["skipped_rows"] == 0
    assert v["loops"] == rows
    assert [r["workflow"] for r in v["scheduled"]] == ["a.yml"]
    for key in KEYS:
        assert _page(key).status_code == 200


def test_probe_workflows_are_still_hidden_from_every_count(tmp_path):
    _write(tmp_path, [_good("a.yml"), _good("zz-probe-x.yml", verdict="broken")])
    v = ops_data._agents_view()
    assert [r["workflow"] for r in v["loops"]] == ["a.yml"]
    assert v["skipped_rows"] == 0
