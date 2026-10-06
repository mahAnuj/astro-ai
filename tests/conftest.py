"""Shared fixtures for the behaviour suite.

WHY THIS SUITE EXISTS — read before adding to it.

The twelve `scripts/verify_*.py` gates cover *data*: almanac dates, combustion
orbs, gochar tables, CSS, email templates, i18n symmetry. Not one covers
*request-path behaviour* — cache lifecycle, concurrency, or what a page renders
when something fails.

That gap is measurable. Across four QA rounds on one batch of reliability
fixes, eleven defects were found, and they fell into three buckets:

    cache / state lifecycle .... 6      (expiry, concurrency, "cached forever")
    error paths ................ 3      (what the user sees when it breaks)
    claim vs. diff ............. 2      (a comment asserting something untrue)

Every one after the first round was introduced by the previous round's *fix*.
The reason they kept getting through is that each change was verified by a
one-off harness written by the person who wrote the change — so it measured the
thing that had just been improved, and not the thing the code exists to do.
The clearest example: a fix for "the strip costs 20s per request" was verified
on timing alone, and shipped a version where the strip did not render at all.

So these tests deliberately assert **what the user gets**, not what the metric
says. Every test here corresponds to a defect that actually shipped into a
commit and was caught by review rather than by anything automated.

Keep them fast and hermetic: no network, no LLM, no GCS. Anything needing a
live provider belongs in a `scripts/verify_*.py` gate, not here.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture(autouse=True)
def _isolate_daily_cache(tmp_path, monkeypatch):
    """Point `daily_cache` at a tmp dir for EVERY test, always.

    This was previously an env var set at the top of one test module, which
    worked only because that module sorts alphabetically last and nothing
    earlier imported `daily_cache` at module scope. Adding a single module that
    does import it caused the suite to overwrite the repo's real
    `data/daily_cache/` with fixtures — including `{"body": ""}` — after which
    a dev server served 503 from a test artefact.

    An autouse fixture patching `_ROOT` directly has no ordering dependency at
    all: it cannot be defeated by adding a module, renaming one, or importing
    something earlier. A containment guarantee that rests on filename sort
    order is not a guarantee.
    """
    from astro_ai import daily_cache

    monkeypatch.setattr(daily_cache, "_ROOT", tmp_path / "daily_cache")


@pytest.fixture(autouse=True)
def _isolate_sqlite_cache(tmp_path, monkeypatch):
    """Point the SQLite LLM cache at a tmp file for EVERY test, always.

    Same defect class as `_isolate_daily_cache` above, and it had already
    happened: before this fixture existed, a run of this suite wrote a 57-char
    `natal:...` row into the repo's real `bhagya.db` — a body far below the
    800-char natal quality floor, i.e. a test artefact sitting in the cache a
    dev server reads. `cache.get`/`put` are reached indirectly from every
    route that generates a reading, so no test has to mention the cache to
    corrupt it.

    Patching `cache.DB_PATH` works because `_conn()` reads the module global
    at call time; it is deliberately not the `BHAGYA_CACHE_DB` env var, which
    is only consulted at import and so loses to whoever imports `cache` first.

    Function-scoped on purpose. A module-scoped fixture runs BEFORE
    function-scoped autouse ones, so anything hitting the cache from module
    scope would bypass this — the same ordering trap that let a module-scoped
    fixture sidestep `_offline_geocode`.
    """
    from astro_ai import cache

    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "bhagya.db")


@pytest.fixture(autouse=True)
def _clear_durable_miss_cache():
    """Empty the durable tier's negative-miss dict around EVERY test.

    It is module-level state keyed by (route, lang, prompt, chart), and the
    charts in this suite repeat — so without this, one test recording a miss
    makes a later test's pre-seeded blob invisible for 30 seconds and the
    failure depends on test order. Same reasoning as the `deps` fixture: a
    flaky suite gets ignored, which costs more than no suite.
    """
    from astro_ai.routes import llm_support

    llm_support._DURABLE_MISSES.clear()
    yield
    llm_support._DURABLE_MISSES.clear()


@pytest.fixture(autouse=True)
def _dummy_api_key(monkeypatch):
    """Give EVERY test a placeholder `OPENAI_API_KEY`, overriding any real one.

    Seven routes gate on `os.environ.get("OPENAI_API_KEY")` and render a 503
    "API key not configured" page when it is unset. `.env` is gitignored, so on
    a fresh clone five of the rashifal tests failed on that gate having never
    reached the behaviour they exist to check (#224). The obvious fix — read
    the real key, skip when absent — is the one this suite has already been
    burned by: eight tests skipped themselves into a green run and
    `verify_behaviour.py` printed PASS with a third of the suite absent.

    Overriding unconditionally, rather than defaulting only when unset, is the
    more important half. It means a developer or CI runner who DOES have a live
    key in their environment cannot have a test spend real quota against it:
    any test that forgets to stub `stub_llm` now fails on a bogus key instead
    of quietly billing the paid-tier safety net. Per the module docstring above,
    anything wanting a live provider belongs in a `scripts/verify_*.py` gate.

    The value is never used to authenticate: every LLM call in this suite is
    stubbed. It only has to be non-empty.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential")


@pytest.fixture(autouse=True)
def _offline_geocode(monkeypatch):
    """Resolve every place locally, so NO test can reach Nominatim.

    The module docstring above has said "no network" since this suite was
    written, but nothing enforced it — it was a convention, and conventions do
    not fail a build. Nine tests drifted across it and a fresh clone with no
    outbound access reported them red without anything being broken (#224).
    A guard that does not guard is worse than no guard, because the docstring
    reads as an assurance.

    `chart.geocode_place` is the single outbound call on these paths: it turns
    free text into (lat, lon, tz) over Nominatim with a 10s timeout, and
    `compute_chart` is that call plus pure local Swiss Ephemeris arithmetic.
    So patching this ONE name is what makes the suite hermetic, and it is
    deliberately the narrowest possible cut — charts, panchang, transits,
    Rahu Kaal and Abhijit are all still really computed. Stubbing
    `compute_chart` instead would have thrown that away and made several
    assertions vacuous.

    Patched on `chart`, where `compute_chart` looks it up in module globals at
    call time. Every place resolves to the same coordinates; no test here
    asserts on a specific location, and the ones that need a place to FAIL use
    `failing_geocode`, which raises from `compute_chart` before reaching this.

    Autouse and unconditional: an opt-in version is one a new test forgets,
    which is precisely how the nine got in.
    """
    from astro_ai import chart

    # Mumbai — the reference location the shared rashifal is generated against.
    monkeypatch.setattr(chart, "geocode_place",
                        lambda place: (19.0760, 72.8777, "Asia/Kolkata"))


@pytest.fixture
def today_iso() -> str:
    return date.today().isoformat()


@pytest.fixture
def deps():
    """`routes.deps` with every in-process cache emptied.

    Emptied per test because these caches are module-level dicts that live for
    the process, so leakage between tests would make failures depend on
    ordering — and a flaky suite gets ignored, which costs more than no suite.
    """
    from astro_ai.routes import deps as _deps

    _deps._PANCHANG_STRIP_CACHE.clear()
    _deps._fallback_cache.clear()
    yield _deps
    _deps._PANCHANG_STRIP_CACHE.clear()
    _deps._fallback_cache.clear()


@pytest.fixture
def failing_geocode(deps, monkeypatch):
    """Make `compute_chart` fail for chosen places, fast.

    Patches the name **`deps.compute_chart`**, not `chart.compute_chart`:
    `deps` does `from astro_ai.chart import compute_chart`, so patching the
    source module rebinds nothing and the stub silently never fires. That
    mistake produced a 0.01s "measurement" of a path that had not run.
    """

    def _install(should_fail, delay: float = 0.0):
        real = deps.compute_chart

        def stub(d, t, place):
            if should_fail(place):
                if delay:
                    import time

                    time.sleep(delay)
                raise RuntimeError(f"geocode failed for {place!r}")
            return real(d, t, place)

        monkeypatch.setattr(deps, "compute_chart", stub)

    return _install


@pytest.fixture
def client():
    """FastAPI test client. Import is inside the fixture so a collection error
    in one module does not take down the whole suite."""
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    return TestClient(app)


@pytest.fixture
def saved_chart(client):
    """POST `/reading` so the `client` carries the chart cookie `/kundli` needs.

    `GET /kundli` with no saved chart renders the SEO landing page and never
    reaches the LLM path, so anything asserting on generation cost has to get
    a chart into the cookie first. Hermetic because `_offline_geocode` above
    resolves the place without Nominatim.

    `follow_redirects=False` keeps the fixture from rendering `/kundli` itself
    — that render would generate a reading and the call count under test would
    start at one.
    """

    def _install(birth_date: str = "1990-04-12", birth_time: str = "14:35",
                 birth_place: str = "Mumbai, India", name: str = "Test Seeker"):
        resp = client.post(
            "/reading",
            data={"name": name, "birth_date": birth_date,
                  "birth_time": birth_time, "birth_place": birth_place},
            follow_redirects=False,
        )
        assert resp.status_code == 303, (
            f"POST /reading returned {resp.status_code}, so no chart cookie was set"
        )
        return {"name": name, "birth_date": birth_date,
                "birth_time": birth_time, "birth_place": birth_place}

    return _install


@pytest.fixture
def stub_llm(monkeypatch):
    """Replace the provider call and count invocations.

    Returns the counter, so a test can assert on *how many* live calls a
    sequence of requests would have made. Several defects here were not wrong
    output but unbounded cost — a body that failed the read gate regenerated on
    every single pageview, all day, on the quota that caused a 21-day outage.
    """
    import astro_ai.llm as llm

    calls = {"n": 0}

    def _install(text_or_fn):
        def fake(*a, **k):
            calls["n"] += 1
            return text_or_fn(calls["n"]) if callable(text_or_fn) else text_or_fn

        monkeypatch.setattr(llm.providers, "chat", fake)
        return calls

    return _install


@pytest.fixture
def rashi_body():
    """Builder for a generated reading that passes the quality gate.

    A fixture rather than a module-level helper because `tests/` is not a
    package — `from tests.conftest import ...` fails, and adding an
    `__init__.py` just to share one function is not worth the import surface.
    """

    def _build(n_chars: int = 900, heading: str = "Aries / Mesha") -> str:
        filler = "A steady day for measured work. "
        return f"## {heading}\n" + filler * (n_chars // len(filler) + 1)

    return _build
