"""The /admin/ops "Google index status" panel (#1065, subtask 2).

`ops_data._index_view` passes `measurements/index-status.json` through. It never
re-ranks the collector's `request_indexing` list, only bounds and sanitises it,
and it must never take the page down: a missing or garbled file is the ordinary
state until the first collection.

The realistic document is built by the collector's own `build_doc` over a fake
`post`, so the panel is read against the shape the collector really writes. As in
test_fetch_index_status.py, the Google response shape is doc-derived, not observed.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import llm_stats, ops_data

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "fetch_index_status_ops", ROOT / "scripts" / "fetch_index_status.py")
fis = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fis)

SITE, BASE = "sc-domain:shubhagya.com", "https://shubhagya.com"
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
HOSTILE = "<script>x</script>"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _collected_doc(n=14, quota_after=None) -> dict:
    """What the collector writes for `n` unindexed pages, via its own code."""
    paths = [f"/learn/page-{i:02d}/" for i in range(n)]
    entries = [{"url": BASE + p, "priority": 0.7} for p in paths]
    impressions = {BASE + p: 100 - i for i, p in enumerate(paths)}
    seen = []

    def post(url, body, bearer):
        seen.append(body["inspectionUrl"])
        if quota_after is not None and len(seen) > quota_after:
            raise fis.ApiError("HTTP 429 from searchconsole.googleapis.com", 429)
        return {"inspectionResult": {"indexStatusResult": {
            "verdict": "NEUTRAL", "coverageState": "Discovered - currently not indexed",
            "robotsTxtState": "ALLOWED", "indexingState": "INDEXING_ALLOWED"}}}

    orig = fis.post
    fis.post = post
    try:
        result = fis.run(entries, SITE, "tok", ROOT, impressions)
    finally:
        fis.post = orig
    doc = fis.build_doc(result, SITE, BASE + "/sitemap.xml", impressions, "gsc-trend-page.json")
    doc["generated_at"] = _iso(NOW - timedelta(hours=3))
    return doc


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._cache.clear()
    ops_data._app_cache.clear()
    yield
    ops_data._cache.clear()
    ops_data._app_cache.clear()


@pytest.fixture
def mdir(monkeypatch, tmp_path):
    d = tmp_path / "m"
    d.mkdir()
    monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(d))
    return d


def _put(mdir, doc=None, raw=None):
    (mdir / "index-status.json").write_text(raw if raw is not None else json.dumps(doc))
    ops_data._cache.clear()


def _page(client, monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
    r = client.get("/admin/ops", auth=("admin", "bhagya-dev"))
    assert r.status_code == 200, r.text[:500]
    i = r.text.index('id="index-status"')
    return r.text[i: r.text.index("</section>", i)]


# --- the view -----------------------------------------------------------------

def test_the_panel_says_not_collected_when_the_file_is_absent(mdir):
    v = ops_data._index_view(NOW)
    assert v["ok"] is False and "not collected" in v["message"]
    assert v["pages"] == [] and v["urls"] == ""


@pytest.mark.parametrize("raw", ["not json {", "[]", '"x"', "null", "{}",
                                 '{"counts": 3}', '{"counts": {}, "request_indexing": 7}',
                                 # Right shape, wrong type: `_age` raises TypeError on it, which
                                 # only the view's own outer guard stands between and a 500.
                                 '{"counts": {}, "generated_at": 12345}'])
def test_a_garbage_file_never_raises(mdir, raw):
    _put(mdir, raw=raw)
    v = ops_data._index_view(NOW)
    assert isinstance(v, dict) and "ok" in v
    assert v["pages"] == []


def test_a_collected_file_passes_through_with_its_counts_and_the_collectors_order(mdir):
    doc = _collected_doc()
    _put(mdir, doc)
    v = ops_data._index_view(NOW)
    assert v["ok"] is True
    assert v["counts"]["total"] == 14 and v["counts"]["not_indexed"] == 14
    assert [i["url"] for i in v["pages"]] == [r["url"] for r in doc["request_indexing"]]
    assert v["impressions_matched"] == {"matched": 14, "with_impressions": 14}
    assert v["urls"].splitlines() == [i["url"] for i in v["pages"]]


def test_at_most_ten_items_and_each_has_a_reason(mdir):
    doc = _collected_doc()
    doc["request_indexing"] = [
        {"url": f"{BASE}/p{i}", "reasons": ["not indexed: x"], "impressions": i}
        for i in range(25)]
    _put(mdir, doc)
    v = ops_data._index_view(NOW)
    assert len(v["pages"]) == 10
    assert all(i["reasons"] for i in v["pages"])
    assert len(v["urls"].splitlines()) == 10


def test_malformed_items_are_dropped_not_fatal(mdir):
    doc = _collected_doc()
    doc["request_indexing"] = [None, 5, {"reasons": ["no url"]}, {"url": 9},
                               {"url": BASE + "/ok", "reasons": "not a list", "impressions": "many"}]
    _put(mdir, doc)
    v = ops_data._index_view(NOW)
    assert v["pages"] == [{"url": BASE + "/ok", "reasons": [], "impressions": None}]


def test_partial_and_its_reason_come_through(mdir):
    doc = _collected_doc(quota_after=3)
    assert doc["partial"] is True
    _put(mdir, doc)
    v = ops_data._index_view(NOW)
    assert v["partial"] is True and "429" in v["partial_reason"]
    assert v["counts"]["not_inspected"] == 11


def test_the_file_age_is_stated(mdir):
    _put(mdir, _collected_doc())
    assert ops_data._index_view(NOW)["age"]["text"] == "3h ago"


def test_snapshot_carries_the_view_and_does_not_fail_on_garbage(mdir):
    _put(mdir, raw="}{")
    s = ops_data.snapshot(NOW)
    assert s["index"]["ok"] is False


# --- the page -----------------------------------------------------------------

def test_the_page_renders_the_panel_with_age_counts_list_and_textarea(client, monkeypatch, tmp_path, mdir):
    doc = _collected_doc()
    doc["generated_at"] = _iso(datetime.now(timezone.utc) - timedelta(hours=5))
    _put(mdir, doc)
    s = _page(client, monkeypatch, tmp_path)
    assert "Google index status" in s and "as of 5h ago" in s
    assert "not indexed" in s and "Discovered - currently not indexed" in s
    assert "The run stopped early" not in s  # no banner on a complete run
    assert "<textarea" in s and "readonly" in s
    area = s[s.index("<textarea"): s.index("</textarea>")]
    assert area.count("\n") == 9, "ten URLs, one per line"
    assert BASE + "/learn/page-00/" in area and BASE + "/learn/page-10/" not in area


def test_the_page_shows_the_partial_banner(client, monkeypatch, tmp_path, mdir):
    _put(mdir, _collected_doc(quota_after=3))
    s = _page(client, monkeypatch, tmp_path)
    assert "The run stopped early" in s and "quota: HTTP 429" in s


def test_a_partial_run_with_nothing_to_list_does_not_claim_nothing_is_waiting(
        client, monkeypatch, tmp_path, mdir):
    doc = _collected_doc(quota_after=3)
    doc["request_indexing"] = []
    _put(mdir, doc)
    s = _page(client, monkeypatch, tmp_path)
    assert "have not been checked" in s
    assert "No page is waiting" not in s


def test_a_complete_run_with_nothing_to_list_says_so(client, monkeypatch, tmp_path, mdir):
    doc = _collected_doc()
    doc["request_indexing"] = []
    _put(mdir, doc)
    s = _page(client, monkeypatch, tmp_path)
    assert "No page is waiting on a recrawl request." in s


def test_the_page_says_not_collected_without_the_file(client, monkeypatch, tmp_path, mdir):
    s = _page(client, monkeypatch, tmp_path)
    assert "not collected yet" in s and "<textarea" not in s


def test_the_page_is_200_on_a_garbage_file(client, monkeypatch, tmp_path, mdir):
    _put(mdir, raw="{{{ not json")
    assert "not collected yet" in _page(client, monkeypatch, tmp_path)


def test_strings_from_the_file_are_escaped(client, monkeypatch, tmp_path, mdir):
    doc = _collected_doc()
    doc["request_indexing"] = [{"url": f"{BASE}/{HOSTILE}</textarea>{HOSTILE}",
                                "reasons": [HOSTILE], "impressions": 1}]
    doc["partial"], doc["partial_reason"] = True, HOSTILE
    _put(mdir, doc)
    s = _page(client, monkeypatch, tmp_path)
    assert HOSTILE not in s and "</textarea>" in s
    assert s.count("</textarea>") == 1, "a URL containing </textarea> must not close the box"
    assert "&lt;script&gt;x&lt;/script&gt;" in s
