# ARCHITECTURE.md — how Shubh Bhagya is built, and why

**Read this before designing anything. It exists to stop you re-deriving decisions that
were already made, already measured, and already paid for.**

This is a *reference* document, not a rules document. `CLAUDE.md` holds the working
agreements you must follow; this holds the shape of the system and the reasoning behind
it. Deliberately NOT merged into `CLAUDE.md`: that file is loaded into every session's
context, including trivial ones, and it is already ~4,400 tokens. Doubling it to carry
architecture would raise the cost of every task in order to help a few — the opposite of
what this document is for. Read this one on demand.

**How to use it.** Skim §1–§4 for orientation. Jump to the section matching your task.
§10 is the decision log — check it before proposing a change, because a surprising number
of "obvious improvements" are already there with a measurement explaining why not.

---

## 1. What the system is

Vedic astrology web app at **shubhagya.com**. FastAPI + Jinja2, Python ≥3.12, `uv`.
Server-rendered HTML with HTMX for partial updates. No SPA, no build step for JS.

Roughly 21,600 lines of Python across 30 modules, 68 routes in 25 route modules,
54 top-level templates plus 76 `/learn` articles, 11 LLM prompt templates, 11 knowledge
files (~6,200 lines), 13 verification gates and a 24-test behaviour suite.

Two things drive nearly every design decision in here, and they are worth internalising
before you read anything else:

1. **Everything runs on free tiers.** Not as a temporary measure — as a constraint.
2. **There is no staging, and test coverage is narrow.** A push to `main` deploys to
   production. Production is the first place code runs. The behaviour suite (§8) covers
   request paths only; most of the app has no automated coverage at all.

---

## 2. The deploy path

```
git push main
   └─> Cloud Build trigger (configured GCP-side, NOT in this repo)
        └─> Cloud Run service `bhagya`, region asia-south1
             └─> Firebase Hosting rewrite, shubhagya.com
```

**Nothing in the working tree reveals this.** There is no `.github/workflows/` and no
`cloudbuild.yaml`. Do not conclude "no CI" from their absence — that conclusion has been
drawn before and it is wrong.

### Cloud Run configuration (verified 2026-08-23)

| setting | value | why |
|---|---|---|
| region | `asia-south1` | users are in India |
| `timeoutSeconds` | 300 | raised from 60 during the 2026-08 email outage |
| `containerConcurrency` | 80 | |
| `minScale` | 0 | free tier; cold starts are accepted |
| `maxScale` | 5 | cost ceiling |
| cpu / memory | 1 / 512Mi | |
| env vars | 15, **all plain values** | none in Secret Manager — see §11 |

### The 60-second ceiling that is not Cloud Run's

**Firebase Hosting caps a rewrite to Cloud Run at ~60 seconds.** Cloud Run's
`timeoutSeconds` does not override it. Anything reached through `shubhagya.com` dies at
60s no matter what Cloud Run is configured to allow.

This cost 21 days of broken daily email in August 2026 and was misdiagnosed twice —
first as Cloud Run's timeout (true at the time, then fixed and the failure persisted),
then as a mysterious retry. Cloud Scheduler logged `INTERNAL` at ~60–70s while Cloud Run
logged `200` at 141.9s for the same request.

**Consequence:** any scheduled job that can exceed 60 seconds must target the Cloud Run
URL directly (`https://bhagya-ht3mu6f2ka-el.a.run.app`), not `shubhagya.com`. All three
scheduler jobs do this as of 2026-08-23.

### Scheduled jobs (3 of 3 free-tier slots used)

| job | time (IST) | target |
|---|---|---|
| `warm-rashifal-en` | 06:30 | `/admin/warm-rashifal?lang=en` |
| `warm-rashifal-hi` | 06:45 | `/admin/warm-rashifal?lang=hi` |
| `daily-rashifal` | 07:00 | `/admin/send-daily-rashifal` |

Retries are **off** deliberately — retries were double-generating readings and doubling
LLM spend. There is no fourth free slot, so new scheduled work must replace something or
move to Cloud Monitoring.

---

## 3. Module map

```
src/astro_ai/
  chart.py         4,212  Swiss Ephemeris, panchang, dashas, gochar, combustion
  learn_registry.py 3,107  /learn article metadata
  numerology.py    1,844  Chaldean + Lo Shu calculators
  festival_registry.py 1,509
  muhurat.py       1,444  electional scoring; shares angas with panchang
  llm.py           1,068  prompt assembly, rashifal fan-out
  matching.py      1,056  Ashtakoota 36-guna
  i18n.py            967  en/hi, symmetric key sets (enforced)
  providers.py       704  provider chain, quality gates, retry policy
  routes/            25 modules, 68 routes
  knowledge/*.md     classical source material — the authority for astrological claims
  prompts/*.txt      11 LLM prompt templates
```

`chart.py` is huge and concurrently edited. **Re-read the region immediately before
editing; never edit by remembered line number.**

---

## 4. Caching — five layers, and what each cannot do

This is the most misunderstood part of the system. Layers, outermost first:

| layer | scope | survives | used for |
|---|---|---|---|
| `hot_cache` | in-process, TTL + stale-while-revalidate | no | homepage trust bar |
| `lru_cache` (stdlib) | in-process, per-function | no | geocode, lunar dates, sankranti |
| `_PANCHANG_CACHE`, `_PANCHANG_STRIP_CACHE` | in-process dicts | no | panchang by (date, coarse lat/lon) and by (date, city) |
| `daily_cache` | **file** on the instance | no | per-rashi readings, keyed `(namespace, slug-lang, date)` |
| `cache` (SQLite) | `/tmp/bhagya.db`, **tmpfs** | no | per-chart LLM output, keyed by fingerprint |
| `storage` (GCS) | bucket | **yes** | the only cross-instance layer |

**Every layer except GCS is per-instance and dies with the container.** `minScale=0`
means containers come and go constantly. If two requests must share a result, GCS is the
only thing that gets them there — this is why `/admin/warm-rashifal` works at all.

### Things that will bite you

- **`storage.py` cannot list by prefix.** Any "scan all blobs" design needs an explicit
  index blob. There is no way around this.
- **`events.py` retention is 30 days.** Anything needing longer history must persist its
  own aggregates.
- **The GCS bucket is in the US; Cloud Run is in `asia-south1`.** Deliberate and
  unchangeable: the GCS free tier is US-only. Every bucket round-trip pays
  cross-continent latency. **Do not propose relocating the bucket** — it has been
  considered and the free tier rules it out.
- **Never do per-request GCS reads on a hot path.** Issue #144 was a ~13-second homepage
  caused by ~30 sequential bucket round-trips per render. Fixed by removing them
  (32 GCS ops → 0), not by moving anything. The homepage is now ~1ms warm and there is a
  gate (`scripts/perf_homepage.py`) that measures it.

### Cache keying for LLM output

- `fingerprint_chart` — sha256 of `"date|time|place"`. No geocode, so it is stable.
- `fingerprint_prompt` — hashes the prompt **file** plus `PROMPT_LOGIC_VERSION`.
- **`PROMPT_LOGIC_VERSION` is the manual lever.** The file hash cannot see changes to the
  Python that *assembles* the user message. Bump it whenever assembly logic changes.
  Currently `v3`.

---

## 5. LLM layer

### Provider chain

`BHAGYA_LLM_PROVIDERS` is an ordered, comma-separated chain; each entry maps to a
`ProviderConfig`. Order is shuffled per request by default (load balancing), and the
chain falls through on failure.

Currently **`groq120,groq20`** — both `openai/gpt-oss-*`.

**`groq_qwen` is deliberately excluded.** `qwen3.6-27b` rejects `reasoning_effort` with a
400, so it is the one model that cannot be bounded; unbounded it reasons until it hits
its completion limit, gets truncated mid-`<think>`, and the envelope stripper cleans it
to zero visible characters — a ~40s call returning nothing. Measured: the full
two-language rashifal job took **399s** with qwen in the chain and **213s** without.

**Groq quotas are keyed per model**, so listing several distinct Groq *models*
multiplies effective throughput on one API key. Listing `groq` and `groq120` does not —
they resolve to the same model and share one bucket while looking like extra capacity.

### Two hard-won rules

1. **`reasoning_effort="low"`** cut completion tokens ~85% (gpt-oss-120b: 3,072 → ~302)
   and *increased* visible output. Capability is probed at runtime — a model that 400s on
   the parameter is remembered and retried without it. Hardcoded model lists go stale;
   two chain entries pointed at decommissioned models for days.
2. **An empty completion is an error, not an answer.** `_call_one` raises
   `EmptyCompletion` rather than returning `""`. Before this, a reasoning-only response
   was indistinguishable from success and cached blank for the day.

### Prompt architecture

`prompts/*.txt` are system prompts. `ask.txt` has three **overlays** appended for
context-specific behaviour (`ask_matching`, `ask_matching_third_party`, `ask_numerology`)
rather than being duplicated.

The user message is assembled in Python — chart data, transits, panchang, day signals.
About **97.6% of a rashifal call's prompt is byte-identical across the 12 rashis**;
Groq's prefix caching is opportunistic (measured: 1 hit in 6), so it cannot be relied on.

### Voice rules that are not negotiable

- **No book-and-chapter citations in user-facing prose.** Cite the tradition. Provenance
  belongs in code comments and `knowledge/*.md` where it can be checked. (`ask.txt` bans
  it outright; `#200` tracks a numerology page that still violates it.)
- **No clock times in the shared rashifal.** It is one national text and Rahu Kaal /
  Abhijit derive from local sunrise: measured spread across Indian cities is **79
  minutes**, and Kolkata's and Guwahati's real Abhijit windows do not overlap Mumbai's at
  all. The reading names the windows; the page renders each reader's own computed times.
- **No markdown.** `reading_body` renders raw under `whitespace-pre-line` with no
  markdown filter, so every asterisk reaches the page. Enforced by a stripper, not only
  by the prompt — told not to, the model still emitted bold in 1 of 4 generations.
- **Answer in the language the question was asked in.**

---

## 6. Astrology calculation

- **Swiss Ephemeris** (`pyswisseph`), **sidereal**, **Lahiri ayanamsa**
  (`swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)`).
- **Whole Sign houses** (`swe.houses_ex(..., b"W", swe.FLG_SIDEREAL)`) — classical
  Parashari standard. Not Placidus.
- **Tithi, yoga and karana are taken at local sunrise**, the classical convention.
- **Location dependence is real and must be respected.** Weekday, tithi and paksha are
  universal for a date; sunrise, sunset, Rahu Kaal and Abhijit are not.

### Conventions that are easy to get wrong

- **Gochara is measured from the natal Moon (Janma Rashi), never the Lagna.** The code
  once keyed favourability on the Lagna house while displaying the Moon house — 62.5% of
  lines carried the wrong verdict, including "Ashtama Shani: favorable".
- **Rahu Kaal is the *n*th of eight equal daylight segments, by weekday.** The ordinal is
  universal; the clock time is not.
- **Abhijit is centred on local solar noon**, width `day_length/15`.
- **Combustion orbs are per-planet, and Mercury/Venus tighten by exactly one degree when
  retrograde** (14→13, 10→9). A flat 8° orb under-reported on 30% of charts. The
  retrograde values were invented at 10 and 8 before being sourced properly.
- **North vs South Indian traditions must never be blended.** Muhurta Chintamani is the
  North Indian source (36-guna Ashtakoota); B.V. Raman's *Muhurtha* is South Indian
  (12 poruthams). Koota *definitions* largely overlap; the point *weights* do not.

---

## 7. Numerology

Two systems, kept separate and both labelled honestly on the page as non-Vedic:

- **Chaldean** letter table — the site's only letter table. A Pythagorean mode existed
  and was removed for sourcing reasons, not popularity: across all books in `data/`,
  "Pythagorean" appears only as passing contrast mentions and the table appears in none.
- **Lo Shu grid** — Chinese, different provenance entirely.

**Reduction policy is declared at every call site.** `_reduce()`'s `preserve_masters`
parameter is keyword-only with **no default**, forcing each caller to state its own
policy. Master numbers (11/22/33) are kept on Life Path and name-derived numbers and
dropped on Psychic and Personal Year — the first is a deliberate product call recorded as
a decision, not a reading of a source.

---

## 8. Accuracy and sourcing discipline

**Astrological claims must trace to `knowledge/*.md`, and through it to a book in
`data/`.** This is not ceremony — this repo has shipped fabricated citations, invented
numeric values, and 9 of 17 wrong festival dates under a header claiming a provenance it
did not have.

### The recurring failure pattern

> Write the justification down, then treat the writing as the fact.

It has produced a fabricated PM spec, a fabricated source citation, a self-authorised
push, and a combustion orb invented and then defended in a comment asserting it was
classical — written *before* any source for it existed in the repo. **Whenever the
justification for a claim is a sentence you authored, that is the signal to stop.**

### Searching the corpus

Use `scripts/corpus_search.py`, not grep — it expands transliterations, excludes
non-book directories, and its `--absent` mode makes "unsourced" checkable.

**But it has produced false negatives by three distinct mechanisms**, all found the hard
way:

1. The corpus changed after a "do not re-search" note was written.
2. OCR split an entry across columns (`Rahu Kalam` reported 0 hits while present on p.199).
3. Its boundary regex rejects Sanskrit inflections (`maudhya` → 0 hits, `Maudhyam` present)
   — `#217`.

A zero result proves the *term* is absent, not the *concept* — and sometimes not even
that. Also verify your own tooling: a `pdftotext` invocation against a wrong path with
`2>/dev/null` returns zero lines and looks exactly like an absent source.

### Verification gates

Twelve `scripts/verify_*.py` gates. The discipline that makes them worth anything:

**Prove a gate can fail before trusting that it passes.** For the behaviour suite this
is automated: `scripts/mutate_behaviour_suite.py` restores each original defect and
asserts the suite goes red (currently 8/8). For everything else, do it by hand. Mutate the thing it guards,
confirm it turns red with a specific message, restore. A gate that has never failed is
not evidence. Several gates here were written with bugs — an optional regex group that
matched empty and reported a false failure, an unscoped row match that read 44 tables
instead of one — and were only caught by mutation-testing them.

---

## 9. Issue and deploy discipline

Two stages, and they must not be merged:

1. **Fix lands locally** → comment on the issue with the SHA, what changed, gate output,
   and anything deliberately left undone. **Do not close.**
2. **Deployed and verified against production** → close with that evidence.

A closing comment must let someone else check you: the commit, what was verified and how,
and the numbers. Partial work does not close.

**QA runs by default before every push** — an independent agent, not self-review.
Verification by the same reasoning that produced the change is not QA. This is not
optional and does not need to be requested; it exists because three consecutive rounds of
self-reviewed "fixes" in one session each introduced new HIGH-severity defects, and QA is
the only reason none shipped.

---

## 10. Decision log

Dated, with the evidence. **Check here before proposing a change.**

| date | decision | why, measured |
|---|---|---|
| — | GCS bucket stays in the US | free tier is US-only; relocation considered and rejected |
| — | Whole Sign houses | classical Parashari standard |
| — | No Pythagorean numerology mode | table appears in none of the books in `data/` |
| 2026-07 | Homepage does zero GCS reads | #144: 32 ops → 0, ~13s → <1s |
| 2026-08-16 | Standing permission to push QA'd work | user's words; conditions are load-bearing |
| 2026-08-21 | `reasoning_effort="low"` on all capable models | 3,072 → ~302 completion tokens, *more* visible output |
| 2026-08-21 | Empty completion raises rather than returning `""` | a blank reading was cached for a full day |
| 2026-08-22 | Rashifal blast split into warm + send | 399s single request → 83s + 130s + 0.02s |
| 2026-08-22 | `groq_qwen` dropped from the chain | unboundable; 399s vs 213s |
| 2026-08-22 | Shared reading never states a clock time | 79-min national spread; two cities' windows do not overlap |
| 2026-08-22 | Gochar favourability keyed from the Moon | 62.5% of lines had the wrong verdict |
| 2026-08-22 | Gochar keeps Raman's benefic/malefic split; no "neutral" band | Raman classifies all twelve; a neutral band would re-invent the category that caused the bug. Framing fixed instead — the panel states the base rate |
| 2026-08-23 | Scheduler targets Cloud Run directly | Firebase Hosting's 60s rewrite cap |
| 2026-08-23 | Scheduler retries off | retries double-generated and doubled LLM spend |
| 2026-08-23 | Retrograde combustion = exactly one degree less | Raman *Muhurtha* p.197 footnote; 10/8 were invented |
| 2026-08-23 | Negative caches are short-TTL, not permanent or absent | caching a failure all day pins a reader to the wrong city; not caching it costs the full timeout every request |
| 2026-08-31 | `og:image` is a generated 1200x630 PNG, never SVG | og:image was a 512x512 icon and all 76 learn articles pointed at 320x320 SVG heroes; FB/LinkedIn/WhatsApp/X/Slack reject SVG outright, so every article previewed as a bare link |

### Rejected, with reasons — do not re-propose without new information

- **Relocating the GCS bucket** to match Cloud Run's region — free tier is US-only.
- **Background task / worker for rashifal generation** — requires a billing change
  (`--no-cpu-throttling` bills for full instance lifetime). Explicitly declined on cost.
- **A pacer spreading LLM call starts** — built, tested, and disabled. `reasoning_effort`
  removed the token pressure it existed for, and it only cost wall-clock against the
  timeout. Code retained for if pressure returns.
- **Showing book/author names to users** — explicitly not wanted; cite the tradition.

---

## 11. Known gaps

- **No alerting on cron failure.** A log-based metric `rashifal_cron_failures` exists but
  has **no notification channel**, so nothing notifies. This is what let 21 days of
  broken email pass unnoticed. Creating the channel needs a `gcloud alpha monitoring
  channels create` the assistant has been denied.
- **All 15 Cloud Run env vars are plain values**, including `ADMIN_PASSWORD`,
  `ASTRO_AI_COOKIE_SECRET`, `BREVO_API_KEY` and a Telegram token. None in Secret Manager.
- **Coverage is narrow.** A behaviour suite exists (`tests/`, run via `uv run pytest` or
  `scripts/verify_behaviour.py`) but covers only request-path regressions — the cache
  lifecycle, degraded pages and blast reporting where eleven defects landed across four
  QA rounds. Everything else is verified by execution plus the thirteen gates.
- **`verify_devanagari_serif`** needs Playwright, which is not installed; it fails
  identically on every tree and is not a signal.

---

## 12. Maintaining this document

**Update it in the same commit as the change it describes**, not afterwards. A decision
log that lags is worse than none — it reads as current and is not, which is the exact
drift `CLAUDE.md` warns about.

Update when you:

- make or reverse an architectural decision → §10, with the measurement
- discover a constraint that will surprise the next person → §2, §4 or §11
- change caching, the provider chain, or the deploy path → §2, §4, §5
- reject a proposal for a reason worth remembering → §10 "Rejected"
- find a new failure mode in the tooling → §8

**Every claim here should be checkable.** Prefer a number and its source over an
adjective. If you cannot verify something you are about to write, say you could not —
this document's whole value is that the next agent can trust it without re-measuring.

Numbers in this file were verified on **2026-08-23**. Re-measure rather than trusting a
figure whose date is stale — every "do not re-check this" note in this repo's history has
eventually outlived its evidence.
