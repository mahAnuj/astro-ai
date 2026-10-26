"""The cached-token accounting probe (#475 Phase 1b) -- capture, isolation, verdict.

THE QUESTION. `providers._pace_done` settles every reservation at
`prompt_tokens + completion_tokens`: cached prompt tokens at FULL weight. Whether
Groq bills them against the 8,000 TPM limit is unknown, and the only place its own
accounting is exposed is the `x-ratelimit-remaining-tokens` response header. This
phase READS that header off calls traffic is already making and changes nothing
about what the bucket charges.

HOW THESE ARE BUILT. Hermetic: a fake clock (`ratelimit_probe._clock`), a fake
OpenAI client (tests/_fake_openai.py), no socket. The Groq stand-in is not a mock
that always agrees: `HeaderLimiter` is a refill-at-limit/60 bucket that emits the
header in three flavours -- charging cached tokens in full, charging them at
nothing, and charging in full while ANOTHER consumer drains the same key -- and
the key test runs ~30 calls of each through the REAL `chat()` and `_call_one`
and asserts the verdict. A probe that can only ever say FULL WEIGHT is not an
instrument; the DISCOUNTED and NOISY runs are what show this one can say no.

WHAT IS PINNED, and why each is here:
  * the header parser never raises and rejects anything that is not a sane pair;
  * a sample exists only when nothing else touched that model's bucket, and every
    other candidate is a visible skip, not a match;
  * cold calls run the same formula as a control and are never counted as warm;
  * a failed attempt breaks the chain, because it may still have been charged;
  * ONE HTTP request per chat() attempt (two only on the reasoning_effort 400);
  * `_last_rl` is reset before every attempt;
  * settle() is unchanged -- this phase is measure-only.
"""
from __future__ import annotations

import json
import random
from types import SimpleNamespace

import httpx
import pytest
from _fake_openai import WithHeaders, fake_client
from openai import APIConnectionError, BadRequestError

from astro_ai import llm_stats, providers
from astro_ai import ratelimit_probe as rp

GROQ = "https://api.groq.com/openai/v1"
M120, M20 = "openai/gpt-oss-120b", "openai/gpt-oss-20b"
P120 = providers.ProviderConfig("groq120", GROQ, M120, "K")
P20 = providers.ProviderConfig("groq20", GROQ, M20, "K")
K120, K20 = f"groq120|{M120}", f"groq20|{M20}"
LIMIT = 8000
RATE = LIMIT / 60.0
GOOD = "A perfectly adequate reading. " * 12


def hdr(remaining, limit=LIMIT):
    return {"x-ratelimit-limit-tokens": str(limit), "x-ratelimit-remaining-tokens": str(remaining)}


# --------------------------------------------------------------------------- #
# the header parser
# --------------------------------------------------------------------------- #

def test_parse_accepts_a_sane_pair_in_any_case_and_as_strings_or_ints():
    assert rp.parse_headers(hdr(7500)) == (8000, 7500)
    assert rp.parse_headers({"X-RateLimit-Limit-Tokens": 8000,
                             "X-RATELIMIT-REMAINING-TOKENS": "0"}) == (8000, 0)
    assert rp.parse_headers(httpx.Headers(hdr(123))) == (8000, 123)


@pytest.mark.parametrize("headers", [
    {},                                                           # nothing
    {"x-ratelimit-limit-tokens": "8000"},                          # no remaining
    {"x-ratelimit-remaining-tokens": "100"},                       # no limit
    hdr("abc"),                                                    # not numeric
    hdr("7500.5"),                                                 # not an integer
    hdr("-1"),                                                     # negative
    hdr(9000),                                                     # remaining > limit
    {"x-ratelimit-limit-tokens": "0", "x-ratelimit-remaining-tokens": "0"},   # no limit
    {"x-ratelimit-limit-tokens": True, "x-ratelimit-remaining-tokens": 1},    # bool is not a count
    None,                                                          # not even a mapping
    object(),
])
def test_parse_rejects_anything_that_is_not_a_sane_pair_without_raising(headers):
    assert rp.parse_headers(headers) is None


# --------------------------------------------------------------------------- #
# the formula and the isolation rule, driven directly on a fake clock
# --------------------------------------------------------------------------- #

class Clock:
    def __init__(self):
        self.now = 1000.0


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(rp, "_clock", lambda: c.now)
    return c


def one_call(clock, key, remaining, *, prompt=3000, cached=2304, completion=300,
             before=0.0, latency=6.0, limit=LIMIT, headers=True):
    """begin -> advance -> finish. Returns the increments finish() produced."""
    clock.now += before
    t = rp.begin(key)
    clock.now += latency
    rl = (limit, remaining) if headers else None
    return rp.finish(t, rl, (prompt, cached, False), completion)


def test_predicted_remaining_is_anchor_plus_steady_refill_minus_prompt_plus_completion(clock):
    """The sentence on the panel: previous remaining + limit/60 per second - (prompt + completion)."""
    assert one_call(clock, K120, 2000) == {"warm_seen": 1, "last_limit": 8000, "skip_noanchor": 1}
    # 30 s idle + 6 s in flight = 36 s of refill = 4800; 2000 + 4800 - 3300 = 3500
    out = one_call(clock, K120, 3500, before=30.0, latency=6.0)
    assert out["warm_n"] == 1 and out["warm_exp"] == 3500 and out["warm_rem"] == 3500
    assert out["warm_cached"] == 2304 and out["warm_disc"] == 0


def test_a_header_above_the_prediction_by_most_of_the_cached_count_votes_discounted(clock):
    one_call(clock, K120, 5000)
    out = one_call(clock, K120, 2500 + 2304, before=0.0, latency=6.0)     # exp = 5000 + 800 - 3300
    assert (out["warm_exp"], out["warm_rem"], out["warm_disc"]) == (2500, 4804, 1)


def test_a_header_below_the_prediction_never_votes_discounted(clock):
    """Another consumer only lowers the figure: that reads as 'charged MORE', not as a discount."""
    one_call(clock, K120, 5000)
    out = one_call(clock, K120, 1000, latency=6.0)                         # exp = 2500
    assert out["warm_disc"] == 0 and out["warm_rem"] < out["warm_exp"]


def test_the_first_call_has_no_anchor_and_says_so(clock):
    out = one_call(clock, K120, 5000)
    assert out.get("skip_noanchor") == 1 and "warm_n" not in out


def test_overlapping_calls_are_both_skipped_and_leave_no_anchor(clock):
    one_call(clock, K120, 5000)                                           # anchor
    a = rp.begin(K120)
    clock.now += 1
    b = rp.begin(K120)
    clock.now += 5
    out_a = rp.finish(a, (LIMIT, 4000), (3000, 2304, False), 300)
    out_b = rp.finish(b, (LIMIT, 3000), (3000, 2304, False), 300)
    assert out_a.get("skip_overlap") == 1 and "warm_n" not in out_a
    assert out_b.get("skip_overlap") == 1 and "warm_n" not in out_b
    # and the NEXT call cannot lean on either of them
    assert one_call(clock, K120, 5000).get("skip_noanchor") == 1


def test_a_call_that_starts_while_another_is_in_flight_is_not_a_sample_even_if_it_finishes_first(clock):
    """The second call sees no start or finish during its OWN run -- but the first was already
    running when it began, so the bucket was shared for all of it."""
    one_call(clock, K120, 5000)                                           # anchor
    first = rp.begin(K120)
    clock.now += 1
    second = rp.begin(K120)
    clock.now += 5
    out_second = rp.finish(second, (LIMIT, 4000), (3000, 2304, False), 300)
    assert out_second.get("skip_noanchor") == 1 and "warm_n" not in out_second
    out_first = rp.finish(first, (LIMIT, 3000), (3000, 2304, False), 300)
    assert out_first.get("skip_overlap") == 1 and "warm_n" not in out_first


def test_a_failed_attempt_breaks_the_chain_because_it_may_still_have_been_charged(clock):
    one_call(clock, K120, 5000)
    t = rp.begin(K120)
    clock.now += 4
    rp.abort(t)
    out = one_call(clock, K120, 5000)
    assert out.get("skip_noanchor") == 1 and "warm_n" not in out


def test_calls_on_a_different_model_do_not_break_this_models_isolation(clock):
    """The bucket is per provider|model; a call to the other model touches a different bucket."""
    one_call(clock, K120, 5000)
    one_call(clock, K20, 5000)
    one_call(clock, K20, 5000)
    out = one_call(clock, K120, 5000 + 6000 - 3300, before=0.0)
    assert out.get("warm_n") == 1, out


def test_a_response_without_headers_is_a_visible_skip_and_leaves_no_anchor(clock):
    one_call(clock, K120, 5000)
    out = one_call(clock, K120, 0, headers=False)
    assert out.get("skip_nohdr") == 1 and "warm_n" not in out
    assert one_call(clock, K120, 5000).get("skip_noanchor") == 1


def test_a_cold_call_runs_the_same_formula_but_is_never_a_warm_sample(clock):
    one_call(clock, K120, 5000)
    out = one_call(clock, K120, 5000 + 800 - 1200, prompt=900, cached=0, completion=300,
                   latency=6.0)
    assert out["cold_seen"] == 1 and out["cold_n"] == 1
    assert out["cold_abs"] == 0 and out["cold_exp"] == out["cold_rem"]
    assert not {"warm_seen", "warm_n", "warm_rem", "warm_exp", "warm_cached"} & set(out)
    # cached_tokens absent (None) is cold too -- Groq omits the object on a miss
    out = one_call(clock, K120, 5000, cached=None)
    assert out.get("cold_seen") == 1 and "warm_seen" not in out


def test_a_full_or_empty_bucket_is_skipped_as_clamped_not_counted_as_agreement(clock):
    """The two invalid shapes are skipped, and counted APART from each other.

    They mean different things to an operator. A ceiling is structural -- on a
    path whose request is the size of the whole bucket it fires on every call
    forever, so `skip_full` rising while `warm_n` stays at 0 says "this path
    cannot be measured by this instrument". An empty bucket is incidental.
    One counter for both could not say which was happening, and the reader
    would see INSUFFICIENT and assume "not deployed long enough".
    """
    one_call(clock, K120, 8000)
    # remaining 8000 + refill beyond the limit - tiny charge: the bucket was at
    # its ceiling before the call, so nothing accumulated during it.
    out = one_call(clock, K120, 8000, prompt=100, cached=64, completion=10, before=20.0)
    assert out.get("skip_full") == 1 and "warm_n" not in out
    assert "skip_clamp" not in out, "a ceiling is counted as a ceiling, not lumped in"
    one_call(clock, K120, 100)
    out = one_call(clock, K120, 0, prompt=5000, cached=2304, completion=1000, latency=1.0)
    assert out.get("skip_clamp") == 1 and "warm_n" not in out         # predicted below zero
    assert "skip_full" not in out


def test_a_sample_whose_bucket_was_at_the_ceiling_is_never_counted_clean(clock):
    """BUG-2 from the independent QA round on PR #536, pinned.

    The old guard tested `exp_full` -- the OUTPUT of the arithmetic -- so when
    `pre = min(limit, ...)` bit, the over-add of `rate x duration` went
    unnoticed and the sample was booked as agreement. Because `pred` is
    98-101% of `limit` for natal (7,871 en / 8,056 hi against 8,000, measured
    2026-10-25), `exp_full > 0` required a near-full bucket -- so the samples
    that survived were exactly the invalid ones.
    """
    one_call(clock, K120, 8000)
    # A long idle gap refills past the ceiling before the call even starts.
    out = one_call(clock, K120, 7000, prompt=3000, cached=2304, completion=800,
                   before=600.0, latency=5.0)
    assert out.get("skip_full") == 1, out
    assert "warm_n" not in out and "warm_disc" not in out, (
        "a sample taken while the bucket was at its ceiling was counted as "
        "agreement; that is the defect this test exists for"
    )


def test_a_call_whose_usage_cannot_be_read_claims_nothing(clock):
    t = rp.begin(K120)
    assert rp.finish(t, (LIMIT, 5000), None, 300) is None
    t = rp.begin(K120)
    assert rp.finish(t, (LIMIT, 5000), (3000, None, True), 300) is None   # impossible cached figure
    t = rp.begin(K120)
    assert rp.finish(t, (LIMIT, 5000), (3000, 100, False), None) is None
    assert rp.finish(None, (LIMIT, 5000), (3000, 100, False), 300) is None


def test_a_changed_limit_between_calls_is_not_compared(clock):
    one_call(clock, K120, 5000, limit=8000)
    assert one_call(clock, K120, 5000, limit=6000).get("skip_noanchor") == 1


def test_every_classified_call_is_either_a_sample_or_a_counted_skip(clock):
    """warm_seen + cold_seen == warm_n + cold_n + skips -- nothing disappears."""
    rng = random.Random(7)
    totals: dict[str, int] = {}

    def add(out):
        for k, v in (out or {}).items():
            if k != "last_limit":
                totals[k] = totals.get(k, 0) + v

    remaining = 4000
    for i in range(80):
        roll = rng.random()
        if roll < 0.1:
            add(one_call(clock, K120, remaining, headers=False))
        elif roll < 0.2:
            t = rp.begin(K120)
            add(one_call(clock, K120, remaining, before=0.5))
            clock.now += 1
            add(rp.finish(t, (LIMIT, remaining), (3000, 2304, False), 300))
        else:
            add(one_call(clock, K120, remaining, before=rng.choice([0, 5, 30]),
                         cached=rng.choice([0, 2304, None]),
                         prompt=rng.choice([2400, 3000]), completion=rng.choice([200, 500])))
        remaining = rng.randint(1500, 6000)
    seen = totals.get("warm_seen", 0) + totals.get("cold_seen", 0)
    samples = totals.get("warm_n", 0) + totals.get("cold_n", 0)
    skips = sum(v for k, v in totals.items() if k.startswith("skip_"))
    assert seen == samples + skips and seen > 40, totals
    assert samples > 0 and skips > 0, "the generator must exercise both sides"


# --------------------------------------------------------------------------- #
# the verdict: a pure function of the summed counters
# --------------------------------------------------------------------------- #

def counters(*, warm_n=20, cold_n=5, f=0.0, cached=2304, vote=0.0, cold_mean_abs=0.0):
    """Counters that yield a chosen discounted fraction, vote and cold error."""
    return {"warm_n": warm_n, "warm_cached": cached * warm_n,
            "warm_exp": 10000 * warm_n, "warm_rem": round((10000 + f * cached) * warm_n),
            "warm_disc": round(vote * warm_n),
            "cold_n": cold_n, "cold_abs": round(cold_mean_abs * cold_n)}


def test_verdict_is_insufficient_below_the_sample_floors_and_not_above_them():
    assert rp.verdict(counters(warm_n=rp.MIN_WARM - 1))["verdict"] == "INSUFFICIENT"
    assert rp.verdict(counters(cold_n=rp.MIN_COLD - 1))["verdict"] == "INSUFFICIENT"
    assert rp.verdict(counters(warm_n=rp.MIN_WARM, cold_n=rp.MIN_COLD))["verdict"] != "INSUFFICIENT"
    assert (rp.MIN_WARM, rp.MIN_COLD) == (20, 5)


def test_verdict_full_weight_discounted_partial_and_noisy():
    assert rp.verdict(counters(f=0.0, vote=0.0))["verdict"] == "FULL WEIGHT"
    assert rp.verdict(counters(f=1.0, vote=1.0))["verdict"] == "DISCOUNTED"
    assert rp.verdict(counters(f=0.5, vote=0.5))["verdict"] == "PARTIAL"
    # f says full weight but a third of the samples individually say otherwise
    assert rp.verdict(counters(f=0.0, vote=0.35))["verdict"] == "PARTIAL"
    assert rp.verdict(counters(f=1.0, vote=0.5))["verdict"] == "PARTIAL"
    noisy = rp.verdict(counters(f=0.0, vote=0.0, cold_mean_abs=0.25 * 2304 + 10))
    assert noisy["verdict"] == "NOISY"
    assert rp.verdict(counters(f=0.0, vote=0.0, cold_mean_abs=0.25 * 2304 - 10))["verdict"] == "FULL WEIGHT"


def test_verdict_reads_a_garbage_blob_as_insufficient_not_as_an_error():
    for junk in ({}, {"warm_n": "x", "cold_n": None}, {"warm_n": True}, {"warm_n": -5},
                 {"warm_n": 99, "cold_n": 99}):          # samples but no cached count at all
        assert rp.verdict(junk)["verdict"] == "INSUFFICIENT", junk


# --------------------------------------------------------------------------- #
# through the REAL chat() and _call_one, against a Groq-shaped limiter
# --------------------------------------------------------------------------- #

class World(Clock):
    pass


class HeaderLimiter:
    """Per-model refill-at-limit/60 bucket that reports `remaining` the way Groq's header does.

    `mode` decides what a warm call is charged: "full" (prompt + completion) or
    "discount" (prompt - cached + completion). `extra(model)` is another consumer
    of the same key, invisible to the app, that drains tokens between its calls.
    """

    def __init__(self, world, mode="full", start=4500.0, extra=None, limit=LIMIT):
        self.w, self.mode, self.extra, self.limit = world, mode, extra, limit
        self.level = {}
        self.t = {}
        self.start = start

    def _refill(self, model):
        lvl = self.level.get(model, self.start)
        t = self.t.get(model, self.w.now)
        lvl = min(self.limit, lvl + (self.w.now - t) * self.limit / 60.0)
        self.t[model] = self.w.now
        return lvl

    def drain_other_consumer(self, model):
        if self.extra:
            self.level[model] = self._refill(model) - self.extra(model)

    def respond(self, model, prompt, cached, completion):
        lvl = self._refill(model)
        charge = prompt + completion - (cached if self.mode == "discount" else 0)
        lvl -= charge
        self.level[model] = lvl
        return int(max(lvl, 0))


def install(monkeypatch, world, limiter, chain, script):
    """chat() over the real _call_one; `script(n)` -> (prompt, cached, completion) per call."""
    monkeypatch.setenv("K", "k")
    monkeypatch.setattr(rp, "_clock", lambda: world.now)
    calls = {"n": 0, "models": []}

    def factory(*, api_key=None, base_url=None, **kw):
        def create(*, model, messages, **k):
            calls["n"] += 1
            calls["models"].append(model)
            prompt, cached, completion = script(calls["n"])
            world.now += 5.0                                   # time in flight
            remaining = limiter.respond(model, prompt, cached, completion)
            usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                                    total_tokens=prompt + completion)
            if cached is not None:
                usage.prompt_tokens_details = SimpleNamespace(cached_tokens=cached)
            resp = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=GOOD),
                                         finish_reason="stop")], usage=usage)
            return WithHeaders(resp, hdr(remaining, limiter.limit))
        return fake_client(create)

    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: list(chain))
    return calls


@pytest.fixture
def stats_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "llm_stats")
    return tmp_path / "llm_stats"


def stored(stats_dir) -> dict:
    files = list(stats_dir.glob("*.json"))
    assert files, "record() wrote nothing"
    return json.loads(files[0].read_text())


def drive(monkeypatch, stats_dir, mode, *, extra=None, extra_mean=0, n_calls=46):
    """~36 warm and ~10 cold sequential chat() calls; returns the stored counters."""
    world = World()
    limiter = HeaderLimiter(world, mode=mode, extra=extra)
    # every 4th call is cold; spacing keeps the bucket mid-range in each scenario
    def script(n):
        return (3000, 0, 300) if n % 4 == 1 else (3000, 2304, 300)

    install(monkeypatch, world, limiter, [P120], script)
    warm_charge = 3300 if mode == "full" else 3300 - 2304
    mean = (warm_charge * 3 + 3300) / 4 + extra_mean
    cycle = mean / RATE
    for n in range(1, n_calls + 1):
        world.now += max(cycle - 5.0, 0.0)
        limiter.drain_other_consumer(M120)
        providers.chat([{"role": "user", "content": "x"}], route="ask")
    return stored(stats_dir)["ratelimit_by_model"][K120]


def test_charging_cached_tokens_in_full_reads_as_full_weight(monkeypatch, stats_dir):
    c = drive(monkeypatch, stats_dir, "full")
    v = rp.verdict(c)
    assert v["verdict"] == "FULL WEIGHT", (v, c)
    assert v["n_warm"] >= rp.MIN_WARM and v["n_cold"] >= rp.MIN_COLD
    assert abs(v["f"]) <= 0.05 and c["warm_disc"] == 0


def test_not_charging_cached_tokens_reads_as_discounted(monkeypatch, stats_dir):
    """The run that shows the probe can say no."""
    c = drive(monkeypatch, stats_dir, "discount")
    v = rp.verdict(c)
    assert v["verdict"] == "DISCOUNTED", (v, c)
    assert v["f"] > 0.95 and c["warm_disc"] == c["warm_n"]


def test_another_consumer_of_the_key_reads_as_noisy_and_never_as_discounted(monkeypatch, stats_dir):
    rng = random.Random(3)
    c = drive(monkeypatch, stats_dir, "full", extra=lambda m: rng.choice([900, 1500]),
              extra_mean=1200, n_calls=60)
    v = rp.verdict(c)
    assert v["verdict"] == "NOISY", (v, c)
    # the direction the panel's sentence claims: an extra consumer lowers Groq's
    # figure below the prediction, so f is NEGATIVE and no sample votes discounted
    assert v["f"] < 0 and c["warm_disc"] == 0, (v, c)


def test_cold_calls_are_excluded_from_the_warm_count_and_the_skips_add_up(monkeypatch, stats_dir):
    c = drive(monkeypatch, stats_dir, "full")
    assert c["warm_seen"] + c["cold_seen"] == 46
    assert c["cold_seen"] == 12 and c["warm_seen"] == 34       # every 4th call, from the 1st
    assert c["warm_n"] <= c["warm_seen"] and c["cold_n"] <= c["cold_seen"]
    skips = sum(c[k] for k in ("skip_noanchor", "skip_overlap", "skip_nohdr", "skip_clamp"))
    assert c["warm_seen"] + c["cold_seen"] == c["warm_n"] + c["cold_n"] + skips
    assert c["skip_noanchor"] == 1, "only the very first call has nothing before it"
    assert c["last_limit"] == LIMIT


def test_one_http_request_per_chat_call_and_no_probe_request(monkeypatch, stats_dir):
    """0 added LLM calls: the probe rides the request traffic was already making."""
    world = World()
    calls = install(monkeypatch, world, HeaderLimiter(world), [P120, P20],
                    lambda n: (3000, 2304, 300))
    for _ in range(7):
        world.now += 30
        providers.chat([{"role": "user", "content": "x"}], route="ask")
    assert calls["n"] == 7, calls
    assert set(calls["models"]) <= {M120, M20}


def test_the_reasoning_effort_retry_is_still_two_requests_not_three(monkeypatch, stats_dir):
    monkeypatch.setattr(providers, "_NO_REASONING_EFFORT", set())
    monkeypatch.setenv("K", "k")
    seen = []

    def factory(*, api_key=None, base_url=None, **kw):
        def create(*, model, messages, **k):
            seen.append(sorted(k))
            if "reasoning_effort" in k:
                req = httpx.Request("POST", GROQ + "/chat/completions")
                raise BadRequestError("reasoning_effort is not supported", body=None,
                                      response=httpx.Response(400, request=req))
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=GOOD),
                                         finish_reason="stop")],
                usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        return fake_client(create)

    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: [P120])
    providers.chat([{"role": "user", "content": "x"}], route="ask")
    assert seen == [["reasoning_effort"], []], seen
    seen.clear()
    providers.chat([{"role": "user", "content": "x"}], route="ask")
    assert seen == [[]], "the capability is remembered: back to one request per call"


def test_headers_reach_the_parser_through_the_real_sdk_not_only_through_a_fake(monkeypatch):
    """A fake client proves the plumbing I wrote; this proves the SDK delivers what it reads."""
    import openai

    def handler(request):
        body = {"id": "1", "object": "chat.completion", "created": 1, "model": M120,
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": GOOD}}],
                "usage": {"prompt_tokens": 3000, "completion_tokens": 300, "total_tokens": 3300,
                          "prompt_tokens_details": {"cached_tokens": 2304}}}
        return httpx.Response(200, json=body, headers={
            "X-RateLimit-Limit-Tokens": "8000", "X-RateLimit-Remaining-Tokens": "4321"})

    def factory(*, api_key=None, base_url=None, **kw):
        return openai.OpenAI(api_key="k", base_url="http://groq.invalid/v1", max_retries=0,
                             http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setenv("K", "k")
    monkeypatch.setattr(providers, "OpenAI", factory)
    assert providers._call_one(P120, [{"role": "user", "content": "x"}]) == GOOD
    assert providers._last_rl.get() == (8000, 4321)
    assert providers._last_prefix.get() == (3000, 2304, False)


def test_last_rl_is_reset_before_every_attempt(monkeypatch, stats_dir):
    """Attempt 1 (groq120) sees headers then fails the quality gate; attempt 2 (groq20) is a
    double that sets usage but no headers. Without the reset, attempt 2 is scored against
    attempt 1's headers instead of being counted as having none."""
    monkeypatch.setenv("K", "k")
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: [P120, P20])
    monkeypatch.setattr(providers, "OpenAI", lambda **kw: fake_client(
        lambda **k: WithHeaders(SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="too short"),
                                     finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=3000, completion_tokens=300, total_tokens=3300,
                                  prompt_tokens_details=SimpleNamespace(cached_tokens=2304))),
            hdr(5000))))
    real = providers._call_one

    def call_one(provider, messages):
        if provider.name == "groq120":
            return real(provider, messages)                 # sets _last_rl, then fails the gate
        providers._last_prefix.set((3000, 2304, False))     # usage, but never any headers
        providers._last_completion.set(300)
        return GOOD

    monkeypatch.setattr(providers, "_call_one", call_one)
    providers.chat([{"role": "user", "content": "x"}], route="ask")
    c = stored(stats_dir)["ratelimit_by_model"][K20]
    assert c["skip_nohdr"] == 1 and c["warm_seen"] == 1, c


def test_a_failed_attempt_in_chat_breaks_the_probe_chain(monkeypatch, stats_dir):
    world = World()
    limiter = HeaderLimiter(world)
    state = {"fail_on": None}
    calls = install(monkeypatch, world, limiter, [P120], lambda n: (3000, 2304, 300))
    real_openai = providers.OpenAI

    def flaky(**kw):
        client = real_openai(**kw)
        inner = client.chat.completions.with_raw_response.create

        def create(**k):
            if calls["n"] + 1 == state["fail_on"]:
                calls["n"] += 1
                raise APIConnectionError(request=httpx.Request("POST", GROQ))
            return inner(**k)
        client.chat.completions.with_raw_response.create = create
        return client

    monkeypatch.setattr(providers, "OpenAI", flaky)
    state["fail_on"] = 3
    for _ in range(5):
        world.now += 30
        try:
            providers.chat([{"role": "user", "content": "x"}], route="ask")
        except providers.AllProvidersExhausted:
            pass
    c = stored(stats_dir)["ratelimit_by_model"][K120]
    # calls 1, 2 | 3 fails | 4, 5 (4 re-anchors, 5 is a sample again)
    #
    # `warm_n` is 1, not 2, SINCE THE BUG-2 FIX. One of the two formerly-counted
    # samples was taken while the bucket sat at its ceiling and is now
    # `skip_full`. It was never a valid sample; the old guard inspected
    # `exp_full` and could not see the clamp that produced it. The drop is the
    # fix working, and the fixture's 30s spacing is what puts the bucket there.
    assert c["warm_seen"] == 4 and c["skip_noanchor"] == 2, c
    assert c["warm_n"] + c.get("skip_full", 0) == 2, c
    assert c["warm_n"] == 1 and c.get("skip_full") == 1, c


def test_settle_is_unchanged_a_warm_call_is_still_charged_prompt_plus_completion(monkeypatch):
    """Measure-only: the bucket must go on charging cached tokens in full."""
    monkeypatch.setenv("BHAGYA_TPM_PACING", "1")
    bucket = providers._bucket_for(P120)
    res, _ = bucket.reserve(5000, 0.0)
    providers._last_prefix.set((2700, 2000, False))          # 2,000 of 2,700 prompt tokens cached
    providers._last_completion.set(500)
    providers._pace_done(res, None)
    assert bucket._level == 3200, "settle() must charge prompt + completion, cached included"


# --- BUG-4: a model two live chain entries claim is not measurable -----------

def test_the_probe_refuses_a_model_two_chain_entries_share(monkeypatch):
    """Groq limits per account AND MODEL, so `groq` and `groq120` -- same model,
    same key -- share one bucket while `_bucket_key` gives them two sequences.

    A sibling's charge between this call's anchor and its response is then
    invisible and the sample is booked clean, and the error runs the WRONG WAY:
    a hidden charge lowers Groq's reported figure below the prediction, pushing
    toward a false FULL WEIGHT. That is the one verdict that would justify
    leaving `settle()` alone for good, so a false one is the expensive
    direction to be wrong in.

    The probe refuses rather than `_bucket_key` being re-keyed: that key is the
    one `chat()` hands `llm_stats.record`, and changing it would make the
    bucket's figures and `measured_by_model` disagree about a row on
    /admin/ops.
    """
    from astro_ai import providers

    class P:
        def __init__(self, name, model):
            self.name, self._m = name, model

        def model(self):
            return self._m

    solo = P("groq120", "openai/gpt-oss-120b")
    monkeypatch.setattr(providers, "_chain", lambda: [solo])
    assert providers._model_is_shared(solo) is False, (
        "a model only one chain entry claims is measurable"
    )

    twin = P("groq", "openai/gpt-oss-120b")
    monkeypatch.setattr(providers, "_chain", lambda: [solo, twin])
    assert providers._model_is_shared(solo) is True
    assert providers._model_is_shared(twin) is True

    other = P("cerebras", "llama-3.3-70b")
    monkeypatch.setattr(providers, "_chain", lambda: [solo, twin, other])
    assert providers._model_is_shared(other) is False, (
        "a different model is unaffected by the pair sharing one bucket"
    )


def test_a_probe_that_cannot_read_the_chain_refuses_rather_than_raises():
    """A measurement must never be the thing that takes down a live LLM call."""
    from astro_ai import providers

    class Broken:
        name = "x"

        def model(self):
            raise RuntimeError("chain unreadable")

    assert providers._model_is_shared(Broken()) is True


def test_chat_books_no_sample_at_all_when_the_model_is_shared(monkeypatch, stats_dir):
    """BUG-4 at the CALL SITE, not just in the helper.

    An earlier version of this file tested `_model_is_shared` directly and
    nothing else, so deleting the guard from `chat()`'s `begin()` call changed
    no test — the mutation sweep reported it MIS-POINTED, which is how a
    guard that is present in a helper and absent from the wiring survives.

    Here the chain lists two entries on the same model, which Groq limits as
    ONE bucket, and the probe must book nothing: no warm sample, no cold
    sample, no skip counters either, because no ticket is ever opened.
    """
    world = World()
    limiter = HeaderLimiter(world)
    install(monkeypatch, world, limiter, [P120], lambda n: (3000, 2304, 300))

    class Twin:
        name = "groq"

        def model(self):
            return P120.model()

    # Both entries resolve to P120's model, so Groq charges one bucket while
    # `_bucket_key` would hand out two independent probe sequences.
    monkeypatch.setattr(providers, "_chain", lambda: [P120, Twin()])

    for _ in range(4):
        world.now += 30
        providers.chat([{"role": "user", "content": "x"}], route="ask")

    probe = stored(stats_dir).get("ratelimit_by_model") or {}
    assert probe.get(K120, {}) == {} or not any(probe.get(K120, {}).values()), (
        f"the probe scored a model two live chain entries share: {probe}"
    )
