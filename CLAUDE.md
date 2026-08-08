# CLAUDE.md — working agreements for this repo

Shubh Bhagya (shubhagya.com) — Vedic astrology web app. FastAPI + Jinja2, Python ≥3.12,
managed with `uv`.

---

## ⚠️ Pushing to `main` deploys to production

**A push to `main` triggers a Cloud Build → Cloud Run deploy of the live site.**
There is no `.github/workflows/` and no `cloudbuild.yaml` in this repo — the trigger is
configured GCP-side, so nothing in the working tree reveals it. Do not conclude "no CI"
from the absence of those files.

There is **no staging environment** and **no test suite**. A push is the deploy, and
production is the first place code runs.

### Rules for agents

- **Never `git push` unless the user asks in that turn.** Committing locally is fine and
  encouraged; pushing is a production deploy and is the user's decision every time.
- **Never push work that has not passed QA.** In the `/feature` and `/bug` loops, only the
  user pushes after the ship summary — not the engineer that wrote the code, and not the
  dev-lead.
- If a task genuinely needs to reach production, say so and ask. Do not infer standing
  permission from a previous push.
- Prefer a branch for anything non-trivial. Landing directly on `main` is for small,
  verified, single-purpose commits.

---

## Close the issue when it ships — with evidence

An issue is not done when the code is written. It is done when it is **deployed and
verified**, and the issue says so.

**Two stages, and do not merge them:**

1. **When the fix lands locally** — comment on the issue with the commit SHA, what changed,
   the gate output, and anything deliberately left undone. **Do not close yet.** `main`
   auto-deploys on push and pushing is the user's decision, so nothing is live until they
   ship it.
2. **Once deployed** — verify against `origin/main` and production, then close with that
   evidence.

**A closing comment must let someone else check you.** Not "fixed" — the commit, what was
verified and how, and the numbers. Examples worth copying: the #144 close (before/after
timings on a named revision), the #157 close (the measurement showing it did not
reproduce), the #154 close (30/30 SHAs, byte-identical route table).

**Do not close on a claim.** Verify against `origin/main`, not against a comment saying it
was fixed. #143 was closed as fixed while a fourth wrong date was still live — QA caught it
and it had to be reopened.

**Partial work does not close.** Comment with what landed and what remains, and leave it
open. A half-closed issue is how #140 would have hidden that its intent classifier was
never wired to anything.

**When an issue turns out not to be real**, close it with the counter-evidence and say what
would make it real — #156's close records that the signed-in path was never tested, so a
genuine repro can still be filed.

**Related issues:** if a fix resolves part of another issue, say so on both. If it makes
another issue obsolete, close that one too rather than leaving it to rot — stale issues
cost more than they look, because the next triage has to re-verify them.

## Verify before you claim

This repo has burned real user-facing time on confident-but-wrong claims. Two rules:

1. **Never report a subagent's output you did not actually receive.** "Still running" and
   "no output yet" are complete answers. Do not reconstruct a spec, a table, or a result
   from memory and present it as delivered work — that is how invented data enters the
   codebase.
2. **Verify data before shipping it, especially dates.** `_FESTIVALS_2026` shipped with
   9 of 17 dates wrong — by up to 21 days — under a header claiming a provenance it did
   not have. Any almanac date, festival date, or muhurat window must be checked against a
   real source, and the source recorded in a comment next to it.

When you cannot verify something, say you could not. When you cannot source a requirement,
ask where it came from rather than concluding it was fabricated — agents cannot see the
user's turns, only the prompt they were handed.

---

## Report status while you run

Background agents are opaque from the outside — the user sees "3 agents running" and
nothing else. Every agent must leave a visible trail.

**Append a line to `AGENT_STATUS.md` (repo root, gitignored) at every meaningful step.**
One line, newest at the bottom:

```
HH:MM  <agent-role> [#issue]  <what just happened / what is next>
```

**Never type the timestamp yourself — you do not have a clock and will guess wrong.**
Let the shell stamp it, always via this exact form:

```bash
printf '%s  dev-lead #132  registry engineer returned; wiring route next\n' \
  "$(date +%H:%M)" >> AGENT_STATUS.md
```

Use `>>` only. Never `>`, never Write, never Edit on this file — a single `>` destroys
every prior line, including other agents' entries, and several agents append concurrently.

Append when you: start, finish reading/design, dispatch a subagent, get one back, start
writing files, commit, hit a blocker, or finish. Do not batch these — write each one as it
happens. If a run dies mid-response (it has happened repeatedly here), this file is the
only record of how far it got.

Dev-leads additionally: append a one-line roster whenever the set of live subagents
changes, so the count the user sees maps to actual work:

```
HH:MM  dev-lead #132  live: architect(design), engineer-1(hub route)
```

Keep lines short. This is a heartbeat, not a report — the ship summary is separate.

---

## Layout

```
src/astro_ai/
  main.py          FastAPI app + every route (large; edit surgically, re-read before editing)
  chart.py         Swiss Ephemeris chart computation, panchang, dashas
  muhurat.py       Muhurat scoring; shares tithi/nakshatra/yoga/karana with panchang
  festivals.py     Festival calendar (date-keyed). Feeds emails + rashifal LLM prompt
  events.py        GCS event log. EVENT_RETENTION_DAYS = 30 — recent() clamps to it
  storage.py       GCS blob read/write. No prefix listing — you cannot enumerate blobs
  profiling.py     Admin audience aggregation (/admin/insights)
  intents.py       stdlib-only regex question-intent classifier
  llm.py           Provider-agnostic LLM calls (OpenAI-compatible)
  knowledge/*.md   Classical Vedic source texts — the authority for astrological claims
  prompts/*.txt    LLM prompt templates
  templates/       Jinja2. learn/ (75 articles), email/, admin_*.html, panchang.html
```

### Source books in `data/` — only four of seven are readable

`pdftotext` works on four; two return **zero lines** (scanned images, no OCR layer, no OCR
tooling installed). Do not burn time trying to read them:

| readable | zero lines |
|---|---|
| `vedic_astro_textbook.pdf` (20,669 — richest, largely unextracted) | `varahmihirHorasastram.pdf` |
| `Astrology For Beginners BVRaman_text.pdf` (15,409) | `Numerology.pdf` |
| `Numerology-With Tantra…` / Johari (5,952) | |
| `Numerology-You.pdf` (1,110 — 43pp sample) | |

`Numerology.pdf` is an Adobe Scan capture with **no title or author metadata**, so even
OCR'd it would be uncitable — it is permanently out of scope (#178). Varahamihira is the
only OCR candidate with a real claim, and it is spike-gated.

**Measured absences — do not re-search:** across all ~37,000 readable lines, `Yoni`, `Vashya`
and `Lo Shu` each return **0 hits**. The Ashtakoota matching tables are not in any readable
source here. That is an absence to report, not a gap to fill from memory.

`data/` is gitignored for copyright hygiene. Cite work and chapter; never paste pages.
See `knowledge/SOURCES.md` for per-book extraction status, and #191 for mining the readable
ones before considering any OCR.

### Things that are easy to get wrong

- **`main.py` is huge and concurrently edited.** Re-read the region immediately before
  editing; never edit by remembered line number.
- **`events.py` retention is 30 days.** Anything needing longer history must persist its
  own aggregates — raw events are gone after 30 days.
- **`storage.py` cannot list by prefix.** Any "scan all blobs" design needs an explicit
  index blob instead.
- **The GCS bucket is in the US; Cloud Run runs in `asia-south1`. This is deliberate and
  cannot be changed** — the GCS free tier is only available in US regions, and this project
  stays on free tiers. So every bucket round-trip pays cross-continent latency.

  **Never do per-request GCS reads on a hot path.** This is not a style preference: issue
  #144 was a ~13-second homepage caused by ~30 sequential bucket round-trips per render.
  The fix took it to under 1s by removing them (32 GCS ops → 0), not by moving anything.
  Cache in-process (`hot_cache`, TTL + stale-while-revalidate), memoise, and batch or
  parallelise anything unavoidable.

  Do not propose relocating the bucket — it has been considered and the free tier rules
  it out.
- **Festival dates reach users through email and the rashifal LLM prompt**, not through a
  web page — plus `/festivals` and the `/panchang` callout, which now render it.
  `festival_for_date()` returns only the FIRST festival on a date; use
  `festivals_for_date()` when a shared date must show all of them (Diwali and
  Narak Chaturdashi both fall on 2026-11-08).
- **`/learn` already contains per-festival and per-muhurat articles** (e.g.
  `karva-chauth-2026.html`, `diwali-muhurat-2026.html`). Do not create a parallel page type
  for the same queries — it cannibalizes pages that already rank. New long-form content
  goes through the `/learn` pattern.

---

## Running locally

```bash
uv sync
uv run astro-ai      # http://127.0.0.1:8000, auto-reloads
```

Requires `.env` (copy `.env.example`). `OPENAI_API_KEY` is the only hard requirement;
`ASTRO_AI_API_BASE` repoints at any OpenAI-compatible provider. See README.md for the
full environment-variable table.

**There is no test suite.** `tests/` holds only `kundali-qa-fixtures.json`. So verify
changes by actually exercising them: run the dev server and hit the route, or at minimum
`python3 -c "import ast; ast.parse(open('<file>').read())"` plus an import check. Never
report a change as working on the strength of the diff alone.

---

## Content and astrological accuracy

- Astrological claims must trace to `knowledge/*.md`, citing the classical tradition rather
  than book-and-chapter references in user-facing prose.
- Match the established voice of existing `/learn` articles — read two before drafting one.
- Regional variation in festival dates and reckoning (purnimanta vs amanta, sunrise-spanning
  rules) is legitimate. State which convention a page uses rather than implying a single
  universal answer.

---

## Untracked by intention

`.local/`, `.serena/`, and `QA_LOG.md` sit untracked in the repo root. Leave them alone —
do not commit, delete, or gitignore them without asking.
