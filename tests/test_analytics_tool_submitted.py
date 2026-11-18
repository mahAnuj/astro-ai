"""#1226 -- `tool_submitted`: the denominator for slice 1's completion events
(#1217), sent by ONE delegated `submit` listener in analytics.js from
`form[data-tool]` (#1070 row 1).

Three layers, because each is blind to the others:

  1. RENDER: every route that serves a tool form puts the right `data-tool` on the
     right `<form>`, read out of the HTML a visitor receives -- including the POST
     error re-render of the three dosha checks, which is the same template.
  2. STATIC: every `<form>` in templates/ that posts to a tool action carries a
     `data-tool` (so a NEW page for a tool cannot silently stay uncounted), no
     template names `tool_submitted` itself (the event is fired by the listener,
     not declared, and an inline `Analytics.` call is forbidden by
     test_analytics_declared_events), and analytics.js has exactly one submit
     listener whose vocabulary is exactly the values the templates use.
  3. BEHAVIOUR (Node, the real analytics.js against a stub DOM): a valid
     `data-tool` sends one `tool_submitted` carrying ONLY `{tool}`; an unknown,
     empty, missing or injected value sends nothing; a form that appears after load
     (an hx-boost swap) is still counted because the listener is on `document`; the
     listener only observes.

Node: `pr-gates` installs it, so under CI a missing `node` FAILS; locally it skips
(same stance as test_cta_click_event.py). Layers 1 and 2 need no Node.

What NO test here can see: that a real browser raises `submit` on an hx-boost form
and GA4 receives it. The stub reproduces listener registration and event shape,
not Chrome's form validation or htmx. The `form_submit` figure in GA4 after deploy
is the browser-level proof (#1226 metric: >= 6 of 9 tools with a non-zero count).

Mutation rows: scripts/mutations/2026_11_18_1226_tool_submitted.py.
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

#: The vocabulary #1226 specifies. Typed out here on purpose: if analytics.js or a
#: template drifts, this is the fixed point they are compared against.
ENUM = {"kundli", "matching", "numerology", "numerology_compat", "muhurat",
        "manglik", "sade_sati", "kaal_sarp", "ask"}

#: form action -> the tool it submits. /dasha's form posts the same birth chart to
#: /reading as the Kundli form, so it counts as `kundli` (there is no dasha tool in
#: the enum, and the completion it leads to is kundli_generated).
ACTION_TOOL = {
    "/reading": "kundli",
    "/matching": "matching",
    "/numerology": "numerology",
    "/numerology/compatibility": "numerology_compat",
    "/muhurat": "muhurat",
    "/manglik-check": "manglik",
    "/sade-sati-check": "sade_sati",
    "/kaal-sarp-check": "kaal_sarp",
    "/ask": "ask",
}


class _Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "form":
            self.forms.append(dict(attrs))


def forms_of(resp) -> list[dict]:
    p = _Forms()
    p.feed(resp.text)
    return p.forms


def tool_forms(resp) -> list[tuple[str, str | None]]:
    """(action, data-tool) for every form on the page that posts to a tool."""
    return [(f.get("action"), f.get("data-tool")) for f in forms_of(resp)
            if f.get("action") in ACTION_TOOL]


# ── 1. render ───────────────────────────────────────────────────────────────
#: route -> the (action, data-tool) pairs it must carry, each exactly once.
GET_PAGES = {
    "/": [("/reading", "kundli")],
    "/kundli": [("/reading", "kundli")],            # no saved chart -> landing page
    "/dasha": [("/reading", "kundli")],
    "/matching": [("/matching", "matching")],
    "/numerology": [("/numerology", "numerology")],
    "/numerology/compatibility": [("/numerology/compatibility", "numerology_compat")],
    "/muhurat": [("/muhurat", "muhurat")],
    "/muhurat/vivah": [("/muhurat", "muhurat")],
    "/manglik-check": [("/manglik-check", "manglik")],
    "/sade-sati-check": [("/sade-sati-check", "sade_sati")],
    "/kaal-sarp-check": [("/kaal-sarp-check", "kaal_sarp")],
}


@pytest.mark.parametrize("path", sorted(GET_PAGES))
def test_the_tool_form_on_each_page_carries_its_tool(client, path):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    assert tool_forms(r) == GET_PAGES[path], (path, tool_forms(r))


def test_the_ask_form_carries_its_tool(client, saved_chart):
    """/ask redirects home without a saved chart (routes/ask.py), so it needs one."""
    saved_chart()
    r = client.get("/ask")
    assert r.status_code == 200
    assert tool_forms(r) == [("/ask", "ask")], tool_forms(r)
    answered = client.get("/ask?q=a+very+private+question&c=general")
    assert answered.status_code == 200
    assert tool_forms(answered) == [("/ask", "ask")]


def test_the_home_page_second_chart_form_is_counted_too(client, saved_chart):
    """With a saved chart `/` shows 'Save another chart' (also POST /reading, and
    kundli_generated fires after it), so it must be in the denominator as well."""
    saved_chart()
    r = client.get("/")
    assert r.status_code == 200
    got = tool_forms(r)
    assert got and all(pair == ("/reading", "kundli") for pair in got), got


@pytest.mark.parametrize("path,tool", [
    ("/manglik-check", "manglik"), ("/sade-sati-check", "sade_sati"),
    ("/kaal-sarp-check", "kaal_sarp"),
])
def test_a_dosha_error_rerender_keeps_the_tool(client, path, tool):
    """The POST error page is the same template and must stay countable, else a
    visitor who mistyped and resubmitted is invisible."""
    r = client.post(path, data={"name": "", "birth_date": "not-a-date",
                                "birth_time": "14:35", "birth_place": "Mumbai, India"})
    assert r.status_code >= 400, r.status_code
    assert tool_forms(r) == [(path, tool)], tool_forms(r)


def test_every_landing_event_page_gets_the_muhurat_tool(client):
    from astro_ai.muhurat import EVENT_LANDING
    assert EVENT_LANDING, "no landing pages to check"
    for key in EVENT_LANDING:
        r = client.get("/muhurat/" + key.replace("_", "-"))
        assert r.status_code == 200, key
        assert tool_forms(r) == [("/muhurat", "muhurat")], key


# ── 2. static ───────────────────────────────────────────────────────────────
_FORM_TAG = re.compile(r"<form\b[^>]*>", re.S)


def _template_forms():
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for m in _FORM_TAG.finditer(text):
            yield path.relative_to(TEMPLATES).as_posix(), m.group(0)


def test_every_template_form_that_posts_to_a_tool_carries_data_tool():
    missing, seen = [], 0
    for name, tag in _template_forms():
        action = re.search(r'action="([^"]*)"', tag)
        if not action:
            continue
        act = action.group(1)
        # dosha_check_form.html renders its action from a variable.
        is_tool = act in ACTION_TOOL or act == "{{ form_action }}"
        if is_tool:
            seen += 1
            if "data-tool" not in tag:
                missing.append((name, act))
    assert seen >= 11, f"expected the 11 tool forms in templates/, found {seen}"
    assert not missing, (
        "a tool form with no data-tool is never counted in tool_submitted, which "
        f"makes that tool's completion ratio unreadable (#1226): {missing}")


def test_the_forms_that_are_not_tools_stay_uncounted():
    """lang, reset, delete, switch, feedback, subscribe, panchang and the admin day
    picker are not tools: counting them would put non-tool traffic in the
    denominator, and `tool` is a closed enum they are not in."""
    for name, tag in _template_forms():
        action = re.search(r'action="([^"]*)"', tag)
        if (action and action.group(1) in ACTION_TOOL) or "{{ form_action }}" in tag:
            continue
        assert "data-tool" not in tag, (name, tag)


def test_templates_never_name_tool_submitted():
    """It is fired by the listener from the form attribute. A marker or inline call
    in a template would double-count it."""
    offenders = [p.relative_to(TEMPLATES).as_posix()
                 for p in sorted(TEMPLATES.rglob("*.html"))
                 if "tool_submitted" in p.read_text(encoding="utf-8")
                 or "toolSubmitted" in p.read_text(encoding="utf-8")]
    assert not offenders, offenders


def _templates_data_tool_values() -> set[str]:
    vals: set[str] = set()
    for name, tag in _template_forms():
        m = re.search(r'data-tool="([^"]*)"', tag)
        if m and "{{" not in m.group(1):
            vals.add(m.group(1))
    # The dosha template derives its value from a dict keyed by form_action.
    text = (TEMPLATES / "dosha_check_form.html").read_text(encoding="utf-8")
    d = re.search(r"\{% set _tool = \{(.*?)\}\.get\(form_action\)", text, re.S)
    assert d, "dosha_check_form.html no longer derives data-tool from form_action"
    vals |= set(re.findall(r":\s*'([a-z_]+)'", d.group(1)))
    return vals


def test_the_template_values_are_exactly_the_enum():
    assert _templates_data_tool_values() == ENUM


def test_analytics_js_has_one_delegated_submit_listener_with_that_vocabulary():
    js = ANALYTICS_JS.read_text(encoding="utf-8")
    assert len(re.findall(r"document\.addEventListener\(\s*'submit'", js)) == 1
    assert len(re.findall(r"addEventListener\(\s*'submit'", js)) == 1, \
        "a submit listener bound to anything but document is not hx-boost safe"
    m = re.search(r"var TOOL_NAMES = \[(.*?)\];", js, re.S)
    assert m, "TOOL_NAMES is gone"
    assert set(re.findall(r"'([a-z_]+)'", m.group(1))) == ENUM
    assert len(re.findall(r"track\(\s*'tool_submitted'", js)) == 1
    assert re.search(r"closest\(\s*'form\[data-tool\]'\s*\)", js)


# ── 3. behaviour under Node ─────────────────────────────────────────────────
_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));

function el(tag, parent, attrs) {
  const e = { tag, parentElement: parent || null, attrs: attrs || {}, nodeType: 1 };
  e.getAttribute = (n) => (n in e.attrs ? e.attrs[n] : null);
  e.closest = (sel) => {
    // Only the selector analytics.js uses: tag[attr].
    const m = /^([a-z]+)\[([a-z-]+)\]$/.exec(sel);
    if (!m) throw new Error('stub cannot answer closest(' + sel + ')');
    for (let n = e; n; n = n.parentElement) {
      if (n.tag === m[1] && m[2] in n.attrs) return n;
    }
    return null;
  };
  return e;
}

const calls = [], listeners = [];
const ctx = { URL, console };
ctx.window = ctx;
ctx.location = { origin: spec.origin, pathname: '/matching', href: spec.origin + '/matching' };
ctx.document = {
  addEventListener: (t, f) => listeners.push([t, f]),
  createElement: () => ({}), head: { appendChild() {} },
  getElementsByTagName: () => [], getElementById: () => null,
  querySelectorAll: () => [], readyState: 'complete',
};
ctx.gtag = (...a) => calls.push(['gtag', ...a]);
ctx.clarity = (...a) => calls.push(['clarity', ...a]);
vm.createContext(ctx);
vm.runInContext(src, ctx);

const out = { listeners: listeners.map(l => l[0]), thrown: [], prevented: 0, stopped: 0, perSubmit: [] };
const events = () => calls.filter(x => x[0] === 'gtag' && x[1] === 'event');
for (const s of spec.submits) {
  const body = el('body');
  const attrs = s.attrs || {};
  const form = el('form', body, attrs);
  let target = form;
  if (s.target === 'child') target = el('button', form);
  if (s.target === 'textnode') target = { nodeType: 3 };
  if (s.target === 'null') target = null;
  if (s.target === 'formless') target = el('div', body);
  const ev = { target, preventDefault() { out.prevented++; }, stopPropagation() { out.stopped++; } };
  const before = events().length;
  try { for (const [t, f] of listeners) if (t === 'submit') f(ev); }
  catch (e) { out.thrown.push(String(e)); }
  out.perSubmit.push(events().length - before);
}
if (spec.direct) {
  try {
    ctx.Analytics.toolSubmitted();
    ctx.Analytics.toolSubmitted({ tool: 'ask', name: 'secret', birth_place: 'Mumbai' });
    ctx.Analytics.toolSubmitted({ tool: 'nope' });
  } catch (e) { out.thrown.push(String(e)); }
}
out.calls = calls;
process.stdout.write(JSON.stringify(out));
"""

NODE = shutil.which("node")


@pytest.fixture
def _node_present():
    if NODE is None:
        if os.environ.get("CI"):
            pytest.fail("node is missing under CI: pr-gates installs Node 22, so a "
                        "missing binary means this gate is not running at all")
        pytest.skip("no node on this box; CI installs it and fails if it is absent")


def _run(tmp_path, submits, direct=False):
    drv = tmp_path / "driver.js"
    drv.write_text(_DRIVER)
    spec = {"origin": "https://shubhagya.com", "submits": submits, "direct": direct}
    r = subprocess.run([NODE, str(drv), str(ANALYTICS_JS)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _events(out):
    return [c for c in out["calls"] if c[0] == "gtag" and c[1] == "event"]


def test_each_enum_value_sends_one_tool_submitted_with_only_tool(tmp_path, _node_present):
    order = sorted(ENUM)
    out = _run(tmp_path, [{"attrs": {"data-tool": t, "data-name": "Priya",
                                     "action": "/x?q=secret"}} for t in order])
    assert [t for t in out["listeners"] if t == "submit"] == ["submit"], \
        "exactly one delegated submit listener"
    assert out["thrown"] == []
    assert out["perSubmit"] == [1] * len(order)
    for (_, _, name, params), tool in zip(_events(out), order):
        assert name == "tool_submitted"
        assert params == {"tool": tool}, params
    assert out["prevented"] == 0 and out["stopped"] == 0, "the listener only observes"
    assert ["clarity", "event", "tool_submitted"] in out["calls"]


@pytest.mark.parametrize("attrs", [
    {"data-tool": "nope"},
    {"data-tool": ""},
    {"data-tool": "Kundli"},                        # case is part of the contract
    {"data-tool": "kundli "},                       # no trimming
    {"data-tool": "kundli&name=Priya"},
    {"data-tool": "__proto__"},
    {"data-tool": "constructor"},                   # an Object.prototype key, not a tool
    {"data-tool": "ask,matching"},
    {},                                             # a data-tool-less form is not a tool
])
def test_an_unknown_or_missing_value_sends_nothing(tmp_path, _node_present, attrs):
    out = _run(tmp_path, [{"attrs": attrs}])
    assert out["thrown"] == []
    assert out["perSubmit"] == [0], _events(out)
    assert _events(out) == []


def test_a_submit_from_inside_a_tool_form_or_with_odd_targets_is_safe(tmp_path, _node_present):
    out = _run(tmp_path, [
        {"attrs": {"data-tool": "ask"}, "target": "child"},     # the button, bubbling up
        {"attrs": {"data-tool": "ask"}, "target": "textnode"},
        {"attrs": {"data-tool": "ask"}, "target": "null"},
        {"attrs": {"data-tool": "ask"}, "target": "formless"},  # inside no form[data-tool]
    ])
    assert out["thrown"] == []
    assert out["perSubmit"] == [1, 0, 0, 0]
    assert _events(out)[0][3] == {"tool": "ask"}


def test_the_listener_is_on_document_so_a_form_added_after_load_counts(tmp_path, _node_present):
    """hx-boost replaces body children without reloading analytics.js. The stub
    creates each form AFTER the script ran and dispatches through the listener that
    `document` holds -- the only registration there is."""
    out = _run(tmp_path, [{"attrs": {"data-tool": "matching"}}])
    assert out["perSubmit"] == [1]
    assert out["listeners"].count("submit") == 1


def test_a_direct_call_cannot_widen_the_params(tmp_path, _node_present):
    out = _run(tmp_path, [], direct=True)
    assert out["thrown"] == []
    ev = _events(out)
    assert len(ev) == 1, ev                       # undefined and 'nope' sent nothing
    assert ev[0][2:] == ["tool_submitted", {"tool": "ask"}], ev
