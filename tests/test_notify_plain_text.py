"""A visitor's text must not reach the owner's Telegram as live markup (#387).

WHY THIS IS HERE, given the charter in conftest.py.

This is a defect that shipped, and the twin of the email hole #373 closed:
`POST /feedback` needs no authentication, `notify.feedback_submitted` puts the
visitor's message straight into the owner's private bot chat, and the message
was sent with `parse_mode: "Markdown"`. The escape helper prefixed `_ * ` [`
with a backslash and never escaped the backslash itself, so a visitor-supplied

    \\[Reset your password](https://shubhagya.com.evil.test)

arrived as `\\\\[Reset your password](...)` -- the doubled backslash is consumed
as one literal backslash and the `[` behind it is left LIVE. A forged clickable
link inside a notification the owner trusts. And if `\\` does NOT escape in
legacy Markdown, the helper escaped nothing in the first place and a plain
`[x](url)` was live all along. Both horns are a hole.

Nothing exercised this path at all: no test named `_escape_md`, none named
`feedback_submitted` except to monkeypatch it to a no-op, and no mutation row on
`notify.py`. So the fix is the one that holds under either horn -- the alert is
sent as PLAIN TEXT, with no parse mode -- and these tests capture the payload
that `httpx` would have been given. Nothing here touches the network.
"""
from __future__ import annotations

import asyncio

import pytest

from astro_ai import notify


# One literal backslash, then the link. The exact string from #387.
FORGERY = "\\[Reset your password](https://shubhagya.com.evil.test)"


@pytest.fixture
def wire(monkeypatch):
    """Capture the sendMessage payload instead of sending it.

    `notify.notify` is replaced by a synchronous drive of the REAL
    `_send_async`, so the assertions below read the actual payload dict the
    transport is handed -- not a reconstruction of it. The HTTP client is a
    stub, so no socket is opened and no token is needed.
    """
    sent: list[dict] = []

    class _Resp:
        status_code = 200
        text = ""

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None):
            sent.append({"url": url, "payload": json})
            return _Resp()

    monkeypatch.setattr(notify.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(
        notify, "notify",
        lambda text, **kw: asyncio.run(
            notify._send_async("fake-token", "fake-chat", text)))
    return sent


def _payload(sent: list[dict]) -> dict:
    assert sent, "nothing was sent"
    return sent[-1]["payload"]


def test_the_telegram_payload_asks_for_no_parse_mode(wire):
    """The whole fix, in one assertion. A parse mode is what turns visitor
    text into markup; without one there is nothing to forge."""
    asyncio.run(notify._send_async("fake-token", "fake-chat", "hello"))
    payload = _payload(wire)
    assert "parse_mode" not in payload, (
        f"visitor-supplied text is being parsed as {payload['parse_mode']!r} "
        f"again -- see #387; the escape in front of it cannot be made sound")
    assert payload["text"] == "hello"


def test_a_visitor_cannot_forge_a_link_in_the_owners_feedback_alert(wire):
    notify.feedback_submitted(type="other", message=FORGERY)
    payload = _payload(wire)
    assert "parse_mode" not in payload
    # The owner reads exactly what was submitted: one backslash, not two, and
    # no inserted escapes. A doubled backslash is the forgery's signature --
    # it is what re-arms the bracket behind it.
    assert FORGERY in payload["text"], payload["text"]
    assert "\\\\" not in payload["text"], payload["text"]


def test_a_visitor_cannot_forge_a_link_through_the_question_field(wire):
    notify.ask_submitted(question=FORGERY, category="other", lang="en")
    payload = _payload(wire)
    assert "parse_mode" not in payload
    assert FORGERY in payload["text"], payload["text"]


def test_visitor_text_reaches_the_owner_verbatim(wire):
    """The notification exists so the owner can read what was actually typed.
    Escaping it mangled that; stripping it would lose it."""
    typed = "a_b *c* `d` [e](f) 100% \\o/"
    notify.feedback_submitted(type="problem", message=typed, page="/kundli",
                              email="visitor@example.test")
    assert typed in _payload(wire)["text"], _payload(wire)["text"]


FORMATTER_CALLS = {
    "kundli_generated": dict(
        lagna="Mesha", moon="Vrishabha", sun="Mithuna", lang="en",
        key="ab12cd34", model="llama-3", tokens=1234, latency_s=1.5,
        cache="miss"),
    "matching_done": dict(
        groom_moon="Mesha", bride_moon="Kanya", total_score="28", lang="en",
        groom_key="ab12cd34", bride_key="ef56ab78"),
    "ask_submitted": dict(
        question="when is a good day to travel", category="travel",
        lang="en", user_email="visitor@example.test", model="llama-3"),
    "new_signin": dict(email="visitor@example.test", name="Vikram",
                       first_time=True),
    "new_signin_without_a_name": dict(email="visitor@example.test", name="",
                                      first_time=False),
    "subscribed": dict(email="visitor@example.test", source="footer",
                       lang="en"),
    "feedback_submitted": dict(type="other", message="the site is useful",
                               page="/kundli", email="visitor@example.test"),
    "feedback_submitted_without_a_message": dict(type="problem", message=""),
    "dosha_checked": dict(dosha_type="Manglik", is_present=True,
                          key="ab12cd34", lagna="Mesha", extra="high"),
    "muhurat_computed": dict(event_type="wedding", city="Pune",
                             days_range=30, good_count=3,
                             user_email="visitor@example.test"),
    "numerology_computed": dict(system="chaldean", life_path=7,
                                key="ab12cd34"),
    "error_seen": dict(source="natal", error_type="ValueError",
                       error_message="boom", path="/kundli", method="GET",
                       user_email="visitor@example.test",
                       traceback_str="Traceback (most recent call last):\n  x"),
}


@pytest.mark.parametrize("event", sorted(FORMATTER_CALLS))
def test_no_formatter_emits_markup_or_escapes(wire, event):
    """Every alert, not just the visitor-facing ones.

    With no parse mode, a `*` or a backtick in the owner's own labels is read
    as a literal `*` or backtick in the notification, and an inserted backslash
    is read as a backslash. None of the inputs above contain any of the three,
    so anything found here was added by the module.
    """
    getattr(notify, event.split("_without")[0])(**FORMATTER_CALLS[event])
    text = _payload(wire)["text"]
    for ch in ("*", "`", "\\"):
        assert ch not in text, f"{event} emits {ch!r} as literal text: {text!r}"
