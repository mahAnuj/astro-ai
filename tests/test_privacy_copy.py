"""Privacy copy must be true of the code, and the admin views must survive both
event shapes (#255).

Every test pins a defect that shipped:

* `/privacy` told people to select "Delete my data" in a Feedback widget that
  has only Problem / Feature / Other -- the only documented deletion route did
  not exist.
* The same page and its neighbours promised "nothing stored on our servers",
  readings cached "a couple of weeks", and cookies that "expire if you go
  inactive" -- the natal cache has no expiry, and the cookie window is a flat
  365 days refreshed on write.
* `/admin/activity` and the dashboard read `name` / `birth_date` / `groom_dob`
  that the events log no longer stores, and would have rendered blank cells for
  every new row.

The copy is checked against the *rendered* page, not the template source, since
a Jinja variable that fails to resolve renders as nothing and passes a source
grep.
"""
from __future__ import annotations

import re

import pytest

from astro_ai import events, session

CONTACT = "contact@shubhagya.com"

# Phrases that were true of nothing. Each is a retired claim from #255.
BANNED = [
    "Nothing stored on our servers",           # kundli_landing.html:37
    "a couple of weeks",                       # privacy.html: natal cache is indefinite
    "expire if you go inactive",               # privacy.html: flat window, refreshed on write
    "All data stored securely in your session cookie",   # account.html: records live in GCS
    "the chart lives only in your browser cookie",       # kundli_landing.html FAQ
    "Delete my data",                          # privacy.html: no such option exists
]


def _text(html: str) -> str:
    """Rendered text with tags stripped and whitespace collapsed -- the copy as
    a reader (or a crawler reading the JSON-LD) sees it."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _signed_in(client) -> None:
    cookie = session._serializer().dumps({
        "user": {"email": "reader@example.test", "name": "Reader",
                 "sub": "sub-1", "since": "2026-10-01T00:00:00+00:00"},
    })
    client.cookies.set(session.COOKIE_NAME, cookie)


# ─── /privacy ──────────────────────────────────────────────────────────────


def test_privacy_page_does_not_point_at_a_delete_option_that_does_not_exist(client):
    from astro_ai.feedback import VALID_TYPES

    html = client.get("/privacy").text
    assert "Delete my data" not in html

    widget = client.get("/privacy").text  # widget is included in base.html
    labels = set(re.findall(r'name="type" value="(\w+)"', widget))
    assert labels == VALID_TYPES, "the widget and feedback.VALID_TYPES disagree"

    # Any instruction of the form: select "X" ... must name an option that exists.
    allowed = {t.lower() for t in VALID_TYPES} | {
        m.lower() for m in re.findall(
            r'<span[^>]*>\s*([A-Za-z ]+?)\s*</span>',
            widget[widget.find("feedback-modal"):])}
    for quoted in re.findall(r'[Ss]elect\s+(?:&quot;|"|“)([^"”&]+)', _text(html)):
        assert quoted.lower() in allowed, f'/privacy says select "{quoted}"'


def test_privacy_page_gives_an_email_to_ask_for_deletion(client):
    html = client.get("/privacy").text
    assert f"mailto:{CONTACT}" in html
    assert html.count(CONTACT) >= 3  # see data, delete, contact


def test_privacy_page_states_the_real_cache_and_cookie_windows(client):
    text = _text(client.get("/privacy").text)
    assert "indefinitely" in text
    days = session.COOKIE_MAX_AGE // 86400
    assert f"{days} days from the last time something is saved" in text
    assert "{{" not in text, "an unresolved template variable leaked"
    assert "don't sell or rent your personal information" in text


def test_privacy_page_discloses_what_still_reaches_the_operator(client):
    text = _text(client.get("/privacy").text)
    assert "Telegram" in text
    assert "Birth details (name, date, time, place) are never included" in text
    assert "activity log" in text.lower()


def test_privacy_page_date_is_a_literal_not_the_current_year(client):
    # `{{ current_year() }}-08-06` made the page claim an update this year,
    # every year, with a fixed month and day nobody had edited it on.
    assert "Last updated: 2026-10-11" in _text(client.get("/privacy").text)


# ─── retired claims, everywhere they were found ────────────────────────────


@pytest.mark.parametrize("path", ["/privacy", "/kundli", "/hi/kundli"])
def test_retired_claims_are_gone(client, path):
    r = client.get(path)
    if r.status_code == 404 and path.startswith("/hi/"):
        pytest.skip("no Hindi surface for this path")
    assert r.status_code == 200, path
    html = r.text
    for phrase in BANNED:
        assert phrase not in html, f"{path} still says {phrase!r}"


def test_signed_in_account_page_has_no_retired_claims(client):
    _signed_in(client)
    r = client.get("/account")
    assert r.status_code == 200
    for phrase in BANNED:
        assert phrase not in r.text, f"/account still says {phrase!r}"
    assert "stored in your account" in r.text


def test_kundli_faq_visible_text_and_json_ld_agree(client):
    """The FAQ answer lives once in a Jinja list and feeds both the visible
    <details> and the FAQPage JSON-LD; a hand-edit of one would leave search
    results quoting a claim the page no longer makes."""
    html = client.get("/kundli").text
    ld = re.search(r'"name": "Is my birth data stored anywhere\?".*?"text": "(.*?)"}}',
                   html, re.S)
    assert ld, "FAQPage JSON-LD lost the storage question"
    answer = ld.group(1)
    assert "signed cookie" in answer
    assert answer.encode().decode("unicode_escape") in html.replace("&#39;", "'")


# ─── admin views: both event shapes ────────────────────────────────────────


SENTINEL = "None"


def _new_kundli() -> dict:
    return {
        "ts": "2026-10-11T08:00:00+00:00", "type": "form_kundli", "email": "",
        "data": {"identity": "a3f91c2e" + "0" * 24, "lang": "hi",
                 "model": "gpt-oss-120b", "rashi_lagna": "Simha",
                 "rashi_moon": "Vrishabha", "rashi_sun": "Kanya",
                 "age_band": "30-39", "city": "Pune"},
    }


def _legacy_kundli() -> dict:
    return {
        "ts": "2026-10-01T08:00:00+00:00", "type": "form_kundli", "email": "",
        "data": {"name": "Priya", "birth_date": "1990-05-04",
                 "birth_time": "06:30", "birth_place": "Jaipur",
                 "lang": "en", "model": "gpt-oss-20b"},
    }


def _new_match() -> dict:
    return {
        "ts": "2026-10-11T09:00:00+00:00", "type": "form_matching", "email": "",
        "data": {"groom_key": "b7c1d2e3" + "0" * 24, "bride_key": "c8d2e3f4" + "0" * 24,
                 "total_score": "27/36", "verdict": "Excellent", "lang": "en",
                 "model": "gpt-oss-120b"},
    }


def _legacy_match() -> dict:
    return {
        "ts": "2026-10-01T09:00:00+00:00", "type": "form_matching", "email": "",
        "data": {"groom_name": "Arjun", "groom_dob": "1988-02-03",
                 "bride_name": "Meera", "bride_dob": "1990-09-10",
                 "total_score": "21/36", "verdict": "Good"},
    }


@pytest.fixture
def admin(client, monkeypatch):
    from astro_ai.main import app
    from astro_ai.routes.deps import require_admin

    app.dependency_overrides[require_admin] = lambda: None
    all_events = [_new_kundli(), _legacy_kundli(), _new_match(), _legacy_match()]

    def fake_recent(*, types=None, limit=100, days=7):
        return [e for e in all_events if types is None or e["type"] in types][:limit]

    monkeypatch.setattr(events, "recent", fake_recent)
    monkeypatch.setattr(events, "counts_by_type", lambda **k: {})
    yield client
    app.dependency_overrides.pop(require_admin, None)


def test_admin_activity_renders_both_event_shapes(admin):
    r = admin.get("/admin/activity")
    assert r.status_code == 200
    html = r.text
    # new shape: short key, rashi triple, age band, city
    assert "a3f91c2e" in html and "a3f91c2e0" not in html  # first 8 chars only
    assert "Simha / Vrishabha / Kanya" in html
    assert "30-39" in html and "Pune" in html
    assert "b7c1d2e3" in html and "c8d2e3f4" in html
    # legacy shape still readable
    assert "Priya" in html and "1990-05-04 06:30" in html and "Jaipur" in html
    assert "Arjun" in html and "Meera" in html


def test_admin_activity_has_no_blank_or_sentinel_cells(admin):
    html = admin.get("/admin/activity").text
    cells = re.findall(r"<td[^>]*>(.*?)</td>", html, re.S)
    assert cells
    for cell in cells:
        inner = _text(cell).strip()
        assert inner, f"blank cell: {cell!r}"
        assert inner != SENTINEL and "undefined" not in inner.lower(), cell


def test_admin_dashboard_renders_both_event_shapes(admin, monkeypatch):
    r = admin.get("/admin")
    assert r.status_code == 200
    text = _text(r.text)
    assert "a3f91c2e" in text and "Simha / Vrishabha / Kanya" in text
    assert "b7c1d2e3 × c8d2e3f4" in text
    assert "Priya · 1990-05-04 · Jaipur" in text
    assert "Arjun × Meera" in text
    assert "(anon)" not in text
    assert "· None" not in text and "None ·" not in text
