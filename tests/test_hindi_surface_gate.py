"""The Hindi-surface gate must not report PASS when it read nothing.

MEASURED 2026-10-19, before the fix these tests pin: pointed at a server that
answers 500 on every path -- a foreign process was squatting the default port
that day -- `scripts/verify_hindi_surface.py` printed

    /hi/rashifal  [500] devanagari=0% sentinels=0 prose=0 nav=0    (x13)
    PASS (13 Hindi URLs: no English sentinel in <main>, Devanagari above each
          page type's floor)

and exited 0, with the final line asserting a floor it had never applied.

WHY IT COULD NOT FAIL. Every check in that gate searches <main> for something
BAD -- an English sentinel, English prose, a missing nav label. A 500 has no
<main> at all, so each search finds nothing and each check "passes". The one
check that looks for something GOOD, the Devanagari floor, was already gated
on `code == 200` and so skipped itself. A gate built entirely from negatives
passes hardest when handed nothing, which is the opposite of what a gate is
for, and it is the same class as the vacuous fixtures found on #412, #418 and
#419 in the same week: the thing under test was never reached.

These tests drive the gate's own `main()` against a stub server on an
ephemeral port, so they exercise the real argument parsing, the real HTTP
path and the real exit codes. Nothing here stubs the gate's internals; a test
that reimplemented its logic would be the defect it is testing for.
"""
from __future__ import annotations

import http.server
import importlib.util
import socket
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "verify_hindi_surface", ROOT / "scripts" / "verify_hindi_surface.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

HEALTH = b'{"ok":true,"revision":"stub","build_sha":null}'


def _serve(handler_body):
    """A stub server on an ephemeral port. Returns (base_url, shutdown)."""
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            code, body = handler_body(self.path)
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", srv.shutdown


def _run(handler_body):
    base, stop = _serve(handler_body)
    argv = sys.argv
    sys.argv = ["verify_hindi_surface.py", "--url", base]
    try:
        return gate.main()
    finally:
        sys.argv = argv
        stop()


def test_a_server_that_500s_on_everything_is_not_a_pass():
    """The exact shape that printed PASS: 500 on every path, /health included.

    2, not 1. The gate did not find a problem -- it never ran, and the two
    must not be the same exit code, because pr-gates treats 2 as "SKIPPED
    (exit 2) -- the check did not run, which is not a pass" and would
    otherwise count this as coverage it does not have.
    """
    assert _run(lambda p: (500, b"<html><body>Internal Server Error</body></html>")) == 2


def test_a_foreign_server_on_the_port_is_not_this_app():
    """A port is not an identity. /health is this app's own route.

    The stub answers 200 with a perfectly valid page on every other path, so
    only the health probe can tell the difference -- which is the point: a
    different app on the port would otherwise be measured as if it were ours.
    """
    page = ("<html><body><main>" + "राशिफल " * 40
            + "</main></body></html>").encode()
    def body(path):
        return (404, b"not me") if path == "/health" else (200, page)
    assert _run(body) == 2


def test_a_page_status_the_gate_cannot_read_is_not_a_pass():
    """200 is a rendered page, 503 the documented degraded card. 404 is neither."""
    def body(path):
        return (200, HEALTH) if path == "/health" else (404, b"<html>gone</html>")
    assert _run(body) == 2


def test_an_empty_main_is_not_a_pass():
    """An empty region satisfies every negative check in the gate at once."""
    def body(path):
        return (200, HEALTH) if path == "/health" else (
            200, b"<html><body><main>   </main></body></html>")
    assert _run(body) == 2


@pytest.mark.parametrize("code", [200, 503])
def test_a_readable_page_is_still_read(code):
    """The guards must not swallow the gate's actual job.

    Hindi prose in <main>, no English sentinel: the gate is expected to reach
    its own checks and return 0. Without this, every test above would pass on
    a gate that had simply been made to exit 2 unconditionally -- which is the
    failure mode a file full of negative assertions invites.
    """
    page = ("<html><body><nav aria-label=\"Main\">राशिफल</nav>"
            "<main>" + "आज का राशिफल " * 30
            + "</main></body></html>").encode()
    def body(path):
        return (200, HEALTH) if path == "/health" else (code, page)
    assert _run(body) == 0
