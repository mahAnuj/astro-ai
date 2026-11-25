"""scripts/fetch_gsc.py --by query-page (#1436, script half of #1432): a query x page map.

Measured gap it closes: every query export carried no page, so the analyst could name a
high-impression query but not the page already serving it (4,442 of 30,711 impressions
visible, ~14%, 2026-10-25..2026-11-21). The pure function carries the row shape; main() is
driven with `post`/`token`/`window` replaced, so nothing here touches the network.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fetch_gsc", ROOT / "scripts" / "fetch_gsc.py")
fg = importlib.util.module_from_spec(_spec)
sys.modules["fetch_gsc"] = fg
_spec.loader.exec_module(fg)

SADE = "https://shubhagya.com/learn/sade-sati/"
FEST = "https://shubhagya.com/festivals"


def _row(query, page, imp, clk=0, pos=8.0):
    return {"keys": [query, page], "impressions": imp, "clicks": clk,
            "ctr": (clk / imp) if imp else 0, "position": pos}


RAW = [  # deliberately not in impressions order; "sade sati" is served by two pages
    _row("sade sati", SADE, 4, 1, 6.04),
    _row("holi date", FEST, 6, 0, 12.0),
    _row("sade sati", FEST, 1, 0, 30.0),
    _row("saturn transit", SADE, 3, 0, 9.0),
]   # rows sum to 14


def _run_main(monkeypatch, capsys, argv, rows, total=100):
    posted = []

    def fake_post(url, body, bearer):
        posted.append(body)
        if "dimensions" not in body:
            return {"rows": [{"impressions": total, "clicks": 0}]}
        return {"rows": rows}

    monkeypatch.setattr(fg, "post", fake_post)
    monkeypatch.setattr(fg, "token", lambda: "tok")
    monkeypatch.setattr(fg, "window", lambda days: ("2026-10-16", "2026-11-12"))
    monkeypatch.setattr(sys, "argv", ["fetch_gsc.py", *argv])
    rc = fg.main()
    return rc, posted, json.loads(capsys.readouterr().out)


def test_row_shape_keeps_the_page_and_sorts_by_impressions():
    rows = fg.query_page_rows(RAW)
    assert all(set(r) == {"query", "page", "impressions", "clicks", "ctr", "position"}
               for r in rows)
    # same query on two pages stays two rows
    assert [(r["query"], r["page"]) for r in rows if r["query"] == "sade sati"] == [
        ("sade sati", SADE), ("sade sati", FEST)]
    assert [r["impressions"] for r in rows] == [6, 4, 3, 1]
    assert rows[1] == {"query": "sade sati", "page": SADE, "impressions": 4, "clicks": 1,
                       "ctr": 0.25, "position": 6.0}


def test_main_posts_one_query_page_body_and_one_total(monkeypatch, capsys):
    rc, posted, _ = _run_main(monkeypatch, capsys, ["--by", "query-page"], RAW)
    assert rc == 0
    dim_bodies = [b for b in posted if "dimensions" in b]
    assert len(dim_bodies) == 1 and dim_bodies[0]["dimensions"] == ["query", "page"]
    assert dim_bodies[0]["rowLimit"] == fg.ROW_LIMIT and dim_bodies[0]["dataState"] == "final"
    assert len([b for b in posted if "dimensions" not in b]) == 1


def test_main_document_states_its_mode_and_partial_coverage(monkeypatch, capsys):
    _, _, doc = _run_main(monkeypatch, capsys, ["--by", "query-page"], RAW, total=100)
    assert doc["mode"] == "query-page" and doc["dimension"] == ["query", "page"]
    assert doc["total_impressions"] == 100 and doc["rows_impressions"] == 14
    assert doc["coverage_pct"] == 14 and doc["truncated"] is False
    assert doc["emitted_rows"] == 4
    assert "14%" in doc["coverage_note"] and "PARTIAL" in doc["coverage_note"]


def test_every_emitted_row_has_a_page(monkeypatch, capsys):
    _, _, doc = _run_main(monkeypatch, capsys, ["--by", "query-page"], RAW)
    assert doc["rows"] and all(r["page"].startswith("https://") for r in doc["rows"])


def test_main_flags_a_truncated_fetch(monkeypatch, capsys):
    monkeypatch.setattr(fg, "ROW_LIMIT", 4)
    _, _, doc = _run_main(monkeypatch, capsys, ["--by", "query-page"], RAW)
    assert doc["truncated"] is True and "TRUNCATED" in doc["coverage_note"]


def test_a_zero_property_total_leaves_coverage_uncomputed(monkeypatch, capsys):
    _, _, doc = _run_main(monkeypatch, capsys, ["--by", "query-page"], RAW, total=0)
    assert doc["coverage_pct"] is None and "not computable" in doc["coverage_note"]


@pytest.mark.parametrize("argv", [
    ["--by", "query-page", "--trend"],
    ["--by", "query-page", "--band"],
    ["--page-daily", "--by", "query-page"],
])
def test_flag_combinations_that_make_no_sense_exit_before_any_request(monkeypatch, argv):
    def boom(*a, **k):
        raise AssertionError("must exit before touching the network")
    monkeypatch.setattr(fg, "post", boom)
    monkeypatch.setattr(fg, "token", boom)
    monkeypatch.setattr(sys, "argv", ["fetch_gsc.py", *argv])
    with pytest.raises(SystemExit) as e:
        fg.main()
    assert isinstance(e.value.code, str) and e.value.code


def test_the_other_modes_still_post_a_single_dimension(monkeypatch, capsys):
    rows = [{"keys": [SADE], "impressions": 5, "clicks": 0, "ctr": 0.0, "position": 9.0}]
    _, posted, doc = _run_main(monkeypatch, capsys, ["--by", "query"], rows, total=5)
    assert [b["dimensions"] for b in posted if "dimensions" in b] == [["query"]]
    assert doc["dimension"] == "query" and "mode" not in doc
    _, posted, doc = _run_main(monkeypatch, capsys, [], rows, total=5)
    assert [b["dimensions"] for b in posted if "dimensions" in b] == [["page"]]
    assert doc["dimension"] == "page" and "mode" not in doc
