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
def _token_bucket_off_and_empty(monkeypatch):
    """Switch the per-model token bucket OFF and empty its registry, every test.

    The bucket (#475) is process-global state with a clock and a sleep behind
    it. Left on, a test that sends several calls through a fake Groq chain
    would be paced against the REAL clock and sleep for real; left populated,
    one test's reservations would delay the next one's. Off is also the
    pre-#475 path exactly, which is what every older test was written against.

    `tests/test_token_bucket.py` opts in by setting BHAGYA_TPM_PACING itself --
    inside the test body, which runs after this fixture and so wins.
    """
    from astro_ai import providers

    monkeypatch.setenv("BHAGYA_TPM_PACING", "0")
    providers._BUCKETS.clear()
    yield
    providers._BUCKETS.clear()


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


@pytest.fixture(autouse=True)
def _no_outbound_http(monkeypatch):
    """Make `urllib.request.urlopen` unreachable for EVERY test, always.

    MEASURED, 2026-10-20 — the docstring at the top of this file has promised
    "no network" since the suite was written, and `_offline_geocode` above says
    in as many words that a guard which does not guard is worse than none. This
    suite was making **16 real HTTPS requests to raw.githubusercontent.com per
    run**, eight each from `test_llm_attribution.py::test_ops_says_it_is_
    reading_a_local_dev_store` and `::test_ops_names_the_bucket_when_one_is_
    configured` (loop/cost/issues/agents/ga4-daily/gsc-daily/gsc-trend-page/
    gsc-trend-query.json). Recorded with a `urlopen` spy, because a real request
    that succeeds looks exactly like no request.

    The cause is a correct-looking local patch. `_ops_page` pins `LIVE_ISSUES`
    and `LIVE_TODAY` off, which stops the two `api.github.com` calls, and then
    sets `OPS_MEASUREMENTS_DIR` to a path that does not exist — which makes
    `measurements_dir()` return None and drops every `_fetch` onto its HTTPS
    branch instead. Round 1 removed 2 of 18 requests and recorded that the
    suite no longer depended on a network it is documented not to use; 16
    remained. So the claim is made true here rather than restated.

    WHY A SUITE-WIDE FIXTURE AND NOT A THIRD LINE IN `_ops_page`. Both of
    `_fetch`'s callers reach the network through a path no test mentions, and
    the pattern of this defect is that the next test will not mention it
    either: `/admin/ops` renders eight files, and nothing on the way there
    reads as outbound I/O. An opt-in guard is the one a new test forgets, which
    is exactly how the nine Nominatim tests got in.

    `urllib.error.URLError` rather than an assertion, deliberately: it is what
    an unreachable network actually raises, so a caller that is supposed to
    degrade — `ops_data._fetch` returns None and logs, by contract — degrades,
    and a caller that is not supposed to still fails. Tests that need a stubbed
    GitHub patch the same attribute inside the test body and win, because
    `monkeypatch` unwinds in LIFO order.

    `httpx` (Brevo, the TestClient, THE LLM CLIENT) and `google-cloud-storage`
    do not go through `urllib`, so this fixture cannot see them. That is
    `_no_outbound_sockets` below, which guards the layer every transport shares.

    THIS FIXTURE ALONE DELIVERED 16 -> 2, NOT 16 -> 0. The comment that stood
    here said `httpx` and `google-cloud-storage` were "already stubbed where
    used", and it was wrong. QA round 4 found it with a spy on
    `socket.socket.connect` and `socket.getaddrinfo` -- a layer `urlopen`
    patching cannot see: two tests in `test_nadi_position_coherence.py` POST
    `/matching`, whose narrative call goes out over `httpx`, so each made a real
    TCP connection to whichever LLM provider the environment is configured for
    (#449). No key was present, so nothing was spent; with one, every suite run
    would have billed it. Both now stub the provider, and the socket guard is
    what keeps the count at 0 rather than a measurement someone repeats.
    """
    import urllib.parse
    import urllib.request

    real = urllib.request.urlopen

    #: Loopback is NOT outbound, and blocking it broke a real test rather than a
    #: real request. `tests/test_hindi_surface_gate.py` (#424) drives the
    #: `verify_hindi_surface` gate against a stub HTTP server it starts itself on
    #: an ephemeral port, through this same `urlopen` — so a blanket block turned
    #: "the suite sends no packets off this machine", which is the promise, into
    #: "no test may run a server", which is not. Measured on the merge of #418
    #: and #424: two failures, both in that file, neither a network request.
    #:
    #: Reaching a loopback address still cannot leave the machine, so the
    #: hermeticity claim this fixture exists to make true is unaffected: the 16
    #: raw.githubusercontent.com requests stay blocked, asserted by
    #: `test_the_behaviour_suite_cannot_reach_the_network`. (The socket guard
    #: below treats loopback the same way, for the same reason.)
    _LOOPBACK = ("127.0.0.1", "localhost", "::1", "[::1]")

    def _host_of(target) -> str:
        url = getattr(target, "full_url", None) or (
            target if isinstance(target, str) else "")
        try:
            return (urllib.parse.urlsplit(url).hostname or "").lower()
        except ValueError:
            return ""

    def _blocked(target=None, *a, **k):
        if _host_of(target) in _LOOPBACK:
            return real(target, *a, **k)
        import urllib.error
        raise urllib.error.URLError(
            "the behaviour suite is hermetic: no outbound HTTP. Stub "
            "urllib.request.urlopen in your test if it needs a response. "
            "(Loopback is allowed — a test may run its own server.)"
        )

    monkeypatch.setattr(urllib.request, "urlopen", _blocked)


@pytest.fixture(autouse=True)
def _no_outbound_sockets(monkeypatch, request):
    """Fail any test that opens a NON-LOOPBACK socket, whatever the transport.

    `_no_outbound_http` above is aimed at `urllib`, and the LLM client is
    `httpx`: for the life of that guard two tests reached a live provider on
    every run while the suite reported itself hermetic (#449). A guard per
    library is the shape that let it happen, so this one sits on
    `socket.socket.connect` and `socket.getaddrinfo`, which every library ends
    in -- `httpx`, `requests`, `urllib`, `google-cloud-storage`, `asyncio`.

    IT RECORDS, AND THEN FAILS AT TEARDOWN, rather than only raising. The LLM
    client, `ops_data._fetch`, the notifiers and most routes catch an exception
    and degrade, so a guard that merely raised from inside `connect` would be
    swallowed one frame up and the test would go green -- the failure the
    `urlopen` guard documents ("a real request that succeeds looks exactly like
    no request"), reproduced one layer down. It still raises an `OSError` so
    nothing leaves the machine; the teardown assertion is what makes it fail.

    Allowed: loopback (127.0.0.0/8, ::1, `localhost`) and AF_UNIX paths --
    `test_hindi_surface_gate.py` runs its own server, and a loopback connection
    cannot leave the host. Anything else is a defect to FIX with a stub, never
    to allow-list, with ONE narrow door:

        @pytest.mark.network_allowed("some.host", reason="why")

    permits resolving that exact host for that exact test, and connecting only
    to the addresses it resolved to. It exists for
    `test_the_token_estimator_never_under_counts_a_real_request`, which needs
    tiktoken's real `o200k_base` vocabulary and there is no honest stub for
    "the estimate is at least the real count". Any other host under the marker
    still fails.

    Function-scoped, like the fixtures above: a module-scoped one would run
    before them. Not covered: `socket.gethostbyname` and friends, which this
    suite does not use, and anything run at import or collection time.

    Yields the list of violations so the test that proves the guard bites can
    inspect it and clear it; no other test should touch it.
    """
    import errno
    import ipaddress
    import socket

    marker = request.node.get_closest_marker("network_allowed")
    allowed_hosts = {str(h).lower() for h in (marker.args if marker else ())}
    resolved: set[str] = set()      # addresses an allowed host resolved to
    violations: list[str] = []

    def _is_loopback(host) -> bool:
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        host = str(host).lower().split("%")[0]
        if host == "localhost":
            return True
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return False
        mapped = getattr(ip, "ipv4_mapped", None)
        return (mapped or ip).is_loopback

    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def getaddrinfo(host, *a, **k):
        # `None` is a passive lookup (binding a server), not a destination.
        if host is None or _is_loopback(host):
            return real_getaddrinfo(host, *a, **k)
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if str(host).lower() in allowed_hosts:
            infos = real_getaddrinfo(host, *a, **k)
            resolved.update(i[4][0] for i in infos)
            return infos
        violations.append(f"getaddrinfo({host!r})")
        raise socket.gaierror(
            socket.EAI_NONAME,
            f"the behaviour suite is hermetic: refused to resolve {host!r}. "
            "Stub the call that reaches it; loopback is allowed.")

    def _permitted(self, address) -> bool:
        if self.family == socket.AF_UNIX or isinstance(address, (str, bytes)):
            return True
        host = address[0]
        return (_is_loopback(host) or str(host) in resolved
                or str(host).lower() in allowed_hosts)

    def connect(self, address, *a, **k):
        if _permitted(self, address):
            return real_connect(self, address, *a, **k)
        violations.append(f"connect({address[0]!r})")
        raise OSError(errno.ENETUNREACH,
                      f"the behaviour suite is hermetic: refused to connect to "
                      f"{address[0]!r}. Stub the call that reaches it.")

    def connect_ex(self, address, *a, **k):
        if _permitted(self, address):
            return real_connect_ex(self, address, *a, **k)
        violations.append(f"connect_ex({address[0]!r})")
        return errno.ENETUNREACH

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)

    yield violations

    assert not violations, (
        "this test reached beyond loopback, and whatever caught the OSError "
        "hid it from the test body: " + "; ".join(violations) + ". Stub the "
        "call that reaches the network (stub_llm for the provider). If it "
        "truly needs one host, mark it @pytest.mark.network_allowed(host, "
        "reason=...) -- that is a decision to defend, not a way to go green."
    )


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
