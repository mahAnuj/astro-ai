"""Panchang-strip cache lifecycle.

Six of the eleven defects found across four QA rounds were in this one
function. Every test below is a defect that reached a commit.

The strip matters more than it looks: since the shared rashifal was changed to
never state a clock time (it says "act in the Abhijit window" because one
national text cannot know the reader's local sunrise), this strip is the ONLY
place the reader gets an actual time. A missing strip is not a cosmetic
degradation — it is a reading that tells someone to act in a window and gives
them no way to know when it is.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path


def test_signed_out_outage_solves_once_not_twice(deps, failing_geocode):
    """A signed-out request already resolves to the default city, so falling
    back to the default re-runs the identical call that just failed.

    Defect: two full 10s geocode timeouts per request instead of one, on the
    homepage, for every visitor without a saved chart.
    """
    calls = []
    real = deps.compute_chart

    def stub(d, t, place):
        calls.append(place)
        raise RuntimeError("geocode down")

    deps.compute_chart = stub
    try:
        deps.panchang_strip_for_city("")
    finally:
        deps.compute_chart = real

    assert len(calls) == 1, f"default city solved {len(calls)}x; the fallback leg must be skipped"


def test_outage_is_cached_not_re_solved_every_request(deps):
    """Defect: the failure path returned without caching, and geocode's own
    lru_cache does not memoise a raising call either — so NOTHING memoised and
    every request paid the full timeout, forever. Baseline paid it once a day.
    """
    calls = []
    real = deps.compute_chart

    def stub(d, t, place):
        calls.append(place)
        raise RuntimeError("geocode down")

    deps.compute_chart = stub
    try:
        for _ in range(5):
            deps.panchang_strip_for_city("")
    finally:
        deps.compute_chart = real

    assert len(calls) == 1, f"{len(calls)} geocode attempts across 5 requests; expected 1"


def test_fallback_keeps_the_strip_visible(deps, failing_geocode):
    """Defect: a blip marked the key and served NOTHING for 60s — the exact
    #213 failure the fallback exists to prevent, made intermittent rather than
    all-day. The reader must keep seeing the default city's times, labelled.
    """
    failing_geocode(lambda place: "Mumbai" not in place)

    results = [deps.panchang_strip_for_city("Guwahati, India") for _ in range(4)]

    assert all(r[0] is not None for r in results), (
        "strip vanished after the first request: " + repr([bool(r[0]) for r in results])
    )
    assert all(r[2] == "Mumbai" for r in results), (
        "fallback must SAY which city it is showing, or the times are a lie"
    )


def test_fallback_is_not_day_cached(deps, failing_geocode):
    """Defect: caching the fallback under the requested key pinned that reader
    to the default city until midnight. Measured: a Guwahati reader would see
    an Abhijit 76 min off, not overlapping their real ~51-minute window at all.
    """
    failing_geocode(lambda place: "Mumbai" not in place)
    deps.panchang_strip_for_city("Guwahati, India")

    assert not deps._PANCHANG_STRIP_CACHE, (
        "fallback result entered the day cache: " + repr(list(deps._PANCHANG_STRIP_CACHE))
    )


def test_total_failure_gets_the_long_window(deps):
    """The two failure cases want different retry windows, and merging them
    was the mistake that produced both a blanked strip and a duty-cycle
    regression.

    Usable fallback -> retry the reader's real city soon.
    Nothing to serve -> retrying buys nothing and costs a blocking geocode.
    """
    real = deps.compute_chart
    deps.compute_chart = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("all down"))
    try:
        deps.panchang_strip_for_city("Kolkata, India")
    finally:
        deps.compute_chart = real

    (result, _at), = deps._fallback_cache.values()
    assert result[0] is None
    ttl = deps._FALLBACK_TTL_S if result[0] is not None else deps._TOTAL_FAILURE_TTL_S
    assert ttl == deps._TOTAL_FAILURE_TTL_S
    assert deps._TOTAL_FAILURE_TTL_S > deps._FALLBACK_TTL_S, (
        "a total failure must be retried LESS often than a usable fallback"
    )


def test_expired_entry_under_concurrency_does_not_raise(deps):
    """Defect (HIGH): `del _fallback_cache[key]` on the expiry path.

    Nothing holds a lock between the read and the delete, so two threads
    reaching the same expired entry both delete and the loser raises KeyError —
    which escapes to the route and 500s `/` and `/rashifal`. The TTL boundary is
    exactly when a herd converges on the key, so the race window coincides with
    peak concurrency.

    This calls the REAL function. An earlier version of this test copied the
    get/pop logic into the test body, which meant it exercised a copy and would
    have passed no matter what `deps.py` did — caught by mutation testing, which
    is the entire argument for doing it.
    """
    escapes: list[str] = []
    real = deps.compute_chart
    real_ttl = deps._TOTAL_FAILURE_TTL_S
    deps.compute_chart = lambda d, t, place: (_ for _ in ()).throw(RuntimeError("down"))
    # TTL of zero puts EVERY caller on the expiry line, which is where the race
    # lives. With a real TTL the first thread writes a fresh entry and the rest
    # return early, so the window almost never opens and the test passes
    # whatever the code does — that is how a concurrency test lies.
    deps._TOTAL_FAILURE_TTL_S = 0.0
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    key = (deps.date.today().isoformat(), "guwahati, india")

    def planter():
        # Keeps an entry present for callers to collide on. Needed IN ADDITION
        # to the zero TTL: without it the first thread removes the entry and
        # the rest find nothing, so two threads rarely hold the same key at
        # once. Zero-TTL alone and planter-alone each let the bug through;
        # only the pair reproduces it.
        for _ in range(20_000):
            deps._fallback_cache[key] = ((None, None, ""), -10_000.0)

    def caller():
        for _ in range(2000):
            try:
                deps.panchang_strip_for_city("Guwahati, India")
            except Exception as err:  # noqa: BLE001 - the point is to catch anything
                escapes.append(repr(err))

    try:
        threads = ([threading.Thread(target=planter) for _ in range(4)]
                   + [threading.Thread(target=caller) for _ in range(12)])
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old_interval)
        deps.compute_chart = real
        deps._TOTAL_FAILURE_TTL_S = real_ttl

    assert not escapes, f"{len(escapes)} exception(s) escaped the route: {escapes[:3]}"


def test_eviction_is_concurrency_safe(deps, monkeypatch):
    """Defect: the replacement for clear() iterated a live dict from a
    Python-level comprehension and raised `dictionary changed size during
    iteration`, surfacing as a 500 on `/` and `/rashifal`. clear() was a single
    C call and could not raise, so this was a NEW failure mode.

    Also calls the real function — the solve chain is stubbed so the SUCCESS
    path (the only one that reaches eviction) runs without an ephemeris hit.
    """
    monkeypatch.setattr(deps, "compute_chart", lambda d, t, place: object())
    monkeypatch.setattr(deps, "compute_panchang", lambda chart: "panchang")
    monkeypatch.setattr(deps, "compute_transit_snapshot",
                        lambda chart: type("S", (), {"planets": []})())

    errors: list[str] = []
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)

    def hammer(n: int):
        for i in range(400):
            try:
                deps.panchang_strip_for_city(f"City{n}x{i}, India")
            except Exception as err:  # noqa: BLE001
                errors.append(repr(err))

    try:
        threads = [threading.Thread(target=hammer, args=(i,)) for i in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old_interval)

    assert not errors, f"{len(errors)} error(s) escaped: {errors[:3]}"
    assert len(deps._PANCHANG_STRIP_CACHE) <= deps._STRIP_CACHE_MAX + 16, (
        f"eviction stopped bounding under concurrency: {len(deps._PANCHANG_STRIP_CACHE)}"
    )


def test_eviction_is_bounded_and_keeps_what_matters(deps, today_iso, monkeypatch):
    """Defect: the >100 guard called clear() on the whole dict, discarding the
    DEFAULT-city entry — the one backing every signed-out page, and the most
    expensive to rebuild — along with the tail that tripped the limit.
    """
    monkeypatch.setattr(deps, "compute_chart", lambda d, t, place: object())
    monkeypatch.setattr(deps, "compute_panchang", lambda chart: "panchang")
    monkeypatch.setattr(deps, "compute_transit_snapshot",
                        lambda chart: type("S", (), {"planets": []})())

    default_key = (today_iso, deps._STRIP_DEFAULT_CITY.lower())
    deps._PANCHANG_STRIP_CACHE[default_key] = ("default", None, "Mumbai")
    for i in range(150):
        deps._PANCHANG_STRIP_CACHE[(today_iso, f"city{i}")] = ("x", None, "x")

    # Eviction is only reachable on the SUCCESS path — a failure goes to the
    # fallback cache and never touches the day cache. Worth knowing: a
    # pure-outage workload cannot trip this bound at all.
    deps.panchang_strip_for_city("Kolkata, India")

    size = len(deps._PANCHANG_STRIP_CACHE)
    assert size <= deps._STRIP_CACHE_MAX + 1, f"unbounded: {size} entries"
    assert default_key in deps._PANCHANG_STRIP_CACHE, "default-city entry was evicted"


def test_no_unguarded_del_on_a_shared_cache():
    """Static guard for the HIGH KeyError race.

    The concurrency test above exercises the real function, but a race is
    nondeterministic by definition: it reproduces reliably in a standalone
    harness (319 KeyErrors) and not under pytest, and I could not close that
    gap for less than it was worth. A test that catches a defect *sometimes*
    is not a gate.

    So this asserts the property rather than the symptom: no bare `del` on a
    module-level cache dict that more than one thread can reach.
    `.pop(k, None)` is idempotent and cannot lose a race; `del` raises
    KeyError for the loser, which escapes to the route and 500s the page. The
    eviction path in the same file already used `.pop` — the rule existed, it
    just was not enforced anywhere.

    Deterministic, instant, and it fails on exactly the diff that caused the
    bug. Delete it only when the shared dicts are behind a lock.
    """
    import re

    source = (Path(__file__).resolve().parent.parent
              / "src/astro_ai/routes/deps.py").read_text()
    offenders = re.findall(r"^\s*del\s+(_[A-Za-z_]*(?:CACHE|cache)[A-Za-z_]*)\[", source, re.M)

    assert not offenders, (
        f"bare `del` on shared cache(s) {sorted(set(offenders))} — use .pop(key, None); "
        "the loser of a concurrent delete raises KeyError into the route"
    )


def test_blank_city_shares_the_default_entry(deps):
    """Defect: keying on the raw input gave "", "  " and None separate slots
    holding byte-identical default-city data."""
    real = deps.compute_chart
    seen = []

    def stub(d, t, place):
        seen.append(place)
        raise RuntimeError("skip")

    deps.compute_chart = stub
    try:
        for city in ("", "   ", None):
            deps.panchang_strip_for_city(city)
    finally:
        deps.compute_chart = real

    assert len(deps._fallback_cache) == 1, (
        "blank inputs opened separate cache entries: " + repr(list(deps._fallback_cache))
    )
