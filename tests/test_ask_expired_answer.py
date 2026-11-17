"""#1087 -- a /ask?q=... link whose cached answer is gone must say so.

`POST /ask` writes the answer to the per-instance /tmp SQLite cache and 303s to a
GET that only READS it. A redeploy, a cold start or a second Cloud Run instance
makes that read miss, and the page used to render the question echoed back with no
answer and no word of why (200, no alert). Nothing here calls a model.
"""
from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from astro_ai.routes import ask as ask_route
from astro_ai.session import SavedChart

SAVED = SavedChart(id="c1", name="Test", birth_date="1990-04-15",
                   birth_time="07:30", birth_place="New Delhi")
Q = "When will I get married?"


def _client(monkeypatch, lookup):
    from astro_ai.main import app

    monkeypatch.setattr(ask_route, "load_collection",
                        lambda request: SimpleNamespace(active=SAVED))
    monkeypatch.setattr(ask_route, "_ask_lookup", lookup)
    return TestClient(app)


def test_cache_miss_renders_a_notice_not_a_silent_page(monkeypatch):
    r = _client(monkeypatch, lambda *a, **k: None).get(
        "/ask", params={"q": Q, "c": "marriage"})
    assert r.status_code == 200
    assert 'data-ask-expired' in r.text
    assert 'role="status"' in r.text
    # the question is still in the box, so re-asking is one press
    assert r.text.count(Q) == 1
    assert 'ask_answered' not in r.text


def test_cache_hit_shows_the_answer_and_no_notice(monkeypatch):
    r = _client(monkeypatch, lambda *a, **k: "THE-ANSWER-1087").get(
        "/ask", params={"q": Q, "c": "marriage"})
    assert "THE-ANSWER-1087" in r.text
    assert 'data-ask-expired' not in r.text


def test_plain_form_visit_shows_no_notice(monkeypatch):
    r = _client(monkeypatch, lambda *a, **k: None).get("/ask")
    assert r.status_code == 200
    assert 'data-ask-expired' not in r.text
