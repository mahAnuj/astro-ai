"""`cta_click` — a /learn reader follows an in-article link to a tool (#570).

#276, #329, #521 and #518 each claim that in-article tool links get used, and the
only proxy was pages/session, which cannot resolve at ~500 sessions/28d. The event
is one delegated `click` listener in `static/analytics.js`. Nothing in the Python
suite executes JavaScript, so a listener that never fired, fired on the homepage
link, or shipped the query string would have passed everything. These tests RUN
the real file under Node against a stub DOM and assert what reaches `gtag`:

  * a tool link clicked on a /learn page sends ONE `cta_click` with paths only;
  * a navigation link, an external link, and any click outside /learn send none;
  * the query string and hash of the link never reach GA4;
  * "/" is the Kundli form AND the Home link, so it counts only outside the
    nav / header / footer chrome;
  * absent gtag / clarity, a text-node target and a malformed href throw nothing.

The second half pins the allowlist against the routing the articles actually use,
so the next slice of #518 cannot add a tool link the event silently ignores.

Node: `pr-gates` runs this suite in a job that installs Node 22, so under CI a
missing `node` FAILS (a gate that skips forever is not a gate). Locally, with no
Node, it skips -- the same stance as the `jq` guard in test_main_red_report.py.
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
ANALYTICS_JS = ROOT / "src" / "astro_ai" / "static" / "analytics.js"
LEARN = ROOT / "src" / "astro_ai" / "templates" / "learn"
LEARN_BASE = ROOT / "src" / "astro_ai" / "templates" / "learn_article_base.html"

ORIGIN = "https://shubhagya.com"

# A minimal DOM: just enough for `closest`, `href`, `parentElement` and the one
# `click` listener. No jsdom (not installed, and no npm deps may be added).
_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const [src, spec] = [fs.readFileSync(process.argv[2], 'utf8'), JSON.parse(fs.readFileSync(0, 'utf8'))];

function el(tag, parent, attrs) {
  const e = { tag, parentElement: parent || null, attrs: attrs || {} };
  e.closest = function (sel) {
    const alts = sel.split(',').map(s => s.trim());
    for (let n = e; n; n = n.parentElement) {
      for (const a of alts) {
        if (a === 'a[href]' ? (n.tag === 'a' && n.attrs.href !== undefined) : n.tag === a) return n;
      }
    }
    return null;
  };
  return e;
}

const calls = [], listeners = [];
const ctx = { URL, console };
ctx.window = ctx;
ctx.location = { origin: spec.origin, pathname: spec.pathname,
                 href: spec.origin + spec.pathname + (spec.search || '') };
ctx.document = {
  addEventListener: (t, f) => listeners.push([t, f]),
  createElement: () => ({}), head: { appendChild() {} },
  getElementsByTagName: () => [], getElementById: () => null,
};
if (spec.gtag)    ctx.gtag    = (...a) => calls.push(['gtag', ...a]);
if (spec.clarity) ctx.clarity = (...a) => calls.push(['clarity', ...a]);
vm.createContext(ctx);
vm.runInContext(src, ctx);

const out = { listeners: listeners.map(l => l[0]), thrown: [], prevented: 0, stopped: 0 };
for (const c of spec.clicks) {
  let parent = el('body');
  for (const tag of c.ancestors || []) parent = el(tag, parent);
  const a = el('a', parent, { href: c.href });
  // `a.href` is the property browsers expose: the attribute, unresolved here, and
  // the listener resolves it with `new URL(a.href, location.href)`.
  a.href = c.href;
  let target = a;
  if (c.target === 'child') target = el('span', a);
  if (c.target === 'textnode') target = { nodeType: 3 };   // no .closest, no parent
  if (c.target === 'bare') target = el('div', parent);     // inside no anchor
  const ev = { target, preventDefault() { out.prevented++; }, stopPropagation() { out.stopped++; } };
  try { for (const [t, f] of listeners) if (t === 'click') f(ev); }
  catch (e) { out.thrown.push(String(e)); }
}
if (spec.direct) {
  try { ctx.Analytics.ctaClick(); ctx.Analytics.ctaClick({ from_path: '/learn/x/', to_path: '/kundli', q: 'secret' }); }
  catch (e) { out.thrown.push(String(e)); }
}
out.calls = calls;
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


def _run(tmp_path, *, clicks, pathname="/learn/manglik-dosh/", gtag=True,
         clarity=True, search="", direct=False):
    drv = tmp_path / "driver.js"
    drv.write_text(_DRIVER)
    spec = {"origin": ORIGIN, "pathname": pathname, "search": search, "gtag": gtag,
            "clarity": clarity, "clicks": clicks, "direct": direct}
    r = subprocess.run([NODE, str(drv), str(ANALYTICS_JS)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _events(out):
    return [c for c in out["calls"] if c[0] == "gtag" and c[1] == "event"]


def test_tool_link_from_a_learn_page_sends_one_cta_click(tmp_path):
    out = _run(tmp_path, clicks=[{"href": "/manglik-check", "ancestors": ["article", "p"]}])
    assert out["listeners"] == ["click"], "exactly one delegated click listener"
    ev = _events(out)
    assert len(ev) == 1, out["calls"]
    _, _, name, params = ev[0]
    assert name == "cta_click"
    assert params["from_path"] == "/learn/manglik-dosh/"
    assert params["to_path"] == "/manglik-check"
    # The click navigates away; without a beacon transport the event can be lost.
    assert params["transport_type"] == "beacon"
    assert ["clarity", "event", "cta_click"] in out["calls"]
    assert out["prevented"] == 0 and out["stopped"] == 0, "the listener only observes"


@pytest.mark.parametrize("href", [
    "/kundli", "/dasha", "/matching", "/ask", "/sade-sati-check", "/kaal-sarp-check",
    "/numerology", "/numerology/compatibility", "/muhurat", "/muhurat/vivah",
    "/muhurat/griha-pravesh", "/dasha/deep-dive",
])
def test_every_tool_the_articles_link_to_counts(tmp_path, href):
    out = _run(tmp_path, clicks=[{"href": href, "ancestors": ["article"]}])
    assert [e[3]["to_path"] for e in _events(out)] == [href]


def test_a_click_on_a_child_of_the_link_counts(tmp_path):
    # Real clicks land on the <span>/<strong> inside the <a>, not on the <a>.
    out = _run(tmp_path, clicks=[{"href": "/kundli", "ancestors": ["article"], "target": "child"}])
    assert len(_events(out)) == 1


@pytest.mark.parametrize("href", [
    "/learn/sade-sati/", "/learn/", "/about", "/privacy", "/rashifal", "/panchang",
    "/kundlifoo", "/askew", "/numerology-fake/x",
])
def test_navigation_and_lookalike_paths_send_nothing(tmp_path, href):
    out = _run(tmp_path, clicks=[{"href": href, "ancestors": ["article"]}])
    assert _events(out) == []
    assert ["clarity", "event", "cta_click"] not in out["calls"]


def test_an_external_origin_link_sends_nothing(tmp_path):
    out = _run(tmp_path, clicks=[
        {"href": "https://evil.example/kundli", "ancestors": ["article"]},
        {"href": "https://www.drikpanchang.com/dasha", "ancestors": ["article"]},
        # Same path, different scheme/host: not our origin.
        {"href": "http://shubhagya.com/kundli", "ancestors": ["article"]},
    ])
    assert _events(out) == []


@pytest.mark.parametrize("pathname", ["/", "/kundli", "/panchang", "/rashifal/aries", "/learnx/y/", "/hi/learn/x/"])
def test_a_click_outside_learn_sends_nothing(tmp_path, pathname):
    out = _run(tmp_path, pathname=pathname, clicks=[{"href": "/kundli", "ancestors": ["article"]}])
    assert _events(out) == []


def test_query_string_and_hash_never_reach_ga4(tmp_path):
    out = _run(tmp_path, search="?utm_source=x&q=private", clicks=[
        {"href": "/kundli?name=Asha&dob=1990-01-01#section", "ancestors": ["article"]},
        {"href": "https://shubhagya.com/ask?ctx=numerology#top", "ancestors": ["article"]},
    ])
    ev = _events(out)
    assert [e[3]["to_path"] for e in ev] == ["/kundli", "/ask"]
    assert all(e[3]["from_path"] == "/learn/manglik-dosh/" for e in ev)
    blob = json.dumps(out["calls"])
    for leak in ("name=", "Asha", "1990", "section", "utm_", "private", "ctx=", "#", "?"):
        assert leak not in blob, f"{leak!r} reached an analytics call: {blob}"


def test_only_the_two_paths_and_the_transport_option_are_sent(tmp_path):
    out = _run(tmp_path, gtag=True, clarity=False, direct=True, clicks=[])
    ev = _events(out)
    assert len(ev) == 2
    # (the first call passed no argument; undefined fields vanish in JSON)
    assert sorted(ev[1][3]) == ["from_path", "to_path", "transport_type"], ev[1]
    assert set(ev[0][3]) <= {"from_path", "to_path", "transport_type"}, ev[0]
    # A caller's extra field cannot ride along to GA4.
    assert "secret" not in json.dumps(out["calls"])


@pytest.mark.parametrize("ancestors,counts", [
    ([], True),                       # a bare link in the body
    (["article", "p"], True),         # in-article prose "Generate your free Kundli"
    (["section"], True),              # end-of-article CTA card
    (["div"], True),                  # the sticky mobile CTA
    (["nav"], False),                 # site nav, breadcrumb, mobile tab bar
    (["header", "div", "nav"], False),
    (["header", "div"], False),
    (["footer", "ul", "li"], False),  # footer "Free Janma Kundli"
])
def test_the_home_link_counts_only_outside_the_site_chrome(tmp_path, ancestors, counts):
    # "/" is the Kundli form AND the Home link; the path alone cannot tell them apart.
    out = _run(tmp_path, clicks=[{"href": "/", "ancestors": ancestors}])
    assert len(_events(out)) == (1 if counts else 0)
    if counts:
        assert _events(out)[0][3]["to_path"] == "/"


def test_a_tool_link_inside_the_nav_still_counts(tmp_path):
    # The chrome exclusion is for "/" only; /ask in the nav is still a tool.
    out = _run(tmp_path, clicks=[{"href": "/ask", "ancestors": ["nav"]}])
    assert len(_events(out)) == 1


@pytest.mark.parametrize("gtag,clarity", [(False, False), (True, False), (False, True)])
def test_missing_providers_and_odd_targets_throw_nothing(tmp_path, gtag, clarity):
    out = _run(tmp_path, gtag=gtag, clarity=clarity, direct=True, clicks=[
        {"href": "/kundli", "ancestors": ["article"]},
        {"href": "/kundli", "ancestors": ["article"], "target": "textnode"},
        {"href": "/kundli", "ancestors": ["article"], "target": "bare"},
        {"href": "http://[bad", "ancestors": ["article"]},   # new URL() throws
    ])
    assert out["thrown"] == []
    assert len(_events(out)) == (3 if gtag else 0)   # 1 click + 2 direct ctaClick calls


# --- the allowlist and the routing the articles use must agree -----------------------

def _tool_roots() -> list[str]:
    src = ANALYTICS_JS.read_text()
    m = re.search(r"var TOOL_ROOTS = \[(.*?)\];", src, re.S)
    assert m, "analytics.js no longer defines TOOL_ROOTS"
    roots = re.findall(r"'(/[^']*)'", m.group(1))
    assert roots, "TOOL_ROOTS parsed empty"
    return roots


def _covered(href: str, roots: list[str]) -> bool:
    return any(href == r or href.startswith(r + "/") for r in roots)


def test_every_tool_href_pinned_by_the_routing_test_is_in_the_allowlist():
    import test_learn_tool_routes as routing

    roots = _tool_roots()
    hrefs = {href for _, href in routing.ROUTED}
    assert hrefs, "test_learn_tool_routes.ROUTED is empty"
    missing = sorted(h for h in hrefs if not _covered(h, roots))
    assert not missing, (
        f"tool links the articles route to that `cta_click` would silently ignore: {missing}")


class _Hrefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            h = dict(attrs).get("href")
            if h and h.startswith("/") and "{" not in h:
                self.hrefs.add(h.split("?")[0].split("#")[0])


# Internal links that are navigation, not tools. "/" is handled by position (see the
# chrome test above), so it is listed here as classified, not as a tool root.
NOT_A_TOOL = {"/", "/about"}


def test_every_learn_internal_href_is_classified():
    """A new kind of internal link in an article must be classified, not ignored.

    Enumerated 2026-11-03 over templates/learn/*.html + learn_article_base.html:
    /, /kundli, /matching, /ask, /sade-sati-check, /manglik-check, /kaal-sarp-check,
    /dasha, /muhurat, /muhurat/vivah, /muhurat/griha-pravesh, /numerology,
    /numerology/compatibility, /about. If this fails, decide: add the root to
    TOOL_ROOTS in analytics.js, or add the href to NOT_A_TOOL here.
    """
    p = _Hrefs()
    for f in [*sorted(LEARN.glob("*.html")), LEARN_BASE]:
        p.feed(f.read_text())
    internal = {h for h in p.hrefs if not h.startswith("/learn/") and h != "/learn"}
    roots = _tool_roots()
    unclassified = sorted(h for h in internal if not _covered(h, roots) and h not in NOT_A_TOOL)
    assert not unclassified, f"internal links neither a tool root nor NOT_A_TOOL: {unclassified}"
    # And the enumeration is not vacuous: the tools really are linked.
    assert sum(1 for h in internal if _covered(h, roots)) >= 8


def test_the_script_tag_is_fingerprinted_so_returning_visitors_get_the_new_bytes(client):
    """sw.js answers a bare /static/ URL from cache and refreshes it a visit late;
    a `?v=<hash>` URL is a new URL, so the new listener reaches a returning visitor
    on the first load after deploy."""
    html = client.get("/learn/manglik-dosh/").text
    m = re.search(r'<script src="/static/analytics\.js\?v=([0-9a-f]{8})" defer>', html)
    assert m, "analytics.js is linked without a content fingerprint"
    from astro_ai.routes.deps import _asset_fingerprint
    assert m.group(1) == _asset_fingerprint("analytics.js")
    assert client.get(f"/static/analytics.js?v={m.group(1)}").status_code == 200
