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


@pytest.fixture
def offline(monkeypatch):
    """Stub the two chart calls the handler makes *before* the send loop.

    `send_daily_rashifal` geocodes a neutral reference chart ("Mumbai, India")
    on every run, so stubbing generation and sending is not enough to keep a
    test off the network — conftest's "no network" rule notwithstanding. The
    older tests in this file predated that and reached Nominatim, so a fresh
    clone with no outbound access reported eight of them red without anything
    being broken (#224). They all take this fixture now; EVERY test that posts
    to the route must, or it is back on the network.

    `compute_panchang` needs no stub: it is only called inside the `call_fn`
    lambda, which `_daily_rashifal_text` (stubbed) never invokes.
    """
    from astro_ai.routes import subscribe

    monkeypatch.setattr(subscribe, "compute_chart", lambda *a, **k: {"stub": "chart"})
    monkeypatch.setattr(subscribe, "compute_transit_snapshot", lambda chart: {})


def _post(client, headers):
    r = client.post("/admin/send-daily-rashifal", headers=headers)
    return r.status_code, r.json()


def test_healthy_send_reports_ok(client, admin_headers, blast, offline):
    sent = blast([_subscriber("a@x.test"), _subscriber("b@x.test")])
    code, body = _post(client, admin_headers)

    assert (code, body["ok"]) == (200, True)
    assert (body["sent"], body["failed"], body["total_subscribers"]) == (2, 0, 2)
    assert sent == ["a@x.test", "b@x.test"]


def test_total_delivery_failure_is_not_reported_as_success(client, admin_headers, blast, offline):
    """The defect: this returned 200 / ok:true while reaching nobody."""
    blast([_subscriber()], send_result=False)
    code, body = _post(client, admin_headers)

    assert code == 500, "a blast that reached nobody must not return 200"
    assert body["ok"] is False
    assert (body["sent"], body["failed"]) == (0, 1)


def test_partial_failure_is_surfaced(client, admin_headers, blast, offline):
    from astro_ai.routes import subscribe

    subs = [_subscriber("good@x.test"), _subscriber("bad@x.test")]
    blast(subs)
    subscribe.email_sender.send = lambda email, **k: email != "bad@x.test"

    code, body = _post(client, admin_headers)

    assert code == 500 and body["ok"] is False
    assert (body["sent"], body["failed"]) == (1, 1)
    assert "bad@x.test" in body["failed_emails"]


def test_zero_subscribers_is_not_a_failure(client, admin_headers, blast, offline):
    """An empty list is a legitimate quiet day, not an outage. Treating it as
    one would fire an alert and poison the cron-failure metric every time."""
    blast([])
    code, body = _post(client, admin_headers)

    assert (code, body["ok"]) == (200, True)
    assert (body["sent"], body["failed"], body["total_subscribers"]) == (0, 0, 0)


def test_signup_landing_mid_run_is_not_a_false_failure(client, admin_headers, blast, offline):
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
def test_sent_plus_failed_always_equals_total(client, admin_headers, blast, offline, subs, send_ok):
    """The invariant a monitor relies on. It only holds because the subscriber
    list is read once."""
    blast(subs, send_result=send_ok)
    _code, body = _post(client, admin_headers)

    assert body["sent"] + body["failed"] == body["total_subscribers"], body


def test_a_raising_subscriber_does_not_abort_the_blast(client, admin_headers, blast, offline, monkeypatch):
    """Defect #220: a raise inside the per-subscriber loop had no handler
    nearer than the app-level one. So one bad row cost every subscriber after
    it their reading, fired NEITHER blast alert (both sit below the loop), and
    never returned the outcome JSON — and Cloud Scheduler runs this job with
    `--max-retry-attempts=0`, so there was no second attempt.

    `email_sender.send` is NOT the raise source despite the issue title: it
    wraps its own HTTP call and returns False. The real ones are the code
    around it, and both are covered here — a row with no `email` key (it was
    subscripted directly at four sites while every other field used `.get()`,
    so the row raised KeyError), and an unexpected raise from the token/render
    code, stubbed onto `unsubscribe_token` for one address.

    Hermetic: the `offline` fixture stubs the pre-loop reference chart and
    `city=""` makes `_panchang_for_city` return None without geocoding, so
    nothing here touches the network.
    """
    from astro_ai.routes import subscribe

    sent = blast([
        _subscriber("first@x.test", city=""),
        {"lang": "en", "rashi": "all", "city": ""},   # no `email` key at all
        _subscriber("boom@x.test", city=""),
        _subscriber("last@x.test", city=""),
    ])

    real_token = subscribe.subscribers.unsubscribe_token

    def exploding_token(email):
        if email == "boom@x.test":
            raise RuntimeError("token backend down")
        return real_token(email)

    monkeypatch.setattr(subscribe.subscribers, "unsubscribe_token", exploding_token)

    alerts: list[str] = []
    monkeypatch.setattr(subscribe, "_fire_error_alert",
                        lambda request, err, source: alerts.append(source))

    code, body = _post(client, admin_headers)

    assert sent == ["first@x.test", "last@x.test"], \
        f"the loop stopped at a bad row instead of continuing: {sent}"
    assert (body["sent"], body["failed"]) == (2, 2), body
    assert body["sent"] + body["failed"] == body["total_subscribers"], body
    assert (code, body["ok"]) == (500, False), body
    assert "rashifal:blast:partial" in alerts, \
        f"a raising subscriber must still reach the partial alert: {alerts}"


def test_partial_alert_carries_no_raw_subscriber_address(client, admin_headers, blast, offline, monkeypatch):
    """Defect #222: the partial alert interpolated `failures[:5]` raw, so up to
    five subscriber addresses went into the Telegram channel AND into
    `events.record`'s `error_message`, which `/admin/activity` renders and GCS
    retains for 30 days. The alert only needs to say how many failed; the app
    log is where identifying data belongs."""
    from astro_ai.routes import subscribe

    blast([_subscriber("good@x.test", city=""), _subscriber("kartik@gmail.test", city="")])
    monkeypatch.setattr(subscribe.email_sender, "send",
                        lambda email, **k: email != "kartik@gmail.test")

    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(subscribe, "_fire_error_alert",
                        lambda request, err, source: messages.append((source, str(err))))

    _post(client, admin_headers)

    partial = [m for source, m in messages if source == "rashifal:blast:partial"]
    assert partial, f"no partial alert fired: {messages}"
    assert "kartik@gmail.test" not in partial[0], f"raw address in alert: {partial[0]}"
    assert "1 of 2" in partial[0], partial[0]
    assert "ka***@gmail.test" in partial[0], partial[0]


def test_masked_address_with_no_at_sign_reveals_nothing(client, admin_headers, blast, offline, monkeypatch):
    """`_mask_email` masks the WHOLE value when there is no `@` to split on.

    The two-character prefix is only safe because a domain follows it; with no
    domain there is nothing to anchor on, so the value could be anything the
    subscribers blob holds and none of it belongs in a Telegram channel or in
    the `/admin/activity` error log GCS keeps for 30 days (#222). Stated in the
    docstring since that fix, but ungated until QA mutated the branch to
    `return email` and the whole suite still passed.
    """
    from astro_ai.routes import subscribe

    blast([_subscriber("good@x.test", city=""), _subscriber("kartik-at-gmail.test", city="")])
    monkeypatch.setattr(subscribe.email_sender, "send",
                        lambda email, **k: email != "kartik-at-gmail.test")

    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(subscribe, "_fire_error_alert",
                        lambda request, err, source: messages.append((source, str(err))))

    _post(client, admin_headers)

    partial = [m for source, m in messages if source == "rashifal:blast:partial"]
    assert partial, f"no partial alert fired: {messages}"
    assert "kartik-at-gmail.test" not in partial[0], f"raw value in alert: {partial[0]}"
    assert "kartik" not in partial[0], f"leading characters leaked: {partial[0]}"
    assert "(first: ***)" in partial[0], partial[0]


def test_a_non_string_email_does_not_cost_the_alert_or_the_outcome_json(
        client, admin_headers, blast, offline, monkeypatch):
    """A truthy non-string `email` must not take the endpoint down.

    `email` is `sub.get("email", "")` — whatever the subscribers blob actually
    holds. `12345` survives the loop (the #220 handler catches it) and then
    reached `_mask_email` in the partial alert, which sits BELOW the loop and
    outside that handler: AttributeError, no alert, no outcome JSON, an HTML
    500. The loop's fix relocated #220's harm rather than removing it, so this
    asserts the whole outcome — both good rows delivered, the alert fired, the
    JSON returned — not just that the mask survives.
    """
    from astro_ai.routes import subscribe

    sent = blast([
        _subscriber("ok@x.test", city=""),
        _subscriber(12345, city=""),
        _subscriber("z@x.test", city=""),
    ])

    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(subscribe, "_fire_error_alert",
                        lambda request, err, source: alerts.append((source, str(err))))

    code, body = _post(client, admin_headers)

    assert sent == ["ok@x.test", "z@x.test"], f"a bad row cost a good one: {sent}"
    assert (body["sent"], body["failed"]) == (2, 1), body
    assert (code, body["ok"]) == (500, False), body
    partial = [m for source, m in alerts if source == "rashifal:blast:partial"]
    assert partial, f"the alert below the loop never fired: {alerts}"
    assert "12345" not in partial[0], f"raw value in alert: {partial[0]}"


def test_a_raising_alert_does_not_cost_the_outcome_json(
        client, admin_headers, blast, offline, monkeypatch):
    """Alerting is best-effort; reporting the outcome is not.

    Every alert sits below the send loop and outside its handler, so a raise
    there produces exactly the silence #220 is about — the blast happened and
    nothing said so. `_fire_error_alert` swallows its own errors today, but the
    guard has to hold regardless of what a future alert path does, which is why
    this stubs a raising one rather than trusting that.
    """
    from astro_ai.routes import subscribe

    sent = blast([_subscriber("good@x.test", city=""), _subscriber("bad@x.test", city="")])

    def one_bad_send(email, **k):
        sent.append(email)
        return email != "bad@x.test"

    monkeypatch.setattr(subscribe.email_sender, "send", one_bad_send)

    def exploding_alert(request, err, source):
        raise RuntimeError(f"telegram down ({source})")

    monkeypatch.setattr(subscribe, "_fire_error_alert", exploding_alert)

    code, body = _post(client, admin_headers)

    assert sent == ["good@x.test", "bad@x.test"], sent
    assert (body["sent"], body["failed"]) == (1, 1), body
    assert (code, body["ok"]) == (500, False), body
    assert body["total_subscribers"] == 2, body
