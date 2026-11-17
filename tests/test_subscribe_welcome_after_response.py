"""/subscribe must answer BEFORE it sends the welcome email (#1163).

Before: a new address built and sent the welcome inside the request (~300-2300 ms
in #1159's QA round) while an existing address returned in ~2-40 ms. The body was
identical, so the response time was the only thing telling an anonymous caller
whether an address was already on the list.

Starlette's TestClient (and httpx's ASGITransport) run the whole app, background
tasks included, before they hand back a response, so `client.post` cannot tell
"sent inside the request" from "sent after it". The app is therefore wrapped in a
thin ASGI spy that notes, at the moment the LAST response byte leaves the app,
whether the welcome stub has finished. The stub blocks on a threading.Event that
only the spy sets, so:

  * welcome after the response -> the stub is still blocked when the body goes
    out; the spy releases it and it finishes;
  * welcome inline             -> the stub blocks the request until its own
    timeout, so it has FINISHED by the time the body goes out.

No wall-clock bound is asserted; the ordering is the claim. The stub's timeout only
bounds how long the broken variant takes to fail.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading

import pytest
from fastapi.testclient import TestClient

from astro_ai import notify, storage, subscribers
from astro_ai.main import app
from astro_ai.routes import subscribe as subscribe_routes

EXISTING = "present@example.com"
NEW = "arrival@example.com"

# Generous: only the inline (broken) variant ever waits for it.
_STUB_TIMEOUT_S = 3.0


@pytest.fixture
def blob(monkeypatch):
    state = {"subscribers": [
        {"email": EXISTING, "lang": "en", "city": "", "rashi": "all",
         "subscribed_at": "2026-01-01T00:00:00+00:00"},
    ]}

    def get_json(key):
        return json.loads(json.dumps(state)) if key == subscribers.SUBSCRIBERS_KEY else None

    def update_json(key, mutator, *, default=None, max_retries=5):
        new = mutator(json.loads(json.dumps(state)))
        state.clear()
        state.update(new)
        return new

    monkeypatch.setattr(storage, "get_json", get_json)
    monkeypatch.setattr(storage, "update_json", update_json)
    return state


class _Spy:
    """ASGI wrapper recording what had happened when the response body left."""

    def __init__(self, inner, release: threading.Event, finished: threading.Event):
        self.inner = inner
        self.release = release
        self.finished = finished
        self.finished_when_body_sent: bool | None = None

    async def __call__(self, scope, receive, send):
        async def spy_send(message):
            if (scope["type"] == "http" and message["type"] == "http.response.body"
                    and not message.get("more_body", False)
                    and scope["path"] == "/subscribe"):
                self.finished_when_body_sent = self.finished.is_set()
                self.release.set()
            await send(message)

        await self.inner(scope, receive, spy_send)


def _slow_welcome(calls, release, finished):
    def _welcome(email, lang, city="", rashi="all"):
        calls.append(email)
        release.wait(timeout=_STUB_TIMEOUT_S)
        finished.set()
        return True
    return _welcome


def test_the_welcome_email_is_sent_after_the_response_not_inside_it(blob, monkeypatch):
    release, finished, calls = threading.Event(), threading.Event(), []
    monkeypatch.setattr(subscribe_routes, "_send_welcome_email",
                        _slow_welcome(calls, release, finished))
    monkeypatch.setattr(notify, "subscribed", lambda **k: None)
    spy = _Spy(app, release, finished)

    r = TestClient(spy).post("/subscribe", data={"email": NEW})

    assert r.status_code == 200 and r.json() == {"ok": True}
    assert spy.finished_when_body_sent is False, (
        "the welcome email had already finished when the response was sent: it ran "
        "inside the request, so a new address is slower than an existing one (#1163)")
    # ...and it did still run, once, to completion, after the response.
    assert calls == [NEW]
    assert finished.is_set()


def test_an_existing_address_sends_no_welcome_and_returns_the_same_body(blob, monkeypatch):
    calls = []
    monkeypatch.setattr(subscribe_routes, "_send_welcome_email",
                        lambda *a, **k: calls.append(a[0]) or True)
    monkeypatch.setattr(notify, "subscribed", lambda **k: None)
    client = TestClient(app)

    existing = client.post("/subscribe", data={"email": EXISTING})
    fresh = client.post("/subscribe", data={"email": NEW})

    assert calls == [NEW], "welcome must go to the new address exactly once, never the existing one"
    assert (existing.status_code, existing.text) == (fresh.status_code, fresh.text)
    assert existing.json() == {"ok": True}


def test_an_invalid_email_sends_no_welcome(blob, monkeypatch):
    calls = []
    monkeypatch.setattr(subscribe_routes, "_send_welcome_email",
                        lambda *a, **k: calls.append(a[0]) or True)
    monkeypatch.setattr(notify, "subscribed", lambda **k: None)

    r = TestClient(app).post("/subscribe", data={"email": "not-an-email"})

    assert r.status_code == 400 and r.json()["ok"] is False
    assert calls == []


def test_the_telegram_alert_is_raised_on_the_event_loop_not_a_worker_thread(blob, monkeypatch):
    """notify() schedules with get_event_loop().create_task and silently skips on
    RuntimeError, so called from the background task's threadpool thread the alert
    would vanish with nothing logged. It must fire where a loop is running."""
    seen = []

    def spy_subscribed(**kwargs):
        try:
            asyncio.get_running_loop()
            running = True
        except RuntimeError:
            running = False
        seen.append((running, kwargs["email"]))

    monkeypatch.setattr(subscribe_routes, "_send_welcome_email", lambda *a, **k: True)
    monkeypatch.setattr(notify, "subscribed", spy_subscribed)

    TestClient(app).post("/subscribe", data={"email": NEW})
    TestClient(app).post("/subscribe", data={"email": EXISTING})

    assert seen == [(True, NEW)], (
        "notify.subscribed must be called once, for the new address only, with a "
        f"running event loop; got {seen}")


def test_a_failed_welcome_is_logged_and_does_not_break_the_response(blob, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("brevo down")

    monkeypatch.setattr(subscribe_routes, "_send_welcome_email", boom)
    monkeypatch.setattr(notify, "subscribed", lambda **k: None)

    with caplog.at_level(logging.WARNING, logger=subscribe_routes.__name__):
        r = TestClient(app).post("/subscribe", data={"email": NEW})

    assert r.status_code == 200 and r.json() == {"ok": True}
    msgs = [rec.getMessage() for rec in caplog.records]
    assert any(m == f"welcome email failed for {NEW}: brevo down" for m in msgs), msgs
