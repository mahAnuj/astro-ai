"""The per-model token bucket in front of Groq (#475 Phase 1).

THE DEFECT. Groq's free tier is 8,000 tokens/minute PER MODEL and the only
reaction to it was reactive: send, take the 429, sleep the hint, retry once. The
daily rashifal job is twelve ~3,200-token calls per language, so it spent a call
-- and a 429 -- on most of them. This is the proactive half: chat() asks a
per-model bucket for room BEFORE sending, waits a bounded time, or moves to the
next provider instead.

HOW THESE ARE BUILT.

* Everything runs on a FAKE clock. `providers._pace_clock` / `_pace_sleep` (and
  `time.sleep`, which the 429 hint path uses) are replaced by one `World`, whose
  sleep advances its clock. Nothing here sleeps for real and nothing opens a
  socket -- `test_suite_is_hermetic.py` enforces the second at the socket layer.
* The Groq stand-in is not a mock that always says yes. `GroqLimiter` is a
  refill-at-8000/60 limiter that REJECTS with Groq's own 429 text, because an
  acceptance test against a stub that can never refuse proves nothing. The one
  429 body on record -- "Limit 8000, Used 5009, Requested 3587 ... try again in
  4.47s" -- is reproduced to the digit by
  `test_the_stub_limiter_reproduces_groqs_own_429`; that arithmetic,
  (5009 + 3587 - 8000) / (8000 / 60) = 4.47, is also the ONLY evidence that Groq
  behaves like a continuous-refill bucket at all (an inference from one body, not
  a measurement; the x-ratelimit headers are read by #475 Phase 1b).
* `LIMIT` is the stub's ceiling and has a mutation row: raise it to infinity and
  the control (`test_without_the_bucket_the_same_burst_is_rejected`) must go red,
  which is what shows the acceptance test could ever have failed.
* The conftest autouse fixture turns pacing OFF for every other test and empties
  the registry. Tests here opt in with the `pacing_on` fixture.

ORDER MATTERS in this file: the calibration test is first because every other
number rests on the estimator being honest.
"""
from __future__ import annotations

import json
import logging
import threading
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from _fake_openai import fake_client
from astro_ai import llm, llm_stats, providers

GROQ = "https://api.groq.com/openai/v1"
M120, M20 = "openai/gpt-oss-120b", "openai/gpt-oss-20b"
P120 = providers.ProviderConfig("groq120", GROQ, M120, "K")
P20 = providers.ProviderConfig("groq20", GROQ, M20, "K")
OTHER = providers.ProviderConfig("other", "https://other.example/v1", "other-model", "K")
K120, K20 = f"groq120|{M120}", f"groq20|{M20}"

#: The stand-in's per-model ceiling. Mutation row 14 raises this to infinity.
LIMIT = 8000

GOOD = "A perfectly adequate reading. " * 12        # 360 chars: over every route's floor
SHORT = "too short"


# --------------------------------------------------------------------------- #
# 1. calibration -- FIRST on purpose
# --------------------------------------------------------------------------- #

def _real_rashifal_messages(lang: str) -> list[dict]:
    """The messages the production rashifal_single path really builds.

    Not a hand-written lookalike: `_generate_rashifal_single` is called for real,
    with `providers.chat` replaced by a capture, so the estimate is measured
    against the exact system prompt and sky-signal block a user's request carries.
    """
    from datetime import date

    from astro_ai import chart, festivals
    from astro_ai.routes.deps import RASHIFAL_PROMPT_PATH

    seen: dict = {}

    def capture(messages, *, route="", **kw):
        seen["m"], seen["route"] = messages, route
        return GOOD

    natal = chart.compute_chart("2000-01-01", "12:00", "Mumbai, India")
    real_chat = providers.chat
    providers.chat = capture
    try:
        llm.generate_rashifal_for_rashi(
            0, chart.compute_transit_snapshot(natal), date.today().isoformat(),
            RASHIFAL_PROMPT_PATH, lang=lang, panchang=chart.compute_panchang(natal),
            festival=festivals.festival_for_date(date.today()))
    finally:
        providers.chat = real_chat
    assert seen["route"] == "rashifal_single"
    return seen["m"]


@pytest.mark.network_allowed(
    "openaipublic.blob.core.windows.net",
    reason="tiktoken downloads the o200k_base vocabulary on first use; a "
           "dependency fetch, not LLM spend, and there is no honest stub for "
           "'the estimate is close to the real count' (#449)")
@pytest.mark.parametrize("lang,max_ratio", [("en", 1.20), ("hi", 1.30)])
def test_the_request_estimate_brackets_a_real_rashifal_request(lang, max_ratio):
    """Never under the real prompt, and not wastefully over it.

    The bucket is only as honest as this number. Under-estimating spends a 429;
    over-estimating makes the 12-call job wait for room it did not need. Both
    ends are asserted against tiktoken (o200k_base, the tokenizer gpt-oss uses)
    on the real message.

    The upper bound is looser for Hindi and that is MEASURED, not assumed: the
    shared prose constant (4.2 B/tok) is calibrated on English and Devanagari is
    three bytes a character, so the Hindi system prompt prices ~29% over the
    real count. That constant is the natal guard's and is gated by its own
    no-under-count test; tightening it here would change what the guard sheds.
    The over-reserve is the safe direction and costs wait, not 429s.
    """
    tiktoken = pytest.importorskip("tiktoken")
    enc = tiktoken.get_encoding("o200k_base")
    messages = _real_rashifal_messages(lang)
    real_prompt = sum(len(enc.encode(m["content"])) for m in messages)
    reserve = providers._SCAFFOLD_TOKENS + providers._completion_reserve("rashifal_single")
    est = providers.estimate_request_tokens(messages, "rashifal_single")

    assert est - reserve >= real_prompt, (
        f"the {lang} prompt part of the estimate ({est - reserve}) is UNDER the real "
        f"count ({real_prompt}); the bucket would admit calls that do not fit")
    assert est <= max_ratio * (real_prompt + reserve), (
        f"estimate {est} is {est / (real_prompt + reserve):.3f}x the real prompt plus "
        f"its reserve ({real_prompt + reserve}); over {max_ratio}x is idle waiting")


def test_the_estimate_prices_system_as_prose_and_the_rest_as_data():
    base = providers._SCAFFOLD_TOKENS + providers._completion_reserve("ask")
    msgs = [{"role": "system", "content": "a" * 420},      # ceil(420 / 4.2) = 100
            {"role": "user", "content": "a" * 365}]        # ceil(365 / 3.65) = 100
    assert providers.estimate_request_tokens(msgs, "ask") == base + 100 + 100
    # Swapping the roles swaps the constants: the split is what is being tested.
    swapped = [{"role": "user", "content": "a" * 420}, {"role": "system", "content": "a" * 365}]
    assert providers.estimate_request_tokens(swapped, "ask") == (
        base + providers.estimate_data_tokens("a" * 420) + providers.estimate_prose_tokens("a" * 365))


def test_the_completion_reserve_is_per_route_with_a_default():
    empty = [{"role": "user", "content": ""}]
    single = providers.estimate_request_tokens(empty, "rashifal_single")
    other = providers.estimate_request_tokens(empty, "natal")
    assert single == providers._SCAFFOLD_TOKENS + 500
    assert other == providers._SCAFFOLD_TOKENS + 800
    assert providers.estimate_request_tokens(empty) == other, "unlabelled routes take the default"


# --------------------------------------------------------------------------- #
# the world: a fake clock, a Groq-shaped limiter, a fake OpenAI client
# --------------------------------------------------------------------------- #

class World:
    """One fake clock. Sleeping advances it; nothing waits in real time."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _rate_limit(msg: str) -> RateLimitError:
    req = httpx.Request("POST", GROQ + "/chat/completions")
    return RateLimitError(msg, response=httpx.Response(429, request=req), body=None)


class GroqLimiter:
    """Groq's per-model TPM limit as a refill-at-LIMIT/60 bucket, with Groq's 429 text.

    Modelled on the one 429 body on record -- Limit 8000, Used 5009, Requested
    3587, "try again in 4.47s" -- which equals (used + requested - limit) / (limit
    / 60) exactly. Each model has its own level, as on Groq.
    """

    def __init__(self, world: World, limit=None):
        self.world, self.limit = world, LIMIT if limit is None else limit
        self.state: dict[str, tuple[float, float]] = {}
        self.rejections: list[tuple[str, float]] = []

    def used(self, model: str) -> float:
        level, t = self.state.get(model, (0.0, self.world.now))
        return max(0.0, level - (self.world.now - t) * self.limit / 60.0)

    def admit(self, model: str, tokens: int) -> None:
        used = self.used(model)
        if used + tokens > self.limit:
            wait = (used + tokens - self.limit) / (self.limit / 60.0)
            self.rejections.append((model, self.world.now))
            raise _rate_limit(
                f"Error code: 429 - Rate limit reached for model `{model}` in organization "
                f"`org_x` service tier `on_demand` on tokens per minute (TPM): Limit "
                f"{self.limit}, Used {int(used)}, Requested {tokens}. Please try again in "
                f"{wait:.2f}s. Need more tokens? Upgrade to Dev Tier today.")
        self.state[model] = (used + tokens, self.world.now)


def _response(text: str, prompt: int, completion: int):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                              total_tokens=prompt + completion))


@pytest.fixture
def pacing_on(monkeypatch):
    monkeypatch.setenv("BHAGYA_TPM_PACING", "1")


@pytest.fixture
def world(monkeypatch):
    w = World()
    monkeypatch.setattr(providers, "_pace_clock", w.clock)
    monkeypatch.setattr(providers, "_pace_sleep", w.sleep)
    # The 429-hint path sleeps through time.sleep. Redirected for the duration of
    # the test only; monkeypatch restores it.
    monkeypatch.setattr(providers.time, "sleep", w.sleep)
    return w


@pytest.fixture
def stats_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "llm_stats")
    llm_stats._warned_rows.clear()
    return tmp_path / "llm_stats"


def _blob(stats_dir) -> dict:
    files = list(stats_dir.glob("*.json"))
    assert files, "record() wrote nothing"
    return json.loads(files[0].read_text())


def _install(monkeypatch, world, chain, *, usage=(2700, 510), latency=0.0, limiter=None,
             script=None, text=GOOD):
    """Run chat() over the REAL _call_one against a fake client.

    `script(model, n)` may raise to fail the n-th call to a model (n from 1), or
    return None to proceed. `limiter` (a GroqLimiter) is consulted only for Groq
    hosts, as the real service would be.
    """
    monkeypatch.setenv("K", "k")
    calls: list[tuple[str, float]] = []
    counts: dict[str, int] = {}

    def factory(*, api_key=None, base_url=None, **kw):
        def create(*, model, messages, **k):
            calls.append((model, world.now))
            counts[model] = counts.get(model, 0) + 1
            if script is not None:
                script(model, counts[model])
            if limiter is not None and base_url.startswith(GROQ):
                limiter.admit(model, usage[0] + usage[1])
            world.now += latency
            return _response(text, *usage)
        return fake_client(create)

    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: list(chain))
    return calls


def _messages(target: int, route: str = "ask") -> tuple[list[dict], int]:
    """Messages whose ESTIMATE is `target` tokens (within a few), and that estimate."""
    base = providers.estimate_request_tokens(
        [{"role": "system", "content": "You are a guide."}, {"role": "user", "content": ""}], route)
    user = "a" * int((target - base) * 3.65)
    msgs = [{"role": "system", "content": "You are a guide."}, {"role": "user", "content": user}]
    est = providers.estimate_request_tokens(msgs, route)
    assert abs(est - target) <= 5, (est, target)
    return msgs, est


def _fill(provider, wait_s: float, est: int) -> None:
    """Load `provider`'s bucket so that a request of `est` tokens must wait `wait_s`."""
    b = providers._bucket_for(provider)
    tokens = round(b.cap - est + wait_s * b.rate)
    assert 0 < tokens <= b.cap
    res, _ = b.reserve(tokens, 0.0)
    assert res is not None and res.wait_s == 0.0


# --------------------------------------------------------------------------- #
# 2. the stand-in is faithful to the one Groq 429 on record
# --------------------------------------------------------------------------- #

def test_the_stub_limiter_reproduces_groqs_own_429(world):
    lim = GroqLimiter(world, limit=8000)
    lim.state[M120] = (5009.0, world.now)
    with pytest.raises(RateLimitError) as exc:
        lim.admit(M120, 3587)
    text = str(exc.value)
    assert "Limit 8000, Used 5009, Requested 3587" in text
    assert "try again in 4.47s" in text, "the arithmetic (5009+3587-8000)/(8000/60) is 4.47"
    assert providers._failure_reason(exc.value) == "429_tpm"
    assert providers._retry_after_seconds(exc.value) == pytest.approx(4.47)


# --------------------------------------------------------------------------- #
# 3. ACCEPTANCE: twelve 3,210-token calls on one model
# --------------------------------------------------------------------------- #

def _burst(monkeypatch, world, n=12, latency=10.0):
    """n sequential rashifal-sized calls to ONE model; returns (limiter, ok, exhausted)."""
    lim = GroqLimiter(world)
    _install(monkeypatch, world, [P120], usage=(2700, 510), latency=latency, limiter=lim)
    msgs, est = _messages(3400, "rashifal_single")
    assert est >= 2700 + 510, "the estimate must cover the actual 3,210 or this proves nothing"
    t0, ok, exhausted = world.now, 0, 0
    for _ in range(n):
        try:
            providers.chat(msgs, route="rashifal_single", max_wait_s=60)
            ok += 1
        except providers.AllProvidersExhausted:
            exhausted += 1
    return lim, ok, exhausted, world.now - t0


def test_twelve_calls_on_one_model_take_no_429_and_fit_in_five_minutes(
        monkeypatch, world, pacing_on):
    """The issue's acceptance: 12 x 3,210 tokens, zero 429_tpm, inside 300 seconds."""
    lim, ok, exhausted, wall = _burst(monkeypatch, world)
    assert lim.rejections == [], f"{len(lim.rejections)} calls were rejected by the limiter"
    assert (ok, exhausted) == (12, 0)
    assert wall <= 300, f"12 calls took {wall:.0f} fake seconds"
    assert world.sleeps, "no waiting at all means the bucket never engaged"


def test_without_the_bucket_the_same_burst_is_rejected(monkeypatch, world):
    """CONTROL. Same stub, same calls, pacing off: it must 429.

    If this ever passes with zero rejections the acceptance test above proves
    nothing -- the stand-in has stopped being able to refuse, and 'no 429s' would
    be true of any code at all.
    """
    monkeypatch.setenv("BHAGYA_TPM_PACING", "0")
    lim, ok, exhausted, _wall = _burst(monkeypatch, world)
    assert len(lim.rejections) >= 1
    assert all(providers._failure_reason(_rate_limit("tokens per minute (TPM)")) == "429_tpm"
               for _ in lim.rejections)
    assert providers._BUCKETS == {}, "pacing off must not even build a bucket"


# --------------------------------------------------------------------------- #
# 4. the bucket itself, on a fake clock
# --------------------------------------------------------------------------- #

@pytest.fixture
def bucket():
    w = World()
    b = providers._TokenBucket(8000, 600, clock=w.clock)
    b.world = w
    return b


def test_an_empty_bucket_admits_at_once(bucket):
    res, wait = bucket.reserve(3000, 0.0)
    assert res is not None and wait == 0.0 and res.wait_s == 0.0


def test_the_wait_is_the_deficit_over_the_refill_rate(bucket):
    bucket.reserve(6000, 99)
    res, wait = bucket.reserve(3000, 99)
    # 6000 + 3000 - 7400 = 1600 tokens short, refilling at 8000/60 per second.
    assert wait == pytest.approx(1600 / (8000 / 60)) == pytest.approx(12.0)
    assert res.wait_s == pytest.approx(12.0)


def test_slots_are_fifo_and_never_go_backwards(bucket):
    slots = []
    for _ in range(8):
        res, _ = bucket.reserve(3000, 999)
        slots.append(bucket.world.now + res.wait_s)
    assert slots == sorted(slots)
    # once saturated, consecutive slots are one request's refill time apart
    assert slots[-1] - slots[-2] == pytest.approx(3000 / (8000 / 60))


def test_a_denied_reserve_changes_nothing(bucket):
    bucket.reserve(7400, 0.0)
    before = (bucket._level, bucket._t)
    res, wait = bucket.reserve(3000, 1.0)
    assert res is None and wait > 1.0
    assert (bucket._level, bucket._t) == before, "a denial must not charge the bucket"


def test_an_oversize_request_is_clamped_and_waits_a_finite_time(bucket):
    res, wait = bucket.reserve(50_000, 60.0)
    assert res is not None and res.tokens == bucket.cap, (
        "a request bigger than the whole bucket can never be admitted unless clamped")
    res2, wait2 = bucket.reserve(50_000, 60.0)
    assert res2 is not None and wait2 == pytest.approx(bucket.cap / bucket.rate)
    assert wait2 <= 60.0


def test_settle_shrinks_and_grows_the_charge_and_only_once(bucket):
    res, _ = bucket.reserve(3000, 0.0)
    bucket.settle(res, 1000)
    assert bucket._level == pytest.approx(1000)
    bucket.settle(res, 9000)
    assert bucket._level == pytest.approx(1000), "a reservation settles exactly once"
    res2, _ = bucket.reserve(1000, 0.0)
    bucket.settle(res2, 4000)
    assert bucket._level == pytest.approx(1000 + 4000)


def test_refund_returns_the_whole_charge(bucket):
    res, _ = bucket.reserve(3000, 0.0)
    bucket.refund(res)
    assert bucket._level == 0.0


def test_the_level_leaks_with_time(bucket):
    """After a minute of silence the bucket is empty -- not still holding 7,400."""
    bucket.reserve(7400, 0.0)
    bucket.world.now += 60
    res, wait = bucket.reserve(7400, 0.0)
    assert res is not None and wait == 0.0
    assert bucket._level == pytest.approx(7400), "the old charge must have drained"


def test_a_forced_reserve_charges_at_once_and_the_next_caller_queues_behind_the_debt(bucket):
    bucket.reserve(7400, 0.0)
    res, wait = bucket.reserve(3000, 0.0, force=True)
    assert res.forced and wait == 0.0 and bucket._level == pytest.approx(10400)
    nxt, nwait = bucket.reserve(1000, 99.0)
    assert nwait == pytest.approx((10400 + 1000 - 7400) / (8000 / 60))
    assert nxt is not None


def test_sixteen_threads_lose_no_charge_and_replay_clean_against_the_limiter():
    """Concurrency. The clock is frozen so the arithmetic is exact.

    (a) No lost update: 16 x 400 tokens fit, so every wait is 0 and the level is
        exactly their sum -- a racy read-modify-write drops some.
    (b) 16 x 3,210 contend: the multiset of waits must equal what ONE thread
        computes for the same sequence (the lock serialises; it cannot invent
        or lose time), and replaying the slots in order against the Groq-shaped
        limiter must produce zero rejections.
    """
    def run(tokens, threads):
        w = World()
        b = providers._TokenBucket(8000, 600, clock=w.clock)
        out, barrier = [], threading.Barrier(threads)

        def work():
            barrier.wait()
            res, _ = b.reserve(tokens, 1e9)
            out.append(res.wait_s)

        ts = [threading.Thread(target=work) for _ in range(threads)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        return w, b, sorted(out)

    _w, b, waits = run(400, 16)
    assert waits == [0.0] * 16 and b._level == 16 * 400

    w, b, waits = run(3210, 16)
    ref = providers._TokenBucket(8000, 600, clock=w.clock)
    serial = sorted(ref.reserve(3210, 1e9)[0].wait_s for _ in range(16))
    assert waits == pytest.approx(serial)

    lim = GroqLimiter(w)
    for slot in waits:                      # ascending: the order the slots are served in
        w.now = 1000.0 + slot
        lim.admit(M120, 3210)
    assert lim.rejections == []


# --------------------------------------------------------------------------- #
# 5. which providers are paced, and the kill switch
# --------------------------------------------------------------------------- #

def test_only_groq_hosts_have_a_known_limit():
    assert providers._tpm_limit(P120) == providers.REQUEST_TOKEN_CEILING
    assert providers._tpm_limit(OTHER) is None
    assert providers._tpm_limit(providers.PROVIDERS["openai"]) is None, "api_base None = OpenAI"
    lookalike = providers.ProviderConfig("x", "https://api.groq.com.evil.example/v1", "m", "K")
    assert providers._tpm_limit(lookalike) is None, "the HOST must match, not a prefix of the URL"


@pytest.mark.parametrize("value,on", [
    ("0", False), ("false", False), ("OFF", False), (" no ", False),
    ("1", True), ("true", True), ("", True)])
def test_the_kill_switch_values(monkeypatch, value, on):
    monkeypatch.setenv("BHAGYA_TPM_PACING", value)
    assert providers._pacing_enabled() is on


def test_unset_means_on(monkeypatch):
    monkeypatch.delenv("BHAGYA_TPM_PACING", raising=False)
    assert providers._pacing_enabled() is True


def test_the_kill_switch_restores_the_unpaced_path_exactly(
        monkeypatch, world, stats_dir):
    monkeypatch.setenv("BHAGYA_TPM_PACING", "0")
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120])
    # Fill the bucket anyway: if pacing were consulted this call would have to wait.
    monkeypatch.setenv("BHAGYA_TPM_PACING", "1")
    _fill(P120, 15.0, est)
    monkeypatch.setenv("BHAGYA_TPM_PACING", "0")
    before = dict(providers._BUCKETS)
    assert providers.chat(msgs, route="ask", max_wait_s=0) == GOOD.strip()
    assert world.sleeps == [] and len(calls) == 1
    assert providers._BUCKETS == before, "no bucket may be touched when the switch is off"
    assert "paced_by_model" not in _blob(stats_dir), "off is recorded as silence, not zeros"


def test_a_non_groq_provider_is_never_paced(monkeypatch, world, pacing_on, stats_dir):
    msgs, _ = _messages(2000)
    calls = _install(monkeypatch, world, [OTHER])
    for _ in range(5):                       # 10k estimated tokens: would saturate any bucket
        providers.chat(msgs, route="ask", max_wait_s=0)
    assert len(calls) == 5 and world.sleeps == []
    assert providers._BUCKETS == {}
    assert "paced_by_model" not in _blob(stats_dir)


def test_the_bucket_key_is_the_key_llm_stats_books_the_call_under(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, _ = _messages(1200)
    _install(monkeypatch, world, [P120])
    providers.chat(msgs, route="ask")
    _install(monkeypatch, world, [P20])
    providers.chat(msgs, route="ask")
    rows = llm_stats.usage_summary(1)["measured_by_model"]
    assert {r["key"] for r in rows} == {K120, K20}
    assert set(providers._BUCKETS) == {K120, K20}
    assert set(_blob(stats_dir)["paced_by_model"]) == {K120, K20}


# --------------------------------------------------------------------------- #
# 6. chat() with the bucket: skip, wait, force
# --------------------------------------------------------------------------- #

def test_a_provider_that_would_wait_too_long_is_skipped_before_any_sleep(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120, P20])
    _fill(P120, 15.0, est)                        # 120b needs 15 s; budget is 6 s
    assert providers.chat(msgs, route="ask") == GOOD.strip()
    assert [m for m, _t in calls] == [M20], "the saturated model must not even be called"
    assert world.sleeps == [], "a skip is decided BEFORE sleeping, not after"
    paced = _blob(stats_dir)["paced_by_model"]
    assert paced[K20] == {"reserved": 1, "waits": 0, "wait_ms": 0, "skips": 0, "forced": 0}


def test_an_affordable_wait_is_slept_then_the_call_is_made(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120])
    _fill(P120, 5.0, est)                         # under the 6 s interactive default
    providers.chat(msgs, route="ask")
    assert world.sleeps == [pytest.approx(5.0, abs=0.01)]
    assert [m for m, _t in calls] == [M120]
    p = _blob(stats_dir)["paced_by_model"][K120]
    assert (p["reserved"], p["waits"], p["skips"], p["forced"]) == (1, 1, 0, 0)
    assert p["wait_ms"] == pytest.approx(5000, abs=10)


def test_when_every_provider_is_over_budget_the_call_is_forced_not_failed(
        monkeypatch, world, pacing_on, stats_dir):
    """Pacing alone must never turn a reading into AllProvidersExhausted."""
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120])
    _fill(P120, 15.0, est)
    assert providers.chat(msgs, route="ask", max_wait_s=0) == GOOD.strip()
    assert len(calls) == 1 and world.sleeps == []
    p = _blob(stats_dir)["paced_by_model"][K120]
    assert (p["reserved"], p["waits"], p["skips"], p["forced"]) == (0, 0, 1, 1)


def test_the_job_budget_waits_where_the_interactive_default_skips(
        monkeypatch, world, pacing_on, stats_dir):
    """Same saturated bucket, same chain: only the budget differs, and it decides.

    This is what the job-budget plumbing (tests/test_pacing_job_budget.py) buys:
    with nobody waiting, the batch sits out a 15 s wait for the model it was
    given instead of spending a fallback on the next one.
    """
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120, P20])
    _fill(P120, 15.0, est)
    providers.chat(msgs, route="ask")                            # interactive default
    assert [m for m, _t in calls] == [M20] and world.sleeps == []
    del calls[:]
    providers.chat(msgs, route="ask", max_wait_s=providers.PACE_JOB_BUDGET_S)
    assert [m for m, _t in calls] == [M120], "the job budget should have waited for room"
    assert world.sleeps == [pytest.approx(15.0, abs=0.01)]


def test_forced_calls_go_in_ascending_predicted_wait(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120, P20])      # chain order: 120b first
    _fill(P120, 15.0, est)
    _fill(P20, 9.0, est)
    providers.chat(msgs, route="ask")
    assert [m for m, _t in calls] == [M20], "the shorter predicted wait is forced first"


def test_max_wait_is_a_total_across_the_chain_not_per_provider(
        monkeypatch, world, pacing_on, stats_dir):
    """Two 4 s waits against a 5 s budget: the first is slept, the second is not."""
    msgs, est = _messages(2000)

    def fail_120(model, n):
        if model == M120:
            raise APITimeoutError(request=httpx.Request("POST", GROQ))

    calls = _install(monkeypatch, world, [P120, P20], script=fail_120)
    _fill(P120, 4.0, est)
    _fill(P20, 4.0, est)
    assert providers.chat(msgs, route="ask", max_wait_s=5) == GOOD.strip()
    assert len(world.sleeps) == 1 and world.sleeps[0] == pytest.approx(4.0, abs=0.01), (
        "only the first 4 s fits; the second would take the total to 8 s")
    assert [m for m, _t in calls] == [M120, M20], "the second ran as a forced call"


def test_a_413_does_not_start_the_forced_pass(monkeypatch, world, pacing_on):
    """A request too large for the chain is structural; forcing would repeat it."""
    msgs, est = _messages(2000)

    class TooLarge(Exception):
        status_code = 413

    def boom(model, n):
        if model == "other-model":
            raise TooLarge("Request too large for model 'other-model'")

    calls = _install(monkeypatch, world, [P120, OTHER], script=boom)
    _fill(P120, 15.0, est)
    with pytest.raises(providers.RequestTooLarge):
        providers.chat(msgs, route="ask", max_wait_s=0)
    assert [m for m, _t in calls] == ["other-model"], "the skipped Groq model was forced after a 413"


def test_the_bucket_lock_is_free_while_a_caller_sleeps(monkeypatch, world, pacing_on):
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120])
    _fill(P120, 5.0, est)
    seen = []

    def sleeping(seconds):
        lock = providers._BUCKETS[K120]._lock
        got = lock.acquire(blocking=False)
        seen.append(got)
        if got:
            lock.release()
        world.sleep(seconds)

    monkeypatch.setattr(providers, "_pace_sleep", sleeping)
    providers.chat(msgs, route="ask")
    assert seen == [True], "sleeping while holding the lock would stall every other caller"


# --------------------------------------------------------------------------- #
# 7. settling: what the bucket is charged after the call
# --------------------------------------------------------------------------- #

def _level(provider) -> float:
    return providers._bucket_for(provider)._level


def test_a_success_is_settled_to_the_tokens_the_response_reported(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120], usage=(2700, 510))
    providers.chat(msgs, route="ask")
    assert _level(P120) == pytest.approx(3210), "estimate in, 2700 + 510 out"


def test_a_quality_failure_is_still_charged_what_groq_counted(
        monkeypatch, world, pacing_on, stats_dir):
    """The tokens were spent even though the reading was thrown away."""
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120], usage=(2700, 510), text=SHORT)
    with pytest.raises(providers.AllProvidersExhausted):
        providers.chat(msgs, route="ask")
    assert _level(P120) == pytest.approx(3210)


def test_a_429_is_refunded_because_nothing_was_consumed(monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)

    def limited(model, n):
        raise _rate_limit("Rate limit reached on tokens per minute (TPM)")   # no hint: no retry

    _install(monkeypatch, world, [P120], script=limited)
    with pytest.raises(providers.AllProvidersExhausted):
        providers.chat(msgs, route="ask")
    assert _level(P120) == pytest.approx(0)


def test_a_timeout_keeps_the_estimate_because_groq_may_have_counted_it(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)

    def slow(model, n):
        raise APITimeoutError(request=httpx.Request("POST", GROQ))

    _install(monkeypatch, world, [P120], script=slow)
    with pytest.raises(providers.AllProvidersExhausted):
        providers.chat(msgs, route="ask")
    assert _level(P120) == pytest.approx(est)


def test_the_retry_after_a_hinted_429_asks_the_bucket_again(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)

    def first_is_limited(model, n):
        if n == 1:
            raise _rate_limit("on tokens per minute (TPM). Please try again in 2.00s.")

    calls = _install(monkeypatch, world, [P120], script=first_is_limited)
    providers.chat(msgs, route="ask")
    assert len(calls) == 2 and 2.0 in world.sleeps
    assert _blob(stats_dir)["paced_by_model"][K120]["reserved"] == 2, (
        "the retry is a second request and needs its own room")
    assert _level(P120) == pytest.approx(3210), "the refused first attempt was refunded"


def test_a_later_attempt_is_not_settled_against_an_earlier_calls_figures(
        monkeypatch, world, pacing_on, stats_dir):
    """The thread-pool leak. A worker thread keeps its ContextVars across tasks.

    Call one reports (1000 prompt, 500 completion). Call two reports a prompt
    size and NO completion -- driven through a fake `_call_one`, because the real
    one always overwrites all three variables together; the leak is reachable
    only by an attempt that never gets that far or a future provider path.
    Without a per-attempt reset, two is settled against one's completion
    (2000 + 500); with it, two has no complete figure and keeps its estimate.
    """
    msgs, est = _messages(2000)
    state = {"n": 0}

    def call_one(provider, messages):
        state["n"] += 1
        providers._last_usage.set(1500 if state["n"] == 1 else None)
        if state["n"] == 1:
            providers._last_prefix.set((1000, None, False))
            providers._last_completion.set(500)
        else:
            providers._last_prefix.set((2000, None, False))     # completion left alone
        return GOOD

    monkeypatch.setattr(providers, "_call_one", call_one)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: [P120])
    providers.chat(msgs, route="ask")
    after_one = _level(P120)
    assert after_one == pytest.approx(1500)
    providers.chat(msgs, route="ask")
    assert _level(P120) - after_one == pytest.approx(est), (
        "call two was settled against call one's completion_tokens")
    assert providers.last_used_tokens() is None, "call one's total leaked into call two"


# --------------------------------------------------------------------------- #
# 8. observability
# --------------------------------------------------------------------------- #

def test_paced_by_model_lands_in_the_blob_in_one_storage_write(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120])
    _fill(P120, 5.0, est)
    writes = []
    real = llm_stats.storage.update_json

    def counting(key, mutator, **kw):
        writes.append(key)
        return real(key, mutator, **kw)

    monkeypatch.setattr(llm_stats.storage, "update_json", counting)
    providers.chat(msgs, route="ask")
    assert len(writes) == 1, f"pacing added a storage write: {writes}"
    assert K120 in _blob(stats_dir)["paced_by_model"]


# --- every provider's pacing is booked under ITS OWN key (QA round 1, #475) ---
#
# chat() keeps one counter dict per provider it touches, but only the serving
# provider's used to reach llm_stats.record(). So the model that waited and then
# 429'd, or that was skipped, was exactly the one missing from the panel.

def test_a_provider_that_waited_then_429d_is_booked_under_its_own_key(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)

    def limited(model, n):
        if model == M120:
            raise _rate_limit("Rate limit reached on tokens per minute (TPM)")  # no hint: no retry

    calls = _install(monkeypatch, world, [P120, P20], script=limited)
    _fill(P120, 3.0, est)                          # within the 6 s default: it WAITS, then 429s
    providers.chat(msgs, route="ask")
    assert [m for m, _t in calls] == [M120, M20]
    paced = _blob(stats_dir)["paced_by_model"]
    p120 = paced[K120]
    assert (p120["reserved"], p120["waits"], p120["skips"], p120["forced"]) == (1, 1, 0, 0)
    assert p120["wait_ms"] == pytest.approx(3000, abs=10), "the 3 s wait went to the wrong model"
    assert paced[K20] == {"reserved": 1, "waits": 0, "wait_ms": 0, "skips": 0, "forced": 0}


def test_a_skipped_provider_that_did_not_serve_still_shows_its_skip(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120, P20])
    _fill(P120, 15.0, est)                         # over the 6 s default: skipped, not called
    providers.chat(msgs, route="ask")
    paced = _blob(stats_dir)["paced_by_model"]
    assert paced[K120] == {"reserved": 0, "waits": 0, "wait_ms": 0, "skips": 1, "forced": 0}
    assert paced[K20]["reserved"] == 1 and paced[K20]["skips"] == 0


def test_when_both_are_over_budget_both_skips_are_booked_and_the_forced_one_too(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    calls = _install(monkeypatch, world, [P120, P20])
    _fill(P120, 12.0, est)
    _fill(P20, 14.0, est)
    providers.chat(msgs, route="ask")
    assert [m for m, _t in calls] == [M120], "the shorter predicted wait is forced"
    paced = _blob(stats_dir)["paced_by_model"]
    assert (paced[K120]["skips"], paced[K120]["forced"], paced[K120]["reserved"]) == (1, 1, 0)
    assert (paced[K20]["skips"], paced[K20]["forced"], paced[K20]["reserved"]) == (1, 0, 0), (
        "the second provider's skip was lost: only the serving provider was recorded")


def test_several_models_pacing_is_still_one_storage_write(
        monkeypatch, world, pacing_on, stats_dir):
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120, P20])
    _fill(P120, 15.0, est)
    writes = []
    real = llm_stats.storage.update_json

    def counting(key, mutator, **kw):
        writes.append(key)
        return real(key, mutator, **kw)

    monkeypatch.setattr(llm_stats.storage, "update_json", counting)
    providers.chat(msgs, route="ask")
    assert set(_blob(stats_dir)["paced_by_model"]) == {K120, K20}
    assert len(writes) == 1, f"booking two models added a storage write: {writes}"


def test_the_llm_call_log_carries_the_time_spent_waiting(
        monkeypatch, world, pacing_on, stats_dir, caplog):
    msgs, est = _messages(2000)
    _install(monkeypatch, world, [P120])
    _fill(P120, 5.0, est)
    with caplog.at_level(logging.INFO, logger="astro_ai.providers"):
        providers.chat(msgs, route="ask")
    fields = [r.json_fields for r in caplog.records if hasattr(r, "json_fields")]
    assert len(fields) == 1 and fields[0]["paced_wait_s"] == pytest.approx(5.0, abs=0.01)


def test_the_llm_call_log_says_null_when_the_call_was_not_paced(
        monkeypatch, world, stats_dir, caplog):
    msgs, _ = _messages(2000)
    _install(monkeypatch, world, [OTHER])
    with caplog.at_level(logging.INFO, logger="astro_ai.providers"):
        providers.chat(msgs, route="ask")
    fields = [r.json_fields for r in caplog.records if hasattr(r, "json_fields")]
    assert fields[0]["paced_wait_s"] is None, "not paced is a silence, not a 0.0 wait"
