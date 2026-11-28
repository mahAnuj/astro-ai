"""A measurements file whose top level is not a JSON object must not 500 /admin/ops (#1542).

`[1]`, `"x"` and `5` all parse, and every reader calls `.get` on what `_fetch` hands it, so
`_loop_view` raised AttributeError out of `snapshot()` (documented "never raises") and every tab
died. The fix is at the one choke point: `_fetch` returns a JSON object or None. These tests use
the REAL `_fetch` against files in a tmp dir; replacing `_fetch` would test nothing.
"""
from __future__ import annotations

import json
import os
import urllib.request

import pytest

from astro_ai import agent_status, ops_data, ops_tabs

KEYS = [k for k, _ in ops_tabs.TABS]
# Every file ops_data fetches: FILES plus the three read outside that tuple.
ALL_FILES = ("agents.json", "claude_usage.json", "cost.json", "ga4-daily.json", "growth.json",
             "gsc-daily.json", "gsc-trend-page.json", "gsc-trend-query.json",
             "index-status.json", "issues.json", "loop.json", "outbox.json")
# Valid JSON that is not an object. "[]" and "null" are falsy, "[1]" / '"x"' / "5" / "true" are not,
# which is the case `if not doc` let through.
NON_OBJECTS = ["[1]", '"x"', "5", "[]", "null", "true"]


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


def test_the_matrix_covers_every_file_ops_data_fetches():
    src = open(ops_data.__file__).read()
    import re
    fetched = set(re.findall(r'_fetch\("([^"]+)"\)', src))
    assert fetched <= set(ALL_FILES), fetched - set(ALL_FILES)
    assert set(ops_data.FILES) <= set(ALL_FILES)


def _page(key: str):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get(f"/admin/ops?tab={key}", auth=("admin", pw))


def _write(tmp_path, names, raw):
    for n in names:
        (tmp_path / n).write_text(raw)
    ops_data._cache.clear()
    ops_data._app_cache.clear()


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("raw", NON_OBJECTS)
def test_every_file_a_non_object_does_not_500_any_tab(tmp_path, raw, key):
    _write(tmp_path, ALL_FILES, raw)
    assert _page(key).status_code == 200


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("name", ALL_FILES)
def test_one_file_a_list_does_not_500_any_tab(tmp_path, name, key):
    _write(tmp_path, [name], "[1]")
    assert _page(key).status_code == 200


@pytest.mark.parametrize("key", KEYS)
def test_an_empty_object_everywhere_is_still_a_page(tmp_path, key):
    _write(tmp_path, ALL_FILES, "{}")
    assert _page(key).status_code == 200


@pytest.mark.parametrize("raw", NON_OBJECTS)
def test_fetch_is_none_for_a_non_object_file(tmp_path, raw):
    _write(tmp_path, ["loop.json"], raw)
    assert ops_data._fetch("loop.json") is None


def test_an_empty_object_is_a_valid_document(tmp_path):
    _write(tmp_path, ["loop.json"], "{}")
    assert ops_data._fetch("loop.json") == {}


class _Resp:
    def __init__(self, body: str):
        self._b = body.encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _stub_https(monkeypatch, body: str):
    calls = []

    def fake(url, timeout=None):
        calls.append(url)
        return _Resp(body)
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return calls


def test_a_bad_disk_file_falls_through_to_https(tmp_path, monkeypatch):
    _write(tmp_path, ["loop.json"], "[1]")
    calls = _stub_https(monkeypatch, json.dumps({"rows": []}))
    assert ops_data._fetch("loop.json") == {"rows": []}
    assert len(calls) == 1


def test_a_non_object_https_body_is_none(monkeypatch):
    calls = _stub_https(monkeypatch, "[1]")
    assert ops_data._fetch("loop.json") is None
    assert len(calls) == 1


def test_a_rejected_value_is_not_cached(tmp_path):
    _write(tmp_path, ["loop.json"], "[1]")
    assert ops_data._fetch("loop.json") is None
    assert "loop.json" not in ops_data._cache
    (tmp_path / "loop.json").write_text('{"rows": []}')
    assert ops_data._fetch("loop.json") == {"rows": []}


def test_the_log_names_the_type_and_never_the_content(tmp_path, caplog):
    _write(tmp_path, ["loop.json"], '["SECRET-CONTENT"]')
    with caplog.at_level("WARNING", logger=ops_data.log.name):
        ops_data._fetch("loop.json")
    assert "loop.json" in caplog.text and "list" in caplog.text
    assert "SECRET-CONTENT" not in caplog.text


def test_agent_status_loops_tolerates_a_list_agents_file(tmp_path):
    _write(tmp_path, ["agents.json"], "[1]")
    assert agent_status._loops() == []
