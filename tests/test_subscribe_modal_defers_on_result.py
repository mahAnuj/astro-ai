"""The subscribe modal must not open over a tool result (#382).

Measured on production 2026-10-15, 10-29 and 11-06: on a fresh profile,
submitting /numerology or /matching renders the result, the page's own script
counts that load as "visit 2" (`SHOW_AT_VISITS = [2, 5]`) and 1.5 s later a
full-screen "Rashifal in your inbox" modal covers the score the visitor came for.

The fix is two halves, and each is pinned here because either alone is inert:

  * the result states of /matching, /numerology and /numerology/compatibility
    render `<span data-subscribe-defer hidden>`; the empty forms do not;
  * `_subscribe_modal.html` returns on that marker BEFORE it counts the visit, so
    the next ordinary load is the one that reaches the threshold (a marker check
    placed after the increment would skip visit 2 and wait for visit 5).

The JS itself has no browser test here, so the second half is an ordering check
on the template source, and the first half drives the real routes.
"""
from __future__ import annotations

import re
from pathlib import Path

_MODAL = Path(__file__).resolve().parents[1] / "src/astro_ai/templates/_subscribe_modal.html"
_MARK = "<span data-subscribe-defer hidden></span>"   # the element, not the attribute name: the modal script quotes the name


def _post_matching(client, stub_llm):
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)
    r = client.post("/matching", data={
        "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00",
        "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": "1990-01-10", "b_birth_time": "10:00",
        "b_birth_place": "Mumbai",
    })
    assert r.status_code == 200, r.status_code
    return r.text


def test_matching_result_carries_the_defer_marker(client, stub_llm):
    assert _MARK in _post_matching(client, stub_llm)


def test_matching_empty_form_does_not(client):
    r = client.get("/matching")
    assert r.status_code == 200
    assert _MARK not in r.text


def test_numerology_result_carries_the_defer_marker(client):
    r = client.post("/numerology", data={"name": "Asha Rao", "birth_date": "1990-05-17"})
    assert r.status_code == 200
    assert "Life Path" in r.text, "the reading did not render; the test proves nothing"
    assert _MARK in r.text


def test_numerology_empty_form_does_not(client):
    r = client.get("/numerology")
    assert r.status_code == 200
    assert _MARK not in r.text


def test_numerology_compat_form_does_not(client):
    r = client.get("/numerology/compatibility")
    assert r.status_code == 200
    assert _MARK not in r.text


def test_the_gate_checks_the_marker_before_it_counts_the_visit():
    src = _MODAL.read_text(encoding="utf-8")
    gate = src[src.index("Auto-show gate"):]
    marker = gate.index("data-subscribe-defer")
    assert re.search(r"if \(document\.querySelector\('\[data-subscribe-defer\]'\)\) return;",
                     gate), "the marker is not checked with an early return"
    assert marker < gate.index("localStorage.setItem(VISITS_KEY"), (
        "the marker is checked after the visit is counted: a result load would "
        "burn visit 2 and push the prompt out to visit 5")
    assert marker > gate.index("INTENT_KEY) !== '1') return"), (
        "the marker check must come after the intent gate, which it is a refinement of")


# ---------------------------------------------------------------------------
# #309: the same rule for the EMPTY calculator form.
#
# #382 covered the result loads, which can carry a marker. An empty form renders
# no marker, so on a repeat visit (`bhagya_visit_count` 1 -> 2) the modal opened
# over /numerology, /matching, /muhurat, /panchang and /kundli before the visitor
# had typed a thing. The gate now also returns on the tool PATHS, before counting.
#
# These run the page's REAL gate script under Node with a stubbed window,
# localStorage and DOM, because an ordering check on the source cannot tell
# whether a visitor on /numerology is shown the modal, which is the claim.
# ---------------------------------------------------------------------------
import json
import shutil
import subprocess

import pytest

_NODE = shutil.which("node")

_HARNESS = r"""
const html = require('fs').readFileSync(0, 'utf8');
const cases = JSON.parse(process.argv[1]);
const m = html.match(/<script>\s*\/\/ Subscribe modal: visit-counter[\s\S]*?<\/script>/);
if (!m) { console.log(JSON.stringify({error: 'gate script not found'})); process.exit(0); }
const src = m[0].replace(/^<script>/, '').replace(/<\/script>$/, '');
function stub() {
  const f = function () { return stub(); };
  return new Proxy(f, {
    get: (t, p) => p === Symbol.toPrimitive ? () => '' : (p === 'length' ? 0 : stub()),
    set: () => true,
    apply: () => stub(),
  });
}
const out = {};
for (const c of cases) {
  const store = Object.assign({}, c.storage);
  let timers = 0;
  const ctx = {
    window: {location: {pathname: c.path}},
    localStorage: {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: k => { delete store[k]; },
    },
    document: {
      getElementById: () => stub(),
      querySelector: sel => (sel === '[data-subscribe-defer]' && c.marker ? stub() : null),
      querySelectorAll: () => [],
      addEventListener: () => {},
      body: stub(),
    },
    setTimeout: (fn, ms) => { if (ms === 1500) timers++; return 0; },
    clearTimeout: () => {},
    fetch: () => Promise.resolve(),
    Analytics: stub(), FormData: function () {},
  };
  new Function(...Object.keys(ctx), src)(...Object.values(ctx));
  out[c.name] = {shown: timers === 1, visits: store['bhagya_visit_count'] || null};
}
console.log(JSON.stringify(out));
"""


def _run_gate(client, cases):
    """Render a real page, lift its gate script, run each case: did it schedule the modal?"""
    page = client.get("/learn").text
    assert "bhagya_visit_count" in page, "the modal script is not on the page; the test proves nothing"
    r = subprocess.run([_NODE, "-e", _HARNESS, json.dumps(cases)], input=page,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "error" not in out, out
    return out


# A returning visitor with intent set and one counted visit: the next COUNTED load is
# visit 2, which is in SHOW_AT_VISITS, so any page that counts it must open the modal.
_RETURNING = {"bhagya_rashifal_intent": "1", "bhagya_visit_count": "1"}
_TOOL_PATHS = ["/numerology", "/kundli", "/muhurat", "/panchang", "/matching",
               "/numerology/compatibility", "/muhurat/wedding", "/panchang/2026-11-11"]


@pytest.mark.skipif(_NODE is None, reason="node not installed; the gate script cannot be run")
def test_empty_calculator_forms_never_open_the_modal(client):
    cases = [{"name": p, "path": p, "storage": _RETURNING} for p in _TOOL_PATHS]
    out = _run_gate(client, cases)
    for p in _TOOL_PATHS:
        assert out[p]["shown"] is False, f"the subscribe modal opens over {p}"
        assert out[p]["visits"] == "1", (
            f"{p} counted a visit ({out[p]['visits']}); the prompt would skip to visit 5")


@pytest.mark.skipif(_NODE is None, reason="node not installed; the gate script cannot be run")
def test_the_modal_still_opens_on_the_next_load_outside_the_tools(client):
    # The control: with the same storage, a page that is not a tool counts visit 2 and
    # schedules the modal. Without it a gate that never shows anything would pass above.
    cases = [{"name": p, "path": p, "storage": _RETURNING}
             for p in ["/learn/sade-sati/", "/", "/rashifal/aries", "/ask"]]
    out = _run_gate(client, cases)
    for c in cases:
        assert out[c["name"]]["shown"] is True, f"{c['name']} no longer reaches the show threshold"
        assert out[c["name"]]["visits"] == "2"

