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
    assert providers._prefix_usage(_usage(100, cached=bad)) == (100, None)
    # A junk PROMPT size leaves nothing usable, so the whole pair is dropped.
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
    assert "—" in unmeasured
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
    assert providers._prefix_usage(_usage(2000, cached=-1)) == (2000, None)
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
CHAT_ROUTES = frozenset({
    "natal", "ask", "matching", "rashifal_single", "today", "dasha", "outlook"})


def test_every_route_name_in_the_footnote_is_a_real_chat_route():
    """BUG-1, statically. Any route the copy names must be able to appear."""
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "astro_ai"
    code = "\n".join(p.read_text() for p in src.rglob("*.py"))
    declared = set(re.findall(r'route="([A-Za-z_0-9]+)"', code))
    assert CHAT_ROUTES <= declared, (
        f"CHAT_ROUTES names {CHAT_ROUTES - declared}, which no longer appears in "
        "src/ -- update the set rather than deleting the check")

    tmpl = (src / "templates" / "admin_dashboard.html").read_text()
    start = tmpl.index("Two different caches")
    end = tmpl.index("</p>", start)
    footnote = tmpl[start:end]
    # Hyphens included, or `gpt-oss-120b` never matches and the allowance below is
    # dead code -- which it was, making the whole assertion `set() <= real`.
    named = set(re.findall(r"<code>([a-z_0-9.\-]+)</code>", footnote))
    MODELS = {"gpt-oss-120b", "gpt-oss-20b", "gpt-oss-safeguard-20b"}
    NOT_ROUTES = {"usage"}          # API field names the copy may legitimately cite
    assert named - MODELS - NOT_ROUTES <= CHAT_ROUTES, (
        f"the prefix-cache footnote names {sorted(named - MODELS - NOT_ROUTES - CHAT_ROUTES)}, "
        "which cannot appear as a prefix_cache row")
    # And a bare mention, with no <code> wrapper, was previously invisible here.
    for overlay in ("ask_matching", "ask_numerology", "dasha_deep_dive", "rashifal"):
        assert overlay not in footnote, (
            f"{overlay!r} is a prompt overlay or a web-cache route, so it can never "
            "appear in this table; naming it is the BUG-1 defect")


# --- QA round 2 findings. BUG-3 was relocated, not removed; NEW-1..NEW-6. -----

@pytest.mark.parametrize("size", [50, 100, 127, 714, 1023, 2363])
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
    assert llm_stats._rate(5000, 2000, 1) == 100.0, "still clamped"
    assert llm_stats._is_impossible(
        {"cached_tokens": 5000, "cached_measurable": 5000,
         "prompt_reported": 2000, "prompt_measurable": 2000}) is True
    assert llm_stats._is_impossible(
        {"cached_tokens": -1, "cached_measurable": 0,
         "prompt_reported": 100, "prompt_measurable": 100}) is True
    assert llm_stats._is_impossible(
        {"cached_tokens": 96, "cached_measurable": 96,
         "prompt_reported": 100, "prompt_measurable": 100}) is False


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
    """NEW-1. The footnote asserted ONE cause; the tooltip above it said two, and
    a third (no usable `usage` block at all) is reachable on a reporting model."""
    _install_model(monkeypatch, [_usage(2363, cached=2304)])
    _chat()
    html = admin.get("/admin").text
    assert "A dash has three causes" in html
    assert "not a short prompt" not in html, (
        "that was the absolute claim the table's own tooltip contradicted")


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
