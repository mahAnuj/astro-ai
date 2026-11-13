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

#: A page every one of the gate's own checks passes: Devanagari well above
#: each floor, no English sentinel, the localised nav label present. Used
#: wherever a test must isolate ONE guard -- if the page itself were
#: rejectable, the test could not say which guard did the rejecting.
GOOD_HINDI = (
    '<html><body><nav aria-label="Main">राशिफल</nav>'
    '<main>' + 'आज का राशिफल ' * 30 + '</main></body></html>'
).encode()


#: The same page without its top nav. Real 503s look like this: error.html
#: renders no <nav aria-label="Main"> (measured 2026-11-13 on both Hindi
#: degraded cards), so a 503 must be accepted without one.
GOOD_HINDI_NO_NAV = (
    '<html><body><main>' + 'आज का राशिफल ' * 30 + '</main></body></html>'
).encode()

HUB = "/hi/rashifal"


def _page(code, body):
    """Handler: valid /health, and `body` at `code` on every page."""
    return lambda path: (200, HEALTH) if path == "/health" else (code, body)


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

    # Port 0 on the server itself: no bind-close-rebind window (#433).
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def stop():
        srv.shutdown()
        srv.server_close()      # shutdown() alone leaves the listening fd open

    return f"http://127.0.0.1:{srv.server_address[1]}", stop


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
    def body(path):
        return (404, b"not me") if path == "/health" else (200, GOOD_HINDI)
    assert _run(body) == 2


@pytest.mark.parametrize("code", [404, 500, 502])
def test_a_page_status_the_gate_cannot_read_is_not_a_pass(code):
    """200 is a rendered page, 503 the documented degraded card. Nothing else is.

    THE PAGE HERE IS PERFECTLY GOOD HINDI, and that is the whole design of the
    fixture. The first version served `<html>gone</html>`, so the empty-<main>
    guard rejected it too -- and the mutation widening the allow-list to
    `(200, 503, 404, 500)` still produced exit 2. *** MISSED ***, caught by a
    different guard than the one under test, reported by both the local sweep
    and CI. With a full Devanagari <main> the ONLY thing that can reject this
    response is its status code.
    """
    def body(path):
        return (200, HEALTH) if path == "/health" else (code, GOOD_HINDI)
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
    def body(path):
        return (200, HEALTH) if path == "/health" else (code, GOOD_HINDI)
    assert _run(body) == 0


# ---- #433: the guards QA round 1 on #424 found unpinned -------------------


@pytest.mark.parametrize("health", [
    # Each of these violates exactly ONE thing /health must satisfy, so the
    # one test that sends them cannot be passed by a gate that checks the
    # other. The old single fixture (404 "not me") violated everything at once.
    pytest.param(b'{"status":"ok","service":"grafana"}', id="ok-token-but-not-our-json"),
    pytest.param(b'{"ok":true,"service":"grafana"}', id="ok-true-but-no-revision"),
    pytest.param(b'{"revision":"r","build_sha":null}', id="revision-but-no-ok"),
    pytest.param(b'{"ok":false,"revision":"r"}', id="not-ok"),
    pytest.param(b"ok revision", id="not-json"),
])
def test_health_200_with_foreign_json_is_not_this_app(health):
    """The identity clause alone: status 200, so only the BODY can reject it.

    `{"status":"ok","service":"grafana"}` passed the old `'"ok"' in body`
    check; the revision-less and ok-less bodies each pin one half of the new one.
    """
    def body(path):
        return (200, health) if path == "/health" else (200, GOOD_HINDI)
    assert _run(body) == 2


def test_health_503_with_our_own_json_is_not_a_pass():
    """The status clause alone: the body is exactly the app's, so only the code
    can reject it. routes/health.py answers 200 on every tier."""
    def body(path):
        return (503, HEALTH) if path == "/health" else (200, GOOD_HINDI)
    assert _run(body) == 2


def test_health_with_a_null_build_sha_is_still_this_app():
    """`revision` must not be so strict that the weaker tier is rejected."""
    def body(path):
        return (200, b'{"ok":true,"revision":"local","build_sha":null}') \
            if path == "/health" else (200, GOOD_HINDI)
    assert _run(body) == 0


def test_an_empty_main_on_a_503_is_not_a_pass():
    """Guard 3 is not 200-only. With the guard exempted on 503 the page falls
    through to DEGRADED_FLOOR and exits 1, so this asserts 2 -- the rejection
    must come from the guard under test, not from the floor behind it."""
    assert _run(_page(503, b"<html><body><main>   </main></body></html>")) == 2


def test_a_503_that_is_not_hindi_fails_the_degraded_floor():
    """Defect F9 was never enforced: thirteen 503s whose whole <main> is
    `<p>Shubh Bhagya</p>` printed devanagari=0% and exited 0. Visible text is
    present, so the empty-<main> guard passes; only the floor can reject it."""
    assert _run(_page(503, b"<html><body><main><p>Shubh Bhagya</p></main></body></html>")) == 1


def test_a_half_english_503_fails_the_degraded_floor(capsys):
    """DEGRADED_FLOOR is a number, not a presence check. This card has
    Devanagari, so it is above zero, and no run of four ASCII words and no
    sentinel, so only the floor can reject it. The real degraded cards measure
    93% and 96% (see DEGRADED_FLOOR)."""
    card = "आज Vedic का Horoscope राशिफल Yoga " * 4
    text = gate._visible(card)
    assert gate._english_prose(text) == [] and not [s for s in gate.SENTINELS if s in text]
    assert 0 < gate._devanagari_share(text) < gate.DEGRADED_FLOOR
    assert _run(_page(503, f"<html><body><main>{card}</main></body></html>".encode())) == 1
    assert "degraded floor" in capsys.readouterr().out


def test_a_503_needs_no_nav_but_a_200_does():
    """error.html renders no top nav, so requiring one on a 503 would fail every
    legitimate degraded page. A 200 without it is a lost call site."""
    assert _run(_page(503, GOOD_HINDI_NO_NAV)) == 0
    assert _run(_page(200, GOOD_HINDI_NO_NAV)) == 1


def test_a_present_devanagari_nav_label_passes():
    assert _run(_page(200, GOOD_HINDI)) == 0


def test_an_english_label_in_the_nav_fails_even_beside_the_hindi_one():
    page = GOOD_HINDI.replace("राशिफल</nav>".encode(), "राशिफल Matching</nav>".encode())
    assert page != GOOD_HINDI
    assert _run(_page(200, page)) == 1


def test_the_nav_check_reads_the_page_not_the_table(capsys):
    """Finding 5: it tested only the i18n value, so deleting <nav> stayed green.
    The nav is present here but carries another label, so presence of the
    element alone is not enough either."""
    page = GOOD_HINDI.replace("राशिफल</nav>".encode(), "कुंडली</nav>".encode())
    assert _run(_page(200, page)) == 1
    assert "nav label" in capsys.readouterr().out


def test_the_pass_line_does_not_claim_the_floor_for_pages_that_503(capsys):
    """Finding 3. Thirteen 503s must read `on the 0 that rendered 200`; the
    over-claim #424 removed was `floor applied` for all thirteen."""
    from astro_ai import hindi_pages
    n = len(hindi_pages.HINDI_PUBLISHED)

    assert _run(_page(503, GOOD_HINDI)) == 0
    out = capsys.readouterr().out
    assert "on the 0 that rendered 200" in out, out
    assert f"on the {n} that served 503" in out, out

    def mixed(path):
        if path == "/health":
            return 200, HEALTH
        return (200 if path == HUB else 503), GOOD_HINDI
    assert _run(mixed) == 0
    out = capsys.readouterr().out
    assert "on the 1 that rendered 200" in out, out
    assert f"on the {n - 1} that served 503" in out, out


def test_an_unreadable_page_does_not_discard_a_real_leak(capsys):
    """Finding 8. An English leak on the hub plus a 404 on one rashi page used to
    exit 2 on whichever came first and, when the 404 did, never print the leak.
    Exit 1: a gate that found a defect ran; the 404 is still listed."""
    leak = ('<nav aria-label="Main">राशिफल</nav><main>'
            + 'आज का राशिफल ' * 30
            + ' great day for all twelve signs </main>').encode()

    def body(path):
        if path == "/health":
            return 200, HEALTH
        if path == HUB:
            return 200, leak
        if path == "/hi/rashifal/leo":
            return 404, b"gone"
        return 200, GOOD_HINDI
    assert _run(body) == 1
    out = capsys.readouterr().out
    assert "great day for all twelve signs" in out, out
    assert "/hi/rashifal/leo answered 404" in out, out


def test_unreadable_pages_alone_still_exit_2_and_are_all_listed(capsys):
    def body(path):
        if path == "/health":
            return 200, HEALTH
        return (404, b"gone") if path in ("/hi/rashifal/leo", "/hi/rashifal/aries") \
            else (200, GOOD_HINDI)
    assert _run(body) == 2
    out = capsys.readouterr().out
    assert "/hi/rashifal/leo answered 404" in out and "/hi/rashifal/aries answered 404" in out, out
