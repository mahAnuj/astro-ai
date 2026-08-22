#!/usr/bin/env python
"""Deploy-free stage-by-stage latency harness for `GET /` — issue #144.

Why this exists
---------------
Production `GET /` took ~20s on *every* request (median 19.9s, warm or cold —
not a cold start). Root cause was storage-shaped, not compute-shaped:

  * `storage._client()` built a brand-new `google.cloud.storage.Client()` on
    every call — fresh credential discovery + metadata-server token fetch +
    a new `AuthorizedSession`, so no HTTP connection was ever reused.
  * `storage.get()` did `blob.exists()` *then* `blob.download_as_text()` —
    two cross-continental round trips per read.
  * `events.counts_by_type(days=30)` reads one blob per day, and the homepage
    handler calls it alongside `users.count()` and `subscribers.count()`.

The bucket is US multi-region while Cloud Run runs in `asia-south1`, so each
of those handshakes crosses an ocean.

This script reproduces that network *shape* locally so the fix can be
measured without a deploy, and re-measured after.

How the simulation works
------------------------
We patch `google.cloud.storage.Client` — NOT `astro_ai.storage._client`.

That distinction matters: the fix for this issue lives *inside* `_client()`
(memoise the client). Stubbing `_client` itself would delete the thing we are
trying to measure and the harness would report "no improvement" forever.
Patching one level lower means client memoisation, connection reuse and the
removal of the `exists()` pre-check all show up honestly in the op counts.

Two latency constants model the prod network, both env-overridable:

  SIM_CLIENT_S (default 0.40)  TLS handshake + auth token fetch for a new client
  SIM_OP_S     (default 0.25)  one asia-south1 <-> US multi-region round trip

Every key is treated as ABSENT by default: `exists()` returns False and
`download_as_text()` raises `google.api_core.exceptions.NotFound`. That keeps
the code under test on its real paths and works against both the pre-fix tree
(exists() pre-check) and the post-fix tree (404-on-download). Set
`SIM_PRESENT=users,subscribers` (comma-separated substrings matched against
the blob key) to make selected keys exist and return `{}` — useful for pricing
the pre-fix double round trip, which a pure-miss run understates.

Usage
-----
    uv run python scripts/perf_homepage.py              # simulated GET / x3
    uv run python scripts/perf_homepage.py --stages     # per-stage breakdown
    uv run python scripts/perf_homepage.py --real       # against the real bucket

Exit code 0 if warm `GET /` is within budget (default 250ms), 1 otherwise.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

SIM_CLIENT_S = float(os.environ.get("SIM_CLIENT_S", "0.40"))
SIM_OP_S = float(os.environ.get("SIM_OP_S", "0.25"))
DEFAULT_BUDGET_MS = 250.0

# Counters are module-level so the fake blob/bucket/client classes can reach
# them without threading a context object through google-cloud-storage's API.
COUNTS: dict[str, int] = {}
SIM_SLEPT_S = 0.0


def _reset_counts() -> None:
    global SIM_SLEPT_S
    for k in ("client", "blob", "exists", "download", "upload", "reload"):
        COUNTS[k] = 0
    SIM_SLEPT_S = 0.0


def _snapshot() -> dict[str, int]:
    return dict(COUNTS)


def _delta(before: dict[str, int]) -> dict[str, int]:
    return {k: COUNTS[k] - before.get(k, 0) for k in COUNTS}


def _sleep(seconds: float) -> None:
    global SIM_SLEPT_S
    if seconds > 0:
        time.sleep(seconds)
    SIM_SLEPT_S += seconds


# ── The fake GCS surface ────────────────────────────────────────────────────

def _not_found_cls():
    """The exception a real 404 raises. Falls back to a lookalike if
    google-api-core is missing so the harness still runs."""
    try:
        from google.api_core import exceptions as gapi_exc  # type: ignore
        return gapi_exc.NotFound
    except Exception:  # pragma: no cover — google-api-core is a hard dep today
        class _NotFound(Exception):
            code = 404
        return _NotFound


NotFound = _not_found_cls()


def _present_patterns() -> list[str]:
    raw = os.environ.get("SIM_PRESENT", "")
    return [p.strip() for p in raw.split(",") if p.strip()]


class _FakeBlob:
    def __init__(self, key: str, present: bool):
        self.key = key
        self.name = key
        self._present = present
        self.generation = 1 if present else None

    def exists(self, *_a, **_kw) -> bool:
        _sleep(SIM_OP_S)
        COUNTS["exists"] += 1
        return self._present

    def download_as_text(self, *_a, **_kw) -> str:
        _sleep(SIM_OP_S)
        COUNTS["download"] += 1
        if not self._present:
            raise NotFound(f"sim: no such object: {self.key}")
        return "{}"

    def upload_from_string(self, _data, *_a, **_kw) -> None:
        _sleep(SIM_OP_S)
        COUNTS["upload"] += 1

    def reload(self, *_a, **_kw) -> None:
        _sleep(SIM_OP_S)
        COUNTS["reload"] += 1
        if not self._present:
            raise NotFound(f"sim: no such object: {self.key}")


class _FakeBucket:
    def __init__(self, name: str):
        self.name = name

    def blob(self, key: str, *_a, **_kw) -> _FakeBlob:
        COUNTS["blob"] += 1
        present = any(p in key for p in _present_patterns())
        return _FakeBlob(key, present)


class _FakeClient:
    """Stands in for `google.cloud.storage.Client`.

    Construction is where the expensive part lives in prod (credential
    discovery + token fetch + new TLS session), so that is where we charge
    SIM_CLIENT_S. Memoising the client in `astro_ai.storage` therefore shows
    up directly as a drop in the `client` counter.
    """

    def __init__(self, *_a, **_kw):
        _sleep(SIM_CLIENT_S)
        COUNTS["client"] += 1

    def bucket(self, name: str, *_a, **_kw) -> _FakeBucket:
        return _FakeBucket(name)


def _install_stub() -> None:
    """Point `google.cloud.storage.Client` at the fake and drop any client
    already memoised by `astro_ai.storage`."""
    from google.cloud import storage as gcs  # type: ignore[attr-defined]
    gcs.Client = _FakeClient
    from astro_ai import storage
    reset = getattr(storage, "reset_client", None)
    if callable(reset):
        reset()


# ── App bootstrap ───────────────────────────────────────────────────────────

def _bootstrap_env(simulated: bool) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-perf-harness-fake")
    if simulated:
        os.environ.setdefault("BHAGYA_STORAGE_BUCKET", "sim-bucket")


def _client_for_app():
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    return TestClient(app)


def _time_requests(client, n: int, *, simulated: bool) -> list[float]:
    """One warm-up request (fills per-process memos), then `n` timed ones."""
    t0 = time.perf_counter()
    warm = client.get("/")
    warm_s = time.perf_counter() - t0
    print(f"warm-up GET / -> {warm.status_code} in {warm_s:.3f}s")
    if warm.status_code != 200:
        print(f"  !! warm-up returned {warm.status_code}; timings below are not "
              f"measuring a real homepage render")

    latencies: list[float] = []
    for i in range(1, n + 1):
        before = _snapshot()
        t0 = time.perf_counter()
        resp = client.get("/")
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)
        ops = _delta(before) if simulated else _delta(before)
        print(f"req {i}: {elapsed:.3f}s  status={resp.status_code}  ops={ops}")
    return latencies


# ── Stage breakdown ─────────────────────────────────────────────────────────

def _trust_stage():
    """Return (label, callable) for the homepage's trust-bar counts.

    Post-fix the counts live in `astro_ai.trust_bar.counts()`. Pre-fix they are
    inline in `main.index`, so we replicate that exact call sequence rather
    than crash on the missing module.
    """
    try:
        from astro_ai import trust_bar  # type: ignore
    except Exception:
        trust_bar = None
    fn = getattr(trust_bar, "counts", None) if trust_bar is not None else None
    if callable(fn):
        return "astro_ai.trust_bar.counts()", fn

    from astro_ai import events, subscribers, users

    def inline():
        out = {}
        try:
            out["users"] = users.count()
        except Exception:
            out["users"] = 0
        try:
            out["subscribers"] = subscribers.count()
        except Exception:
            out["subscribers"] = 0
        try:
            out.update(events.counts_by_type(days=events.EVENT_RETENTION_DAYS))
        except Exception:
            pass
        return out

    return "inline main.index trust block (pre-fix tree)", inline


def _timed(label: str, fn):
    before = _snapshot()
    t0 = time.perf_counter()
    try:
        fn()
        note = ""
    except Exception as err:  # a stage that blows up is data, not a crash
        note = f"  !! raised {type(err).__name__}: {err}"
    elapsed = time.perf_counter() - t0
    print(f"  {label:<34} {elapsed*1000:8.1f}ms  ops={_delta(before)}{note}")
    return elapsed


def _run_stages(client) -> None:
    from astro_ai import main as app_main

    print("\n--- stages (each timed separately) ---")

    label, trust_fn = _trust_stage()
    _timed(label, trust_fn)

    cache = getattr(app_main, "_PANCHANG_STRIP_CACHE", None)
    panchang_fn = getattr(app_main, "panchang_strip_for_city", None)
    if callable(panchang_fn):
        if isinstance(cache, dict):
            cache.clear()
            _timed("panchang_strip_for_city (cold)",
                   lambda: panchang_fn("Mumbai, India"))
        _timed("panchang_strip_for_city (memo)",
               lambda: panchang_fn("Mumbai, India"))
    else:
        print("  panchang_strip_for_city             n/a (not in this tree)")

    # Capture the real template + context off a live request, then re-render it
    # in isolation. Rendering is pure CPU, so this is the floor `GET /` can hit.
    captured = {}
    original = app_main.templates.TemplateResponse

    def _spy(*args, **kwargs):
        resp = original(*args, **kwargs)
        if getattr(resp, "template", None) is not None and "resp" not in captured:
            captured["resp"] = resp
        return resp

    app_main.templates.TemplateResponse = _spy
    try:
        client.get("/")
    finally:
        app_main.templates.TemplateResponse = original

    resp = captured.get("resp")
    if resp is None:
        print("  template render                     n/a (no TemplateResponse captured)")
        return
    tmpl, ctx = resp.template, resp.context
    _timed(f"render {getattr(tmpl, 'name', '?')}", lambda: tmpl.render(ctx))


# ── Real-bucket mode ────────────────────────────────────────────────────────

def _check_real_prereqs() -> str | None:
    """None if we can talk to a real bucket, else a human-readable reason."""
    bucket = os.environ.get("BHAGYA_STORAGE_BUCKET", "").strip()
    if not bucket:
        return "BHAGYA_STORAGE_BUCKET is not set"
    try:
        import google.auth  # type: ignore
        google.auth.default()
    except Exception as err:
        return (f"no Application Default Credentials ({type(err).__name__}: {err}) — "
                f"run `gcloud auth application-default login`")
    return None


def _install_real_counters() -> None:
    """Count real client constructions and real storage reads. No latency is
    injected — the network provides it."""
    from google.cloud import storage as gcs  # type: ignore[attr-defined]
    from astro_ai import storage

    real_init = gcs.Client.__init__

    def counting_init(self, *a, **kw):
        COUNTS["client"] += 1
        return real_init(self, *a, **kw)

    gcs.Client.__init__ = counting_init

    real_get = storage.get

    def counting_get(key):
        COUNTS["download"] += 1
        return real_get(key)

    storage.get = counting_get


# ── Entry point ─────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stages", action="store_true",
                        help="also break GET / down into trust counts, panchang and render")
    parser.add_argument("--real", action="store_true",
                        help="hit the real bucket instead of the simulation "
                             "(needs BHAGYA_STORAGE_BUCKET + ADC)")
    parser.add_argument("--requests", type=int, default=3,
                        help="timed requests after the warm-up (default 3)")
    parser.add_argument("--budget-ms", type=float, default=DEFAULT_BUDGET_MS,
                        help=f"warm GET / budget in ms (default {DEFAULT_BUDGET_MS:.0f})")
    args = parser.parse_args(argv)

    _reset_counts()
    _bootstrap_env(simulated=not args.real)

    if args.real:
        reason = _check_real_prereqs()
        if reason:
            print(f"--real unavailable: {reason}")
            print("Refusing to print simulated numbers under a --real flag.")
            return 1
        print(f"mode: REAL bucket={os.environ['BHAGYA_STORAGE_BUCKET']}")
        _install_real_counters()
    else:
        print(f"mode: SIMULATED  SIM_CLIENT_S={SIM_CLIENT_S:.2f}s  "
              f"SIM_OP_S={SIM_OP_S:.2f}s  SIM_PRESENT={_present_patterns() or 'none'}")
        _install_stub()

    # Provenance banner. This script inserts its OWN repo's src/ on sys.path,
    # so invoking it BY PATH from a different worktree silently measures this
    # tree, not the one you cd'd into — which quietly turns a before/after
    # comparison into after/after. Printing the resolved module file makes that
    # mistake visible instead of silent. Copy the script into the tree you want
    # to measure, or check this line before trusting a number.
    import astro_ai
    print(f"measuring: {astro_ai.__file__}")

    client = _client_for_app()
    _reset_counts()
    latencies = _time_requests(client, max(1, args.requests), simulated=not args.real)

    if args.stages:
        _run_stages(client)

    median_s = statistics.median(latencies)
    budget_s = args.budget_ms / 1000.0
    mode = "real" if args.real else "simulated"
    ok = median_s <= budget_s
    print(f"\nmedian warm GET / ({mode}): {median_s*1000:.0f}ms "
          f"(min {min(latencies)*1000:.0f}ms, max {max(latencies)*1000:.0f}ms)")
    if not args.real:
        print(f"simulated network time charged across the run: {SIM_SLEPT_S:.2f}s")
    print(f"{'PASS' if ok else 'FAIL'}: warm GET / {median_s*1000:.0f}ms "
          f"{'<=' if ok else '>'} budget {args.budget_ms:.0f}ms")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
