"""#1067 -- conversion events are DECLARED by the template and FIRED by analytics.js.

`analytics.js` loads with `defer` (base.html), so an inline top-level
`<script>Analytics.kundliGenerated(...)</script>` in the page body runs first and
throws `Analytics is not defined` on every FULL page load. `kundli_generated`,
`ask_answered` and `dasha_deep_dive_viewed` were all fired that way, and worked
only after an hx-boost swap, when `window.Analytics` already existed from an
earlier load. Nothing failed anywhere; the events were simply never sent
(`dasha_deep_dive_viewed` was absent from 28 days of GA4).

Four layers, because each is blind to the others:

  1. STATIC: no template calls `Analytics.*` from code that runs at parse time.
     (A handler or `addEventListener` callback is fine: it runs after load.)
  2. RENDER: the three real routes emit the declaring element, with the right
     name and params that parse as JSON -- and a hostile value cannot break out
     of the attribute.
     (kundli_generated and ask_answered render only on the GET that follows their
     POST, #1068: these tests reach them through the `saved_chart` / POST /ask
     fixtures, whose cookie jar carries the one-shot flag. When they fire and
     when they do not is tests/test_analytics_completion_events.py.)
  3. BEHAVIOUR (Node, the real analytics.js against a stub DOM): an event fires
     once on load, a second scan does not re-fire it, an element a swap adds later
     fires once, and a malformed payload neither throws nor blocks its neighbour.
  4. The mutation rows in scripts/mutations/2026_11_17_1067_declared_events.py
     re-break each of those and require this file to go red.

Node: `pr-gates` installs it, so under CI a missing `node` FAILS; locally it skips
(same stance as test_cta_click_event.py). Layers 1 and 2 need no Node.

What NO test here can see: that a real browser, loading a real page, delivers the
event to GA4. The Node stub reproduces `readyState` and the listener order, not
Chrome's parser. The Playwright check in the issue is the browser-level proof.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "src" / "astro_ai" / "templates"
ANALYTICS_JS = ROOT / "src" / "astro_ai" / "static" / "analytics.js"

# ── 1. static ───────────────────────────────────────────────────────────────
_SCRIPT_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
_CALL_RE = re.compile(r"\bAnalytics\.\w+\s*\(")


def _paren_close(text: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


def _brace_close(text: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


#: The Google Identity Services sign-in callback. Google's SDK invokes it only
#: after a visitor completes the OAuth popup, long after analytics.js has run, so
#: a call inside it is event-time exactly like one inside an addEventListener
#: argument (#1229: base.html's `login`). Only this one named function is allowed.
_GIS_CALLBACK_RE = re.compile(r"window\.handleGoogleSignIn\s*=\s*function\s*\([^)]*\)\s*\{")


def immediate_analytics_calls(template_text: str) -> list[str]:
    """`Analytics.*(` calls in inline <script> blocks that run at parse time.

    A call is allowed only when it sits inside the argument list of an
    `addEventListener(...)` -- a click/submit handler, or base.html's
    DOMContentLoaded callback -- because that runs after the deferred script has.
    Anything else (top level, an IIFE, a bare `if`) runs while the page is still
    parsing and is exactly the #1067 shape. Scoped to <script> blocks with no
    `src`; markup, Jinja comments and `//` comment lines are not code. An
    `onclick="Analytics...."` attribute is not scanned: it runs on a click.
    """
    bad = []
    for m in _SCRIPT_RE.finditer(template_text):
        if re.search(r"\bsrc\s*=", m.group("attrs"), re.I):
            continue
        body = "\n".join(ln for ln in m.group("body").splitlines()
                         if not ln.lstrip().startswith("//"))
        spans = [(a.end() - 1, _paren_close(body, a.end() - 1))
                 for a in re.finditer(r"addEventListener\s*\(", body)]
        spans += [(g.end() - 1, _brace_close(body, g.end() - 1))
                  for g in _GIS_CALLBACK_RE.finditer(body)]
        for c in _CALL_RE.finditer(body):
            if not any(lo < c.start() < hi for lo, hi in spans):
                bad.append(body[c.start():c.start() + 60].splitlines()[0])
    return bad


def test_the_detector_flags_the_1067_shape_and_allows_handlers():
    """The scanner must go red on the defect, or the next test proves nothing."""
    assert immediate_analytics_calls(
        "<script>Analytics.kundliGenerated({ lang: 'en' });</script>")
    assert immediate_analytics_calls(
        "<script>\n  {% if answer %}\n  Analytics.track('ask_answered', {a: 1});\n"
        "  {% endif %}\n</script>")
    assert immediate_analytics_calls(
        "<script>(function () { Analytics.track('x'); })();</script>")
    assert not immediate_analytics_calls(
        "<script>form.addEventListener('submit', function () {\n"
        "  fetch('/x').then(function (j) { Analytics.feedbackSent({type: 'a'}); });\n"
        "});</script>")
    assert not immediate_analytics_calls(
        "<script>// Analytics.track('commented out')\nvar x = 1;</script>")
    assert not immediate_analytics_calls("<p>Analytics.track('prose')</p>")
    # #1229: the Google sign-in callback is event-time; any other function is not.
    assert not immediate_analytics_calls(
        "<script>window.handleGoogleSignIn = function (r) {\n"
        "  fetch('/a').then(function (j) { Analytics.login({method: 'google'}); });\n"
        "};</script>")
    assert immediate_analytics_calls(
        "<script>window.somethingElse = function (r) { Analytics.login({method: 'google'}); };"
        "</script>")
    assert immediate_analytics_calls(
        "<script>window.handleGoogleSignIn = function (r) { };\nAnalytics.login({});</script>")


def test_no_template_calls_analytics_while_the_page_is_parsing():
    offenders = {}
    for path in sorted(TEMPLATES.rglob("*.html")):
        bad = immediate_analytics_calls(path.read_text(encoding="utf-8"))
        if bad:
            offenders[str(path.relative_to(TEMPLATES))] = bad
    assert not offenders, (
        "an inline Analytics.* call runs BEFORE the deferred analytics.js and throws "
        "'Analytics is not defined' on a full page load (#1067). Declare the event "
        "instead: {{ analytics_event('name', {...}) }} from _analytics_event.html. "
        f"Found: {offenders}")


# ── 2. render ───────────────────────────────────────────────────────────────
class _Declared(HTMLParser):
    def __init__(self):
        super().__init__()
        self.events: list[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-analytics-event" in a:
            self.events.append({"tag": tag, "hidden": "hidden" in a,
                                "name": a["data-analytics-event"],
                                "raw_params": a.get("data-analytics-params")})


def declared(html: str) -> list[dict]:
    p = _Declared()
    p.feed(html)
    return p.events


def _params(ev: dict) -> dict:
    return json.loads(ev["raw_params"])


def test_a_hostile_value_cannot_break_out_of_the_attribute():
    from astro_ai.routes.deps import templates

    tpl = templates.env.from_string(
        '{% from "_analytics_event.html" import analytics_event %}'
        "{{ analytics_event('probe', {'v': v, 'lang': 'en'}) }}"
        "<b id=after></b>")
    nasty = "\"'><script>alert(1)</script>&amp; \\u0027 </script> x=1 \n"
    out = tpl.render(v=nasty)
    evs = declared(out)
    assert len(evs) == 1, f"the value injected markup: {out!r}"
    assert evs[0]["hidden"] and evs[0]["tag"] == "div"
    assert _params(evs[0]) == {"v": nasty, "lang": "en"}, "the value did not round-trip"
    assert "<script" not in out and "id=after" in out
    # Literal quote characters never appear inside the attribute value itself.
    attr = re.search(r"data-analytics-params='(.*?)'></div>", out, re.S)
    assert attr and "'" not in attr.group(1)


def test_kundli_result_declares_kundli_generated(client, saved_chart, monkeypatch):
    from astro_ai.routes import kundli as K

    monkeypatch.setattr(K, "generate_reading", lambda *a, **k: "## Personality\n" + "Body. " * 60)
    saved_chart(name="Asha", birth_date="1990-08-15", birth_time="23:55",
                birth_place="Varanasi, India")
    r = client.get("/kundli")
    assert r.status_code == 200
    evs = [e for e in declared(r.text) if e["name"] == "kundli_generated"]
    assert len(evs) == 1 and evs[0]["hidden"], declared(r.text)
    assert _params(evs[0]) == {"lang": "en"}
    assert "Analytics.kundliGenerated" not in r.text.replace("analytics.js", "")


def test_ask_answer_declares_ask_answered_with_a_fixed_category(client, saved_chart,
                                                               stub_llm):
    stub_llm("## Answer\n" + "A canned answer body. " * 30)
    saved_chart()
    posted = client.post("/ask", data={"question": "When will I get married?",
                                       "category": "marriage", "context": "chart"},
                         follow_redirects=False)
    assert posted.status_code == 303, posted.status_code
    r = client.get(posted.headers["location"])
    assert r.status_code == 200
    evs = [e for e in declared(r.text) if e["name"] == "ask_answered"]
    assert len(evs) == 1 and evs[0]["hidden"], declared(r.text)
    assert _params(evs[0]) == {"category": "marriage", "lang": "en"}
    # The question is free text: it must be in no declared payload.
    assert "married" not in evs[0]["raw_params"]


def test_ask_without_an_answer_declares_nothing(client, saved_chart):
    saved_chart()
    r = client.get("/ask")
    assert r.status_code == 200
    assert declared(r.text) == []


def test_deep_dive_declares_dasha_deep_dive_viewed(client, saved_chart, monkeypatch):
    from astro_ai.routes import dasha as D

    monkeypatch.setattr(D, "generate_dasha_deep_dive",
                        lambda **k: "## Overview\n" + "Deep dive body. " * 40)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    saved_chart(name="Asha", birth_date="1990-08-15", birth_time="23:55",
                birth_place="Varanasi, India")
    r = client.get("/dasha/deep-dive")
    assert r.status_code == 200, r.status_code
    evs = [e for e in declared(r.text) if e["name"] == "dasha_deep_dive_viewed"]
    assert len(evs) == 1 and evs[0]["hidden"], declared(r.text)
    p = _params(evs[0])
    assert set(p) == {"mahadasha", "antardasha", "lang"}
    planets = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    assert p["mahadasha"] in planets and p["antardasha"] in planets, p
    assert p["lang"] == "en"
    assert "Asha" not in evs[0]["raw_params"], "the seeker's name is in an analytics payload"


# ── 3. behaviour: the real analytics.js under Node ───────────────────────────
# A DOM stub with just what the scan touches: querySelectorAll with the
# `:not([data-analytics-fired])` filter, get/setAttribute, addEventListener and
# readyState. No jsdom (not installed, and no npm deps may be added).
_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
const listeners = [], page = [], sent = [];
function node(d) {
  const a = {};
  if (d.event !== undefined) a['data-analytics-event'] = d.event;
  if (d.rawParams !== undefined) a['data-analytics-params'] = d.rawParams;
  return { getAttribute: k => (k in a ? a[k] : null),
           setAttribute: (k, v) => { a[k] = String(v); },
           has: k => k in a };
}
const ctx = { URL, console };
ctx.window = ctx;
ctx.BHAGYA_ANALYTICS_CONFIG = { ga4: 'G-TEST', clarity: '' };
ctx.location = { origin: 'https://shubhagya.com', href: 'https://shubhagya.com/kundli',
                 pathname: '/kundli' };
ctx.document = {
  readyState: spec.readyState,
  referrer: '',
  addEventListener: (t, f) => listeners.push([t, f]),
  createElement: () => ({}), head: { appendChild() {} },
  getElementsByTagName: () => [], getElementById: () => null,
  querySelectorAll: sel => {
    if (sel.indexOf('[data-analytics-event]') < 0) return [];
    return page.filter(n => n.has('data-analytics-event') &&
      !(sel.indexOf(':not([data-analytics-fired])') >= 0 && n.has('data-analytics-fired')));
  },
};
for (const d of spec.initial || []) page.push(node(d));
vm.createContext(ctx);
vm.runInContext(src, ctx);
const events = () => (ctx.dataLayer || []).map(a => Array.prototype.slice.call(a))
  .filter(c => c[0] === 'event' && c[1] !== 'user_identified');
const fire = t => { for (const [n, f] of listeners) if (n === t) f({}); };
const out = { thrown: [], listeners: listeners.map(l => l[0]), steps: [] };
try {
  for (const step of spec.steps || []) {
    if (step.op === 'dcl') fire('DOMContentLoaded');
    if (step.op === 'settle') fire('htmx:afterSettle');
    if (step.op === 'add') for (const d of step.nodes) page.push(node(d));
    out.steps.push(events());
  }
  out.final = events();
  out.fired = page.map(n => n.has('data-analytics-fired'));
} catch (e) { out.thrown.push(String(e)); }
process.stdout.write(JSON.stringify(out));
"""

NODE = shutil.which("node")


@pytest.fixture
def node_present():
    if NODE is None:
        if os.environ.get("CI"):
            pytest.fail("node is missing under CI: pr-gates installs Node 22, so a "
                        "missing binary means this gate is not running at all")
        pytest.skip("no node on this box; CI installs it and fails if it is absent")


def _run(tmp_path, **spec):
    drv = tmp_path / "driver.js"
    drv.write_text(_DRIVER)
    r = subprocess.run([NODE, str(drv), str(ANALYTICS_JS)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["thrown"] == [], out["thrown"]
    return out


KUNDLI = {"event": "kundli_generated", "rawParams": '{"lang":"en"}'}
ASK = {"event": "ask_answered", "rawParams": '{"category":"career","lang":"hi"}'}


def test_a_declared_event_fires_once_on_domcontentloaded(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading", initial=[KUNDLI],
               steps=[{"op": "none"}, {"op": "dcl"}])
    assert out["steps"][0] == [], "fired before the document finished parsing"
    assert out["final"] == [["event", "kundli_generated", {"lang": "en"}]], out["final"]
    assert out["fired"] == [True]


def test_a_deferred_script_fires_immediately_without_waiting_for_dcl(node_present, tmp_path):
    """A deferred script runs with readyState 'interactive', after parsing: the
    exact moment the old inline call lost the race."""
    out = _run(tmp_path, readyState="interactive", initial=[KUNDLI], steps=[])
    assert out["final"] == [["event", "kundli_generated", {"lang": "en"}]], out["final"]


def test_dcl_after_an_immediate_scan_does_not_fire_it_again(node_present, tmp_path):
    out = _run(tmp_path, readyState="interactive", initial=[KUNDLI],
               steps=[{"op": "dcl"}, {"op": "settle"}])
    assert len(out["final"]) == 1, out["final"]


def test_a_second_scan_after_settle_does_not_refire(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading", initial=[KUNDLI],
               steps=[{"op": "dcl"}, {"op": "settle"}, {"op": "settle"}])
    assert len(out["final"]) == 1, out["final"]


def test_an_element_added_by_a_swap_fires_once_and_only_once(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading", initial=[KUNDLI],
               steps=[{"op": "dcl"}, {"op": "add", "nodes": [ASK]},
                      {"op": "settle"}, {"op": "settle"}])
    names = [e[1] for e in out["final"]]
    assert names == ["kundli_generated", "ask_answered"], names
    assert out["final"][1][2] == {"category": "career", "lang": "hi"}


def test_the_swap_listener_is_registered(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading", steps=[])
    assert "htmx:afterSettle" in out["listeners"], out["listeners"]
    assert "DOMContentLoaded" in out["listeners"], out["listeners"]


def test_malformed_params_throw_nothing_and_do_not_stop_the_next_event(node_present,
                                                                      tmp_path):
    bad = {"event": "kundli_generated", "rawParams": "{not json"}
    out = _run(tmp_path, readyState="loading", initial=[bad, ASK],
               steps=[{"op": "dcl"}, {"op": "settle"}])
    names = [e[1] for e in out["final"]]
    assert names == ["kundli_generated", "ask_answered"], names
    assert out["final"][0][2] == {}, "an unparsed payload must send no params"
    assert out["fired"] == [True, True], "a bad element is stamped, so it is not retried"


@pytest.mark.parametrize("raw", ["[1,2]", "null", '"str"', "7", ""])
def test_non_object_payloads_send_no_params(node_present, tmp_path, raw):
    out = _run(tmp_path, readyState="loading",
               initial=[{"event": "kundli_generated", "rawParams": raw}],
               steps=[{"op": "dcl"}])
    assert out["final"] == [["event", "kundli_generated", {}]], out["final"]


def test_only_scalar_params_survive(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading",
               initial=[{"event": "kundli_generated",
                         "rawParams": '{"lang":"en","n":3,"ok":true,"nest":{"a":1},"arr":[1]}'}],
               steps=[{"op": "dcl"}])
    assert out["final"][0][2] == {"lang": "en", "n": 3, "ok": True}


def test_an_element_with_no_event_name_is_skipped_but_stamped(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading",
               initial=[{"event": "", "rawParams": "{}"}, KUNDLI],
               steps=[{"op": "dcl"}, {"op": "settle"}])
    assert [e[1] for e in out["final"]] == ["kundli_generated"]
    assert out["fired"] == [True, True]


def test_a_page_with_nothing_declared_sends_nothing(node_present, tmp_path):
    out = _run(tmp_path, readyState="loading", steps=[{"op": "dcl"}, {"op": "settle"}])
    assert out["final"] == []
