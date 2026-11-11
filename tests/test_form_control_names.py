"""Every visible form control needs an accessible name (#596).

Measured on production 2026-11-10: six controls carried a placeholder and nothing
else -- the subscribe modal's email, city and rashi, the feedback widget's message
and email, and /learn's search box. A placeholder is not a name (it vanishes on
input and is not reliably announced), so a screen reader said "edit text".

The test parses RENDERED HTML in both languages, not the template source, so an
`aria-label` that sits inside the wrong `{% if lang %}` arm, or renders empty, fails
here. It also pins the number of controls found per surface: a scan that finds
nothing proves nothing, and would pass if a control were renamed out of its reach.

Radios and checkboxes are excluded because they are wrapped in `<label>`; hidden,
submit and button inputs carry no field to name.
"""
from __future__ import annotations

from html.parser import HTMLParser

import pytest

_NAMELESS_OK = {"hidden", "radio", "checkbox", "submit", "button", "reset", "image"}


class _Scan(HTMLParser):
    """Collects each visible control and whether it has an accessible name."""

    def __init__(self) -> None:
        super().__init__()
        self.controls: list[tuple[str, dict[str, str]]] = []
        self._label_for: set[str] = set()
        self._in_label = 0
        self._label_stack_controls: list[int] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "label":
            self._in_label += 1
            if a.get("for"):
                self._label_for.add(a["for"])
        elif tag in ("input", "select", "textarea"):
            if tag == "input" and a.get("type", "text").lower() in _NAMELESS_OK:
                return
            a["_wrapped"] = "1" if self._in_label else ""
            self.controls.append((tag, a))

    def handle_endtag(self, tag):
        if tag == "label" and self._in_label:
            self._in_label -= 1

    def unnamed(self) -> list[str]:
        bad = []
        for tag, a in self.controls:
            named = (
                a.get("aria-label", "").strip()
                or a.get("aria-labelledby", "").strip()
                or a.get("title", "").strip()
                or a["_wrapped"]
                or (a.get("id") and a["id"] in self._label_for)
            )
            if not named:
                bad.append(f"<{tag} name={a.get('name')!r} id={a.get('id')!r}>")
        return bad


def _scan(html: str) -> _Scan:
    s = _Scan()
    s.feed(html)
    return s


def _render(template: str, lang: str) -> str:
    from starlette.requests import Request

    from astro_ai.routes.deps import templates
    # The subscribe modal reads the session cookie, so it needs a real Request.
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [],
                       "query_string": b"", "scheme": "http", "server": ("t", 80)})
    return templates.env.get_template(template).render(lang=lang, request=request)


@pytest.mark.parametrize("lang", ["en", "hi"])
@pytest.mark.parametrize("template,expected", [
    ("_subscribe_modal.html", {"email", "city", "rashi"}),
    ("_feedback_widget.html", {"message", "email"}),
])
def test_partial_controls_are_named(template, expected, lang):
    scan = _scan(_render(template, lang))
    found = {a.get("name") for _, a in scan.controls}
    assert expected <= found, f"{template} ({lang}): expected controls {expected}, found {found}"
    assert scan.unnamed() == [], f"{template} ({lang}) has controls with no accessible name"


def test_learn_index_search_is_named(client):
    r = client.get("/learn")
    assert r.status_code == 200, r.status_code
    scan = _scan(r.text)
    assert any(a.get("id") == "learn-search" for _, a in scan.controls), (
        "#learn-search not found; the test proves nothing")
    assert scan.unnamed() == []


def test_homepage_controls_are_named(client):
    """The pages the issue measured: the partials arrive through base.html."""
    r = client.get("/")
    assert r.status_code == 200, r.status_code
    scan = _scan(r.text)
    names = {a.get("name") for _, a in scan.controls}
    assert {"city", "rashi", "message"} <= names, names
    assert scan.unnamed() == []


def test_the_scan_can_fail():
    """Guard against the scan being a function that passes any HTML."""
    s = _scan('<input type="email" name="x" placeholder="p"><textarea></textarea>'
              '<input type="hidden" name="h"><label><input type="radio"></label>'
              '<input id="ok"><label for="ok">Ok</label><select aria-label="  "></select>')
    assert len(s.unnamed()) == 3, s.unnamed()
