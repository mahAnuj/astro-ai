# astro-ai

A Vedic-astrology AI product. A user enters their birth date, time, and place;
an LLM produces a personality reading. This repo is the **MVP foundation** —
the long-term product (with real chart calculation, accounts, Q&A, payments)
will be built on top of it after [prompteval](https://github.com/mahAnuj/prompteval)
v0.1 ships and is used to lock prompt quality here.

## What ships today (MVP)

| Piece | Status |
|---|---|
| Web form to collect birth details (date, time, place) | shipped |
| FastAPI backend that calls OpenAI with a Vedic-astrologer system prompt | shipped |
| Server-rendered reading page | shipped |
| Version-controlled prompts under `evals/prompts/` (so prompteval can iterate them) | shipped |

## Explicitly NOT in the MVP (and why)

- **Real chart calculation (ephemeris)** — Kundali computation needs `pyswisseph`
  + geocoding + timezone handling. Deferred to the next milestone. The MVP's LLM
  is asked to reason from the date (Sun sign) and time-of-day (rough Lagna)
  rather than invent specific planet placements. Readings will be looser than
  what real software produces; that's the explicit tradeoff for shipping fast.
- **User accounts / chart storage / Q&A chat** — comes after real chart calc.
- **Payments / paid tier** — comes after Q&A.
- **Prompt eval pipeline wired in** — depends on prompteval v0.1 reaching PyPI
  (Week 9 of prompteval's plan). The prompt files at `evals/prompts/v1.txt`
  and `v2.txt` are already in the right place for it.

## Run it locally

You'll need an OpenAI API key.

```bash
cp .env.example .env
# edit .env, add OPENAI_API_KEY

uv sync
uv run astro-ai
```

Open <http://127.0.0.1:8000>. The dev server auto-reloads when you edit
templates, code, or the prompt at `evals/prompts/v1.txt`.

## Where the prompt lives

`evals/prompts/v1.txt` is the system prompt the app serves. Edit it freely —
the app reads it fresh on every request, so there's no restart needed. This
location is deliberate: when prompteval is wired in, this same file is what
gets compared against `evals/prompts/v2.txt` in regression runs.

## Roadmap

1. **Now** — LLM-only MVP (this commit). Form + reading.
2. **Next** — wire `pyswisseph` + `geopy` + `timezonefinder` so the app
   actually computes the chart. Update the prompt to expect structured chart
   data as input.
3. **Then** — wire prompteval. Build `evals/dataset.jsonl` (synthetic charts
   to start, then real anonymised ones). Run `prompteval compare v1 v2` on
   every prompt edit; gate CI on regressions.
4. **Then** — user accounts, saved charts, multi-turn Q&A about a stored chart
   (the actual product wedge).
5. **Then** — paid tier (deeper readings, transit forecasts, compatibility),
   marketing.

## Disclaimer

Readings are interpretive and for personal reflection — not advice.
In this MVP the LLM does not compute planetary positions from an ephemeris,
so specific astrological claims should be taken as illustrative rather than
authoritative. Real chart calculation lands in the next milestone above.
