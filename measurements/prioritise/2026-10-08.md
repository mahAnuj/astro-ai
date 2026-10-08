# /prioritise report — 2026-10-08, `origin/main` = `cdade53` (local main identical, clean, 0 ahead)

60 open issues (BACKLOG.md header said 29 at `b8e9936`; the scan before that, 36 at `c14093c`).
Produced by the project-manager agent. Read-only: nothing closed, nothing commented, BACKLOG.md untouched.

## Environment gaps — what limits these verdicts

| Gap | Effect |
|---|---|
| **Production WAS reachable** (curl to shubhagya.com works from this sandbox) | Several verdicts below are production-measured at 07:05-07:15 UTC 2026-10-08, revision `bhagya-00397-xkw`, `/health` `build_sha` = `9c99ca9` (non-null: the exact tier is live). Read-only GETs only. |
| **I refused to POST to production** | `POST /reading` relays name/DOB/place to Telegram and spends LLM quota. So **#266 (Kundli) was NOT re-probed.** The analyst did not probe it either. Its status is unmeasured. |
| `gh` authenticated as claude[bot], but **Actions API returns 403** | I could not read verify-production / agent-* run results or logs. #285's three failing runs unverified by me. |
| `.venv` present, `swisseph` imports | I ran `pytest`: **198 passed** (matches `EXPECTED_TESTS = 198`). Did not run the 20+ `verify_*` gates or the mutation harness this pass. |
| `data/` holds **1 book** (`vedic_astro_textbook.pdf`); `pdftotext` not installed | No corpus verdict in this report is corpus-measured. Anything about `data/matching/…` is read from SOURCES.md prose, not the file. |
| `/tmp/measure/report.md` present (2026-10-08, analyst) | **Cannot be used to rank — see #272 below. It is built on ~7-9% of the site's search data.** |
| `AGENT_STATUS.md` absent; no open PRs; no `issue/*` branch on origin | Nothing in flight in this checkout. Remote branches `claude/github-issues-prioritize-n12fv3`, `feat/124-hindi-url-prefix`, `fix/id-token-all-loops`, plus 4 abandoned August branches. |

## Deltas against BACKLOG.md (header `b8e9936`, 95 commits ago)

- **Open count 29 -> 60.** Closed since: #216, #218, #228 (all 08-30), #229. 34 issues new or reopened. 26 of the 29 old rows survive.
- **Diff of `b8e9936..origin/main`: 237 files** (218 outside `templates/learn/`). The big movers: the #233 redesign (09-02..09-04), #124 Hindi `/hi/` (09-20..10-06), the #266 natal compression (09-05), the agent-org plumbing (10-07..10-08).
- **Files NOT touched in that diff**: `matching.py`, `numerology.py`, `knowledge/*.md` (except `SOURCES.md`), `scripts/corpus_search.py`. So verdicts on #175, #177, #201, #151, #159, #140 are **carried unchecked** (their original `checked@` kept; I re-measured #163 only).
- **Verdicts that CHANGED:**
  - **#178** was "hold: 4a unverifiable from a clone". Now: scope empty. SOURCES.md :270/:307 documents the Raman *Muhurtha* restoration and its readings (round 3). **Propose close** (file itself not present here).
  - **#150** was "Q7: whole page missing". Now **half done**: moonrise/moonset is wired and rendered (`9710313`, `panchang.html:162-199`). Gulika is **sourced** (`81c3564`, SOURCES.md §28.2) but not rendered. Yamaganda and Brahma Muhurta are **0 hits in 4 books**, so they stay blocked. `panchang.html:278` still says "deferred to a next release". Retitle.
  - **#163** was "23/45 disagreements". **Re-measured now: 19/45, 1 friend<->enemy flip (1,8).** The issue title is stale; still a duplicate of #201.
  - **#184** was "stale pointers incl. `_HOMEPAGE_PANCHANG_CACHE`". That symbol is gone from the tree (fixed in `a7dd30b`), but **7 `main.py` pointers remain** (`notify.py:55`, `subscribers.py:51`, `learn_registry.py:9`, `i18n.py:8`, `daily_cache.py:8`, `adhik_maas.py:105`, `lunar_observances.py:139`). Still live, trivial.
  - **#212** was Q6. The change **is on `origin/main`** (`1c4ec5f` reachable) but the issue stays open on purpose: its live A/B was never run. Demoted to headroom-only.
  - **#209** was "rescope to moolatrikona". Confirmed: padas now computed (`chart.py:218`), `kundli_landing.html` pada claims now true; only `about.html:162` ("moolatrikona ... computed from first principles per BPHS") is false. `chart.py:1114` is a comment, not a computation.
  - **#124** was "not now". It **landed** (13 `/hi/` URLs, `3851506`). Open pending production verification; I verified part (below).
  - **#173, #172, #193, #214, #217-#228** from the old queue: all closed. Dropped from the index.
- **New since the last scan (34):** #230 #231 #232 #233 #242-#251 #253 #254 #255 #260 #262-#268 #270 #272 #276 #278 #279 #280 #282 #285 #286.

## Staleness sweep — close these (evidence)

| # | Verdict | Evidence | checked@ |
|---|---|---|---|
| **#280** agent-infra has no GCP auth, BUILD_SHA cannot be set | **Close — done.** | `curl /health` -> `{"build_sha":"9c99ca986834a456797f55aead5f353d447596fc"}` (was `null` when filed). CLAUDE.md records the trigger edit on 2026-10-08 (`31e25af`). `agent-infra.yml:44` now has `google-github-actions/auth`. The human did it by hand, as the issue's own thread proposed. | cdade53 |
| **#232** memoise the rashifal blast text | **Close — overtaken.** The code it describes does not exist on `main`. | `grep storage src/astro_ai/routes/rashifal.py` -> nothing; the route reads `daily_cache.get("rashifal_single", ...)` (:239), a per-instance file cache. `26a8f7a` and `bc34852` (the commits it cites) are **not on `origin/main`**. `storage.get` was last in that file at `db04fc5`. Fold its "cache lifecycle" caution into #268. | cdade53 |
| **#178** [BLOCKER] acquire Muhurtha + Lo Shu | **Close** (scope empty). Drop `[BLOCKER]` either way. | Items 1-3 struck, 4b dropped, 5 absorbed by #191 (thread). 4a: SOURCES.md :270, :307 record the Raman *Muhurtha* 1948 restore and that its reading "falsified three" earlier claims. **Caveat: `data/matching/` is not in this checkout; I read the registry, not the file.** | cdade53 `corpus-unverified` |
| **#163** numerology pair tables disagree | **Close as duplicate of #201** (still pending from the last scan). | Re-measured with `.venv`: `_pair_verdict` vs `_LP_DESTINY_*` over the 45 ordered pairs -> **19 disagree, 1 flip (1,8)**. Title's "23 of 45" and "3 unreachable rows" are stale. | cdade53 |
| **#185** route-table guard as gate | **Close as "no"** (still pending since 08-25). | `scripts/route_inventory.py` exists; no `routes.expected*` anywhere. Filer said closing "no" is fine. | cdade53 |
| **#282** BUILD_SHA + collapse duplicated checks | **Do not close; retitle.** Item 1 is done (see #280). Items 3-4 (drop 3 live assertions; split post-deploy / daily-health) are unstarted: `verify-production.yml` still has one `verify` job and the #172/#193/#216 steps. Item 2: the sweep already uses `xargs -P 6` / `-P 2`. Not urgent (430/2000 Actions minutes). | cdade53 |
| **#209** | **Retitle to moolatrikona only** (or close and refile as an XS `about.html` copy fix). | Above. | cdade53 |
| **#150** | **Retitle to "Gulikai / Yamaganda / Brahma Muhurta"**; moonrise half shipped. | Above. | cdade53 |
| **#124** | **Do NOT close yet** — see the queue note under #268. | | cdade53 |

## Queue (5-7 items, by user harm then unblocking power)

Measured today, so read these first.

**Production probes, 07:05-07:20 UTC (my own probes add some load; I stopped after ~12 requests):**
- `/rashifal` -> 200 in 2.1s. `/hi/rashifal` -> 200 in 0.6s.
- Cold per-rashi pages: `/rashifal/virgo` **503** x4 (19.7s, 34.7s, 4.7s, 19.7s), `/rashifal/aries` **503** (12.6s), `/rashifal/taurus` **503**, `/rashifal/leo` **503**, `/rashifal/pisces` **503**, `/hi/rashifal/aries` **503**. `/rashifal/gemini` **200** after 12.4s; `/hi/rashifal/virgo` 200 (first try timed out at 60s, then was cached).
- The 503 body is the "High demand right now" page (`AllProvidersExhausted`). So: **intermittent LLM-chain exhaustion on the indexed per-rashi pages, today, in front of readers and crawlers.**
- I could **not** determine the cause (TPD exhausted? blast not run today? stampede after today's ~6 deploys?). Needs Cloud Run logs.

### 1. #255 — privacy copy states eight things the code does not do  `priority:high`, `needs-human-review`
- **Broken:** live on production now. Confirmed by `curl`: `/privacy` still says to use the Feedback button and select "Delete my data" (`privacy.html:106`); `feedback.py:44` `VALID_TYPES = {"problem","feature","other"}` — **the option does not exist**. `/kundli` still says "Nothing stored on our servers unless you sign in" (`kundli_landing.html:37`) while `routes/kundli.py` relays name/DOB/time/place to Telegram (:269) and records them to GCS (:275). `dosha_check_form.html:81` and `account.html:14` likewise.
- **Why first:** it is *wrong in front of every anonymous visitor*, it is *silent* (nobody checks a privacy sentence), and a user who acts on the deletion promise gets nothing. The code itself (`events.py:29-32`, `notify.py:24-30`) carries a written instruction to update the policy that was never followed. Open since 09-02, 0 comments.
- **Blocks / blocked by:** blocked on a human decision *only* for "what should we store". **The disclosure half is unblocked today:** make the copy true (claims 1-5, 7, 8 by rewording; claim 3 by deleting the promise or adding the option). Also asks someone with console access to confirm `ASTRO_AI_COOKIE_SECRET` is set on Cloud Run (`session.py:44` fallback is a public constant) — I could not.
- **Size:** S (copy) + M (deletion path, `/account` export). **Loop:** `/bug` for the copy; hand the store-or-not decision to product-manager/human. **Gate:** yes — a test that fails if `privacy.html` names a feedback type not in `VALID_TYPES`.

### 2. #268 — rashi pages cold-generate in front of users, and the proposed fix as written will not work
- **Broken:** see probes above. Per-(rashi, lang, date) readings are generated on the first request. 12 en + 12 hi pages, ~3,330 input tokens each, against 2 x 8,000 TPM.
- **Why second:** not silent (users see a 503), but it is the highest-volume product page and **Googlebot is the first reader** of a Hindi surface that `#124` published this week; the 13 `/hi/` URLs are only worth indexing if they answer 200.
- **Correction to #268 before anyone builds it:** its fix is "have the warm job populate `rashifal_single`". But `daily_cache.py` is a **per-instance ephemeral file cache** (`daily_cache.py:1-20`, its own docstring: "cross-instance still relies on GCS"). `admin.py` has 0 references to `rashifal_single` (I confirmed). A warm POST lands on one instance of up to 5; every other instance, and **every redeploy**, starts cold. Today alone had ~6 deploys from agent-infra commits. A pre-warm that does not write a GCS tier is a no-op for most readers. Needs a GCS-backed tier with a miss-path read only (not a hot-path read — #144), plus the lifecycle rules in #232 (date-keyed expiry, bounded, `.pop(k, None)`).
- **Tokens:** ~78,300 input tokens/day (39% of the 200k TPD) just to hold both languages warm; re-measure against the combined blast, which also runs daily (#268's own caveat).
- **Related and blocked by this:** **#124** cannot be closed on its current evidence. I verified reciprocal `en-IN`/`hi-IN`/`x-default` + self-canonical on `/hi/rashifal`, and 13 `/hi/` entries in the sitemap; but `/hi/rashifal/aries` was 503. The last two commits on that branch (`1d9d7c6`, `3851506`) were never through QA (the issue says so itself).
- **Size:** M. **Loop:** `/feature` via architect first (cache tier), then `/bug`. **Gate:** yes, a measurement: cold-start 503 rate for 24 URLs after a forced redeploy, before and after.
- **Do first (XS):** read the Cloud Run logs for today's `AllProvidersExhausted` / TPD lines. That decides whether this is a quota problem or a cache problem. I cannot.

### 3. #272 — the objective is scored from ~9% of the data  (and the analyst's report is built on it)
- **Broken:** `fetch_gsc.py:43` asks only for `dimensions:["query"]`; Google withholds anonymised queries, so it reads **769 of 8,097 impressions (9%)**, then `:66` `rows[:100]` cuts to ~7%. Evidence is in the issue thread (owner's measurement, 2026-10-08, `dataState: final`, by-page = 101% of truth). I could not re-run it (no Google credentials) — **carried from the thread, not independently measured.**
- **Why third:** it is the gating issue for every SEO/conversion item. `/tmp/measure/report.md` concludes "0 of 10 band queries in the top 5" and "nothing can be said about movement" — **both are statements about 7% of the site.** That report must not be used to demote or promote anything. The page-level view the thread produced already shows what the query view hid: `/festivals` 773 impressions at pos 39.7 and 1 click; `/learn/rahu-mahadasha-career-problems/` 790 impressions, 2 clicks; `/learn/rahu-mahadasha-ketu-antardasha/` 934 impressions, 21 clicks, pos 7.5.
- **Blocks:** #267 (can't be decomposed honestly), #276 (can't be scored), every analyst post-ship score. **Blocked by:** nothing. **Not in flight:** no `issue/272-*` branch or PR exists on origin; three agent-work runs claimed to dispatch an engineer and left nothing (#285). Check that again before re-dispatching.
- **Size:** S. **Loop:** `/agent-cycle` (it is the loop's own tooling) or `/bug`. **Gate:** yes — the export must print `coverage_pct`; accept only if a query-only export says <100.

### 4. #266 — verify the Kundli fix on production, then close or escalate  (XS, but could outrank everything)
- **State:** the compression/413 handling is on `origin/main` (`94ff253`, `b158603`, `2772535`...), `natal.txt` 18,095 -> 13,135 B, 198 tests pass. The issue's own last comment: "QA-passed, ready" and notes **the live wire behaviour was never exercised** (no `GROQ_API_KEY` in that session). The analyst this week did not submit a chart either.
- **Why here:** `/kundli` is the acquisition funnel's core tool. If it still returns "high demand", it outranks #1. Today's rashi-page 503s say the LLM chain is under pressure *right now*, so this is not a safe assumption.
- **How:** needs an actor allowed to POST: `uv run python scripts/validate_issue.py 266 --samples 5` after adding a `repro:` line (the issue has none, so the script would answer NO-REPRO — per #281, "not checkable", not "fine"). I deliberately did not do it from here.
- **Loop:** none — a human or `agent-measure` with credentials. **Gate:** it *is* the gate.

### 5. #270 — Hindi rashifal readings contain English fragments  `severity:medium`
- **Broken:** `chart.py:3683 _RAHU_KAAL_BAND` is eight English strings handed to a Hindi prompt (:3735), so the model echoes "early afternoon". Found by `verify_hindi_surface.py` on first production run.
- **Why fifth:** it is on pages `#124` just made indexable, and it is the same bug class as the "6 of 12" defect already half-fixed. But **intermittent**: today's cached `/hi/rashifal/virgo` has 0 English fragments (0 hits for `early afternoon` / `Abhijit window`), so it does **not reproduce on that page now** — it is probabilistic, 1 of 12 at filing. Code cause unchanged, so I keep it.
- **Size:** S. **Loop:** `/bug`. **Gate:** `verify_hindi_surface.py` exists. Note the prompt change alters input tokens and the cache fingerprint; record tokens/call before and after (CLAUDE.md).
- **Do not run in the same window as #268** — both touch the rashifal generation path.

### 6. #209 (moolatrikona) + #265 (share card) — two advertised-but-not-true provenance claims  (XS each, one theme)
- **#209:** `about.html:162` says moolatrikona is "computed from first principles per BPHS". Never computed (`grep` shows only a comment at `chart.py:1114`). Remove the word or the claim. **#265:** `scripts/generate_og_card.py:49` bakes "Swiss Ephemeris chart math · 76 cited explainers" into `static/og/default.png`, the `og:image` of the homepage and all 76 articles; reaches **beyond the site** (every social preview), and the count is hardcoded. **Currently correct** (76 articles = 76), so the hardcode is latent; the "Swiss Ephemeris" badge is the already-ruled-on #234 shape.
- **Different files, no collision.** Regenerate and commit the PNG. **Loop:** `/bug`. **Gate:** #265 — read the count from `learn_registry` and add a stored-inputs check.

### 7. #278 + #286 — let the unattended loop finish work and check its own facts  (infra, XS-S)
- **#278:** verified by grep: `poppler-utils` is installed only in `pr-gates.yml:118` and `agent-research.yml:49`. `agent-work` and `agent-discover` run without `pdftotext`, so their QA cannot run `corpus_search.py` or `verify_rule_citations`, which `qa.md` requires. **#286:** `scripts/verify_issue_evidence.py` does not exist (confirmed), yet `/agent-cycle` calls it.
- **Why seventh:** unblocking power for the corpus-dependent items (#230, #194, anything astrological), not user harm. **Not queued:** #285 — `db4834c` (`agent-cycle.md:106` `run_in_background: false`) is the fix for it and is *unproven*; I could not read the runs. Do not touch #285 until the next `agent-work` run shows a branch.
- **Needs a PR with `workflows` scope**, which the agent job token lacks. **Loop:** human PR or `/agent-cycle`.

### Next after the queue (not in the top 7)
- **#276** (move a CTA above line 87 of the Rahu-Ketu article). The defect is as filed (`href="/dasha"` at :87 of 120, confirmed), template-only. But n = 29 sessions and the metric needs #272's channel dimension to be read honestly; and it **must not share a PR with the title/meta change** the issue itself names.
- **#150 remainder: Gulikai.** Sourced, unblocked, S. The one `/panchang` anga that can ship value now.
- **#230**: `natal.txt:65` still reads "fully manifested per Parashara" (verified); mitigated because `:56` tells the model not to name texts. No gate reads `prompts/*.txt`. S-M with a mutation.
- **#260** six shlokas in semibold sans (verified: `learn_article_base.html:378` still the sans face). Cosmetic. **#254** `prose` classes with no rules (`grep -c '\.prose' app.css` = 0, `plugins` absent). **#262** dead `rashifal.html` still present, 0 references. Needs a human choice (delete or revive) on each of these.

## Blocked list

| Issue | Waits on | What ships today |
|---|---|---|
| **#201** (+#163) | A directional 9x9 model | **On-page disclosure** that the two pages read Johari two ways. Carried unchecked from the last scan (numerology.py untouched). |
| **#219** combustion convention | A tradition ruling | State the convention; cite the `namkaran` waiver. `muhurat.py` has changed since the last scan (+45 lines) — **not re-read**, so even this row is carried. |
| **#150 remainder** | Yamaganda and Brahma Muhurta need *Muhurta Chintamani* (0 hits in 4 books) | **Gulikai now.** |
| **#255 store-or-not** | A human ruling | Copy fixes now (queue 1). |
| **#263** /ask citation line | Decide what a citation means; token re-measure | Nothing; a placeholder would be a fabricated citation. |
| **#264** /ask as a thread | Whether it is wanted at all; tokens | Nothing. |
| **#279** corpus books in CI | 4 owned books need a private-bucket upload and an IAM grant (human) | The 4 public books via `fetch_corpus.py --fetch`, after #278. |
| **#191** extract ~22k lines | The `data/` machine (Goodwin 28,171 lines) | n/a |
| **#124** | #268 (cold pages 503) and a native-speaker pass | n/a |
| **#285** | Proof from the next `agent-work` run | n/a |

## Explicitly NOT recommended

- **The redesign sub-issues #242-#251 and epic #233.** All were *reopened* 2026-09-04 for ~30 absent designed sections. Design/feature work, no user is lied to. Partial landings since: `619423d` (proportional Mahadasha timeline, motion 4), `6d0db0e` (mobile footer) — **so the "ABSENT" lists in those comments are partly stale**; they need re-auditing before anyone works from them. Not individually re-checked here.
- **#124 close / any Hindi expansion beyond 13 URLs.** The decision to publish 13, not ~200, is measured (83-98% textual identity otherwise). Don't re-open it.
- **#128 #129 #131 #114 #115 #198 #203** — features/design, unchanged verdict.
- **#200** — needs a ruling on Cheiro, as before.
- **#231 Cosmic Card SVG og:image** — real (`kundli_card.py:125` still `image/svg+xml`) but only affects a signed-in user sharing a snapshot.
- **#251 motion / #253 SW remainder / #282 items 3-4** — latent or housekeeping; #253's stylesheet half is fixed (`?v=` hash) and only icons/manifest remain.
- **Reading `/tmp/measure/report.md` as a mandate.** Its "0 of 10", its CTR comparisons and its "objective is one topic" are computed from the anonymised-query slice (#272).
- **Adding a Groq model to fix #268.** The thread measured the live catalogue: 3 usable text models, 3 x 8,000 TPM still cannot absorb 78,300 tokens in a burst.

## Full open-issue index (60)

`checked@` = SHA at which *this pass* verified the row. `—` = not individually re-verified this pass; original SHA kept in brackets where one existed.

| # | Title (short) | State | checked@ |
|---|---|---|---|
| 286 | verify_issue_evidence.py does not exist | **Q7** | cdade53 |
| 285 | agent-cycle engineer dispatch produces nothing in CI | fix landed (`db4834c`), unproven — hold | — (comments read; runs unreadable, 403) |
| 282 | Set BUILD_SHA, collapse duplicated prod checks | **retitle** (item 1 done; 3-4 open) — not urgent | cdade53 |
| 280 | agent-infra no GCP auth / BUILD_SHA | **propose close — done** | cdade53 |
| 279 | CI holds 1 of 8 corpus books | blocked (4 need human) | cdade53 (grep: no fetch step) |
| 278 | poppler missing in 6 workflows | **Q7** | cdade53 |
| 276 | Rahu-Ketu article CTA at line 87 of 120 | next after queue | cdade53 (line 87/120 confirmed) |
| 272 | GA4/GSC export: 9% of data, no channel/page | **Q3** | cdade53 (code lines :43 :66 :35 confirmed; the 9% figure is from the thread) |
| 270 | Hindi rashifal echoes English window text | **Q5** (intermittent) | cdade53 |
| 268 | Pre-warm rashifal_single | **Q2** (fix design corrected) | cdade53 |
| 267 | [SEO] optimise 6-20 band | umbrella; decompose after #272 | — |
| 266 | /kundli "high demand" 413 | **Q4** verify on prod | cdade53 (code on main; not probed) |
| 265 | og:image card bakes Swiss Ephemeris + count | **Q6** | cdade53 |
| 264 | /ask as a thread | blocked / not wanted-first | — |
| 263 | /ask citation line has no data | blocked | — |
| 262 | delete rashifal.html | needs human choice; file present, 0 refs | cdade53 |
| 260 | learn shlokas in semibold sans | live, cosmetic | cdade53 |
| 255 | Privacy copy: eight false claims | **Q1** | cdade53 (production curl) |
| 254 | `prose` classes never had rules | live, cosmetic | cdade53 |
| 253 | SW stale stylesheet | partly fixed (stylesheet); remainder latent | — (body/comment read; `sw.js:14` unchanged `bhagya-v3`) |
| 251 | Redesign: motion | reopened; partly overtaken (`619423d`) | — |
| 250 | Redesign: Learning Hub | reopened | — |
| 249 | Redesign: Vivah Muhurat | reopened | — |
| 248 | Redesign: Ask | reopened | — |
| 247 | Redesign: Numerology | reopened | — |
| 246 | Redesign: Kundli Matching | reopened | — |
| 245 | Redesign: Today + Panchang | reopened | — |
| 244 | Redesign: Daily Rashifal | reopened | — |
| 243 | Redesign: Kundli result | reopened; timeline landed `619423d` | — |
| 242 | Redesign: homepage | reopened; footer partly `6d0db0e` | — |
| 233 | Epic: visual redesign | reopened | — |
| 232 | memoise blast text | **propose close — overtaken** | cdade53 |
| 231 | Cosmic Card served as SVG | live, narrow audience | cdade53 |
| 230 | prompts assert sourced claims, no gate | live (`natal.txt:65`), next-after-queue | cdade53 |
| 219 | muhurat combustion convention | blocked (2 disclosures) | — [c14093c]; `muhurat.py` changed since, not re-read |
| 212 | rashifal prompt input +18.5%/call | change on main; live A/B outstanding; headroom only | cdade53 (reachability only) |
| 211 | rashifal readings differ by prompt; Gochara unused | live | cdade53 (0 "gochar" in `rashifal_single.txt`) |
| 209 | /kundli, /about advertise padas/moolatrikona/SwissEph | **retitle** to moolatrikona; **Q6** | cdade53 |
| 203 | [DESIGN] name numerology | not recommended now | — [c14093c] |
| 201 | directional 9x9 numerology model | blocked (value) | — [c14093c] (`numerology.py` untouched since `b8e9936`) |
| 200 | numerology copy names books | needs ruling | — [c14093c] |
| 198 | [DESIGN] mobile hero motion | not recommended now | — [c14093c] |
| 194 | nothing verifies quotation within cited range | live | cdade53 (grep of `verify_rule_citations.py`: no such check) |
| 191 | extract ~22k readable lines | blocked on `data/` machine | — [c14093c] |
| 185 | route-table guard as gate | **propose close as "no"** | cdade53 |
| 184 | post-#154 stale pointers + dead code | live (7 pointers remain; `_HOMEPAGE_PANCHANG_CACHE` one is fixed) | cdade53 |
| 178 | [BLOCKER] acquire Muhurtha + Lo Shu | **propose close** | cdade53 `corpus-unverified` |
| 177 | no Ashtakoot material in corpus | live; 3 gaps listed in thread | — |
| 175 | Vashya collapses 5x5 | live; rejected half awaits owner review | — |
| 163 | numerology pair tables disagree | **propose close as dup of #201** (now 19/45, 1 flip) | cdade53 |
| 159 | [FEATURE] local RAG index | keep open, deferred | — [c14093c] |
| 151 | knowledge/*.md has no Panchang-anga material | deferred; pair with #191 | — [c14093c] |
| 150 | /panchang omits Yamaganda/Gulikai/Brahma Muhurta | **retitle**; moonrise shipped; Gulikai next | cdade53 |
| 140 | [FEATURE] user profiling insights | live | — |
| 131 | [FEATURE] Kundli PDF | not recommended now | — [c14093c] |
| 129 | [FEATURE] Shodashvarga | not recommended now | — [c14093c] |
| 128 | [FEATURE] Ashtakvarga | not recommended now | — [c14093c] |
| 124 | [SEO] Hindi at /hi/ | landed; **do not close** (blocked on #268) | cdade53 (partial: hreflang + sitemap + 200 on index; 503 on a cold rashi page) |
| 115 | [FEATURE] 3D dasha helix | not recommended now | — [c14093c] |
| 114 | [FEATURE] WebGL mandala | not recommended now | — [c14093c] |

## What I could not determine

- **Why** the rashi pages 503 today (quota vs cache vs stampede) — needs Cloud Run logs.
- Whether **/kundli** works — would need a POST I declined to make.
- Whether the **three `agent-work` runs** failed for the reason #285 gives — Actions API 403.
- Any **GSC/GA4 number** independently — no Google credentials; #272's figures are the owner's, carried.
- Whether the **redesign "ABSENT" lists** are still true — not re-audited.
- Anything **corpus-measured** — 1 of 8 books present, no `pdftotext`.
