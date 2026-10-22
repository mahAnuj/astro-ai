"""The socket guard in `conftest._no_outbound_sockets`, shown to bite (#449).

A guard nobody has watched fail is a docstring. `_no_outbound_http` was one for
as long as the LLM client used `httpx`: it was correct, and aimed at the wrong
layer, and the suite reported itself hermetic while two tests reached a live
provider. So these drive the REAL fixture rather than a copy of its rules:

  * a non-loopback lookup and connect are refused AND recorded;
  * the failure survives a caller that swallows the `OSError` -- which is the
    whole reason the guard records and asserts at teardown instead of merely
    raising, since the LLM client, `ops_data._fetch` and most routes degrade
    on an exception;
  * loopback and AF_UNIX stay open, because `test_hindi_surface_gate.py` runs
    its own server;
  * `network_allowed` opens ONE named host and nothing else.

Nothing here sends a packet, and none reaches the real socket layer: refusals
happen before it, and where the guard LETS a call through (the marker cases)
the function underneath is a stand-in installed by `underfloor`, so "allowed"
is observed as "the stand-in was reached" rather than as a connection.
`203.0.113.0/24` is TEST-NET-3 (RFC 5737), never routed -- belt and braces. A
socket spy over the suite therefore sees only the one deliberate exception.

`scripts/mutate_behaviour_suite.py` removes the recording, the teardown
assertion and the marker's scope in turn, and each must turn this file red.
"""
from __future__ import annotations

import errno
import os
import shutil
import socket
import tempfile

import pytest

pytest_plugins = ["pytester"]

_NOT_ROUTED = "203.0.113.7"
_OTHER = "203.0.113.8"


def test_a_non_loopback_lookup_and_connect_are_refused_and_recorded(
        _no_outbound_sockets):
    violations = _no_outbound_sockets

    with pytest.raises(OSError):
        socket.getaddrinfo(_NOT_ROUTED, 443)
    with socket.socket() as s, pytest.raises(OSError) as exc:
        s.connect((_NOT_ROUTED, 443))
    assert exc.value.errno == errno.ENETUNREACH
    with socket.socket() as s:
        assert s.connect_ex((_NOT_ROUTED, 443)) == errno.ENETUNREACH

    assert violations == [
        f"getaddrinfo({_NOT_ROUTED!r})",
        f"connect({_NOT_ROUTED!r})",
        f"connect_ex({_NOT_ROUTED!r})",
    ]
    # Cleared so this test's own teardown passes. Without this line the guard
    # would, correctly, fail the test that just proved it works.
    violations.clear()


#: macOS `sun_path` is 104 bytes; Linux allows 108. Asserted rather than
#: trusted because the number is the whole reason this test binds where it does.
_SUN_PATH_MAX = 104


def test_loopback_and_unix_sockets_stay_open(_no_outbound_sockets):
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        socket.getaddrinfo("localhost", port)
        with socket.socket() as client:
            client.connect(("127.0.0.1", port))

    # NOT pytest's `tmp_path` (#472). On macOS that is already 127 bytes --
    # `/var/folders/_z/3m0wb73157nczwxzppyv3mb40000gn/T/pytest-of-<user>/
    # pytest-N/<test-name>0/s` -- against a 104-byte `sun_path`, so `bind`
    # raised "AF_UNIX path too long" for every macOS developer from the day
    # this file landed. The Linux runner's `/tmp/pytest-of-runner/...` fits
    # under its 108, so CI was green and only local runs were red. That is the
    # worst arrangement available: `uv run pytest` is what CLAUDE.md asks
    # everyone to run before handing work back, and a suite that is always red
    # for an unrelated reason gets ignored -- which is what this guard exists
    # to prevent.
    #
    # `socket.socketpair()` would drop the filesystem entirely, and #472
    # proposed it, but it never calls `connect` -- and an AF_UNIX `connect`
    # being let through is the entire assertion here, since the guard hooks
    # `socket.socket.connect`. It would turn this case into a no-op that still
    # passed. A short directory keeps `bind` and `connect` real.
    sock_dir = tempfile.mkdtemp(prefix="hermetic-")
    try:
        path = os.path.join(sock_dir, "s")
        assert len(path.encode()) <= _SUN_PATH_MAX, (
            f"AF_UNIX bind path is {len(path.encode())} bytes, over the "
            f"{_SUN_PATH_MAX}-byte macOS limit: {path!r}. Bind under a short "
            f"temp root; this is #472 returning."
        )
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(path)
            server.listen(1)
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(path)
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)

    assert _no_outbound_sockets == []


@pytest.fixture
def underfloor(monkeypatch):
    """Stand-ins for the real socket calls, installed BENEATH an inner guard.

    The inner run's guard captures whatever is installed when it sets up, so
    these become its "real" functions: a call the guard lets through lands here
    and is recorded in the returned list, instead of reaching a network.
    """
    reached: list[tuple[str, str]] = []

    def getaddrinfo(host, port=0, *a, **k):
        reached.append(("getaddrinfo", host))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]

    def connect(self, address, *a, **k):
        reached.append(("connect", address[0]))

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)
    return reached


def _inner_run(pytester, body: str):
    """Run `body` as a test under this suite's REAL conftest, in-process."""
    from pathlib import Path

    pytester.makeconftest((Path(__file__).parent / "conftest.py").read_text())
    pytester.makeini("[pytest]\nmarkers =\n    network_allowed(*hosts, reason)\n")
    pytester.makepyfile(f"import socket\nimport pytest\n\n{body}")
    return pytester.runpytest_inprocess("-p", "no:cacheprovider")


def test_a_swallowed_refusal_still_fails_the_test(pytester, underfloor):
    """The shape the guard exists for: the OSError is caught one frame up.

    Without the teardown assertion this inner test PASSES, which is exactly how
    the two LLM-reaching tests stayed green behind `except Exception`.
    """
    result = _inner_run(pytester, f'''
def test_degrades_gracefully():
    try:
        socket.getaddrinfo("{_NOT_ROUTED}", 443)
        socket.socket().connect(("{_NOT_ROUTED}", 443))
    except OSError:
        pass            # what the LLM client, `_fetch` and the routes do
''')
    outcomes = result.parseoutcomes()
    assert outcomes.get("passed") == 1 and outcomes.get("errors") == 1, (
        result.stdout.str())
    result.stdout.fnmatch_lines(["*reached beyond loopback*"])
    assert underfloor == [], "a refused call still reached the socket layer"


def test_the_marker_opens_only_the_host_it_names(pytester, underfloor):
    result = _inner_run(pytester, f'''
@pytest.mark.network_allowed("{_NOT_ROUTED}", reason="x")
def test_named_host_only():
    socket.getaddrinfo("{_NOT_ROUTED}", 443)
    socket.socket().connect(("{_NOT_ROUTED}", 443))
    for other in ("{_OTHER}",):
        with pytest.raises(OSError):
            socket.getaddrinfo(other, 443)
        with pytest.raises(OSError):
            socket.socket().connect((other, 443))
''')
    # The named host got through to the floor, in both calls...
    assert underfloor == [("getaddrinfo", _NOT_ROUTED), ("connect", _NOT_ROUTED)]
    # ...the other was refused AND recorded, so the test that passed still errs.
    outcomes = result.parseoutcomes()
    assert outcomes.get("passed") == 1 and outcomes.get("errors") == 1, (
        result.stdout.str())
    result.stdout.fnmatch_lines([f"*getaddrinfo('{_OTHER}')*connect('{_OTHER}')*"])


def test_a_test_that_stays_on_loopback_is_not_flagged(pytester, underfloor):
    result = _inner_run(pytester, '''
def test_quiet():
    socket.getaddrinfo("localhost", 80)
''')
    assert result.parseoutcomes() == {"passed": 1}, result.stdout.str()
    assert underfloor == [("getaddrinfo", "localhost")]
