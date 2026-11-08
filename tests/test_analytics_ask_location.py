"""#528 -- a visitor's `/ask` question must not reach GA4 as the page URL.

POST /ask answers with a 303 to `/ask?q=<the whole question>&c=<category>` (a
deliberate, shareable URL), and `analytics.js` used to run
`gtag('config', id, {anonymize_ip: true})` with no `page_location`, so GA4 stored
the full URL. The 28-day export held `/ask?q=But+you+said+i+am+very+unlikely+to+get+
stable+relstionship.&c=general` as a landing page.

Nothing in the Python suite executes JavaScript, so these tests RUN the real
`static/analytics.js` under Node against a stub DOM and assert what reaches `gtag`:

  * on a URL carrying `q`, `config` carries a `page_location` with `q` removed;
  * the question text appears nowhere in anything sent to `gtag`;
  * on every other URL `config` carries NO `page_location` (a config parameter
    sticks to later events, so a blanket override would mis-attribute them);
  * after an hx-boost navigation the override is reset to the real URL, once.

Node: under CI a missing `node` FAILS; locally it skips (same stance as
test_cta_click_event.py).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ANALYTICS_JS = ROOT / "src" / "astro_ai" / "static" / "analytics.js"
ORIGIN = "https://shubhagya.com"
QUESTION = "But+you+said+i+am+very+unlikely+to+get+stable+relstionship."

_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
const calls = [], listeners = [];
const ctx = { URL, console };
ctx.window = ctx;
ctx.BHAGYA_ANALYTICS_CONFIG = { ga4: 'G-TEST', clarity: '' };
const loc = { origin: spec.origin, href: spec.origin + spec.path };
Object.defineProperty(loc, 'pathname', { get: () => new URL(loc.href).pathname });
ctx.location = loc;
ctx.document = {
  addEventListener: (t, f) => listeners.push([t, f]),
  createElement: () => ({}), head: { appendChild() {} },
  getElementsByTagName: () => [], getElementById: () => null,
};
vm.createContext(ctx);
vm.runInContext(src, ctx);
// The real gtag pushes into dataLayer; read it back as the sequence of calls.
const seen = () => (ctx.dataLayer || []).map(a => Array.prototype.slice.call(a));
const out = { thrown: [] };
try {
  out.initial = seen();
  if (spec.navigateTo) {
    loc.href = spec.origin + spec.navigateTo;
    for (const [t, f] of listeners) if (t === 'htmx:pushedIntoHistory') f({});
    out.afterNav = seen();
    for (const [t, f] of listeners) if (t === 'htmx:pushedIntoHistory') f({});
    out.afterSecondNav = seen();
  }
  if (spec.pageView) { ctx.Analytics.pageView(); out.afterPageView = seen(); }
} catch (e) { out.thrown.push(String(e)); }
process.stdout.write(JSON.stringify(out));
"""

NODE = shutil.which("node")


@pytest.fixture(scope="module", autouse=True)
def _node_present():
    if NODE is None:
        if os.environ.get("CI"):
            pytest.fail("node is missing under CI: pr-gates installs Node 22, so a "
                        "missing binary means this gate is not running at all")
        pytest.skip("no node on this box; CI installs it and fails if it is absent")


def _run(tmp_path, path, **extra):
    drv = tmp_path / "driver.js"
    drv.write_text(_DRIVER)
    spec = {"origin": ORIGIN, "path": path, **extra}
    r = subprocess.run([NODE, str(drv), str(ANALYTICS_JS)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["thrown"] == [], out["thrown"]
    return out


def _config(calls):
    cfgs = [c for c in calls if c[0] == "config"]
    assert len(cfgs) == 1, calls
    return cfgs[0][2]


def test_ask_question_never_reaches_gtag_config(tmp_path):
    out = _run(tmp_path, f"/ask?q={QUESTION}&c=general")
    cfg = _config(out["initial"])
    assert cfg["anonymize_ip"] is True
    assert cfg["page_location"] == f"{ORIGIN}/ask?c=general"
    blob = json.dumps(out["initial"])
    assert "relstionship" not in blob and "unlikely" not in blob and "q=" not in blob


def test_hindi_prefixed_ask_is_stripped_too(tmp_path):
    out = _run(tmp_path, f"/hi/ask?q={QUESTION}")
    assert _config(out["initial"])["page_location"] == f"{ORIGIN}/hi/ask"


def test_percent_encoded_and_repeated_q_are_both_removed(tmp_path):
    out = _run(tmp_path, "/ask?q=a%20private%20thing&q=second&c=love&utm_source=x")
    loc = _config(out["initial"])["page_location"]
    assert "private" not in loc and "second" not in loc
    assert "c=love" in loc and "utm_source=x" in loc


@pytest.mark.parametrize("path", ["/", "/ask", "/ask?c=general", "/learn/sade-sati/",
                                  "/rashifal/aries?utm_source=x"])
def test_urls_without_q_get_no_override(tmp_path, path):
    """A config parameter sticks to later events: override only when needed."""
    out = _run(tmp_path, path)
    assert "page_location" not in _config(out["initial"])


def test_override_is_reset_once_after_a_boosted_navigation(tmp_path):
    out = _run(tmp_path, f"/ask?q={QUESTION}", navigateTo="/kundli")
    sets = lambda calls: [c for c in calls if c[0] == "set"]
    assert sets(out["initial"]) == []
    after = sets(out["afterNav"])
    assert [c[1] for c in after] == [{"page_location": f"{ORIGIN}/kundli"}]
    # Once reset, further navigations send nothing more.
    assert sets(out["afterSecondNav"]) == after


def test_navigation_on_a_page_never_overridden_sends_no_set(tmp_path):
    out = _run(tmp_path, "/learn/sade-sati/", navigateTo="/kundli")
    assert [c for c in out["afterNav"] if c[0] == "set"] == []


def test_manual_page_view_carries_the_sanitised_location(tmp_path):
    out = _run(tmp_path, f"/ask?q={QUESTION}&c=general", pageView=True)
    ev = [c for c in out["afterPageView"] if c[0] == "event" and c[1] == "page_view"]
    assert len(ev) == 1
    assert ev[0][2]["page_location"] == f"{ORIGIN}/ask?c=general"
    assert "relstionship" not in json.dumps(ev)
