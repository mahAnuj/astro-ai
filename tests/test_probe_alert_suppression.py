"""`X-Bhagya-Probe` suppresses the four PII-free owner alerts and nothing else (#618).

THE DEFECT. `verify-production.yml` POSTs two real user forms against the live
site on every push to `main`, and both fired the owner's Telegram alert as if a
visitor had submitted them -- 4-6 identical alerts a day, byte-identical,
because the probe's input is hardcoded so the 8-hex key never moves.

The probes are correct and cannot be GETs (#172, #216/#218) and a static gate
cannot replace them: it guards the SOURCE, while the probe proves the DEPLOYED
BYTES carry the disclosure -- which matters while #253 is open, a service
worker serving a stale stylesheet since 2026-08-16. So the probe is right;
alerting a person for it is the bug.

WHY THE SCOPE IS WHAT THESE TESTS ARE MOSTLY ABOUT

The header is UNAUTHENTICATED. Anyone can send it. That is fine for an alert
carrying a diagnostic and a keyed hash, and not fine for one carrying a
question, an email or a name. So the rule is an ALLOW-LIST, and the tests that
matter are the ones proving a PII-carrying formatter is NOT suppressible --
`test_a_PII_carrying_alert_is_never_suppressed` is the acceptance criterion the
issue puts third, and it is the one a careless later edit would break.

A deny-list would have been the obvious shape and is the wrong one: a formatter
added later would be suppressible by default, and the one that mattered would
be the one nobody remembered to list.

THE ALLOW-LIST IS CHECKED AGAINST `notify.py` ITSELF, not against a copy of its
contents in this file. `test_the_allow_list_matches_what_notify_documents`
reads that module's own docstring, so the two cannot drift apart silently --
which is the failure #628 had just produced in a different pair of files.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from astro_ai import probe

ROOT = pathlib.Path(__file__).resolve().parent.parent


class _Req:
    """Enough of a Starlette request for this module, with case-insensitive headers.

    Real `request.headers` is case-insensitive, and that is load-bearing rather
    than convenient: HTTP header names are case-insensitive and a proxy may
    normalise them, so a case-sensitive lookup would work in tests and fail
    behind one.
    """

    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = _CI(headers or {})


class _CI(dict):
    def get(self, key, default=None):          # noqa: D102
        lower = {k.lower(): v for k, v in self.items()}
        return lower.get(key.lower(), default)


def _probe_req(value: str = probe.PROBE_VALUE, *, name: str = probe.PROBE_HEADER) -> _Req:
    return _Req({name: value})


# --------------------------------------------------- it suppresses the four

@pytest.mark.parametrize("event", sorted(probe.SUPPRESSIBLE))
def test_each_PII_FREE_alert_is_suppressed_for_a_declared_probe(event):
    assert probe.suppresses_owner_alert(_probe_req(), event) is True


@pytest.mark.parametrize("header_name", [
    "X-Bhagya-Probe", "x-bhagya-probe", "X-BHAGYA-PROBE", "x-Bhagya-probe",
])
def test_the_header_name_is_matched_case_insensitively(header_name):
    """HTTP header names are case-insensitive and a proxy may rewrite them."""
    assert probe.suppresses_owner_alert(
        _probe_req(name=header_name), "numerology_computed") is True


# ------------------------------------------- and nothing else, ever (AC 3)

@pytest.mark.parametrize("event", [
    "ask_submitted", "new_signin", "subscribed", "feedback_submitted",
])
def test_a_PII_carrying_alert_is_never_suppressed(event):
    """ACCEPTANCE CRITERION 3, and the reason the allow-list exists.

    `notify.py` documents these as carrying a question, an email or a name.
    The header is unauthenticated, so honouring it here would let anyone
    silence the alert for their own real submission -- hiding activity from the
    owner, which is strictly worse than the noise this change removes.
    """
    assert probe.suppresses_owner_alert(_probe_req(), event) is False


@pytest.mark.parametrize("event", [
    "muhurat_computed", "error_seen", "", "KUNDLI_GENERATED",
    "kundli_generated ", "notify", "deploy_seen",
])
def test_an_event_name_not_on_the_list_is_never_suppressed(event):
    """Including near-misses: trailing space, wrong case, a plausible new name.

    A formatter added next month is NOT suppressible until someone adds it
    deliberately, which is the whole difference between an allow-list and a
    deny-list.
    """
    assert probe.suppresses_owner_alert(_probe_req(), event) is False


# ----------------------------------------- the header itself must be exact

@pytest.mark.parametrize("value", [
    "", "0", "1", "true", "VERIFY-PRODUCTION", "verify-production ",
    "verify", "verify-production-x", "some-other-probe",
])
def test_only_the_EXACT_value_suppresses(value):
    """Not a truthiness test and not a prefix.

    `X-Bhagya-Probe: 0` reads as "a probe" under truthiness, and
    `verify-production-x` passes a prefix test. The value says WHICH caller it
    is, so a different one must not inherit this suppression.
    """
    assert probe.suppresses_owner_alert(_probe_req(value), "kundli_generated") is False


def test_no_header_at_all_sends_the_alert():
    assert probe.suppresses_owner_alert(_Req(), "kundli_generated") is False


# ------------------------------------- every failure falls toward ALERTING

@pytest.mark.parametrize("bad", [None, object(), "not a request", 7, []])
def test_an_unusable_request_sends_the_alert_rather_than_raising(bad):
    """A module that decides whether to notify must never 500 a user request.

    `notify` itself log-and-swallows for the same reason. Returning False means
    the alert fires: noise, not a swallowed visitor.
    """
    assert probe.suppresses_owner_alert(bad, "kundli_generated") is False


def test_a_headers_mapping_that_RAISES_sends_the_alert():
    class _Boom:
        @property
        def headers(self):
            raise RuntimeError("header backend down")

    assert probe.suppresses_owner_alert(_Boom(), "matching_done") is False


# ------------------------------------------------ the rule lives ONCE (AC 4)

def test_the_allow_list_matches_what_notify_documents():
    """Read from `notify.py`, not restated here, so the two cannot drift.

    That module's docstring names the four PII-free alerts explicitly. #628 was
    exactly this failure in another pair of files -- one fact, two copies, two
    answers for weeks -- so the agreement is asserted rather than assumed.
    """
    doc = (ROOT / "src" / "astro_ai" / "notify.py").read_text(encoding="utf-8")
    header = doc.split('"""', 2)[1]
    documented = set(re.findall(r"`(\w+)`", header.split("carry NO PII")[0]))
    assert probe.SUPPRESSIBLE <= documented, (
        f"probe.SUPPRESSIBLE names {sorted(probe.SUPPRESSIBLE - documented)}, which "
        f"notify.py's own docstring does not list as PII-free")
    assert len(probe.SUPPRESSIBLE) == 4


def _code(text: str) -> str:
    """`text` with comment-only lines dropped.

    Scanning raw source would match the call sites' own PROSE -- both name
    `X-Bhagya-Probe` in a comment to say what the guard is for. This file's
    first draft did exactly that and the test failed on its own rationale,
    which is the trap `tests/test_qa_on_green.py` records in the same words:
    "a guard that fires on its own rationale is noise, and noise is how a real
    hit gets ignored."
    """
    return "\n".join(ln for ln in text.splitlines()
                      if not ln.lstrip().startswith("#"))


def test_neither_route_reimplements_the_rule():
    """ACCEPTANCE CRITERION 4. The header is read in ONE source file.

    Two call sites each testing the header themselves is how one of them keeps
    an allow-list that `notify.py` has moved past.
    """
    hits = sorted(p.name for p in (ROOT / "src").rglob("*.py")
                  if probe.PROBE_HEADER in _code(p.read_text(encoding="utf-8")))
    assert hits == ["probe.py"], (
        f"{probe.PROBE_HEADER} is read in {hits}; it belongs in probe.py alone")


def test_the_routes_still_SAY_what_the_guard_is_for():
    """The other half of the one above, and not redundant with it.

    A reader at the call site has to learn why an alert is conditional without
    opening another file. Dropping the comment would make the test above pass
    more easily, so this makes that direction cost something too.
    """
    for route in ("numerology.py", "kundli.py"):
        src = (ROOT / "src" / "astro_ai" / "routes" / route).read_text(encoding="utf-8")
        assert "#618" in src, f"{route} does not say why its alert is conditional"


@pytest.mark.parametrize("route,event", [
    ("numerology.py", "numerology_computed"),
    ("kundli.py", "kundli_generated"),
])
def test_each_route_guards_its_alert_through_the_helper(route, event):
    """The call site asks `probe`, and asks about ITS OWN event.

    Passing another event's name would suppress the wrong alert, and both are
    on the allow-list so nothing else would catch it.
    """
    src = (ROOT / "src" / "astro_ai" / "routes" / route).read_text(encoding="utf-8")
    assert f'probe.suppresses_owner_alert(request, "{event}")' in src


def test_the_kundli_activity_EVENT_is_not_suppressed():
    """Scoped to the alert channel, deliberately.

    `events.record` is the activity log; the fix is for the thing that was
    paging a person. Suppressing the event too would quietly change what
    /admin/activity counts, which is a different decision and is noted on #618
    rather than taken here.
    """
    lines = (ROOT / "src" / "astro_ai" / "routes" / "kundli.py").read_text(
        encoding="utf-8").splitlines()
    g = next(i for i, l in enumerate(lines)
             if 'probe.suppresses_owner_alert(request, "kundli_generated")' in l)
    r = next(i for i, l in enumerate(lines) if i > g and "events.record(" in l)

    def indent(i: int) -> int:
        return len(lines[i]) - len(lines[i].lstrip())

    # INDENTATION, not a keyword count. The first version sliced from the call
    # expression -- which is AFTER the `if` keyword on that line -- and then
    # counted `if `, so it read 0 and failed on correct code. Nesting is a
    # question about indentation, so it is asked that way.
    assert indent(r) <= indent(g), (
        f"events.record (line {r + 1}, indent {indent(r)}) is nested inside the "
        f"suppression guard (line {g + 1}, indent {indent(g)})")


# ------------------------------- through a REAL request (AC 1 and AC 2)
#
# The source-grep cases above cannot catch an INVERTED guard: dropping the
# `not` leaves the asserted string intact while alerting only for probes and
# silencing every visitor. These two drive the live route instead, which is
# also what the issue's first two acceptance criteria actually say.

@pytest.fixture
def sink(monkeypatch):
    """Capture what would reach Telegram, bypassing env config and dedup.

    Patches `notify.notify` itself, the way `tests/test_privacy_relay.py` does:
    every formatter resolves it from module globals at call time, so this
    catches the alert however it was composed.
    """
    from astro_ai import notify

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        notify, "notify", lambda text, *, dedup_key="": sent.append((text, dedup_key)))
    return sent


_PROBE_FORM = {"name": "CI Check", "birth_date": "1988-05-14"}


def test_a_probe_POST_to_numerology_fires_NO_owner_alert(client, sink):
    """ACCEPTANCE CRITERION 1, with the verifier's own hardcoded input.

    `1988-05-14` -> 1+9+8+8+0+5+1+4 = 36 -> life path 9, Chaldean: the exact
    alert the owner was receiving 4-6 times a day.
    """
    resp = client.post("/numerology", data=_PROBE_FORM,
                       headers={probe.PROBE_HEADER: probe.PROBE_VALUE})
    assert resp.status_code == 200, "the probe must still get its page"
    assert sink == [], f"the probe still alerted: {sink}"


def test_a_normal_POST_to_numerology_STILL_fires_the_alert(client, sink):
    """ACCEPTANCE CRITERION 2, and the case an inverted guard breaks.

    This is the half that cannot be checked by reading the source: `if not
    probe.suppresses_owner_alert(...)` and `if probe.suppresses_owner_alert(...)`
    both contain the string the grep tests assert.
    """
    resp = client.post("/numerology", data=_PROBE_FORM)
    assert resp.status_code == 200
    assert len(sink) == 1, f"a real submission did not alert: {sink}"
    assert "life path" in sink[0][0]


def test_a_WRONG_probe_value_on_a_real_route_still_alerts(client, sink):
    """The route inherits the helper's exactness rather than re-deciding it."""
    client.post("/numerology", data=_PROBE_FORM,
                headers={probe.PROBE_HEADER: "some-other-caller"})
    assert len(sink) == 1, "an unrecognised probe value suppressed the alert"
