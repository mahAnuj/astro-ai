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

THE SECOND DEFECT (QA round 2). The 150 s budget is PER CALL. The inline
two-language send-daily job makes 24 calls in ONE 300 s request, and nothing
bounded the total: 319-395 s simulated in 8 of 8 seeds. So the batch jobs now
pass a JOB-LEVEL DEADLINE (`providers.pace_deadline()`, one absolute time), and
every call turns it into its own `max_wait_s = min(budget, time left)` the
moment before it calls chat(). Asserted below: the per-call figure never exceeds
the budget and is 0 once the deadline has passed; it decays as the clock moves;
send-daily computes ONE deadline for both languages; and a 24-call fan-out whose
waits would otherwise total past the allowance sleeps no more than the
allowance. The fan-out runs on a fake clock against a Groq-shaped limiter -- no
socket, no real sleep, no LLM call.

Nothing here sends a request: `providers.chat` is a capture throughout, and
`tests/test_suite_is_hermetic.py` enforces that at the socket layer.
"""
from __future__ import annotations

import itertools
from datetime import date

import pytest

from astro_ai import chart, festivals, llm, providers
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import RASHIFAL_PROMPT_PATH
# The fake clock, the Groq-shaped limiter and the fake-client installer are the
# ones the bucket's own tests use; a second copy would drift from them.
from test_token_bucket import (  # noqa: E402
    GroqLimiter, P20, P120, pacing_on, world,  # noqa: F401  (fixtures are used by name)
)
from test_token_bucket import _install  # noqa: E402

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
# the per-call figure: capped at the budget, decaying with the clock, 0 after
# --------------------------------------------------------------------------- #

class _Clock:
    """A settable stand-in for providers._pace_clock."""

    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = _Clock()
    monkeypatch.setattr(providers, "_pace_clock", c)
    return c


def test_the_job_budget_is_150_seconds_and_longer_than_the_interactive_default():
    assert providers.PACE_JOB_BUDGET_S == 150.0
    assert providers.PACE_JOB_BUDGET_S > providers.RETRY_AFTER_MAX_S


def test_the_job_deadline_leaves_headroom_under_the_300s_cloud_run_timeout():
    """It bounds WAITING only; the calls after it still cost latency and the send follows."""
    assert providers.PACE_JOB_DEADLINE_S >= providers.PACE_JOB_BUDGET_S
    assert providers.PACE_JOB_DEADLINE_S <= 240.0, (
        "a pacing deadline past 240 s leaves under 60 s for the last calls' latency, "
        "their 429 handling and the email loop inside a 300 s request")


def test_no_deadline_means_the_interactive_default(clock):
    assert providers.pace_wait_budget(None) is None


def test_the_per_call_wait_never_exceeds_the_budget_and_decays_with_the_clock(clock):
    deadline = providers.pace_deadline()
    assert deadline == clock.now + providers.PACE_JOB_DEADLINE_S
    seen = []
    for elapsed in (0, 50, 70, 100, providers.PACE_JOB_DEADLINE_S - 40,
                    providers.PACE_JOB_DEADLINE_S - 1.5):
        clock.now = 1000.0 + elapsed
        seen.append(providers.pace_wait_budget(deadline))
    assert all(w <= providers.PACE_JOB_BUDGET_S for w in seen), seen
    assert seen[0] == providers.PACE_JOB_BUDGET_S, "far from the deadline the per-call cap rules"
    assert seen[-1] == pytest.approx(1.5)
    assert seen == sorted(seen, reverse=True), f"the allowance must only shrink: {seen}"
    assert seen[-2] == pytest.approx(40.0)


def test_the_per_call_wait_is_zero_once_the_deadline_has_passed(clock):
    deadline = providers.pace_deadline()
    clock.now = deadline                           # exactly on it
    assert providers.pace_wait_budget(deadline) == 0.0
    clock.now = deadline + 400                     # long past: floored, never negative
    assert providers.pace_wait_budget(deadline) == 0.0


# --------------------------------------------------------------------------- #
# the batch entry points pass a deadline
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("lang", ["en", "hi"])
def test_warm_rashifal_passes_a_job_deadline(client, admin_headers, captured_generate, lang):
    r = client.post(f"/admin/warm-rashifal?lang={lang}", headers=admin_headers)
    assert r.status_code == 503                       # the capture stub ends the call
    assert len(captured_generate) == 1
    left = captured_generate[0]["pace_deadline"] - providers._pace_clock()
    assert 0 < left <= providers.PACE_JOB_DEADLINE_S, (
        f"warm should hand over a deadline about {providers.PACE_JOB_DEADLINE_S}s out, got {left}")


def test_send_daily_shares_ONE_deadline_across_both_languages(
        client, admin_headers, monkeypatch, offline, clock):
    """The 24 calls are one 300 s request. A per-language deadline would be two."""
    from astro_ai.routes import subscribe

    seen: list[tuple[str, float]] = []

    def fake_generate(**kw):
        seen.append((kw["lang"], kw["pace_deadline"]))
        clock.now += 100.0               # a language takes a while; a recomputed deadline moves
        if len(seen) == 1:
            return "## Aries\nA short body."
        raise AllProvidersExhausted("stop after the second language")

    monkeypatch.setattr(subscribe, "generate_rashifal", fake_generate)
    monkeypatch.setattr(subscribe, "_daily_rashifal_text", lambda *, call_fn, **kw: call_fn())
    client.post("/admin/send-daily-rashifal", headers=admin_headers)
    assert [lang for lang, _ in seen] == ["en", "hi"], "the handler never reached the second language"
    assert seen[0][1] == seen[1][1], (
        "en and hi were handed different deadlines; the second language would get a "
        "fresh allowance and the 24 calls could pass the 300 s timeout")


def test_the_welcome_email_is_interactive_and_passes_no_deadline(
        monkeypatch, captured_generate):
    """It runs inside the subscriber's own POST, so it keeps the short default."""
    from astro_ai.routes import subscribe

    monkeypatch.setattr(subscribe.email_sender, "send", lambda *a, **k: True)
    subscribe._send_welcome_email("w@example.test", "en")
    assert len(captured_generate) == 1, "the welcome email never reached generate_rashifal"
    assert captured_generate[0].get("pace_deadline") is None


# --------------------------------------------------------------------------- #
# the deadline survives the thread pool, and each of the twelve calls decays it
# --------------------------------------------------------------------------- #

def _transit():
    natal = chart.compute_chart("2000-01-01", "12:00", "Mumbai, India")
    return natal, chart.compute_transit_snapshot(natal)


def _run_rashifal(lang="en", **kw):
    natal, transit = _transit()
    return llm.generate_rashifal(
        transit, date.today().isoformat(), RASHIFAL_PROMPT_PATH, lang=lang,
        panchang=chart.compute_panchang(natal),
        festival=festivals.festival_for_date(date.today()), **kw)


def test_generate_rashifal_hands_each_pool_call_its_own_wait_from_the_deadline(
        monkeypatch, clock):
    seen: list[tuple[str, float | None]] = []

    def capture(messages, *, route="", **kw):
        seen.append((route, kw.get("max_wait_s")))
        return GOOD

    monkeypatch.setattr(providers, "chat", capture)
    _run_rashifal(pace_deadline=clock.now + 90.0)
    assert len(seen) == 12
    assert {r for r, _ in seen} == {"rashifal_single"}
    assert [w for _, w in seen] == [90.0] * 12, (
        "a pool worker did not compute its wait from the deadline; the deadline "
        "must travel as an argument, and be read when the call is made")


def test_a_deadline_already_past_gives_every_pool_call_zero(monkeypatch, clock):
    seen: list[float | None] = []
    monkeypatch.setattr(providers, "chat",
                        lambda messages, *, route="", **kw: seen.append(kw.get("max_wait_s")) or GOOD)
    _run_rashifal(pace_deadline=clock.now - 5.0)
    assert seen == [0.0] * 12


def test_a_far_deadline_still_caps_each_call_at_the_budget(monkeypatch, clock):
    seen: list[float | None] = []
    monkeypatch.setattr(providers, "chat",
                        lambda messages, *, route="", **kw: seen.append(kw.get("max_wait_s")) or GOOD)
    _run_rashifal(pace_deadline=clock.now + 10_000.0)
    assert seen == [providers.PACE_JOB_BUDGET_S] * 12


# --------------------------------------------------------------------------- #
# the bound itself: 24 calls, two languages, one deadline
# --------------------------------------------------------------------------- #

_PINNED_CALL_TOKENS = 4_500
"""Per-call bucket cost for the 24-call scenario below. An INPUT, not a measurement.

It used to be inherited from the real rashifal messages, and that made this
test's pressure a hostage to prompt wording: on 2026-10-24 a prompt edit (#513,
dropping the Rahu Kaal / Abhijit instruction -- -119 tok/call EN, -219 HI) took
the overrun away and the deadline stopped biting at all. `given` bottomed out at
2.7 instead of reaching 0.0, so the bound this file exists to prove was no
longer being exercised. Pinning it means a wording change can never silently
drain the scenario again.

**This has a WINDOW, not a floor, so do not just raise it.** Too low and the
waits never exhaust the allowance (3,330 -> min 2.7; 3,900 -> 3.9; 4,200 ->
1.6). Too high and each wait exceeds `pace_left`, so calls are FORCED past the
bucket without sleeping and the clock stops advancing -- 4,800 jumps back to
min 13.5 with sleeps falling 88.6s -> 68.8s. 4,500 sits in the window: min 0.0,
88.6s of sleep against the 100s allowance. If this ever goes red, re-find the
window; never weaken the `0.0 in given` guard to make a run green, because a
vacuous pass here is a pacing bound nothing is checking.
"""


def _fan_out_two_languages(monkeypatch, world, *, per_call_only: bool):
    """Both languages of the send-daily job against a Groq-shaped limiter.

    One pool worker (`_RASHIFAL_CONCURRENCY` patched to 1 for this test only) so
    the single fake clock is not raced; the BOUND is on pacing sleeps and does not
    depend on the worker count. The deadline is shortened to 100 s so that the
    24 calls' bucket waits (~225 s here) total well past it. `per_call_only`
    restores the pre-deadline behaviour -- every call may wait the full budget --
    which is the control that shows the bound is the deadline's doing.
    """
    monkeypatch.setattr(llm, "_RASHIFAL_CONCURRENCY", 1)
    monkeypatch.setattr(providers, "PACE_JOB_DEADLINE_S", 100.0)
    # Per-call bucket cost is an INPUT to this scenario, like `usage=` and
    # `latency=` beside it -- not something to inherit from whatever the
    # rashifal prompt happens to weigh this week. It WAS inherited: the
    # reservation is estimated from the real messages, so on 2026-10-24 a prompt
    # edit (#513 -- dropping the Rahu Kaal / Abhijit instruction, -119 tok/call
    # EN and -219 HI) took the pressure out and the deadline stopped biting at
    # all. `given` came back [100.0, 99.0, 98.0, ...] with no 0.0 and the guard
    # below caught it. A pacing bound that silently stops being exercised by a
    # wording change is not a bound, so the cost is pinned to what these 24
    # calls weighed when the bound was written.
    monkeypatch.setattr(providers, "estimate_request_tokens",
                        lambda messages, route="": _PINNED_CALL_TOKENS)
    if per_call_only:
        monkeypatch.setattr(providers, "pace_wait_budget",
                            lambda deadline: providers.PACE_JOB_BUDGET_S)
    limiter = GroqLimiter(world)
    _install(monkeypatch, world, [P120, P20], usage=(2700, 510), latency=1.0, limiter=limiter)
    # Alternate which model a request tries first, as the default per-request
    # shuffle does on average: a fixed order puts all 24 calls on one bucket.
    turn = itertools.count()
    monkeypatch.setattr(providers, "_ordered_for_request",
                        lambda: [P120, P20] if next(turn) % 2 == 0 else [P20, P120])

    pace_sleeps: list[float] = []
    real_sleep = providers._pace_sleep

    def recording_sleep(seconds):
        pace_sleeps.append(seconds)
        real_sleep(seconds)

    monkeypatch.setattr(providers, "_pace_sleep", recording_sleep)
    given: list[float | None] = []
    real_chat = providers.chat

    def recording_chat(messages, *, route="", max_wait_s=None):
        given.append(max_wait_s)
        return real_chat(messages, route=route, max_wait_s=max_wait_s)

    monkeypatch.setattr(providers, "chat", recording_chat)

    start = world.now
    deadline = providers.pace_deadline()
    failed = 0
    for lang in ("en", "hi"):
        try:
            _run_rashifal(lang=lang, pace_deadline=deadline)
        except AllProvidersExhausted:
            failed += 1
    return {"start": start, "deadline": deadline, "sleeps": pace_sleeps, "given": given,
            "limiter": limiter, "failed_languages": failed}


def test_24_calls_sleep_no_more_than_the_deadline_allows(monkeypatch, world, pacing_on):
    r = _fan_out_two_languages(monkeypatch, world, per_call_only=False)
    allowance = r["deadline"] - r["start"]
    assert allowance == 100.0
    assert sum(r["sleeps"]) <= allowance + 1e-6, (
        f"{sum(r['sleeps']):.1f}s of pacing sleep against a {allowance:.0f}s allowance")
    assert all(g <= providers.PACE_JOB_BUDGET_S for g in r["given"] if g is not None)
    assert 0.0 in r["given"], "no call was ever handed 0: the deadline never bit"
    # Once a call is handed 0 every later one is too: the allowance only shrinks.
    first_zero = r["given"].index(0.0)
    assert set(r["given"][first_zero:]) == {0.0}


def test_the_same_24_calls_with_only_a_per_call_budget_sleep_past_the_allowance(
        monkeypatch, world, pacing_on):
    """CONTROL: this is the failure the deadline exists for."""
    r = _fan_out_two_languages(monkeypatch, world, per_call_only=True)
    allowance = r["deadline"] - r["start"]
    assert sum(r["sleeps"]) > allowance, (
        f"the control slept only {sum(r['sleeps']):.1f}s of a {allowance:.0f}s allowance; "
        "the fan-out no longer exercises the bound, so the test above proves nothing")


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


def test_generate_rashifal_without_a_deadline_passes_none_to_every_call(monkeypatch):
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
