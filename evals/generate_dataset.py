"""Generate evals/dataset.jsonl from a list of fixture birth details.

Re-run any time the production prompt's expected user-message shape changes
(e.g. if we add new data blocks). Each row contains the exact user-message
string the LLM will see, plus `expected` metadata the scorers will check.

Usage:
    uv run python evals/generate_dataset.py
"""

from __future__ import annotations

import json
from pathlib import Path

from astro_ai.chart import compute_chart, compute_vedic_flags, format_flags_for_prompt, format_for_prompt
from astro_ai.llm import BirthDetails


# Five fixture seekers covering a spread of Lagnas, dosha states, and locations.
FIXTURES: list[dict[str, str]] = [
    {"id": "fx-anuj",   "name": "Anuj",   "birth_date": "1990-05-15", "birth_time": "08:30", "birth_place": "Mumbai, India"},
    {"id": "fx-priya",  "name": "Priya",  "birth_date": "1992-08-22", "birth_time": "14:15", "birth_place": "Delhi, India"},
    {"id": "fx-arjun",  "name": "Arjun",  "birth_date": "1985-11-03", "birth_time": "22:45", "birth_place": "Bangalore, India"},
    {"id": "fx-meera",  "name": "Meera",  "birth_date": "1998-02-18", "birth_time": "06:10", "birth_place": "Chennai, India"},
    {"id": "fx-rohan",  "name": "Rohan",  "birth_date": "1976-09-30", "birth_time": "11:20", "birth_place": "London, UK"},
]


def build_row(fixture: dict[str, str]) -> dict[str, object]:
    """Compute the chart + flags, then format the input + expected blocks."""
    details = BirthDetails(
        name=fixture["name"],
        birth_date=fixture["birth_date"],
        birth_time=fixture["birth_time"],
        birth_place=fixture["birth_place"],
    )
    chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    flags = compute_vedic_flags(chart)
    moon = next(p for p in chart.planets if p.name == "Moon")
    sun = next(p for p in chart.planets if p.name == "Sun")

    user_message = (
        f"Name: {details.name}\n"
        f"Birth date: {details.birth_date}\n"
        f"Birth time: {details.birth_time} (local time)\n"
        f"Birth place: {details.birth_place}\n"
        f"\n"
        f"{format_for_prompt(chart)}\n"
        f"\n"
        f"{format_flags_for_prompt(flags)}\n"
    )

    # `expected` carries the data scorers use to grade output personalisation.
    expected = {
        "lagna_sign": chart.lagna_rashi.split(" (")[0],          # "Cancer"
        "moon_sign":  moon.rashi.split(" (")[0],                 # "Pisces"
        "moon_nakshatra": moon.nakshatra,                        # "Revati"
        "sun_sign":   sun.rashi.split(" (")[0],
        "manglik":    flags.manglik,
        "sade_sati":  flags.sade_sati,
        # Scorers should confirm the output mentions the seeker's actual placements.
        "must_mention": [chart.lagna_rashi.split(" (")[0], moon.nakshatra],
        # Six section headings the prompt asks for.
        "required_sections": [
            "Personality", "Career", "Wealth", "Relationships", "Health", "Travel",
        ],
        "min_chars": 1500,
        "max_chars": 6000,
    }

    return {"id": fixture["id"], "input": user_message, "expected": expected}


def main() -> None:
    here = Path(__file__).resolve().parent
    out = here / "dataset.jsonl"
    rows = [build_row(fx) for fx in FIXTURES]
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
