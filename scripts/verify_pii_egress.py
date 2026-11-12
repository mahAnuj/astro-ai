#!/usr/bin/env python3
"""PII egress sweep (#744): plant a sentinel in every personal field, drive the
real routes, and read back what left the process at each sink.

    uv run python scripts/verify_pii_egress.py      # exit 0 pass, 1 fail, 2 could not run

WHY THIS EXISTS. #255 decided that no birth detail reaches Telegram or the
events log, and pinned it with `tests/test_privacy_relay.py`: two sinks, five
flows. The site has more places data leaves than that -- the Brevo mail payload,
the LLM prompt, the storage blobs, the logs, and the rendered page that the GA4
and Clarity scripts read -- and nothing guarded them. #354 asked for the whole
inventory; its "ten egress points" is a count of MODULES that can reach a
network, not of PII sinks, so this covers every PII-capable SINK instead (see
`ARCHITECTURE.md` section 10).

HOW. One policy table (`POLICY`, `BLOB_RULES`, `MAIL_RULES`, `LLM_RULES`) says
which field classes may reach which sink. A recorder (`Egress`) sits at each
module boundary -- no network, no LLM, no GCS -- and `evaluate()` scans what it
caught for the sentinel of every class the sink does not allow. Sentinels, not
identifier-name greps: #354 rejects the latter because an f-string, a dict
spread or a reformat walks straight past it.

WHERE THE SUBSTANCE LIVES. The scenarios run inside pytest
(`tests/test_pii_egress*.py`), because `tests/conftest.py` carries the autouse
isolation (tmp cache, offline geocoder, dummy key, socket guard) and a script
that re-implemented it would write the repo's real `bhagya.db` the day the copy
went stale. This file is the single source of truth for WHAT may go WHERE and
how to scan for it; `main()` only runs the three test files and applies
`verify_behaviour.py`'s rule that a skip, xfail or deselect is a failure.

IT IS NOT A PROOF. It checks the routes it drives with the values it plants. A
new caller of an existing sink, or a new LLM payload builder, is invisible to it
until someone adds a scenario (the optional AST ledger in the design was not
built). What it cannot see at all is listed in `ARCHITECTURE.md` section 11.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent

TEST_FILES = (
    "tests/test_pii_egress_scanner.py",
    "tests/test_pii_egress.py",
    "tests/test_pii_egress_analytics.py",
)

# ─── sentinels ─────────────────────────────────────────────────────────────
# Person A is the visitor, B a partner. Values are copied from
# tests/test_privacy_relay.py (they are not importable from a test module), with
# two deliberate differences: the partner's place is "Wendlebury Holm" so that
# partner name and partner city do not share a word, and the email is unrelated
# to the name so that a name scan can be case-insensitive without matching it.
NAME = "Zorbax Quillfeather"
DOB = "1987-03-14"
TOB = "06:47"
PLACE = "Quillmere-on-Thames, Oxfordshire"          # city + region
EMAIL = "seeker7731@example.test"
QUESTION = "Will prosperity ever arrive, zanzibar?"  # token: zanzibar
MESSAGE = "The chart page felt slow, quokka"         # token: quokka

B_NAME = "Ysolde Fenwhistle"
B_DOB = "1990-11-02"
B_TOB = "21:15"
B_PLACE = "Wendlebury Holm, Lincolnshire"

FIELD_CLASSES = ("name", "dob", "tob", "city", "region", "email", "question", "message")

# Why the lookarounds are there, each one paid for:
#  * a birth time is HH:MM and every ISO timestamp carries HH:MM:SS, so a bare
#    "06:47" matched a legitimate clock for a minute a day (#437, CI run
#    39379764420). `(?<![\d:])` and `(?![\d:])` make it a whole clock reading.
#  * a four-digit year sits inside hex identity keys (32-hex `identity`, 8-hex
#    lookup keys) and inside decimals such as a latency. Neither boundary class
#    can start or end a real year.
FIELDS: dict[str, re.Pattern[str]] = {
    "name": re.compile(r"zorbax|quillfeather|ysolde|fenwhistle", re.I),
    "dob": re.compile(
        r"1987-03-14|1990-11-02"
        r"|(?<![0-9a-fA-F.])(?:1987|1990)(?![0-9a-fA-F])(?!\.\d)"),
    "tob": re.compile(r"(?<![\d:])(?:06:47|21:15)(?![\d:])"),
    "city": re.compile(r"quillmere|wendlebury", re.I),
    "region": re.compile(r"oxfordshire|lincolnshire", re.I),
    "email": re.compile(r"seeker7731", re.I),
    "question": re.compile(r"zanzibar", re.I),
    "message": re.compile(r"quokka", re.I),
}


def classes_in(text: str) -> set[str]:
    """The sentinel classes present in `text`."""
    return {cls for cls, rx in FIELDS.items() if rx.search(text or "")}


# ─── the policy ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Rule:
    allow: frozenset[str]
    why: str


def _rule(allow: str, why: str) -> Rule:
    return Rule(frozenset(allow.split()), why)


NOTHING = Rule(frozenset(), "default-deny: no sentinel of any class may appear")

#: Sinks with one rule each. `why` names the heading in templates/privacy.html.
POLICY: dict[str, Rule] = {
    "telegram": _rule(
        "email question message",
        'privacy.html "Notifications to the site operator": the question, feedback '
        "text and email are sent; birth details (name, date, time, place) never are"),
    "events": _rule(
        "email question city",
        'privacy.html "Our 30-day activity log": the question, answer and email, '
        "plus the birth CITY and an age band; not name, date, time or full place"),
    "log": _rule(
        "email",
        'privacy.html "Operational logs" says a log line can include an email '
        "address (failed send, failed sign-in step, an unsubscribe link) and the "
        "nothing else: the place name a failed lookup used to log (#819) is gone "
        "(#908, scenario `strip-place-unresolved`). This pins TODAY's behaviour "
        "(email_sender.send logs the address, subscribe.py and account.py log it) "
        "so that a NEW flow is caught; tightening it is a separate decision"),
    "geocode": _rule(
        "city region",
        'privacy.html "Place lookup" names Nominatim: the geocoder is only ever '
        "handed a place string (birth place or a subscriber's city), never a "
        "name, date, time, email or question"),
}

#: Storage blobs by key prefix, longest match wins; anything unlisted is NOTHING.
BLOB_RULES: tuple[tuple[str, Rule], ...] = (
    ("users.json", _rule(
        "name dob tob city region email question",
        'privacy.html "Email + name": the account store keeps saved charts and '
        "reading history, which includes the question of a signed-in /ask")),
    ("subscribers.json", _rule("email", "the newsletter list: an address, language, city")),
    ("feedback.json", _rule("email message", "the feedback the visitor chose to write")),
    ("snapshot/", _rule(
        "name dob tob city region",
        'privacy.html "Readings you share": opt-in Share stores name, date, time, place')),
)

#: Brevo mail by purpose (classified from the subject). Unlisted purpose: NOTHING.
MAIL_RULES: dict[str, Rule] = {
    "welcome": _rule("email", 'privacy.html "Who we share data with": a welcome to a subscriber'),
    "feedback": _rule("email message", "the feedback forward to the owner"),
    "kundli-reading": _rule(
        "email name dob tob city region",
        "the signed-in user asked for their own saved reading, sent to their own address"),
}

_PERSONAL = "name dob tob city region"
#: LLM payloads by `route=`. `rashifal_single` is the only SHARED label: its
#: output is cached for everyone, so no sentinel may reach it. `email` is allowed
#: on no route at all.
LLM_RULES: dict[str, Rule] = {
    "natal": _rule(_PERSONAL, 'privacy.html "Questions you ask" / chart data goes to the provider'),
    "today": _rule(_PERSONAL, "a personal reading"),
    "monthly": _rule(_PERSONAL, "a personal reading"),
    "yearly": _rule(_PERSONAL, "a personal reading"),
    "dasha": _rule(_PERSONAL, "a personal reading"),
    "matching": _rule(_PERSONAL, "both partners' chart data"),
    "ask": _rule(_PERSONAL + " question", "the question is sent with the chart data"),
    "rashifal_single": Rule(frozenset(), "SHARED cache: one reading is served to every visitor"),
}

#: What the page gives the browser's analytics scripts. Nothing may be in it.
ANALYTICS_SINKS = ("analytics:title", "analytics:config", "analytics:props",
                   "analytics:calls", "analytics:location")


def allowed(sink: str, key: str = "") -> frozenset[str]:
    """The classes `sink` (with its `key`) is allowed to carry."""
    if sink in POLICY:
        return POLICY[sink].allow
    if sink == "blob":
        best = ""
        for prefix, _ in BLOB_RULES:
            if key.startswith(prefix) and len(prefix) > len(best):
                best = prefix
        return dict(BLOB_RULES)[best].allow if best else NOTHING.allow
    if sink == "mail":
        return MAIL_RULES.get(key, NOTHING).allow
    if sink == "llm":
        return LLM_RULES.get(key, NOTHING).allow
    if sink == "analytics:location":
        # POST /ask redirects to /ask?q=<question>; analytics.js strips `q`
        # before GA4 sees it (#528, tests/test_analytics_ask_location.py).
        return frozenset({"question"}) if key == "/ask" else NOTHING.allow
    return NOTHING.allow          # blobkey, analytics:*, and any sink nobody modelled


#: Known leaks, asserted by EQUALITY (not xfail: verify_behaviour.py fails any
#: xfail). A new leak is a failure, and so is a fixed one -- delete the entry.
#: (sink, key, class). CURRENTLY EMPTY. It held eight entries, each the page
#: <title> carrying the visitor's name (templates rendered `details.name` into
#: {% block title %}, and static/analytics.js sets no `page_title`, so gtag
#: collects document.title); #817 made every one of those titles name-free.
#: A leak that reappears is a failure, not a pin to add back.
KNOWN_GAPS: frozenset[tuple[str, str, str]] = frozenset()

Finding = tuple[str, str, str]      # (sink, key, class)


def mail_purpose(subject: str) -> str:
    s = subject or ""
    if "[Shubh Bhagya feedback]" in s:
        return "feedback"
    if s.startswith("Welcome to Shubh Bhagya") or s.startswith("Shubh Bhagya में स्वागत"):
        return "welcome"
    if "Kundli Reading" in s or "कुंडली रीडिंग" in s:
        return "kundli-reading"
    return "unknown"


def _matching_paren_end(text: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def page_surfaces(html: str) -> dict[str, str]:
    """What a page hands to GA4 and Clarity, as text per surface.

    `title` is document.title (gtag's default page_title); `config` and `props`
    are the two inline blobs base.html builds for analytics.js; `calls` is the
    argument text of every `Analytics.*(` and `gtag(` call in the markup.
    """
    out: dict[str, str] = {}
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    out["title"] = m.group(1) if m else ""
    m = re.search(r"window\.BHAGYA_ANALYTICS_CONFIG\s*=\s*\{.*?\};", html, re.S)
    out["config"] = m.group(0) if m else ""
    m = re.search(r"window\.BHAGYA_USER_PROPS\s*=\s*\{.*?\};", html, re.S)
    out["props"] = m.group(0) if m else ""
    out["calls"] = "\n".join(analytics_call_args(html))
    return out


def analytics_call_args(text: str) -> list[str]:
    """Each `Analytics.<fn>(...)` / `gtag(...)` call in `text`, parentheses and all."""
    return [text[m.start():_matching_paren_end(text, m.end() - 1)]
            for m in re.finditer(r"(?:Analytics\.\w+|gtag)\(", text)]


# ─── the recorder ──────────────────────────────────────────────────────────
@dataclass
class Egress:
    """Everything that left the process during one scenario."""

    telegram: list[tuple[str, str]] = field(default_factory=list)   # (text, dedup_key)
    writes: list[tuple[str, str]] = field(default_factory=list)     # (storage key, JSON/text)
    mail: list[tuple[str, str]] = field(default_factory=list)       # (subject, whole payload)
    llm: list[tuple[str, str]] = field(default_factory=list)        # (route, messages JSON)
    geocode: list[str] = field(default_factory=list)
    responses: list[dict] = field(default_factory=list)             # one per HTTP response
    log_records: list = field(default_factory=list)                 # set from caplog
    store: dict[str, str] = field(default_factory=dict)             # the fake bucket
    llm_mode: str = "ok"            # "ok" | "exhausted"
    brevo_status: int = 201
    armed: dict[str, int] = field(default_factory=dict)
    mp: object = None               # the pytest monkeypatch, for scenarios that re-patch

    # -- installation --------------------------------------------------
    def install(self, monkeypatch) -> "Egress":
        """Put a recorder at each sink. Imports astro_ai here, never at import."""
        from astro_ai import chart, email_sender, notify, providers, storage

        self.mp = monkeypatch
        monkeypatch.setattr(
            notify, "notify",
            lambda text, *, dedup_key="": self.telegram.append((text, dedup_key)))

        # Every module reaches storage as `storage.<fn>(...)`, so these five
        # names are the whole surface. A CAS-faithful update_json is not needed:
        # only the serialised value matters.
        store = self.store

        def _put(key, value, *, content_type=""):
            store[key] = value
            self.writes.append((key, value))
            return True

        def _update_json(key, mutator, *, default=None, max_retries=5):
            current = json.loads(store[key]) if key in store else default
            new = mutator(current)
            _put(key, json.dumps(new, ensure_ascii=False))
            return new

        monkeypatch.setattr(storage, "get", lambda key: store.get(key))
        monkeypatch.setattr(
            storage, "get_json",
            lambda key: json.loads(store[key]) if key in store else None)
        monkeypatch.setattr(storage, "put", _put)
        monkeypatch.setattr(
            storage, "put_json",
            lambda key, value: _put(key, json.dumps(value, ensure_ascii=False)))
        monkeypatch.setattr(storage, "update_json", _update_json)

        # The real payload builder runs; only the HTTP post is replaced.
        monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")
        monkeypatch.setenv("BHAGYA_EMAIL_FROM", "owner@example.test")

        def _post(url, **kw):
            payload = kw.get("json") or {}
            self.mail.append((payload.get("subject", ""),
                              json.dumps(payload, ensure_ascii=False)))
            return SimpleNamespace(status_code=self.brevo_status, text="brevo said no")

        monkeypatch.setattr(email_sender, "httpx", SimpleNamespace(post=_post))

        def _chat(messages, **kw):
            route = kw.get("route", "") or "unknown"
            self.llm.append((route, json.dumps(messages, ensure_ascii=False)))
            if self.llm_mode == "exhausted":
                raise providers.AllProvidersExhausted("every provider is down")
            return _llm_body(route)

        monkeypatch.setattr(providers, "chat", _chat)

        def _geocode(place):
            self.geocode.append(place)
            return (19.0760, 72.8777, "Asia/Kolkata")

        monkeypatch.setattr(chart, "geocode_place", _geocode)
        return self

    def watch(self, client) -> None:
        """Record every HTTP response the client receives, redirects included."""
        def _hook(resp):
            resp.read()
            ctype = resp.headers.get("content-type", "")
            self.responses.append({
                "route": resp.request.url.path,
                "method": resp.request.method,
                "status": resp.status_code,
                "location": resp.headers.get("location", ""),
                "html": resp.text if "text/html" in ctype else "",
            })
        client.event_hooks["response"].append(_hook)

    def arm(self) -> None:
        """Remember where setup ended, so `count` measures the scenario itself.

        A signed-in scenario sends a sign-in alert and writes the account blob
        before its own flow starts; without this, `telegram >= 1` would pass on
        the sign-in alone and say nothing about the flow under test.
        """
        self.armed = {"telegram": len(self.telegram), "writes": len(self.writes),
                      "mail": len(self.mail), "llm": len(self.llm),
                      "geocode": len(self.geocode), "responses": len(self.responses)}

    # -- counting (anti-vacuity) ---------------------------------------
    def count(self, what: str) -> int:
        """Captures since `arm()`. `what`: telegram | mail | geocode | responses |
        llm | llm:<route> | blob:<key prefix> | events."""
        a = self.armed
        if what in ("telegram", "mail", "geocode", "responses"):
            return len(getattr(self, what)) - a.get(what, 0)
        if what == "llm":
            return len(self.llm) - a.get("llm", 0)
        if what.startswith("llm:"):
            return sum(1 for r, _ in self.llm[a.get("llm", 0):] if r == what[4:])
        if what == "events":
            return sum(1 for k, _ in self.writes[a.get("writes", 0):] if k.startswith("events/"))
        if what.startswith("blob:"):
            return sum(1 for k, _ in self.writes[a.get("writes", 0):] if k.startswith(what[5:]))
        raise KeyError(what)

    def check_expects(self, expects: dict[str, tuple[int, int | None]]) -> list[str]:
        """Problems with a scenario's declared minimum/maximum capture counts.

        An empty list is a pass. A scenario that captured NOTHING at all is a
        problem of its own, whatever it declared: a sweep that saw nothing says
        nothing.
        """
        problems = []
        if not (self.telegram or self.writes or self.mail or self.llm
                or self.geocode or self.responses):
            problems.append("captured nothing at any sink")
        for what, (lo, hi) in expects.items():
            n = self.count(what)
            if n < lo or (hi is not None and n > hi):
                bound = f">= {lo}" if hi is None else f"in [{lo}, {hi}]"
                problems.append(f"{what}: saw {n}, expected {bound}")
        return problems

    # -- scanning ------------------------------------------------------
    def _captures(self):
        """(sink, key, text) for everything recorded."""
        for text, dedup in self.telegram:
            yield "telegram", "", text + "\n" + dedup
        for key, text in self.writes:
            yield "blobkey", "", key
            if key.startswith("events/"):
                yield "events", key, text
            else:
                yield "blob", key, text
        for subject, payload in self.mail:
            yield "mail", mail_purpose(subject), payload
        for route, payload in self.llm:
            yield "llm", route, payload
        for place in self.geocode:
            yield "geocode", "", place
        for rec in self.log_records:
            if not rec.name.startswith("astro_ai"):
                continue          # httpx's own client log names the request URL
            text = rec.getMessage()
            if rec.exc_info:
                import traceback
                text += "\n" + "".join(traceback.format_exception(*rec.exc_info))
            yield "log", "", text
        for r in self.responses:
            if r["location"]:
                yield "analytics:location", r["route"], r["location"]
            if not r["html"]:
                continue
            for surface, text in page_surfaces(r["html"]).items():
                yield "analytics:" + surface, r["route"], text

    def scan(self) -> set[Finding]:
        """Every (sink, key, class) observed, allowed or not."""
        return {(sink, key, cls)
                for sink, key, text in self._captures()
                for cls in classes_in(text)}

    def violations(self) -> set[Finding]:
        """Observed minus what the policy allows. KNOWN_GAPS are NOT removed here."""
        return {(s, k, c) for s, k, c in self.scan() if c not in allowed(s, k)}


# ─── scenarios ─────────────────────────────────────────────────────────────
def _llm_body(route: str) -> str:
    """A reading that passes each route's quality gate, with no sentinel in it."""
    filler = "The chart favours patient, deliberate work this season. "
    if route == "rashifal_single":
        return "## Aries / Mesha\n" + filler * 20
    return "## Personality\n" + filler * 12 + "\n\n## Career\n" + filler * 12 + "\n"


BIRTH_FORM = {"name": NAME, "birth_date": DOB, "birth_time": TOB, "birth_place": PLACE}
MATCH_FORM = {
    "g_name": NAME, "g_birth_date": DOB, "g_birth_time": TOB, "g_birth_place": PLACE,
    "b_name": B_NAME, "b_birth_date": B_DOB, "b_birth_time": B_TOB, "b_birth_place": B_PLACE,
}


def sign_in(client, monkeypatch) -> None:
    """A real sign-in through POST /auth/google, with Google's verifier stubbed.

    The Google profile name is left EMPTY on purpose: `name` then means "the name
    typed into a birth form" at every sink, and the sign-in alert, which carries
    the profile name by design (privacy.html), does not collide with it.
    """
    from google.oauth2 import id_token

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.example.test")
    monkeypatch.setattr(
        id_token, "verify_oauth2_token",
        lambda *a, **k: {"email": EMAIL, "email_verified": True,
                         "sub": "sub-744-sentinel", "name": ""})
    r = client.post("/auth/google", data={"credential": "x"})
    assert r.status_code == 200, f"sign-in did not succeed: {r.status_code} {r.text[:200]}"


def save_chart(client) -> None:
    r = client.post("/reading", data=BIRTH_FORM, follow_redirects=False)
    assert r.status_code == 303, f"POST /reading returned {r.status_code}"


@dataclass(frozen=True)
class Scenario:
    drive: Callable
    expects: dict
    signed_in: bool = False
    chart: bool = False
    llm_mode: str = "ok"
    why: str = ""


SCENARIOS: dict[str, Scenario] = {}


def scenario(name: str, *, expects: dict, signed_in=False, chart=False, llm_mode="ok", why=""):
    def _wrap(fn):
        SCENARIOS[name] = Scenario(fn, expects, signed_in, chart, llm_mode, why)
        return fn
    return _wrap


ONE = (1, None)
NONE_ = (0, 0)


@scenario("reading-kundli", signed_in=True, chart=True,
          expects={"telegram": ONE, "events": ONE, "llm:natal": ONE, "blob:users.json": ONE})
def _kundli(c, e):
    assert c.get("/kundli").status_code == 200


@scenario("matching", signed_in=True,
          expects={"telegram": ONE, "events": ONE, "llm:matching": ONE})
def _matching(c, e):
    assert c.post("/matching", data=MATCH_FORM).status_code == 200


def _dosha(path):
    def drive(c, e):
        assert c.post(path, data=BIRTH_FORM).status_code == 200
    return drive


for _name, _path in (("manglik", "/manglik-check"), ("sade-sati", "/sade-sati-check"),
                     ("kaal-sarp", "/kaal-sarp-check")):
    # The three dosha call sites sit inside `try/except Exception: pass`, so a
    # signature change would delete the alert silently: `telegram >= 1` is what
    # catches that, and `llm == 0` pins that these routes never call a model.
    scenario(_name + "-dosha", expects={"telegram": ONE, "llm": NONE_})(_dosha(_path))


@scenario("numerology", expects={"telegram": ONE, "llm": NONE_})
def _numerology(c, e):
    assert c.post("/numerology", data={"name": NAME, "birth_date": DOB}).status_code == 200


@scenario("numerology-compatibility", expects={"responses": ONE, "llm": NONE_})
def _compat(c, e):
    r = c.post("/numerology/compatibility", data={
        "name_a": NAME, "birth_date_a": DOB, "name_b": B_NAME, "birth_date_b": B_DOB})
    assert r.status_code == 200


@scenario("ask", signed_in=True, chart=True,
          expects={"telegram": ONE, "events": ONE, "llm:ask": ONE, "blob:users.json": ONE})
def _ask(c, e):
    r = c.post("/ask", data={"question": QUESTION, "category": "general", "context": "chart"},
               follow_redirects=False)
    assert r.status_code == 303, r.status_code
    assert c.get(r.headers["location"]).status_code == 200


@scenario("subscribe", expects={"telegram": ONE, "blob:subscribers.json": ONE, "mail": ONE})
def _subscribe(c, e):
    # The subscriber's city is a different data class from the birth city (it is
    # sent to Telegram as `source=` by design), so it carries no sentinel here.
    r = c.post("/subscribe", data={"email": EMAIL, "lang": "en", "city": "Mumbai"})
    assert r.status_code == 200 and r.json()["ok"] is True


@scenario("feedback", expects={"telegram": ONE, "blob:feedback.json": ONE, "mail": ONE})
def _feedback(c, e):
    # The Referer carries the question on purpose: a visitor who opens the widget
    # from /ask?q=... sends it, and a "show the owner where they came from" change
    # to the forward would otherwise put it in the mail unseen.
    r = c.post("/feedback",
               data={"type": "other", "message": MESSAGE, "email": EMAIL, "page": "/ask"},
               headers={"Referer": "https://shubhagya.com/ask?q=" + QUESTION.replace(" ", "+")})
    assert r.status_code == 200 and r.json()["ok"] is True


@scenario("snapshot", signed_in=True, chart=True, expects={"blob:snapshot/": ONE})
def _snapshot(c, e):
    r = c.post("/kundli/snapshot")
    assert r.status_code == 200 and r.json()["ok"] is True, r.text[:200]


@scenario("personal-readings", signed_in=True, chart=True,
          expects={"llm:today": ONE, "llm:monthly": ONE, "llm:yearly": ONE})
def _personal(c, e):
    for path in ("/today", "/monthly", "/yearly"):
        assert c.get(path).status_code == 200, path


@scenario("rashifal-is-shared", signed_in=True, chart=True, expects={"llm:rashifal_single": ONE})
def _rashifal(c, e):
    # The shared-cache invariant: a signed-in visitor with a saved chart gets the
    # same prompt as everyone, so nothing of theirs may be in it.
    assert c.get("/rashifal/aries").status_code == 200
    assert c.get("/rashifal").status_code == 200


@scenario("dasha", signed_in=True, chart=True, expects={"responses": (2, None), "llm:dasha": ONE})
def _dasha_pages(c, e):
    assert c.get("/dasha").status_code == 200
    assert c.get("/dasha/deep-dive").status_code == 200


@scenario("muhurat-personal", signed_in=True, chart=True,
          expects={"responses": ONE, "telegram": ONE})
def _muhurat(c, e):
    r = c.post("/muhurat", data={
        "event_type": "vivah", "city": "Mumbai", "start_date": "2026-12-01", "days": 30,
        "use_personal": "on", "bride_name": NAME, "bride_dob": DOB, "bride_time": TOB,
        "bride_place": PLACE, "groom_name": B_NAME, "groom_dob": B_DOB, "groom_time": B_TOB,
        "groom_place": B_PLACE})
    assert r.status_code == 200, r.status_code


@scenario("email-my-reading", signed_in=True, chart=True,
          expects={"mail": ONE})
def _email_reading(c, e):
    # A saved natal reading must exist first; /kundli writes it for a signed-in user.
    assert c.get("/kundli").status_code == 200
    e.arm()
    r = c.post("/email/kundli-reading")
    assert r.status_code == 200 and r.json()["ok"] is True, r.text[:200]


@scenario("llm-exhausted", signed_in=True, chart=True, llm_mode="exhausted",
          expects={"llm": (2, None), "telegram": (2, None)})
def _exhausted(c, e):
    assert c.get("/kundli").status_code in (502, 503)
    r = c.post("/ask", data={"question": QUESTION, "category": "general", "context": "chart"},
               follow_redirects=True)
    assert r.status_code in (502, 503), r.status_code


@scenario("brevo-fails", expects={"mail": ONE, "blob:subscribers.json": ONE})
def _brevo_down(c, e):
    e.brevo_status = 500
    r = c.post("/subscribe", data={"email": EMAIL, "lang": "en", "city": "Mumbai"})
    assert r.status_code == 200


@scenario("place-rejected", expects={"telegram": ONE, "geocode": ONE})
def _chart_error(c, e):
    from astro_ai import chart
    from astro_ai.chart import ChartError

    def _boom(place):
        e.geocode.append(place)
        raise ChartError(f"Geocoding failed for {place!r}: no match")

    # The recorder's stub is replaced for this one scenario so the place is
    # rejected; `e.geocode` still records what the geocoder was handed.
    e.mp.setattr(chart, "geocode_place", _boom)
    assert c.post("/manglik-check", data=BIRTH_FORM).status_code == 400
    r = c.post("/reading", data=BIRTH_FORM, follow_redirects=False)
    assert r.status_code in (303, 400, 422), r.status_code


@scenario("strip-place-unresolved", chart=True,
          expects={"geocode": (2, None), "responses": (2, None)})
def _strip_place_unresolved(c, e):
    """The homepage panchang strip geocodes the SAVED BIRTH PLACE, and when that
    fails it logs and falls back to Mumbai (routes/deps.py, #213). It used to log
    the place itself (#908), a leak no other scenario reached: `place-rejected`
    fails the place on the form routes, which never touch the strip.

    Two failures, because the log has two lines. First only the visitor's place
    fails (the warning). Then everything fails, so the default city fails too and
    `log.exception` prints a traceback whose `__context__` is the FIRST failure,
    i.e. a ChartError that embeds the place.
    """
    from astro_ai import chart
    from astro_ai.chart import ChartError
    from astro_ai.routes import deps

    everything_down = False

    def _geocode(place):
        e.geocode.append(place)
        if everything_down or place == PLACE:
            raise ChartError(f"Geocoding failed for {place!r}: no match")
        return (19.0760, 72.8777, "Asia/Kolkata")

    # Process-global strip caches would otherwise serve an earlier test's Mumbai
    # entry and the geocoder would never be asked.
    e.mp.setattr(deps, "_PANCHANG_STRIP_CACHE", {})
    e.mp.setattr(deps, "_fallback_cache", {})
    e.mp.setattr(chart, "geocode_place", _geocode)
    assert c.get("/").status_code == 200
    everything_down = True
    deps._fallback_cache.clear()
    assert c.get("/").status_code == 200


def run_scenario(name: str, monkeypatch, caplog, tmp_path) -> Egress:
    """Install the recorders, run one scenario, return what was caught.

    `monkeypatch`, `caplog` and `tmp_path` are pytest's: the first two are undone
    by pytest, so a scenario cannot leak a patch into the next test. `tmp_path`
    must be a directory this scenario owns: conftest's autouse isolation points
    the SQLite and daily caches at one tmp dir PER TEST, so two scenarios run in
    one test would share a cache and the second would be served the first's
    reading without ever reaching its own LLM path.
    """
    import logging

    from fastapi.testclient import TestClient

    from astro_ai import cache, daily_cache
    from astro_ai.main import app
    from astro_ai.routes import kundli, llm_support

    sc = SCENARIOS[name]
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "bhagya.db")
    monkeypatch.setattr(daily_cache, "_ROOT", tmp_path / "daily_cache")
    llm_support._DURABLE_MISSES.clear()
    e = Egress(llm_mode=sc.llm_mode).install(monkeypatch)
    # Process-global rate limiters keyed by the signed-in sub, which every
    # scenario shares: left alone, the sixth run in a process would be a 429.
    monkeypatch.setattr(kundli, "_SNAPSHOT_CREATED_TODAY", {})
    monkeypatch.setattr(kundli, "_EMAIL_KUNDLI_LAST_SENT", {})
    client = TestClient(app)
    e.watch(client)
    if sc.signed_in:
        sign_in(client, monkeypatch)
    if sc.chart:
        save_chart(client)
    e.arm()
    sc.drive(client, e)
    e.log_records = list(caplog.records)
    return e


# ─── the gate ──────────────────────────────────────────────────────────────
def main() -> int:
    print("PII egress sweep (#744) — sentinels in every field, read back at every sink")
    missing = [f for f in TEST_FILES if not (ROOT / f).exists()]
    if missing:
        print(f"COULD NOT RUN — missing: {', '.join(missing)}")
        return 2
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *[str(ROOT / f) for f in TEST_FILES],
         "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
    out = result.stdout + result.stderr
    if result.returncode not in (0, 1):
        print(out[-2000:])
        print(f"COULD NOT RUN — pytest exited {result.returncode} (not a pass)")
        return 2
    # A skip, xfail or deselect is not a pass: the sweep would be absent while
    # reporting green (same rule, same reason as verify_behaviour.py).
    muted = re.search(r"(\d+)\s+(skipped|xfailed|xpassed|deselected)", out)
    passed = re.search(r"(\d+)\s+passed", out)
    count = int(passed.group(1)) if passed else 0
    print(out[-1500:] if result.returncode else "", end="")
    if result.returncode == 0 and not muted and count > 0:
        print(f"PASS ({count} tests)")
        return 0
    if muted:
        print(f"FAIL — tests did not run: {muted.group(0)}")
        return 1
    print("FAIL — a sentinel reached a sink the policy does not allow, a scenario "
          "captured less than it declared, or no test ran")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
