"""Overview ships only the top issues in its blob (#1562).

`issues` was the one term of the `ops-data` blob with no ceiling: 167 open issues were
~64 KB and put the Overview at 252,049 B against the 250,000 cap. The Backlog tile now
drills into the top `OVERVIEW_ISSUE_ROWS`, in the order its script sorts them; the Backlog
tab still ships every row. These render the real page from synthetic issues.docs.

What this cannot see: the sheet opening in a browser. The title is read from the template
source and the blob, not by running the script.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import ops_data, ops_tabs

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()
PRIORITIES = ["high", "medium", "low", "unset"]


def _doc(n: int) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Priorities interleave and numbers do not follow priority, so only a real sort passes.
    rows = [{"number": 1000 + i, "title": f"issue {i}", "priority": PRIORITIES[(i * 7) % 4],
             "area": "ops", "type": "bug", "created": "2020-01-01T00:00:00Z", "ask": "", "blocked": False}
            for i in range(n)]
    return {"generated_at": now, "repo": "mahAnuj/astro-ai", "objective": "", "open": n,
            "with_ask": 0, "rows": rows, "blocked": [], "trend": {"generated_at": now, "days": []}}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def _serve(monkeypatch, n: int) -> dict:
    doc = _doc(n)
    monkeypatch.setattr(ops_data, "_fetch", lambda name: doc if name == "issues.json" else None)
    return doc


def _page(q: str):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def _blob(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="ops-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def _js_order(rows: list[dict]) -> list[int]:
    """The order the script's comparator gives, rank literal read from the template."""
    lit = re.search(r'"backlog":.*?var rank = (\{[^}]*\});', TPL, re.S).group(1)
    rank = json.loads(re.sub(r"(\w+):", r'"\1":', lit))
    return [r["number"] for r in sorted(
        rows, key=lambda r: (rank.get(r["priority"], 9), -r["number"]))]


def test_overview_blob_ships_at_most_the_cap_in_the_scripts_order(monkeypatch):
    doc = _serve(monkeypatch, 200)
    rows = _blob(_page("?tab=overview").text)["issues"]
    assert len(rows) == ops_tabs.OVERVIEW_ISSUE_ROWS == 50
    assert [r["number"] for r in rows] == _js_order(doc["rows"])[:50]


def test_backlog_tab_still_ships_every_issue(monkeypatch):
    _serve(monkeypatch, 200)
    assert len(_blob(_page("?tab=backlog").text)["issues"]) == 200


def test_overview_bytes_do_not_grow_with_the_backlog(monkeypatch):
    _serve(monkeypatch, 60)
    small = len(_page("?tab=overview").content)
    ops_data._app_cache.clear()
    _serve(monkeypatch, 200)
    big = len(_page("?tab=overview").content)
    # `created` is old so none is `filed_today` (that list is a separate blob key, bounded by
    # the day); the server-rendered queue is capped at 14 rows and the blob at 50.
    assert big - small < 4_000, (small, big)


def test_python_rank_order_equals_the_scripts_rank_literal():
    lit = re.search(r'"backlog":.*?var rank = (\{[^}]*\});', TPL, re.S).group(1)
    js = json.loads(re.sub(r"(\w+):", r'"\1":', lit))
    assert js == ops_tabs._ISSUE_RANK


def test_top_issues_never_raises_on_a_bad_row():
    rows = [{"number": "x", "priority": "high"}, {"number": 5, "priority": "weird"},
            {"number": 9, "priority": "low"}, "junk", {"priority": None}, {"number": 3, "priority": "high"}]
    out = ops_tabs.top_issues(rows, 4)
    assert len(out) == 4 and out[0] == {"number": 3, "priority": "high"}
    assert ops_tabs.top_issues(None, 5) == [] and ops_tabs.top_issues(rows, 0) == []


def test_the_drill_title_says_when_it_is_cut(monkeypatch):
    _serve(monkeypatch, 200)
    h = _page("?tab=overview").text
    assert "of 200 open (the Backlog tab lists all)" in h
    assert 'ISSUES.length === 200' in h
    ops_data._app_cache.clear()
    _serve(monkeypatch, 30)
    assert "ISSUES.length === 30" in _page("?tab=overview").text
