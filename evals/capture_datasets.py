"""Capture the EXACT messages production sends for every prompt, as eval datasets.

Run (regenerates evals/datasets/<prompt>.jsonl):

    PYTHONPATH=tests uv run pytest -p conftest evals/capture_datasets.py -q

WHY THIS AND NOT A HAND-WRITTEN DATASET. A prompt is only half of what the
model sees: the user message (chart, dasha, flags, transits, today's date, the
question, a partner chart) is assembled by eleven different builders, and an
eval whose inputs drift from those builders measures a prompt nobody runs.
So this drives the REAL routes in-process -- with the suite's own offline
isolation (tests/conftest.py, loaded as a plugin) -- and replaces only the
model call with a recorder. Every row is what production would have sent.

Two deliberate differences from the test suite:
  * places resolve to their real coordinates (a small table below), not all
    to Mumbai, so the fixture charts differ the way real users' do;
  * /ask's per-visitor daily quota is lifted, since each seeker asks four;
  * the recorder returns a long, neutral body so routes that validate a
    reading's shape do not loop; only the FIRST call per (prompt, fixture)
    is kept.

Nothing here is imported by the app or collected by the suite (`testpaths`
is `tests`).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "src" / "astro_ai" / "prompts"
OUT = Path(__file__).resolve().parent / "datasets"

# Real coordinates for the fixture cities (lat, lon, tz). Approximate to the
# city centre, which is all a birth chart from a city name ever is.
PLACES = {
    "Mumbai, India": (19.0760, 72.8777, "Asia/Kolkata"),
    "Delhi, India": (28.6139, 77.2090, "Asia/Kolkata"),
    "Bangalore, India": (12.9716, 77.5946, "Asia/Kolkata"),
    "Chennai, India": (13.0827, 80.2707, "Asia/Kolkata"),
    "Kolkata, India": (22.5726, 88.3639, "Asia/Kolkata"),
    "Pune, India": (18.5204, 73.8567, "Asia/Kolkata"),
    "London, UK": (51.5074, -0.1278, "Europe/London"),
    "New York, USA": (40.7128, -74.0060, "America/New_York"),
}

# Eight seekers: a spread of lagnas, decades, hemispheres and birth hours.
SEEKERS = [
    {"name": "Anuj", "birth_date": "1990-05-15", "birth_time": "08:30", "birth_place": "Mumbai, India"},
    {"name": "Priya", "birth_date": "1992-08-22", "birth_time": "14:15", "birth_place": "Delhi, India"},
    {"name": "Arjun", "birth_date": "1985-11-03", "birth_time": "22:45", "birth_place": "Bangalore, India"},
    {"name": "Meera", "birth_date": "1998-02-18", "birth_time": "06:10", "birth_place": "Chennai, India"},
    {"name": "Rohan", "birth_date": "1976-09-30", "birth_time": "11:20", "birth_place": "London, UK"},
    {"name": "Kavya", "birth_date": "2001-12-05", "birth_time": "03:40", "birth_place": "Kolkata, India"},
    {"name": "Vikram", "birth_date": "1969-07-21", "birth_time": "17:55", "birth_place": "Pune, India"},
    {"name": "Sara", "birth_date": "1994-03-11", "birth_time": "09:05", "birth_place": "New York, USA"},
]
# One question per seeker, the kinds /ask actually gets.
QUESTIONS = [
    "Will I get a better job this year?",
    "When is a good time for me to get married?",
    "Should I start my own business?",
    "What does my chart say about my health?",
    "Is this a good period to buy a house?",
    "Why do I feel stuck in my career right now?",
    "What remedies would help me during this dasha?",
    "Will moving abroad work out for me?",
]
RASHIS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio"]

BODY = (
    "## Overview\n" + "This period asks for patience and steady effort. " * 40 + "\n\n"
    "## Remedies\n" + "Keep a simple routine and observe the day's discipline. " * 20
)


def _prompt_of(system: str) -> str | None:
    """Which prompt file produced this system message. An /ask overlay is
    appended after ask.txt, so the overlay (the more specific file) wins."""
    texts = {p.stem: p.read_text(encoding="utf-8").strip() for p in PROMPTS.glob("*.txt")}
    overlays = [n for n in texts if n.startswith("ask_") and texts[n] and texts[n] in system]
    if overlays:
        return max(overlays, key=lambda n: len(texts[n]))
    hits = [n for n, t in texts.items() if t and system.startswith(t[:400])]
    return max(hits, key=lambda n: len(texts[n])) if hits else None


def test_capture(client, monkeypatch):
    import astro_ai.chart as chart
    import astro_ai.llm as llm

    monkeypatch.setattr(chart, "geocode_place", lambda place: PLACES.get(place, PLACES["Mumbai, India"]))
    # /ask has a per-visitor daily quota; each seeker asks four questions here.
    import astro_ai.routes.ask as ask_route
    monkeypatch.setattr(ask_route, "_ask_quota_remaining", lambda request: 99)

    rows: dict[str, dict[str, dict]] = {}
    current = {"id": "?"}

    def record(*a, **k):
        msgs = k.get("messages") or (a[0] if a else [])
        system = next((m["content"] for m in msgs if m.get("role") == "system"), "")
        user = "\n\n".join(m["content"] for m in msgs if m.get("role") == "user")
        name = _prompt_of(system)
        if name and user:
            rows.setdefault(name, {}).setdefault(current["id"], {"id": current["id"], "input": user})
        return BODY

    monkeypatch.setattr(llm.providers, "chat", record)

    for i, s in enumerate(SEEKERS):
        sid = s["name"].lower()
        client.cookies.clear()
        r = client.post("/reading", data=s, follow_redirects=False)
        assert r.status_code == 303, (s, r.status_code)
        for path in ("/kundli", "/today", "/monthly", "/yearly", "/dasha/deep-dive"):
            current["id"] = sid
            client.get(path)
        current["id"] = sid
        client.post("/ask", data={"question": QUESTIONS[i], "category": "general", "context": "chart"})
        current["id"] = f"{sid}-num"
        client.post("/ask", data={"question": "What do my numbers say about this year?",
                                  "category": "general", "context": "numerology"})
        partner = SEEKERS[(i + 1) % len(SEEKERS)]
        current["id"] = f"{sid}+{partner['name'].lower()}"
        client.post("/matching", data={
            "g_name": s["name"], "g_birth_date": s["birth_date"], "g_birth_time": s["birth_time"],
            "g_birth_place": s["birth_place"], "b_name": partner["name"],
            "b_birth_date": partner["birth_date"], "b_birth_time": partner["birth_time"],
            "b_birth_place": partner["birth_place"]})
        client.post("/ask", data={"question": "Are we compatible for marriage?",
                                  "category": "general", "context": "matching"})
        # A third party's match: the seeker is neither partner.
        a, b = SEEKERS[(i + 2) % len(SEEKERS)], SEEKERS[(i + 3) % len(SEEKERS)]
        current["id"] = f"{sid}:{a['name'].lower()}+{b['name'].lower()}"
        client.post("/matching", data={
            "g_name": a["name"], "g_birth_date": a["birth_date"], "g_birth_time": a["birth_time"],
            "g_birth_place": a["birth_place"], "b_name": b["name"], "b_birth_date": b["birth_date"],
            "b_birth_time": b["birth_time"], "b_birth_place": b["birth_place"]})
        client.post("/ask", data={"question": "Is this a good match for them?",
                                  "category": "general", "context": "matching"})

    for rashi in RASHIS:
        current["id"] = rashi
        client.get(f"/rashifal/{rashi}")

    OUT.mkdir(exist_ok=True)
    for name, by_id in sorted(rows.items()):
        (OUT / f"{name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in by_id.values()), encoding="utf-8")
        print(f"{name}: {len(by_id)} rows")
    missing = sorted(p.stem for p in PROMPTS.glob("*.txt") if p.stem not in rows)
    print("not captured:", missing or "none")
    if missing:
        pytest.fail(f"no dataset captured for {missing}; add a route call above")
