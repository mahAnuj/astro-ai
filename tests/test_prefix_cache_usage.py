"""Groq's prefix cache is measured, and "not reported" is never shown as zero (#396).

Production runs two models that cache prompt prefixes automatically, and nothing
in the repo read the figure -- `usage.prompt_tokens_details.cached_tokens` had
zero occurrences. The dashboard's only "cache" number was the app's own response
cache, a different mechanism with a different lifetime.

The defect worth guarding is not "the field is not read" but its quiet cousin:
a provider that does NOT report the field (every non-Groq provider, and any
model without caching) being recorded as a measured 0. That would put a
confident "0% cached" on a route nobody measured, and it is the exact reading
that sends a future change toward context reduction on a false premise.

These run the REAL `_call_one` against a fake OpenAI client -- a faked
`_call_one` would skip the one function that reads the field.

Hermetic: no bucket, no network, no LLM. Storage is a tmp dir.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from astro_ai import events, llm_stats, providers

GOOD = "A perfectly adequate reading. " * 10
SHORT = "too short"        # 200 OK, fails the quality gate on `ask`


@pytest.fixture
def stats_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    d = tmp_path / "llm_stats"
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", d)
    return d


def _usage(prompt=2278, cached="absent"):
    """A usage block. cached="absent" omits prompt_tokens_details entirely, as
    every non-Groq provider does; None models details present, field null."""
    u = SimpleNamespace(prompt_tokens=prompt, total_tokens=prompt + 300)
    if cached != "absent":
        u.prompt_tokens_details = SimpleNamespace(cached_tokens=cached)
    return u


def _install(monkeypatch, replies, route="ask"):
    """chat() over the real _call_one. `replies[name]` = (text, usage)."""
    chain = [providers.ProviderConfig(n, f"https://{n}.example/v1", f"{n}-model", "K")
             for n in replies]
    monkeypatch.setenv("K", "k")

    def factory(*, api_key=None, base_url=None, **kw):
        name = base_url.split("//")[1].split(".")[0]
        text, usage = replies[name]
        resp = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text),
                                     finish_reason="stop")],
            usage=usage)
        completions = SimpleNamespace(create=lambda **k: resp)
        return SimpleNamespace(chat=SimpleNamespace(completions=completions))

    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: chain)
    return route


def _chat(route="ask"):
    return providers.chat([{"role": "user", "content": "x"}], route=route)


def _agg(route="ask"):
    return llm_stats.range_summary(1)["aggregate"]["prefix_cache"][route]


# 1 -------------------------------------------------------------------------

def test_a_reported_cache_figure_is_recorded_and_becomes_a_ratio(stats_dir, monkeypatch):
    _install(monkeypatch, {"p": (GOOD, _usage(2278, cached=1920))})
    _chat()
    e = _agg()
    assert (e["calls"], e["reported"]) == (1, 1)
    assert (e["prompt_tokens"], e["cached_tokens"]) == (2278, 1920)
    assert e["pct"] == pytest.approx(84.3, abs=0.05)


# 2 -------------------------------------------------------------------------

def test_a_provider_that_does_not_report_is_absent_never_zero(stats_dir, monkeypatch):
    """The issue's required absent-field test: a non-Groq provider must not
    make the dashboard report a confident 0%."""
    _install(monkeypatch, {"p": (GOOD, _usage(2278))})     # no prompt_tokens_details
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["reported"] == 0
    assert e["prompt_tokens"] == 0 and e["cached_tokens"] == 0
    assert e["pct"] is None and e["pct"] != 0


# 3 -------------------------------------------------------------------------

def test_a_measured_miss_is_zero_and_distinct_from_absent(stats_dir, monkeypatch):
    _install(monkeypatch, {"p": (GOOD, _usage(2278, cached=0))})
    _chat()
    e = _agg()
    assert e["reported"] == 1 and e["pct"] == 0.0
    assert e["pct"] is not None


# 4 -------------------------------------------------------------------------

def test_a_null_cached_tokens_inside_details_is_absent(stats_dir, monkeypatch):
    _install(monkeypatch, {"p": (GOOD, _usage(2278, cached=None))})
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["reported"] == 0 and e["pct"] is None


@pytest.mark.parametrize("bad", [True, "1920", 12.5, object()])
def test_prefix_usage_accepts_only_real_ints(bad):
    assert providers._prefix_usage(_usage(100, cached=bad)) is None
    assert providers._prefix_usage(SimpleNamespace(prompt_tokens=bad)) is None
    assert providers._prefix_usage(None) is None
    assert providers._prefix_usage(_usage(100, cached=40)) == (100, 40)


# 5 -------------------------------------------------------------------------

def test_a_failed_providers_figures_do_not_become_the_next_providers(stats_dir, monkeypatch):
    """A returns 200 with cached=1000 but fails the quality gate; B serves and
    reports nothing. Only B is recorded, and it must record as absent."""
    _install(monkeypatch, {
        "a": (SHORT, _usage(2000, cached=1000)),
        "b": (GOOD, _usage(2278)),
    })
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["reported"] == 0
    assert e["cached_tokens"] == 0 and e["pct"] is None


def test_chat_resets_the_figure_before_each_call_so_a_stub_cannot_inherit_it(
        stats_dir, monkeypatch):
    """The reset in chat() is what protects a `_call_one` that never sets the
    variable (a test fake, or a future provider path) from reading the one
    before it. The real _call_one overwrites on every call, so only a call that
    does not reach that line can show the difference."""
    real = providers._call_one
    chain = [providers.ProviderConfig(n, f"https://{n}.example/v1", f"{n}-model", "K")
             for n in ("a", "b")]
    monkeypatch.setenv("K", "k")

    def factory(*, api_key=None, base_url=None, **kw):
        resp = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=SHORT),
                                     finish_reason="stop")],
            usage=_usage(2000, cached=1000))
        return SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **k: resp)))

    def call_one(provider, messages):
        if provider.name == "a":
            return real(provider, messages)       # sets (2000, 1000), then fails the gate
        return GOOD                                # never touches the variable

    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: chain)
    monkeypatch.setattr(providers, "_call_one", call_one)
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["reported"] == 0
    assert e["cached_tokens"] == 0 and e["pct"] is None


# 6 -------------------------------------------------------------------------

def test_the_ratio_is_over_reported_calls_only(stats_dir, monkeypatch):
    _install(monkeypatch, {"p": (GOOD, _usage(2000, cached=1000))})
    _chat()
    _install(monkeypatch, {"p": (GOOD, _usage(2278))})
    for _ in range(3):
        _chat()
    e = _agg()
    assert e["calls"] == 4 and e["reported"] == 1
    assert e["pct"] == 50.0, "three unreported calls must not dilute the one measurement"


# 7 -------------------------------------------------------------------------

def test_a_day_file_from_before_the_change_neither_errors_nor_dilutes(stats_dir, monkeypatch):
    stats_dir.mkdir(parents=True)
    old = date.today() - timedelta(days=1)
    (stats_dir / f"{old.isoformat()}.json").write_text(json.dumps({
        "date": old.isoformat(),
        "counts": {"groq120|m|ask": 50}, "totals": {"ask": 50}, "fallbacks": 0,
    }))
    # Only a pre-change day: nothing measured, nothing invented.
    assert llm_stats.range_summary(3)["aggregate"]["prefix_cache"] == {}

    _install(monkeypatch, {"p": (GOOD, _usage(2000, cached=1000))})
    _chat()
    agg = llm_stats.range_summary(3)["aggregate"]
    assert agg["prefix_cache"]["ask"]["calls"] == 1, "50 pre-change calls must not be counted"
    assert agg["prefix_cache"]["ask"]["pct"] == 50.0
    assert agg["total_calls"] == 51


def test_recording_a_prefix_figure_adds_no_storage_write(stats_dir, monkeypatch):
    """It rides the existing mutator. A second writer would double the GCS
    round-trips on every LLM call (the #144 failure class)."""
    writes = []
    real = llm_stats.storage.update_json
    monkeypatch.setattr(llm_stats.storage, "update_json",
                        lambda *a, **k: (writes.append(a[0]), real(*a, **k))[1])
    llm_stats.record(provider="p", model="m", route="ask")
    base = len(writes)
    llm_stats.record(provider="p", model="m", route="ask",
                     prompt_tokens=2000, cached_tokens=1000)
    assert len(writes) - base == base == 1


# 8 -------------------------------------------------------------------------

@pytest.fixture
def admin(client, monkeypatch):
    from astro_ai.main import app
    from astro_ai.routes.deps import require_admin

    app.dependency_overrides[require_admin] = lambda: None
    monkeypatch.setattr(events, "recent", lambda **k: [])
    monkeypatch.setattr(events, "counts_by_type", lambda **k: {})
    yield client
    app.dependency_overrides.pop(require_admin, None)


def _row(html: str, first_cell: str) -> str:
    for row in re.findall(r"<tr\b.*?</tr>", html, flags=re.S):
        cells = re.findall(r"<td\b.*?</td>", row, flags=re.S)
        if cells and re.sub(r"<[^>]+>", "", cells[0]).strip() == first_cell:
            return row
    raise AssertionError(f"no table row starting with {first_cell!r}")


def test_dashboard_names_both_caches_and_shows_unreported_as_a_dash(
        admin, stats_dir):
    llm_stats.record(provider="g", model="m", route="rashifal_single",
                     prompt_tokens=2278, cached_tokens=1920)
    llm_stats.record(provider="o", model="m", route="today")      # reports nothing

    r = admin.get("/admin")
    assert r.status_code == 200
    html = r.text
    assert "Response-cache" in html
    assert "Provider-side prefix cache" in html

    measured = _row(html, "rashifal_single")
    assert "84.3%" in measured
    unmeasured = _row(html, "today")
    assert "—" in unmeasured
    assert "0%" not in re.sub(r"<[^>]+>", " ", unmeasured), (
        "a route the provider never reported on must not read as 0% cached")
