"""Visitor text at /admin/feedback is escaped by a setting someone must not lose (#409).

WHY THIS IS HERE, given the charter in conftest.py.

`POST /feedback` needs no authentication and stores `message`, `page` (200
chars) and `ua` (the User-Agent, 300 chars) raw. `admin_feedback.html` prints
them with a plain `{{ }}`, so what stands between a visitor's `<script>` and the
owner's browser is Jinja's autoescape and nothing else. Until #409 that setting
was INHERITED from Starlette's `Jinja2Templates(directory=...)` default and
nothing asserted it: `autoescape=False`, or a dependency changing its default,
would have kept every gate green. `ua` is the field a future edit trips over --
the escaping work on the owner's email never mentioned it, because it is not in
that email at all.

`|safe` is an established idiom here (a dozen uses on app-controlled values), so
"add `|safe` to make this render" is a move someone has already made many times.
The second half of this file fails if that move is made on a visitor field.
It is NOT a ban on `|safe`: the existing uses are on `t(lang, ...)` strings and
server-built values and must keep passing.

Hermetic: no network, no GCS (`feedback.list_all` is patched), no LLM.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai import feedback as feedback_store
from astro_ai.routes.deps import TEMPLATES_DIR, templates

PAYLOAD = '<script>alert("x")</script>'

# Visitor-controlled feedback fields (feedback.add stores them; admin_feedback.html
# renders them). `user_agent` is the argument name `ua` is stored under.
VISITOR_FIELDS = ("message", "page", "ua", "email", "user_agent")


# --------------------------------------------------------------------------
# 1. The environment itself
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["admin_feedback.html", "x.html", "x.htm", "x.xml"])
def test_autoescape_is_on_for_html_templates(name):
    # Asserted on the REAL environment the routes render with, not a copy.
    assert callable(templates.env.autoescape)
    assert templates.env.autoescape(name) is True


def test_a_script_tag_in_a_rendered_html_template_comes_out_escaped():
    # Behaviour, not configuration: render through the real env and read the output.
    out = templates.env.from_string("<p>{{ v }}</p>").render(v=PAYLOAD)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_the_environment_was_not_left_to_a_default(tmp_path):
    # `from_string` is autoescaped via default_for_string; a FILE is the path that
    # depends on the extension list, so render an actual .html file.
    (tmp_path / "probe.html").write_text("<i>{{ v }}</i>")
    import jinja2

    env = templates.env.overlay(loader=jinja2.FileSystemLoader(str(tmp_path)))
    out = env.get_template("probe.html").render(v=PAYLOAD)
    assert "&lt;script&gt;" in out and "<script>" not in out


def test_text_and_svg_templates_keep_their_pre_pin_behaviour():
    # The pin reproduces select_autoescape()'s defaults EXACTLY, so no shipped
    # output moved. .svg (cosmic_card.svg) has always rendered unescaped; this
    # records it as a decision rather than an accident. Widening it is a
    # separate change that alters shipped bytes -- see ARCHITECTURE.md (#409).
    assert templates.env.autoescape("cosmic_card.svg") is False
    assert templates.env.autoescape("x.txt") is False


# --------------------------------------------------------------------------
# 2. /admin/feedback end to end, attribute context included
# --------------------------------------------------------------------------

# Passes the store's deliberately lax _EMAIL_RE while carrying " < > / .
LAX_EMAIL = 'a"<>/b@c".d'


@pytest.fixture
def admin_page(client, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")

    def _render(entry: dict) -> str:
        monkeypatch.setattr(feedback_store, "list_all", lambda: [entry])
        r = client.get("/admin/feedback", auth=("admin", "bhagya-dev"))
        assert r.status_code == 200
        return r.text

    return _render


def _entry(**over) -> dict:
    e = {"id": "abc123", "type": "problem", "message": "m", "email": "",
         "page": "", "ua": "", "ts": "2026-10-19T00:00:00Z"}
    e.update(over)
    return e


def test_the_lax_email_payload_really_passes_the_store_validator():
    # Otherwise the attribute-context test below would prove nothing about a
    # value the store can actually hold.
    assert feedback_store._EMAIL_RE.match(LAX_EMAIL)


def test_a_quote_and_angle_brackets_cannot_leave_the_mailto_attribute(admin_page):
    html = admin_page(_entry(email=LAX_EMAIL))
    assert 'href="mailto:a&#34;&lt;&gt;/b@c&#34;.d"' in html
    # ...and the visible text of the same link is escaped too.
    assert ">a&#34;&lt;&gt;/b@c&#34;.d</a>" in html


@pytest.mark.parametrize("field", ["message", "page", "ua", "email"])
def test_every_visitor_field_is_escaped_on_the_admin_page(admin_page, field):
    value = LAX_EMAIL if field == "email" else PAYLOAD
    html = admin_page(_entry(**{field: value}))
    assert "<script>alert" not in html
    assert "&lt;" in html


# --------------------------------------------------------------------------
# 3. No template renders a visitor field through an escape hatch
# --------------------------------------------------------------------------

_COMMENT = re.compile(r"\{#.*?#\}", re.S)
_TAG = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
_STRING = re.compile(r"'(?:\\.|[^'\\])*'|" + r'"(?:\\.|[^"\\])*"')
_UNSAFE = re.compile(r"\|\s*(?:safe|markup)\b|\bMarkup\s*\(")
_AUTOESCAPE_OFF = re.compile(
    r"\{%-?\s*autoescape\s+(?:false|off|0)\s*-?%\}(.*?)\{%-?\s*endautoescape\s*-?%\}",
    re.S | re.I)
_FIELD = re.compile(r"(?<![\w'\"])(?:%s)\b" % "|".join(VISITOR_FIELDS))


def scan(source: str, strict: bool = False) -> list[str]:
    """Return one finding per escape hatch that touches a visitor field.

    String literals are blanked first so `t(lang, 'email_subject')` -- a
    translation KEY that merely contains the word -- is not a visitor field.
    `strict` (templates that handle feedback entries) bans the hatch outright,
    because `{% set m = e.message %}{{ m|safe }}` launders the field through an
    alias this token match cannot follow.
    """
    source = _COMMENT.sub("", source)
    findings: list[str] = []
    for m in _TAG.finditer(source):
        tag = m.group(0)
        code = _STRING.sub("''", tag)
        if _UNSAFE.search(code) and (strict or _FIELD.search(code)):
            findings.append(f"escape hatch on a visitor field: {' '.join(tag.split())}")
    for m in _AUTOESCAPE_OFF.finditer(source):
        if strict or _FIELD.search(_STRING.sub("''", m.group(1))):
            findings.append("{% autoescape false %} around a visitor field")
    # An unterminated or unrecognised opener must not slip past the block regex.
    if strict and re.search(r"\{%-?\s*autoescape\s+(?:false|off|0)", source, re.I) \
            and not findings:
        findings.append("{% autoescape false %} in a feedback template")
    return findings


def _all_templates() -> list[Path]:
    return sorted(Path(TEMPLATES_DIR).rglob("*.html"))


# Scope of the STRICT rule: the templates that receive feedback entries. Chosen by
# name rather than by listing, so a new `*feedback*.html` is covered the day it
# is added; test_the_feedback_scope_is_not_empty stops a rename emptying it.
# Everything else gets the narrower field-token rule, because `|safe` is correct
# on app-controlled values (`t(lang, ...)`, `ops_json`, `intro_body`) all over the
# site and banning it globally would only teach people to route around the gate.
def _feedback_templates() -> list[Path]:
    return [p for p in _all_templates() if "feedback" in p.name]


def test_the_feedback_scope_is_not_empty():
    names = {p.name for p in _feedback_templates()}
    assert "admin_feedback.html" in names, names


def test_no_template_renders_a_visitor_field_through_an_escape_hatch():
    bad = {str(p.relative_to(TEMPLATES_DIR)): f
           for p in _all_templates() if (f := scan(p.read_text()))}
    assert not bad, bad


def test_feedback_templates_use_no_escape_hatch_at_all():
    bad = {p.name: f for p in _feedback_templates()
           if (f := scan(p.read_text(), strict=True))}
    assert not bad, bad


# The scanner is itself a gate, so prove it can go red -- and that it does not
# go red on the app-controlled uses it must leave alone.
@pytest.mark.parametrize("src", [
    "{{ e.ua | safe }}",
    "{{ e.message|safe }}",
    '<a href="mailto:{{ e.email | safe }}">',
    "{{ page|safe }}",
    "{{ e.ua | markup }}",
    "{{ Markup(e.message) }}",
    "{% autoescape false %}{{ e.page }}{% endautoescape %}",
    "{{ (e.message | trim)\n | safe }}",
])
def test_the_scanner_catches_each_escape_hatch(src):
    assert scan(src), src


def test_the_scanner_catches_an_aliased_field_only_in_strict_mode():
    src = "{% set m = e.message %}{{ m | safe }}"
    assert not scan(src)
    assert scan(src, strict=True)


@pytest.mark.parametrize("src", [
    "{{ t(lang, 'bhagya_lede') | safe }}",
    "{{ t(lang, 'email_subject') | safe }}",
    "{{ intro_body | safe }}",
    "{{ ops_json | safe }}",
    "{{ e.ua }}",
    "{# {{ e.ua | safe }} #}",
    "{% autoescape false %}{{ intro_body }}{% endautoescape %}",
])
def test_the_scanner_leaves_app_controlled_uses_alone(src):
    assert scan(src) == [], src
