"""#1506: the per-route HTTP 5xx count the weekly measurement reads.

Asserts what the visitor gets and what lands in the day blob, against the REAL app
(`astro_ai.main.app`) with a few probe routes added for the test: the middleware's position
in that stack is what decides whether production labels a route or says "unmatched", and a
hand-built app cannot show it. Hermetic: no bucket, the local fallback dir is tmp_path.
"""
from __future__ import annotations

import asyncio
import json
import types
from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.testclient import TestClient
from starlette.requests import ClientDisconnect

from astro_ai import http_errors, main, storage

P = "/__t1506"


@pytest.fixture
def probe(tmp_path, monkeypatch):
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setenv("BHAGYA_HTTP_ERRORS_FALLBACK_DIR", str(tmp_path / "he"))
    clock = {"t": 1000.0}
    monkeypatch.setattr(http_errors, "time", types.SimpleNamespace(monotonic=lambda: clock["t"]))
    monkeypatch.setattr(http_errors, "_LAST_FLUSH", clock["t"])   # nothing flushes until asked
    monkeypatch.setattr(http_errors, "_PENDING", {})
    writes = []
    real = storage.update_json

    def _spy(key, mutator, **kw):
        if key.startswith("http_errors/"):      # the error path also writes events/
            writes.append(key)
        return real(key, mutator, **kw)

    monkeypatch.setattr(storage, "update_json", _spy)

    @main.app.get(P + "/boom/{slug}")
    def _boom(slug: str):
        raise RuntimeError("1506 probe")

    @main.app.get(P + "/unavail/{slug}")
    def _unavail(slug: str):
        raise HTTPException(503, "down")

    @main.app.get(P + "/inline/{slug}")
    def _inline(slug: str):
        return Response("inline-body", status_code=502)

    @main.app.get(P + "/ok")
    def _ok():
        return Response("fine")

    @main.app.get(P + "/moved")
    def _moved():
        return RedirectResponse(P + "/ok", status_code=301)

    @main.app.get(P + "/bad")
    def _bad():
        raise HTTPException(400, "nope")

    added = len(main.app.router.routes)
    client = TestClient(main.app, raise_server_exceptions=False)
    yield types.SimpleNamespace(client=client, clock=clock, writes=writes, dir=tmp_path / "he")
    del main.app.router.routes[added - 6:added]


def _blob(p) -> dict:
    return json.loads((p.dir / f"{date.today().isoformat()}.json").read_text())


def test_5xx_counts_under_the_template_and_the_response_is_unchanged(probe):
    for slug in ("abc", "xyz"):
        assert probe.client.get(f"{P}/boom/{slug}").status_code == 500
        r = probe.client.get(f"{P}/unavail/{slug}")
        assert r.status_code == 503
        r = probe.client.get(f"{P}/inline/{slug}")
        assert (r.status_code, r.text) == (502, "inline-body")
    http_errors.flush_on_shutdown()
    assert _blob(probe)["by_route"] == {
        f"GET {P}/boom/{{slug}}": {"500": 2},
        f"GET {P}/unavail/{{slug}}": {"503": 2},
        f"GET {P}/inline/{{slug}}": {"502": 2},
    }


def test_the_template_survives_the_forwarded_host_rewrite(probe):
    """Firebase always sets X-Forwarded-Host; the rewrite copies the scope, and a middleware
    outside it reads no route -- every production 5xx would be 'unmatched'."""
    h = {"X-Forwarded-Host": "shubhagya.com"}
    assert probe.client.get(f"{P}/boom/abc", headers=h).status_code == 500
    assert probe.client.get(f"{P}/inline/abc", headers=h).status_code == 502
    http_errors.flush_on_shutdown()
    labels = set(_blob(probe)["by_route"])
    assert labels == {f"GET {P}/boom/{{slug}}", f"GET {P}/inline/{{slug}}"}


def test_the_middleware_is_innermost_so_it_sees_the_route():
    names = [m.cls.__name__ for m in main.app.user_middleware]   # outermost first
    assert names.index("HttpErrorMiddleware") > names.index("_RewriteHostFromForwardedMiddleware")


def test_non_5xx_responses_count_nothing(probe):
    assert probe.client.get(f"{P}/ok").status_code == 200
    assert probe.client.get(f"{P}/moved", follow_redirects=False).status_code == 301
    assert probe.client.get(f"{P}/bad").status_code == 400
    assert probe.client.get(f"{P}/no-such-page-1506").status_code == 404
    assert http_errors._PENDING == {}
    http_errors.flush_on_shutdown()
    assert probe.writes == []


def test_distinct_raw_paths_share_one_label_and_labels_are_capped(probe):
    for i in range(150):
        probe.client.get(f"{P}/boom/s{i}")
    assert http_errors._PENDING == {f"GET {P}/boom/{{slug}}": {"500": 150}}
    http_errors._PENDING.clear()
    for i in range(http_errors.MAX_ROUTES + 50):
        http_errors.count(f"GET /r{i}", 500)
    assert len(http_errors._PENDING) == http_errors.MAX_ROUTES
    assert sum(n for s in http_errors._PENDING.values() for n in s.values()) == http_errors.MAX_ROUTES + 50
    assert sum(http_errors._PENDING["other"].values()) == 51


def test_the_day_blob_is_capped_when_merging_into_a_nearly_full_one(probe):
    probe.dir.mkdir(parents=True)
    full = {f"GET /old{i}": {"500": 1} for i in range(http_errors.MAX_ROUTES - 1)}
    (probe.dir / f"{date.today().isoformat()}.json").write_text(json.dumps({"by_route": full}))
    http_errors.count("GET /new-a", 500)
    http_errors.count("GET /new-b", 503)
    http_errors.flush_on_shutdown()
    by_route = _blob(probe)["by_route"]
    assert len(by_route) == http_errors.MAX_ROUTES
    assert by_route["other"] == {"500": 1, "503": 1}


def test_a_burst_inside_one_interval_is_one_write_and_no_count_is_lost(probe):
    probe.clock["t"] = 5000.0
    http_errors._LAST_FLUSH = float("-inf")             # the process's first 5xx
    for i in range(20):
        probe.client.get(f"{P}/boom/s{i}")
    assert len(probe.writes) == 1                       # not one write per failed request
    http_errors.flush_on_shutdown()
    assert len(probe.writes) == 2
    assert _blob(probe)["by_route"][f"GET {P}/boom/{{slug}}"] == {"500": 20}
    probe.clock["t"] += http_errors.FLUSH_MIN_INTERVAL_S
    probe.client.get(f"{P}/boom/late")                  # the interval elapsed: due again
    assert len(probe.writes) == 3


def test_a_storage_failure_never_changes_the_response_and_the_count_is_kept(probe, monkeypatch):
    def _down(*a, **k):
        raise OSError("bucket down")

    (probe.dir.parent / "blocker").write_text("a file where the fallback dir must go")
    monkeypatch.setenv("BHAGYA_HTTP_ERRORS_FALLBACK_DIR", str(probe.dir.parent / "blocker" / "x"))
    monkeypatch.setattr(storage, "update_json", _down)
    probe.clock["t"] = 9000.0
    http_errors._LAST_FLUSH = float("-inf")
    r = probe.client.get(f"{P}/inline/abc")
    assert (r.status_code, r.text) == (502, "inline-body")
    assert probe.client.get(f"{P}/boom/abc").status_code == 500
    assert sum(n for s in http_errors._PENDING.values() for n in s.values()) == 2   # re-queued
    # ...and lands once storage is back.
    monkeypatch.setenv("BHAGYA_HTTP_ERRORS_FALLBACK_DIR", str(probe.dir))
    monkeypatch.setattr(storage, "update_json", lambda *a, **k: None)
    http_errors.flush_on_shutdown()
    assert http_errors._PENDING == {}
    assert sum(sum(v.values()) for v in _blob(probe)["by_route"].values()) == 2


def _call(app, scope_extra=None):
    """Drive the middleware with a stub ASGI app; returns the messages it forwarded."""
    sent = []

    async def _receive():
        return {"type": "http.request"}

    async def _send(m):
        sent.append(m)

    scope = {"type": "http", "method": "GET", "path": "/x", **(scope_extra or {})}
    asyncio.run(http_errors.HttpErrorMiddleware(app)(scope, _receive, _send))
    return sent


def test_an_unhandled_exception_is_counted_and_re_raised_unchanged(probe):
    async def _app(scope, receive, send):
        raise ValueError("kept")

    with pytest.raises(ValueError, match="kept"):
        _call(_app)
    assert http_errors._PENDING == {"GET unmatched": {"500": 1}}


def test_a_client_disconnect_is_not_a_server_fault(probe):
    async def _app(scope, receive, send):
        raise ClientDisconnect()

    with pytest.raises(ClientDisconnect):
        _call(_app)
    assert http_errors._PENDING == {}


def test_messages_are_forwarded_untouched_and_non_http_scopes_pass_through(probe):
    async def _app(scope, receive, send):
        await send({"type": "http.response.start", "status": 503, "headers": [(b"x", b"y")]})
        await send({"type": "http.response.body", "body": b"b"})

    sent = _call(_app)
    assert sent == [{"type": "http.response.start", "status": 503, "headers": [(b"x", b"y")]},
                    {"type": "http.response.body", "body": b"b"}]
    seen = []

    async def _ws(scope, receive, send):
        seen.append(scope["type"])

    asyncio.run(http_errors.HttpErrorMiddleware(_ws)({"type": "websocket"}, None, None))
    assert seen == ["websocket"]


def test_range_summary_skips_what_a_hand_edited_blob_got_wrong(probe):
    probe.dir.mkdir(parents=True)
    today = date.today()
    (probe.dir / f"{today.isoformat()}.json").write_text(json.dumps({"by_route": {
        "GET /a": {"500": 2, "503": True, "502": -1, "504": "3", "404": 9, "x": 1},
        "GET /b": ["not", "a", "dict"],
        "GET /c": {"500": 1}}}))
    (probe.dir / f"{date.fromordinal(today.toordinal() - 1).isoformat()}.json").write_text(
        json.dumps({"by_route": ["list"]}))
    s = http_errors.range_summary(7, today)
    assert s["total"] == 3 and s["days_recorded"] == 2 and s["days"] == 7
    assert s["by_route"] == {"GET /a": {"total": 2, "by_status": {"500": 2}},
                             "GET /c": {"total": 1, "by_status": {"500": 1}}}
    assert (s["from"], s["to"]) == (date.fromordinal(today.toordinal() - 6).isoformat(), today.isoformat())


def test_label_for_never_carries_the_raw_path_or_an_unknown_method():
    assert http_errors.label_for({"method": "BREW", "path": "/secret/token"}) == "OTHER unmatched"
    route = types.SimpleNamespace(path="/learn/{slug}")
    assert http_errors.label_for({"method": "GET", "route": route, "path": "/learn/abc"}) == "GET /learn/{slug}"


def test_count_books_only_status_500_to_599(probe):
    for status in (200, 301, 400, 404, 499, 600, 0, "abc", None):
        http_errors.count("GET /x", status)
    assert http_errors._PENDING == {}
    http_errors.count("GET /x", 599)
    assert http_errors._PENDING == {"GET /x": {"599": 1}}
