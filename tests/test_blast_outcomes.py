"""`/admin/send-daily-rashifal` must report what actually happened.

This endpoint returned a literal `{"ok": True}` and HTTP 200 on its last line
regardless of outcome — it could fail to deliver to every subscriber and still
look healthy. It then failed silently for **21 consecutive days**, and nobody
noticed, because nothing it returned or logged said otherwise.

`ok` now means "subscribers got their email", and a bad outcome returns 500 so
it also registers in the `rashifal_cron_failures` log metric, which counts
status >= 400. A lying 200 registered as healthy there too.

Nothing here sends mail: `email_sender.send` is stubbed in every test and
asserted against. If you add a case, stub it first.
"""
from __future__ import annotations

import pytest

SECTIONS = "\n\n".join(
    f"## {r}\n" + "A steady day for measured work. " * 40
    for r in (
        "Aries / Mesha", "Taurus / Vrishabha", "Gemini / Mithuna", "Cancer / Karka",
        "Leo / Simha", "Virgo / Kanya", "Libra / Tula", "Scorpio / Vrishchika",
        "Sagittarius / Dhanu", "Capricorn / Makara", "Aquarius / Kumbha", "Pisces / Meena",
    )
)


def _subscriber(email: str = "a@example.test", **over) -> dict:
    return {"email": email, "lang": "en", "rashi": "all", "city": "Delhi", **over}


@pytest.fixture
def admin_headers():
    """Override the auth dependency instead of supplying a password.

    This used to read ADMIN_PASSWORD from the environment or `.env` and
    `pytest.skip` when neither had it. `.env` is gitignored, so on a fresh
    clone all eight of these tests skipped, pytest exited 0, and
    `verify_behaviour.py` printed PASS — a third of the suite silently absent
    while the gate reported green. A test that skips itself into a pass is
    worse than a missing test, because it looks like coverage.

    Overriding the dependency makes them hermetic: no secret, no environment,
    no skip. Auth itself is not what these tests are about.
    """
    from astro_ai.main import app
    from astro_ai.routes.deps import require_admin

    app.dependency_overrides[require_admin] = lambda: None
    yield {}
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def blast(monkeypatch):
    """The route with generation stubbed and mail sending disarmed."""
    from astro_ai.routes import subscribe

    monkeypatch.setattr(subscribe, "_daily_rashifal_text", lambda **k: SECTIONS)
    sent: list[str] = []

    def _configure(subscribers, send_result=True):
        monkeypatch.setattr(subscribe.subscribers, "list_subscribers",
                            subscribers if callable(subscribers) else (lambda: subscribers))

        def fake_send(email, **k):
            sent.append(email)
            return send_result

        monkeypatch.setattr(subscribe.email_sender, "send", fake_send)
        return sent

    return _configure


def _post(client, headers):
    r = client.post("/admin/send-daily-rashifal", headers=headers)
    return r.status_code, r.json()


def test_healthy_send_reports_ok(client, admin_headers, blast):
    sent = blast([_subscriber("a@x.test"), _subscriber("b@x.test")])
    code, body = _post(client, admin_headers)

    assert (code, body["ok"]) == (200, True)
    assert (body["sent"], body["failed"], body["total_subscribers"]) == (2, 0, 2)
    assert sent == ["a@x.test", "b@x.test"]


def test_total_delivery_failure_is_not_reported_as_success(client, admin_headers, blast):
    """The defect: this returned 200 / ok:true while reaching nobody."""
    blast([_subscriber()], send_result=False)
    code, body = _post(client, admin_headers)

    assert code == 500, "a blast that reached nobody must not return 200"
    assert body["ok"] is False
    assert (body["sent"], body["failed"]) == (0, 1)


def test_partial_failure_is_surfaced(client, admin_headers, blast):
    from astro_ai.routes import subscribe

    subs = [_subscriber("good@x.test"), _subscriber("bad@x.test")]
    blast(subs)
    subscribe.email_sender.send = lambda email, **k: email != "bad@x.test"

    code, body = _post(client, admin_headers)

    assert code == 500 and body["ok"] is False
    assert (body["sent"], body["failed"]) == (1, 1)
    assert "bad@x.test" in body["failed_emails"]


def test_zero_subscribers_is_not_a_failure(client, admin_headers, blast):
    """An empty list is a legitimate quiet day, not an outage. Treating it as
    one would fire an alert and poison the cron-failure metric every time."""
    blast([])
    code, body = _post(client, admin_headers)

    assert (code, body["ok"]) == (200, True)
    assert (body["sent"], body["failed"], body["total_subscribers"]) == (0, 0, 0)


def test_signup_landing_mid_run_is_not_a_false_failure(client, admin_headers, blast):
    """Defect: `list_subscribers()` was called twice — once to send, once to
    count — so `total` described a different population from the one we sent
    to. A signup arriving between the two gave sent=0 with total=1, which read
    as "delivered to nobody": HTTP 500, a false alert, and a false entry in the
    metric.

    The tell was sent=0 WITH failed=0, which is impossible for a real failure.
    """
    calls = {"n": 0}

    def signup_mid_run():
        calls["n"] += 1
        return [] if calls["n"] == 1 else [_subscriber()]

    blast(signup_mid_run)
    code, body = _post(client, admin_headers)

    assert (code, body["ok"]) == (200, True), f"false failure: {body}"
    assert calls["n"] == 1, f"subscriber list read {calls['n']}x; capture it once"


@pytest.mark.parametrize("subs,send_ok", [
    ([_subscriber()], True),
    ([_subscriber(), _subscriber("b@x.test")], False),
    ([], True),
])
def test_sent_plus_failed_always_equals_total(client, admin_headers, blast, subs, send_ok):
    """The invariant a monitor relies on. It only holds because the subscriber
    list is read once."""
    blast(subs, send_result=send_ok)
    _code, body = _post(client, admin_headers)

    assert body["sent"] + body["failed"] == body["total_subscribers"], body
