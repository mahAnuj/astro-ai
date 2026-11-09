"""#817: the visitor's name never enters the server-rendered <title> (or the og:/
twitter: tags and meta description that copy it) on the eight routes #744 found.

gtag collects `document.title` and `base.html` copies `self.title()` into og:title
and twitter:title, so a name in the title reached analytics, tab titles, bookmarks
and social cards. The sentinel is the one the PII sweep uses; every test renders
the real route and reads the real HTML. The ratchet in test_pii_egress_analytics.py
catches the same leak through `KNOWN_GAPS`; these tests name the routes, cover
`lang=hi`, and prove the sentinel IS on the page body where the h1 still names the
visitor, so "not in the title" is not vacuously true of a page that never rendered it.
"""
from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_pii_egress.py"
if "verify_pii_egress" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("verify_pii_egress", _SCRIPT)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["verify_pii_egress"] = _mod
    _spec.loader.exec_module(_mod)
pii = sys.modules["verify_pii_egress"]

_HEAD_TAGS = (
    re.compile(r"<title>(.*?)</title>", re.S),
    re.compile(r'<meta property="og:title" content="(.*?)">', re.S),
    re.compile(r'<meta name="twitter:title" content="(.*?)">', re.S),
)


@pytest.fixture
def client(monkeypatch, caplog, tmp_path):
    """The PII sweep's recorders (no network, no GCS, no LLM) and a TestClient."""
    from fastapi.testclient import TestClient

    from astro_ai import cache, daily_cache
    from astro_ai.main import app
    from astro_ai.routes import kundli, llm_support

    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "bhagya.db")
    monkeypatch.setattr(daily_cache, "_ROOT", tmp_path / "daily_cache")
    llm_support._DURABLE_MISSES.clear()
    pii.Egress(llm_mode="ok").install(monkeypatch)
    monkeypatch.setattr(kundli, "_SNAPSHOT_CREATED_TODAY", {})
    monkeypatch.setattr(kundli, "_EMAIL_KUNDLI_LAST_SENT", {})
    c = TestClient(app)
    c.monkeypatch = monkeypatch
    return c


def _signed_in_with_chart(c):
    pii.sign_in(c, c.monkeypatch)
    pii.save_chart(c)


def _head(html: str) -> list[str]:
    found = [m.group(1) for rx in _HEAD_TAGS if (m := rx.search(html))]
    assert len(found) == len(_HEAD_TAGS), "title / og:title / twitter:title not all on the page"
    return found


def _no_name_in_head(html: str, *names: str):
    for tag in _head(html):
        for n in names:
            assert n not in tag, f"{n!r} is in a head title: {tag!r}"
    # the meta description is copied into og:description/twitter:description
    for rx in (re.compile(r'<meta name="description" content="(.*?)">', re.S),
               re.compile(r'<meta property="og:description" content="(.*?)">', re.S)):
        for m in rx.finditer(html):
            for n in names:
                assert n not in m.group(1), f"{n!r} is in a description: {m.group(1)[:120]!r}"


@pytest.mark.parametrize("lang, anon", [("en", "Your reading"), ("hi", "आपका पठन")])
def test_kundli_title_is_the_anon_key_and_the_h1_still_names_the_visitor(client, lang, anon):
    _signed_in_with_chart(client)
    r = client.get(f"/kundli?lang={lang}")
    assert r.status_code == 200
    assert pii.NAME in r.text, "the name is no longer on the page body: this test is vacuous"
    _no_name_in_head(r.text, pii.NAME)
    assert f"<title>{anon} — Shubh Bhagya</title>" in r.text


@pytest.mark.parametrize("path, lang, anon", [
    ("/monthly", "en", "Your month ahead"), ("/monthly", "hi", "आपका मासिक भविष्यफल"),
    ("/yearly", "en", "Your year ahead"), ("/yearly", "hi", "आपका वार्षिक भविष्यफल"),
])
def test_outlook_title_is_the_anon_key(client, path, lang, anon):
    _signed_in_with_chart(client)
    r = client.get(f"{path}?lang={lang}")
    assert r.status_code == 200
    assert pii.NAME in r.text, "the name is no longer on the page body: this test is vacuous"
    _no_name_in_head(r.text, pii.NAME)
    assert f"<title>{anon} — Shubh Bhagya</title>" in r.text


@pytest.mark.parametrize("path, title", [
    ("/manglik-check", "Manglik Dosh Check — Shubh Bhagya"),
    ("/sade-sati-check", "Sade Sati Report — Shubh Bhagya"),
    ("/kaal-sarp-check", "Kaal Sarp geometry check — Shubh Bhagya"),
])
def test_dosha_result_title_is_name_free_for_an_anonymous_post(client, path, title):
    """No sign-in, no saved chart: the anonymous POST path."""
    r = client.post(path, data=pii.BIRTH_FORM)
    assert r.status_code == 200
    _no_name_in_head(r.text, pii.NAME)
    assert f"<title>{title}</title>" in r.text


def test_numerology_title_and_description_are_name_free(client):
    r = client.post("/numerology", data={"name": pii.NAME, "birth_date": pii.DOB})
    assert r.status_code == 200
    assert pii.NAME in r.text, "the h1 no longer names the visitor: this test is vacuous"
    _no_name_in_head(r.text, pii.NAME, pii.NAME.split()[0])
    assert re.search(r"<title>Numerology Reading — Life Path \d+</title>", r.text)


def test_numerology_compatibility_title_and_description_are_name_free(client):
    r = client.post("/numerology/compatibility", data={
        "name_a": pii.NAME, "birth_date_a": pii.DOB,
        "name_b": pii.B_NAME, "birth_date_b": pii.B_DOB})
    assert r.status_code == 200
    _no_name_in_head(r.text, pii.NAME, pii.B_NAME, pii.NAME.split()[0], pii.B_NAME.split()[0])
    assert re.search(r"<title>Numerology Compatibility — \d+/100</title>", r.text)
