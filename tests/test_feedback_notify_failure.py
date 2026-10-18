"""A notification failure must not turn a SAVED submission into a 500 (#408).

WHY THIS IS HERE, given the charter in conftest.py.

This is a defect that shipped. `routes/feedback.py` had `import logging` inside
the email `except` block. Python fixes scope at compile time, so that made
`logging` function-local for the whole of `submit_feedback` -- including the
Telegram handler that runs EARLIER, which calls `logging.getLogger(...)` and
raised UnboundLocalError. The row was already stored, so the visitor was shown a
500 for a submission that had succeeded.

#183 added that handler to stop a broken channel being invisible; it was the
handler itself that broke. Nothing exercised a notify failure, so it sat live.

These drive the real route body with the failing channel and assert what the
visitor gets (200 `{"ok": true}`), that the row was stored, and that the failure
is LOGGED rather than swallowed (#183's intent).
"""
from __future__ import annotations

import asyncio
import json
import logging

import pytest

from astro_ai import feedback as feedback_store
from astro_ai.routes import feedback as feedback_route


@pytest.fixture
def stored(monkeypatch):
    """Stub the store (no GCS) and record that the row was saved."""
    box: list[dict] = []
    entry = {"type": "problem", "message": "hello", "email": "", "page": "/x",
             "ts": "2026-10-18T00:00:00Z", "id": "abc123"}

    def _add(**kw):
        box.append(kw)
        return True, "", entry

    monkeypatch.setattr(feedback_store, "add", _add)
    return box


def _submit():
    class _Req:
        headers: dict = {}

    return asyncio.new_event_loop().run_until_complete(
        feedback_route.submit_feedback(_Req(), type="problem", message="hello",
                                       email="", page="/x"))


def _boom(*_a, **_kw):
    raise RuntimeError("channel down")


def test_a_telegram_failure_does_not_500_a_saved_submission(monkeypatch, stored, caplog):
    monkeypatch.setattr(feedback_route.notify, "feedback_submitted", _boom)
    monkeypatch.delenv("BHAGYA_EMAIL_FROM", raising=False)
    with caplog.at_level(logging.WARNING):
        resp = _submit()
    assert resp.status_code == 200
    assert json.loads(resp.body) == {"ok": True}
    assert len(stored) == 1, "the row must have been stored"
    # Logged, not swallowed (#183).
    assert any("Telegram notify failed" in r.getMessage() and "channel down" in r.getMessage()
               for r in caplog.records)


def test_an_email_failure_does_not_500_a_saved_submission(monkeypatch, stored, caplog):
    monkeypatch.setattr(feedback_route.notify, "feedback_submitted", lambda **kw: None)
    monkeypatch.setattr(feedback_route.email_sender, "send", _boom)
    monkeypatch.setenv("BHAGYA_EMAIL_FROM", "owner@example.test")
    with caplog.at_level(logging.WARNING):
        resp = _submit()
    assert resp.status_code == 200
    assert json.loads(resp.body) == {"ok": True}
    assert len(stored) == 1
    assert any("admin feedback notification failed" in r.getMessage()
               and "channel down" in r.getMessage() for r in caplog.records)


def test_both_channels_failing_still_returns_success(monkeypatch, stored, caplog):
    # The two handlers share one function scope; this is the composed body.
    monkeypatch.setattr(feedback_route.notify, "feedback_submitted", _boom)
    monkeypatch.setattr(feedback_route.email_sender, "send", _boom)
    monkeypatch.setenv("BHAGYA_EMAIL_FROM", "owner@example.test")
    with caplog.at_level(logging.WARNING):
        resp = _submit()
    assert resp.status_code == 200
    assert len(stored) == 1
    msgs = [r.getMessage() for r in caplog.records]
    assert any("Telegram notify failed" in m for m in msgs)
    assert any("admin feedback notification failed" in m for m in msgs)
