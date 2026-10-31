# /prioritise report - 2026-10-31

**Verified against** `origin/main` = `d66d59b` (fetched during the scan; it moved from `26e2119` by one commit, PR #550, which touches `.github/workflows/{pr-gates,main-red-report}.yml`, `ops_today.py` and tests - none of the files my per-issue checks read). Local `main` was clean and equal to `origin/main` at `26e2119`; my local tree stayed at `26e2119`, so `checked@` below says `26e2119` for tree checks, `prod 6d2f702` for production checks (`/health` `build_sha` = `6d2f702dabf3...`, revision `bhagya-00535-hld`), and `d66d59b` where I read the merged PR itself.
Read-only apart from the 7 closures and 3 comments listed below. `BACKLOG.md` not written. Nothing pushed.

**Which input I used.** `measurements/prioritise/latest.md` (2026-10-08, `cdade53`, 60 open) is newer than `BACKLOG.md` (header: last full scan 2026-08-25 at `c14093c`, closed out 2026-08-26 at `b8e9936`, 29 open). **I used `latest.md` as the cache and treated both as caches.** `/tmp/measure/report.md` does not exist in this run; the analyst's committed report `measurements/2026-10-31.md` (window 2026-10-01..10-28, GSC page dimension at 100% coverage, GA4 100%) stands in for it.

## Environment gaps - which verdicts are narrower than they look

| Gap | Effect |
|---|---|
| **Production reachable (GET only).** 20 URLs probed 19:33-19:55Z. **I did not POST** to production (it relays form data to Telegram and spends LLM quota). | `/kundli` POST path, `/ask`, `/matching` POST are unmeasured by me. |
| **`data/` absent; `pdftotext` not installed.** | No corpus verdict here is corpus-measured. Anything about the books is read from `knowledge/*.md` and issue threads. #178's closure is *proposed*, not executed, for this reason. |
| **`validate_issue.py` not run.** 0 of the open trusted issues I ranked has an executable `http` `repro:` (#543 says the same of the shell dialect: step 0 has run on 0 of 123). Per #281, NO-REPRO means "not checkable by HTTP probe". I established each premise by `grep` against the tree or a live GET and say which, row by row. | |
| **Full `pytest` and the mutation harness not run** this pass. I ran `verify_workflows.py` (PASS), `verify_prompt_contracts.py` (PASS), `tests/test_agent_merge_fork_guard.py` (18 passed), and `qa_verdict.sh --dry-run`. | |
| **Provenance:** `resolve_provenance.py` run on all 136 open issues (read-only, `--repo mahAnuj/astro-ai`): **94 trusted (exit 0), 42 outsider (exit 1), 0 unresolved (exit 2).** | The 42 outsiders are not ranked, not assessed and not closed by me; I have used none of their text. (Before I had resolved provenance I made one live GET for one outsider-filed claim; I have not used the result.) |
| `AGENT_STATUS.md` absent; 1 open PR (#544). `gh run list` worked (no 403 this time). | Nothing else in flight on this checkout. |

## The finding that changes how to read this backlog

**136 issues were open, not ~60.** And **42 of them are outsider-by-rule.** Every `app/claude`-authored issue is `is_bot=true`, so every one of them - the discovery loop's SEO, UI-audit, content and measurement issues, plus the steward's and infra-lead's infra findings - cannot enter this queue until the owner re-files it or applies `provenance:trusted` as a human. That is the policy working as written, and it also means the loop's own findings are un-workable by the loop. Whether any is worth re-filing is #367's job, not this scan's; the numbers are in the index (rows say "outsider-by-rule"). The 42: 278 279 291 308 309 310 340 341 366 379 380 381 382 392 426 444 457 485 490 502 503 508 528 553 557 560 567 568 570 580 581 582 583 584 593 594 595 596 597 605 610 616.

## Deltas against the prior scans

- **Open count:** 29 (`b8e9936`, BACKLOG.md) -> 60 (`cdade53`, latest.md) -> **136 at start of this scan -> 129 after 7 closures.** 48 of latest.md's 60 were still open at the start; **88 are new since 2026-10-08** (84 still open after my closures).
- **Closed since 2026-10-08, by others (12 of latest.md's 60):** #191 #253 #255 #260 #266 #268 #270 #272 #276 #280 #285 #286. Every item in latest.md's queue is therefore gone or changed: Q1 #255 (closed 10-13), Q2 #268 (10-09), Q3 #272 (10-08), Q4 #266 (10-21), Q5 #270 (10-08), Q6 #209 (partial; moolatrikona fixed, #265 still open), Q7 #278 (outsider now) and #286 (closed 10-13).
- **latest.md's pending closure proposals:** #280 closed by others; #232 and #163 **closed by me now**; #178 and #185 still pending (see below); #282 not closed (item 1 verified done in production, items 3-4 optional); #150 and #209 retitles never done.
- **Carried forward unchecked (original verdict kept, em-dash `checked@`):** 65 of the 87 trusted rows, marked `—` in the index. I did not re-read the source for them. They include #114 #115 #128 #129 #131 #140 #150 #151 #159 #175 #194 #198 #201 #203 #212 #219 #231 #233 #242-#251 #254 #263 #264 #265 #267 and the loop-hardening rows.
- **Verdicts that CHANGED this pass:**
  - **#124** (latest.md: "do not close, blocked on #268"): #268 is closed and I verified the shipped scope on production (below). Now **propose-close on shipped scope**.
  - **#211** (latest.md: "live, 0 gochar in the prompt"): the Gochara verdict is now computed (`3101663`, `2db70ab`, #524) and the page shows "Today's Gochara 2/9" and per-area ratings. Largely shipped; keep open for the owner to confirm, close next pass.
  - **#209**: the `about.html` moolatrikona claim is gone (`grep -ci moolatrikona src/astro_ai/templates/about.html` = 0; live `/kundli` = 0 hits). Remainder is the "Swiss Ephemeris"/Moshier label, a human decision.
  - **#177**: its title says the engine is untraceable; the 2026-10-17 audit in its own thread found the engine sourced and the **verdict bands unsourced**. It is now ranked for that residue (Q2), not for its title.
  - **#230, #232, #163**: closed (below). **#461**: fixed by PR #550 merged 19:39Z today.

## Closures made this pass (7)

All trusted-provenance issues; each comment carries the command, its output and the SHA. Re-check any of them from the issue thread.

| # | Kind | Evidence (short) |
|---|---|---|
| **#230** prompts assert sourced claims, no gate sees them | already fixed | `grep -iE "fully manifested|per Parashara" prompts/natal.txt` = nothing (was `:95`); the only attributive lines in `prompts/*.txt` are two *prohibitions* (`ask.txt:22`, `natal.txt:56`); `verify_natal_prompt.py` + `mutate_natal_prompt_gate.py` family I (`per Parashara` and ~12 variants) and `verify_prompt_contracts.py` -> `PASS - 10 asserted`. |
| **#232** memoise the blast text | overtaken | `grep storage routes/rashifal.py` = nothing; `rashifal_derive.derive_single_reading` (`:102-135`) reads tier-0 `daily_cache` first, GCS only on a miss, then `put`s. Prod: `/rashifal/leo` 6.27 s cold then 0.51 s. Residual (concurrent cold reads) stated as unverified. |
| **#357** `agent-merge` edge-only, strands PRs | already fixed | `agent-merge.yml:60-62` `workflow_run: ["PR gates","verify-build"]`; `:106-108` `cron "*/30 * * * *"`; sweep in `4d9f51a` #359, `a2442b7` #378, `233440f` #563. |
| **#358** fork branch name interpolated into `run:` | already fixed | no PR-controlled `${{ }}` in any `run:` (hits are `env:` only); `agent-merge.yml:150-160` same-repo guard; `tests/test_agent_merge_fork_guard.py` 18 passed; `verify_workflows.py` PASS incl. check 5 `run:`-interpolation over 17 workflows. |
| **#406** `qa-fail` is write-only | already fixed | `scripts/qa_verdict.sh:138-159` PASS drops `qa-fail`, SHA-bound (exit 3); **executed:** `qa_verdict.sh --pr 544 --verdict PASS --dry-run` on a PR carrying `qa-fail` prints `--remove-label qa-fail`. `detect_stalls.py` emits `qa-fail-refixed`. |
| **#407** `verify_hindi_surface` PASSes against a 500 server | already fixed | **executed:** a local server answering 500 to everything -> `COULD NOT VERIFY: ... /health answered 500`, `rc=2`. Code `verify_hindi_surface.py:240-260`. Follow-up gaps are #433. |
| **#163** two numerology tables disagree | duplicate/subsumed (survivor **#201**) | determinate parts done 08-15/16; re-measured **19 of 45** still disagree, identical to 10-08 and to #201's directional-model scope. |

Comments (no close) on **#604** (the ranking reasoning) and **#124** (production verification).

## The queue (6 items, ranked by user harm, then unblocking power)

**No trusted, open, un-in-flight issue is verified wrong in front of a user right now** - I looked (rashifal pages, /matching, /numerology, /about, /kundli, /hi/*, /privacy all 200 and consistent with their issues' remaining scope). So the ranking is by silence and reach, and three of six items are one human hand away because they edit `.github/workflows/**` (the loop's App token has no `workflows` permission, so these ship as human PRs, as #359 did).

**Traffic context (analyst 2026-10-31, W = 10-01..10-28):** 14,625 impressions, 158 clicks, 456 GA4 sessions; 87% of impressions at position 6-20; none of the ten biggest pages in the top 5. **`/matching` is the one top-5 page (pos 4.4, 346 impressions)** - which is why Q2 is on it. The #311 title/meta change measured 0.721% CTR against a predicted >= 1.5% (MISS); #276 and #329 are INCONCLUSIVE at 30 and 5 organic sessions. **At this traffic, no ship is scoreable within a window, so prefer correctness and honesty over anything whose only justification is a CTR delta.**

### 1. #604 - `needs-human-review` does not hold a PR on edge-triggered runs
- **Broken:** verified in source. `agent-merge.yml` reads the label only at `:299` (sweep filter); the `qa` step (`:524-534`) matches only `qa-fail`/`qa-pass`; the comment at `:402` claims "the sweep filter and the labels step both refuse" - there is no labels step. `CLAUDE.md` repeats the claim.
- **Why here:** the one documented human hold is silently ignored on two of three triggers, on a site where a merge is a production deploy with no staging. Silent, and an agent-facing instruction is false. Trust-boundary paths stay separately held (`boundary` step), which bounds it. Covers the undone `agent-merge` item of #361.
- **Blocks/blocked by:** nothing. **Size:** XS-S. **Loop:** human PR (workflow file; trust boundary). **Gate: yes** - a test feeding the `qa` step `needs-human-review,qa-pass` expecting refusal, a mutation row, `verify_workflows.py` green.

### 2. #177 (split) - the Uttam/Madhyam/Avara verdict bands, and Bhakoot 5/9, are unsourced and presented as findings
- **Broken:** `matching.py:391 _overall_verdict` thresholds (>=30 / >=24 / >=18) and `matching.py:781 _BHAKOOT_DOSHA_NAMES` (5/9 scored 0/7) have no source in the 13-book corpus per the 2026-10-17 `astro-auditor` re-audit in #177's thread (`corpus_search.py --absent` on `uttam`, `madhyam`, `avara`, `nava panchama`: 0 hits; **I did not re-run it, `data/` is absent**). The code lines I did re-confirm. The page shows "Good compatibility (Madhyam)" and a 18/24/30 legend with no editorial disclosure.
- **Why here:** it is on the only page ranking in the top 5, it is a confident verdict number nobody checks (silent), and the identical defect class on the Manglik ladder was fixed by *disclosure* two days ago (#429: `fa36687`, `6d2f702`) - so the pattern and the wording precedent exist. **I am not claiming the values are wrong**, only unsourced; the auditor says "correct value unknown".
- **Unblocked disclosure fix:** state that the bands and the 5/9 handling are Bhagya's editorial rule, as the Manglik sentence does. No source needed.
- **Blocked by:** the owner splitting #177 (its title and body are half-refuted; a cycle reading it as filed will chase the wrong half). **Size:** S. **Loop:** `/bug` after a human retitle. **Gate:** yes - `verify_*` that the disclosure string is on the rendered result, with a mutation.

### 3. #618 + #423 - one PR to `verify-production.yml`
- **#618:** `verify-production.yml:596` POSTs `/numerology` (`name=CI Check`) and `:721` POSTs `/reading`, each firing the owner's Telegram alert; 4-6 identical alerts a day per the issue's run count (I read the lines; I did not count the runs). **#423:** `verify_hindi_surface` and `verify_english_surface` are excluded from `pr-gates` (`:290 NEEDS_LIVE_LLM`) and `verify-production.yml` never references either (`grep -rn verify_hindi_surface .github` -> the exclusion line only), so the 13 `/hi/` URLs #124 published are verified nowhere automatically.
- **Why here:** reaches beyond the site (the owner's alert channel trains the owner to ignore it on the day something real breaks) and an unguarded SEO surface. **Same file, one PR.** Both are silent.
- **Size:** S. **Loop:** human PR (workflow). **Gate:** yes - assert the probes carry whatever suppression marker the app honours (this touches `notify.py`, also trust-boundary); #423's gate must be mutated to prove it goes red on a 500, which #407's fix now does.

### 4. #513 remainder + #514 audit - the daily rashifal email
- **State:** the structural fixes shipped (`2db70ab`; Chandra Bala and per-area ratings are on the live page). Left: the undated email subject (`routes/subscribe.py:763`, still `"Today's Rashifal — Shubh Bhagya"`, I grepped it), and #514's lucky-colour half (not visible on the page; unverified).
- **Why here:** email persists and is harder to retract than a page; this is the highest-volume product output and the owner's own complaint. But the harm is dullness, not falsehood.
- **Blocked by one human line:** the 2026-10-24 cycle declined the subject slice because `metric:` has no number (`verify_issue_evidence.py`). Give it one (for example distinct subjects over N consecutive sends == N). **Size:** XS. **Loop:** `/bug`. **Gate:** a test on the subject builder.

### 5. #518 - slice 3: route the remaining dead-end `/learn` articles to a tool
- **State:** two slices shipped (`a9fc25f`, `f2c2104`). `/learn` is 58% of sessions at 1.34 pages/session (analyst). Template-only, no tokens.
- **Why fifth, not higher:** the analyst could not score the earlier slices (#276 1.17 vs >= 1.20 on 30 sessions; #329 on 5). Ship it because it is cheap and correct, **not** because a window will show it worked; do not spend more on measurement infra for it.
- **Size:** S. **Loop:** `/feature`/cycle slice. **Gate:** the existing first-screen-link check, extended.

### 6. #413 + #602 - one PR to `agent-work.yml`
- **#413:** `if: failure()` at `agent-work.yml:217` means a cycle that exits 0 out of turns reports nothing (still true at that line; `qa-on-green` and the steward are partial nets). **#602:** an empty `$sha` makes `gh api ...?head_sha=` return every run, suppressing the #322 rescue (LOW, latent; read from the issue, **not re-verified**).
- **Why last:** loop-internal, mitigated, latent. **Size:** S. **Loop:** human PR (workflow). **Gate:** `verify_workflows.py` + a test.

## Blocked list

| Issue | Waits on | What ships today |
|---|---|---|
| **#402** the most common /ask questions (studies, career, relationships, money) answered from model recall | Arudha/D-24 extraction from Rao on a `data/` machine; #399 runtime loader (no prompt growth: `ask.txt` is 1,251 tokens, #266 was a 413); corpus in CI (#279, outsider) | **Unblocked disclosure half:** state on `/ask` for these four areas that the answer is not rule-sourced. Needs the owner to say whether that is wanted. AC1/AC3 stay blocked. |
| **#475** token-bucket pacing | Phase 1b verdict `PENDING`: needs production days of measurement | Nothing; phases 0-3 are shipped |
| **#201** (now also #163's survivor) | A directional 9x9 numerology model | On-page disclosure that the two pages read Johari two ways (carried, unchecked) |
| **#209** remainder | Human ruling on the "Swiss Ephemeris" label (Moshier mode) | n/a - ruled shape |
| **#219** combustion convention | A tradition ruling | State the convention (carried, unchecked) |
| **#175** Vashya 5x5 | A second edition of Muhurta Chintamani to collate (acquisition) | Half-sign splits shipped |
| **#461** | `close-on-evidence` (PR #550 merged 19:39Z; touches `src/` so `verify-production` will run) | Do not close by hand |
| **#543** | PR #544 (draft, `qa-fail`) | n/a |
| **#124** | Owner decision to close on shipped scope; the traffic thesis is unscored until ~2026-11-04 | n/a |

## Stale-but-NOT-closed (propose; I did not close because I could not prove it, or the kind does not apply)

| # | Proposal | Why not closed |
|---|---|---|
| **#124** | Close on shipped scope | Scope narrowed on purpose (13 URLs, not the top-10 pages); "partial work does not close". Production-verified and commented. |
| **#178** [BLOCKER] Muhurtha + Lo Shu | Close, drop `[BLOCKER]` | `SOURCES.md :330/:387` record the restore, but `data/` is absent here, so I read the registry and not the file (`corpus-unverified`). Pending since 08-25. |
| **#185** route-table gate | Close as "no" | An owner decision (the owner's 08-26 comment argued the other way); not one of my four kinds. |
| **#211** | Close next pass | Largely shipped and live; scope confirmation is the owner's. |
| **#282** | Retitle; close as "no" on items 3-4 | Item 1 verified (`/health` live). Items 3-4 unstarted. |
| **#209 / #150** | Retitle to the remainder | Never done since 10-08. |

## Explicitly NOT recommended

- **The 42 outsider issues.** Not ranked, not assessed. Re-file or label as a human if one matters; #367 owns the triage.
- **#543 / #461 / #475** - in flight, merged-awaiting-close, or waiting on data respectively.
- **#365** third-party PR security reviewer: 0 forks (`gh api repos/mahAnuj/astro-ai` -> `forks=0`), public repo. Latent.
- **#354, #361, #367** security/provenance umbrella: partial work shipped; the one live residue is #604 (Q1).
- **#431 #432 #433 #462 #463 #464 #466 #467 #577 #385 #386 #390 #391 #317 #327 #350 #351 #446 #447 #453 #456 #459 #460** - latent hardening or measurement; the issues themselves say "not urgent" or "latent". Revisit only if a defect they describe bites.
- **#233 and #242-#251 (redesign), #114 #115 #128 #129 #131 #198 #203** - design/feature; no user is lied to.
- **#399 (retrieval) and #159 (RAG)** - architecture; only worth starting as the unblocker for #402, and not before the owner wants it.
- **Reading the analyst's #311 MISS as a mandate to rewrite more titles.** One page reached 1.5%; at 3,606 impressions and 26 clicks the data cannot discriminate between a bad title and no effect.
- **Any SEO/CTR-motivated item scored by window.** #490/#570 (outsider) describe the measurement gap; nothing in a 28-day window at 456 sessions can score a page-level ship.

## What I could not determine

- Whether `/kundli` POST, `/ask` and `/matching` POST work on production (no POSTs made).
- Any corpus absence (no `data/`, no `pdftotext`).
- The rashifal email's current repetition (needs the GCS blobs, no credentials here).
- #602 (SHA-guard defect) and the run counts in #618: read from the issues, not re-measured.
- Whether the 65 carried-forward trusted rows still hold: not re-read.
- The cron-lag claim in #357's closure comes from the workflow's own comment (71 runs), not from my measurement.

## Full open-issue index (129 open after closures; 136 at start)

`checked@`: the SHA at which *this pass* verified the row (`26e2119` tree, `prod 6d2f702` production, `d66d59b` merged PR read). `—` = not individually re-verified this pass.

| # | Title (short) | State in this scan | checked@ |
|---|---|---|---|
| 114 | [FEATURE] Interactive 3D birth chart — WebGL mandala with bandwidth-adaptive f | not recommended now (feature/design; unchanged verdict) | — |
| 115 | [FEATURE] Timeline Lotus — Vimshottari Dasha as scrubbable 3D helix, bandwidth | not recommended now (feature/design; unchanged verdict) | — |
| 124 | [SEO] Move Hindi from client-side toggle to /hi/... URLs with hreflang | **propose-close on shipped scope** (commented; production-verified, scope deliberately narrowed so not closed by me) | prod 6d2f702 |
| 128 | [FEATURE] Add Ashtakvarga calculator — competitor gap | not recommended now (feature/design; unchanged verdict) | — |
| 129 | [FEATURE] Add Shodashvarga divisional charts (D-1 to D-60) | not recommended now (feature/design; unchanged verdict) | — |
| 131 | [FEATURE] PDF download of Kundli — matchmaking use case gap | not recommended now (feature/design; unchanged verdict) | — |
| 140 | [FEATURE] User profiling insights — audience shape from birth details + questi | partially shipped (`intents.py` inert per 08-07 audit); not queued | — |
| 150 | [BUG] /panchang still omits Yamaganda, Gulikai, Brahma Muhurta and moonrise/mo | carried forward; not queued | — |
| 151 | [BUG] knowledge/*.md has no Panchang-anga material — astrological claims on /p | carried forward; not queued | — |
| 159 | [FEATURE] Local RAG index over knowledge/*.md + data/ books for citation-beari | carried forward; not queued | — |
| 175 | matching: Vashya koota collapses the 5x5 matrix to 3 tiers and ignores the hal | carried forward; not queued | — |
| 177 | knowledge: no Ashtakoot Guna Milan material in the corpus or in data/ — the en | **Q2** (owner retitle/split first; body half-refuted) | 26e2119 |
| 178 | [BLOCKER] Ashtakoota + Lo Shu + Rudraksha rules have no source in repo — acqui | **propose-close** (scope empty; SOURCES.md :330/:387 record the Muhurtha restore) - `corpus-unverified`, `data/` absent | 26e2119 |
| 184 | [CHORE] Post-#154 cleanup: stale main.py doc pointers + dead code | live, trivial: 7 stale `main.py` pointers remain | 26e2119 |
| 185 | [CHORE] Decide whether the #154 route-table guard should become a permanent ga | owner decision (route-table gate); recommend close as "no"; not queued | 26e2119 |
| 194 | [TASK] Nothing verifies that a cited quotation appears within its cited line r | carried forward; not queued | — |
| 198 | [DESIGN] Mobile hero has no motion — and after #195 the sample chart now costs | not recommended now (feature/design; unchanged verdict) | — |
| 200 | numerology: user-facing copy names books and authors throughout, against CLAUD | remainder deliberate (SEO titles allowlisted; i18n history). Live /numerology still names Cheiro 9x in title/meta. Keep; owner call | 26e2119 |
| 201 | numerology: resolving #163's 23 pair disagreements needs a directional 9x9 mod | carried forward; not queued | — |
| 203 | [DESIGN] Name numerology: build a "Your Name" section inside the /numerology r | not recommended now (feature/design; unchanged verdict) | — |
| 209 | kundli: /kundli landing and /about advertise nakshatra padas, moolatrikona and | remainder = "Swiss Ephemeris" vs Moshier label: human decision. moolatrikona claim is gone (`grep -ci moolatrikona about.html` = 0, /kundli live = 0) | 26e2119 |
| 211 | rashifal: the 12 daily readings differ because the prompt says to, not because | largely shipped (3101663 Moon-keyed Gochara; per-area ratings live); keep open until owner confirms scope - candidate to close next pass | 26e2119 |
| 212 | rashifal: prompt input grew 18.5%/call on the path that caused the 21-day outa | carried forward; not queued | — |
| 219 | muhurat combustion: degree-orb model vs the days-from-heliacal model, and two  | carried forward; not queued | — |
| 231 | Cosmic Card is served as SVG, so snapshot og:image previews fail on every majo | live, narrow audience (signed-in snapshot share); not queued | — |
| 233 | Epic: visual redesign — modern devotional identity (desktop + mobile) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 242 | Redesign: homepage (index.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 243 | Redesign: Kundli result (result.html, _south_indian_chart.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 244 | Redesign: Daily Rashifal — highest silent-breakage risk in the epic | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 245 | Redesign: Today + Panchang (today.html, panchang.html, _panchang_strip.html, _ | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 246 | Redesign: Kundli Matching (matching.html, matching_result.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 247 | Redesign: Numerology (numerology.html) — two gates and production CI grep this | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 248 | Redesign: Ask (ask.html, _ask_cta.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 249 | Redesign: Vivah Muhurat (muhurat_finder.html, muhurat_landing.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 250 | Redesign: Learning Hub — 2 files, 76 articles, and one gate that hates reflowi | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 251 | Redesign: motion — chart cast, dasha bars, hero glow, nav condense | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) | — |
| 254 | Six pages use `prose` classes that have never had any rules — the typography p | carried forward; not queued | — |
| 262 | Delete rashifal.html — 246 lines of dead code, now the only purple file left | live chore: `templates/rashifal.html` present; only i18n comments reference it | 26e2119 |
| 263 | /ask: the citation line the design wants has no data behind it | carried forward; not queued | — |
| 264 | /ask as a thread: the design shows multi-turn, the app has no conversation his | carried forward; not queued | — |
| 265 | The og:image card bakes "Swiss Ephemeris" and a hardcoded explainer count into | carried forward; not queued | — |
| 267 | [SEO] Organic traction is real and unpromoted — optimise the 6–20 band before  | carried forward; not queued | — |
| 278 | [INFRA] agent-discover/agent-work (and 4 more workflows) never install poppler | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 279 | [INFRA] CI holds 1 of 8 registered corpus books and nothing fetches the rest — | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 282 | [INFRA] Set BUILD_SHA on the Cloud Build trigger, then collapse the duplicated | item 1 done (/health `build_sha` live = 6d2f702); items 3-4 optional - retitle or close as "no" | prod 6d2f702 |
| 291 | Workflow prompts still label GSC pages as 'queries' and GA4 row count as 'land | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 308 | [UI] Mobile feedback FAB sits on top of reading text on result and form pages | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 309 | [UI] Subscribe modal fires over the empty form on the second tool page a visit | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 310 | [UI] PWA install banner covers the primary CTA on the first fold, mobile and d | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 317 | [INFRA] Harden verify_workflows.py: two missing checks and a heredoc false pos | latent loop/gate hardening; not queued | — |
| 327 | [INFRA] Nothing checks the AI output against the prompt's own rules, so a mode | latent loop/gate hardening; not queued | — |
| 335 | [INFRA] Nothing shows whether the agent team is working, failing or costing to | 7 of 8 acceptance criteria met per 10-21 comment; not queued | — |
| 340 | [INFRA] The exact tier is live, but the tree still says it never ran - and pri | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 341 | [INFRA] verify-production's exact deploy gate waits 12 min for a SHA that may  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 350 | [INFRA] Provider headroom is unmeasurable: llm_stats is per-day against a per- | latent loop/gate hardening; not queued | — |
| 351 | [INFRA] GCP spend is unreadable without a billing export, but free-tier headro | latent loop/gate hardening; not queued | — |
| 354 | security: the repo is public and the loop auto-merges — nothing gates the syst | partial; owner superseded by #361/#362; keep open | — |
| 361 | security: the loop acts on any issue from anyone, and strictness should key on | partial; its remaining agent-merge hold item is #604 (Q1); keep open | — |
| 365 | A third-party PR gets CI and nothing else — no agent reviews it, and there is  | not recommended now: repo has 0 forks (API, 2026-10-31) | 2026-10-31 API |
| 366 | [UI] Sub-12px text remains on / (24 nodes), /panchang (9) and 16 other templat | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 367 | Triage an outsider's issue automatically: ask for what is missing, or recommen | partial (stage 1 shipped, `qa-fail` label); not queued | — |
| 379 | [UI] PWA install banner: the Install button sits under the mobile tab bar — un | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 380 | [UI] Birth-chart labels render at 6.5–8.3px on mobile (/kundli, /matching) — t | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 381 | [UI] Install/favicon icons are still the retired purple — #233 moved the site  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 382 | [UI] Subscribe modal covers the /matching and /numerology result on a first vi | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 385 | verify_no_relaxation floors catch DELETION of a policy phrase, not SOFTENING B | latent loop/gate hardening; not queued | — |
| 386 | verify_no_relaxation's phrase check reads HEAD, so a local run reports a floor | latent loop/gate hardening; not queued | — |
| 390 | _walk's non-greedy extraction can lift an unterminated fragment, and two negat | latent loop/gate hardening; not queued | — |
| 391 | The sweep believes a gh that prints a value and then exits non-zero | latent loop/gate hardening; not queued | — |
| 392 | [INFRA] detect_stalls cannot name the owner of a partial/* PR, and reports hum | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 399 | architecture: knowledge/ ships in the image but no runtime code ever reads it  | carried forward; not queued | — |
| 402 | ask: the four life areas users actually ask about — studies, career, relations | blocked: needs Arudha/D-24 extraction + #399 loader + corpus in CI (#279); see Blocked | 26e2119 |
| 403 | agent-merge: a conflicting PR is now skipped silently — report the conflict an | loop-meta; no PR-visible conflict report in agent-merge.yml (steward routes via merge_main_into_branch.py); not queued | 26e2119 |
| 413 | agent-work.yml cannot report a cycle that stops after the engineer: the comple | **Q6** (bundle with #602: one PR to agent-work.yml) | 26e2119 (`if: failure()` still at :217 only) |
| 423 | verify_hindi_surface and verify_english_surface run nowhere — excluded from pr | **Q3** (bundle with #618) | 26e2119 |
| 426 | [CONTENT] Saturn's exit from Pisces is stated as 'early 2027' / 'late Feb 2027 | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 429 | chart: the Manglik severity ladder is UNSOURCED, and its "1st house = moderate | partial: disclosure shipped (fa36687, 6d2f702); remainder is a source decision - not queued | — |
| 431 | prefix_cache rows have no schema version, so adding a ninth counter would eras | latent loop/gate hardening; not queued | — |
| 432 | One Effective prefix-cache figure spans two models' caches, and CACHE_REPORTIN | latent loop/gate hardening; not queued | — |
| 433 | verify_hindi_surface: eight guard gaps from QA round 1 on #424 (five live muta | latent loop/gate hardening; not queued | — |
| 444 | [INFRA] Loop outcome report (weekly) | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 446 | repo: #405 parts 2-4 are undone and untracked — the test floor and mutation ta | partial slice merged (#548); loop-meta; not queued | — |
| 447 | close-on-evidence: an issue closed with three of four parts undone — the three | latent loop/gate hardening; not queued | — |
| 453 | The loop can only address work by issue number, so any PR not on an issue/* br | latent loop/gate hardening; not queued | — |
| 456 | needs-human-review can be applied with no stated reason, which makes the merge | latent loop/gate hardening; not queued | — |
| 457 | detect_stalls: steward-ineffective and 'CONFLICTING for Nh' use PR age, not st | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 459 | Squash merge leaves a branch looking unmerged: phantom PRs for shipped work, a | latent loop/gate hardening; not queued | — |
| 460 | resolve_union corrupts a mutation row when the conflict is intra-row, and only | latent loop/gate hardening; not queued | — |
| 461 | pr-gates never runs on main, so a red main is invisible — two independently-gr | fix MERGED (PR #550 at d66d59b, 19:39Z); awaiting close-on-evidence - do not close | d66d59b |
| 462 | Three MIS-POINTED mutation rows, and the 0.2s static check that would have cau | latent loop/gate hardening; not queued | — |
| 463 | No gate measures seo_description length — 8 of 38 exceed 160 chars decoded, up | latent loop/gate hardening; not queued | — |
| 464 | Gate 7 cannot catch an FAQ naming a practice its page lacks — QA pasted the fi | latent loop/gate hardening; not queued | — |
| 466 | ARCHITECTURE.md holds four successive revisions of one decision-log row as fou | latent loop/gate hardening; not queued | — |
| 467 | Gate 7 is literal-bound: QA measured 18 of 20 plausible rewrites escaping, and | latent loop/gate hardening; not queued | — |
| 475 | Pace LLM calls against a per-model token bucket so a 429_tpm is a short wait,  | blocked on data: Phases 0-3 shipped, Phase 1b verdict PENDING (needs production days) | — |
| 485 | detect_stalls: partial/* PRs are reported as mergeable-but-open forever, thoug | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 490 | [MEASURE] No per-page x per-day export, so no page-level ship can be scored be | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 502 | detect_stalls/agent-cycle read QA verdict time from the qa-fail label event, w | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 503 | stall routing: no independent-QA path for human-authored partial/ PRs, guard 2 | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 508 | [SEO] /matching ranks 4.3 on 336 impressions and got 0 clicks — title/meta tes | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 513 | Daily rashifal email repeats its opening every day — the per-rashi opening_sty | **Q4** (remainder: undated subject line; metric needs a number) | 26e2119 |
| 514 | Rashifal layout: move the fixed furniture out of the prose into computed field | **Q4** audit (Chandra Bala shipped and live; day-colour half unverified) | 26e2119 (tree) / prod 6d2f702 |
| 518 | Learn articles are 56% of sessions and 71% have no route to a tool — the media | **Q5** (slice 3; two slices shipped, effect not yet measurable) | — |
| 523 | Per-area day ratings from Gochara karakas — Work / Money / Relationships / Hea | partial slice merged (#524); per-area ratings live (Gochara 2/9 on /rashifal/aries); remainder not queued | prod 6d2f702 |
| 528 | privacy: the visitor's /ask question travels in the URL and is recorded by GA4 | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 543 | Nothing executes the shell `repro:` dialect, so step 0's probe has run on 0 of | in flight: PR #544 (draft, `qa-fail`) - do not queue | 26e2119 |
| 553 | [CONTENT] /learn/panch-mahapurush-yoga/ tells readers Kundali Matching compare | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 557 | publish_measurements.sh: one GraphQL error enabling auto-merge strands the mea | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 560 | qa-on-green writes its 'dispatched at <sha>' marker before the dispatch, so a  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 567 | [INFRA] rashifal-generate's 3 h margin to the Groq fallback is smaller than Gi | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 568 | [INFRA] agent-infra authenticates as agent-analytics, which holds no Cloud Bui | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 570 | [MEASURE] No event records a click on an in-article tool link, so #276, #329 a | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 577 | verify_conflict_markers: the 8 MiB truncation and the 7-wide blockquote are ab | latent loop/gate hardening; not queued | — |
| 580 | [INFRA] detect_stalls counts stalls no cycle can act on as OBLIGED, so the ste | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 581 | numerology: name compound sums every letter; Cheiro adds each word's single nu | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 582 | numerology: master numbers and Karmic Debt contradict the page's own Cheiro co | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 583 | numerology: Life Path 'Strong/Cautious months' for 2-9 trace to nothing in the | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 584 | numerology: 0-100 compatibility and Bhagya scores rest on invented weights, an | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 593 | [BUG] /panchang shows yesterday's date, weekday and tithi from 00:00 to 05:30  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 594 | [UI] Top /learn landing article uses the raw path "/dasha" as link text | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 595 | [UI] /numerology result: 38 text nodes under 12px, down to 9px on the Lo Shu g | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 596 | [UI] Six form controls (subscribe modal, feedback widget, /learn search) have  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 597 | [UI] /kundli on mobile: the first form field sits 138px under the tab bar — /  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 602 | agent-work gates guard: an empty $sha makes the API return every run in the re | **Q6** (bundle with #413; LOW/latent) | — |
| 604 | needs-human-review does not hold a PR: agent-merge reads it only in the sweep  | **Q1** | 26e2119 |
| 605 | test_rashifal_day_detail.py module-scoped fixture bypasses _offline_geocode an | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 610 | chief-cleared is documented as releasing a prompts/knowledge PR but no workflo | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 616 | detect_stalls: a green qa-pass PR that later became CONFLICTING is reported me | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 618 | The production verifier POSTs real user forms, so every verify fires an owner  | **Q3** (bundle with #423: one PR to verify-production.yml) | 26e2119 |
