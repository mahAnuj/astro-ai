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
