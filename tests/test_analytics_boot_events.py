"""#1069 -- no `feature_view`, no `user_identified` event; user properties are SET once.

base.html used to run an inline DOMContentLoaded script that called
`Analytics.userIdentified(BHAGYA_USER_PROPS)` and `Analytics.featureView(<first path
segment>)`. <body> is hx-boost, so a boosted navigation never re-runs it: GA4's
`feature_view` was a count of FULL page loads, not feature views, and
`user_identified` (701 events in 28 days, the second-largest event) carried no
behaviour at all. GA4's own page_view already covers every page, boosted or not.

What replaced them is not an event: analytics.js, in its GA4 bootstrap, sends the
sticky `gtag('set', 'user_properties', window.BHAGYA_USER_PROPS)` once per full load
(base.html defines BHAGYA_USER_PROPS in a plain <script> BEFORE the deferred file).

Layers:
  1. STATIC: base.html and analytics.js name none of the removed methods, and
     base.html has no inline script that listens for DOMContentLoaded or calls
     Analytics. (Needs no Node.)
  2. RENDER: a real page still defines BHAGYA_USER_PROPS, with enum-only values.
  3. BEHAVIOUR (Node, the real analytics.js against a stub DOM): boot sends exactly
     one user_properties `set` and no event; DOMContentLoaded, htmx:afterSettle and
     htmx:pushedIntoHistory send no feature_view and no user_identified; a missing
     or malformed BHAGYA_USER_PROPS, and GA4 being unconfigured, neither throw nor
     send anything.

Node: `pr-gates` installs it, so under CI a missing `node` FAILS; locally it skips.

What NO test here can see: that GA4 attaches the property to later events in a real
browser, or that a boosted history-change page_view is recorded. The GA4 counts after
deploy (feature_view and user_identified falling to 0) are the browser-level proof.

Mutation rows: scripts/mutations/2026_11_19_1069_ga4_boot_events.py.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BASE_HTML = ROOT / "src" / "astro_ai" / "templates" / "base.html"
ANALYTICS_JS = ROOT / "src" / "astro_ai" / "static" / "analytics.js"

REMOVED = ["featureView", "userIdentified", "pwaInstalled"]
PROPS = {"age_bucket": "30-40", "lang": "hi", "has_chart": "yes"}


# ── 1. static ───────────────────────────────────────────────────────────────
def test_base_html_names_none_of_the_removed_methods():
    text = BASE_HTML.read_text(encoding="utf-8")
    for name in REMOVED:
        assert name not in text, f"base.html still mentions {name} (#1069)"


def test_base_html_has_no_inline_domcontentloaded_analytics_script():
    """Every inline <script> in base.html: none listens for DOMContentLoaded and
    none calls `Analytics.*` -- that was the removed feature_view/user_identified
    block, and it was blind to hx-boost."""
    text = BASE_HTML.read_text(encoding="utf-8")
    for m in re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", text, re.S | re.I):
        if re.search(r"\bsrc\s*=", m.group("attrs"), re.I):
            continue
        code = "\n".join(ln for ln in m.group("body").splitlines()
                         if not ln.lstrip().startswith("//"))
        assert "DOMContentLoaded" not in code, code[:200]
        assert not re.search(r"\bAnalytics\s*\.\s*(userIdentified|featureView)", code), code[:200]
    assert "BHAGYA_USER_PROPS" in text, "the user-properties source must stay"


def test_analytics_js_defines_none_of_the_removed_methods():
    js = ANALYTICS_JS.read_text(encoding="utf-8")
    for name in REMOVED:
        assert not re.search(rf"\b{name}\b", js), f"analytics.js still names {name} (#1069)"
    for ev in ("'feature_view'", "'user_identified'", "'pwa_installed'"):
        assert ev not in js, f"analytics.js still sends {ev}"


# ── 2. render ───────────────────────────────────────────────────────────────
def test_a_rendered_page_defines_user_props_and_calls_nothing_inline(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "window.BHAGYA_USER_PROPS" in html
    m = re.search(r"window\.BHAGYA_USER_PROPS\s*=\s*\{(.*?)\};", html, re.S)
    assert m, "BHAGYA_USER_PROPS literal not found"
    keys = set(re.findall(r"^\s*(\w+):", m.group(1), re.M))
    assert keys == {"age_bucket", "lang", "has_chart"}, keys
    for name in REMOVED:
        assert name not in html, f"the rendered page still contains {name}"


# ── 3. behaviour: the real analytics.js under Node ───────────────────────────
_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
const listeners = [];
const ctx = { URL, console };
ctx.window = ctx;
ctx.BHAGYA_ANALYTICS_CONFIG = { ga4: spec.ga4, clarity: '' };
ctx.location = { origin: 'https://shubhagya.com', href: 'https://shubhagya.com' + spec.path,
                 pathname: spec.path };
ctx.document = {
  readyState: 'interactive',
  referrer: '',
  addEventListener: (t, f) => listeners.push([t, f]),
  createElement: () => ({}), head: { appendChild() {} },
  getElementsByTagName: () => [], getElementById: () => null,
  querySelectorAll: () => [],
};
vm.createContext(ctx);
const out = { thrown: [], listeners: [] };
try {
  // A plain script defines the props before the deferred analytics.js runs.
  if (spec.propsJs !== undefined) vm.runInContext('window.BHAGYA_USER_PROPS = ' + spec.propsJs, ctx);
  vm.runInContext(src, ctx);
  const seen = () => (ctx.dataLayer || []).map(a => Array.prototype.slice.call(a));
  const fire = t => { for (const [n, f] of listeners) if (n === t) f({}); };
  out.boot = seen();
  for (const t of spec.fire || []) fire(t);
  out.after = seen();
  out.listeners = listeners.map(l => l[0]);
  out.methods = Object.keys(ctx.Analytics || {});
  out.hasGtag = typeof ctx.gtag;
} catch (e) { out.thrown.push(String(e)); }
process.stdout.write(JSON.stringify(out));
"""

NODE = shutil.which("node")


@pytest.fixture(autouse=True)
def _node_present(request):
    if "tmp_path" not in request.fixturenames:
        return  # layers 1 and 2 need no Node
    if NODE is None:
        if os.environ.get("CI"):
            pytest.fail("node is missing under CI: pr-gates installs Node 22, so a "
                        "missing binary means this gate is not running at all")
        pytest.skip("no node on this box; CI installs it and fails if it is absent")


def _run(tmp_path, *, ga4="G-TEST", props=PROPS, path="/kundli", fire=()):
    drv = tmp_path / "driver.js"
    drv.write_text(_DRIVER)
    spec = {"ga4": ga4, "path": path, "fire": list(fire)}
    if props is not None:
        spec["propsJs"] = props if isinstance(props, str) else json.dumps(props)
    r = subprocess.run([NODE, str(drv), str(ANALYTICS_JS)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["thrown"] == [], out["thrown"]
    return out


def _events(calls):
    return [c for c in calls if c[0] == "event"]


def _sets(calls):
    return [c for c in calls if c[0] == "set" and c[1] == "user_properties"]


def test_boot_sets_user_properties_once_and_sends_no_event(tmp_path):
    out = _run(tmp_path)
    assert [c[2] for c in _sets(out["boot"])] == [PROPS], out["boot"]
    assert len(_sets(out["boot"])) == 1
    assert _events(out["boot"]) == [], out["boot"]
    assert not any(c[0] == "event" and c[1] == "user_identified" for c in out["boot"])


def test_user_properties_are_set_before_config_so_the_first_page_view_carries_them(tmp_path):
    kinds = [(c[0], c[1] if c[0] == "set" else None) for c in _run(tmp_path)["boot"]]
    assert kinds.index(("set", "user_properties")) < [k[0] for k in kinds].index("config")


def test_page_load_and_boosted_navigation_send_no_feature_view_or_user_identified(tmp_path):
    """DOMContentLoaded (full load), htmx:afterSettle (a boosted swap) and
    htmx:pushedIntoHistory (a boosted URL push) are the three moments the old
    inline script's job could have been repeated. None may send either event."""
    out = _run(tmp_path, fire=["DOMContentLoaded", "htmx:afterSettle",
                               "htmx:pushedIntoHistory", "htmx:afterSettle",
                               "htmx:pushedIntoHistory"])
    assert {"DOMContentLoaded", "htmx:afterSettle", "htmx:pushedIntoHistory"} <= set(out["listeners"])
    names = {c[1] for c in _events(out["after"])}
    assert "feature_view" not in names and "user_identified" not in names, names
    assert _events(out["after"]) == [], out["after"]
    # And the properties were not re-sent as a `set` either: once per full load.
    assert len(_sets(out["after"])) == 1


@pytest.mark.parametrize("path", ["/", "/kundli", "/learn/sade-sati/", "/hi/ask",
                                  "/admin", "/static/app.css"])
def test_no_page_path_yields_a_feature_view(tmp_path, path):
    out = _run(tmp_path, path=path, fire=["DOMContentLoaded"])
    assert all(c[1] != "feature_view" for c in _events(out["after"]))


def test_the_public_surface_has_none_of_the_removed_methods(tmp_path):
    out = _run(tmp_path)
    for name in REMOVED:
        assert name not in out["methods"], out["methods"]
    assert "track" in out["methods"] and "toolSubmitted" in out["methods"]


def test_boot_without_user_props_does_not_throw_or_set(tmp_path):
    out = _run(tmp_path, props=None)
    assert _sets(out["boot"]) == [] and _events(out["boot"]) == []
    # GA4 itself is still configured.
    assert any(c[0] == "config" for c in out["boot"])


@pytest.mark.parametrize("bad", ["null", "'a string'", "42", "[1, 2]", "undefined"])
def test_boot_with_malformed_user_props_sends_no_set(tmp_path, bad):
    out = _run(tmp_path, props=bad)
    assert _sets(out["boot"]) == [], out["boot"]


def test_boot_with_ga4_unconfigured_does_not_throw_and_sends_nothing(tmp_path):
    for ga4 in ("", None):
        out = _run(tmp_path, ga4=ga4, fire=["DOMContentLoaded", "htmx:afterSettle",
                                            "htmx:pushedIntoHistory"])
        assert out["boot"] == [] and out["after"] == []
        assert out["hasGtag"] == "undefined"
        assert "track" in out["methods"]


def test_user_props_values_are_enum_only(tmp_path):
    """The property bag reaches GA4 verbatim from the page; pin that the real
    page's three keys are the whole vocabulary (rendered, then sent)."""
    sent = _sets(_run(tmp_path)["boot"])[0][2]
    assert set(sent) == {"age_bucket", "lang", "has_chart"}
    assert sent["has_chart"] in {"yes", "no"} and sent["lang"] in {"en", "hi"}
