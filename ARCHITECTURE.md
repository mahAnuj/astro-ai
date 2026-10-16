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

**Size, measured 2026-08-30; every row re-measured 2026-10-11 and now gated by scripts/verify_architecture_counts.py.** Every row carries the command that produced it, because the
prose version of this paragraph had six stale numbers at once — the line count was 32% low
— and five of them sat unchanged beside a sixth being corrected. Re-run the command; do not
trust the number.

| | count | command |
|---|---|---|
| Python | 32,046 lines | `find src -name '*.py' \| xargs cat \| wc -l` |
| top-level modules | 40 | `ls src/astro_ai/*.py \| wc -l` |
| route handlers | 68 | `grep -rhoE '^@router\.(get\|post\|put\|delete\|patch\|head\|options)\(' src/astro_ai/routes/*.py \| wc -l` |
| modules declaring a router | 24 | `grep -ln '^router = APIRouter' src/astro_ai/routes/*.py \| wc -l` |
| top-level templates | 57 | `ls src/astro_ai/templates/*.html \| wc -l` |
| `/learn` articles | 76 | `ls src/astro_ai/templates/learn/*.html \| wc -l` |
| LLM prompt templates | 11 | `ls src/astro_ai/prompts/*.txt \| wc -l` |
| knowledge files | 11 files, 8,021 lines | `ls src/astro_ai/knowledge/*.md \| wc -l; cat src/astro_ai/knowledge/*.md \| wc -l` |
| verification gates | 27 | `ls scripts/verify_*.py \| wc -l` |
| behaviour suite | 613 tests | `uv run pytest -p no:warnings \| grep -oE '[0-9]+ passed'` |

`routes/` holds 27 files; the three that declare no router are `__init__.py` and the leaf
helpers `deps.py` and `llm_support.py`. Counting files rather than routers is what makes
"route modules" read 26 — say which you mean.

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

**Nothing in the working tree reveals this.** `.github/workflows/` exists (PR gates, the
production check, the agent loops) but none of it deploys; the trigger is not in the tree, and
there is no `cloudbuild.yaml`. Do not conclude "no CI" from their absence — that conclusion has
been drawn before and it is wrong.

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

Line counts re-measured 2026-10-11 with `wc -l src/astro_ai/*.py | sort -rn`; four of the
ten below were stale on the 2026-08-30 pass, so re-run it rather than citing these.

```
src/astro_ai/
  chart.py         4,535  Swiss Ephemeris, panchang, dashas, gochar, combustion
  learn_registry.py 3,107  /learn article metadata
  numerology.py    1,910  Chaldean + Lo Shu calculators
  festival_registry.py 1,509
  muhurat.py       1,475  electional scoring; shares angas with panchang
  llm.py           1,224  prompt assembly, rashifal fan-out
  rashifal_derive.py 144  /rashifal/{rashi} reading cut from the cached combined text (#268)
  matching.py      1,056  Ashtakoota 36-guna
  i18n.py          1,220  en/hi, symmetric key sets — enforced by
                        tests/test_i18n_symmetry.py (added 2026-10-05). The
                        word "enforced" sat here for months with nothing behind
                        it: translate() falls back to English, so a missing Hindi
                        key rendered ENGLISH on a Hindi page, silently (#124 QA)
  providers.py       918  provider chain, quality gates, retry policy
  identity.py         65  keyed HMAC identity hash for events and alerts, from a subkey of
                        ASTRO_AI_COOKIE_SECRET (#255); unlike chart.fingerprint_chart it is a secret
  notify.py          377  Telegram alerts — diagnostics only for kundli/matching/dosha/numerology (#255)
  routes/            27 files — 24 declare a router, 67 handlers (see §1)
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
  Event rows hold a keyed `identity_key` and a coarse `age_band` / `city`, never raw birth
  fields (#255); events written before that change still hold raw fields until they age out.
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
  It is an **unkeyed fingerprint, not a secret**: the input space is small and it is a GCS
  path component. Never put it in the events log or a Telegram alert; `identity.identity_key`
  (keyed HMAC, #255) is the one that may leave the app.
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

**A prompt has a size budget, and it is small.** Groq's free tier is 8,000 TPM
**per model**, and it is charged against the whole request — so the system prompt,
the assembled chart data and Groq's own accounting all come out of one 8,000-token
allowance. `natal.txt` reached 18,095 B (4,332 tok, 54% of the request) and took
`/kundli` down with a 413; see the 2026-09-05 rows in the decision log. Two things
follow for any prompt change:

- **Measure it, do not estimate it.** `scripts/measure_natal_request.py` assembles the
  real request for the eight golden charts and counts it with tiktoken.
  `scripts/verify_natal_prompt.py` is the cheap ratchet in the `verify_*` sweep.
- **The natal path degrades instead of failing.** `llm._shed_to_fit` drops optional
  blocks in a declared order when a request will not fit. If you add a block to the
  natal user message, give it a shed rank — an unranked block defaults to rank 0,
  "never shed", which is the right default only for something the page also renders.

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

Twenty-seven `scripts/verify_*.py` gates — count it with `ls scripts/verify_*.py` rather
than trusting this number, which read "Twelve" while thirteen sat on disk and then
"Fourteen" while sixteen did. Twice now the warning has outlived the number it warns
about, inside its own sentence. The discipline that makes them worth anything:

**Prove a gate can fail before trusting that it passes.** For the behaviour suite this
is automated: `scripts/mutate_behaviour_suite.py` restores each original defect and
asserts the suite goes red (currently 23/23, with a CONTROL row that MUST report missed
— a caught control means the sandbox was already red and every verdict in the run is
void). For everything else, do it by hand. Mutate the thing it guards,
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
| 2026-09-05 | **`natal.txt` compressed 18,095 B → 13,135 B, and the natal request now has a pre-flight size guard** | `/kundli` was dead in production with a Groq **413 — "Limit 8000, Requested 8562"**. A size failure, not a rate failure: a request bigger than the whole per-minute budget cannot succeed at any traffic level, and `groq120`/`groq20` share the 8,000 TPM cap, so the chain's fallback re-sent the identical bytes and got the identical 413. Measured with tiktoken `o200k_base` over the eight golden charts (`scripts/measure_natal_request.py`, which is the first thing in this repo to read `tests/kundali-qa-fixtures.json`): the old prompt was **4,332 tok — 54% of the request**, and the largest fixture assembled to **8,019 tok, already over the ceiling before Groq adds its own accounting**. That is the outage reproduced from a fixture, not inferred. Compression removed redundancy and no rules, and saves **1,221 tok on every natal call** (4,332 → 3,111, measured with tiktoken o200k_base). It read 1,250 for one commit: that was correct for the 13,029 B intermediate, and the follow-up that grew the prompt to 13,124 B updated the byte and worst-case figures on this very line while leaving the saving — the exact drift this log exists to prevent, caught by QA rather than by any gate. One correction to how that was first written up, because the count matters: the same three prohibitions ("no separate section", "do not list the placements", "do not name the technique") were restated by **two** of the six conditional-block handlers, not six — only D-9 and D-10 ever carried all three. So folding them into one umbrella is deduplication for those two and a **new, broader constraint** for the other four, which is a different thing and was briefly a self-contradiction: an umbrella reading "never list the placements it contains" sat over a block called `--- HOUSE LORD PLACEMENTS ---` whose own bullet requires conveying exactly those placements. The umbrella is now scoped — "treat a block as a LENS, never as a heading" governs all of them; the placement and technique-naming bans apply to the two DIVISIONAL blocks only. Found by QA, not by the gate, which anchors on the rule's words and cannot see what the rule is scoped to. Worst case is now **6,798 tok** (en) / **6,930** (hi), leaving ~1,200 of headroom. `scripts/verify_natal_prompt.py` holds the 45 rules and the byte budget; it was written BEFORE the compression, against the pre-compression file, so the rule set was captured before anything moved |
| 2026-09-05 | **Optional prompt blocks shed in a declared order rather than the request 413ing** | Compression alone moves the cliff; the next chart with a long Manglik block and five topic summaries finds it again. `llm._shed_to_fit` drops, worst-first: topic summaries (trimmed ENTRY BY ENTRY first — dropping all five to save fifty tokens is a bad trade), then aspects, nakshatras, D-10, D-9. **House lords, planet dignity, Manglik detail and yogas are never shed**: the last two are rendered as panels on the same page, so dropping them from the prompt makes the prose disagree with the panel beside it, which is the #176 failure class and worse than a thinner reading. Every shed logs at WARNING — a silent degradation is how "why is my reading shorter than my friend's" goes unexplained for months |
| 2026-09-05 | **Two measured bytes-per-token constants, not one; the safety lives in the margin** | Instruction prose runs **4.227 B/tok** (4.295 for hi), chart-data blocks **3.697–3.778**. Each constant sits just below the **floor** for its own kind, not below the average — 3.7 looks safe against a "3.70–3.78" range and is not, because `strong-gajakesari` is 3.6970 and gets under-counted by two tokens (`tests/test_natal_request_size.py` found this against tiktoken). A single 3.9 average was tried and rejected: it priced the hi system prompt 326 tok high and made the guard shed the whole 4.6 kB summaries block on 4 of 8 charts to save ~50 tokens they did not need. `cache.estimate_tokens` is deliberately NOT reused — at 4.0 it under-counts these requests by ~3%, and a guard that under-counts waves through exactly what it exists to stop. It stays as-is for the `/admin/usage` counters, which are stats, not a safety check |
| 2026-09-05 | **A 413 is `RequestTooLarge` and skips same-host providers; a 429 still falls through** | Groq sends the 413 with `"code": "rate_limit_exceeded"` and the openai SDK has no 413 subclass, so it arrived as a generic `APIStatusError` and the `except APIError` branch logged "trying next in chain" — burning a second identical call on a model with the same cap. `providers._is_request_too_large` matches on the STATUS CODE first, because classifying an ordinary 429 as unfixable would stop the chain falling through and turn a recoverable blip into a dead page. `RequestTooLarge` subclasses `AllProvidersExhausted` so the routes' existing handlers still render the degraded page. Providers on other hosts are still tried — that is what lets the paid `openai` net catch an oversized request |
| 2026-09-05 | **The completion reservation is NOT capped — investigated, not measured** | Groq counts input plus whatever completion it reserves against TPM, and `providers.py` sets no `max_completion_tokens`. Static evidence bounds it: gpt-oss-120b's default completion limit is tens of thousands of tokens, so if Groq reserved it in full against an 8,000 bucket then every natal request would have 413'd from the day the chain was configured, and they did not — so the reservation is not the dominant term. That does not make it zero, and settling it needs one live call with a `GROQ_API_KEY` these containers do not have. `scripts/measure_natal_request.py --live` sends the same request with and without a cap and prints Groq's own `x-ratelimit-*` headers. Until that runs, do not cap: the truncation failure mode it risks is the one that made `groq_qwen` unusable (a ~40s call returning zero visible characters), and `REQUEST_TOKEN_MARGIN = 1000` absorbs the unknown in the meantime |
| 2026-09-03 | The Latin BODY face swapped globally to Manrope, while `display` stays Crimson Pro and the redesign's Marcellus is applied PER-SCREEN | #242. The homepage could not render as designed without Marcellus loaded, and the font budget (`MAX_FONT_BYTES = 285,000` in `scripts/verify_devanagari_serif.py`) had ~16 KB of headroom against a measured 268,820 B — adding two families on top of Inter and Crimson Pro would have cost ~39 KB and blown it. Measured from Google Fonts on 2026-09-03, latin subset, the exact URLs `base.html` requests: **Inter (variable, wght@400;500;600;700) 48,256 B** out; **Manrope (same axis) 24,836 B** and **Marcellus (static — it has no weight axis) 14,552 B** in. Net **−8,868 B**, so the total falls rather than rises. `display` was deliberately NOT swapped in the same motion: Marcellus ships one weight, and 15 `font-display font-bold`/`font-semibold` elements in this tree would have got a SYNTHESISED bold — the defect family #189 exists to remove. Two of those 15 (`_subscribe_modal.html:37`, `rashifal.html:181`) render Devanagari under the Hindi toggle and resolve to Noto Sans Devanagari 700, which is real and already loaded, so "just drop the bold" would de-bold Hindi headings. Crimson Pro retires with the last un-migrated screen, returning a further ~48 KB. Both new stacks keep `"Noto Sans Devanagari"` as their second entry (#189/#235) |
| 2026-09-03 | **Crimson Pro retired; Marcellus + Manrope are the whole Latin stack** | #261. Measured from the live css2 URL the page requests: latin + devanagari now totals **248,836 B** against `MAX_FONT_BYTES = 285,000`, down from **268,820 B** before the epic — a smaller page having ADDED a family and removed two (Inter in #242, Crimson Pro here). Seven `font-display font-bold` elements moved to Marcellus unbolded; Marcellus ships one weight and Google Fonts will never serve another, so any bold on it is synthesised (#189's defect family). Two of those seven render Devanagari under the Hindi toggle and now resolve to Noto Sans Devanagari 400 — real, loaded, regular |
| 2026-09-03 | **Tiro Devanagari Sanskrit rejected on payload** | #261. The handoff specifies it for all Devanagari. Its devanagari subset is **183,900 B** against Noto Serif Devanagari's **50,952 B** — 3.6x, **+132,948 B** — taking the page to ~297 KB against a 285,000 B budget. Does not fit. Recorded as a finding rather than a quiet overspend, per the token-budget rule in CLAUDE.md. Re-measure before re-proposing; do not re-derive from memory |
| 2026-09-03 | **The mobile tab bar lives at the END of `<body>`, not in `_nav.html`** | #261. In `_nav.html` — included at the top of every page — its five links came early in the DOM while painting at the bottom of the viewport, producing one backward focus transition per language on mobile: the WCAG 2.4.3 violation #195 exists to prevent, measured by the keyboard sweep. Moved last in the document; the active tab derives from `request.url.path` because `active_page` is block-scoped and invisible there. Costs 75px of viewport, so the homepage CTA's real clearance at 375x667 is **86px** (129px without it) — `measure_cta_fold.py` reports NO change and is right to, because it measures document position, which a fixed element never moves |
| 2026-09-03 | **Semantic status colours are not brand colours, and sit at the -800 stop** | #243/#245. good/steady/testing/deep and avoid/act are scales, and the 14-colour role palette has no green or amber. They stay on emerald/amber/rose — but at -800, because -700 is 4.48:1 (emerald) and 4.10:1 (amber) on cream-2 and fails AA at the sizes these render at. The handoff's own "Rahu Kaal in sindoor on a night block" is 2.53:1 — a fourth contrast failure in that document, after the three #236 corrected |
| — | GCS bucket stays in the US | free tier is US-only; relocation considered and rejected |
| 2026-10-04 | Hindi gets 13 URLs at `/hi/{path}`, not ~200 | with `?lang=hi` the rest of the site is 83-98% textually identical to English (only the chrome is translated): `/learn/` ~0.97-0.98 similar / ~1.5-1.8% Devanagari (two independent measurements, differing by method and by that day's content; the conclusion is unaffected). Only `/rashifal` + the 12 rashi pages have genuinely Hindi primary content (prod `/rashifal/aries?lang=hi`: 74.3% Devanagari, 0.240 similarity). Publishing the rest would ship ~200 near-duplicates |
| 2026-10-04 | `/hi` is a ROUTER, not a path-stripping middleware | rewriting `scope["path"]` makes `request.url.path` return the English path inside the handler, so `base.html` canonicalises `/hi/rashifal` onto `/rashifal` — the exact defect #124 removes. Built, reproduced, discarded |
| 2026-10-04 | `?lang=hi` 301s to `/hi/{path}` for published paths only | otherwise the same Hindi content stays reachable under an English canonical. Unpublished paths keep `?lang=hi` working — there is no Hindi URL to send them to |
| 2026-10-05 | the language control stays a `<select>`, not a button group | `base.html` sets `hx-boost="true"` on `<body>`. A user-clicked `<button type=submit>` fires a submit event, so htmx intercepts it, swaps the body and leaves `<html>` alone — and `html[lang="hi"] { font-size: 108% }` therefore never applies, so Devanagari renders 8% small and a screen reader keeps the English voice. Measured in Chromium: 6 of 9 switches stale without `hx-boost="false"`, 0 with. `<select onchange="this.form.submit()">` is immune by construction — a PROGRAMMATIC submit fires no submit event, so htmx never sees it. A button-group rewrite was built, broke this, and was reverted; it was better in real ways (aria-pressed, works with JS off, no `<noscript>`) and should return as its own change with `scripts/verify_lang_switch_browser.py` green and the mobile-reachability fix. That gate clicks the control and reads `document.documentElement.lang` plus the computed root font-size, because four QA rounds of server-side verification could not see this class at all — `TestClient` cannot run htmx |
| 2026-10-04 | unpublished pages emit NO hreflang, not a lone `en-IN` | a `hi-IN` pointing at a non-existent page makes Google discard hreflang site-wide, poisoning the 13 URLs that matter to decorate ~198 that do not |
| 2026-10-04 | sitemap sweep cost: **TPM is the binding constraint, not TPD** | 12 cold Hindi generations per `verify-production` sweep at 3,341 tokens each (measured with `o200k_base`, the right family for `gpt-oss-120b/20b`; mean prompt 13,674 chars across the 12 rashis) = **40,092 input tokens/day, 20.0% of the 200k TPD** — fits. But the sweep issues them at `-P 6` with NO pacing (`_RASHIFAL_MIN_INTERVAL_S = 0.0`, and the single-rashi path is never paced at all — an earlier version of this row said `rashifal.py` passes `pacer=None`, but `generate_rashifal_for_rashi` takes no `pacer` parameter; the conclusion was right and the mechanism invented, QA round 6), so a fully cold sweep is English 12 + Hindi 12 ≈ **78,600 input tokens in a few minutes** against 8,000 TPM per model / 16,000 for the `groq120,groq20` chain. It cannot fit under ~5 minutes however scheduled, so it will 429 down the chain toward the paid `openai` leg. **Pre-existing for the English 12; #124 doubles it.** Nothing pre-warms the `rashifal_single` namespace — the warm-rashifal jobs write only the combined key. *(Superseded by #268, 2026-10-08: the single route now derives its reading from the combined text instead of generating, see the row below. And this row's headline conclusion — "TPM is the binding constraint", TPD "fits" at 40,092/200,000 — was disproved the same day: the daily budget was exhausted at **198,298 of 200,000 TPD** and 21 of 24 pages 503'd.)* Measured by QA 2026-10-04; actual 429 behaviour NOT measured (needs real Groq calls). Flagged for the human: the fix is either pacing the sweep or adding a model, and adding a model is not an agent's decision |
| 2026-10-08 | `verify-production` stops sweeping the LLM-backed pages, and stops running on commits that cannot reach production | **The 2026-10-04 row above predicted this and was right; this is the fix.** Two findings, both measured. (1) The sweep spent the product's own free tier to verify it: 24 `/rashifal/{rashi}` pages x ~3,330 input tokens = ~80k per sweep, and the sweep ran on every push to `main` — 12 times on 2026-10-08, so **~960k free-tier tokens** to prove pages render. Pacing at `-P 2` capped the token *rate* but not the *spend*, and made the sweep serial-slow: **13 consecutive runs died at exactly 600s** (`exit code 124`), and since the smoke gate exits 1 it **skipped every later assertion**, including the #216/#218 rule-source check — the expensive step was masking the valuable ones. Excluded; the weekly run probes **one** page, rotating by ISO week, all 24 covered in 24 weeks. (2) Of the last 25 commits on `main`, **zero** touched a shipped path — all `.github/`, `.claude/`, `scripts/`, `measurements/`, root `*.md` — yet each paid ~5 min of deploy wait plus a 189-URL sweep: **227 Actions minutes in one day** against a 2,000-minute month. `paths-ignore` derived from the Dockerfile's four `COPY` targets, as an ignore-list so a new top-level path defaults to verifying, and `*.md` not `**.md` because the latter would exempt `src/astro_ai/knowledge/*.md` from verification. (Corrected 2026-10-15: this row first called that corpus "the runtime corpus" — it is not read at runtime; see the #354 row. The conclusion stands as the conservative default, since the files ship in the image under `src/`.) The weekly probe asserts on the `.speakable-body` **div** rather than page size: stripping the reading from `/rashifal/aries` leaves **124,784 of 125,952 bytes** intact, so a byte floor passes a page with no reading — mutation-tested, 1,279 chars real vs 111 empty. Cost: a docs-only fix now produces no run, so `close-on-evidence` cannot auto-close it; those close via `/prioritise` |
| 2026-10-08 | `/rashifal/{rashi}` is DERIVED from the cached combined reading, not pre-warmed | #268. The issue proposed a warm step writing the 24 `rashifal_single` entries. Two things in the code say that cannot work. (1) `generate_rashifal` is 12 calls of `_generate_rashifal_single` — the same function, prompt and day signals the single route uses — so the combined text the job already caches *contains* every page's reading; warming the single namespace would pay for the same 24 readings twice: ~24 x 3,330 = ~80k input tokens on top of the ~80k the combined job spends, ~160k of a 200k TPD before any reader. (2) `rashifal_single` is `daily_cache` only (a file on one instance; no GCS/SQLite tier), and Cloud Run runs `minScale=0`/`maxScale=5`, so a warm request would fill one instance's disk and nobody else's. It also would not have helped on 2026-10-08: with the budget gone (198,298 of 200,000 TPD) a warm job has nothing to generate with, but the 07:00 combined blob was already in the bucket. Chosen: on a `rashifal_single` miss the route reads the combined text (`daily_cache` tier 0, then the GCS blob through `_durable_get`'s 30s negative cache; SQLite skipped, it is per-instance), cuts the rashi's section **by heading name** — exact per-segment equality, exactly one match, never position and never substring (`min`, a Pisces token in `chart._RASHI_NAME_TOKENS`, is inside "Gemini / Mithuna") — runs the single route's own quality gate, stores it, serves it. Placed before the `_regen_blocked` cooldown so a gate-failed rashi heals from the blob. Fail-closed: any miss falls through to live generation exactly as before. The write-back of a GCS blob into the `rashifal` tier-0 file is quality-gated, because `_daily_rashifal_text` returns a tier-0 hit unchecked and an ungated write-back would let the 07:00 blast email a corrupt blob. `warm_rashifal` now reports `single_pages` (how many of 12 pages are derivable), `ok` needs 12 of 12, and fewer than 12 fires an alert at HTTP 200 — this is the "how many readings it wrote" detector the issue asked for. **Tokens: 0 new per call and per day** (no prompt text touched; a cold reader with the blob present costs 0 where it cost ~3,330). Rejected: a warm job generating 24 more readings (above); splitting the combined blob into 24 GCS blobs (more writes and a second source of truth); the route calling `_daily_rashifal_text` itself (83-130s cold, past the 60s Firebase ceiling); re-adding paid `openai` to the chain; serving yesterday's reading. **Not measured:** the real Hindi heading format — `rashifal_single.txt` says `## {English} / {Sanskrit}` while the Hindi suffix says to translate headings, and no production Hindi combined text was available, so the Devanagari names in `rashifal_derive.py` are an assumption and the Hindi test fixture is labelled as one (an unrecognised format reads `single_pages: 0` for `hi` and the page falls through to live generation); GCS read latency from `asia-south1`; production blob contents. A call that emits intro text before its `## ` heading contaminates the previous section — the same text already reaches subscribers. The verify-production blind spot (nothing probes the 24 pages since 5b3dd71) is a separate issue |
| 2026-10-09 | `.github/workflows/` is now read by a gate: `scripts/verify_workflows.py`, with `scripts/mutate_verify_workflows.py` proving it can go red | #313 part 1. Four defects in the agent loop's own plumbing lived silently until a correct QA'd PR could not merge: `agent-merge` read `steps.pr.outputs.sha` inside the step whose id is `pr` (always empty, HTTP 422, the whole `workflow_run` leg failing 100%); `close-on-evidence` lacked `pull-requests: read` (HTTP 403, masked because its `if` had never passed); `pr-gates` omitted `ready_for_review` from `types` (stranded draft #303); `agent-merge` fetched `isDraft` and never read it. Nothing read those files, and no red run was ever read. The gate is static, PyYAML-only, no network, and checks three things per file: (1) a step reading its own `steps.<id>.outputs.*`, with shell comments stripped first and quote-aware, because `agent-merge.yml` now discusses that very expression in prose; (2) every `gh` call at command position in a `run:` block against the job's effective `permissions` (job replaces workflow; write implies read; omitted = none), judged only when the step's `GH_TOKEN` resolves to the workflow token, with other tokens printed as SKIPPED and unrecognised calls printed as UNCLASSIFIED rather than guessed; (3) `pull_request` / `pull_request_target` carrying an explicit `types:` including `ready_for_review`, with one justified exemption (`agent-merge`'s `labeled`-only trigger). A file it cannot parse FAILS; `EXPECTED_WORKFLOWS` is pinned (14 once `agent-steward.yml` landed); exit 2 is could-not-verify. **What it does NOT catch:** defect 4 (a value fetched and never read -- needs data flow) and anything about *effect*, i.e. a workflow that passes all three checks and still does nothing; that is #313 part 2, the weekly outcome report, not built. `mutate_verify_workflows.py` re-introduces each defect in a temp copy and requires exit 1 plus a FAIL line naming the file, rule and thing broken, with controls that the untouched copy, a comment-only mention, a trailing-comment mention and an **uninterpolated** mention in a quoted shell string all exit 0, and that the same text **interpolated** (`${{ ... }}`) exits 1 — GitHub substitutes only inside `${{ }}`, so bare text is inert and failing on it was a false positive QA caught, which that harness had itself been requiring. `TRIGGER_EXEMPT` also pins the `types:` value an exemption was granted for, so an exemption cannot survive the justification it was granted under; wired into `pr-gates.yml` beside the behaviour-suite mutation step. First run against the live tree found three latent defects (see #313): `agent-discover` and `agent-work` run `gh run list`/`gh run download` with no `actions: read` on a private repo, hidden by `continue-on-error` plus a quiet fall-through, and `verify-build` has `pull_request:` with no `types:`. No LLM path, 0 tokens |
| 2026-10-09 | The loop-outcome report judges **effect over a trailing window, never a conclusion**; `scripts/report_loop_outcomes.py` + `loop-outcomes.yml` (Tue 03:30 UTC) | #316 (part 2 of #313). Four defects on 2026-10-08/09 hid behind green or absent status: `agent-merge`'s `workflow_run` leg 422'd on every run (4 of 4, ids 37823306954 / 37824154542 / 37878016497 / 37878770889) while the `pull_request_target` leg merged; `close-on-evidence` 403'd on a missing `pull-requests: read`; the measurement fetch 403'd inside a `continue-on-error` step so **the delivery cycle never once received the analyst's measurement**; and `close-on-evidence`'s first real run closed nothing (PR #312 mentioned #304, no closing keyword). #315's static gate sees two. Every verdict is `expected` (derived UPSTREAM: gate completions, `qa-pass` events, merged agent PRs with a green verification of their merge commit) against `effect` (observed DOWNSTREAM: leg runs, merges, a bot `closed` event, a commit touching the loop's report file, the measurement fetch's own log). Four verdicts — OK, IDLE (expected set empty), BROKEN, UNKNOWN (403/404/expired log) — and **UNKNOWN is never green**: exit 1 BROKEN, 2 UNKNOWN. IDLE vs BROKEN is the point; conflating them is what hid the 403 for the loop's whole life. A PR is judged only if it MERGED inside the window (`Window.merged_in`), not merely if it was updated there — `agent_prs` selects by `updated_at`, and a PR merged last week and commented on this week read as a false BROKEN (its verification run and its issue's close belong to the previous window); the in-flight grace boundary is inclusive (exactly `GRACE` old is judged). Receipts are read from the step's OUTPUT only, after `##[endgroup]`, because the group above it echoes the script source, which contains both `no prior measurement` and `measurement from run`. Classifiers are pure behind a `Source` seam and tested offline from `tests/fixtures/loop_outcomes/` (a scenario directory holds only what differs from `healthy/`); fixtures not fetched from the API say `recorded: false` in `MANIFEST.json` and a test pins the three that may claim otherwise. The workflow's `gh api` calls are invisible to #315's gate, so the endpoint -> scope table lives in the script header and a test asserts the YAML grants each. A BROKEN/UNKNOWN week is posted to ONE standing issue, because #313's first defect WAS a red run nobody read; it is never auto-closed. **Cost:** 0 LLM tokens; 24 and 31 distinct `gh api` calls on the two fixture weeks (memoised), growing ~3 per agent PR and 2 per log receipt (capped at 14 per loop) against a 1,000/h token limit — **not measured against live GitHub**, this sandbox's token gets 403 on `actions/*`. **Not yet validated against its own metric:** replaying 2026-10-08..10 needs the file on `main` (`gh workflow run loop-outcomes.yml -f since=2026-10-08 -f until=2026-10-10`); the job-log line format is from the API docs, not a recording, so the first live run must be read for that. Rejected: a conclusions-only dashboard (that is the defect), an LLM summariser (0 tokens is the point), committing the report under `measurements/` (never ships, invites load-bearing use), folding it into verify-production or #315 (different question: site / tree vs history) |
| 2026-10-15 | **`agent-merge` holds any PR that touches the trust boundary for a human; and `knowledge/*.md` is not read at runtime** | #354 item 1. The repo is public and the loop merges unattended, so green gates plus `qa-pass` stopped being a sufficient test for a change to what the product says, what agents believe, what the gates are, or where user data goes. A `Trust boundary` step (after `size`, before the draft/merge/post-merge-verify steps, which now key on `steps.boundary.outputs.ok`) labels the PR `needs-human-review`, comments once, and leaves it open if any changed file is under `src/astro_ai/prompts/`, `src/astro_ai/knowledge/` or `.github/workflows/`, or is exactly `events.py`, `notify.py`, `email_sender.py` or `storage.py`. The list is the single `TRUST_BOUNDARY` env var in `agent-merge.yml`. **Three choices that carry the weight.** (1) The file list comes from `pulls/N/files --paginate`, not `gh pr view --json files`, which stops at 100 and would let a protected path hide at position 101; at the API's 3,000 ceiling the step fails closed. Rename sources (`previous_filename`) are checked too. (2) The job still has no checkout (`pull_request_target` + write token): paths are compared as strings via a file, never interpolated or executed. (3) Entries ending `/` match by prefix and every other entry by exact path, so `events_helper.py` and `routes/storage.py` are not held. Covered by `tests/test_agent_merge_trust_boundary.py` (33 tests, which lift the workflow's own `is_protected` and list rather than reimplementing them) and two entries in `mutate_behaviour_suite.py`. **Correction recorded with it:** CLAUDE.md and the 2026-10-08 row said `knowledge/*.md` is read at runtime. Measured 2026-10-15: `grep -rn "knowledge" --include="*.py" src/ \| grep -E "read_text\|open\(\|glob\|iterdir\|Path"` returns 1 hit, a comment (`numerology.py:996`). The corpus is the authority *agents* cite; the file that IS read at runtime and becomes the system prompt is `prompts/*.txt` (`routes/deps.py` `PROMPTS_DIR`). Not done here (separate items of #354): egress allow-list, PII sentinel sweep, issue provenance, prompt hash manifest. Note this PR itself touches `.github/workflows/`, so it is the first one the guard would hold |
| 2026-10-15 | **No pull-request value reaches a `run:` block in a workflow carrying a privileged trigger** | #358. `agent-merge` interpolated a pull-request HEAD BRANCH NAME into shell at four places, the earliest being the agent-branch filter itself — `case "${{ steps.pr.outputs.branch }}" in`. `${{ }}` is substituted **before bash parses the script**, so the value was not a shell string but shell source, and the `issue/*` filter could not protect the file because the filter *was* the injection point. Measured 2026-10-15: `git check-ref-format` accepts `issue/1$(id)`, ``issue/1`id```, `issue/1;id;` and a `${IFS}`-spaced pipeline — `$ ( ) " ` ; & \|` are all legal in a ref and `${IFS}` stands in for the forbidden space. The job holds `contents: write` + `actions: write` and had **no fork guard**: a fork PR reached it with no maintainer action, because `pr-gates` runs on `pull_request`, `workflow_run` then fires in the base repo with the base definition and the write token, and `workflow_run.event == 'pull_request'` was true. **Three changes.** (1) All 24 event- and PR-derived interpolations in `agent-merge.yml` and the one in `close-on-evidence.yml` now arrive via `env:`, where bash never re-parses them, expanded quoted. (2) The job's `if:` requires the head repository to equal `github.repository` on **both** legs — `pull_request_target` carries `event.pull_request.head.repo`, `workflow_run` carries `event.workflow_run.head_repository`, and neither is readable from the other. (3) `verify_workflows.py` check 5 fails on **any** `${{` inside a `run:` block of a workflow triggered by `pull_request_target`, `workflow_run` or `issue_comment`. The rule is "none" rather than "no unsafe ones" because deciding which values an outsider can influence is precisely the judgment that failed. **The gate's own first draft was wrong in the way the file already warned about:** it reported `re.findall(r"\$\{\{[^}]*\}\}")` and exited 0 on `${{ format('{0}', steps.pr.outputs.branch) }}` — `[^}]*` stops at the `}` in `{0}` — so a real defect read as clean and the gate printed `ok`. `mutate_verify_workflows.py` caught it; detection is now the presence of `${{`. Check 1 carries a comment about the identical trap. Covered by `tests/test_agent_merge_fork_guard.py` (16 tests, including that every `$PR_*`/`$EVENT_*`/`$RUN_*` name a step expands is **declared** — the failure mode of this refactor is an undeclared name expanding to the empty string, which does not error), 3 mutations and 2 false-positive controls in `mutate_verify_workflows.py` (24/24), and 3 in `mutate_behaviour_suite.py`. Not executed against GitHub; the claim rests on reading the workflow and on `check-ref-format` |
| 2026-10-15 | **`agent-merge` sweeps every 30 minutes instead of relying only on edges** | #357. Both existing triggers are **edges**, and nothing could re-ask the question once one was spent, so a PR whose last green check landed after its last edge stayed green, `qa-pass` and `MERGEABLE` forever. Four instances: #303 (`ready_for_review` absent from `pr-gates`' types, so no check at all), #322 (a `GITHUB_TOKEN`-authored PR emits no `workflow_run`), #352 (the green run was `workflow_dispatch`, deliberately excluded because a dispatched run checks out the branch, not `refs/pull/N/merge`), #356 (`verify-build` is a different workflow and this one listens only to `PR gates`). Each was fixed by adding or correcting an edge; a fifth was always going to be missed. **#356 shows the ordering is not even unlikely:** `pr-gates` deliberately skips its suite on a docs-only change — and deliberately still *runs*, so this job keeps its trigger — finishing in **9s**, while `verify-build` has no such skip and takes **~70s**. Measured 2026-10-15: 9s vs 68s on #356, against 8m34s vs 75s on the code PR before it. The "`pr-gates` is the slowest check" assumption holds for code PRs and inverts for exactly the PRs the skip was written for. **The sweep adds no authority.** It supplies a PR number and nothing else; `own`, `gates`, `qa`, `size` and `boundary` re-read everything from the API in the same order, so the worst it can do is merge something that already satisfies every condition. Its candidate filter requires open, non-draft, same-repository, `issue/*`, `qa-pass` present and `qa-fail`/`needs-human-review`/`too-large-to-automerge` absent — `qa-pass` because `sort \| first` over all open PRs would otherwise let one unlabelled lower-numbered PR starve an eligible one every 30 minutes, and the three hold labels because re-labelling a held PR on a cron is a comment loop. A new `concurrency: {group: agent-merge, cancel-in-progress: false}` serialises the workflow repo-wide (a per-PR group is impossible: the `workflow_run` leg does not know its PR until the first step runs), and the `pr` step now exits early unless the PR is still `OPEN`, so a sweep racing an edge cannot reach `gh pr merge` on a merged PR. Covered by `tests/test_agent_merge_sweep.py` (14 tests, which lift the jq filter out of the workflow and drive it with synthetic `/pulls` payloads) and two entries in `mutate_behaviour_suite.py` |
| 2026-10-15 | **Per-route miss latency and the fallback REASON are counters in the existing day-file; `/admin/ops` names the store it read** | #355. Production's own store showed an avg cache-miss of ~40 s and 101 fallbacks against 196 misses over 30 days, and neither was attributable: `miss_latency_sum_ms` was global (a 24-reading rashifal blast and one `/ask` were one number) and `record()` took `fallback: bool`. **Per-route latency is TWO keys**, `miss_latency_sum_ms` and `miss_latency_n`, on `call_by_route[route]`, not one: day-files written before this change hold misses with no latency, so dividing by `calls - hits` would put zeros in the numerator for the whole 30-day window and a zero reads as "fast". `usage_summary` divides by `miss_latency_n` and emits `avg_miss_latency_ms: None` (rendered `—`) when it is 0; the global keys are untouched. **Fallback reasons** are `fallback_reasons["<failed_provider>\|<reason>"]`, incremented in the same mutator as `fallbacks`, so the two agree for every day recorded after the change (earlier days have `fallbacks` and no reasons, so a mixed window's reasons sum to LESS, and the page says so). Reason is a closed vocabulary from `providers._failure_reason`: `429_tpm`, `429_tpd`, `429`, `413`, `timeout`, `empty`, `quality`, `error`; the 413 test runs first because Groq's 413 body says "tokens per minute (TPM)" and would otherwise be filed as a rate limit. `chat()` sets provider and reason only through one nested `_fail()` so they cannot drift from `last_err`; with several failures before a success, the LAST one is recorded (one entry per fallback keeps the sum exact). The panel labels say so: "needed a retry or a 2nd provider" (a same-provider retry after a 429 also counts as a fallback, pre-existing) and "reason for the last failure". Limit/Used/Requested figures are deliberately not parsed (#350). **`storage.describe_store()`** reports `gcs:<bucket>` or `local:<dir>` from configuration, not reachability (a configured but unreachable bucket still falls back to /tmp at call time), and the App health panel prints it (tooltip names BOTH local dirs, since `events` has its own, or says a bucket is "configured, not verified reachable"), in amber and plainly "local dev store — not production" when local, because "0 errors" from a developer's /tmp and from production's bucket were indistinguishable. **Cost:** 0 LLM tokens; 0 added GCS reads or writes (the new keys ride the `update_json` that `record()` and `record_call()` already make); the blob grows by two ints per route and one small dict key per distinct (provider, reason) pair |
| 2026-10-15 | **/admin/ops reads the backlog LIVE and app health in-process; team health stays a snapshot, and every panel says which** | #353. Three panels, three different answers, and the page now labels each rather than implying one freshness. **Backlog: live.** Measured 2026-10-15, `/repos/{repo}/issues?state=open&per_page=100` is **1 request, 1.08 s**, and the derivation over it is byte-identical to `gh issue list` across all 67 rows. It is also the panel where staleness actively misleads: on 2026-10-14 the page read `66 open` against 65 actual and the number looked WRONG rather than OLD. Fallback is the committed `issues.json`, because an unauthenticated call is 60/hour per egress IP and Cloud Run's is shared with every other tenant behind that NAT — a fallback raises its own amber alert, so the downgrade is never silent. **App health: already live**, read from this app's own GCS stores in-process on a 60 s cache; it was only ever labelled in the same grey as every other caption. **Team health: cannot be live, measured.** `collect_agent_performance` needs **46 GitHub requests** (1 workflow list + 2 run queries × 15 workflows + up to 15 commit lookups) — one render would spend 46 of the 60/hour budget — and the one-request shortcut (`/actions/runs?per_page=100`, 3.08 s) covers only **11 of 15** workflows, because a workflow that is broken is one that has not run recently and falls out of the window. It is also uncomputable in the container at all: `liveness()` reads `.github/workflows/*.yml` and `schedule_since()` shells to `git log`, and the image copies `pyproject.toml uv.lock README.md` and `src/`. So its only freshness lever is collection frequency, raised from twice a day to every three hours — collectors only, no analyst, no LLM call, and `measurements/**` is on the trigger's `ignoredFiles` so none of it deploys. The derivation moved to `src/astro_ai/issue_backlog.py` because `scripts/` is not in the image and a second copy of `derive_priority` is how a live count and the snapshot it falls back to would start disagreeing |
| 2026-10-15 | **Outsider-issue triage stage 1 is `scripts/triage_outsider_issues.py`: mechanical, 0 Groq tokens, fail-closed on the resolver, and the workflow that would run it is NOT in the tree** | #367 (`partial/`, does not close it). Chief's ruling: option A. The script checks only what needs no judgement: (a) the Evidence Block, by importing `verify_issue_evidence.check()` and reading the **issue body only** (comments include this script's own example `repro:`, which would satisfy it); (b) a duplicate of an **older** open issue by token-set Jaccard over title+body, `DUP_THRESHOLD = 0.40` — measured over the 74 open issues on 2026-10-15, 2,701 pairs, median 0.058, max 0.275 (#310 vs #308, distinct), and no real duplicate existed to calibrate the upper side, so that side is a test fixture (0.885 vs 0.256). Outcomes `triage:needs-detail` > `triage:possible-duplicate` > `triage:reviewed`. **The outsider test has one source**, `scripts/resolve_provenance.py <n>` (#361/#363) by argv with no `--apply`: exit 1 proceed, 0 skip silently, anything else or a missing file writes nothing and exits 2 naming the cause — so the script is **inert until #363 lands**, and its tests mock the resolver contract (one real call on a known outsider issue is owed after). Comments are static templates plus integers: they never echo a stranger's title or body, and `#N` is the only link. One comment per issue per state via `<!-- triage-stage1:<state> -->`, honoured only in a comment this token wrote (`viewerDidAuthor`); no code path closes anything, enforced by a source scan and a row in `mutate_behaviour_suite.py`. **Deliberately not built:** AC3 `triage:cannot-reproduce` (`validate_issue.py` follows off-host URLs and its `POST /reading` fixtures spend production Groq tokens on a stranger's say-so), stage 2, the workflow (a push touching `.github/workflows/` is a trust-boundary change and the loop's token cannot push it; delivered as a patch for a human). **Cost:** 0 LLM tokens; ~2 `gh` calls per not-yet-triaged open issue per run (the resolver's), not measured live because the resolver is absent. **Merge note:** #363 and this change both raise `EXPECTED_TESTS` and the `behaviour suite` row in §1; whichever merges second must re-sum both (this change took the suite 497 → 540) |
| 2026-10-15 | **The loop resolves an issue's provenance before acting on it: `scripts/resolve_provenance.py`, fail closed, no bot allowlist (PARTIAL)** | #361. Nothing checked who filed an issue (`grep -rciE 'author_association|collaborator|permission'` over agent-cycle.md and project-manager.md: 0 and 0), so an outsider's issue reached an engineer. **Chief's ruling, Standing ruling 4 clause 3** ("an option that cannot announce its own failure is not robust"): Option A. Permission from `collaborators/<login>/permission`, never `author_association`: `admin`/`write` trusted; `read`/`none`/404 outsider; 403, 5xx, timeout, empty or unrecognised output UNRESOLVED (exit 2, one comment, stop). Every `is_bot=true` author is outsider with no login allowlist. `provenance:trusted` counts only if its LATEST `labeled` event was applied by a `type == User` account with `admin`/`write`. **Measured:** bot-filed issues are 17/40 of the recent window but 21/312 all-time (6.7%); `claude[bot]` resolves to `none`, `app/github-actions` to a 404. **Landed:** the resolver, `tests/test_resolve_provenance.py` (73 tests), eight mutation rows, `agent-cycle.md` Step 0a, `project-manager.md` and `qa.md` rules. **Policy narrowed by the owner on the same day, after this branch was built:** *"outsider's issue can't be assigned to engineer ... don't do any implementation."* Exit 1 was "proceed under four stricter rules" (no `qa-pass`, text is data, no corpus citation, no `chief`); it is now **comment, label, skip** — not ranked, not built, under any label or assignment — and the four rules are deleted with the case they covered. The resolver is unchanged; only the policy applied to its verdict moved. This is safer and not merely simpler: if the owner wants an outsider's idea built they re-file it as their own issue, which resolves trusted on its own, so the text an agent reads is the owner's wording and the injection surface is absent rather than managed. Evaluating whether an outsider issue is worth doing moves to #367, which starts with `verify_issue_evidence.py` and `validate_issue.py` and so costs nothing on issues a script can answer. **Measured, and why `qa-pass` is what holds:** in `agent-merge.yml` the `QA verdict` step reads only `qa-fail`/`qa-pass`, and `needs-human-review` is read by the #357 sweep's candidate filter alone, so on the `labeled` and `workflow_run` legs that label does NOT stop a merge; withholding `qa-pass` does. **NOT landed, and needs a human push (the loop's App token has no `workflows` permission):** swapping `agent-merge`'s hold predicate from paths to the provenance label, removing `TRUST_BOUNDARY`, rewriting `tests/test_agent_merge_trust_boundary.py` against the new predicate, and the hold mutation. The path hold stays until then; nothing was weakened. **Known gaps:** (1) `agent-work.yml`'s safety-net push, unfinished-cycle summary and loop receipt only recognise `issue/*` branches, so on a `partial/<n>-*` branch (the form used for work that leaves acceptance criteria undone, so `agent-merge` and `close-on-evidence` ignore it) the cycle must push after every commit itself and nothing catches a lost runner; fixing it is a `.github/workflows/` edit. (2) the UNRESOLVED-comment marker is honoured only in a comment this token wrote (`viewerDidAuthor`), so a copied marker cannot silence the stop, but a rerun under a different identity posts a visible duplicate. (3) whether the agent-work App token may call the permission API is unverified (a 403 there makes every issue UNRESOLVED, visibly) |
| 2026-10-13 | The delivery loop's per-cycle outcomes and the team's cost are committed as `measurements/loop.json` and `measurements/cost.json` by `agent-measure`'s `commit` job, via `scripts/collect_loop_measurements.py` | #338, slice 1 of #335 (the data layer only; `/admin/ops` is a later slice). The row above reports per-LEG health into a 90-day artifact and one standing issue, neither readable by a page. This writes one row per completed `agent-work` run: `run, workflow, date, started, trigger, conclusion, minutes, issue, pr, pr_merged, outcome, attribution`. **Attribution is the run's own record, in three labelled tiers, never a time-window match:** `receipt` (a final `if: always()` step in `agent-work.yml` prints `LOOP-RECEIPT issue=<n|none> branch=<b> pr=<n|none>` with `printf ...%s`, so the step's echoed source in the log cannot satisfy the reader's `issue=(\d+|none)`; a failed PR lookup prints NO receipt rather than `pr=none`), `log` (runs before the receipt: the net step's own lines `<branch> already on origin` / `no commits on <branch>` / `on '<b>', not an issue branch` / `branch 'issue/..' set up to track`, with the PR then looked up by branch name among PRs that existed when the run ended — branches are reused: `issue/255-...` carries #328 and #330), else `unattributed` (issue and pr null). Spike on the 23 completed runs of 2026-10-08..13: **18 resolve by log line (15 to an issue), 5 are unattributed** — three runs whose push died on an expired token before any log line was written, one that predates the net step's messages, and one cancelled run. A log read needs `gh api --allow-escape-sequences` (gh 2.102.0 refuses every job log without it; `report_loop_outcomes.GhSource.text` does not pass it, so its measurement-receipt reads may be reporting UNKNOWN for that reason — not touched here). **`unknown` is a fifth outcome beyond the brief's four** (`shipped`, `pr open`, `nothing`, `failed`): a green run whose log named no branch is not `nothing`, and calling it that is the silent-success shape #316 exists to find. `nothing` requires the run's own statement that nothing was pushed (a receipt with `pr=none`, `no commits on`, or `not an issue branch`); a PR looked up by branch for a `no commits on` run would have been #292, opened two hours later by a different run. A `failure` run whose rescue step still merged a PR is `shipped` with `conclusion: failure` kept. Several runs can work one branch, so count distinct `pr`, not rows. Settled rows are frozen (only `pr open`, or an unreadable PR, is re-read, PR only), rows prune at 120 days, and a document that fails `validate_loop` writes nothing and exits 1 so the previous file stands. `cost.json` comes from a rates table in the script: Claude Max 5x $100 (owner-confirmed 2026-10-13), GitHub Actions / Groq / GA4 / Search Console $0, Google Cloud and OpenAI **null** with a reason in `status` (`awaiting billing export`: no BigQuery billing export on bhagya-500701; `no usage source read`). A figure needs status `known`/`free-tier`; a zero standing on any other status, or a null with no reason, fails validation; no total and no timestamp, so an unchanged table is no commit. **Placement:** the `commit` job, not a new workflow (15 stays 15); its collect step runs BEFORE the report-less early exit so the loop file is not skipped on the days the analyst writes nothing, is `continue-on-error`, and the job gains `actions: read` + `pull-requests: read` for `gh api` calls `verify_workflows.py` cannot see (the endpoint-to-scope table is in the script header). **`measurements/` is not in the container image (the Dockerfile copies `src/` only), so a page must fetch these files over HTTP, not read them from disk.** Zero LLM calls. |
| 2026-10-11 | **Birth details leave the Telegram relay and the events log; events carry a keyed identity hash and a coarse profile instead** | #255. The kundli, matching, dosha and numerology Telegram alerts carried name, birth date, time, place and email, and `form_kundli` / `form_matching` events stored the same fields for the 30-day GCS window; #222 had already ruled that identifying data stays in the app log, not the channel. Now: the alerts send a diagnostic only (rashi names, model, tokens, latency, cache state, an 8-hex short key), and events store `identity_key` plus `age_band` and `city`. **`identity.identity_key` is an HMAC-SHA256 under a domain-separated subkey of `ASTRO_AI_COOKIE_SECRET`.** Rejected: an *unsalted hash* (name + date + time + place is a small structured space, a lookup table from the plaintext); *`fingerprint_chart`* (unsalted, and it is a GCS path component, so it is an identifier not a secret); a *per-row random salt* (defeats the one property wanted, that the same chart yields the same key twice so an alert can be matched to its event); a *new env var* (needs a GCP step an agent cannot take, and an unset one fails silently). Rotating the secret changes every key, bounded by the 30-day event retention. `age_band` / `city` are kept so the `/admin/insights` audience panels survive; **`city` fails closed**: `birth_place` is free text and users type street addresses into it (`Flat 4B, Rose Villa, Andheri, Mumbai` first stored `Flat 4B`), so `profiling._city_from_place` returns `""` for more than three comma tokens, any digit (bar a bare trailing postal code), any address word (flat, house, road, nagar, ...) or a first token over four words. `geocode_place` returns only coordinates and a timezone, so there is no canonical place name to prefer; `profiling.audience_summary` prefers them and falls back to raw fields for legacy events. The owner can override to strict (drop city and band). A `ChartError` message embeds the raw birth place, so `_fire_error_alert` relays its class name only. The session cookie is `Secure` when `K_REVISION` is set (i.e. on Cloud Run), not in local dev. **Natal cache stays indefinite** (owner-decided); the privacy copy now says so. **Relays that still carry PII are disclosed in `privacy.html`, not stripped**: `ask`, `signin`, `subscribe`, `feedback`, `muhurat`, `error_seen`. **Also found:** the Kaal Sarp Telegram alert had never fired. It read `KaalSarpDetails.is_present`, the field is `is_kaal_sarp`, and the `AttributeError` was swallowed by a `try/except: pass`; fixed and pinned. **Not done:** a scrub of raw events already stored (destructive, needs the owner's go-ahead; it is unknown whether the bucket has a lifecycle rule, so the 30-day window is a code-side retention only until checked). **0 new tokens per call**: no prompt is touched; `providers.last_used_tokens` only exposes the usage the provider already returned |
| — | Whole Sign houses | classical Parashari standard |
| — | No Pythagorean numerology mode | table appears in none of the books in `data/` |
| 2026-07 | Homepage does zero GCS reads | #144: 32 ops → 0, ~13s → <1s |
| 2026-08-16 | Standing permission to push QA'd work | user's words; conditions are load-bearing |
| 2026-08-21 | `reasoning_effort="low"` on all capable models | 3,072 → ~302 completion tokens, *more* visible output |
| 2026-08-21 | Empty completion raises rather than returning `""` | a blank reading was cached for a full day |
| 2026-08-22 | Rashifal blast split into warm + send | 399s single request → 83s + 130s + 0.02s |
| 2026-08-22 | `groq_qwen` dropped from the chain | unboundable; 399s vs 213s |
| 2026-08-22 | Shared reading never states a clock time | 79-min national spread; two cities' windows do not overlap |
| 2026-10-08 | The rashifal day-windows block is localised in FULL, not just the two names | #270. `format_day_windows_for_rashifal` localised only `rahu_kaal` / `abhijit_muhurta`; the band (`_RAHU_KAAL_BAND`), the ordinal (`_ordinal`), the directive prose and the example phrases `('during Rahu Kaal', 'in the Abhijit window near midday')` went to the model in English, and the Hindi reading echoed them into Devanagari prose (live on `/hi/rashifal/virgo`: "in the Abhijit window near midday", "Rahu काल"). Measured at d6c570d: **168 English words** left in the Hindi block once the two names were stripped; **0** after. Chosen: 18 i18n keys (`rashifal_window_facts`, `rashifal_window_directive`, `rahu_ord_1..8`, `rahu_band_1..8`), `chart.py` reduced to an assembler over the literal `_RAHU_KAAL_KEYS` table (literal, not `f"rahu_band_{n}"`, so `test_no_translation_key_is_defined_but_unused` can still see the keys). **English is byte-identical** — sha256 over the seven weekdays is `04118625184f5800` before and after, pinned in `tests/test_rashifal_window_block.py`. Hindi cost, o200k_base, 7 weekdays: **244–247 → 373–380 tokens (+~132/call)**, +3.9% of a ~3,341-token call; en unchanged at 243–246. Roughly +1.5k tokens/day on the Hindi blast (architect's estimate, not re-measured end to end) against the 200k TPD ceiling. A second echo source remains: `prompts/rashifal_single.txt` (English system prompt, lines ~92/112/141) says `Say "during Rahu Kaal" or "in the Abhijit window near midday"`. It is deliberately NOT edited — that would move the EN+HI prompt fingerprint and re-warm every cache — so the Hindi directive ends with a sentence telling the model not to repeat English example phrases from other instructions; that is a mitigation, not a proof, and the live hit-rate was not re-measured. Rejected: localising only band/ordinal/examples (the architect counted 103 Latin words remaining, so a no-English test would need an allowlist and prove little), `_LANG_SUFFIX['hi']` (shared with natal at the TPM ceiling), post-filtering the output. Out of scope, still English in the Hindi prompt: `/today`'s `format_panchang_for_prompt` takes no `lang`, and the weekday/tithi/Moon/retrograde signal lines. `PROMPT_LOGIC_VERSION` not bumped: rashifal's daily cache ignores it and a bump would orphan natal blobs |
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
| 2026-08-31 | `og:image` is a generated 1200x630 PNG, never SVG | og:image was a 512x512 icon and all 76 learn articles pointed at 320x320 SVG heroes; FB/LinkedIn/WhatsApp/X/Slack reject SVG outright, so every article previewed as a bare link |
| 2026-09-04 | Responses are gzipped, hashed static assets are `immutable` for a year, and the one-time per-process init is paid in the lifespan, not on a reader's request | The site had served every byte uncompressed since launch. Measured on production revision `bhagya-00380-t58` with a real `GET` carrying `Accept-Encoding: gzip, br`, headers dumped and the body kept raw: homepage HTML **141,191 B** served against 36,283 B under `gzip -9` (−74%), `app.css` **85,037 B** against 13,151 B (−85%). No `content-encoding` on either while `vary: accept-encoding` WAS present. Not a measuring artifact — the same curl through the same proxy gets `content-encoding: gzip` from google.com; `firebase.json` rewrites `**` to Cloud Run, so compression was the origin's to do. The homepage is `no-store`, so ~105 KB was paid on EVERY load, not just the first. After, on production revision `bhagya-00381-czp`: homepage **36,407 B**, `app.css` **13,152 B**, first-load total (html+css+fonts) **460,524 → 283,855 B, −176,669 B**. Separately, Cloud Run answers `cache-control: private` with no `max-age`, so a content-hashed `app.css?v=…` still cost a round trip to `asia-south1` per navigation despite #237 hashing it for exactly this reason; `_CachedStaticFiles` keys the rule on whether the URL is content-addressed (`?v=` → `immutable` 1y, else 300s), and `/sw.js` is untouched at `no-cache` because it is served from its own route for scope `/` — an immutable year there would make #253 permanent. Third: the FIRST request in a process cost **1.195 s** against **0.003 s** for the second. `cProfile` splits it — `TimezoneFinder()` 0.551 s and a live Nominatim geocode 0.422 s, both one-time (a second, different city costs 0.048 s; `trust_bar.counts()` is 1 ms, so #144's fix is holding). A/B against a `git worktree` at `da26382`, three fresh processes each: first `GET /` **5.05 / 2.17 / 2.38 s → 0.30 / 0.31 / 0.18 s**, cold total (startup + first request) **8.56 / 4.40 / 4.62 s → 6.64 / 3.15 / 2.90 s**. The lifespan does NOT shorten a scale-from-zero — Cloud Run already holds that request through startup — and the docstring says so; what it buys is Nominatim leaving the request path (`geocode_place` passes `timeout=10`, so a slow Nominatim could hang the homepage for ten seconds), a 1→2 scale-up warming before it takes traffic, and the cost appearing in startup logs. **`TimezoneFinderL` rejected on measurement**: 0.526 s to construct against 0.551 s (1.05×, no gain) and it returns `Etc/GMT+1` for Reykjavik where the full finder returns `Atlantic/Reykjavik` — one of the polar cities #150 and #227 are measured against. Fonts are now 83% of the remaining first-load payload (234,296 B of 283,855 B) and are the next lever, not the CSS |

### Rejected, with reasons — do not re-propose without new information

- **`TimezoneFinderL` in place of `TimezoneFinder`** — measured 2026-09-04 at
  0.526 s to construct against 0.551 s, i.e. no faster, while returning
  `Etc/GMT+1` for Reykjavik where the full finder returns `Atlantic/Reykjavik`.
- **Excluding already-compressed content types from `GZipMiddleware`** — PNG and
  woff2 responses gain nothing from it, but the static payload is small and an
  exclusion list is one more thing that has to stay true. Revisit with a
  measurement if the image surface grows, not on principle.
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
  QA rounds. Everything else is verified by execution plus the eighteen gates.
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
- **`verify_devanagari_serif` cannot complete in an agent container, but not for the
  reason recorded here until 2026-09-03.** Playwright IS installed and the gate runs;
  what fails is the network. Headless Chromium cannot reach `fonts.googleapis.com`
  through the agent proxy — the tunnel closes mid-handshake (`ws_closed_mid_exchange`,
  ~39 B received), with or without an explicit `proxy=` on the launch and with QUIC and
  HTTP/2 disabled. The gate does the right thing with that: it exits **2**, COULD NOT
  VERIFY, rather than reporting a pass. So it is not a false failure to work around —
  it is a check that has to run in CI, where the network is real. Font PAYLOAD figures
  can still be established out of band by fetching the css2 URL and summing the woff2
  responses (that is where #242's numbers came from); which FACE painted a given node
  cannot be, and needs the browser.

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
