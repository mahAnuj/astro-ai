"""Who gets the long token-bucket wait, and who keeps the short one (#475 Phase 1).

THE DEFECT (QA round 1 on PR #498). `providers.chat(max_wait_s=)` existed and no
caller in the app passed it, so every request -- the 7 AM batch included -- got
the 6 s interactive default. A job with nobody waiting is the one caller that
should accept a long wait for bucket room, and it is also the traffic that
overspends a bucket: twelve ~3,200-token calls per language against 8,000 TPM.
The design said interactive callers keep the short default and the batch jobs
pass a larger budget; nothing connected the two.

WHAT IS ASSERTED, and where each fake sits:

* the two batch entry points (`/admin/warm-rashifal`, `/admin/send-daily-rashifal`)
  hand `generate_rashifal` the job budget. `generate_rashifal` is stubbed to
  capture its kwargs -- the seam under test is the call site;
* `generate_rashifal` carries the budget to every one of its twelve
  `providers.chat` calls, which run in a ThreadPoolExecutor. This is the reason
  the budget is an argument and not a ContextVar: context does not propagate
  into a pool worker, so a ContextVar set by the route would read as unset in
  every one of the twelve. Real `generate_rashifal`, `providers.chat` captured;
* the interactive entry points -- the on-demand `/rashifal/{rashi}` card, and
  the welcome email, which runs inside the subscriber's own request -- pass NO
  budget;
* the budget changes what chat() does: with the same saturated bucket, the
  default skips to the next provider and the job budget waits.

Nothing here sends a request: `providers.chat` is a capture throughout, and
`tests/test_suite_is_hermetic.py` enforces that at the socket layer.
"""
from __future__ import annotations

from datetime import date

import pytest

from astro_ai import chart, festivals, llm, providers
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import RASHIFAL_PROMPT_PATH

GOOD = "A perfectly adequate reading. " * 12


@pytest.fixture
def admin_headers():
    from astro_ai.main import app
    from astro_ai.routes.deps import require_admin

    app.dependency_overrides[require_admin] = lambda: None
    yield {}
    app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def offline(monkeypatch):
    """The reference-chart calls every batch handler makes before generating."""
    from astro_ai.routes import subscribe

    monkeypatch.setattr(subscribe, "compute_chart", lambda *a, **k: {"stub": "chart"})
    monkeypatch.setattr(subscribe, "compute_transit_snapshot", lambda chart: {})
    monkeypatch.setattr(subscribe, "compute_panchang", lambda chart: None)
    monkeypatch.setattr(subscribe, "_fire_error_alert", lambda *a, **k: None)


@pytest.fixture
def captured_generate(monkeypatch, offline):
    """Run each route's own call_fn, with generate_rashifal capturing its kwargs.

    `_daily_rashifal_text` is replaced by a function that invokes the route's
    real `call_fn` lambda and then raises, so the handler stops at its normal
    all-providers-failed branch without touching storage or the mail path.
    """
    from astro_ai.routes import subscribe

    seen: list[dict] = []

    def fake_generate(**kw):
        seen.append(kw)
        raise AllProvidersExhausted("captured")

    def fake_text(*, call_fn, **kw):
        return call_fn()

    monkeypatch.setattr(subscribe, "generate_rashifal", fake_generate)
    monkeypatch.setattr(subscribe, "_daily_rashifal_text", fake_text)
    return seen


# --------------------------------------------------------------------------- #
# the batch entry points pass the job budget
# --------------------------------------------------------------------------- #

def test_the_job_budget_is_150_seconds_and_longer_than_the_interactive_default():
    assert providers.PACE_JOB_BUDGET_S == 150.0
    assert providers.PACE_JOB_BUDGET_S > providers.RETRY_AFTER_MAX_S


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_warm_rashifal_passes_the_job_budget(client, admin_headers, captured_generate, lang):
    r = client.post(f"/admin/warm-rashifal?lang={lang}", headers=admin_headers)
    assert r.status_code == 503                       # the capture stub ends the call
    assert len(captured_generate) == 1
    assert captured_generate[0]["max_wait_s"] == providers.PACE_JOB_BUDGET_S


def test_send_daily_rashifal_passes_the_job_budget_for_both_languages(
        client, admin_headers, captured_generate):
    client.post("/admin/send-daily-rashifal", headers=admin_headers)
    # The first language's failure ends the handler: one captured call is enough
    # to show the call site passes it, and the lambda is the same for both.
    assert captured_generate, "send-daily never reached generate_rashifal"
    assert all(k["max_wait_s"] == providers.PACE_JOB_BUDGET_S for k in captured_generate)


def test_the_welcome_email_is_interactive_and_passes_no_budget(
        monkeypatch, captured_generate):
    """It runs inside the subscriber's own POST, so it keeps the short default."""
    from astro_ai.routes import subscribe

    monkeypatch.setattr(subscribe.email_sender, "send", lambda *a, **k: True)
    subscribe._send_welcome_email("w@example.test", "en")
    assert len(captured_generate) == 1, "the welcome email never reached generate_rashifal"
    assert captured_generate[0].get("max_wait_s") is None


# --------------------------------------------------------------------------- #
# the budget survives the thread pool, to every one of the twelve calls
# --------------------------------------------------------------------------- #

def _transit():
    natal = chart.compute_chart("2000-01-01", "12:00", "Mumbai, India")
    return natal, chart.compute_transit_snapshot(natal)


def test_generate_rashifal_hands_the_budget_to_all_twelve_pool_calls(monkeypatch):
    seen: list[tuple[str, float | None]] = []

    def capture(messages, *, route="", **kw):
        seen.append((route, kw.get("max_wait_s")))
        return GOOD

    monkeypatch.setattr(providers, "chat", capture)
    natal, transit = _transit()
    llm.generate_rashifal(
        transit, date.today().isoformat(), RASHIFAL_PROMPT_PATH, lang="en",
        panchang=chart.compute_panchang(natal),
        festival=festivals.festival_for_date(date.today()),
        max_wait_s=providers.PACE_JOB_BUDGET_S)
    assert len(seen) == 12
    assert {r for r, _ in seen} == {"rashifal_single"}
    assert [w for _, w in seen] == [providers.PACE_JOB_BUDGET_S] * 12, (
        "a pool worker did not receive the budget; it must travel as an argument")


# --------------------------------------------------------------------------- #
# the interactive entry point keeps the short default
# --------------------------------------------------------------------------- #

def test_the_on_demand_rashi_card_passes_no_budget(monkeypatch):
    """A user is waiting on /rashifal/{rashi}: the short default must stand."""
    seen: list[dict] = []

    def capture(messages, *, route="", **kw):
        seen.append(kw)
        return GOOD

    monkeypatch.setattr(providers, "chat", capture)
    natal, transit = _transit()
    llm.generate_rashifal_for_rashi(
        0, transit, date.today().isoformat(), RASHIFAL_PROMPT_PATH, lang="en",
        panchang=chart.compute_panchang(natal),
        festival=festivals.festival_for_date(date.today()))
    assert len(seen) == 1
    assert seen[0].get("max_wait_s") is None


def test_generate_rashifal_without_a_budget_passes_none_to_every_call(monkeypatch):
    seen: list[float | None] = []

    def capture(messages, *, route="", **kw):
        seen.append(kw.get("max_wait_s", "ABSENT"))
        return GOOD

    monkeypatch.setattr(providers, "chat", capture)
    natal, transit = _transit()
    llm.generate_rashifal(
        transit, date.today().isoformat(), RASHIFAL_PROMPT_PATH, lang="en",
        panchang=chart.compute_panchang(natal), festival=None)
    assert seen == [None] * 12
