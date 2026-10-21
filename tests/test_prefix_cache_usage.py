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


@pytest.fixture(autouse=True)
def _forget_warned_rows():
    """The skip WARNING is deduped per key per process (BUG-18), so a test that
    asserts the log fires must not inherit another test's suppression."""
    llm_stats._warned_rows.clear()
    yield
    llm_stats._warned_rows.clear()


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
    assert (e["prompt_reported"], e["cached_tokens"]) == (2278, 1920)
    assert e["hit_pct"] == pytest.approx(84.3, abs=0.05), (
        "a reported figure is the provider's own and counts whatever the model: "
        "cached_tokens is an OpenAI-compatible field and four of the eight "
        "configured providers are not Groq")
    # But this model is not in CACHE_REPORTING_MODELS, so a SILENCE from it would
    # have meant nothing, and effective_pct -- which is about silences -- abstains.
    assert e["measurable"] == 0 and e["effective_pct"] is None
    assert e["reported_unmeasurable"] == 1, (
        "a figure reported by a model our rule says cannot report is evidence the "
        "rule is wrong, so it is counted rather than dropped")


# 2 -------------------------------------------------------------------------

def test_a_provider_that_does_not_report_is_absent_never_zero(stats_dir, monkeypatch):
    """The issue's required absent-field test: a non-Groq provider must not
    make the dashboard report a confident 0%."""
    _install(monkeypatch, {"p": (GOOD, _usage(2278))})     # no prompt_tokens_details
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["measurable"] == 0 and e["reported"] == 0
    assert e["prompt_measurable"] == 0 and e["prompt_reported"] == 0
    assert e["cached_tokens"] == 0
    assert e["hit_pct"] is None and e["hit_pct"] != 0
    # BOTH rates stay None. This provider cannot report, so its silence carries
    # no information and must not be scored as a miss either.
    assert e["effective_pct"] is None and e["effective_pct"] != 0


# 3 -------------------------------------------------------------------------

def test_a_measured_miss_is_zero_and_distinct_from_absent(stats_dir, monkeypatch):
    """A reported ZERO is a measurement; an absent field is not.

    Note on the shape: Groq itself never sends `{"cached_tokens": 0}` -- measured
    2026-10-17, a miss omits `prompt_tokens_details` entirely, which is what
    test_a_provider_that_does_not_report_is_absent_never_zero covers. This case
    is the OpenAI-compatible contract rather than Groq's observed behaviour, kept
    because the chain has four non-Groq providers and any of them may send it.
    """
    _install(monkeypatch, {"p": (GOOD, _usage(2278, cached=0))})
    _chat()
    e = _agg()
    assert e["reported"] == 1 and e["hit_pct"] == 0.0
    assert e["hit_pct"] is not None


# 4 -------------------------------------------------------------------------

def test_a_null_cached_tokens_inside_details_is_absent(stats_dir, monkeypatch):
    _install(monkeypatch, {"p": (GOOD, _usage(2278, cached=None))})
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["reported"] == 0 and e["hit_pct"] is None


@pytest.mark.parametrize("bad", [True, "1920", 12.5, object()])
def test_prefix_usage_accepts_only_real_ints(bad):
    # A junk CACHED figure is discarded but the prompt size survives: it is what
    # lets llm_stats.record() tell "this model never reports" from "this call
    # missed". Returning None for the pair here is what hid that distinction.
    # `True` for the third element: the provider DID say something and it was
    # unusable, which record() must not book as a measured zero. Round 4 found
    # that collapsing "said nothing" into "said something impossible" made a
    # misreporting provider indistinguishable from one that missed.
    assert providers._prefix_usage(_usage(100, cached=bad)) == (100, None, True)
    # A junk PROMPT size leaves nothing usable, so the whole pair is dropped.
    assert providers._prefix_usage(SimpleNamespace(prompt_tokens=bad)) is None
    assert providers._prefix_usage(None) is None
    assert providers._prefix_usage(_usage(100, cached=40)) == (100, 40, False)


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
    assert e["cached_tokens"] == 0 and e["hit_pct"] is None


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
    assert e["cached_tokens"] == 0 and e["hit_pct"] is None


# 6 -------------------------------------------------------------------------

def test_the_ratio_is_over_reported_calls_only(stats_dir, monkeypatch):
    _install(monkeypatch, {"p": (GOOD, _usage(2000, cached=1000))})
    _chat()
    _install(monkeypatch, {"p": (GOOD, _usage(2278))})
    for _ in range(3):
        _chat()
    e = _agg()
    assert e["calls"] == 4 and e["reported"] == 1
    assert e["hit_pct"] == 50.0, "three unreported calls must not dilute the one measurement"


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
    assert agg["prefix_cache"]["ask"]["hit_pct"] == 50.0
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
    assert _pc_cells(html, "today")[-2:] == ["—", "—"], (
        "both rates are dashes; this used to pass on a literal em dash that "
        "only appeared inside the Hit-rate TOOLTIP text")
    assert "0%" not in re.sub(r"<[^>]+>", " ", unmeasured), (
        "a route the provider never reported on must not read as 0% cached")


# --- #396 follow-up: a MISS on a cache-reporting model is a measured zero ----
#
# Groq returns no `prompt_tokens_details` object at all on a cache miss -- not
# `cached_tokens: 0`. Measured live 2026-10-17 against openai/gpt-oss-120b with
# the real 2,363-token rashifal_single prefix: 1 hit (cached 2304) and 6 misses
# across 7 identical calls, every miss arriving as `prompt_tokens_details: null`.
#
# So "absent" means two different things depending on the model, and only one of
# them is unmeasurable. Scoring both as unmeasurable excluded every miss from the
# denominator and overstated the saving ~7x.

CACHING_MODEL = "openai/gpt-oss-120b"


def _install_model(monkeypatch, usages, model=CACHING_MODEL, route="ask"):
    """Like _install, but pins the MODEL -- which is what decides measurability.

    `usages` is a list consumed one per call, so a single install can serve a
    hit-then-miss sequence the way the live probe saw it.
    """
    chain = [providers.ProviderConfig("groq120", "https://p.example/v1", model, "K")]
    monkeypatch.setenv("K", "k")
    pending = list(usages)

    def factory(*, api_key=None, base_url=None, **kw):
        def create(**k):
            usage = pending.pop(0)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=GOOD),
                                         finish_reason="stop")],
                usage=usage)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    monkeypatch.setattr(providers, "OpenAI", factory)
    monkeypatch.setattr(providers, "_ordered_for_request", lambda: chain)
    return route


def test_the_two_rates_diverge_and_effective_is_the_honest_one(stats_dir, monkeypatch):
    """The live sample, replayed: 1 hit + 6 misses on a cache-reporting model.

    This is the regression the follow-up exists for. Before it, the six misses
    were all dropped from the denominator and the dashboard showed 97.5%.
    """
    hit = _usage(2363, cached=2304)
    misses = [_usage(2363) for _ in range(6)]          # details absent, as Groq sends
    _install_model(monkeypatch, [hit] + misses)
    for _ in range(7):
        _chat()
    e = _agg()
    assert (e["calls"], e["measurable"], e["reported"]) == (7, 7, 1)
    assert e["prompt_measurable"] == 2363 * 7
    assert e["prompt_reported"] == 2363
    assert e["cached_tokens"] == 2304

    # How hard a hit lands -- true, and not a saving.
    assert e["hit_pct"] == pytest.approx(97.5, abs=0.05)
    # The quota actually saved. 2304 / (2363*7).
    assert e["effective_pct"] == pytest.approx(13.9, abs=0.05)
    assert e["effective_pct"] < e["hit_pct"] / 6, (
        "a miss on a cache-reporting model must enter the denominator; if the two "
        "rates track each other the misses are being dropped again")


def test_a_miss_on_a_non_reporting_model_is_not_scored_as_zero(stats_dir, monkeypatch):
    """The other half of the distinction, and why it cannot just count every miss.

    llama-3.3-70b-versatile has no prefix cache at all, so its silence says
    nothing. Counting it as a measured zero would invent a 0% for a route that
    was never observed -- the mirror of the bug above.
    """
    _install_model(monkeypatch, [_usage(2363)], model="llama-3.3-70b-versatile")
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["measurable"] == 0 and e["reported"] == 0
    assert e["hit_pct"] is None and e["effective_pct"] is None


def test_a_prompt_under_the_minimum_cacheable_length_is_not_measurable(stats_dir, monkeypatch):
    """A prompt under MIN_CACHEABLE_PREFIX is unmeasured, not 0% cached.

    No real route lands here: the threshold is judged on the whole request and
    the smallest system prompt any route sends is 732 tokens (`monthly`), before
    its chart or question payload. `dasha` measures 1,426 on the wire and `today`
    1,863. The guard exists for a future short prompt, not for today's traffic --
    an earlier docstring named dasha (944) and today (743), which were
    system-prompt figures compared against a whole-request limit.
    """
    _install_model(monkeypatch, [_usage(llm_stats.MIN_CACHEABLE_PREFIX - 1)])
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["measurable"] == 0
    assert e["effective_pct"] is None, "an ineligible prompt is unmeasured, not 0%"


def test_a_reported_call_under_the_minimum_feeds_the_hit_rate_only(
        stats_dir, monkeypatch):
    """A sub-floor report is real data but says nothing about what a silence means.

    The earlier design shared one `cached_tokens` between both rates, so a
    reported sub-floor call HAD to be forced into `measurable` or effective_pct
    would exceed 100% -- and that force was what made measurability depend on the
    outcome. With separate numerators it goes to the hit rate, is counted in
    `reported_unmeasurable`, and touches the effective denominator not at all.
    """
    short = llm_stats.MIN_CACHEABLE_PREFIX - 1
    _install_model(monkeypatch, [_usage(short, cached=short)])
    _chat()
    e = _agg()
    assert e["reported"] == 1 and e["hit_pct"] == 100.0
    assert e["measurable"] == 0 and e["prompt_measurable"] == 0
    assert e["cached_measurable"] == 0, (
        "a sub-floor report must not enter the effective numerator, or its prompt "
        "tokens would have to be forced into the denominator to keep the ratio "
        "under 100% -- which is the outcome-dependence this design removed")
    assert e["effective_pct"] is None
    assert e["reported_unmeasurable"] == 1
    # Asserted on the sums and the flag, never on `pct <= 100`: _rate() clamps, so
    # that comparison is vacuous and would pass while the accounting was broken.
    assert e["impossible"] is False


def test_the_dashboard_shows_the_effective_rate_not_only_the_hit_rate(
        stats_dir, monkeypatch, admin):
    """The number a reader takes away must be the saving, not the hit rate."""
    _install_model(monkeypatch, [_usage(2363, cached=2304)] + [_usage(2363) for _ in range(6)])
    for _ in range(7):
        _chat()
    html = admin.get("/admin").text
    row = _row(html, "ask")
    assert "13.9%" in row, "the effective rate must be rendered"
    assert "Effective" in html and "Hit rate" in html, "both columns must be labelled"
    assert "Read Effective, not Hit rate" in html, (
        "the page must say which number is the saving; two bare percentages "
        "invite the reader to take the larger one")


# --- QA round 1 findings on #410 (BUG-1..BUG-9). Each defect, pinned. --------

def test_a_miss_and_a_hit_at_the_same_size_are_both_measurable(stats_dir, monkeypatch):
    """BUG-3. Measurability must depend on (model, size), never on the OUTCOME.

    With the floor at 1024 a hit at 714 tokens was measurable (because reporting
    implies measurable) while a miss at 714 on the identical request was not, so
    the denominator selected for hits -- the same bias at the length level that
    this module removed at the model level. 1 hit + 6 misses at 714 read 97.5%
    where the truth is 13.9%.
    """
    _install_model(monkeypatch, [_usage(714, cached=696)] + [_usage(714) for _ in range(6)],
                   model="openai/gpt-oss-20b")
    for _ in range(7):
        _chat()
    e = _agg()
    assert e["measurable"] == 7, (
        "a miss must be as measurable as a hit of the same size on the same model; "
        "if only the hit counts, the denominator selects for hits")
    assert e["prompt_measurable"] == 714 * 7
    assert e["effective_pct"] == pytest.approx(13.9, abs=0.05)
    assert e["hit_pct"] == pytest.approx(97.5, abs=0.05)


def test_the_threshold_is_the_bottom_of_groqs_range_not_the_top():
    """BUG-3. The constant's VALUE is the fix; pin it with the reason."""
    assert llm_stats.MIN_CACHEABLE_PREFIX == 128, (
        "128 is the bottom of Groq's documented 128-1024 range. At the top, a hit "
        "above the floor is measurable and a miss on the identical request is not")


def test_an_old_schema_day_blob_is_skipped_whole_not_summed_field_by_field(
        stats_dir, monkeypatch):
    """BUG-2. A row from the FIRST #396 schema must not inflate a mixed window.

    That schema stored `prompt_tokens`; this one stores `prompt_measurable` /
    `prompt_reported`. Summing by the current field list took such a row's
    cached_tokens into the numerator with nothing in either denominator, and a
    mixed window published 571% effective / 3998% hit.
    """
    stats_dir.mkdir(parents=True, exist_ok=True)
    old = date.today() - timedelta(days=1)
    (stats_dir / f"{old.isoformat()}.json").write_text(json.dumps({
        "date": old.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0,
        "prefix_cache": {                      # the c2735cf shape, verbatim
            "groq120|openai/gpt-oss-120b|ask": {
                "calls": 40, "reported": 40,
                "prompt_tokens": 80_000, "cached_tokens": 76_000}},
    }))
    _install_model(monkeypatch, [_usage(2363, cached=2304)] + [_usage(2363) for _ in range(6)])
    for _ in range(7):
        _chat()
    e = llm_stats.range_summary(3)["aggregate"]["prefix_cache"]["ask"]
    assert e["cached_tokens"] == 2304, (
        "the old row's 76,000 cached tokens must not enter the numerator when its "
        "prompt total cannot enter the denominator")
    assert e["calls"] == 7 and e["measurable"] == 7
    assert e["effective_pct"] == pytest.approx(13.9, abs=0.05)
    # NOT `hit_pct <= 100`: _rate() clamps, so that passes even with the old
    # row's 78,304 cached tokens in the numerator (true rate 3313%). The clamp
    # hides the symptom, so the assertion has to be on the sum and on the
    # explicit anomaly flag that exists because the clamp hides it.
    assert e["impossible"] is False, (
        "cached tokens must not exceed prompt tokens; if they do the accounting "
        "is broken and the clamp is the only reason the percentage looks sane")


def test_a_rate_is_clamped_and_a_negative_count_is_refused(stats_dir, monkeypatch):
    """BUG-6. The figures are the provider's; nothing upstream vouches for them."""
    # Negative counts never become a measurement in the first place.
    assert providers._prefix_usage(_usage(-5, cached=-1)) is None
    assert providers._prefix_usage(_usage(2000, cached=-1)) == (2000, None, True)
    # And an impossible overshoot is clamped rather than published.
    assert llm_stats._rate(5000, 2000, 1) == 100.0
    assert llm_stats._rate(0, 0, 1) is None
    assert llm_stats._rate(100, 200, 0) is None


def test_the_footnote_does_not_name_routes_that_do_not_exist(admin, stats_dir, monkeypatch):
    """BUG-1. The copy claimed five routes were excluded by the threshold.

    Two of them (`ask_matching`, `ask_numerology`) are PROMPT OVERLAYS on the
    `ask` route, not routes -- nothing ever passes them to providers.chat, so no
    such row can appear. The other three were compared as system-prompt tokens
    against a threshold applied to the whole request, which they clear.
    """
    _install_model(monkeypatch, [_usage(2363, cached=2304)])
    _chat()
    html = admin.get("/admin").text
    for ghost in ("ask_matching</code>", "ask_numerology</code>"):
        assert ghost not in html, f"{ghost} is a prompt overlay, not a chat route"
    assert "a dash or about 0" not in html
    assert "system + question or chart" in html, (
        "the threshold is judged on the whole request; saying so is what stops the "
        "next reader repeating the system-prompt-only mistake")


def test_effective_is_disclosed_as_a_share_of_measurable_not_of_traffic(
        admin, stats_dir, monkeypatch):
    """BUG-9. 'The quota actually saved' is a saving over MEASURABLE calls."""
    _install_model(monkeypatch, [_usage(2363, cached=2304)])
    _chat()
    html = admin.get("/admin").text
    assert "not over Fresh calls" in html


# The routes that actually reach providers.chat and can therefore appear as a
# prefix_cache row. `rashifal` and `dasha_deep_dive` are also passed as `route=`
# but only to the WEB cache (routes/subscribe.py, routes/dasha.py), so naming
# either in the prefix-cache copy is the same defect as naming a prompt overlay:
# a row that can never appear. Deriving this set from `route="..."` across src/
# yields a SUPERSET and lets exactly that mistake through.
#: `outlook` left this set in #473. `generate_outlook_reading` serves BOTH
#: /monthly and /yearly and used to label every call "outlook", so one provider
#: route stood for two cached features and its measured tokens could be
#: attributed to neither. It now takes the caller's `active_page`, so the names
#: here are "monthly" and "yearly" -- which is also why the default argument
#: `route: str = "outlook"` is not a `route="..."` literal and no longer
#: appears to this scan.
CHAT_ROUTES = frozenset({
    "natal", "ask", "matching", "rashifal_single", "today", "dasha",
    "monthly", "yearly"})


def test_every_route_name_in_the_footnote_is_a_real_chat_route():
    """BUG-1 statically, hardened twice.

    Round 2 found the first version derived its route set from `route="..."`
    across src/, which is a SUPERSET -- `rashifal` and `dasha_deep_dive` are
    web-cache routes that never reach providers.chat, so naming either was the
    same never-appears defect and stayed green.

    Round 3 found five more holes in the second version: a plain-text name off a
    hard-coded four-item list, ANY capitalisation (the regex was lower-case
    only), and anything outside one `<p>` slice -- including the column tooltips
    that a sibling test treats as part of the same copy. It also rejected
    `rashifal_single`, a REAL chat route, because `rashifal` is a prefix of it.

    So: the whole prefix-cache block, case-insensitively, word-boundary matched,
    derived from CHAT_ROUTES rather than a denylist.
    """
    import pathlib as _pl
    src = _pl.Path(__file__).resolve().parents[1] / "src" / "astro_ai"
    code = "\n".join(q.read_text() for q in src.rglob("*.py"))
    declared = set(re.findall(r'route="([A-Za-z_0-9]+)"', code))
    # #473: `generate_outlook_reading` takes its route from the caller, so
    # "monthly" and "yearly" are never `route="..."` literals. Imported rather
    # than re-listed here -- a second copy of a route list is how the first
    # version of this test went stale.
    from astro_ai.llm import OUTLOOK_ROUTES
    declared |= set(OUTLOOK_ROUTES)
    assert CHAT_ROUTES <= declared, (
        f"CHAT_ROUTES names {CHAT_ROUTES - declared}, which no longer appears in "
        "src/ -- update the set rather than deleting the check")

    tmpl = (src / "templates" / "admin_dashboard.html").read_text()
    # The WHOLE prefix-cache section, not one paragraph: the header tooltips are
    # copy too, and a name hidden in one was invisible to the old slice.
    start = tmpl.index("PROVIDER-SIDE PREFIX CACHE")
    # To the END of the footnote paragraph. NOT to the first `{% endif %}` after
    # "Two different caches": the footnote now opens with two conditional notices,
    # so that landed BEFORE the prose and silently excluded it -- which is how a
    # first version of this very assertion covered nothing.
    block = tmpl[start:tmpl.index("</p>", tmpl.index("Two different caches"))]
    assert "A call is Measurable" in block and "Measurable</th>" in block, (
        "the slice must span the column tooltips AND the whole footnote; if either "
        "anchor moves, this test is checking a window with nothing in it")

    # Every route-shaped token, however wrapped and however capitalised.
    MODELS = {"gpt-oss-120b", "gpt-oss-20b", "gpt-oss-safeguard-20b"}
    NOT_ROUTES = {"usage"}   # an API FIELD name the copy cites; never a route
    named = {m.lower() for m in re.findall(r"<code>([A-Za-z_0-9.\-]+)</code>", block)}
    assert named - MODELS - NOT_ROUTES <= CHAT_ROUTES, (
        f"the prefix-cache copy names {sorted(named - MODELS - NOT_ROUTES - CHAT_ROUTES)} "
        "in a <code> span, which cannot appear as a prefix_cache row")

    # And unwrapped: any non-chat route name anywhere in the block, whole-word and
    # case-insensitive. `\b` is what stops `rashifal` matching `rashifal_single`
    # (underscore is a word character, so the boundary does not fire mid-token).
    # "monthly" left this list in #473 and is now a CHAT route: it used to be a
    # web-cache route only, because every /monthly and /yearly call reached
    # providers.chat labelled "outlook". Threading the feature name through is
    # what made its tokens attributable, and it is what moves it across this
    # line. "yearly" was never listed, so it needs no removal -- which is worth
    # noticing: the pair was already asymmetric here.
    ghosts = (declared - CHAT_ROUTES) | {"ask_matching", "ask_numerology", "panchang"}
    for ghost in sorted(ghosts):
        assert not re.search(rf"\b{re.escape(ghost)}\b", block, re.IGNORECASE), (
            f"{ghost!r} is a prompt overlay, a prompt file or a web-cache route, so it "
            "can never appear as a prefix_cache row; naming it is the BUG-1 defect")

    # The guard above must not reject a legitimate route (round 3, BUG-11).
    assert "rashifal_single" not in ghosts
    for real in sorted(CHAT_ROUTES):
        assert real not in ghosts, f"{real} is a chat route and must not be denied"


# [50,100,127] pin the 128-floor variant of the bug and [714,1023] the 1024-floor
# variant. 2363 is the live-measured request size: it cannot fail under any floor
# in play, and is kept as documentation of the real call, not as a guard (QA r3).
# 128 is included so SYMMETRY is pinned at the boundary too, but note what this
# test can and cannot see: it asserts a hit and a miss of the same size AGREE,
# and flipping `>=` to `>` moves both together, so they still agree. Adding 128
# here does NOT pin the comparison -- that needs
# `test_a_prompt_exactly_at_the_floor_is_measurable` below, which asserts the
# value rather than the symmetry. QA round 4 reported the flip surviving the
# suite; my first response was to add 128 here, which did not kill it either.
@pytest.mark.parametrize("size", [50, 100, 127, 128, 714, 1023, 2363])
def test_measurability_never_depends_on_the_outcome_at_any_size(
        size, stats_dir, monkeypatch):
    """BUG-3, round 2. The asymmetry must be STRUCTURALLY absent, not just rare.

    Round 1 found a hit at 714 measurable while a miss at 714 was not. Round 2
    showed that lowering the floor to 128 only moved the band to [0,128): a hit
    below it was still measurable, and the claim that such a hit "cannot occur"
    was an assumption about Groq rather than a property of this code --
    CACHE_REPORTING_MODELS matches the model STRING, with no provider check, and
    `_legacy_provider` reads both the base URL and the model from the environment.

    So this is parametrised across the floor instead of asserting at one size: at
    EVERY size, a hit and a miss of that size on the same model must agree about
    measurability. Nothing about the outcome may change the denominator.
    """
    _install_model(monkeypatch, [_usage(size, cached=size // 2)])
    _chat()
    hit = _agg()
    # Fresh day-file so the two cases cannot pollute each other.
    for f in stats_dir.glob("*.json"):
        f.unlink()
    _install_model(monkeypatch, [_usage(size)])
    _chat()
    miss = _agg()
    assert hit["measurable"] == miss["measurable"], (
        f"at {size} tokens a hit and a miss disagree about measurability "
        f"(hit={hit['measurable']}, miss={miss['measurable']}): the denominator "
        "is selecting on the outcome, which is BUG-3 at a different size")



def test_a_sub_floor_report_is_counted_so_the_floor_is_falsifiable(
        stats_dir, monkeypatch):
    """BUG-3, round 2. Whether gpt-oss-20b's real floor is under 1024 could not be
    settled without live Groq calls. Production can settle it for free: a figure
    reported below our floor means the floor is too high, and the counter says so.
    """
    _install_model(monkeypatch, [_usage(100, cached=96)], model="openai/gpt-oss-20b")
    _chat()
    e = _agg()
    assert e["reported_unmeasurable"] == 1
    assert e["measurable"] == 0 and e["effective_pct"] is None


def test_an_impossible_accounting_is_flagged_not_smoothed_to_100(stats_dir, monkeypatch):
    """NEW-6. The clamp hides the only evidence the sums are wrong.

    The old-schema aggregation bug was FOUND by seeing 571% and 3998% on the
    dashboard. Under a silent clamp it would have read a tidy 100.0%. So the
    clamp stays -- a nonsense percentage is not worth publishing -- but the fact
    that it bit is published beside it.
    """
    def row(**kw):
        return {**llm_stats._PREFIX_ZERO, "calls": 10, **kw}

    assert llm_stats._rate(5000, 2000, 1) == 100.0, "still clamped"
    # cached exceeding prompt, on either side
    assert llm_stats._is_impossible(row(
        cached_tokens=5000, cached_measurable=5000,
        prompt_reported=2000, prompt_measurable=2000)) is True
    assert llm_stats._is_impossible(row(cached_tokens=-1)) is True
    # pairs record() cannot produce (BUG-15)
    assert llm_stats._is_impossible(row(
        cached_tokens=90, cached_measurable=900,
        prompt_reported=100, prompt_measurable=10_000)) is True
    assert llm_stats._is_impossible(row(calls=1, measurable=2)) is True
    assert llm_stats._is_impossible(row(calls=1, reported=2)) is True
    # and the legitimate shapes stay clean
    assert llm_stats._is_impossible(row(
        cached_tokens=96, cached_measurable=96,
        prompt_reported=100, prompt_measurable=100)) is False
    assert llm_stats._is_impossible(row(
        cached_tokens=100, cached_measurable=100,
        prompt_reported=100, prompt_measurable=100)) is False, "cached == prompt is legal"
    assert llm_stats._is_impossible(row(calls=0)) is False, "an all-zero row is not an anomaly"


def test_a_skipped_old_schema_row_is_logged_and_counted(stats_dir, monkeypatch, caplog):
    """NEW-5. The skip was silent, and the comment overstated the signal it gave.

    When the route also has current-schema days the row is not "missing" -- the
    only symptom was a silent gap between the By-route table and Fresh calls.
    """
    stats_dir.mkdir(parents=True, exist_ok=True)
    old = date.today() - timedelta(days=1)
    (stats_dir / f"{old.isoformat()}.json").write_text(json.dumps({
        "date": old.isoformat(), "counts": {"groq120|m|ask": 40},
        "totals": {"ask": 40}, "fallbacks": 0,
        "prefix_cache": {"groq120|openai/gpt-oss-120b|ask": {
            "calls": 40, "reported": 40,
            "prompt_tokens": 80_000, "cached_tokens": 76_000}},
    }))
    _install_model(monkeypatch, [_usage(2363, cached=2304)])
    _chat()
    with caplog.at_level("WARNING"):
        agg = llm_stats.range_summary(3)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 1, (
        "the count is what explains the gap between By route and Fresh calls")
    assert "unrecognised shape" in caplog.text, (
        "a silently dropped row is a discrepancy nobody can explain")
    assert "prompt_tokens" in caplog.text, (
        "the log must name the fields it saw, or the next schema drift is a guess")
    assert agg["prefix_cache"]["ask"]["cached_tokens"] == 2304


def test_the_footnote_and_the_column_tooltip_agree_on_what_a_dash_means(
        admin, stats_dir, monkeypatch):
    """NEW-1, then QA round 6 (F-1, F-2). The tooltips used to ENUMERATE the
    causes of a dash (three of them) while the footnote listed four, so on the
    fourth the tooltip's whole list was false -- and this test only checked the
    footnote, never the tooltip it was named for. The tooltips now enumerate
    nothing and point at the footnote; this reads them off a row of EACH of the
    four causes and asserts the footnote lists those four."""
    _seed_four_dash_causes()
    html = admin.get("/admin").text
    assert "An Effective dash has four causes" in html
    assert "not a short prompt" not in html, (
        "that was the absolute claim the table's own tooltip contradicted")
    hit_tips, eff_tips = set(), set()
    for route in _FOUR_DASH_ROUTES:
        row = _row(html[html.index("Provider-side prefix cache (Groq)"):], route)
        titles = re.findall(r'<td\b[^>]*\btitle="([^"]*)"[^>]*>&mdash;</td>', row)
        assert len(titles) == 2, f"{route}: Hit rate and Effective should both be dashes with a tooltip"
        # Positional: the Hit-rate cell precedes the Effective cell in the row.
        hit_tips.add(titles[0])
        eff_tips.add(titles[1])
    assert len(hit_tips) == 1 and len(eff_tips) == 1, (
        f"a tooltip varies by row: {hit_tips} / {eff_tips}")
    (hit_tip,), (eff_tip,) = hit_tips, eff_tips
    assert hit_tip != eff_tip, (
        "ONE tooltip for both columns is the round-7 defect: they dash under "
        "different rules, so a shared text is false on one of them")
    for tip in (hit_tip, eff_tip):
        assert tip.startswith("Unmeasured, not 0%"), tip
    # Effective points at the footnote's four causes and names none of them, so it
    # cannot be false on a row of another cause.
    assert "lists the four causes" in eff_tip, eff_tip
    for cause in ("non-reporting", "minimum", "usage", "impossible"):
        assert cause not in eff_tip, (
            f"a tooltip that names a cause is false on a row of another cause: {eff_tip!r}")
    # Hit rate states its OWN rule and must not borrow Effective's count.
    assert "reported a cache figure" in hit_tip, hit_tip
    assert "four causes" not in hit_tip, (
        "Effective's four causes do not describe a Hit-rate dash -- round 7, N-1")


# One route per cause of a dash. Fresh calls is 3 on every one so that no count
# differs; the four rows must be indistinguishable in every column.
_FOUR_DASH_ROUTES = ("ask", "today", "natal", "monthly")


def _seed_four_dash_causes():
    for _ in range(3):
        # (1) a non-reporting model served every call
        llm_stats.record(provider="openai", model="gpt-4o", route="ask",
                         prompt_tokens=5000, cached_tokens=None)
        # (2) a reporting model, prompt under the minimum
        llm_stats.record(provider="groq120", model=CACHING_MODEL, route="today",
                         prompt_tokens=100, cached_tokens=None)
        # (3) a reporting model, no usable usage block
        llm_stats.record(provider="groq120", model=CACHING_MODEL, route="natal")
        # (4) every report was impossible and discarded
        llm_stats.record(provider="groq120", model=CACHING_MODEL, route="monthly",
                         prompt_tokens=1000, cached_tokens=None,
                         reported_impossible=True)


def test_all_four_dash_causes_render_identically_and_the_footnote_lists_them(
        admin, stats_dir):
    """QA round 6, F-1. The footnote said "The Measurable column tells the first
    two apart from Fresh calls". Seeded, all four causes give Fresh 3,
    Measurable 0, Reported 0 and dashes: NO column separates them, which is why
    the footnote tells the operator to check, and why that sentence is gone.
    Each of the four causes is also named in the footnote (an unguarded deletion
    of one, 'no usable usage block', survived round 6)."""
    _seed_four_dash_causes()
    html = admin.get("/admin").text
    for route in _FOUR_DASH_ROUTES:
        assert _pc_cells(html, route)[1:] == ["3", "0", "—", "0", "—", "—", "—"], route
    causes = _notice(html)
    causes = causes[causes.index("An Effective dash has four causes"):]
    for phrase in ("a non-reporting model served every call",
                   "the prompts were under the minimum",
                   "the provider returned no usable usage block at all",
                   "every report it sent was impossible and discarded"):
        assert phrase in causes, phrase


def test_sentences_that_no_test_could_pin_stay_deleted(admin, stats_dir):
    """QA round 6, F-1/F-3/F-4. Each of these was a claim the page made that no
    assertion could fail on: F-1's and F-3's were FALSE (seeded, no column
    separates the four dash causes; a route of only impossible reports gets a
    notice that does not say the fourth cause happened), the rest are facts
    about Groq or about prompt sizes that nothing in this tree ties the page to
    (the 732 figure is scripts/verify_token_budget.py's, not the page's). A
    sentence that cannot fail a test is deleted, not reworded."""
    _seed_four_dash_causes()
    _seed_both_causes()
    html = admin.get("/admin").text
    text = _notice(html)
    for gone in ("Measurable column tells",
                 "the notice above says so when that has happened",
                 "732", "should not happen",
                 "survives our cold starts", "2 hours"):
        assert gone not in text, f"{gone!r} is back in the footnote"


def test_a_reporting_model_with_no_usage_block_is_unmeasured(stats_dir, monkeypatch):
    """NEW-1, the third cause of a dash, on a fully cache-reporting model."""
    _install_model(monkeypatch, [None])
    _chat()
    e = _agg()
    assert e["calls"] == 1 and e["measurable"] == 0 and e["reported"] == 0
    assert e["effective_pct"] is None and e["hit_pct"] is None


def test_a_sub_floor_report_does_not_inflate_the_effective_numerator(
        stats_dir, monkeypatch):
    """The >100% guard in the separate-numerator design, on a MIXED window.

    One measurable miss plus one sub-floor hit. If effective_pct used the shared
    `cached_tokens` instead of `cached_measurable`, the sub-floor hit's cached
    tokens would land in the effective numerator while its prompt tokens stayed
    out of the effective denominator -- the exact overshoot the old disjunct was
    bolted on to prevent, and the reason that disjunct made measurability depend
    on the outcome.
    """
    short = llm_stats.MIN_CACHEABLE_PREFIX - 1
    _install_model(monkeypatch, [_usage(2000), _usage(short, cached=short)])
    _chat(); _chat()
    e = _agg()
    assert e["measurable"] == 1 and e["prompt_measurable"] == 2000
    assert e["cached_tokens"] == short, "the hit is real data and feeds hit_pct"
    assert e["cached_measurable"] == 0, "but not the effective numerator"
    assert e["effective_pct"] == 0.0, (
        "one measurable call, a miss: the honest effective rate is 0%, not "
        f"{short}/2000 borrowed from a call that was never measurable")
    assert e["impossible"] is False


# --- QA round 3 findings -------------------------------------------------------

def test_a_cached_count_larger_than_its_prompt_is_refused_at_the_source():
    """BUG-9. "Neither rate can exceed 100% by construction" was ASSUMED.

    Round 3 found nothing enforced it: `_prefix_usage(prompt=100, cached=5000)`
    returned `(100, 5000)`, record() stored it, and the published 5000% was saved
    only by the display clamp -- a vendor assumption dressed as a property of the
    code, which is the error species round 2 condemned. Now enforced, so the
    claim is true of the code and the clamp is defence in depth.
    """
    assert providers._prefix_usage(_usage(100, cached=5000)) == (100, None, True)
    assert providers._prefix_usage(_usage(0, cached=900)) == (0, None, True)
    assert providers._prefix_usage(_usage(100, cached=100)) == (100, 100, False), "equal is legal"
    assert providers._prefix_usage(_usage(2363, cached=2304)) == (2363, 2304, False)
    # A true SILENCE is not a rejection, and the two must never be the same
    # value: Groq omits the field on a miss, which record() resolves from the
    # model. This is the pair round 4 found collapsed.
    assert providers._prefix_usage(_usage(1000)) == (1000, None, False)
    assert providers._prefix_usage(_usage(1000, cached=None)) == (1000, None, False)


def test_the_anomaly_flag_is_visible_when_only_the_reported_side_is_broken(
        stats_dir, monkeypatch, admin):
    """BUG-1. The glyph hung off the Effective cell, inside its `{% else %}`.

    So when the impossibility was on the REPORTED side and effective_pct was
    None, `impossible` was True and nothing rendered anywhere, while Hit rate
    showed a tidy clamped 100.0% -- the exact outcome the flag exists to prevent.
    It now hangs off the route cell, which always renders.
    """
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(),
        "counts": {"groq120|openai/gpt-oss-120b|ask": 7},
        "totals": {"ask": 7}, "fallbacks": 0,
        "prefix_cache": {"groq120|openai/gpt-oss-120b|ask": {
            **llm_stats._PREFIX_ZERO,
            "calls": 7, "reported": 7, "prompt_reported": 100, "cached_tokens": 5000}},
    }))
    e = llm_stats.range_summary(1)["aggregate"]["prefix_cache"]["ask"]
    assert e["impossible"] is True and e["effective_pct"] is None
    html = admin.get("/admin").text
    assert "&#9888;" in html or "⚠" in html, (
        "an impossible row must be flagged even when Effective is a dash")


def test_the_two_column_pairs_each_divide_to_their_own_rate(
        stats_dir, monkeypatch, admin):
    """BUG-2. The table showed `prompt_measurable` beside `cached_tokens`.

    Those come from different numerators, so the two adjacent columns divided to
    450% on screen with `impossible` False -- the split was made in the data and
    not carried into the table. Each pair must now be self-consistent.
    """
    _install_model(monkeypatch, [_usage(1000)])                    # measurable miss
    _chat()
    _install_model(monkeypatch, [_usage(5000, cached=4500)], model="gpt-4o")
    _chat()
    e = _agg()
    assert e["measurable"] == 1 and e["prompt_measurable"] == 1000
    assert e["cached_measurable"] == 0, "the gpt-4o hit is not measurable"
    assert e["cached_tokens"] == 4500 and e["prompt_reported"] == 5000
    assert e["effective_pct"] == 0.0 and e["hit_pct"] == 90.0
    html = admin.get("/admin").text
    assert "1000 / 0" in html, "the measurable pair must be shown together"
    assert "5000 / 4500" in html, "the reported pair must be shown together"


def test_the_unmeasurable_report_notice_names_the_benign_cause_and_forbids_the_harmful_fix(
        stats_dir, monkeypatch, admin):
    """BUG-4. The notice named two causes and prescribed a fix that reinstates v1.

    `reported_unmeasurable` also increments for the case the design EXISTS for --
    a non-Groq provider reporting its own cache, correctly excluded from
    Effective. Telling the operator to add that model to CACHE_REPORTING_MODELS
    would make its silences count as measured zeros under a Groq-derived floor.
    """
    _install_model(monkeypatch, [_usage(5000, cached=4500)], model="gpt-4o")
    _chat()
    assert _agg()["reported_unmeasurable"] == 1
    html = admin.get("/admin").text
    text = _notice(html)
    assert "non-Groq provider reporting its own cache" in text
    assert "Do not add a non-Groq model to the reporting set" in text


def test_a_malformed_stat_key_is_counted_and_logged_not_dropped_silently(
        stats_dir, monkeypatch, caplog):
    """BUG-13. `len(parts) != 3` was a silent `continue`.

    That is the branch EVERY stored row falls into if a segment is ever added to
    `stat_key`, so a whole window could vanish with nothing to show for it.
    """
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0,
        "prefix_cache": {"p|m|extra|route": dict(llm_stats._PREFIX_ZERO),
                         "p|m": dict(llm_stats._PREFIX_ZERO),
                         "justroute": dict(llm_stats._PREFIX_ZERO)},
    }))
    with caplog.at_level("WARNING"):
        agg = llm_stats.range_summary(1)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 3
    assert "not provider|model|route" in caplog.text


def test_the_skip_notice_survives_when_every_row_is_skipped(
        stats_dir, monkeypatch, admin):
    """BUG-12. The notice lived inside `{% if ...prefix_cache %}`.

    In the total-loss case the table does not render, so the notice vanished with
    it and the only trace was a server log nobody reads.
    """
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(), "counts": {"groq120|m|ask": 4},
        "totals": {"ask": 4}, "fallbacks": 0,
        "prefix_cache": {"groq120|m|ask": {
            "calls": 4, "reported": 3, "prompt_tokens": 80, "cached_tokens": 76}},
    }))
    agg = llm_stats.range_summary(1)["aggregate"]
    assert agg["prefix_cache"] == {} and agg["prefix_cache_skipped_rows"] == 1
    html = admin.get("/admin").text
    assert "stored row(s) were excluded as unreadable" in html, (
        "when every row is skipped the table is absent, so the notice must not be "
        "inside the table's own {% if %}")
    # The same clauses as the footnote's notice, in the total-loss variant
    # (QA round 5): both causes of a skip are named, and "every row" is the claim
    # that distinguishes this variant from the footnote's.
    import html as _html
    flat = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", html)))
    assert ("(written by an older schema, or keyed in a shape this page does not "
            "recognise) — which is every row in this window, so there is no table "
            "to show.") in flat
    assert "Widen the window" not in flat and "re-record" not in flat, (
        "advice with no test behind it (QA round 6, F-4)")


def test_the_skip_warning_is_not_emitted_once_per_row_per_request(
        stats_dir, monkeypatch, caplog):
    """BUG-18. 30 rows x a 30-day window logged ~900 lines on one page view."""
    stats_dir.mkdir(parents=True, exist_ok=True)
    bad = {"calls": 1, "reported": 1, "prompt_tokens": 10, "cached_tokens": 5}
    for d in range(3):
        day = date.today() - timedelta(days=d)
        (stats_dir / f"{day.isoformat()}.json").write_text(json.dumps({
            "date": day.isoformat(), "counts": {}, "totals": {}, "fallbacks": 0,
            "prefix_cache": {"groq120|m|ask": dict(bad)},
        }))
    with caplog.at_level("WARNING"):
        llm_stats.range_summary(5)
        llm_stats.range_summary(5)
    lines = [r for r in caplog.records if "unrecognised shape" in r.getMessage()]
    assert len(lines) == 1, (
        f"one key across 3 days and 2 calls logged {len(lines)} times; the dedup is "
        "what keeps a persistent old row from flooding every /admin load")


def test_the_by_route_table_still_has_its_own_headers():
    """Not a QA finding -- a bug I introduced while fixing BUG-2 and nothing caught.

    Editing "the Route table" by its first match rewrote the BY-ROUTE table's
    headers with the prefix-cache ones, so the page would have shipped a table
    labelled Measurable/Hit rate/Effective over cells holding response-cache hits
    and token estimates. There are two tables whose first column is Route.
    """
    import pathlib as _pl
    tmpl = (_pl.Path(__file__).resolve().parents[1]
            / "src" / "astro_ai" / "templates" / "admin_dashboard.html").read_text()
    by_route = tmpl[tmpl.index("By route</h3>"):tmpl.index("</tr>", tmpl.index("By route</h3>"))]
    for header in ("Response-cache hits", "Response-cache hit rate", "Avg miss",
                   "Input (est.)", "Output (est.)"):
        assert header in by_route, f"the By-route table lost its {header!r} header"
    for alien in ("Measurable", "Effective", "Msr prompt", "Rep prompt"):
        assert alien not in by_route, (
            f"{alien!r} belongs to the prefix-cache table; the By-route headers were "
            "overwritten and its cells no longer match its labels")


# --- QA round 4 findings -------------------------------------------------------
#
# Every finding below was introduced by round 3 -- the round that was fixing
# things -- except the two unpinned guards, which round 3 shipped without a
# test. Each test here was bite-tested against its own mutant AND checked that
# the mutant dies on THIS guard rather than on a neighbouring one: the #424 miss
# this week was a mutant caught by the wrong check, which leaves the intended
# one unpinned while the suite looks green.

def _seed(stats_dir, row, *, counts=None, route="ask",
          key="groq120|openai/gpt-oss-120b|ask"):
    """Write one day's blob with a chosen prefix_cache row."""
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(),
        "counts": counts if counts is not None else {key: row.get("calls", 0)},
        "totals": {route: row.get("calls", 0)}, "fallbacks": 0,
        "prefix_cache": {key: {**llm_stats._PREFIX_ZERO, **row}},
    }))
    return llm_stats.range_summary(1)["aggregate"]


# A coherent row in which calls != measurable != reported: 9 fresh calls, 7 of them
# measurable silences on a reporting model, 2 reports on calls the rule calls
# unmeasurable (so reported_unmeasurable == 2). Every clause of `_is_impossible`
# holds, so a test using it cannot pass or fail on the anomaly flag.
_GAP_ROW = {"calls": 9, "measurable": 7, "prompt_measurable": 7000,
            "reported": 2, "prompt_reported": 2000, "cached_tokens": 1000,
            "reported_unmeasurable": 2}


def _notice(html: str) -> str:
    """The prefix-cache footnote as the operator reads it: tags gone, entities
    decoded, whitespace collapsed. Asserting on raw HTML pins line breaks and
    `&ldquo;`, so a re-flowed paragraph read as a deleted claim (and a deleted
    claim could hide behind a re-flow)."""
    import html as _html
    start = html.index("Two different caches")
    para = html[start:html.index("</p>", start)]
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", para))).strip()


def _pc_cells(html: str, route: str) -> list[str]:
    """Cells of `route` in the PREFIX-CACHE table, not the By-route one above it
    (both have a row for most routes)."""
    import html as _html
    table = html[html.index("Provider-side prefix cache (Groq)"):]
    cells = re.findall(r"<td\b.*?</td>", _row(table, route), flags=re.S)
    return [_html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in cells]


def test_an_impossible_report_is_not_booked_as_a_measured_zero(stats_dir, monkeypatch):
    """BUG-2, round 4, introduced by round 3's fix for round 3's BUG-9.

    `_prefix_usage` rejects `cached > prompt` by returning a SILENCE, and on an
    eligible call `record()` books a silence as a measured zero. Measured before
    this fix:

        _prefix_usage(prompt=1000, cached=5000) -> (1000, None)
          -> {"reported": 0, "cached_tokens": 0, "effective_pct": 0.0,
              "reported_unmeasurable": 0, "impossible": false}

    No warning, no dash, and `reported_unmeasurable` -- the counter that exists
    to make the rule falsifiable -- stayed 0 because it is gated on
    `cached_tokens is not None`. A misreporting provider was indistinguishable
    from one that genuinely missed, and it dragged the published saving down.
    That is the thing the docstring shipped in the same diff forbids: "SMOOTHING
    an impossible figure into a plausible one is its own defect".

    The three cases must be mutually distinguishable, so all three are asserted
    together -- asserting only the impossible one would pass on a change that
    broke the genuine miss instead.
    """
    _install_model(monkeypatch, [_usage(1000, cached=5000)])   # impossible
    _chat()
    bad = _agg()
    assert bad["reported_unmeasurable"] == 1, "the rejection left no evidence"
    assert bad["measurable"] == 0, (
        "an impossible report entered the Effective denominator, so it reads as "
        "a measured zero")
    assert bad["effective_pct"] is None, (
        f"published {bad['effective_pct']}% off a report we threw away")

    # A GENUINE miss on the same model and size is still a measured zero, which
    # is correct and is the distinction that was lost.
    _install_model(monkeypatch, [_usage(1000)])
    _chat()
    good = _agg()
    assert good["measurable"] == 1 and good["reported_unmeasurable"] == 1
    assert good["effective_pct"] == 0.0, (
        "a real miss must still count as the zero it is, or the fix for the "
        "impossible case has thrown away the measurement it was protecting")


def test_the_measurable_side_of_the_impossibility_check_is_pinned(stats_dir):
    """BUG-3, round 4. Deleting the clause left 720 tests passing.

    `_is_impossible` has two published-ratio clauses. The reported-side twin was
    pinned; the measurable side -- the column the footnote tells the operator to
    read -- was not. The row below is impossible on the MEASURABLE side only, so
    the reported clause cannot fire and this isolates the one under test.
    """
    row = {"calls": 7, "measurable": 7, "reported": 7,
           "prompt_measurable": 100, "cached_measurable": 5000,
           "prompt_reported": 6000, "cached_tokens": 5000}
    agg = _seed(stats_dir, row)
    e = agg["prefix_cache"]["ask"]

    # THE FIXTURE MUST SATISFY EVERY OTHER CLAUSE, or deleting the target one
    # leaves a neighbour firing and the test passes for the wrong reason. My
    # first version set cached_tokens=0, which tripped
    # `cached_measurable > cached_tokens` as well -- the clause under test could
    # be deleted and this still read True. The bite harness caught it; the suite
    # did not, because a suite only ever asks whether SOMETHING went red.
    assert e["cached_tokens"] <= e["prompt_reported"]        # reported ratio ok
    assert e["cached_measurable"] <= e["cached_tokens"]      # subset ok
    assert e["measurable"] <= e["calls"] and e["reported"] <= e["calls"]
    assert e["cached_tokens"] >= 0 and e["cached_measurable"] >= 0
    assert e["cached_measurable"] > e["prompt_measurable"]   # the one clause left

    assert e["impossible"] is True, (
        "cached_measurable 5000 > prompt_measurable 100 is not a cache, and it "
        "is the only clause this row violates")


def test_the_impossible_tooltip_says_the_row_is_untrustworthy(admin, stats_dir):
    """BUG-4, round 4. Rewriting the warning to "All good here." stayed green.

    The glyph was asserted; its text was not, so the one sentence that tells an
    operator what the glyph MEANS could say anything.
    """
    _seed(stats_dir, {"calls": 7, "reported": 7,
                      "prompt_reported": 100, "cached_tokens": 5000})
    html = admin.get("/admin").text
    assert "&#9888;" in html or "⚠" in html
    assert "clamped and untrustworthy" in html, (
        "the glyph renders with no statement that the row cannot be trusted")


def test_the_effective_fraction_is_guarded_on_measurable_not_reported(admin, stats_dir):
    """BUG-4, round 4. `{% if pc.measurable %}` -> `{% if pc.reported %}` stayed green.

    The mutant breaks the most common production shape -- a reporting model where
    every call missed -- by rendering a dash in the fraction cell beside a real
    `Effective 0.0%`: a percentage with its own numerator and denominator hidden.

    So the fixture is exactly that shape: measurable > 0, reported == 0.
    """
    _seed(stats_dir, {"calls": 7, "measurable": 7, "prompt_measurable": 7000})
    e = llm_stats.range_summary(1)["aggregate"]["prefix_cache"]["ask"]
    assert e["measurable"] == 7 and e["reported"] == 0, "fixture shape drifted"
    assert e["effective_pct"] == 0.0, "a measurable all-miss route reads 0%, not a dash"
    row = _row(admin.get("/admin").text, "ask")
    assert "7000 / 0" in row, (
        "Effective reads 0.0% while its own fraction renders a dash — the "
        "numerator and denominator behind the published percentage are hidden")


def test_the_gap_against_by_route_is_counted_not_explained_away(admin, stats_dir):
    """BUG-1, round 4, introduced by round 3.

    Round 3 shipped: "Do not read that against 'By route' above: that table is
    keyed by web route and this one by chat route, so the two never match
    anyway." Both lists are the third segment of `provider|model|route` -- the
    same vocabulary -- so the claim is false, and it was the panel's only
    guidance about a mismatch: it told the operator that a measured 400-call
    discrepancy six rows up in the same card was expected and meaningless.

    The fixture is the real shape: a day with 409 calls in `counts` and a
    prefix_cache row for only 9 of them, which is what a window spanning the
    #396 deploy looks like. `skipped_rows` stays 0, so neither pre-existing
    notice fires -- that is why the gap needed its own number.

    `calls` (9) and `measurable` (7) DIFFER on purpose (QA round 5, G-2). The
    gap is by_route minus `calls`; with both at 7 a computation that subtracted
    `measurable` instead rendered the same 400 and this test could not tell.
    Now it would render 402.
    """
    key = "groq120|openai/gpt-oss-120b|ask"
    agg = _seed(stats_dir, _GAP_ROW, counts={key: 409})
    assert agg["prefix_cache_skipped_rows"] == 0, (
        "the fixture must not trip the schema notice, or it cannot show that "
        "the gap was previously undisclosed")
    e = agg["prefix_cache"]["ask"]
    assert (e["calls"], e["measurable"]) == (9, 7), "fixture shape drifted"
    assert agg["prefix_cache_unaccounted"] == {"ask": 400}, (
        "409 in By route minus 9 CALLS is 400; minus 7 measurable would be 402")
    text = _notice(admin.get("/admin").text)
    assert "400 call(s) in “By route” above are not counted in Fresh calls here" in text, (
        "the exact 400-call gap is not stated anywhere on the page")
    assert "402 call(s)" not in text, "the gap was computed from `measurable`, not `calls`"
    assert "never match anyway" not in text, (
        "the false caveat is back: the two lists ARE keyed the same way")


def test_no_gap_is_claimed_when_the_two_lists_agree(admin, stats_dir):
    """The disclosure must mean something, so it must be absent when exact."""
    key = "groq120|openai/gpt-oss-120b|ask"
    agg = _seed(stats_dir, _GAP_ROW, counts={key: 9})
    assert agg["prefix_cache_unaccounted"] == {}
    assert "not counted in Fresh calls here" not in _notice(admin.get("/admin").text)

def test_a_prompt_exactly_at_the_floor_is_measurable(stats_dir, monkeypatch):
    """BUG-5, round 4. `>=` -> `>` left the whole suite green.

    The parametrize list that was meant to cover this ran
    [50, 100, 127, 714, 1023, 2363]: every value is strictly below or strictly
    above 128, so the only value that distinguishes the two comparisons was
    never driven. Round 3 reviewed that list and added nothing at the boundary.

    Adding 128 to it is not enough either, and that is worth recording: that
    test asserts a hit and a miss of the same size AGREE about measurability,
    and flipping the comparison moves both together, so they go on agreeing.
    A boundary needs a test that asserts the VALUE, not the symmetry.

    Both sides of the edge, because asserting only `== MIN` would pass on a
    rule that measured everything.
    """
    _install_model(monkeypatch, [_usage(llm_stats.MIN_CACHEABLE_PREFIX)])
    _chat()
    assert _agg()["measurable"] == 1, (
        f"a prompt of exactly {llm_stats.MIN_CACHEABLE_PREFIX} tokens is at the "
        "floor and must be measurable; `>` instead of `>=` excludes it")

    for f in stats_dir.glob("*.json"):
        f.unlink()
    _install_model(monkeypatch, [_usage(llm_stats.MIN_CACHEABLE_PREFIX - 1)])
    _chat()
    assert _agg()["measurable"] == 0, (
        "one token under the floor must not be measurable, or the floor is not "
        "a floor")


# --- QA round 5 ----------------------------------------------------------------
#
# S-1 and S-2 were FALSE SENTENCES on a page that contradicted itself on one
# screen:
#
#   S-1  the `reported_unmeasurable` notice told the operator a misreporting
#        provider "needs no action" and that "its figure counts toward Hit
#        rate". For an IMPOSSIBLE report both are false -- `record()` discards
#        the figure (reported stays 0) and Hit rate renders a dash six columns
#        to the left of the sentence. The counter holds TWO populations (a real
#        report on an unmeasurable call; an impossible report) and cannot tell
#        them apart WITHOUT a ninth `_PREFIX_ZERO` key (issue #431), so the copy
#        states both and each clause must be true of the case it names.
#   S-2  the gap sentence said the unaccounted calls "count toward Fresh calls
#        above" -- the opposite of its definition (`by_route - pc.calls`) -- and
#        said routes with a schema-skipped row have "no prefix-cache row" when
#        the row exists and was excluded.
#
# The guards below hold EVERY factual clause of that notice area to the rendered
# page: a seeded dashboard, the real route, and for each claim both the sentence
# and the table cell it is about. A sentence-only assert passes when the data
# changes under it; a cell-only assert passes when the sentence is rewritten to
# say the opposite -- which is exactly what shipped.

def _seed_both_causes(monkeypatch=None):
    """2 genuine reports on a non-Groq model (route `ask`) and 3 impossible ones
    on a Groq model (route `today`) -- distinct counts so a wrong sum or a
    swapped route cannot hide behind symmetry.

    Through `record()`, the function `chat()` calls with the 3-tuple
    `_prefix_usage` returns: routes other than `ask` fail the quality gate on the
    fake provider's canned text, and the real-path half is already driven by
    test_an_impossible_report_is_not_booked_as_a_measured_zero."""
    for _ in range(2):
        llm_stats.record(provider="openai", model="gpt-4o", route="ask",
                         prompt_tokens=5000, cached_tokens=4500)
    for _ in range(3):
        llm_stats.record(provider="groq120", model=CACHING_MODEL, route="today",
                         prompt_tokens=1000, cached_tokens=None,
                         reported_impossible=True)


def _by_route_counts(html: str) -> dict[str, int]:
    """The llm_stats card's "By route" list (a <ul>), which the gap sentence calls
    "By route above". NOT the response-cache table that shares the heading."""
    start = html.index('mb-2">By route</div>')
    ul = html[start:html.index("</ul>", start)]
    return {r: int(n) for r, n in re.findall(
        r'<span class="text-bhagya-ink-soft">(.*?)</span>\s*<span[^>]*>(\d+)</span>', ul)}


def test_the_unmeasurable_notice_sums_both_causes_into_its_count(
        admin, stats_dir, monkeypatch):
    _seed_both_causes()
    ru = sum(v["reported_unmeasurable"] for v in
             llm_stats.range_summary(1)["aggregate"]["prefix_cache"].values())
    assert ru == 5, "fixture shape drifted: 2 genuine + 3 impossible"
    assert "5 call(s) carried a cache report that Effective leaves out" in _notice(
        admin.get("/admin").text), (
        "the count is the sum over routes of BOTH populations")
    # "The counter cannot tell its two causes apart" is true BECAUSE of the sum
    # above: one counter, fed by both populations (2 + 3). Round 6 mutated it to
    # "tells" and nothing failed.
    assert "The counter cannot tell its two causes apart" in _notice(
        admin.get("/admin").text)


def test_a_genuine_unmeasurable_report_is_in_hit_rate_and_out_of_effective_as_the_notice_says(
        admin, stats_dir, monkeypatch):
    """Cause (1). The notice says: counted in Reported and in Hit rate, kept out
    of Effective, needs no action."""
    _seed_both_causes()
    html = admin.get("/admin").text
    cells = _pc_cells(html, "ask")
    # Fresh, Measurable, Msr pair, Reported, Rep pair, Hit rate, Effective
    assert cells[1:] == ["2", "0", "—", "2", "10000 / 9000", "90.0%", "—"], (
        f"the row the (1) clause describes changed: {cells}")
    text = _notice(html)
    assert "that figure is counted in Reported and in Hit rate" in text
    assert "is rightly kept out of Effective" in text


def test_an_impossible_report_is_in_neither_rate_and_not_harmless_as_the_notice_says(
        admin, stats_dir, monkeypatch):
    """Cause (2), S-1. The notice used to say this case "needs no action" and
    "counts toward Hit rate" while the row beside it rendered a dash."""
    _seed_both_causes()
    html = admin.get("/admin").text
    cells = _pc_cells(html, "today")
    assert cells[1:] == ["3", "0", "—", "0", "—", "—", "—"], (
        "three impossible reports must leave Reported 0 and both rates a dash, "
        f"which is what the (2) clause promises: {cells}")
    text = _notice(html)
    cause2 = text[text.index("(2) An impossible report."):]
    assert "in neither Hit rate nor Effective" in cause2
    assert "not in Reported or Measurable, only in Fresh calls" in cause2
    assert "does need attention" in cause2
    # The two harmless-sounding claims are about cause (1) ONLY.
    assert "needs no action" not in cause2, (
        "an impossible report was described as needing no action")
    assert "counts toward Hit rate" not in text and "counted in Hit rate" not in cause2, (
        "an impossible report was described as counted in Hit rate")
    assert "needs no action" in text[:text.index("(2) An impossible report.")], (
        "cause (1) lost the reassurance that is true of it")


def test_a_route_of_only_impossible_reports_shows_a_dash_in_both_rates_as_the_notice_says(
        admin, stats_dir, monkeypatch):
    """The notice's last clause about cause (2): "a route whose only reports were
    of this kind shows a dash in both rates"."""
    for _ in range(2):
        llm_stats.record(provider="groq120", model=CACHING_MODEL, route="today",
                         prompt_tokens=1000, cached_tokens=None, reported_impossible=True)
    html = admin.get("/admin").text
    e = llm_stats.range_summary(1)["aggregate"]["prefix_cache"]["today"]
    assert e["hit_pct"] is None and e["effective_pct"] is None
    assert _pc_cells(html, "today")[-2:] == ["—", "—"]
    assert "a route whose only reports were of this kind shows a dash in both rates" in _notice(html)


def test_the_impossible_report_clause_names_exactly_what_the_code_rejects(
        admin, stats_dir):
    """QA round 6, F-4. Cause (2) says an impossible report is "more cached
    tokens than the prompt it came from, or a count that was not a non-negative
    whole number". Round 6 mutated "more" to "fewer" and deleted the second
    half; nothing failed. The sentence is now tied to what the code rejects."""
    for cached in (101, -1, 1.5, "5", True):
        assert providers._prefix_usage(_usage(100, cached=cached)) == (100, None, True), cached
    for cached in (0, 100):
        assert providers._prefix_usage(_usage(100, cached=cached)) == (100, cached, False), cached
    _seed_both_causes()
    assert ("The provider claimed more cached tokens than the prompt it came from, "
            "or a count that was not a non-negative whole number.") in _notice(
        admin.get("/admin").text)


def test_the_floor_the_notice_names_is_the_floor_the_code_applies(
        admin, stats_dir, monkeypatch):
    """"the 128-token floor" and "at least 128 prompt tokens" are numbers the page
    states about the code; they must follow MIN_CACHEABLE_PREFIX."""
    _seed_both_causes()
    text = _notice(admin.get("/admin").text)
    n = llm_stats.MIN_CACHEABLE_PREFIX
    assert f"the {n}-token floor is too high for a Groq model" in text
    assert f"with at least {n} prompt tokens" in text


def test_the_footnote_count_of_cache_reporting_models_is_the_set_size(
        admin, stats_dir, monkeypatch):
    """"one of the three cache-reporting models": the set holds six model STRINGS
    (each of three models with and without the `openai/` prefix)."""
    _seed_both_causes()
    models = {m.rsplit("/", 1)[-1] for m in llm_stats.CACHE_REPORTING_MODELS}
    assert len(models) == 3, "the set changed; the footnote's 'three' is now wrong"
    assert "one of the three cache-reporting models" in _notice(admin.get("/admin").text)


def test_the_dash_causes_are_counted_and_the_fourth_is_the_impossible_report(
        admin, stats_dir, monkeypatch):
    """The sentence said "three causes" after round 4 added a fourth: a route
    whose every report was discarded shows a dash in both rates (see the `today`
    row below) and none of the three listed causes describes it."""
    _seed_both_causes()
    html = admin.get("/admin").text
    assert _pc_cells(html, "today")[-2:] == ["—", "—"]
    text = _notice(html)
    causes = text[text.index("An Effective dash has four causes"):]
    assert "every report it sent was impossible and discarded" in causes
    assert "three causes" not in text


def test_the_excluded_rows_notice_counts_rows_and_names_both_causes_and_the_calls_are_missing(
        admin, stats_dir):
    """"N stored row(s) were excluded as unreadable (older schema, or a key shape
    the page does not recognise), so their calls are missing from this table."

    The old copy said only "written by an older schema", which is false for a
    malformed key -- the other branch that increments `skipped_rows`. Two rows,
    one of each, on routes the current-schema row does not cover, so the count
    (2) and the missing rows are both observable.
    """
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    good_key = "groq120|openai/gpt-oss-120b|ask"
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(),
        "counts": {good_key: 9, "groq120|openai/gpt-oss-120b|today": 5,
                   "groq120|openai/gpt-oss-120b|natal": 4},
        "totals": {"ask": 9, "today": 5, "natal": 4}, "fallbacks": 0,
        "prefix_cache": {
            good_key: {**llm_stats._PREFIX_ZERO, **_GAP_ROW},
            # older schema: `prompt_tokens`, no `prompt_measurable`
            "groq120|openai/gpt-oss-120b|today": {
                "calls": 5, "reported": 5, "prompt_tokens": 50, "cached_tokens": 40},
            # a key shape with a fourth segment
            "groq120|openai/gpt-oss-120b|natal|extra": dict(llm_stats._PREFIX_ZERO),
        },
    }))
    agg = llm_stats.range_summary(1)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 2
    html = admin.get("/admin").text
    text = _notice(html)
    assert ("2 stored row(s) were excluded as unreadable (written by an older "
            "schema, or keyed in a shape this page does not recognise), so their "
            "calls are missing from this table") in text
    for skipped_only in ("today", "natal"):
        with pytest.raises(AssertionError):
            _pc_cells(html, skipped_only)      # "missing from this table", literally


def test_the_gap_sentence_says_the_unaccounted_calls_are_not_in_fresh_calls(
        admin, stats_dir):
    """S-2. The sentence said these calls "count toward Fresh calls above" while
    `prefix_cache_unaccounted` is DEFINED as by_route minus the Fresh calls cell.
    Tie the sentence to the cell: By route 409, Fresh calls 9, gap 400."""
    key = "groq120|openai/gpt-oss-120b|ask"
    _seed(stats_dir, _GAP_ROW, counts={key: 409})
    html = admin.get("/admin").text
    assert _pc_cells(html, "ask")[1] == "9", "Fresh calls is the row's `calls`"
    assert _by_route_counts(html)["ask"] == 409, (
        "By route no longer carries the 409 the gap is measured against")
    text = _notice(html)
    assert "are not counted in Fresh calls here" in text
    assert "count toward Fresh calls" not in text, (
        "the gap sentence claims the unaccounted calls ARE in Fresh calls, the "
        "opposite of how the gap is defined")


def test_the_gap_lists_every_route_with_its_own_count_and_sums_them(
        admin, stats_dir):
    """"(ask 400 · today 3)": per-route numbers, and the headline is their sum."""
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    ask, td = "groq120|openai/gpt-oss-120b|ask", "groq120|openai/gpt-oss-120b|today"
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(), "counts": {ask: 409, td: 3},
        "totals": {"ask": 409, "today": 3}, "fallbacks": 0,
        "prefix_cache": {ask: {**llm_stats._PREFIX_ZERO, **_GAP_ROW}},
    }))
    text = _notice(admin.get("/admin").text)
    assert "403 call(s) in “By route” above are not counted in Fresh calls here (ask 400 · today 3)" in text


def test_the_gap_names_both_causes_and_a_skipped_row_really_does_widen_it(
        admin, stats_dir):
    """S-2, second half. The sentence said routes with a schema-skipped row have
    "no prefix-cache row here". The row exists and was EXCLUDED, and its calls
    are in the gap. Both halves of that are asserted: the data, then the words."""
    stats_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    td = "groq120|openai/gpt-oss-120b|today"
    (stats_dir / f"{today.isoformat()}.json").write_text(json.dumps({
        "date": today.isoformat(), "counts": {td: 3}, "totals": {"today": 3},
        "fallbacks": 0,
        "prefix_cache": {td: {"calls": 3, "reported": 1, "prompt_tokens": 9,
                              "cached_tokens": 1}},          # older schema
    }))
    agg = llm_stats.range_summary(1)["aggregate"]
    assert agg["prefix_cache_skipped_rows"] == 1
    assert agg["prefix_cache_unaccounted"] == {"today": 3}, (
        "a skipped row's calls are in By route and not in the table, so they ARE the gap")
    # No current-schema row at all -> the table is absent and the total-loss
    # notice carries the explanation; add one so the footnote (and the gap) render.
    _seed_alongside(stats_dir, td)
    text = _notice(admin.get("/admin").text)
    assert "days recorded before this panel existed, which carry no cache figure at all" in text
    assert ("and the stored rows excluded as unreadable (counted above when there are "
            "any), whose calls “By route” still counts") in text
    assert "no prefix-cache row" not in text, "a skipped row does exist; it was excluded"
    # Days before the panel existed are ABSENT from the table, not scored as a
    # zero -- the older-day test below shows them in the gap and in no row.
    assert "and so are absent rather than zero" in text


def _seed_alongside(stats_dir, skipped_key):
    """Add a readable current-schema `ask` row to today's blob, keeping the
    skipped one, so the footnote renders."""
    p = stats_dir / f"{date.today().isoformat()}.json"
    blob = json.loads(p.read_text())
    ask = "groq120|openai/gpt-oss-120b|ask"
    blob["counts"][ask] = 9
    blob["totals"]["ask"] = 9
    blob["prefix_cache"][ask] = {**llm_stats._PREFIX_ZERO, **_GAP_ROW}
    p.write_text(json.dumps(blob))


def test_both_lists_are_keyed_on_the_same_route_as_the_gap_sentence_claims(
        admin, stats_dir):
    """"The two lists are keyed the same way -- both on the chat route". The
    claim is checked by finding the SAME label in both tables."""
    key = "groq120|openai/gpt-oss-120b|ask"
    _seed(stats_dir, _GAP_ROW, counts={key: 409})
    html = admin.get("/admin").text
    assert "ask" in _by_route_counts(html) and _pc_cells(html, "ask"), (
        "By route and the prefix-cache table no longer share a route label")
    assert "both on the chat route" in _notice(html)
    assert "web route" not in _notice(html), (
        "the false vocabulary-mismatch caveat is back")


def test_the_part_of_the_gap_owed_to_older_days_does_shrink_as_they_age_out(
        stats_dir):
    """"The part owed to older days shrinks as they age out of the window." True
    only if the gap is computed over the requested window. A pre-#396 day two
    days back (counts, no prefix_cache) is in a 3-day gap and not in a 1-day one."""
    stats_dir.mkdir(parents=True, exist_ok=True)
    key = "groq120|openai/gpt-oss-120b|ask"
    for back, with_pc in ((0, True), (2, False)):
        day = date.today() - timedelta(days=back)
        blob = {"date": day.isoformat(), "counts": {key: 9}, "totals": {"ask": 9},
                "fallbacks": 0}
        if with_pc:
            blob["prefix_cache"] = {key: {**llm_stats._PREFIX_ZERO, **_GAP_ROW}}
        (stats_dir / f"{day.isoformat()}.json").write_text(json.dumps(blob))
    assert llm_stats.range_summary(1)["aggregate"]["prefix_cache_unaccounted"] == {}
    assert llm_stats.range_summary(3)["aggregate"]["prefix_cache_unaccounted"] == {"ask": 9}


def test_the_gap_copy_says_older_days_age_out(admin, stats_dir):
    key = "groq120|openai/gpt-oss-120b|ask"
    _seed(stats_dir, _GAP_ROW, counts={key: 409})
    assert "shrinks as they age out of the window" in _notice(admin.get("/admin").text)


# The two rate columns dash under DIFFERENT rules, both of them `_rate`'s:
#
#   hit_pct       = _rate(cached_tokens,     prompt_reported,   reported)
#   effective_pct = _rate(cached_measurable, prompt_measurable, measurable)
#
# and `_rate` returns None exactly when `not n or prompt <= 0`. So each column
# has a TWO-CLAUSE rule and nothing else, which is why the page now states the
# rule per column instead of counting causes: rounds 4, 5, 6 and 7 each found
# one more cause, because an enumeration cannot be closed by inspection.
#
# A route where every measurable call MISSED: Groq sends no figure on a miss, so
# `reported` is 0 while `measurable` is not. Hit rate dashes (n == 0) and
# Effective is a real 0.0%. This is the commonest shape on a Groq route and it is
# the row round 7 failed the page on -- none of Effective's four causes describes
# it, and the shared tooltip sent the reader to a note that did not cover it.
_ALL_MISS_ROW = {"calls": 3, "measurable": 3, "prompt_measurable": 3000,
                 "cached_measurable": 0, "reported": 0, "prompt_reported": 0,
                 "cached_tokens": 0}


def _dash_titles(html: str, route: str) -> list[str]:
    row = _row(html[html.index("Provider-side prefix cache (Groq)"):], route)
    return re.findall(r'<td\b[^>]*\btitle="([^"]*)"[^>]*>&mdash;</td>', row)


def test_an_all_miss_route_dashes_hit_rate_beside_a_real_effective(admin, stats_dir):
    """QA round 7, N-1. Every call measurable, every one a miss: Hit rate is a
    dash and Effective is a measured 0.0%. The page used to say "A dash has four
    causes" and none of the four is true here -- Measurable is 3, the model
    reports, the prompts are long enough and no report was discarded -- while the
    dash's own tooltip pointed at that list. Both are now scoped to Effective."""
    _seed(stats_dir, _ALL_MISS_ROW, route="allmiss",
          key="groq120|openai/gpt-oss-120b|allmiss")
    html = admin.get("/admin").text
    assert _pc_cells(html, "allmiss")[1:] == [
        "3", "3", "3000 / 0", "0", "—", "—", "0.0%"], _pc_cells(html, "allmiss")

    # Exactly one dash on this row, and it is Hit rate's.
    (tip,) = _dash_titles(html, "allmiss")
    assert "reported a cache figure" in tip, tip
    assert "four causes" not in tip, (
        "Effective's four causes are all false on this row -- the round-7 defect")

    # And the footnote names this pair rather than leaving the reader to infer it.
    text = _notice(html)
    assert "beside a real" in text and "Effective number" in text, text
    assert "no call hit" in text, (
        "the operator needs to be told what the pair MEANS, not just that it occurs")

    # `_rate`'s two guards are INDEPENDENT, and the row above exercises only the
    # denominator one: `reported` and `prompt_reported` are both 0 there, so
    # dropping `not n` changes nothing on it. Asserted directly, because a stored
    # row carrying prompt tokens against zero observed calls must still read as
    # unobserved -- booking it as a measured 0.0% is the one error this whole
    # panel exists to prevent ("absent is never zero").
    assert llm_stats._rate(0, 5000, 0) is None, (
        "zero observations is unobserved, whatever the denominator says")


def test_a_reported_prompt_total_of_zero_is_the_hit_rate_rules_second_clause(
        admin, stats_dir):
    """Round 7 listed this as a possible SIXTH cause it had not seeded. It is not
    a sixth cause -- it is the second clause of `_rate`'s own rule (`prompt <= 0`),
    which is why the page states the rule instead of a list. Reports arrived, so
    `reported` is 3, but they carried no prompt tokens: Hit rate dashes on the
    denominator, not on the count."""
    row = {**_ALL_MISS_ROW, "reported": 3, "prompt_reported": 0}
    assert not llm_stats._is_impossible({**llm_stats._PREFIX_ZERO, **row}), (
        "the fixture must be a coherent row, or it proves nothing about the rule")
    assert llm_stats._rate(0, 0, 3) is None, "the clause under test"
    _seed(stats_dir, row, route="zeroprompt",
          key="groq120|openai/gpt-oss-120b|zeroprompt")
    html = admin.get("/admin").text
    cells = _pc_cells(html, "zeroprompt")
    # Rep p/c is "0 / 0", NOT a dash: reports did arrive (`reported` is 3), so the
    # cell renders its sums. The dash is Hit rate's alone, and it comes from the
    # denominator. That distinction is the whole fixture.
    assert cells[1:] == ["3", "3", "3000 / 0", "3", "0 / 0", "—", "0.0%"], cells
    (tip,) = _dash_titles(html, "zeroprompt")
    assert "reported no prompt tokens" in tip, (
        f"the tooltip must cover the denominator clause, not only the count: {tip!r}")
    assert "reported no prompt tokens" in _notice(html)


def test_the_two_caches_sentences_cannot_be_softened(admin, stats_dir):
    """Round 7 ran 17 mutants and TWO survived: "is opportunistic" -> "is
    guaranteed", and "dies with it" -> "survives cold starts". Both are claims the
    page makes that no assertion could fail, and this repo's rule is that such a
    sentence is deleted or pinned. Both are true and worth keeping -- Groq's docs
    say hits are not guaranteed, and the response cache is per-instance -- so they
    are pinned here.

    Note the earlier guard read "survives our cold starts"; the surviving mutant
    said "survives cold starts" and walked straight through the word "our". This
    asserts on the claim, not on one spelling of its negation."""
    _seed_four_dash_causes()
    text = _notice(html := admin.get("/admin").text)

    assert "is opportunistic" in text, text
    assert "guarantee" not in text.lower(), (
        "Groq's docs say it 'tries to maximize cache hits, but this is not "
        "guaranteed'; a page promising a guarantee would be false")

    assert "dies with it" in text, text
    assert "survives" not in text.lower(), (
        "the response cache lives in one Cloud Run instance; any claim that it "
        "survives an instance going away is false, however it is spelled")
    assert html is not None
