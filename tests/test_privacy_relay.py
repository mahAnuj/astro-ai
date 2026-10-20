"""No birth detail reaches Telegram or the events log (#255 part 2).

The owner's decided scope: the kundli, matching, dosha (x3) and numerology
alerts are a DIAGNOSTIC (rashi names, model, tokens, latency, an 8-hex key),
never an identity; `form_kundli` / `form_matching` events keep an HMAC key and
a coarse age band + city instead of name/date/time/place; and a `ChartError`,
whose message embeds the raw birth place, is not relayed at all.

These drive the REAL routes with sentinel values and read back what the sink
received and what landed in the events file, so a formatter that silently
regrows a parameter, or a call site that passes `name=` again, goes red. The
dosha and numerology call sites sit inside `try/except Exception: pass`, which
means a signature mismatch there would not error -- it would just delete the
alert. Every case therefore asserts the sink was called EXACTLY once.
"""
from __future__ import annotations

import json
import re
from datetime import date

import pytest

NAME = "Zorbax Quillfeather"
DATE = "1987-03-14"
TIME = "06:47"
PLACE = "Quillmere-on-Thames, Oxfordshire"

B_NAME = "Ysolde Fenwhistle"
B_DATE = "1990-11-02"
B_TIME = "21:15"
B_PLACE = "Fenwhistle Holm, Lincolnshire"

EMAIL = "zorbax.quillfeather@example.test"

_BIRTH_FORM = {"name": NAME, "birth_date": DATE, "birth_time": TIME, "birth_place": PLACE}
_MATCH_FORM = {
    "g_name": NAME, "g_birth_date": DATE, "g_birth_time": TIME, "g_birth_place": PLACE,
    "b_name": B_NAME, "b_birth_date": B_DATE, "b_birth_time": B_TIME, "b_birth_place": B_PLACE,
}

# Everything that identifies somebody. "Quillmere" and "Oxfordshire" are listed
# separately so that a partial leak of the place (the city half) is also caught
# in the Telegram text, where no city is allowed at all.
_FORBIDDEN_IN_RELAY = [
    "Zorbax", "Quillfeather", "1987", DATE, TIME, "Quillmere", "Oxfordshire",
    "Ysolde", "Fenwhistle", "1990-11-02", B_TIME, "Lincolnshire", EMAIL,
]

_HEX8 = re.compile(r"(?<![0-9a-f])[0-9a-f]{8}(?![0-9a-f])")


def _natal_body(_n: int = 0) -> str:
    filler = "The chart favours patient, deliberate work this season. "
    return "## Personality\n" + filler * 10 + "\n\n## Career\n" + filler * 10 + "\n"


@pytest.fixture
def sink(monkeypatch):
    """Capture what would be sent to Telegram, bypassing env config and dedup.

    Patches `notify.notify` itself: every formatter resolves it from module
    globals at call time. Dedup keys are captured too -- they live in an
    in-memory dict, and a dedup key built from the email or the DOB is the same
    leak by another route.
    """
    from astro_ai import notify

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        notify, "notify", lambda text, *, dedup_key="": sent.append((text, dedup_key)))
    return sent


@pytest.fixture
def event_log(tmp_path, monkeypatch):
    """Route `events.record` to a tmp file and return a reader for today's events."""
    from astro_ai import events

    monkeypatch.setattr(events, "_LOCAL_FALLBACK_DIR", tmp_path / "events")
    # No bucket in the suite, but make "storage unavailable" explicit so the
    # local-fallback path is the one under test regardless of the environment.
    monkeypatch.setattr(events.storage, "update_json", lambda *a, **k: None)

    def _read() -> list[dict]:
        path = events._local_path(date.today())
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))["events"]

    return _read


@pytest.fixture
def signed_in(monkeypatch):
    """Make kundli and matching see a signed-in user (so an email is available to leak)."""
    from types import SimpleNamespace

    from astro_ai.routes import kundli, matching

    user = SimpleNamespace(email=EMAIL, sub="", name=NAME)
    monkeypatch.setattr(kundli, "load_user", lambda request: user)
    monkeypatch.setattr(matching, "load_user", lambda request: user)


def _assert_clean(sent: list[tuple[str, str]]) -> str:
    assert len(sent) == 1, (
        f"expected exactly one relay alert, got {len(sent)}: {sent!r} -- a missed "
        f"signature change inside try/except would show up here as zero"
    )
    text, dedup_key = sent[0]
    for needle in _FORBIDDEN_IN_RELAY:
        assert needle not in text, f"{needle!r} leaked into the Telegram text:\n{text}"
        assert needle not in dedup_key, f"{needle!r} leaked into dedup key {dedup_key!r}"
    assert _HEX8.search(text), f"no 8-hex lookup key in:\n{text}"
    return text


def _expected_rashis(date_, time_, place) -> tuple[str, str, str]:
    """Independent of notify.chart_rashis: read the chart directly."""
    from astro_ai.chart import compute_chart

    c = compute_chart(date_, time_, place)
    moon = next(p.rashi for p in c.planets if p.name == "Moon")
    sun = next(p.rashi for p in c.planets if p.name == "Sun")
    return c.lagna_rashi, moon, sun


# ─── T1: what Telegram receives ────────────────────────────────────────────


@pytest.mark.parametrize("with_email", [False, True], ids=["anonymous", "signed-in"])
def test_kundli_relay_is_a_diagnostic_not_an_identity(
        client, saved_chart, stub_llm, sink, event_log, request, with_email):
    if with_email:
        request.getfixturevalue("signed_in")
    stub_llm(_natal_body)
    saved_chart(birth_date=DATE, birth_time=TIME, birth_place=PLACE, name=NAME)
    resp = client.get("/kundli")
    assert resp.status_code == 200

    text = _assert_clean(sink)
    assert "Kundli generated" in text
    lagna, moon, sun = _expected_rashis(DATE, TIME, PLACE)
    for rashi in (lagna, moon, sun):
        assert rashi in text, f"{rashi!r} missing from:\n{text}"
    assert "cache=miss" in text


def test_matching_relay_is_a_diagnostic_not_an_identity(
        client, stub_llm, sink, event_log):
    stub_llm(_natal_body)
    resp = client.post("/matching", data=_MATCH_FORM)
    assert resp.status_code == 200

    text = _assert_clean(sink)
    assert "Kundli matching" in text
    # Two partners -> two distinct lookup keys.
    assert len(set(_HEX8.findall(text))) == 2, text


def test_matching_relay_stays_clean_when_signed_in(
        client, stub_llm, sink, event_log, signed_in):
    stub_llm(_natal_body)
    assert client.post("/matching", data=_MATCH_FORM).status_code == 200
    _assert_clean(sink)


@pytest.mark.parametrize("path, label", [
    ("/manglik-check", "Manglik check"),
    ("/sade-sati-check", "Sade Sati check"),
    ("/kaal-sarp-check", "Kaal Sarp check"),
])
def test_dosha_relay_carries_no_birth_detail(client, sink, path, label):
    resp = client.post(path, data=_BIRTH_FORM)
    assert resp.status_code == 200

    text = _assert_clean(sink)
    assert label in text
    lagna, moon, sun = _expected_rashis(DATE, TIME, PLACE)
    for rashi in (lagna, moon, sun):
        assert rashi in text, f"{rashi!r} missing from:\n{text}"


def test_numerology_relay_carries_no_name_or_date(client, sink):
    resp = client.post("/numerology", data={"name": NAME, "birth_date": DATE})
    assert resp.status_code == 200

    text = _assert_clean(sink)
    assert "life path" in text


def test_one_chart_gets_one_key_across_routes(client, saved_chart, stub_llm, sink):
    """The key is what lets the owner correlate an alert with its event, and a
    dosha check with the kundli of the same person. It must be a pure function
    of the identity -- not of the route or the moment."""
    stub_llm(_natal_body)
    client.post("/manglik-check", data=_BIRTH_FORM)
    saved_chart(birth_date=DATE, birth_time=TIME, birth_place=PLACE, name=NAME)
    client.get("/kundli")
    assert len(sink) == 2, sink
    keys = [set(_HEX8.findall(t)) for t, _ in sink]
    assert keys[0] & keys[1], f"no shared key between {sink!r}"


# ─── T2: what the events log keeps ─────────────────────────────────────────

_ALLOWED = {
    "form_kundli": {"identity", "lang", "model", "rashi_lagna", "rashi_moon",
                    "rashi_sun", "age_band", "city"},
    "form_matching": {"groom_key", "bride_key", "total_score", "verdict", "lang", "model"},
}
_FORBIDDEN_IN_EVENT = [
    "Zorbax", "Quillfeather", DATE, TIME, "Oxfordshire", PLACE,
    "Ysolde", "Fenwhistle", B_DATE, B_TIME, "Lincolnshire",
]


def _scannable(evt: dict) -> str:
    """The event as JSON, WITHOUT its server timestamp.

    `ts` is `datetime.isoformat()`, so it carries `HH:MM:SS` — and a birth time
    is `HH:MM`. Any birth time whose minutes are a valid second count therefore
    appears inside a legitimate timestamp once an hour, for one second, and a
    whole-blob substring scan reads that as an identity leak.

    Measured: CI run 39379764420 started at 06:21:15 UTC and failed on
    `assert '21:15' not in blob` because `B_TIME` is `21:15`. Both fixtures
    collide — `TIME` at `*:06:47`, `B_TIME` at `*:21:15` — so roughly two
    seconds an hour, ~48s a day, this suite fails for no reason. It fired on a
    merge commit and would have sent the stall loop after a phantom.

    `ts` is a server clock reading and is not identity, so it is excluded rather
    than the needles being narrowed: narrowing them is what would lose the
    guard. Everything that could actually carry a leak — `type`, `email` and
    every `data` field — is still scanned, and a time planted in any of those
    still fails.
    """
    return json.dumps({k: v for k, v in evt.items() if k != "ts"},
                      ensure_ascii=False)


def _only(events_: list[dict], type_: str) -> dict:
    found = [e for e in events_ if e["type"] == type_]
    assert len(found) == 1, f"expected one {type_} event, got {events_!r}"
    return found[0]


def test_kundli_event_keeps_analytics_and_drops_identity(
        client, saved_chart, stub_llm, sink, event_log):
    stub_llm(_natal_body)
    saved_chart(birth_date=DATE, birth_time=TIME, birth_place=PLACE, name=NAME)
    client.get("/kundli")

    evt = _only(event_log(), "form_kundli")
    extra = set(evt["data"]) - _ALLOWED["form_kundli"]
    assert not extra, f"form_kundli carries fields outside the allow-list: {extra}"
    assert set(evt["data"]) == _ALLOWED["form_kundli"], evt["data"]
    blob = _scannable(evt)
    for needle in _FORBIDDEN_IN_EVENT:
        assert needle not in blob, f"{needle!r} leaked into the event:\n{blob}"

    lagna, moon, sun = _expected_rashis(DATE, TIME, PLACE)
    assert (evt["data"]["rashi_lagna"], evt["data"]["rashi_moon"],
            evt["data"]["rashi_sun"]) == (lagna, moon, sun)
    assert re.fullmatch(r"[0-9a-f]{32}", evt["data"]["identity"])
    # The coarse fields are what keep /admin/insights alive.
    assert evt["data"]["age_band"] not in ("", "unknown")
    assert evt["data"]["city"]
    # And the alert's 8-hex key is the event's identity prefix.
    assert evt["data"]["identity"][:8] in sink[0][0]


def test_matching_event_keeps_scores_and_drops_identity(
        client, stub_llm, sink, event_log):
    stub_llm(_natal_body)
    client.post("/matching", data=_MATCH_FORM)

    evt = _only(event_log(), "form_matching")
    assert set(evt["data"]) <= _ALLOWED["form_matching"], evt["data"]
    assert set(evt["data"]) == _ALLOWED["form_matching"], evt["data"]
    blob = _scannable(evt)
    for needle in _FORBIDDEN_IN_EVENT:
        assert needle not in blob, f"{needle!r} leaked into the event:\n{blob}"
    assert evt["data"]["groom_key"] != evt["data"]["bride_key"]
    assert evt["data"]["groom_key"][:8] in sink[0][0]
    assert evt["data"]["bride_key"][:8] in sink[0][0]


# ─── T8: a ChartError carries the birth place ──────────────────────────────

_CHART_ERROR_PLACE = "Quillmere-on-Thames, Oxfordshire"


def _chart_error():
    from astro_ai.chart import ChartError

    try:
        raise ChartError(f"Geocoding failed for {_CHART_ERROR_PLACE!r}: timed out")
    except ChartError as err:
        return err


def test_chart_error_is_relayed_without_its_message_or_traceback(sink, event_log):
    from astro_ai.routes.llm_support import _fire_error_alert

    err = _chart_error()
    try:
        raise err
    except Exception:
        # format_exc() only has something to say inside an except block, which
        # is where every real call site invokes this.
        _fire_error_alert(None, err, "chart:test")

    assert len(sink) == 1, sink
    text, dedup_key = sink[0]
    assert "ChartError" in text, "the class name is the one thing worth keeping"
    for needle in ("Quillmere", "Oxfordshire", _CHART_ERROR_PLACE, "Geocoding failed"):
        assert needle not in text, f"{needle!r} in Telegram text:\n{text}"
        assert needle not in dedup_key
    evt = _only(event_log(), "error")
    blob = _scannable(evt)
    for needle in ("Quillmere", "Oxfordshire", "Geocoding failed"):
        assert needle not in blob, f"{needle!r} in the recorded event:\n{blob}"
    assert evt["data"]["error_type"] == "ChartError"
    assert evt["data"]["traceback"] == ""


def test_other_errors_still_relay_their_message(sink, event_log):
    """The redaction is for ChartError only; a provider outage's message is the
    whole diagnostic and must keep arriving."""
    from astro_ai.routes.llm_support import _fire_error_alert

    try:
        raise RuntimeError("provider exploded in a recognisable way")
    except RuntimeError as err:
        _fire_error_alert(None, err, "test")
    assert "provider exploded in a recognisable way" in sink[0][0]
    assert "Traceback" in sink[0][0]


@pytest.mark.parametrize("path", ["/manglik-check", "/sade-sati-check", "/kaal-sarp-check"])
def test_a_rejected_place_on_the_real_dosha_routes_is_not_relayed(
        client, sink, event_log, monkeypatch, path):
    from astro_ai.chart import ChartError
    from astro_ai.routes import dosha

    def _boom(d, t, place):
        raise ChartError(f"Geocoding failed for {place!r}: no match")

    monkeypatch.setattr(dosha, "compute_chart", _boom)
    resp = client.post(path, data=_BIRTH_FORM)
    assert resp.status_code == 400

    assert len(sink) == 1, sink
    assert "ChartError" in sink[0][0]
    assert "Quillmere" not in sink[0][0] and "Oxfordshire" not in sink[0][0]
    blob = json.dumps(_only(event_log(), "error"), ensure_ascii=False)
    assert "Quillmere" not in blob and "Oxfordshire" not in blob
