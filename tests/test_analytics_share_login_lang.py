"""#1229 -- `login`, `language_switched`, `share` and `from_path` on
`subscribe_completed` (#1070 rows 9-12, slice 3).

Same three layers as tests/test_analytics_tool_submitted.py, because each is blind
to the others:

  1. RENDER: the routes a visitor loads put the right `data-share-method` /
     `data-share-content` on the right control, read out of the HTML received.
  2. STATIC: every vocabulary value in analytics.js is pinned against the markup
     that carries it (and the reverse), every wa.me anchor is declared, templates
     never call the new methods themselves except base.html's one `login` call,
     and the language picker still posts with `form.submit()`.
  3. BEHAVIOUR (Node, the real analytics.js against a stub DOM): one event per
     action with exactly the listed params; a value outside the fixed vocabulary
     sends nothing; the listeners only observe; `from_path` never carries a query.

Decisions this file pins (each is a reading, argued in the commit message):
  * `data-whatsapp-share` controls in result.html are method=whatsapp (they POST a
    snapshot and then open wa.me). method=snapshot is the Cosmic Card link there,
    the only other share control on a reading.
  * `_pdf_download_button.html` is included from four pages; only result.html names
    a content type in the closed list (kundli). Numerology, matching_result and the
    muhurat finder pass nothing, so their button sends NO event (the list is not
    widened).
  * language_switched listens for the select's `change`, not `submit`:
    `form.submit()` (what _lang_picker.html calls) raises no `submit` event.

Node: `pr-gates` installs it, so under CI a missing `node` FAILS; locally it skips.
Layers 1 and 2 need no Node.

What NO test here can see: that a real browser delivers the beacon before the
navigation unloads the page, that GA4 accepts the event, and that wa.me opens. The
stub reproduces listener registration and event shape. The GA4 counts after deploy
are the browser-level proof (#1229 metric).

Mutation rows: scripts/mutations/2026_11_18_1229_share_login_lang.py.
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

#: Typed out on purpose: the fixed points analytics.js and the templates are
#: compared against.
METHODS = {"whatsapp", "snapshot", "pdf"}
CONTENT = {"kundli", "rashifal", "learn"}
LANGS = {"en", "hi"}

#: every share control in the templates: (template, method, content)
EXPECTED_CONTROLS = sorted([
    ("learn_article_base.html", "whatsapp", "learn"),
    ("rashifal_single.html", "whatsapp", "rashifal"),
    ("_rashifal_card_content.html", "whatsapp", "rashifal"),
    ("result.html", "whatsapp", "kundli"),     # header icon
    ("result.html", "whatsapp", "kundli"),     # return-triggers button
    ("result.html", "snapshot", "kundli"),     # Cosmic Card link
    ("_pdf_download_button.html", "pdf", "{{ _share }}"),
])


def _read(rel: str) -> str:
    return (TEMPLATES / rel).read_text(encoding="utf-8")


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict]] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def tags_of(html: str) -> list[tuple[str, dict]]:
    p = _Tags()
    p.feed(html)
    return p.tags


def share_controls(html: str) -> list[tuple[str, str | None, str | None]]:
    return [(t, a.get("data-share-method"), a.get("data-share-content"))
            for t, a in tags_of(html) if "data-share-method" in a]


# ── 1. render ───────────────────────────────────────────────────────────────
def test_a_learn_article_share_link_is_declared_whatsapp_learn(client):
    r = client.get("/learn/sade-sati/")
    assert r.status_code == 200
    got = share_controls(r.text)
    assert got == [("a", "whatsapp", "learn")], got
    wa = [a for t, a in tags_of(r.text) if t == "a" and "wa.me" in (a.get("href") or "")]
    assert len(wa) == 1 and "data-share-method" in wa[0], wa


def test_rashifal_page_and_card_fragment_declare_whatsapp_rashifal(client, stub_llm,
                                                                  today_iso, rashi_body):
    from astro_ai import daily_cache

    stub_llm(lambda _n: rashi_body(heading="Aries / Mesha"))
    daily_cache.put("rashifal_single", "aries-en", {"body": ""}, today_iso)
    page = client.get("/rashifal/aries")
    assert page.status_code == 200
    assert share_controls(page.text) == [("a", "whatsapp", "rashifal")], share_controls(page.text)
    frag = client.get("/rashifal/aries", headers={"HX-Rashifal-Fragment": "1"})
    assert frag.status_code == 200
    assert share_controls(frag.text) == [("a", "whatsapp", "rashifal")], share_controls(frag.text)
    for body in (page.text, frag.text):
        wa = [a for t, a in tags_of(body) if t == "a" and "wa.me" in (a.get("href") or "")]
        assert wa and all("data-share-method" in a for a in wa), wa


def test_the_kundli_result_declares_its_whatsapp_snapshot_and_pdf_controls(
        client, saved_chart, monkeypatch):
    from astro_ai.routes import kundli as K

    monkeypatch.setattr(K, "generate_reading", lambda *a, **k: "## Personality\n" + "Body. " * 60)
    saved_chart(name="Asha", birth_date="1990-08-15", birth_time="23:55",
                birth_place="Varanasi, India")
    r = client.get("/kundli")
    assert r.status_code == 200
    got = sorted(share_controls(r.text), key=str)
    assert got == sorted([("a", "whatsapp", "kundli"), ("a", "whatsapp", "kundli"),
                          ("a", "snapshot", "kundli"), ("button", "pdf", "kundli")],
                         key=str), got
    # the WhatsApp declaration sits on the same element the page's own handler binds
    for t, a in tags_of(r.text):
        if "data-whatsapp-share" in a:
            assert a.get("data-share-method") == "whatsapp", a
    # the declaration never carries a name, date or place
    for t, a in tags_of(r.text):
        if "data-share-method" in a:
            assert a["data-share-method"] in METHODS and a["data-share-content"] in CONTENT


def _render_pdf_partial(**ctx) -> str:
    from astro_ai.routes.deps import templates

    tpl = templates.env.from_string(
        '{% with pdf_filename_hint = "Priya Kundli"' +
        "".join(f", {k} = {v!r}" for k, v in ctx.items()) +
        ' %}{% include "_pdf_download_button.html" %}{% endwith %}')
    return tpl.render(lang="en", t=lambda lang, key, **k: key)


def test_the_pdf_button_is_declared_only_when_the_page_names_a_content_type():
    named = share_controls(_render_pdf_partial(pdf_share_content="kundli"))
    assert named == [("button", "pdf", "kundli")], named
    bare = _render_pdf_partial()
    assert share_controls(bare) == [] and "data-share" not in bare, \
        "a page that names no content type must send no share event"


def test_numerology_matching_and_muhurat_pdf_buttons_send_nothing():
    """Their content (numerology, matching, muhurat) is not in the closed list, so
    the include passes nothing. Widening the list is a separate decision."""
    for rel in ("numerology.html", "matching_result.html", "muhurat_finder.html"):
        text = _read(rel)
        assert '"_pdf_download_button.html"' in text, rel
        assert "pdf_share_content" not in text, rel
    assert "pdf_share_content = 'kundli'" in _read("result.html")


# ── 2. static ───────────────────────────────────────────────────────────────
def test_every_share_control_in_the_templates_is_the_expected_one():
    got = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        rel = path.relative_to(TEMPLATES).as_posix()
        for tag in re.finditer(r"<(?:a|button)\b[^>]*>", path.read_text(encoding="utf-8"), re.S):
            m = re.search(r'data-share-method="([^"]*)"', tag.group(0))
            if m:
                c = re.search(r'data-share-content="([^"]*)"', tag.group(0))
                got.append((rel, m.group(1), c.group(1) if c else None))
    assert sorted(got) == EXPECTED_CONTROLS, got


def test_the_template_values_are_exactly_the_vocabularies():
    methods, content = set(), set()
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        methods |= set(re.findall(r'data-share-method="([a-z]+)"', text))
        content |= {v for v in re.findall(r'data-share-content="([^"]*)"', text)
                    if "{{" not in v}
        content |= set(re.findall(r"pdf_share_content = '([a-z]+)'", text))
    assert methods == METHODS, methods
    assert content == CONTENT, content


def test_every_wa_me_anchor_in_a_template_is_declared():
    """A new wa.me link must join the `share` count, or it is silently uncounted.
    (result.html's wa.me URLs are built in JS inside strings, not anchors.)"""
    bad, seen = [], 0
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for tag in re.finditer(r"<a\b[^>]*>", text, re.S):
            if "wa.me" in tag.group(0):
                seen += 1
                if 'data-share-method="whatsapp"' not in tag.group(0):
                    bad.append(path.name)
    assert seen == 3, f"expected the 3 wa.me anchors, found {seen}"
    assert not bad, bad


def test_templates_do_not_fire_the_new_events_themselves():
    """share and language_switched are fired by the delegated listeners; an inline
    call, or a declared event of the same name, would double-count. `login` is
    called from exactly one place: base.html's handleGoogleSignIn."""
    login_sites = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(TEMPLATES).as_posix()
        for needle in ("Analytics.share", "Analytics.languageSwitched", "'share'",
                       "'language_switched'", '"language_switched"', "analytics_event('login'",
                       "analytics_event('share'"):
            assert needle not in text, (rel, needle)
        if "Analytics.login" in text:
            login_sites.append(rel)
    assert login_sites == ["base.html"], login_sites


def test_login_fires_on_the_success_branch_before_the_reload_and_is_guarded():
    text = _read("base.html")
    m = re.search(r"if \(j\.ok\) \{(.*?)location\.reload\(\);", text, re.S)
    assert m, "handleGoogleSignIn's success branch changed shape"
    branch = m.group(1)
    assert branch.count("Analytics.login({ method: 'google' })") == 1, branch
    assert "window.Analytics && window.Analytics.login" in branch, \
        "an unguarded call would block the reload if analytics.js failed to load"
    assert "try {" in branch and "catch" in branch
    # not on the failure branch
    assert text.count("Analytics.login(") == 1
    after = text.split("location.reload();", 1)[1][:300]
    assert "Analytics.login" not in after


def test_the_language_picker_still_uses_form_submit_and_the_vocabulary_is_en_hi():
    """analytics.js listens for the select's `change` BECAUSE `form.submit()` raises
    no `submit` event. If this markup moves to requestSubmit() (which does), the
    `change` listener double-counts with any new submit listener, so rethink both."""
    text = _read("_lang_picker.html")
    sel = re.search(r"<select\s[^>]*>", text, re.S).group(0)
    assert 'name="lang"' in sel and "this.form.submit()" in sel
    assert "requestSubmit" not in text
    assert 'action="/lang"' in text
    assert set(re.findall(r'<option\b[^>]*value="([^"]*)"', text)) == LANGS


def test_analytics_js_vocabularies_and_listener_shape():
    js = ANALYTICS_JS.read_text(encoding="utf-8")
    for name, want in (("SHARE_METHODS", METHODS), ("SHARE_CONTENT", CONTENT),
                       ("LANG_CODES", LANGS)):
        m = re.search(r"var %s = \[(.*?)\];" % name, js, re.S)
        assert m, f"{name} is gone"
        assert set(re.findall(r"'([a-z]+)'", m.group(1))) == want, name
    # exactly one delegated listener per event, all on document
    assert len(re.findall(r"document\.addEventListener\(\s*'change'", js)) == 1
    assert len(re.findall(r"addEventListener\(\s*'change'", js)) == 1
    # ONE click listener (cta_click and share share it; test_cta_click_event pins it)
    assert len(re.findall(r"addEventListener\(\s*'click'", js)) == 1
    assert len(re.findall(r"document\.addEventListener\(\s*'click'", js)) == 1
    assert "ctaClickHandler(e);\n    shareClickHandler(e);" in js
    assert len(re.findall(r"addEventListener\(\s*'submit'", js)) == 1       # tool_submitted only
    assert re.search(r"closest\(\s*'\[data-share-method\]'\s*\)", js)
    assert re.search(r"closest\(\s*'form\[action=\"/lang\"\]'\s*\)", js)
    for ev in ("login", "share", "language_switched"):
        assert len(re.findall(r"track\(\s*'%s'" % ev, js)) == 1, ev
    # never read an href, URL or text for a share
    handler = js.split("function shareClickHandler", 1)[1].split("The one delegated click listener", 1)[0]
    assert "data-share-method" in handler, "sliced the wrong region"
    for banned in (".href", "textContent", "innerText", "location.href", ".search"):
        assert banned not in handler, banned


def test_the_subscribe_modal_sends_the_path_only():
    text = _read("_subscribe_modal.html")
    assert text.count("Analytics.subscribeCompleted(") == 1
    call = re.search(r"Analytics\.subscribeCompleted\((.*?)\);", text, re.S).group(1)
    assert "from_path: location.pathname" in call
    for banned in ("location.href", "location.search", "location.hash", "document.URL"):
        assert banned not in call, banned


# ── 3. behaviour under Node ─────────────────────────────────────────────────
_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));

// A node: { tag, attrs, value, parentElement }. closest() answers the three
// selector shapes analytics.js uses: [attr], tag[attr], tag[attr="v"] and a comma
// list of tags; anything else throws so the stub cannot silently agree.
function matches(n, sel) {
  let m;
  if ((m = /^([a-z]*)\[([a-z-]+)="([^"]*)"\]$/.exec(sel))) {
    return (!m[1] || n.tag === m[1]) && n.attrs[m[2]] === m[3];
  }
  if ((m = /^([a-z]*)\[([a-z-]+)\]$/.exec(sel))) {
    return (!m[1] || n.tag === m[1]) && m[2] in n.attrs;
  }
  if (/^[a-z, ]+$/.test(sel)) return sel.split(/\s*,\s*/).includes(n.tag);
  throw new Error('stub cannot answer closest(' + sel + ')');
}
function node(o, parent) {
  const e = { tag: o.tag, parentElement: parent || null, attrs: o.attrs || {},
              value: o.value, nodeType: 1 };
  e.getAttribute = (n) => (n in e.attrs ? e.attrs[n] : null);
  e.closest = (sel) => { for (let n = e; n; n = n.parentElement) if (matches(n, sel)) return n; return null; };
  return e;
}

const calls = [], listeners = [];
const ctx = { URL, console };
ctx.window = ctx;
ctx.location = { origin: spec.origin, pathname: spec.pathname || '/matching',
                 href: spec.origin + (spec.pathname || '/matching') };
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

const out = { listeners: listeners.map(l => l[0]), thrown: [], prevented: 0, stopped: 0, per: [] };
const events = () => calls.filter(x => x[0] === 'gtag' && x[1] === 'event');
for (const s of spec.dispatch || []) {
  // chain: outermost first; the target is the innermost unless s.target says otherwise
  let parent = null, last = null;
  for (const o of s.chain) { last = node(o, parent); parent = last; }
  let target = last;
  if (s.target === 'textnode') target = { nodeType: 3, parentElement: last };
  if (s.target === 'null') target = null;
  const ev = { type: s.type, target, preventDefault() { out.prevented++; },
               stopPropagation() { out.stopped++; } };
  const before = events().length;
  try { for (const [t, f] of listeners) if (t === s.type) f(ev); }
  catch (e) { out.thrown.push(String(e)); }
  out.per.push(events().length - before);
}
for (const [fn, arg] of spec.direct || []) {
  try { ctx.Analytics[fn](...(arg === undefined ? [] : [arg])); }
  catch (e) { out.thrown.push(fn + ': ' + String(e)); }
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


def _run(tmp_path, dispatch=None, direct=None, pathname=None):
    drv = tmp_path / "driver.js"
    drv.write_text(_DRIVER)
    spec = {"origin": "https://shubhagya.com", "dispatch": dispatch or [],
            "direct": direct or [], "pathname": pathname}
    r = subprocess.run([NODE, str(drv), str(ANALYTICS_JS)], input=json.dumps(spec),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _events(out):
    return [c for c in out["calls"] if c[0] == "gtag" and c[1] == "event"]


def _click(method, content, *, target="self", extra=None):
    attrs = {"href": "https://wa.me/?text=Priya%20born%2012-04-1990", "data-share-method": method}
    if content is not None:
        attrs["data-share-content"] = content
    attrs.update(extra or {})
    chain = [{"tag": "body"}, {"tag": "a", "attrs": attrs}]
    if target == "child":
        chain.append({"tag": "svg"})
    return {"type": "click", "chain": chain, "target": target if target in ("textnode", "null") else None}


def _change(value, *, name="lang", form_action="/lang", target=None):
    return {"type": "change", "target": target, "chain": [
        {"tag": "body"}, {"tag": "form", "attrs": {"action": form_action}},
        {"tag": "select", "attrs": {"name": name}, "value": value}]}


# -- share
@pytest.mark.parametrize("method", sorted(METHODS))
@pytest.mark.parametrize("content", sorted(CONTENT))
def test_every_method_and_content_pair_sends_one_share_with_only_those_two(
        tmp_path, _node_present, method, content):
    out = _run(tmp_path, [_click(method, content)])
    assert out["thrown"] == []
    assert out["per"] == [1]
    (_, _, name, params), = _events(out)
    assert name == "share"
    assert params == {"method": method, "content_type": content}, params
    assert ["clarity", "event", "share"] in out["calls"]
    assert out["prevented"] == 0 and out["stopped"] == 0, "the listener only observes"


def test_a_click_on_an_icon_inside_the_control_counts_once(tmp_path, _node_present):
    out = _run(tmp_path, [_click("whatsapp", "kundli", target="child"),
                          _click("whatsapp", "kundli", target="textnode")])
    assert out["thrown"] == []
    assert out["per"] == [1, 1]
    assert all(e[3] == {"method": "whatsapp", "content_type": "kundli"} for e in _events(out))


@pytest.mark.parametrize("method,content", [
    ("whatsapp", "numerology"), ("whatsapp", None), ("whatsapp", ""), ("whatsapp", "Kundli"),
    ("whatsapp", "kundli "), ("telegram", "kundli"), ("", "kundli"), ("WhatsApp", "kundli"),
    ("whatsapp,pdf", "kundli"), ("__proto__", "kundli"), ("whatsapp", "constructor"),
    ("whatsapp", "kundli&name=Priya"),
])
def test_a_value_outside_the_vocabulary_sends_nothing(tmp_path, _node_present, method, content):
    out = _run(tmp_path, [_click(method, content)])
    assert out["thrown"] == []
    assert out["per"] == [0], _events(out)
    assert _events(out) == []


def test_a_click_elsewhere_or_on_an_odd_target_sends_nothing_and_never_throws(
        tmp_path, _node_present):
    plain = {"type": "click", "target": None, "chain": [
        {"tag": "body"}, {"tag": "a", "attrs": {"href": "https://wa.me/?text=x"}}]}
    out = _run(tmp_path, [plain, _click("pdf", "kundli", target="null")])
    assert out["thrown"] == []
    assert out["per"] == [0, 0], "an undeclared wa.me link is not a share"


def test_a_page_added_after_load_counts_because_the_listener_is_on_document(
        tmp_path, _node_present):
    out = _run(tmp_path, [_click("pdf", "kundli")])
    assert out["per"] == [1]
    assert out["listeners"].count("click") == 1 and out["listeners"].count("change") == 1


def test_share_and_cta_click_do_not_both_fire_on_one_click(tmp_path, _node_present):
    """On a /learn/ page a declared wa.me anchor is external (cta_click ignores it)
    and a declared in-site control sends only `share`."""
    out = _run(tmp_path, [_click("whatsapp", "learn")], pathname="/learn/sade-sati/")
    assert [e[2] for e in _events(out)] == ["share"]


def test_a_direct_share_call_cannot_widen_the_params(tmp_path, _node_present):
    out = _run(tmp_path, direct=[
        ["share", None],
        ["share", {"method": "pdf"}],
        ["share", {"content_type": "kundli"}],
        ["share", {"method": "pdf", "content_type": "kundli", "url": "https://x/?q=secret",
                   "name": "Priya"}],
        ["share", {"method": "nope", "content_type": "kundli"}],
    ])
    assert out["thrown"] == []
    ev = _events(out)
    assert len(ev) == 1, ev
    assert ev[0][2:] == ["share", {"method": "pdf", "content_type": "kundli"}], ev


# -- language_switched
@pytest.mark.parametrize("to", sorted(LANGS))
def test_picking_a_language_sends_one_language_switched_with_beacon(tmp_path, _node_present, to):
    out = _run(tmp_path, [_change(to)])
    assert out["thrown"] == []
    assert out["per"] == [1]
    (_, _, name, params), = _events(out)
    assert name == "language_switched"
    assert params == {"to_lang": to, "transport_type": "beacon"}, params
    assert out["prevented"] == 0 and out["stopped"] == 0, "the form must still post"


@pytest.mark.parametrize("value", ["fr", "", "EN", "en ", "hi,en", "__proto__", "constructor",
                                   None, "en&next=/ask?q=secret"])
def test_any_other_language_value_sends_nothing(tmp_path, _node_present, value):
    out = _run(tmp_path, [_change(value)])
    assert out["thrown"] == []
    assert out["per"] == [0], _events(out)


def test_only_the_lang_select_inside_the_lang_form_counts(tmp_path, _node_present):
    out = _run(tmp_path, [
        _change("hi", form_action="/reading"),            # some other form's field
        _change("hi", name="category"),                    # another control in the lang form
        _change("hi", target="textnode"),                  # text node: parent is the select
        _change("hi", target="null"),
    ])
    assert out["thrown"] == []
    assert out["per"] == [0, 0, 1, 0], out["per"]


def test_a_direct_language_call_cannot_widen_the_params(tmp_path, _node_present):
    out = _run(tmp_path, direct=[
        ["languageSwitched", None],
        ["languageSwitched", {"lang": "hi"}],                  # the retired field name
        ["languageSwitched", {"to_lang": "hi", "next": "/ask?q=secret", "name": "Priya"}],
    ])
    assert out["thrown"] == []
    ev = _events(out)
    assert len(ev) == 1, ev
    assert ev[0][2:] == ["language_switched", {"to_lang": "hi", "transport_type": "beacon"}]


# -- login
def test_login_sends_method_google_with_beacon(tmp_path, _node_present):
    out = _run(tmp_path, direct=[["login", {"method": "google"}]])
    assert out["thrown"] == []
    ev = _events(out)
    assert len(ev) == 1 and ev[0][2:] == ["login", {"method": "google", "transport_type": "beacon"}], ev
    assert ["clarity", "event", "login"] in out["calls"]


def test_login_with_any_other_method_or_none_sends_nothing(tmp_path, _node_present):
    out = _run(tmp_path, direct=[
        ["login", None], ["login", {}], ["login", {"method": "Google"}],
        ["login", {"method": "facebook"}], ["login", {"method": ""}],
        ["login", {"method": "__proto__"}],
    ])
    assert out["thrown"] == []
    assert _events(out) == []


def test_login_cannot_carry_an_email_or_name(tmp_path, _node_present):
    out = _run(tmp_path, direct=[["login", {"method": "google", "email": "a@b.co",
                                            "name": "Priya", "credential": "jwt"}]])
    assert _events(out)[0][3] == {"method": "google", "transport_type": "beacon"}


# -- subscribe_completed
def test_subscribe_completed_keeps_lang_and_adds_the_path(tmp_path, _node_present):
    out = _run(tmp_path, direct=[["subscribeCompleted", {"lang": "hi", "from_path": "/learn/sade-sati/"}]])
    assert out["thrown"] == []
    assert _events(out)[0][2:] == ["subscribe_completed",
                                   {"lang": "hi", "from_path": "/learn/sade-sati/"}]


@pytest.mark.parametrize("given,want", [
    ("/rashifal/aries?c=career", "/rashifal/aries"),
    ("/ask?q=will+I+marry+Priya", "/ask"),
    ("/learn/x/#section", "/learn/x/"),
    ("/panchang?city=Mumbai#top", "/panchang"),
    ("/", "/"),
])
def test_from_path_never_carries_a_query_or_hash(tmp_path, _node_present, given, want):
    out = _run(tmp_path, direct=[["subscribeCompleted", {"lang": "en", "from_path": given}]])
    params = _events(out)[0][3]
    assert params == {"lang": "en", "from_path": want}, params
    assert "?" not in params["from_path"] and "#" not in params["from_path"]


def test_subscribe_completed_rebuilds_its_params_and_omits_a_non_string_path(tmp_path, _node_present):
    out = _run(tmp_path, direct=[
        ["subscribeCompleted", {"lang": "en", "email": "a@b.co", "name": "Priya"}],
        ["subscribeCompleted", {"lang": "en", "from_path": {"x": 1}}],
        ["subscribeCompleted"],
    ])
    assert out["thrown"] == []
    evs = _events(out)
    assert [e[3] for e in evs[:2]] == [{"lang": "en"}, {"lang": "en"}], [e[3] for e in evs]
    assert len(evs) == 3 and evs[2][2] == "subscribe_completed"
    for e in evs:
        assert set(e[3]) <= {"lang", "from_path"}, e[3]
