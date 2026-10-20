"""Where a cache miss's 40 seconds goes, and why half the misses needed a 2nd provider (#355).

Production's own store said: avg miss latency 40s, 101 fallbacks against 196
misses over 30 days. Neither could be attributed. `miss_latency_sum_ms` was
recorded only GLOBALLY, so a 24-reading rashifal blast and a single `/ask`
were one number; and `record()` took `fallback: bool`, so "the first provider
was rate-limited" and "the first provider returned garbage" were the same
count. The stated limit on the issue was that the figure was real and unusable.

These tests pin the three things the fix has to keep true:

  * latency is per ROUTE, and a day-file written before the change reads as
    UNKNOWN (None) rather than as fast (0) — and does not dilute a day that
    has the data;
  * the fallback reason is the one the failing provider actually gave, and
    the reasons sum to the fallbacks;
  * /admin/ops says which store it read, because "0 errors" from a developer's
    /tmp and from production's bucket looked identical.

Hermetic: no bucket, no network, no LLM. Storage is a tmp dir.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from astro_ai import llm_stats, ops_data, providers, storage


@pytest.fixture
def stats_dir(tmp_path, monkeypatch):
    """Point llm_stats at a tmp dir and make GCS unavailable, so it uses it."""
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    d = tmp_path / "llm_stats"
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", d)
    return d


def _today_blob(stats_dir):
    return json.loads((stats_dir / f"{date.today().isoformat()}.json").read_text())


# --------------------------------------------------------------------------
# per-route miss latency
# --------------------------------------------------------------------------

def test_two_routes_with_different_latencies_get_different_averages(stats_dir):
    for ms in (60_000, 40_000):
        llm_stats.record_call(route="rashifal", cache_hit=False, latency_ms=ms)
    llm_stats.record_call(route="ask", cache_hit=False, latency_ms=4_000)
    llm_stats.record_call(route="ask", cache_hit=True)   # a hit must not count

    by = {r["route"]: r for r in llm_stats.usage_summary(1)["by_route"]}
    assert by["rashifal"]["avg_miss_latency_ms"] == 50_000
    assert by["ask"]["avg_miss_latency_ms"] == 4_000, (
        "a cache hit has no latency to average in; counting it halves the figure"
    )


def test_a_day_file_from_before_the_change_is_unknown_not_fast(stats_dir):
    """The reason per-route latency is TWO keys and not one.

    Day-files written before #355 hold misses and no latency. Averaging over
    `calls - hits` would put zeros in the numerator for all of them, and a zero
    on /admin/ops reads as "fast".
    """
    stats_dir.mkdir(parents=True)
    old = date.today() - timedelta(days=1)
    (stats_dir / f"{old.isoformat()}.json").write_text(json.dumps({
        "date": old.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0,
        "calls": {"total": 10, "hits": 0, "misses": 10, "input_tokens": 1000,
                  "output_tokens": 100, "miss_latency_sum_ms": 400_000},
        "call_by_route": {"rashifal": {"calls": 10, "hits": 0,
                                       "input_tokens": 1000, "output_tokens": 100}},
    }))

    only_old = {r["route"]: r for r in llm_stats.usage_summary(2)["by_route"]}
    assert only_old["rashifal"]["avg_miss_latency_ms"] is None

    # And it must not dilute a day that does have the data.
    llm_stats.record_call(route="rashifal", cache_hit=False, latency_ms=30_000)
    mixed = {r["route"]: r for r in llm_stats.usage_summary(2)["by_route"]}
    assert mixed["rashifal"]["calls"] == 11
    assert mixed["rashifal"]["avg_miss_latency_ms"] == 30_000, (
        "the 10 old misses have no latency recorded; they must not drag the "
        "one measured miss toward zero"
    )


def test_the_global_latency_figure_keeps_its_shape(stats_dir):
    """admin_dashboard.html and ops_data read these keys; they must not move."""
    llm_stats.record_call(route="ask", cache_hit=False, latency_ms=2_000)
    s = llm_stats.usage_summary(1)
    assert s["avg_miss_latency_ms"] == 2_000
    assert _today_blob(stats_dir)["calls"]["miss_latency_sum_ms"] == 2_000


# --------------------------------------------------------------------------
# _failure_reason
# --------------------------------------------------------------------------

def _rate_limit(msg: str) -> RateLimitError:
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return RateLimitError(msg, response=httpx.Response(429, request=req), body=None)


class _Status(Exception):
    def __init__(self, code: int, msg: str) -> None:
        super().__init__(msg)
        self.status_code = code


GROQ_TPM = ("Rate limit reached for model `openai/gpt-oss-120b` in organization `org_x` "
            "service tier `on_demand` on tokens per minute (TPM): Limit 8000, Used 7900, "
            "Requested 3300.")
GROQ_TPD = ("Rate limit reached for model `openai/gpt-oss-120b` on tokens per day (TPD): "
            "Limit 200000, Used 199000, Requested 3300.")


@pytest.mark.parametrize("err, expected", [
    (_rate_limit(GROQ_TPM), "429_tpm"),
    (_rate_limit(GROQ_TPD), "429_tpd"),
    (_rate_limit("Too many requests, slow down"), "429"),
    # Groq's 413 body spells out "tokens per minute (TPM)"; it is structural,
    # and filing it under 429_tpm is the conflation RequestTooLarge exists to stop.
    (_Status(413, "Request too large for model on tokens per minute (TPM): Limit 8000"),
     "413"),
    (APITimeoutError(request=httpx.Request("POST", "https://x")), "timeout"),
    (providers.EmptyCompletion("200 with no text"), "empty"),
    (ValueError("anything else"), "error"),
])
def test_failure_reason_classification(err, expected):
    assert providers._failure_reason(err) == expected


# --------------------------------------------------------------------------
# chat() -> llm_stats.record
# --------------------------------------------------------------------------

def _chain(*names):
    return [providers.ProviderConfig(n, f"https://{n}.example/v1", f"{n}-model", "K")
            for n in names]


def _run_chat(monkeypatch, behaviours, route="ask"):
    """Run chat() over fakes. `behaviours[name]` is an exception or a reply."""
    chain = _chain(*behaviours)

    def fake_call_one(provider, messages):
        b = behaviours[provider.name]
        if isinstance(b, Exception):
            raise b
        return b

    monkeypatch.setattr(providers, "_ordered_for_request", lambda: chain)
    monkeypatch.setattr(providers, "_call_one", fake_call_one)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    return providers.chat([{"role": "user", "content": "x"}], route=route)


GOOD = "A perfectly adequate reading. " * 10


def test_a_tpm_429_then_success_is_recorded_with_its_reason_and_provider(
        stats_dir, monkeypatch):
    seen = {}
    real = llm_stats.record

    def spy(**kw):
        seen.update(kw)
        real(**kw)

    monkeypatch.setattr(llm_stats, "record", spy)
    out = _run_chat(monkeypatch, {"first": _rate_limit(GROQ_TPM), "second": GOOD})

    assert out == GOOD.strip()
    assert seen["provider"] == "second"
    assert seen["fallback"] is True
    assert seen["fallback_reason"] == "429_tpm"
    assert seen["failed_provider"] == "first"

    blob = _today_blob(stats_dir)
    assert blob["fallback_reasons"] == {"first|429_tpm": 1}


def test_reasons_sum_to_fallbacks_across_mixed_failures(stats_dir, monkeypatch):
    """The invariant the docstring states, over every way a provider can fail."""
    short = "too short"          # passes the call, fails the quality gate on `ask`
    cases = [
        {"a": _rate_limit(GROQ_TPD), "b": GOOD},
        {"a": providers.EmptyCompletion("no text"), "b": GOOD},
        {"a": short, "b": GOOD},
        {"a": _Status(500, "boom"), "b": GOOD},
        {"a": GOOD},                                   # no fallback at all
    ]
    for c in cases:
        _run_chat(monkeypatch, c)

    blob = _today_blob(stats_dir)
    assert blob["fallbacks"] == 4
    assert sum(blob["fallback_reasons"].values()) == blob["fallbacks"]
    assert blob["fallback_reasons"] == {
        "a|429_tpd": 1, "a|empty": 1, "a|quality": 1, "a|error": 1,
    }


def test_a_fallback_with_no_reason_is_still_counted_in_the_reasons(stats_dir):
    """A caller on the old `fallback=True` signature must not break the sum."""
    llm_stats.record(provider="p", model="m", route="ask", fallback=True)
    blob = _today_blob(stats_dir)
    assert blob["fallbacks"] == 1
    assert blob["fallback_reasons"] == {"unknown|unknown": 1}


def test_range_summary_sums_reasons_and_tolerates_old_days(stats_dir):
    stats_dir.mkdir(parents=True)
    old = date.today() - timedelta(days=1)
    (stats_dir / f"{old.isoformat()}.json").write_text(json.dumps(
        {"date": old.isoformat(), "counts": {}, "totals": {}, "fallbacks": 5}))
    for _ in range(2):
        llm_stats.record(provider="a", model="m", route="ask", fallback=True,
                         fallback_reason="429_tpm", failed_provider="g")
    llm_stats.record(provider="a", model="m", route="ask", fallback=True,
                     fallback_reason="timeout", failed_provider="g")

    agg = llm_stats.range_summary(2)["aggregate"]
    assert agg["fallbacks"] == 8
    assert list(agg["fallback_reasons"].items()) == [("g|429_tpm", 2), ("g|timeout", 1)]


# --------------------------------------------------------------------------
# naming the store
# --------------------------------------------------------------------------

def test_describe_store_names_the_bucket_or_the_local_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("BHAGYA_STORAGE_BUCKET", " some-bucket ")
    assert storage.describe_store() == "gcs:some-bucket"

    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET")
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
    assert storage.describe_store() == f"local:{tmp_path / 'stats'}"


def _ops_page(client, monkeypatch, tmp_path):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    # AND the today tiles. Rendering /admin/ops goes down the live path for
    # both, so without this the behaviour suite spends the runner's 60/hour
    # GitHub budget. Found by QA on #418 with a `urlopen` recorder, not by a
    # failing test: a real request that succeeds looks exactly like no request.
    #
    # These two lines are no longer what makes this test hermetic, and the
    # round-1 version of this comment claimed they were. They stopped the two
    # `api.github.com` calls and left SIXTEEN requests to
    # raw.githubusercontent.com — eight per test — because the line below
    # points `OPS_MEASUREMENTS_DIR` at a path that does not exist, which is
    # exactly what drops every `_fetch` onto its HTTPS branch. The guard that
    # actually holds is `conftest._no_outbound_http`; these stay because
    # pinning the two switches is still the right thing for a test that is not
    # about the live path, and because a URLError'd live read is a different
    # code path from a switched-off one.
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(tmp_path / "none"))
    ops_data._cache.clear()
    ops_data._app_cache.clear()
    try:
        r = client.get("/admin/ops", auth=("admin", "bhagya-dev"))
    finally:
        ops_data._app_cache.clear()
        ops_data._cache.clear()
    return r


def test_ops_says_it_is_reading_a_local_dev_store(client, stats_dir, monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
    llm_stats.record_call(route="rashifal", cache_hit=False, latency_ms=41_200)
    llm_stats.record(provider="second", model="m", route="rashifal", fallback=True,
                     fallback_reason="429_tpm", failed_provider="first")
    r = _ops_page(client, monkeypatch, tmp_path)
    assert r.status_code == 200
    html = r.text
    assert "local dev store — not production" in html
    assert str(stats_dir) in html
    assert "first 429_tpm ×1" in html
    assert "41.2 s" in html
    # The tooltip must name BOTH local dirs: events does not use llm_stats' dir.
    from astro_ai import events
    assert str(events._LOCAL_FALLBACK_DIR) in html
    assert "needed a retry or a 2nd provider" in html
    assert "reason for the last failure" in html


def test_ops_names_the_bucket_when_one_is_configured(client, stats_dir, monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
    llm_stats.record_call(route="ask", cache_hit=False, latency_ms=1_000)
    # Configured but unreachable: the data still comes from the tmp dir (the
    # call-time fallback), which is a limit of describe_store() the docstring
    # states — it reports configuration, not reachability.
    monkeypatch.setenv("BHAGYA_STORAGE_BUCKET", "prod-bucket")
    monkeypatch.setattr(storage, "_client", lambda: None)
    r = _ops_page(client, monkeypatch, tmp_path)
    assert r.status_code == 200
    assert "gcs:prod-bucket" in r.text
    assert "not production" not in r.text
    assert "configured, not verified reachable" in r.text
