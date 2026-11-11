"""PII egress sweep (#744), the analytics proxy: what the page hands GA4 and Clarity.

The browser is not observable in-process, so this judges the NEAREST thing that
is: the server-rendered HTML each scenario returns. GA4 collects `document.title`
by default (`static/analytics.js` sets no `page_title`), reads the two inline
blobs `base.html` builds (`BHAGYA_ANALYTICS_CONFIG`, `BHAGYA_USER_PROPS`) and the
arguments of every `Analytics.*(` call. Clarity replays the rendered DOM; what it
masks is not knowable from here (`ARCHITECTURE.md` section 11).

`privacy.html` says of analytics: "No birth details, no email, no question text is
included", and defines birth details as name, date, time and place. Measured on
the first run of this sweep: the <title> of EIGHT routes carries the visitor's
name (`details.name` rendered into `{% block title %}`). #817 made all eight
name-free and `KNOWN_GAPS` is now EMPTY. It is still asserted by EQUALITY: a new
leak fails, and a pin for something that does not leak fails too. It is not
`xfail`, because `verify_behaviour.py` treats any xfail as "tests did not run".
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src" / "astro_ai" / "templates"
ANALYTICS_JS = ROOT / "src" / "astro_ai" / "static" / "analytics.js"
_SCRIPT = ROOT / "scripts" / "verify_pii_egress.py"
if "verify_pii_egress" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("verify_pii_egress", _SCRIPT)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["verify_pii_egress"] = _mod
    _spec.loader.exec_module(_mod)
pii = sys.modules["verify_pii_egress"]

SCENARIOS = (
    "reading-kundli", "matching", "manglik-dosha", "sade-sati-dosha", "kaal-sarp-dosha",
    "numerology", "numerology-compatibility", "ask", "subscribe", "feedback", "snapshot",
    "personal-readings", "rashifal-is-shared", "dasha", "muhurat-personal",
    "email-my-reading", "llm-exhausted", "brevo-fails", "place-rejected",
)


def _page(e):
    return {v for v in e.violations() if v[0].startswith("analytics:")}


@pytest.fixture
def run(monkeypatch, caplog, tmp_path):
    return lambda name: pii.run_scenario(name, monkeypatch, caplog, tmp_path)


def test_the_known_gaps_equal_what_the_scenarios_observe(monkeypatch, caplog, tmp_path):
    """The ratchet. Both directions fail: an unlisted leak is a new defect, and a
    listed one that no longer leaks is a fix that must delete its pin."""
    observed: set = set()
    for name in SCENARIOS:
        caplog.clear()
        observed |= _page(pii.run_scenario(name, monkeypatch, caplog, tmp_path / name))
    assert observed - pii.KNOWN_GAPS == set(), (
        f"NEW page-surface leak(s), not in KNOWN_GAPS: {sorted(observed - pii.KNOWN_GAPS)}")
    assert pii.KNOWN_GAPS - observed == set(), (
        f"these no longer leak: delete them from KNOWN_GAPS in "
        f"scripts/verify_pii_egress.py -> {sorted(pii.KNOWN_GAPS - observed)}")


@pytest.mark.parametrize("name", SCENARIOS)
def test_a_scenario_leaks_nothing_to_analytics_beyond_the_known_gaps(run, name):
    e = run(name)
    extra = _page(e) - pii.KNOWN_GAPS
    assert extra == set(), f"{name}: (sink, route, class) not in KNOWN_GAPS: {sorted(extra)}"


def test_the_config_and_props_blocks_carry_no_sentinel_for_a_signed_in_visitor(run):
    """`BHAGYA_USER_PROPS` is built per request from the session, which is where
    an address or an age would be added by someone meaning well."""
    e = run("reading-kundli")
    pages = [r for r in e.responses if r["html"]]
    assert pages, "no HTML page was captured"
    assert any("BHAGYA_USER_PROPS" in r["html"] and "BHAGYA_ANALYTICS_CONFIG" in r["html"]
               for r in pages), "the analytics blocks are not on the page any more"
    bad = {v for v in e.violations()
           if v[0] in ("analytics:config", "analytics:props", "analytics:calls")}
    assert bad == set(), sorted(bad)


def test_a_title_outside_the_known_gaps_carries_nothing(run):
    """/dasha's title must be free of every sentinel. This is the check that a NEW
    title which embeds the name or email fails on (the ratchet above covers the rest)."""
    e = run("dasha")
    titles = {r["route"] for r in e.responses if r["html"]}
    assert {"/dasha", "/dasha/deep-dive"} <= titles, titles
    bad = {v for v in e.violations() if v[0] == "analytics:title" and v[1].startswith("/dasha")}
    assert bad == set(), sorted(bad)


def test_the_ask_redirect_may_carry_the_question_only_because_analytics_js_strips_it(run):
    """POST /ask answers 303 to /ask?q=<the question>, a deliberate shareable URL.
    The allowance in the policy is conditional on #528: analytics.js removes `q`
    before GA4 sees page_location (tests/test_analytics_ask_location.py runs it
    under Node). If that line goes, the allowance is a lie."""
    e = run("ask")
    redirects = [r for r in e.responses if r["route"] == "/ask" and r["location"]]
    assert redirects, "POST /ask did not redirect"
    assert "zanzibar" in redirects[0]["location"].lower() or "q=" in redirects[0]["location"]
    assert {v for v in e.violations() if v[0] == "analytics:location"} == set()
    assert "searchParams.delete('q')" in ANALYTICS_JS.read_text(encoding="utf-8")


# ─── static: the templates, for states no scenario drives ──────────────────

#: Every Jinja expression allowed inside an `Analytics.*(` / `gtag(` argument list.
#: A scenario only sees the state it drives; a template can branch on state it does
#: not, so the argument lists are read statically too. Each entry is a value with
#: no personal content: the language code, a question CATEGORY from a fixed list,
#: and the two dasha lords (a planet name, one of nine, derived from the chart --
#: the same grain as the rashi triple the Telegram alerts carry by design; this is
#: a judgement call that privacy.html does not spell out, recorded in
#: ARCHITECTURE.md section 11).
ALLOWED_CALL_EXPRESSIONS = frozenset({
    "lang", "current_category", "dasha.mahadasha.lord", "dasha.antardasha.lord",
})

#: The same for the two inline blocks base.html builds for analytics.js.
#: `_ga4_id` / `_clarity_id` are the site's provider ids, or '' on /admin/* (#735);
#: both come from env config, never from a request.
ALLOWED_BLOCK_EXPRESSIONS = frozenset({
    "_ga4_id", "_clarity_id", "user_age_bucket(request)",
    "lang or 'en'", "'yes' if user_age_bucket(request) else 'no'",
})

_JINJA = re.compile(r"\{\{\s*(.*?)\s*\}\}|\{%.*?%\}", re.S)


def _templates():
    return sorted(TEMPLATES.rglob("*.html"))


def _expressions(chunk: str) -> list[str]:
    """Jinja expressions inside `chunk`; a block tag (`{% if %}`) counts as one,
    spelt with its braces, because control flow inside an argument list could
    include data conditionally and is never in the allow-list."""
    return [m.group(1) if m.group(1) is not None else m.group(0) for m in _JINJA.finditer(chunk)]


def test_every_template_expression_inside_an_analytics_call_is_a_known_safe_value():
    found: dict[str, list[str]] = {}
    n_calls = 0
    for path in _templates():
        for call in pii.analytics_call_args(path.read_text(encoding="utf-8")):
            n_calls += 1
            for expr in _expressions(call):
                found.setdefault(expr, []).append(path.name)
    assert n_calls >= 6, (
        f"only {n_calls} Analytics/gtag calls found in the templates: the scan stopped "
        f"finding them, which is how a static check becomes vacuous")
    extra = {k: v for k, v in found.items() if k not in ALLOWED_CALL_EXPRESSIONS}
    assert not extra, (
        f"a template passes an unreviewed expression to an analytics call: {extra}. "
        f"Add it to ALLOWED_CALL_EXPRESSIONS only if it can never carry a name, date, "
        f"time, place, email or question.")
    stale = ALLOWED_CALL_EXPRESSIONS - set(found)
    assert not stale, f"allowed but no longer used, delete: {sorted(stale)}"


def test_every_template_expression_inside_the_analytics_blocks_is_a_known_safe_value():
    found: set[str] = set()
    for path in _templates():
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"window\.BHAGYA_(?:ANALYTICS_CONFIG|USER_PROPS)\s*=\s*\{.*?\};",
                             text, re.S):
            found.update(_expressions(m.group(0)))
    assert found, "the analytics blocks were not found in any template"
    assert found <= ALLOWED_BLOCK_EXPRESSIONS, sorted(found - ALLOWED_BLOCK_EXPRESSIONS)
    assert ALLOWED_BLOCK_EXPRESSIONS <= found, sorted(ALLOWED_BLOCK_EXPRESSIONS - found)


def test_the_static_scan_reads_a_planted_leak():
    """The scan itself must be able to fail: a planted expression is found and is
    not on the allow-list."""
    planted = "<script>Analytics.track('x', { who: '{{ details.name }}', l: '{{ lang }}' });</script>"
    exprs = [x for call in pii.analytics_call_args(planted) for x in _expressions(call)]
    assert exprs == ["details.name", "lang"]
    assert "details.name" not in ALLOWED_CALL_EXPRESSIONS
    block = "{% if answer %}x{% endif %}"
    assert _expressions(block)[0] not in ALLOWED_CALL_EXPRESSIONS
