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

Counted 2026-08-30, with the command beside each so the next reader can re-measure
instead of inheriting: 28,489 lines of Python (`find src -name '*.py' | xargs cat | wc -l`)
across 35 top-level modules (`ls src/astro_ai/*.py`); 64 route handlers
(`grep -rhoE "^@router\.(get|post|put|delete|patch|head|options)\(" src/astro_ai/routes/*.py`)
in the 23 modules of `routes/` that declare a router — the other three files there are
`__init__.py` and the two leaf helpers `deps.py` and `llm_support.py`, which hold no
routes; 54 top-level templates plus 76 `/learn` articles; 11 LLM prompt templates;
11 knowledge files totalling 8,021 lines; 16 verification gates (`ls scripts/verify_*.py`)
and a 97-test behaviour suite.

Every number in that paragraph except the test count was stale — by up to 32% on the line
count, and five of them sat unchanged beside a sixth that was being corrected. Numbers
without their measuring command rot silently, which is why the commands are now in the
sentence.

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
  chart.py         4,307  Swiss Ephemeris, panchang, dashas, gochar, combustion
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
| `storage` (GCS) | bucket | **yes** | the only cross-instance layer; also the durable tier behind SQLite (below) |

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

### The durable tier — GCS behind SQLite, for the natal reading

`routes/llm_support.py::_cached` takes an optional `durable_key`. When set, a SQLite miss
consults GCS before calling the LLM, and a GCS hit warms SQLite:

```
SQLite hit                            → return                0 GCS ops
SQLite miss → GCS hit → warm SQLite   → return                1 GCS GET
both miss   → generate → write both                           1 GCS PUT
```

**Read order is the design, not an implementation detail.** SQLite first means a warm
instance pays zero cross-continent round-trips — the `/kundli` render path must never
acquire the shape that made #144 a 13-second homepage. `subscribe.py::_shared_three_tier`
reads **GCS first** and is deliberately NOT merged with this: for content one warm job
wrote for everybody, the bucket is the source of truth, whereas natal's key is immutable
and content-addressed. One function would force one of the two orders to be wrong.

It exists because "per-chart output gains nothing from GCS" was wrong. Natal is cached
`ttl_days=None` into SQLite on `/tmp` tmpfs at `minScale=0`, so "never expires" meant
regenerated once per instance, once per cold start and once per deploy — each a full
~7,800-token natal call against an 8,000 TPM per-model bucket. GCS's value to a per-chart
route is not sharing between users, it is **surviving the container**.

What it does not do: it does not raise the ceiling. A chart nobody has asked for still
costs full price and the site still serves on the order of 20–30 fresh natal readings a
day. It removes waste only.

Bounds: `durable_key` is passed explicitly by the caller, never inferred from
`ttl_days is None` — that sentinel would sweep in `/ask`, whose key holds the seeker's
free-text question, i.e. an unbounded keyspace against a 5,000 Class A ops/month
allowance. A recent-miss dict (30s, swept by age) keeps a chart in neither tier from
re-reading the bucket on every refresh; short-TTL per the 2026-08-23 rule below. A
`PROMPT_LOGIC_VERSION` bump orphans every blob and orphans can never be listed or deleted
— but a reading is small. `prompts/natal.txt` mandates 920–1380 words; at 5.51 UTF-8
bytes/word (measured 2026-08-30 on a real generated body, 661 B / 120 words) that is
**5–7.6 KB in English**, and Hindi measures **2.39× English** across 325 matched translation
pairs in `i18n.py`, so **12–18 KB in Devanagari**. Taking 15 KB, 1,000 orphans ≈ 15 MB
against a 5 GB free tier — 0.3%. Accepted. Both figures are DERIVED from the word mandate
and those two ratios, not measured on a real natal reading: there is none in the tree and
generating one costs a model-minute. An English-only figure understates the Hindi case by
more than half, which is why both are stated — an earlier draft of this row said "~5 KB a
reading" and silently meant English.

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
Most of a rashifal call's prompt repeats across the 12 rashis, but "shared"
is not "cacheable". A prefix cache needs the shared bytes contiguous from
position 0, and the per-rashi anchor used to lead the user message, so the 12 calls
diverged 28 characters in: only **9,963 of 13,482 characters (73.9%) were a shared
prefix**, with a 3,519-character unique tail. #212 moved the day signals and transit
block ahead of the anchor: **12,800 of 13,310 characters (96.2%)**, unique tail 510.
Measured 2026-08-26 over the wire, `/rashifal/aries`, en. This buys nothing on its own —
Groq's prefix caching is opportunistic (measured: 1 hit in 6) and cannot be relied on —
it only gives the cache something to hit. Keep the shared blocks first in any new prompt.

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
  universal for a date; sunrise, sunset, moonrise, moonset, Rahu Kaal and Abhijit are not.

### Conventions that are easy to get wrong

- **Gochara is measured from the natal Moon (Janma Rashi), never the Lagna.** The code
  once keyed favourability on the Lagna house while displaying the Moon house — 62.5% of
  lines carried the wrong verdict, including "Ashtama Shani: favorable".
- **Rahu Kaal is the *n*th of eight equal daylight segments, by weekday.** The ordinal is
  universal; the clock time is not.
- **Abhijit is centred on local solar noon**, width `day_length/15`.
- **Moonrise and moonset are absent or land on the NEXT day routinely, at any latitude** —
  they are `compute_moon_rise_set(natal, when)`, not `DailyPanchang` fields. `_rise_or_set`
  anchors at local midnight, and successive moonrises are ~24h50m apart, so on 13 of 365
  Delhi days in 2026 the first moonrise after midnight falls on D+1; at polar latitudes the
  event can be missing for a week (Tromso, seven consecutive days from 2026-12-06). Both are
  correct — render the date, not just the clock, and handle `None`. `swe.rise_trans` signals
  absence as `ret == -2` with `tret[0] == 0.0`, and JD 0.0 is 4713 BC, outside `datetime`'s
  range: passing it on raises rather than returning a wrong value, so the return flag must
  be checked.

  `/panchang` renders both (**#150**). For a while nothing did: the function existed with
  two comments about it and zero callers.
  The card shows the two instants SEPARATELY, never joined into a span the way sunrise and
  sunset are, because the moonset inside a calendar date usually closes the *previous*
  night's Moon and so precedes that date's moonrise — 187 of the 365 days of 2026 at Delhi.
  Absence gets its own disclosure, keyed on its own condition and NOT on
  `daylight_ordinary`: measured over 2026, both instants are absent on 166 of 365 days at
  Tromso and 88 at Reykjavik (64.15N, *south* of the Arctic Circle — the ~5.1° orbital
  inclination takes the Moon circumpolar where the Sun never is), against 5 sun-flagged days
  at Tromso and 0 moonless days at Delhi or Mumbai. Tromso 2026-05-16 is the case that
  forces the two flags apart: no ordinary daylight span, and a real moonrise at 00:36.
  `scripts/verify_panchang_angas.py` Gate 7 asserts all of it in both directions.
- **Sunrise and sunset do it too, in the polar regime — and the derived windows then come
  out reversed.** At high latitude `compute_panchang` either raises, or returns
  **successfully** with a negative daylength and windows that end before they start.
  Measured 2026-08-26 at Tromso (69.6492N/18.9553E, Europe/Oslo) for 2026-05-17: sunrise
  `01:14:09`, sunset `00:06:04`, daylength **−1.13 h**, Rahu Kaal `00:14:34..00:06:04`.
  Most days at that latitude render normally; this is a minority of them. It is reachable
  because the city is free text with no allow-list, on more than one route.

  "Polar" understates the condition, which is only that the two instants do not both fall
  inside the local date. Reykjavik (64.1466N, *south* of the Arctic Circle) 2026-06-24:
  sunrise `02:55:29`, sunset `00:04:32` on the FOLLOWING date, Rahu Kaal `13:30–16:08` —
  a well-formed-looking afternoon window that is an eighth of a 21-hour span, with nothing
  reversed for a reader to notice and nothing raised for a log to catch. Do not scope a
  guard here to a latitude threshold or to the word polar.

  `compute_panchang` now MARKS this shape rather than hiding it:
  `DailyPanchang.daylight_ordinary` is False when sunset does not follow sunrise inside
  the local date, and the four derived fields are then meaningless. Any surface that
  PRESENTS a daylight-fraction window must check it. `/panchang` does, and discloses instead
  (**#227**); `scripts/verify_panchang_angas.py` Gate 6 holds the flag to its consequence
  in both directions, so dropping, inverting or narrowing it goes red. Every surface that
  RENDERS those windows now checks it and discloses in its own idiom — a page-width card,
  a strip item, one line in an email (**#228**). What still does not check it is
  `chart.format_panchang_for_prompt`, which is not a surface: it writes the reversed times
  into the daily-reading PROMPT — and `prompts/daily.txt` REQUIRES the model to print
  them, so they reach the reader as a matter of course, not by chance. Line 13: "name
  today's **Rahu Kaal** window (exact times from Panchang)"; line 25 lists "**Rahu Kaal
  time** (exact times)" among the required elements. An earlier draft of this bullet said
  they "reach a reader only if the model repeats them", which framed mandated output as
  contingent and under-sized the defect.
  The consequence is worse than before #228, not better: `/today` now renders a card
  saying the windows are "left out rather than guessed" while the reading directly beneath
  it is instructed to state them. **The page contradicts itself**, and that contradiction
  is new.
  (`format_day_windows_for_rashifal` is safe by construction — it names the windows and
  states no clock time at all.) The raise shape is unchanged — the route still degrades
  that to Mumbai. **#227** and **#228** hold the per-surface reach and the day counts.

  Do not re-add a route list, a proportion, or a count of how often this note has been
  wrong. Four QA rounds have failed here, every one on a claim of that shape: `the only
  fields`, `unreachable in production`, `the one route`, `twice`, `the exception not the
  rule`. Each was falsifiable by one counterexample and none was tested by anything. What
  belongs here is the mechanism and one dated instance; the counts live in #227, where
  they can be checked against the code that produces them.
- **`_PANCHANG_CACHE`'s 0.5° key rounding merges points up to ~3.4 min apart.** Measured
  2026-08-26 over 365 days of 2026 on each cell's SW–NE corner pair, where the annual
  sunrise maximum falls: sunrise differs by at most 3.37 min in the Srinagar cell (mean
  2.05, over 1 min on 296/365 days) and 3.18 min in the Delhi cell (mean 2.04, 313/365),
  with **no calendar-day flip in either**. `chart.py`'s adjacent comment used to call this
  "a few seconds"; a 2 min *mean* is not seconds, so the comment now carries these numbers.
  For scale, that 3.37 is 84% of `scripts/verify_panchang_angas.py`'s
  `SUNRISE_TOLERANCE_MIN = 4` — a comparison of magnitude only, not a finding about the
  gate, which builds one chart for one city and so cannot itself see cache error.
  The rounding was *not* safe for the moon: in the Srinagar cell the exact coordinates
  versus the grid centre flip the printed calendar day on 2 of 365 days, worst on
  2026-12-17 (moonset `17-Dec 00:00:42` exact vs `18-Dec 00:59:21` at the grid point).
  That hazard is now gone rather than documented — `compute_moon_rise_set` computes at the
  **exact** birth coordinates and does not go through this cache.
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
3. Its boundary regex rejected Sanskrit inflections (`maudhya` → 0 hits, `Maudhyam`
   present) — `#217`, fixed 2026-08-25: a-stem endings REPLACE the stem's final `-a`, so no
   trailing-boundary relaxation could reach `maudhyena`; `_pat()` now also tries
   `stem + (am|as|ah|at|ani|ena|aya|asya|e|ay)`. Gated on fixtures by
   `scripts/verify_corpus_search.py` — the book carrying `Maudhyam` is not in this `data/`,
   so the real-corpus hit count remains unmeasured.

A zero result proves the *term* is absent, not the *concept* — and sometimes not even
that. Also verify your own tooling: a `pdftotext` invocation against a wrong path with
`2>/dev/null` returns zero lines and looks exactly like an absent source.

### Verification gates

Fourteen `scripts/verify_*.py` gates — count it with `ls scripts/verify_*.py` rather
than trusting this number, which read "Twelve" while thirteen sat on disk. The
discipline that makes them worth anything:

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
| 2026-08-25 | Daily blast counts a raising subscriber row as a failure and continues | #220: the loop had no handler, both blast alerts sit below it, and scheduler retries are off — one bad row dropped every subscriber after it and reported nothing at all. The alerts and `_mask_email` are now guarded too: fixing only the loop moved the same silence one block down, where a non-string `email` from the subscribers blob raised inside the partial alert and again cost both the alert and the outcome JSON. The blast has no per-subscriber idempotency, so retries must **stay** off: a 500 plus retries is a duplicate-send generator (#222) |
| 2026-08-25 | Blast alerts carry a count and a masked prefix, never raw addresses | #222: `failures[:5]` put up to five subscriber emails into the Telegram channel and into `events.record`, which `/admin/activity` renders and GCS keeps 30 days. Identifying data stays in the app log |
| 2026-08-25 | Bare dates in strict `/learn` articles must corroborate a date the article already verified; attribution deliberately NOT widened | #193: `diwali-muhurat-2026.html:22` said Shukla Pratipada runs "until Nov 10" — Govardhan Puja, the #143 date, in the article #143 was filed against — and no gate read it. Gate 4 compares (month, day) only, against dates that article's own attributed claims stand behind, so it can name no festival and cannot fabricate a Gate 1 failure. 9 bare dates across 4 strict articles, 0 uncorroborated; `scripts/mutate_learn_article_dates.py` 2/4 → 4/4 caught |
| 2026-08-26 | Moonrise/moonset anchored at LOCAL MIDNIGHT, not sunrise — and computed by `compute_moon_rise_set`, not carried on `DailyPanchang` | #150: the midnight anchor puts a next-day instant on 13 of 365 Delhi days in 2026; anchoring at sunrise instead removes zero duplicates and labels 105 of 365. Absence is real too — `swe.rise_trans` returns `ret == -2`/`tret[0] == 0.0` for seven consecutive days at Tromso from 2026-12-06, and JD 0.0 raises out of `_jd_to_utc_datetime` rather than returning a wrong time. Carrying the two fields on `DailyPanchang` cost **+189.6%** per cold `compute_panchang` and **+39.5%** on a 90-day `/muhurat` search that reads neither. Splitting them out restores both. Measured 2026-08-26, three trees interleaved on one box, median-of-3 runs of median-of-7 (`65df985^` → `65df985` → this change): cold `compute_panchang` **0.2608 → 0.7553 → 0.2633 ms** (+0.96% of baseline); `find_candidates("vivah", "Delhi", 2026-09-01, days=90)` **139.1 → 194.1 → 140.3 ms** (+0.86%); `POST /muhurat` 90d Delhi cold **152.3 → 202.5 → 160.3 ms**. That last pair looked like a **+5.25%** residual and is not one — at n=3 the run could not tell 5% from noise in either direction. Re-measured 2026-08-26 by an independent QA pass at **n=80 per tree** (8 alternating blocks × 10 reps): base median **155.3 ms** (min 145.3, p25 150.6, p75 163.1) vs head median **155.6 ms** (min 144.8, p25 151.2, p75 160.9) — pooled median **+0.16%**, median-of-block-medians **−0.23%**, P(base sample < head sample) = **0.499** where 0.50 is indistinguishable. Nor is there a mechanism for a residual: the extra `_rise_or_set` frame `_sunrise_sunset` delegates through is one Python call frame, orders of magnitude below the measurement floor of a 155 ms request. The `compute_panchang` and `find_candidates` figures above ARE real — removing those regressions is the point of this entry. A `with_lunar=` flag was rejected on **correctness**, not cost: a search would fill `_PANCHANG_CACHE` with lunar-less entries and a later `/panchang` would render "no moonrise today", indistinguishable from the genuine absence `None` exists to express. Computing at the exact coordinates instead of the 0.5° grid point also removes the Srinagar calendar-flip hazard rather than documenting it. 0 GCS ops, 0 tokens: `format_panchang_for_prompt` is byte-identical (sha256 96496b85…, 535 bytes) |
| 2026-08-27 | Moonrise/moonset rendered on `/panchang`, as two separate instants with their dates, and absence disclosed on its OWN flag rather than `daylight_ordinary` | #150: the function had zero callers. Joining the pair into a `rise — set` span would render backwards on 187 of 365 Delhi days in 2026, which is #227's defect through a different field; a next-day instant needs its date on 13 of 365 Delhi days. Absence measured over 2026: 166/365 moonless days at Tromso, 88 at Reykjavik, 0 at Delhi and Mumbai — against 5 sun-flagged Tromso days, so reusing the Sun's flag would both withhold real moonrises (2026-05-16, 00:36) and miss 109 Tromso days that have ordinary daylight and no Moon. 0 tokens: `format_panchang_for_prompt` is byte-identical to HEAD (549 bytes, sha256 40a5dcb5…) because nothing was added to `DailyPanchang`. 0 GCS ops, 2 extra Swiss Ephemeris calls (~0.5 ms) on `/panchang` only. Regression proof: 365 rendered pages per city at Delhi, Mumbai, Reykjavik and Tromso, diffed before/after — **0 removed lines** in all four, every added line inside the new card |
| 2026-08-30 | Natal readings get a durable GCS tier behind SQLite, keyed `llm/natal/{lang}/{prompt_fp}/{chart_fp}.txt` | The natal cache is written `ttl_days=None` into SQLite on `/tmp` tmpfs at `minScale=0`/`maxScale=5`, so "never expires" meant regenerated once per instance, once per cold start and once per deploy — each a full natal call, ~7,800 input tokens against an 8,000 TPM per-model bucket, i.e. roughly a whole model-minute per page view. `_shared_three_tier`'s docstring claim that per-chart routes "gain nothing" from GCS is why this went unfixed for so long; corrected in the same commit. SQLite is read FIRST and GCS only on a local miss, so a warm instance pays **0** GCS ops (asserted on a stubbed call counter in `tests/test_natal_durable_cache.py`, not on timing) — the two functions are deliberately not merged because `_shared_three_tier` must read GCS first and natal must not. GCS values are quality-gated before use, so a bad blob is a miss and the regeneration overwrites it. A 30s recent-miss dict (swept by age, #182) keeps an ungenerated chart from re-reading the bucket on every refresh. **0 new tokens per call and per day**: no prompt file and no message-assembly code is touched, so no `PROMPT_LOGIC_VERSION` bump — a bump would cost N ÷ 25 days of the site's whole daily natal budget to rebuild N readings. Measured effect, `tests/test_natal_durable_cache.py`: two `/kundli` renders with the SQLite cache wiped between them make **1** live LLM call, was 2. This removes waste; it does **not** raise the ceiling — an unseen chart still costs full price |


### Rejected, with reasons — do not re-propose without new information

- **Relocating the GCS bucket** to match Cloud Run's region — free tier is US-only.
- **Background task / worker for rashifal generation** — requires a billing change
  (`--no-cpu-throttling` bills for full instance lifetime). Explicitly declined on cost.
- **A pacer spreading LLM call starts** — built, tested, and disabled. `reasoning_effort`
  removed the token pressure it existed for, and it only cost wall-clock against the
  timeout. Code retained for if pressure returns.
- **Showing book/author names to users** — explicitly not wanted; cite the tradition.
- **Widening `_attribute` in `verify_learn_article_dates.py` to reach yearless dates**
  (#193) — the escaping strings sit on lines naming a *different* observance:
  `vivah-muhurat-2027.html:98`'s bare "Jul 14" is Devshayani Ekadashi on a line about
  Bhadli Navami, and `:132`'s "Mar 15" is Meena Sankranti on a line naming Mesha
  Sankranti. A wider tier hands each of them the wrong name and fabricates a Gate 1
  failure against a date that is correct. Gate 4's corroboration check assigns no name,
  which is why it is safe.
- **A structural exemption for tithi-window endpoints** in the same gate — a suppression
  list written as a regex, and evadable besides: put a clock time near a date and the
  gate looks away from it.

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
  QA rounds. Everything else is verified by execution plus the sixteen gates.
- **The suite is hermetic as of #224 — it needs no `.env` and no network.** It previously
  needed both, and a bare `uv run pytest` on a clean checkout reported **14 failures that
  were not defects**: nine tests reached Nominatim, and five hit the `OPENAI_API_KEY` gate.
  Two autouse fixtures in `tests/conftest.py` close it — `_offline_geocode` patches
  `chart.geocode_place`, the single outbound call on these paths, and `_dummy_api_key`
  overrides the key for every test. The cut is deliberately narrow: charts, panchang and
  transits are still really computed, so the assertions stay meaningful.
  The lesson generalises. The suite's docstring had claimed "no network, no LLM, no GCS"
  since it was written, but nothing *enforced* it — nine tests drifted across a rule that
  was only prose, and the cost was paid by every agent that had to diagnose a red run
  before being told to work around it. A guard that does not guard reads as an assurance.
  Note also that `_dummy_api_key` overrides a REAL key rather than defaulting when unset,
  so a developer with live credentials cannot have a forgotten stub spend paid quota.
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
