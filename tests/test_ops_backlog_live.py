"""The /admin/ops backlog is fetched live, and must degrade loudly (#353).

WHY THIS FILE EXISTS
--------------------
Every other panel on /admin/ops reads a file that a cron committed. The backlog
reads the GitHub API on the request, which buys the one number a reader most
needs to be correct and introduces the one failure the rest of the page cannot
have: a call that does not come back.

The measured reason for going live at all: on 2026-10-14 the page showed
`66 open` from a 07:22Z collection while 65 were actually open. A count that is
two off reads as WRONG, not as OLD -- so the panel was teaching the reader to
distrust the page.

Three things are asserted here because all three have a way of going wrong
silently, and silently is the only way that matters on a monitoring page:

  1. PULL REQUESTS ARE ISSUES on `/repos/{repo}/issues`. Measured 2026-10-15
     the endpoint returned 69 items for 67 open issues. Without the filter the
     headline is inflated by every open PR, and it would still look plausible.
  2. A FAILED CALL MUST FALL BACK AND SAY SO. An unauthenticated call is
     limited to 60/hour per egress IP, shared with every other tenant behind
     the same NAT on Cloud Run, so this will happen for reasons unrelated to
     this app. Rendering yesterday's count while labelled "live" would be worse
     than rendering nothing.
  3. A LIVE PANEL HAS NO AGE. The staleness alert must not fire on a panel
     fetched this second, or the strip grows a row that is present on every
     single render and the reader learns to skip the strip.

Hermetic: `urlopen` is stubbed in every test. No network, per conftest.
"""
from __future__ import annotations

import json
import sys
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from astro_ai import issue_backlog, ops_data  # noqa: E402


def _issue(number: int, *, title: str = "x: a thing", body: str = "",
           labels: tuple[str, ...] = (), pr: bool = False) -> dict:
    """One item as the REST endpoint returns it: snake_case, PRs included."""
    out = {
        "number": number,
        "title": title,
        "body": body,
        "created_at": "2026-10-01T00:00:00Z",
        "updated_at": "2026-10-02T00:00:00Z",
        "labels": [{"name": n} for n in labels],
    }
    if pr:
        out["pull_request"] = {"url": "https://api.github.com/x"}
    return out


@contextmanager
def _stub(monkeypatch, pages: list[list[dict]] | Exception):
    """Serve `pages` to successive API calls, or raise. `calls` holds the URLs.

    `ops_data` and `issue_backlog` share one `urllib.request.urlopen`, so this
    intercepts both and routes by host: api.github.com gets `pages`, and every
    other URL -- the raw.githubusercontent.com fallbacks for loop.json and the
    rest -- raises, which is what "no network" looks like to those loaders.
    Letting them through would make the suite non-hermetic; counting them in
    `calls` would make the one-call-per-render assertion meaningless.
    """
    calls: list[str] = []

    class _Resp:
        def __init__(self, payload): self._p = payload
        def read(self): return json.dumps(self._p).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" not in url:
            raise urllib.error.URLError(f"not stubbed: {url}")
        calls.append(url)
        if isinstance(pages, Exception):
            raise pages
        if len(calls) > len(pages):
            raise AssertionError(f"urlopen called {len(calls)}x for {len(pages)} pages")
        return _Resp(pages[len(calls) - 1])

    monkeypatch.setattr(issue_backlog.urllib.request, "urlopen", fake)
    yield calls


# --------------------------------------------------------------------------
# fetch_live
# --------------------------------------------------------------------------

def test_pull_requests_on_the_issues_endpoint_are_not_backlog_rows(monkeypatch):
    page = [_issue(1), _issue(2, pr=True), _issue(3), _issue(4, pr=True)]
    with _stub(monkeypatch, [page]):
        got = issue_backlog.fetch_live("o/r", timeout=1)
    assert [i["number"] for i in got] == [1, 3]


def test_rest_field_names_are_normalised_to_the_shape_row_for_reads(monkeypatch):
    with _stub(monkeypatch, [[_issue(7, labels=("priority:high", "bug"))]]):
        got = issue_backlog.fetch_live("o/r", timeout=1)
    row = issue_backlog.row_for(got[0])
    # `gh` emits createdAt/updatedAt; the REST API emits created_at/updated_at.
    # If the normalisation were dropped, `created` would be None and every row
    # would silently leave "filed today" empty rather than fail.
    assert row["created"] == "2026-10-01T00:00:00Z"
    assert row["updated"] == "2026-10-02T00:00:00Z"
    assert row["priority"] == "high"
    assert row["type"] == issue_backlog.derive_type(["bug"])


def test_a_full_page_is_followed_and_a_short_page_ends_the_walk(monkeypatch):
    full = [_issue(n) for n in range(100, 200)]          # exactly 100 -> go on
    short = [_issue(1), _issue(2)]                        # < 100 -> stop
    with _stub(monkeypatch, [full, short]) as calls:
        got = issue_backlog.fetch_live("o/r", timeout=1)
    assert len(got) == 102
    assert len(calls) == 2 and "page=2" in calls[1]


def test_the_page_walk_is_capped_so_one_render_cannot_become_many_requests(monkeypatch):
    pages = [[_issue(n + i * 100) for n in range(100)]
             for i in range(issue_backlog.MAX_PAGES)]
    with _stub(monkeypatch, pages) as calls:
        issue_backlog.fetch_live("o/r", timeout=1)
    # The stub raises if asked for a page beyond the list, so reaching the end
    # of the loop without an error IS the assertion. Stated anyway.
    assert len(calls) == issue_backlog.MAX_PAGES


def test_fetch_live_raises_rather_than_returning_an_empty_backlog(monkeypatch):
    with _stub(monkeypatch, urllib.error.HTTPError("u", 403, "rate limited", {}, None)):
        with pytest.raises(urllib.error.HTTPError):
            issue_backlog.fetch_live("o/r", timeout=1)


def test_counts_are_derived_from_the_rows_they_are_printed_above():
    rows = [_issue(1, labels=("priority:high",)), _issue(2), _issue(3, labels=("bug",))]
    doc = issue_backlog.build([dict(r, createdAt=r["created_at"]) for r in rows],
                              repo="o/r", objective="obj")
    assert doc["open"] == len(doc["rows"]) == 3
    assert sum(doc["by_priority"].values()) == 3
    assert sum(doc["by_area"].values()) == 3
    assert sum(doc["by_type"].values()) == 3
    assert doc["objective"] == "obj"


def test_the_collector_imports_the_derivation_rather_than_keeping_a_copy():
    """One definition, or the live count and its own fallback can disagree."""
    src = (ROOT / "scripts" / "collect_issue_backlog.py").read_text()
    assert "from astro_ai.issue_backlog import" in src
    for name in ("def derive_priority", "def derive_area", "def row_for", "def build"):
        assert name not in src, f"{name} is defined twice; it must only be imported"


# --------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------

@pytest.fixture
def committed(tmp_path, monkeypatch):
    """A `measurements/` dir holding a deliberately OLD snapshot."""
    doc = issue_backlog.build(
        [{"number": 9, "title": "x: old", "body": "", "labels": [],
          "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z"}],
        repo="o/r", objective="the committed objective",
        generated_at="2026-10-01T00:00:00Z")
    (tmp_path / "issues.json").write_text(json.dumps(doc))
    monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(tmp_path))
    ops_data._cache.clear()
    ops_data._live_cache = None
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", True)
    yield doc
    ops_data._cache.clear()
    ops_data._live_cache = None


def test_a_live_backlog_replaces_the_committed_count_and_is_labelled_live(
        committed, monkeypatch):
    with _stub(monkeypatch, [[_issue(1), _issue(2), _issue(3)]]):
        snap = ops_data.snapshot(now=datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc))
    I = snap["issues"]
    assert I["live"] is True and I["fell_back"] is False
    assert I["open"] == 3, "the committed file says 1; the page must show the live count"
    assert snap["issues_source"] == "the GitHub API, live"


def test_a_live_backlog_raises_no_staleness_alert_though_the_file_is_two_weeks_old(
        committed, monkeypatch):
    with _stub(monkeypatch, [[_issue(1)]]):
        snap = ops_data.snapshot(now=datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc))
    assert not [a for a in snap["alerts"] if "Backlog" in a["title"]]


def test_a_failed_live_call_shows_the_committed_count_and_raises_an_alert(
        committed, monkeypatch):
    with _stub(monkeypatch, urllib.error.URLError("no route")):
        snap = ops_data.snapshot(now=datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc))
    I = snap["issues"]
    assert I["ok"] is True, "a failed fetch must not blank the panel"
    assert I["live"] is False and I["fell_back"] is True
    assert I["open"] == committed["open"] == 1
    alerts = [a for a in snap["alerts"] if a["title"].startswith("Backlog fell back")]
    assert len(alerts) == 1 and alerts[0]["level"] == "amber"
    # And the age is shown, because the number now IS as-of a time.
    assert snap["ages"]["Backlog"]["stale"] is True


def test_the_live_backlog_carries_the_objective_from_the_committed_file(
        committed, monkeypatch):
    """OBJECTIVE.md is not in the container, so the API cannot supply it."""
    with _stub(monkeypatch, [[_issue(1)]]):
        snap = ops_data.snapshot(now=datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc))
    assert snap["issues"]["live"] is True
    assert snap["objective"] == "the committed objective"


def test_pinning_the_page_to_the_snapshot_makes_no_api_call_and_is_not_a_fallback(
        committed, monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    with _stub(monkeypatch, []) as calls:
        snap = ops_data.snapshot(now=datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc))
    assert calls == []
    I = snap["issues"]
    # Not a fallback: nothing failed. The distinction is what keeps the alert
    # strip honest in an environment deliberately configured without egress.
    assert I["live"] is False and I["fell_back"] is False
    assert not [a for a in snap["alerts"] if a["title"].startswith("Backlog fell back")]


def test_one_render_makes_one_api_call_however_many_panels_read_the_backlog(
        committed, monkeypatch):
    with _stub(monkeypatch, [[_issue(1)]]) as calls:
        ops_data.snapshot(now=datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc))
        ops_data.snapshot(now=datetime(2026, 10, 15, 6, 1, tzinfo=timezone.utc))
    assert len(calls) == 1, "the 300s cache is what keeps this inside the API budget"
