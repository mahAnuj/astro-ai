"""PII egress sweep (#744), server-side sinks: what leaves the process.

Each scenario in `scripts/verify_pii_egress.py` drives REAL routes with a sentinel
planted in every personal field (a real sign-in through POST /auth/google, a saved
chart in the real cookie), with a recorder at every module boundary: Telegram, the
storage blobs (events, users, subscribers, feedback, snapshots, the durable LLM
cache), the Brevo payload, the LLM messages, the logs and the geocoder. No network,
no LLM, no GCS. The policy of what may go where is `POLICY` and friends in that
script; this file says whether the app obeys it.

The page <title> and the other things a browser's analytics scripts read are the
SAME scenarios judged by `tests/test_pii_egress_analytics.py`; they are excluded
here so a known gap there cannot mask a regression here.

Three kinds of assertion, because each catches something the others cannot:

  * policy: no sentinel of a class the sink does not allow;
  * `expects`: the scenario produced at least what it declared. The dosha and
    numerology alerts sit inside `try/except Exception: pass`, so a signature
    change deletes the alert silently, and "nothing leaked" stays true of an alert
    that no longer exists. `test_privacy_relay.py` asserts "exactly once" for the
    same reason; this generalises it;
  * the scenario set itself is pinned, so deleting one is a failure.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_pii_egress.py"
if "verify_pii_egress" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("verify_pii_egress", _SCRIPT)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["verify_pii_egress"] = _mod
    _spec.loader.exec_module(_mod)
pii = sys.modules["verify_pii_egress"]

SCENARIOS = (
    "reading-kundli", "matching", "manglik-dosha", "sade-sati-dosha", "kaal-sarp-dosha",
    "numerology", "numerology-compatibility", "ask", "subscribe", "feedback", "snapshot",
    "personal-readings", "rashifal-is-shared", "dasha", "muhurat-personal",
    "email-my-reading", "llm-exhausted", "brevo-fails", "place-rejected",
)
DOSHA = ("manglik-dosha", "sade-sati-dosha", "kaal-sarp-dosha")
BIRTH = {"name", "dob", "tob", "city", "region"}


def _server(e):
    """Violations at server-side sinks only (the page surfaces are the other file)."""
    return {v for v in e.violations() if not v[0].startswith("analytics:")}


@pytest.fixture
def run(monkeypatch, caplog, tmp_path):
    return lambda name: pii.run_scenario(name, monkeypatch, caplog, tmp_path)


def test_the_scenario_set_is_the_one_the_sweep_declares():
    assert set(SCENARIOS) == set(pii.SCENARIOS), (
        "a scenario was added or removed in scripts/verify_pii_egress.py without "
        "this list: a deleted scenario is a flow nobody checks any more")


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_scenario_stays_inside_the_policy_and_produced_what_it_declared(run, name):
    e = run(name)
    assert e.check_expects(pii.SCENARIOS[name].expects) == [], (
        "the scenario captured less than it declared, so 'nothing leaked' proves nothing")
    assert _server(e) == set(), (
        f"{name}: a sentinel reached a sink the policy does not allow "
        f"(sink, key, class): {sorted(_server(e))}")


@pytest.mark.parametrize("name", DOSHA)
def test_the_dosha_alerts_carry_no_birth_detail(run, name):
    """#255: a diagnostic (rashi names, a keyed hash), never an identity. The
    alert call sits inside `try/except: pass`; `expects` is what notices it gone."""
    e = run(name)
    assert e.check_expects(pii.SCENARIOS[name].expects) == []
    assert e.count("telegram") == 1 and e.count("llm") == 0
    text, dedup = e.telegram[-1]
    assert pii.classes_in(text + dedup) == set(), (text, dedup)


def test_the_kundli_event_carries_only_the_coarse_profile(run):
    """The activity log may hold the birth CITY and an age band, never the name,
    date, time or the full place (privacy.html, "Our 30-day activity log")."""
    e = run("reading-kundli")
    assert e.count("events") >= 1
    seen = {c for s, k, c in e.scan() if s == "events"}
    assert "city" in seen, "the coarse profile (city) is what keeps /admin/insights alive"
    assert seen <= pii.POLICY["events"].allow, seen - pii.POLICY["events"].allow
    assert not (seen & {"name", "dob", "tob", "region"})


def test_a_failed_llm_call_logs_and_alerts_no_birth_detail_or_question(run):
    """Every LLM failure path logs with a traceback and relays an alert; the
    question is in scope at the /ask one and must not reach either."""
    e = run("llm-exhausted")
    msgs = [r.getMessage() for r in e.log_records if r.name.startswith("astro_ai")]
    assert any("ask LLM generation failed" in m for m in msgs), (
        "the failure path did not log: the scenario no longer reaches it", msgs)
    for sink in ("log", "telegram", "events"):
        leaked = {c for s, _, c in e.scan() if s == sink} & (BIRTH | {"question"})
        assert not leaked, f"{leaked} reached the {sink} sink on an LLM failure"


def test_the_feedback_forward_carries_only_the_message_and_the_address(run):
    """The Referer of a visitor on /ask?q=... carries their question; the owner's
    copy of a feedback form must not grow it."""
    e = run("feedback")
    assert {pii.mail_purpose(s) for s, _ in e.mail} == {"feedback"}
    seen = {c for s, k, c in e.scan() if s == "mail"}
    assert seen == {"email", "message"}, seen


def test_the_shared_rashifal_prompt_carries_nothing_personal(run):
    """One reading is served to every visitor, so a signed-in visitor with a saved
    chart must still get exactly the prompt everyone gets."""
    e = run("rashifal-is-shared")
    assert e.count("llm:rashifal_single") >= 1
    assert pii.LLM_RULES["rashifal_single"].allow == frozenset()
    for route, payload in e.llm:
        assert route == "rashifal_single", route
        assert pii.classes_in(payload) == set(), payload[:300]


@pytest.mark.parametrize("name", ("reading-kundli", "snapshot", "ask", "subscribe",
                                  "email-my-reading"))
def test_no_storage_key_or_unlisted_blob_carries_a_sentinel(run, name):
    """Default-deny: only users.json, subscribers.json, feedback.json and snapshots
    may hold personal data, each of its own classes. Everything else (the durable
    natal cache, rashifal, llm_stats, a key nobody has written down) holds none,
    and no KEY NAME does either (a key built from the raw birth details would be
    the cache's own leak)."""
    e = run(name)
    assert e.writes, "the scenario wrote nothing to storage"
    bad = {v for v in e.violations() if v[0] in ("blob", "blobkey")}
    assert bad == set(), sorted(bad)
    unlisted = [k for k, _ in e.writes
                if not k.startswith("events/")
                and not any(k.startswith(p) for p, _ in pii.BLOB_RULES)]
    assert unlisted, "no unlisted key was written, so default-deny was not exercised"


def test_a_failed_welcome_mail_logs_the_address_and_nothing_else(run):
    """Pins today's behaviour (the log line names the recipient) so that a new flow
    logging something more is caught. privacy.html is silent on email in logs."""
    e = run("brevo-fails")
    seen = {c for s, _, c in e.scan() if s == "log"}
    assert seen == {"email"}, f"expected the address to be logged, and only that: {seen}"


def test_the_geocoder_is_only_ever_handed_a_place(run):
    e = run("reading-kundli")
    assert e.geocode, "the geocoder was never called"
    for place in e.geocode:
        assert pii.classes_in(place) <= pii.POLICY["geocode"].allow, place


def test_a_rejected_place_relays_no_place_and_no_name(run):
    """#255 T8: a ChartError message embeds the raw place. Class name only."""
    e = run("place-rejected")
    assert e.count("telegram") == 2
    for text, dedup in e.telegram:
        assert "ChartError" in text
        assert pii.classes_in(text + dedup) == set(), text
    assert {c for s, _, c in e.scan() if s in ("events", "log")} <= pii.POLICY["log"].allow


def test_the_sign_in_alert_is_checked_too(run):
    """Every signed-in scenario signs in through the real route first, so the
    sign-in alert and the account blob are inside the sweep. The Google profile
    name is empty by construction, so the alert shows '(no name)'."""
    e = run("matching")
    assert e.telegram and "New user signed up" in e.telegram[0][0]
    assert pii.classes_in(e.telegram[0][0]) == {"email"}
