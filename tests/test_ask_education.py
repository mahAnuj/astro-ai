"""#402 AC1 + AC6 -- the `education` focus area on /ask, and the honesty line it carries.

SCOPE, STATED PLAINLY: nothing here calls a model. These tests read the category
set, the rendered chip, the category the POST hands the generator, and the text of
`prompts/ask.txt`. They show that the model is TOLD that an exam outcome cannot be
settled from this chart; whether it obeys is unmeasured until a probe runs against
a live provider.

Where the entry comes from. knowledge/houses.md "Studies and exams -- SOURCED"
(Rao 7.2, 7.3.5, 13.4.1): 4th = formal/early education, 5th = intelligence and
scholarship, 9th = higher studies. Rao reads *success in an exam* as the 5th from
Arudha Lagna in D-24, and neither Arudha nor D-24 is in the data /ask receives, so
the prompt says the chart cannot settle it (AC6) rather than improvising one. The
6th house is NOT an exam house in the corpus (#402's CORRECTION comment), so it
must not appear in the entry.
"""
from __future__ import annotations

import re
from types import SimpleNamespace

from fastapi.testclient import TestClient

from astro_ai import llm
from astro_ai.routes import ask as ask_route
from astro_ai.routes import deps
from astro_ai.session import SavedChart

PROMPT = llm._system_prompt(deps.ASK_PROMPT_PATH, "en", None)
SAVED = SavedChart(id="c1", name="Test", birth_date="1990-04-15",
                   birth_time="07:30", birth_place="New Delhi")


def _entry() -> str:
    hits = [ln for ln in PROMPT.splitlines() if ln.startswith("- education:")]
    assert len(hits) == 1, hits
    return hits[0]


def _client(monkeypatch):
    from astro_ai.main import app

    monkeypatch.setattr(ask_route, "load_collection",
                        lambda request: SimpleNamespace(active=SAVED))
    monkeypatch.setattr(ask_route.events, "record", lambda **k: None)
    monkeypatch.setattr(ask_route.notify, "ask_submitted", lambda **k: None)
    seen: dict = {}

    def fake_generate(**kw):
        seen.update(kw)
        return "EDU-ANSWER-402"

    monkeypatch.setattr(ask_route, "generate_ask_answer", fake_generate)
    return TestClient(app), seen


def test_education_is_an_accepted_category():
    assert "education" in ask_route._ASK_CATEGORIES


def test_a_post_with_education_reaches_the_generator_as_education(monkeypatch):
    """Not coerced to `general` (routes/ask.py: an unknown category is)."""
    client, seen = _client(monkeypatch)
    r = client.post("/ask", data={"question": "How will my studies go this year?",
                                  "category": "education"}, follow_redirects=False)
    assert r.status_code == 303, r.text[:200]
    assert seen["category"] == "education"
    assert "c=education" in r.headers["location"]


def test_an_unknown_category_is_still_coerced_to_general(monkeypatch):
    """The allow-list still bites: adding one value must not open it."""
    client, seen = _client(monkeypatch)
    client.post("/ask", data={"question": "How will my studies go this year?",
                              "category": "exams-guaranteed"}, follow_redirects=False)
    assert seen["category"] == "general"


def test_the_education_chip_renders_and_is_checked_when_selected(monkeypatch):
    client, _ = _client(monkeypatch)
    page = client.get("/ask?c=education")
    assert page.status_code == 200
    chip = re.search(r'<input type="radio" name="category" value="education"([^>]*)>',
                     page.text, re.S)
    assert chip, "no education chip in the Focus area row"
    assert "checked" in chip.group(1)
    other = re.search(r'<input type="radio" name="category" value="career"([^>]*)>',
                      page.text, re.S)
    assert other and "checked" not in other.group(1)


def test_every_chip_the_template_offers_is_an_accepted_category():
    """A chip the route would coerce to `general` is a button that lies."""
    from pathlib import Path

    html = (Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates"
            / "ask.html").read_text(encoding="utf-8")
    loop = re.search(r"\{% for cat in \[([^\]]*)\] %\}", html)
    chips = set(re.findall(r"'([a-z]+)'", loop.group(1)))
    assert "education" in chips
    assert chips == ask_route._ASK_CATEGORIES


def test_the_entry_names_only_the_bhavas_the_corpus_gives_for_learning():
    entry = _entry()
    for house in ("4th", "5th", "9th"):
        assert house in entry
    # The 6th is rivals/service/health in Rao, never the exam house (#402 CORRECTION).
    assert not re.search(r"\b(6|six)(th)?\b|sixth", entry, re.I)
    # No other house number appears either: only the three that trace.
    assert set(re.findall(r"\b(\d+)(?:st|nd|rd|th)\b", entry)) == {"4", "5", "9"}


def test_the_entry_says_the_chart_cannot_settle_an_exam_and_gives_no_verdict():
    low = _entry().lower()
    assert "cannot settle whether an exam is passed" in low
    assert "no pass/fail" in low
    assert "improvise none" in low
    # AC6's positive half: what it CAN speak to.
    assert "learning and focus" in low


def test_the_entry_does_not_teach_the_model_jargon_it_is_forbidden_to_emit():
    low = _entry().lower()
    for word in ("d-24", "d24", "arudha", "karaka", "navamsa", "lagna", "rao", "bphs"):
        assert word not in low, word
    assert "never say these numbers" in low


def test_the_entry_sits_inside_category_guidance_and_the_prompt_still_forbids_house_numbers():
    start = PROMPT.index("CATEGORY GUIDANCE")
    end = PROMPT.index("CROSS-LINK RULE")
    assert _entry() in PROMPT[start:end]
    assert "DO NOT reference natal house numbers" in PROMPT
    assert "Never a yes/no verdict" in PROMPT


def test_no_learn_slug_is_invented_for_education():
    """The CROSS-LINK list has no education article; adding a link to one that
    does not exist is the failure the list's own 'do not invent slugs' guards."""
    from pathlib import Path

    slugs = set(re.findall(r"`/learn/([a-z0-9-]+)/`", PROMPT))
    learn = Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates" / "learn"
    for slug in slugs:
        assert (learn / f"{slug}.html").exists(), slug
    assert not any(k in s for s in slugs for k in ("exam", "education", "study", "student"))
