"""scripts/fetch_gsc.py --page-daily (#490): a page x date series.

Measured gap it closes: gsc-daily.json is site-level (date only) and gsc-all.json
is page-level with no date, so a page-level ship could not be scored against its
own deploy date. The pure function carries the grouping rules; main() is driven
with `post`/`token`/`window` replaced, so nothing here touches the network.
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


def _row(page, date, imp, clk=0, pos=8.0):
    return {"keys": [page, date], "impressions": imp, "clicks": clk,
            "ctr": (clk / imp) if imp else 0, "position": pos}


RAW = [  # deliberately out of chronological order
    _row(SADE, "2026-11-03", 30, 3, 6.0),
    _row(FEST, "2026-11-01", 100, 1, 12.0),
    _row(SADE, "2026-11-01", 10, 0, 10.0),
    _row(SADE, "2026-11-05", 60, 6, 4.0),
]


def test_rows_group_per_page_in_chronological_order():
    out = fg.page_daily_rows(RAW)
    assert set(out["pages"]) == {SADE, FEST}
    assert [d["date"] for d in out["pages"][SADE]] == ["2026-11-01", "2026-11-03", "2026-11-05"]
    assert out["pages"][SADE][1] == {"date": "2026-11-03", "impressions": 30, "clicks": 3,
                                     "ctr": 0.1, "position": 6.0}


def test_per_page_totals_and_impression_weighted_position():
    t = fg.page_daily_rows(RAW)["page_totals"][SADE]
    assert (t["impressions"], t["clicks"], t["days_with_data"]) == (100, 9, 3)
    assert t["ctr"] == 0.09
    # (10*10 + 30*6 + 60*4) / 100 = 5.2 ; an unweighted mean would be 6.7
    assert t["position"] == 5.2


def test_pages_are_ordered_by_total_impressions():
    # RAW's two pages tie at 100, which would pin nothing; each side gets a clear winner
    assert list(fg.page_daily_rows(RAW + [_row(FEST, "2026-11-02", 500)])["pages"]) == [FEST, SADE]
    assert list(fg.page_daily_rows(RAW + [_row(SADE, "2026-11-04", 500)])["pages"]) == [SADE, FEST]


def test_watchlist_keeps_only_matching_pages_and_reports_the_rest():
    out = fg.page_daily_rows(RAW, ["/learn/sade-sati/", "/learn/never-existed/"])
    assert list(out["pages"]) == [SADE]
    assert out["unmatched_pages"] == ["/learn/never-existed/"]
    assert out["emitted_impressions"] == 100
    assert out["rows_impressions"] == 200   # describes the whole fetch, not the filter


def test_no_watchlist_emits_every_page_and_no_unmatched():
    out = fg.page_daily_rows(RAW)
    assert len(out["pages"]) == 2 and out["unmatched_pages"] == []
    assert out["emitted_impressions"] == out["rows_impressions"] == 200


def test_a_day_without_a_row_is_not_zero_filled():
    days = [d["date"] for d in fg.page_daily_rows(RAW)["pages"][SADE]]
    assert "2026-11-02" not in days and "2026-11-04" not in days
    assert len(days) == 3


def _run_main(monkeypatch, capsys, argv, rows, total=200):
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


def test_main_requests_page_and_date_dimensions(monkeypatch, capsys):
    rc, posted, doc = _run_main(monkeypatch, capsys, ["--page-daily"], RAW)
    assert rc == 0
    dim_bodies = [b for b in posted if "dimensions" in b]
    assert len(dim_bodies) == 1 and dim_bodies[0]["dimensions"] == ["page", "date"]
    assert dim_bodies[0]["rowLimit"] == fg.ROW_LIMIT and dim_bodies[0]["dataState"] == "final"
    assert doc["mode"] == "page-daily" and doc["dimension"] == ["page", "date"]
    assert doc["total_impressions"] == 200 and doc["rows_impressions"] == 200
    assert doc["coverage_pct"] == 100 and doc["truncated"] is False
    assert "not zero-filled" in doc["note"]


def test_main_applies_the_watchlist_and_reports_unmatched(monkeypatch, capsys):
    rc, _, doc = _run_main(
        monkeypatch, capsys, ["--page-daily", "--pages", "/learn/sade-sati/, /nope/"], RAW)
    assert list(doc["pages"]) == [SADE]
    assert doc["unmatched_pages"] == ["/nope/"]
    assert doc["emitted_impressions"] == 100 and doc["coverage_pct"] == 100


def test_main_flags_a_truncated_fetch(monkeypatch, capsys):
    monkeypatch.setattr(fg, "ROW_LIMIT", 4)
    _, _, doc = _run_main(monkeypatch, capsys, ["--page-daily"], RAW)
    assert doc["truncated"] is True and "TRUNCATED" in doc["coverage_note"]


@pytest.mark.parametrize("argv", [
    ["--page-daily", "--trend"],
    ["--page-daily", "--band"],
    ["--page-daily", "--by", "page"],
    ["--pages", "/learn/"],
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
    _, posted, doc = _run_main(monkeypatch, capsys, [], rows, total=5)
    assert [b["dimensions"] for b in posted if "dimensions" in b] == [["page"]]
    assert doc["dimension"] == "page"


def test_trend_by_date_is_still_refused(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["fetch_gsc.py", "--trend", "--by", "date"])
    with pytest.raises(SystemExit) as e:
        fg.main()
    assert "redundant" in e.value.code
