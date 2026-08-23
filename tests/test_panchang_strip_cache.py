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

import ast
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


def test_total_failure_is_retried_less_often_than_a_usable_fallback(deps, monkeypatch):
    """The two failure cases must keep DIFFERENT retry windows.

    Asserts the observable — what is served at a given age — rather than
    recomputing the TTL selector inside the test. The previous version did the
    latter, which made one line `assert X == X`: it had already asserted the
    result was unusable, then re-derived the branch that follows from exactly
    that. Both mutations of the real selector escaped it.

    That was the third instance of this shape in a suite written to eliminate
    it. A test that recomputes the thing it is checking is testing itself.
    """
    solves = []

    def counting_solve(d, t, place):
        solves.append(place)
        raise RuntimeError("down")

    monkeypatch.setattr(deps, "compute_chart", counting_solve)
    # Age every cached entry to sit BETWEEN the two windows: past the short one,
    # inside the long one. A usable fallback must be re-solved; a total failure
    # must still be served from cache.
    # LITERAL bounds, not values derived from the constants under test.
    #
    # The first version computed its probe point as the midpoint of the two
    # constants, so any change to them moved the probe with them and the test
    # passed regardless: `else float('inf')`, a 600->86400 day-long cache (the
    # very thing this docstring condemns), 60->0, and 600->61 all escaped it.
    # A test whose inputs are derived from its subject cannot constrain it.
    assert 30.0 <= deps._FALLBACK_TTL_S <= 120.0, (
        f"fallback window {deps._FALLBACK_TTL_S}s is outside the range this test "
        "was written for; re-derive the numbers, do not widen the assert"
    )
    assert 300.0 <= deps._TOTAL_FAILURE_TTL_S <= 3600.0, (
        f"total-failure window {deps._TOTAL_FAILURE_TTL_S}s is outside the intended "
        "range — under 5min re-arms the event-loop stall, over an hour is the "
        "day-long cache #213 removed"
    )
    assert deps._TOTAL_FAILURE_TTL_S >= 5 * deps._FALLBACK_TTL_S, (
        "the two windows have collapsed together; the split is the whole point"
    )
    between = 180.0    # fixed: past the fallback window, inside the total-failure one
    aged_at = deps._time.monotonic() - between
    key = (deps.date.today().isoformat(), "kolkata, india")

    # 1. Total failure: nothing to serve, so do NOT retry inside the long window.
    deps._fallback_cache[key] = ((None, None, ""), aged_at)
    solves.clear()
    result = deps.panchang_strip_for_city("Kolkata, India")
    assert solves == [], "a total failure was re-solved inside its own window"
    assert result[0] is None

    # 2. Usable fallback of the SAME age: past its shorter window, so retry.
    deps._fallback_cache[key] = (("panchang", None, "Mumbai"), aged_at)
    solves.clear()
    deps.panchang_strip_for_city("Kolkata, India")
    assert solves, "a stale fallback was served instead of retrying the real city"

    # 3. A total failure aged PAST its own window must be retried too —
    # "retried less often" must not degrade into "never retried".
    deps._fallback_cache[key] = (
        (None, None, ""), deps._time.monotonic() - (deps._TOTAL_FAILURE_TTL_S + 10),
    )
    solves.clear()
    deps.panchang_strip_for_city("Kolkata, India")
    assert solves, "a total failure past its window was never retried — that is a cache, not a TTL"


def test_concurrent_access_raises_nothing(deps, monkeypatch):
    """General concurrency smoke test — honestly named this time.

    Its predecessor was called `test_expired_entry_under_concurrency_does_not
    _raise` and claimed to cover the `del` KeyError race. Review measured it
    with `del` compiled in: 0 escapes in 24,000 calls, three runs. It could not
    fail on the defect it was named for, and cost ~2.5s a run to do so. The race
    is covered deterministically by `test_no_unguarded_del_on_a_shared_dict`.

    This keeps the part that has value — many threads through the real function,
    nothing escapes — without claiming to catch a specific race it cannot. It is
    a tripwire for races NOT yet known, which is a real job, just a different one.
    """
    monkeypatch.setattr(deps, "compute_chart",
                        lambda d, t, place: (_ for _ in ()).throw(RuntimeError("down")))
    escapes: list[str] = []
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)

    def caller(n: int):
        for i in range(200):
            try:
                deps.panchang_strip_for_city(f"City{n % 3}, India")
            except Exception as err:  # noqa: BLE001 - anything escaping is the failure
                escapes.append(repr(err))

    try:
        threads = [threading.Thread(target=caller, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old_interval)

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


_DICT_FACTORIES = {"dict", "defaultdict", "OrderedDict", "Counter"}


def _module_level_dicts(tree: ast.Module) -> set[str]:
    """Names bound at module scope to a dict — the ones every thread shares.

    Collects more spellings than a literal `{}`: review found `dict()`, a dict
    comprehension, and an `AnnAssign` whose annotation says `MutableMapping`
    all sliding past a literals-only version. Alias chains
    (`_b = _a; del _b[k]`) and cross-module attribute deletes
    (`del deps._cache[k]`) are still not caught and are not worth chasing —
    recorded here so the next reader knows the boundary rather than assuming
    there isn't one.
    """
    names: set[str] = set()

    def _is_dictish(value) -> bool:
        if isinstance(value, (ast.Dict, ast.DictComp)):
            return True
        return (isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in _DICT_FACTORIES)

    for node in tree.body:
        if isinstance(node, ast.Assign) and _is_dictish(node.value):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            ann = ast.unparse(node.annotation) if node.annotation else ""
            # The VALUE decides, not the annotation string: `_m: MutableMapping
            # [str, int] = {}` is as shared as one annotated `dict`.
            if _is_dictish(node.value) or "dict" in ann.lower() or "mapping" in ann.lower():
                names.add(node.target.id)
    return names


def _locally_bound(fn: ast.AST) -> set[str]:
    """Names a function binds itself — parameters and local assignments.

    A `del` on one of those cannot race anything: it is a local, however much
    its name resembles a module-level dict. Without this the guard fails on
    correct single-threaded code, and a gate that cries wolf gets deleted.
    """
    bound: set[str] = set()
    args = getattr(fn, "args", None)
    if args:
        for group in (args.posonlyargs, args.args, args.kwonlyargs):
            bound.update(a.arg for a in group)
        for extra in (args.vararg, args.kwarg):
            if extra:
                bound.add(extra.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
    return bound


def test_no_unguarded_del_on_a_shared_dict():
    """Static guard for the KeyError race, across the WHOLE package.

    `.pop(k, None)` is idempotent; `del d[k]` raises KeyError for the loser of a
    concurrent delete, which escapes to the route and 500s the page. The race is
    nondeterministic — it reproduces in a standalone harness and not under
    pytest — so this asserts the property instead of the symptom.

    The first version of this was a regex over `deps.py` alone, and review found
    FOUR ways past it: a different module (`del _regen_failures[k]` in
    `rashifal.py`), a dict whose name lacks "cache", a space before the bracket,
    and a multi-target `del a[0], b[k]`. Its docstring claimed to check module
    -level cache dicts everywhere; it checked one spelling in one file.

    An AST walk cannot be defeated by whitespace, naming or statement shape, and
    it sees every module. Deleting a whole name (`del temp`, used at module
    scope to drop import-time loop variables) is untouched — only subscripted
    deletes on a module-level dict are flagged.
    """
    root = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
    offenders: list[str] = []

    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text())
        shared = _module_level_dicts(tree)
        if not shared:
            continue
        # Only deletes INSIDE a function can race — a module-scope `del` runs
        # once at import, single-threaded, and is a legitimate way to drop a
        # loop temporary.
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            local = _locally_bound(fn)
            for node in ast.walk(fn):
                if not isinstance(node, ast.Delete):
                    continue
                for target in node.targets:
                    if (isinstance(target, ast.Subscript)
                            and isinstance(target.value, ast.Name)
                            and target.value.id in shared
                            and target.value.id not in local):
                        offenders.append(
                            f"{path.relative_to(root.parent.parent)}:{node.lineno} "
                            f"del {target.value.id}[...]"
                        )

    assert not offenders, (
        "bare `del` on a module-level dict — use .pop(key, None), because the "
        "loser of a concurrent delete raises KeyError into the route:\n  "
        + "\n  ".join(offenders)
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
