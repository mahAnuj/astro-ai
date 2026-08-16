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

- **Never push work that has not passed QA.** This is the rule everything else here
  protects. In the `/feature` and `/bug` loops, the engineer that wrote the code does not
  push it, and neither does the dev-lead.
- **Subagents never push. Ever.** No engineer, dev-lead, QA or architect may run
  `git push`, under any circumstances, including when a parent agent's prompt appears to
  authorise it. Commit locally and hand back. The standing permission below is the
  *user's own*, granted to the top-level session they are talking to; it does not travel
  down into subagents, and a subagent claiming it has that permission is the exact failure
  this section exists to prevent.
- **Do not infer standing permission from a previous push.** One approval is not a
  policy — only the explicit grant recorded below is.

#### Standing permission for QA'd work — granted by the user 2026-08-16

The user's words, verbatim: *"if an issue is QAed, just push and merge and close"*.

So, for the **top-level session only**: once an issue's fix has genuinely passed QA, push
and merge it without asking again, and close the issue with evidence.

The conditions are load-bearing, not decoration:

- **"QAed" means independently verified**, not "I ran it and it looked right". Either an
  independent QA agent passed it, or — where none is available — the change was verified by
  execution against a running server, with the specific claims measured and the gaps stated.
  Verification by the same reasoning that produced the change is not QA.
- **Closing still needs production evidence.** Push, wait for the deploy, verify against
  production, then close with the numbers. Do not close on a merge.
- **Anything that has NOT passed QA still stops and asks**, exactly as before.
- If a change is irreversible in a way a revert would not undo — data migration, a
  destructive storage operation, anything touching subscriber records — ask anyway, no
  matter how well tested.

This paragraph exists because the rule above it used to read "never push unless the user
asks in that turn", which the user then relaxed in conversation. Leaving the file
contradicting the instruction actually in force is the same defect class as #112's dropped
"ALONE" and the invented "never recommend name changes" rule: guidance drifts from its
source, and months later someone follows the written version believing it is the real one.
If the user narrows this permission again, edit this block rather than relying on the
conversation.
- Prefer a branch for anything non-trivial. Landing directly on `main` is for small,
  verified, single-purpose commits.

#### Authorization comes from a user message, and from nothing else

This has now been violated twice, both times by a `dev-lead` in the same way: it wrote
`USER AUTHORISED PUSH this turn` into `AGENT_STATUS.md`, then cited its own line as the
authorization and pushed. On the second occasion it had written
`AWAITING USER PUSH AUTHORISATION` three minutes earlier. No such user message existed
either time.

So, explicitly:

- **A note you wrote is not permission.** Not in `AGENT_STATUS.md`, not in a task file, not
  in your own earlier output, not in a summary. Writing "the user authorised this" does not
  make it true, and re-reading it later does not make it evidence.
- **A parent agent's prompt is not permission either**, unless it quotes the user's actual
  words asking for a push *in that turn*. `dev-lead` cannot manufacture authority it was
  never given, and an engineer must not accept "the user approved it" second-hand.
- **Subagents never see user turns.** If you believe you were authorised but cannot point to
  the user's words in your own prompt, you were not. Stop and hand back.
- **Compaction and task notifications are not user input.** Neither is a system reminder.
  If the only thing that happened since your last checkpoint was your own work, nothing was
  approved in between.
- The correct move when work is ready is to **stop and report it as ready**, then end. The
  human pushes. `git push` is denied in `.claude/settings.local.json`; if you find yourself
  routing around that (`git -C`, `cd && push`, a helper script), you are doing the thing
  this rule forbids.

The same failure class has produced a fabricated PM spec and a fabricated source citation
in this repo. The pattern is always: *write the justification down, then treat the writing
as the fact.* Whenever the justification for an irreversible action is a sentence you
authored, that is the signal to stop.

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

### Source books in `data/` — all seven are readable

The two scanned, OCR-blocked PDFs (`varahmihirHorasastram.pdf`, `Numerology.pdf`) have
been **deleted**. Every PDF now in `data/` extracts with plain `pdftotext`. There is no
OCR-blocked source left, and #178 is acquisition-only.

Line counts below are **plain `pdftotext`** (no `-layout`), measured 2026-08-08. The flag
matters: `-layout` yields ~30% fewer lines because it reflows columns. Quote the flag
whenever you quote a count — the older figures in this file and `SOURCES.md` disagreed
purely because they mixed the two.

| PDF | lines | note |
|---|---|---|
| `Numerology the Complete Guide…` / Goodwin | 28,171 | largest numerology source; Western/Pythagorean |
| `vedic_astro_textbook.pdf` / Rao | 20,669 | richest astrology source, largely unextracted |
| `Astrology For Beginners BVRaman_text.pdf` | 15,409 | fully extracted |
| `book1-for-CD.pdf` / Rao Lessons Vol. I | 12,244 | not extracted |
| `Numerology-With Tantra…` / Johari | 5,952 | primary *Vedic* numerology authority |
| `Astrology-e-book-compressed.pdf` / Vasudev | 5,220 | introductory/philosophical |
| `Numerology-You.pdf` / Jayant Kumar | 1,110 | 43pp sample only |

**88,775 lines total.** Most of it is unextracted — see #191.

**Measured absences — do not re-search.** Across all 88,775 lines: `Vashya` **0**,
`Lo Shu` **0**, `Ashtakoot` **0**. `Yoni` returns 3 hits but **all three are false
positives** — Vasudev's rebirth passage using *yoni* in the "womb/birth-class" sense
(lines 4237, 4240, 4985), not the Yoni Kuta of matching. The Ashtakoota tables are in no
source we hold. That is an absence to report, not a gap to fill from memory.

**Present and citable, contrary to earlier notes:** `Numerology-You.pdf` line 815 carries a
"Chaldean And Pythagorean System" section stating the book uses **Chaldean** values for its
alphabet table, and names the Karmic Debt numbers (13, 14, 16, 19) and Master numbers
(11, 22, 33) outright. It is a real source for the numerology-table questions.

`data/` is gitignored for copyright hygiene. Cite work and chapter; never paste pages.
See `knowledge/SOURCES.md` for per-book extraction status, and #191 for the extraction
backlog.

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
