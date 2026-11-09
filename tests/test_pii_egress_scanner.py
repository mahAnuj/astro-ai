"""The mechanics of the PII egress sweep (#744), with no app and no route.

`scripts/verify_pii_egress.py` holds the sentinels, the policy and the scanner;
`tests/test_pii_egress.py` and `tests/test_pii_egress_analytics.py` drive real
routes through it. These are the pure-function checks underneath, and each pins a
way the sweep itself could quietly stop working: a scanner that matches a clock
reading, a policy row widened, a default-deny that is no longer deny, an
`expects` guard that a silenced sink would walk past.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_pii_egress.py"
if "verify_pii_egress" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("verify_pii_egress", _SCRIPT)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["verify_pii_egress"] = _mod
    _spec.loader.exec_module(_mod)
pii = sys.modules["verify_pii_egress"]


# ─── the sentinels classify as themselves, and only themselves ──────────────

@pytest.mark.parametrize("value, expected", [
    (pii.NAME, {"name"}),
    (pii.B_NAME, {"name"}),
    (pii.DOB, {"dob"}),
    (pii.B_DOB, {"dob"}),
    (pii.TOB, {"tob"}),
    (pii.B_TOB, {"tob"}),
    (pii.PLACE, {"city", "region"}),
    (pii.B_PLACE, {"city", "region"}),
    (pii.EMAIL, {"email"}),
    (pii.QUESTION, {"question"}),
    (pii.MESSAGE, {"message"}),
])
def test_each_sentinel_is_one_class_and_not_another(value, expected):
    """If the partner's city shared a word with the partner's name, or the email
    with the name, a leak of one would be reported as the other and the policy
    row that allows one of them would hide the leak of the other."""
    assert pii.classes_in(value) == expected


def test_every_field_class_has_a_pattern():
    assert set(pii.FIELDS) == set(pii.FIELD_CLASSES)


# ─── the false-positive guards, each one paid for ───────────────────────────

@pytest.mark.parametrize("stamp", [
    "2026-11-09T21:06:47.123456",      # TIME 06:47 inside HH:MM:SS
    "2026-11-09T06:47:12+00:00",
    "2026-11-09T05:21:15.5",            # B_TIME 21:15 inside HH:MM:SS
    "2026-11-09T21:15:03",
    "ts 12:06:47",
])
def test_a_birth_time_is_not_matched_inside_a_clock_reading(stamp):
    """#437: `06:47` is a legitimate minute:second of every hour, so a bare
    substring scan failed for about two seconds an hour on a merge commit. The
    stamps are fabricated, so this does not depend on the clock."""
    assert "tob" not in pii.classes_in(stamp), stamp


def test_a_birth_time_on_its_own_is_matched():
    for text in ("born at 06:47", "time=06:47,", "21:15"):
        assert "tob" in pii.classes_in(text), text


@pytest.mark.parametrize("text", [
    "a1987b",
    "identity 0f1987c3d2e1a4b5c6d7e8f9a0b1c2d3",   # inside a 32-hex key
    "latency 0.1987s",
    "19870",
    "id 11987",
    "1987.5",
])
def test_a_year_is_not_matched_inside_a_hex_key_or_a_decimal(text):
    assert "dob" not in pii.classes_in(text), text


@pytest.mark.parametrize("text", ["born in 1987.", "(1990)", "March 14, 1987", "1987-03-14"])
def test_a_year_as_a_year_is_matched(text):
    assert "dob" in pii.classes_in(text), text


# ─── the policy ─────────────────────────────────────────────────────────────

def test_policy_telegram_forbids_birth_details():
    """#255: the alert is a diagnostic, never an identity."""
    assert not (pii.POLICY["telegram"].allow & {"name", "dob", "tob", "city", "region"})
    assert pii.allowed("telegram") == pii.POLICY["telegram"].allow


def test_every_rule_names_its_source_and_stays_inside_the_known_classes():
    rules = [r for r in pii.POLICY.values()]
    rules += [r for _, r in pii.BLOB_RULES] + list(pii.MAIL_RULES.values())
    rules += list(pii.LLM_RULES.values())
    for rule in rules:
        assert rule.why.strip(), "a rule with no stated source is a rule nobody can argue with"
        assert rule.allow <= set(pii.FIELD_CLASSES), rule.allow


def test_email_is_allowed_on_no_llm_route():
    for route, rule in pii.LLM_RULES.items():
        assert "email" not in rule.allow, route


def test_the_shared_rashifal_route_allows_no_sentinel_at_all():
    assert pii.allowed("llm", "rashifal_single") == frozenset()


@pytest.mark.parametrize("sink, key", [
    ("llm", "unknown"),
    ("llm", "a-route-nobody-wrote-down"),
    ("mail", "unknown"),
    ("mail", "a-purpose-nobody-wrote-down"),
    ("blob", "llm/natal/en/v4/abc.txt"),
    ("blob", "rashifal/2026-11-09-en-v1.txt"),
    ("blob", "a-key-nobody-wrote-down.json"),
    ("blobkey", ""),
    ("a-sink-nobody-modelled", ""),
    ("analytics:title", "/anything"),
    ("analytics:config", "/anything"),
    ("analytics:props", "/anything"),
    ("analytics:calls", "/anything"),
])
def test_anything_unlisted_is_default_deny(sink, key):
    assert pii.allowed(sink, key) == frozenset(), (sink, key)


def test_the_longest_blob_prefix_wins_and_snapshots_do_not_take_email():
    assert "question" in pii.allowed("blob", "users.json")
    assert pii.allowed("blob", "subscribers.json") == frozenset({"email"})
    assert "email" not in pii.allowed("blob", "snapshot/abc.json")
    assert "name" in pii.allowed("blob", "snapshot/abc.json")
    # a key that merely CONTAINS a listed prefix is not that blob
    assert pii.allowed("blob", "llm/users.json") == frozenset()


def test_the_location_header_may_carry_the_question_only_on_ask():
    assert pii.allowed("analytics:location", "/ask") == frozenset({"question"})
    assert pii.allowed("analytics:location", "/kundli") == frozenset()


@pytest.mark.parametrize("subject, purpose", [
    ("[Shubh Bhagya feedback] 💬 Feedback", "feedback"),
    ("Welcome to Shubh Bhagya — your daily Rashifal starts tomorrow", "welcome"),
    ("Shubh Bhagya में स्वागत है — कल से दैनिक राशिफल शुरू", "welcome"),
    ("Your Kundli Reading — Shubh Bhagya", "kundli-reading"),
    ("आपकी कुंडली रीडिंग — Shubh Bhagya", "kundli-reading"),
    ("A subject nobody has seen", "unknown"),
])
def test_a_mail_is_classified_by_its_subject_and_an_unknown_one_is_denied(subject, purpose):
    assert pii.mail_purpose(subject) == purpose


# ─── the recorder reads what it should and flags what it should ─────────────

def _egress(**captures) -> "pii.Egress":
    e = pii.Egress()
    for k, v in captures.items():
        setattr(e, k, v)
    return e


def test_a_leak_at_each_sink_is_a_violation():
    cases = {
        "telegram": _egress(telegram=[(f"hello {pii.NAME}", "k")]),
        "events": _egress(writes=[("events/2026-11-09.json", f'{{"dob": "{pii.DOB}"}}')]),
        "blob": _egress(writes=[("feedback.json", f'{{"name": "{pii.NAME}"}}')]),
        "mail": _egress(mail=[("[Shubh Bhagya feedback] x", f"from {pii.B_PLACE}")]),
        "llm": _egress(llm=[("rashifal_single", f"for {pii.NAME}")]),
        "geocode": _egress(geocode=[pii.EMAIL]),
        "blobkey": _egress(writes=[(f"snapshot/{pii.NAME}.json", "{}")]),
    }
    for sink, e in cases.items():
        assert e.violations(), f"a sentinel at the {sink} sink was not flagged"
        assert {s for s, _, _ in e.violations()} & {sink, "blobkey", "events", "blob"}, (sink, e.violations())


def test_an_allowed_class_is_observed_but_not_a_violation():
    e = _egress(telegram=[(f"ask: {pii.QUESTION} from {pii.EMAIL}", "k")])
    assert ("telegram", "", "question") in e.scan()
    assert ("telegram", "", "email") in e.scan()
    assert e.violations() == set()


def test_events_are_judged_by_the_events_rule_not_the_blob_default():
    e = _egress(writes=[("events/2026-11-09.json", f'{{"city": "{pii.PLACE.split(",")[0]}"}}')])
    assert e.violations() == set()          # city is allowed in the activity log
    e = _egress(writes=[("events/2026-11-09.json", f'{{"region": "{pii.PLACE}"}}')])
    assert ("events", "events/2026-11-09.json", "region") in e.violations()


def test_an_event_timestamp_is_not_read_as_a_birth_time():
    blob = '{"events": [{"ts": "2026-11-09T21:06:47.5", "type": "form_kundli"}]}'
    e = _egress(writes=[("events/2026-11-09.json", blob)])
    assert e.scan() == set(), e.scan()


def test_only_astro_ai_loggers_are_scanned():
    """httpx logs the request URL client-side, `GET http://testserver/ask?q=...`.
    That is the test client talking to itself, not the app logging a question."""
    def rec(name, msg):
        return SimpleNamespace(name=name, exc_info=None, getMessage=lambda: msg)

    e = _egress(log_records=[rec("httpx", f"GET /ask?q={pii.QUESTION}"),
                             rec("astro_ai.routes.ask", f"failed for {pii.QUESTION}")])
    assert e.violations() == {("log", "", "question")}
    e = _egress(log_records=[rec("httpx", f"GET /ask?q={pii.QUESTION}")])
    assert e.violations() == set()


def test_page_surfaces_reads_title_config_props_and_call_arguments():
    html = (
        "<head><title>Reading for X — Shubh Bhagya</title></head>"
        '<script>window.BHAGYA_ANALYTICS_CONFIG = {\n ga4: "G-1" \n};\n'
        'window.BHAGYA_USER_PROPS = {\n age_bucket: "30-39"\n};</script>'
        "<script>Analytics.track('e', {a: '1', f: t(lang, 'k')}); gtag('event', 'x');</script>"
    )
    s = pii.page_surfaces(html)
    assert s["title"] == "Reading for X — Shubh Bhagya"
    assert "G-1" in s["config"] and "30-39" in s["props"]
    assert "a: '1'" in s["calls"] and "gtag('event', 'x')" in s["calls"]


def test_a_page_with_a_sentinel_in_each_surface_is_flagged_per_surface():
    html = (f"<title>{pii.NAME}</title>"
            f"<script>window.BHAGYA_ANALYTICS_CONFIG = {{ ga4: \"{pii.EMAIL}\" }};"
            f"window.BHAGYA_USER_PROPS = {{ a: \"{pii.B_NAME}\" }};"
            f"Analytics.track('e', {{ q: '{pii.QUESTION}' }});</script>")
    e = _egress(responses=[{"route": "/p", "method": "GET", "status": 200,
                            "location": "", "html": html}])
    assert e.violations() == {
        ("analytics:title", "/p", "name"), ("analytics:config", "/p", "email"),
        ("analytics:props", "/p", "name"), ("analytics:calls", "/p", "question")}


def test_known_gaps_are_all_page_titles_carrying_a_name():
    """#817 cleared the eight title pins. An entry returning is a regression to be
    fixed, not a pin to re-add; if one is ever added on purpose it must still be a
    page title carrying a name, the only shape the equality ratchet was built for."""
    assert pii.KNOWN_GAPS == frozenset()
    assert all(s == "analytics:title" and c == "name" for s, _, c in pii.KNOWN_GAPS)


# ─── anti-vacuity: a sweep that saw nothing, or less than it declared, fails ─

def test_a_scenario_that_captured_nothing_fails_outright():
    problems = pii.Egress().check_expects({})
    assert any("nothing" in p for p in problems), problems


def test_a_silenced_sink_fails_the_expects_guard():
    """The dosha and numerology notifies sit inside `try/except: pass`, so a
    signature change deletes the alert and a 'nothing leaked' check stays green.
    The declared minimum is what turns that into a failure."""
    e = pii.Egress()
    e.responses.append({"route": "/x", "method": "GET", "status": 200, "location": "", "html": ""})
    e.arm()
    assert e.check_expects({"responses": (0, None)}) == []
    problems = e.check_expects({"telegram": (1, None)})
    assert problems and "telegram" in problems[0]


def test_expects_counts_only_what_happened_after_setup():
    e = pii.Egress()
    e.telegram.append(("sign-in alert", ""))
    e.responses.append({"route": "/auth/google", "method": "POST", "status": 200,
                        "location": "", "html": ""})
    e.arm()
    assert e.count("telegram") == 0, "the sign-in alert must not satisfy the flow's own minimum"
    e.telegram.append(("the flow's alert", ""))
    assert e.count("telegram") == 1


def test_an_upper_bound_catches_a_route_that_started_calling_a_model():
    e = pii.Egress()
    e.responses.append({"route": "/x", "method": "GET", "status": 200, "location": "", "html": ""})
    e.arm()
    e.llm.append(("natal", "{}"))
    assert e.check_expects({"llm": (0, 0)}), "a dosha route that called the LLM must fail"
    assert e.count("llm:natal") == 1 and e.count("llm:ask") == 0
