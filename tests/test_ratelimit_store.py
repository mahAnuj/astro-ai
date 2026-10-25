"""The `ratelimit_by_model` store behind the cached-token probe (#475 Phase 1b).

Read/write side only; nothing here produces a probe increment by running the
probe -- every test hands `record()` one directly (the capture side is
tests/test_ratelimit_probe.py).

What is easy to get quietly wrong, and so is pinned:

  * `record()` must still make exactly ONE storage write per call -- the new key
    rides the existing mutator (a second `update_json` per call would double the
    cross-continent GCS round-trips on the LLM path, #144);
  * `_PREFIX_ZERO` must stay at its eight keys. A ninth is how the prefix-cache
    panel once emptied itself: every row already stored fails the
    `_PREFIX_ZERO.keys() <= pc.keys()` gate and is skipped whole;
  * a day with no `ratelimit_by_model` contributes NOTHING (not a zero) and is
    not counted in `ratelimit_days`;
  * `last_limit` is a state, not a quantity: the latest day's value, never a sum;
  * a hand-edited blob must not take the window down;
  * a request that fails on every provider books nothing -- record() is
    success-only, and the panel says so.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from astro_ai import llm_stats
from astro_ai import ratelimit_probe as rp

G = ("groq120", "openai/gpt-oss-120b")
K = "groq120|openai/gpt-oss-120b"
K20 = "groq20|openai/gpt-oss-20b"


def inc(**kw):
    return {**{"warm_seen": 1, "warm_n": 1, "warm_rem": 5000, "warm_exp": 5100,
               "warm_cached": 2304, "warm_disc": 0, "last_limit": 8000}, **kw}


@pytest.fixture
def day(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path)
    monkeypatch.setattr(llm_stats.storage, "update_json", lambda *a, **k: None)
    monkeypatch.setattr(llm_stats.storage, "get_json", lambda *a, **k: None)
    return tmp_path


def blob(day_dir) -> dict:
    files = list(day_dir.glob("*.json"))
    assert files, "record() wrote nothing"
    return json.loads(files[0].read_text())


def write_day(day_dir, d, content) -> None:
    (day_dir / f"{d.isoformat()}.json").write_text(json.dumps(
        {"date": d.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0, **content}))


def test_record_sums_the_counters_and_overwrites_last_limit(day):
    llm_stats.record(provider=G[0], model=G[1], route="ask", prompt_tokens=3000,
                     completion_tokens=300, ratelimit=inc(warm_rem=100, warm_exp=200))
    llm_stats.record(provider=G[0], model=G[1], route="ask", prompt_tokens=3000,
                     completion_tokens=300,
                     ratelimit=inc(warm_rem=50, warm_exp=70, warm_disc=1, last_limit=6000))
    c = blob(day)["ratelimit_by_model"][K]
    assert (c["warm_seen"], c["warm_n"], c["warm_rem"], c["warm_exp"], c["warm_cached"],
            c["warm_disc"]) == (2, 2, 150, 270, 4608, 1)
    assert c["last_limit"] == 6000, "a limit is a state: the latest value, not a sum"
    assert set(c) == set(rp.FIELDS), "every counter is present from the first write"


def test_a_call_with_no_increments_writes_no_key_at_all(day):
    """Absent, not zero: that is how the panel tells 'probe never ran' from 'ran, kept nothing'."""
    for rl in (None, {}):
        llm_stats.record(provider=G[0], model=G[1], route="ask", prompt_tokens=10,
                         completion_tokens=5, ratelimit=rl)
    assert "ratelimit_by_model" not in blob(day)


def test_record_is_still_exactly_one_storage_write_per_call(monkeypatch):
    calls = []

    def fake_update(key, mut, default=None):
        calls.append(key)
        return mut(None)                    # non-None: no local-fallback second write

    monkeypatch.setattr(llm_stats.storage, "update_json", fake_update)
    llm_stats.record(provider=G[0], model=G[1], route="rashifal_single", prompt_tokens=3000,
                     completion_tokens=500, cached_tokens=2304, ratelimit=inc())
    assert len(calls) == 1, f"the probe must ride the existing mutator, got {len(calls)} writes"


def test_prefix_zero_is_untouched_and_prefix_rows_survive_a_probe_write(day):
    assert len(llm_stats._PREFIX_ZERO) == 8
    kw = dict(provider=G[0], model=G[1], route="rashifal_single", prompt_tokens=3000,
              completion_tokens=300, cached_tokens=2304)
    llm_stats.record(**kw)
    plain = llm_stats.range_summary(1)["aggregate"]
    assert plain["prefix_cache"]["rashifal_single"]["calls"] == 1
    llm_stats.record(**kw, ratelimit=inc())
    after = llm_stats.range_summary(1)["aggregate"]
    assert after["prefix_cache"]["rashifal_single"]["calls"] == 2, "range_summary lost its prefix rows"
    assert after["prefix_cache_skipped_rows"] == 0, "a stored row failed the eight-key schema gate"
    assert set(blob(day)["prefix_cache"]["groq120|openai/gpt-oss-120b|rashifal_single"]) == set(
        llm_stats._PREFIX_ZERO)


def test_the_blob_grows_with_models_not_with_calls(day):
    for i in range(120):
        who = ("groq120", "a") if i % 2 else ("groq20", "b")
        llm_stats.record(provider=who[0], model=who[1], route="ask", ratelimit=inc())
    assert set(blob(day)["ratelimit_by_model"]) == {"groq120|a", "groq20|b"}


def test_garbage_and_negative_values_cannot_poison_the_counters(day):
    llm_stats.record(provider="g", model="m", route="ask",
                     ratelimit={"warm_seen": 2, "warm_n": "x", "warm_rem": -500, "skip_clamp": None,
                                "cold_abs": True, "last_limit": -3})
    c = blob(day)["ratelimit_by_model"]["g|m"]
    assert c["warm_seen"] == 2 and c["warm_n"] == 0 and c["warm_rem"] == 0
    assert c["skip_clamp"] == 0 and c["cold_abs"] == 0 and c["last_limit"] == 0


def test_cold_increments_never_reach_the_warm_counters(day):
    llm_stats.record(provider=G[0], model=G[1], route="ask",
                     ratelimit={"cold_seen": 3, "cold_n": 2, "cold_rem": 10, "cold_exp": 12,
                                "cold_abs": 2, "skip_noanchor": 1})
    c = blob(day)["ratelimit_by_model"][K]
    assert (c["warm_seen"], c["warm_n"], c["warm_rem"], c["warm_exp"], c["warm_cached"]) == (0,) * 5
    assert (c["cold_seen"], c["cold_n"]) == (3, 2)


# --------------------------------------------------------------------------- #
# the read side
# --------------------------------------------------------------------------- #

def mm(calls=1):
    return {"calls": calls, "measured": calls, "input_tokens": 10, "output_tokens": 5}


def test_usage_summary_sums_across_days_and_counts_only_days_that_carried_the_key(day):
    today = date.today()
    write_day(day, today, {"measured_by_model": {K: mm()},
                           "ratelimit_by_model": {K: {**inc(), "warm_n": 3, "last_limit": 8000}}})
    write_day(day, today - timedelta(days=1), {
        "measured_by_model": {K: mm()},
        "ratelimit_by_model": {K: {**inc(), "warm_n": 4, "last_limit": 6000}}})
    write_day(day, today - timedelta(days=2), {"measured_by_model": {K: mm()}})   # no probe
    write_day(day, today - timedelta(days=3), {})                                  # legacy
    s = llm_stats.usage_summary(4)
    assert s["ratelimit_days"] == 2
    (row,) = s["measured_by_model"]
    assert row["ratelimit"]["warm_n"] == 7 and row["ratelimit"]["warm_seen"] == 2
    assert row["ratelimit"]["last_limit"] == 8000, "newest day wins; 14,000 would be a sum"


def test_a_model_the_probe_never_saw_reports_none_not_a_dict_of_zeros(day):
    write_day(day, date.today(), {"measured_by_model": {K: mm(), K20: mm()},
                                  "ratelimit_by_model": {K: inc()}})
    rows = {r["key"]: r for r in llm_stats.usage_summary(1)["measured_by_model"]}
    assert rows[K]["ratelimit"]["warm_n"] == 1
    assert rows[K20]["ratelimit"] is None


def test_a_window_with_no_probe_has_zero_probe_days(day):
    write_day(day, date.today(), {"measured_by_model": {K: mm()}})
    s = llm_stats.usage_summary(1)
    assert s["ratelimit_days"] == 0 and s["measured_by_model"][0]["ratelimit"] is None


def test_a_hand_edited_blob_does_not_raise_and_range_summary_is_unchanged(day):
    today = date.today()
    base = {"counts": {"groq120|openai/gpt-oss-120b|ask": 3}, "totals": {"ask": 3}, "fallbacks": 1,
            "fallback_reasons": {"groq120|429_tpm": 1}}
    write_day(day, today, base)
    plain = llm_stats.range_summary(1)["aggregate"]
    write_day(day, today, {**base, "measured_by_model": {"e|f": mm(2)},
                           "ratelimit_by_model": {"a|b": "garbage", "c|d": {"warm_n": "x", "warm_seen": [1]},
                                                  "e|f": inc(warm_n=2)}})
    s = llm_stats.usage_summary(1)                                     # must not raise
    rows = {r["key"]: r for r in s["measured_by_model"]}
    assert rows["e|f"]["ratelimit"]["warm_n"] == 2
    assert "a|b" not in rows
    assert rows["c|d"]["ratelimit"]["warm_n"] == 0, "a malformed value counts as 0"
    assert llm_stats.range_summary(1)["aggregate"] == plain
    write_day(day, today, {**base, "ratelimit_by_model": "not a dict"})
    assert llm_stats.usage_summary(1)["ratelimit_days"] == 0


def test_a_request_that_fails_on_every_provider_books_nothing(monkeypatch, tmp_path):
    """record() is success-only, so the probe's samples from a request that ends in
    AllProvidersExhausted are not on the panel. The panel says so; this makes it true."""
    from types import SimpleNamespace

    from _fake_openai import WithHeaders, fake_client

    from astro_ai import providers

    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "s")
    monkeypatch.setenv("K", "k")
    p = providers.ProviderConfig("groq120", "https://api.groq.com/openai/v1", G[1], "K")
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="too short"), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=3000, completion_tokens=300, total_tokens=3300,
                              prompt_tokens_details=SimpleNamespace(cached_tokens=2304)))
    monkeypatch.setattr(providers, "OpenAI", lambda **kw: fake_client(
        lambda **k: WithHeaders(resp, {"x-ratelimit-limit-tokens": "8000",
                                       "x-ratelimit-remaining-tokens": "5000"})))
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: [p])
    with pytest.raises(providers.AllProvidersExhausted):
        providers.chat([{"role": "user", "content": "x"}], route="ask")
    assert not list((tmp_path / "s").glob("*.json")), "a failed request must book nothing"
