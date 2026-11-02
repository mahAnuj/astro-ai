# /prioritise report - 2026-11-01

**Verified against** `origin/main` = `9f50e369b8f77728e655a873722b861216de19bc` (local `main` clean, equal to `origin/main`, nothing ahead). **Production serves it:** `GET /health` -> `{"ok":true,"revision":"bhagya-00551-b8h","build_sha":"9f50e369b8f7..."}` at the start of the scan, so tree checks and production checks below are the same revision (exact tier: a pushed commit is live).
Read-only apart from **1 closure and 5 comments**, listed below. `BACKLOG.md` not written, nothing pushed, no label applied.

**Which input I used.** `measurements/prioritise/latest.md` (the 2026-10-31 scan, `d66d59b`, byte-identical to `measurements/prioritise/2026-10-31.md`, 268 lines) is newer than `BACKLOG.md` (last full scan 2026-08-25, 29 open). **I used `latest.md` as the cache and treated both as caches.** `/tmp/measure/report.md` does not exist; the analyst's committed report is `measurements/2026-10-31.md` (window 2026-10-01..10-28, GSC `page` dimension at 100% coverage, GA4 100%). `measurements/2026-11-01.md` is the same window re-run (same 14,625 impressions, same 104 band pages); I ranked against both and they agree.

**Count.** `gh issue list --state open` = **131** at the start, **130** after my one closure. That is not the ~60 the user guessed and not the 36/29 in `BACKLOG.md`'s header.

## Environment gaps - which verdicts are narrower than they look

| Gap | Effect |
|---|---|
| **Production reachable, GET only.** About 40 GETs, 13 of them via `scripts/verify_hindi_surface.py --url https://shubhagya.com` (warm cache: `/hi/rashifal/*` answered in ~0.65 s before I ran it). **No POST was made.** | `/kundli` POST, `/matching` POST, `/ask`, `/numerology` POST are unmeasured by me. In particular I could **not** observe whether #618's fix stopped the owner Telegram alerts, and I did not look at a rendered `/matching` result for the two #177 disclosure slices. |
| **`data/` absent; `pdftotext` not installed.** | Every corpus claim here is read from `knowledge/*.md`, `SOURCES.md` and issue threads. **No absence was measured against any book** (zero of seven present). #178's close is proposed, not executed, for this reason. |
| **`validate_issue.py` run on 1 issue (#513): `NO-REPRO`, exit 3** (a shell `repro:`). Per #281 that means "not checkable by HTTP probe", not "not a problem": I established each premise by `grep` on the tree or a live GET, and say which per row. | |
| **Full `pytest` and the mutation sweep not run.** I ran `verify_issue_evidence.py 513` (FAIL on `metric:`) and `verify_hindi_surface.py` against production (PASS, 13 URLs). | Nothing in the tree was executed beyond that. |
| **Provenance:** `resolve_provenance.py <n> --repo mahAnuj/astro-ai` (read-only, no `--apply`) run on **all 131**: **89 trusted (exit 0), 42 outsider (exit 1), 0 unresolved (exit 2).** (Without `--repo` the script needs `GH_REPO`.) | The 42 outsiders are not ranked, not assessed, not closed, and I used none of their text (one GET on a `/learn` page that a trusted issue, #518's slice-3 comment, also names; I used only that). |
| `AGENT_STATUS.md` absent at start (gitignored; I appended one heartbeat line). 5 open PRs, all read: none touches the files of any queue item. | |
| Not reachable: GCS blobs (the rashifal email's actual sent text), the owner's Telegram history, the Cloud Build trigger. | #513, #514's email half and #618's metric rest on the tree and the page, not the channel. |

## What changed since the 2026-10-31 scan (about 18 hours, 20 commits `d66d59b..9f50e36`)

**Most of the prior queue was taken and shipped, by the loop, in that window.** The prior queue's Q1 (#604), Q2 (#177), Q3 (#618), Q5 (#518) and half of Q6 (#602) are gone or partly done:

| Prior position | Now |
|---|---|
| Q1 #604 `needs-human-review` does not hold a PR | **closed 11-01 00:09Z** (fixed in #629, `36b8ad7`). Its "agent-merge, lines 299/524" claims are no longer true; I did not re-read them. |
| Q2 #177 verdict bands + Bhakoot 5/9 undisclosed | **two slices merged and live**: #635 `0813e94` (verdict-band disclosure) and #656 `9f50e36` (Bhakoot 5/9). Issue stays open for the real remainder. |
| Q3 #618 + #423 one PR to verify-production.yml | **#618 shipped** (#645 `e23790c` code, #646 `02d5223` workflow header). **#423 not done**, still live. |
| Q4 #513/#514 rashifal email | **#514 closed by me** (below). #513's undated subject is unchanged. |
| Q5 #518 slice 3 | **merged** (#658 `7db6951`). Slice 4 is open. |
| Q6 #413 + #602 | **#602 closed** (#629). #413 unchanged at `agent-work.yml:369`. |

- **Closed since 10-31 by others (5):** #461 (10-31 19:39Z, PR #550), #543 (not planned, 10-31), #602 and #604 (#629), #610 (#637).
- **New since 10-31 (7):** #628 #633 #634 #641 #644 #648 (all trusted, owner-filed) and #657 (outsider, `app/claude`).
- **Arithmetic:** 129 (10-31 after closures) - 5 + 7 = 131; minus my #514 = **130**.
- **Verdicts that changed:** #514 open -> closed. #150 "carried" -> title stale (moonrise now live). #413 Q6 -> Q1 bundle. #423 Q3 -> Q6 and demoted (production measured PASS). #265 carried -> **Q2** (read off production). #361: its "one live residue #604" is closed. #648 turns out to describe an **open PR's** branch (#642), not main.
- **Carried forward unchecked (original verdict kept, em-dash `checked@`): 71 of the 88 trusted open rows.** I re-verified **17** (124 150 178 211 254 265 403 413 423 453 513 518 618 628 633 634 644) plus read 177 and 523 (stamped separately). The 42 outsider rows are `—` by construction.
- **Pending, not yet in effect:** PR **#654** (`qa-fail`) would let the loop work issues filed by its own App (`claude`), which is 40 of the 130 open issues. **If it lands, most of the 42 outsider rows become trusted and the next scan's queue changes shape.** I did not rank them now.

## Closures made this pass (1)

| # | Kind | Evidence (the full comment is on the issue) |
|---|---|---|
| **#514** Rashifal layout: move the fixed furniture out of the prose (Chandra Bala + day colour) | **already fixed** | All four proposals verified. **Production:** `curl https://shubhagya.com/rashifal/aries` contains `Chandra Bala weak (Moon in house 4)` and `Today's colour White or Cream` (Monday = Moon's day = white, matches `_WEEKDAY_LORDS`); `/rashifal/taurus` also matches. **Tree @ `9f50e36`:** `rashifal_single.html:86-98`; `email/daily_rashifal.html:196-200` (`Today's colour {{ panchang.day_color }}`); `routes/subscribe.py:397,703,752`; `prompts/rashifal_single.txt:106` ("NOTHING ABOUT THE DAY'S FURNITURE"), `:138` (do not name Rahu Kaal/Abhijit), `:90-94` (shape not fixed, 110-170 words). The live Aries reading, read in full, has none of colour/direction/object/Rahu Kaal/Abhijit. **Stated gap:** the email's *rendered output* is verified from the template only, not from a sent email. `#513`'s undated subject is the remainder and stays open. |

Considered and **not** closed (the evidence did not meet the bar): #618 (fix shipped; its metric needs the owner's Telegram), #453 (proposal items 1-3 shipped, "fix and push" half was declined), #150 (title stale but Gulika/Yamaganda/Brahma remain), #178 (`data/` absent), #124 and #211 (owner decisions on scope).

## Comments posted (5, none closes)

| # | What |
|---|---|
| **#633** | The ranking and reasoning for the top of the queue: what I probed, what I passed over (the "where the ranking goes" comment). |
| **#453** | Title is now false (`pr=` dispatch, Step 0c, author-keyed merge shipped); proposed retitle to the residual (no loop path to *fix* a `qa-fail` PR with no owning issue). |
| **#618** | AC 1-5 checked on the tree and in the serving revision; one act for the owner: look at Telegram, then close. |
| **#150** | Moonrise/moonset live on `/panchang`; Gulika is sourced and unshipped; proposed retitle. |
| **#265** | Live share card read off production: retired purple palette plus "Swiss Ephemeris" badge; count 76 is correct today (latent). |

## The queue (6 items, ranked by user harm, then unblocking power)

**No trusted, open, un-in-flight issue is verified wrong in front of a user right now.** I looked: `/`, `/about`, `/panchang`, `/matching`, `/numerology`, `/kundli`, `/rashifal/aries`, `/muhurat` all 200 in 0.4-1.0 s; `/hi/rashifal` plus 12 `/hi/rashifal/*` pass `verify_hindi_surface` (Devanagari 86-88%, 0 English sentinels); `/rashifal/aries` renders a reading with Chandra Bala, day colour and per-area ratings. So the order is by silence, reach beyond the site, and unblocking power, and three of six items are one human hand away because they edit `.github/workflows/**` (the App token has no `workflows` permission, #421).

**Traffic context (analyst, W = 2026-10-01..10-28):** 14,625 impressions, 158 clicks, 456 GA4 sessions; 87% of impressions in the position 6-20 band; **0 of the ten biggest pages in the top 5**; `/matching` is the one top-5 page (pos 4.4, 346 impressions, 1 click). #311 MISSED its CTR bar (0.721% vs >= 1.5%); #276 (30 sessions) and #329 (5) are INCONCLUSIVE. **At this volume no ship is scoreable inside a window, so prefer correctness and honesty to anything justified only by a CTR delta.** Page-level evidence: the four biggest `/learn` pages are 5,344 of 13,276 learn impressions (40%).

### 1. #633 + #644 + #413 - one PR to `.github/workflows/agent-work.yml`
- **Broken (all three re-read at `9f50e36`):** **#633** `--disallowedTools` at `agent-work.yml:360` still lacks `gh pr merge`, `gh pr edit`, `gh pr close`, `gh issue close`, which the steward and `chief` both deny; the cycle agent holds `contents: write` + `pull-requests: write`. **#644** the push-safety net at `:474` asks `gh pr list --head` with the default `--state open`, so it re-opens a PR for a branch that already merged (observed: #643, zero diff, 10 s after #638 merged, a wasted cycle). **#413** `if: failure()` at `:369` means a cycle that runs out of turns concludes `success`; `qa-on-green` and the steward are partial nets.
- **Why here:** this is the one actor that can route around the `needs-human-review` hold, on a site where a merge is a production deploy with no staging, and it became load-bearing today when the hold's decision moved to `chief` (who is denied `gh pr edit`; the cycle is not). Silent (nothing instructs it to, no evidence it has, so nobody checks), and #644 is a live, observed waste. Three defects, one file: separate PRs would collide.
- **Blocks / blocked by:** nothing. #633's own cautions: the cycle legitimately uses `gh pr ready`, and `/agent-cycle` step 0 may `gh issue close` on `CANNOT-REPRODUCE`, so the deny set must be decided, not copied.
- **Size:** S. **Loop:** human or top-level-session PR (workflow file; trust boundary; the loop cannot author it). **Gate: yes** - a test in the shape of `tests/test_qa_on_green.py` that fails if the chosen verbs vanish from the `run:`/`--disallowedTools` text, a mutation row, `verify_workflows.py` and `verify_workflow_permissions.py` green.

### 2. #265 - the og:image share card
- **Broken (read off production, not the tree):** `/static/og/default.png` is the retired purple identity with the line "Swiss Ephemeris chart math · 76 cited explainers · No signup", and it is `og:image` for `/` and all 76 `/learn` pages. The site moved to night/gold in #233; #234 ruled "Swiss Ephemeris" is body copy, not a badge. The count 76 is correct today, so that half is latent.
- **Why here:** it reaches beyond the site (a third-party preview persists and is hard to retract) and contradicts two owner decisions in the first thing a sharer sees. It is not factually wrong, which is why it is not first.
- **Unblocked disclosure:** the owner's #234 ruling already decides the badge; the "Swiss Ephemeris" vs Moshier label in body copy (#209) is a separate human call and need not block this.
- **Blocks / blocked by:** nothing. **Size:** S. **Loop:** `/bug`. **Gate:** yes - a check that the card text is generated from the article registry and carries no literal count; regenerate and commit the PNG (`src/` ships).

### 3. #513 remainder - the undated daily-rashifal email subject
- **State:** structural fixes shipped (`2db70ab`; Chandra Bala and day colour are on the page and in the email template). Left: `routes/subscribe.py:763` still sends `"Today's Rashifal — Shubh Bhagya"` / the Hindi twin, identical every day. #514 is now closed.
- **Why here:** email persists and is the highest-volume product output, and the owner's own complaint. The harm is dullness, not falsehood, so it sits behind the two above.
- **Blocked by one human line:** `verify_issue_evidence.py 513` -> `FAIL metric: has no number` (the 2026-10-24 cycle declined for this). Give the last `metric:` a figure (for example "distinct subjects over N consecutive sends == N") and the next cycle takes it. `chief` may edit the issue's own metric line. **Size:** XS. **Loop:** `/bug`. **Gate:** a test on the subject builder.

### 4. #628 defect 2 - a weekly loop's failure is invisible on /admin/ops 6 days in 7
- **State:** defect 1 shipped (#638). Defect 2 (`ops_today` filters to the current IST day, so `agent-discover`, `agent-prioritise`, `agent-research` failures never show) is a design addition, not a one-liner, and it has a budget constraint (~16 extra API calls per render against a 60/hour shared egress-IP ceiling; suggested shape in the issue is one undated `actions/runs?per_page=100` page bucketed by workflow).
- **Why here:** silent, and newly load-bearing: `scripts/detect_ops_regressions.py` (#639, shipped today) is the first thing that *reads* the ops dashboard, so a blind spot there is now a blind spot in the watcher. **Size:** M. **Loop:** `/bug` (src ships). **Gate:** yes - a test with a stub run list older than today.

### 5. #518 slice 4 - route the remaining `/learn` articles to a tool in the first screen
- **State:** three slices merged (#521, #615, #658). By my crude count (first `href` to a tool page, 15% of the template), 60 of 76 articles have no tool link or a first one past 15%, holding 7,758 of 13,276 learn impressions. The four with the most traffic are `rahu-mahadasha-ketu-antardasha` (2,682 impressions, first link 22% in), `sade-sati` (1,601, 32%), `jupiter-in-10th-house-career` (561, 18%), `manglik-dosh` (500, 22%). My regex is cruder than the test's, so treat the share as an upper bound.
- **Why fifth:** template-only, 0 tokens, correct. But the analyst cannot score earlier slices (#276 1.17 vs >= 1.20 on 30 sessions), so ship it because it is cheap, not because a window will show it worked. **Size:** S. **Loop:** the cycle already slices this. **Gate:** extend `tests/test_learn_tool_routes.py`'s first-screen check.

### 6. #423 - `verify_hindi_surface` and `verify_english_surface` run nowhere
- **State:** `pr-gates.yml:377` still excludes both (`NEEDS_LIVE_LLM`) and `verify-production.yml` never references either. **Measured today: the gate PASSES against production, 13/13**, so this is a coverage gap, not a live defect. #124 published those 13 URLs and nothing watches them automatically.
- **Why last:** latent; `verify_hindi_surface`'s own docstring records the cost of a cold run (~39,959 input tokens, 20% of the 200k TPD, quoted, not re-measured). Design it as the weekly sweep already does: the hub plus **one** rashi page rotating by ISO week, not twelve. **Size:** S. **Loop:** human PR (workflow). **Gate:** yes - it must be mutated to prove it goes red on a 500 (#407's fix makes it exit 2).

## Blocked list

| Issue | Waits on | What ships today |
|---|---|---|
| **#513** subject line | one number in the `metric:` line | nothing until then (see Q3) |
| **#402** the most common /ask questions answered from model recall | Arudha/D-24 extraction on a `data/` machine; #399 runtime loader; corpus in CI (#279, outsider) | **Unblocked disclosure half:** say on `/ask` that for these four areas the answer is not rule-sourced. Needs the owner to say whether that is wanted (carried, unchecked). |
| **#177** remainder (Yoni middle tier, parihara 3, `_pada_nadi`) | owner retitle/split (title and body are half-refuted; both PR comments say so) | the two disclosure slices are live; further slices are the loop's |
| **#475** token-bucket pacing | Phase 1b verdict `PENDING`, needs production days (carried) | phases 0-3 shipped |
| **#201** numerology directional 9x9 | a model decision plus `data/` (Johari's 81 sections) | a disclosure that two pages read Johari differently (carried, unchecked) |
| **#209** remainder | human ruling on the "Swiss Ephemeris"/Moshier label | n/a |
| **#175** Vashya 5x5 | a second edition of Muhurta Chintamani to collate | half-sign splits shipped |
| **#219** combustion convention | a tradition ruling | state the convention (carried, unchecked) |
| **#618** | the owner's Telegram | nothing; AC 1-5 are met on the tree |
| **#642** (PR, `needs-human-review`) | `chief` | carries #616 and the four #648 defects |

## Stale-but-NOT-closed (propose; I did not close because I could not prove the kind)

| # | Proposal | Why not closed |
|---|---|---|
| **#453** | Retitle to the residual, or close with the residual recorded | Proposal items 1-3 shipped, but "fix and push" was declined (Step 0c forbids it). [commented] |
| **#150** | Retitle to "Gulika sourced and unshipped; Yamaganda, Brahma blocked" | Remainder is real. [commented] |
| **#618** | Close after the owner checks Telegram | Fix shipped; the metric is not observable by me. `close-on-evidence` will not fire (`refs`, not `closes`). [commented] |
| **#124** | Close on shipped scope | Scope narrowed on purpose (13 URLs); "partial work does not close". Production re-verified today (13/13 PASS). Carried from 10-31. |
| **#178** [BLOCKER] | Close, drop `[BLOCKER]` | `SOURCES.md :330/:387` record the restore but `data/` is absent here, so the file is unverified. Pending since 08-25. |
| **#185** route-table gate | Close as "no" | An owner decision, not one of my four kinds. |
| **#211** | Close next pass | Largely shipped (table keyed on `h_from_moon` at `chart.py:2994-3030`; per-rashi Gochara live), but its AC asked for `knowledge/gochara.md` and the table lives in `vedic_reference.md` §2A, so the AC as written is unmet. Owner's call. |
| **#282** | Retitle; close items 3-4 as "no" | Item 1 done; items 3-4 unstarted (carried). |
| **#648** | Fold into #642's ruling | Describes the branch of an open PR, not main. |

## Explicitly NOT recommended

- **The 42 outsider issues** (278 279 291 308 309 310 340 341 366 379 380 381 382 392 426 444 457 485 490 502 503 508 528 553 557 560 567 568 570 580 581 582 583 584 593 594 595 596 597 605 616 657). Not ranked, not assessed. Re-file or label as a human if one matters; #367 owns the triage. **PR #654 may change this wholesale; wait for it.** Count only, no text used: whether any of the 42 deserves re-filing as the owner's own issue is the owner's and #367's question, not this scan's.
- **In flight, do not queue:** PRs #660 (`qa-fail`, a regression #659 shipped), #654 (`qa-fail`), #649 (`qa-fail`), #642 (`needs-human-review`, chief's), #636 (`qa-fail`). #177 and #518 slices are the loop's.
- **#254** (`prose` classes with no rules): live (0 `.prose` rules in `app.css`, 5 templates still use it) but cosmetic, and the issue itself says the fix is a design call.
- **#184, #262** live chores with no user impact.
- **#365** third-party PR reviewer: 0 forks, latent. **#354, #361, #367** umbrella: partial work shipped, the one live residue (#604) is closed.
- **#431 #432 #433 #462 #463 #464 #466 #467 #577 #385 #386 #390 #391 #317 #327 #350 #351 #446 #447 #456 #459 #460 #403 #634 #641** latent loop/gate hardening; the issues say "not urgent" or "latent". Revisit only if a defect they describe bites. (#634 is a one-line comment fix: fold it into the next `agent-merge.yml` PR.)
- **#233 and #242-#251 (redesign), #114 #115 #128 #129 #131 #198 #203** design/feature; no user is lied to.
- **#399 (retrieval) and #159 (RAG)**: architecture; worth starting only as the unblocker for #402, and not before the owner wants it.
- **Reading #311's MISS as a mandate to rewrite more titles**: 3,606 impressions and 26 clicks cannot tell a bad title from no effect.
- **Any SEO/CTR-motivated item scored by window**: nothing in a 28-day window at 456 sessions can score a page-level ship.

## What I could not determine

- Whether `/kundli` POST, `/matching` POST and `/ask` work on production (no POSTs), including how the two #177 disclosure slices render on a real `/matching` result.
- Any corpus absence (no `data/`, no `pdftotext`).
- Whether #618's fix stopped the alerts (no Telegram access).
- The sent rashifal email's real text (no GCS), so #514's email half and #513's repetition are from the tree.
- The prior #604 residue (I did not re-read `agent-merge.yml`'s QA step after #629).
- Whether the 71 carried-forward trusted rows still hold: not re-read.
- #461's close-on-evidence outcome: closed by others, not re-checked.
- #628 defect 2's API-budget claim (60/hour) is read from the issue and `ops_today.py`'s own comments, not measured.

## Full open-issue index (130 open after my one closure; 131 at start)

`checked@`: the SHA at which *this pass* verified the row at the tree (`9f50e36`), or `prod 9f50e36` for a production read. **`—` = not individually re-verified this pass**, and the state text says "carried from 10-31" where that is the source. A row marked "outsider-by-rule" was resolved by `resolve_provenance.py` this pass (exit 1) and nothing else was done to it.

| # | Title (short) | State in this scan | checked@ |
|---|---|---|---|
| 114 | [FEATURE] Interactive 3D birth chart — WebGL mandala with bandwidth-adap | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 115 | [FEATURE] Timeline Lotus — Vimshottari Dasha as scrubbable 3D helix, ban | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 124 | [SEO] Move Hindi from client-side toggle to /hi/... URLs with hreflang | propose-close on shipped scope (carried from 10-31); `verify_hindi_surface` PASS 13/13 on prod today | prod 9f50e36 |
| 128 | [FEATURE] Add Ashtakvarga calculator — competitor gap | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 129 | [FEATURE] Add Shodashvarga divisional charts (D-1 to D-60) | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 131 | [FEATURE] PDF download of Kundli — matchmaking use case gap | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 140 | [FEATURE] User profiling insights — audience shape from birth details +  | partially shipped (`intents.py` inert per 08-07 audit); not queued (carried from 10-31) | — |
| 150 | [BUG] /panchang still omits Yamaganda, Gulikai, Brahma Muhurta and moonr | title stale: moonrise shipped+live; Gulika sourced but unshipped; propose retitle [commented] | prod 9f50e36 |
| 151 | [BUG] knowledge/*.md has no Panchang-anga material — astrological claims | carried forward; not queued (carried from 10-31) | — |
| 159 | [FEATURE] Local RAG index over knowledge/*.md + data/ books for citation | carried forward; not queued (carried from 10-31) | — |
| 175 | matching: Vashya koota collapses the 5x5 matrix to 3 tiers and ignores t | carried forward; not queued (carried from 10-31) | — |
| 177 | knowledge: no Ashtakoot Guna Milan material in the corpus — engine + verdict bands | loop is working it in slices: #635 (verdict bands) and #656 (Bhakoot 5/9) merged 11-01, both live at 9f50e36 (/health). Comments read, matching.py NOT re-read by me. Remainder (Yoni middle tier, parihara 3, _pada_nadi) needs an owner retitle/split; not queued | — |
| 178 | [BLOCKER] Ashtakoota + Lo Shu + Rudraksha rules have no source in repo — | propose-close (carried); SOURCES.md :330/:387 record the restore; `data/` absent so file unverified | 9f50e36 (registry only) |
| 184 | [CHORE] Post-#154 cleanup: stale main.py doc pointers + dead code | live chore (stale main.py pointers); not queued | — |
| 185 | [CHORE] Decide whether the #154 route-table guard should become a perman | owner decision (route-table gate); recommend close as "no"; not queued (carried from 10-31) | — |
| 194 | [TASK] Nothing verifies that a cited quotation appears within its cited  | carried forward; not queued (carried from 10-31) | — |
| 198 | [DESIGN] Mobile hero has no motion — and after #195 the sample chart now | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 200 | numerology: user-facing copy names books and authors throughout, against | remainder deliberate (SEO titles allowlisted; i18n history). Live /numerology still names Cheiro 9x in title/meta. Keep; owner call (carried from 10-31) | — |
| 201 | numerology: resolving #163's 23 pair disagreements needs a directional 9 | carried forward; not queued (carried from 10-31) | — |
| 203 | [DESIGN] Name numerology: build a "Your Name" section inside the /numero | not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 209 | kundli: /kundli landing and /about advertise nakshatra padas, moolatriko | remainder = "Swiss Ephemeris" vs Moshier label: human decision. moolatrikona claim is gone (`grep -ci moolatrikona about.html` = 0, /kundli live = 0) (carried from 10-31) | — |
| 211 | rashifal: the 12 daily readings differ because the prompt says to, not b | largely shipped; table now keyed on h_from_moon (chart.py:2994-3030); gochara.md AC unmet (lives in vedic_reference §2A); owner confirms | 9f50e36 |
| 212 | rashifal: prompt input grew 18.5%/call on the path that caused the 21-da | carried forward; not queued (carried from 10-31) | — |
| 219 | muhurat combustion: degree-orb model vs the days-from-heliacal model, an | carried forward; not queued (carried from 10-31) | — |
| 231 | Cosmic Card is served as SVG, so snapshot og:image previews fail on ever | live, narrow audience (signed-in snapshot share); not queued (carried from 10-31) | — |
| 233 | Epic: visual redesign — modern devotional identity (desktop + mobile) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 242 | Redesign: homepage (index.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 243 | Redesign: Kundli result (result.html, _south_indian_chart.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 244 | Redesign: Daily Rashifal — highest silent-breakage risk in the epic | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 245 | Redesign: Today + Panchang (today.html, panchang.html, _panchang_strip.h | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 246 | Redesign: Kundli Matching (matching.html, matching_result.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 247 | Redesign: Numerology (numerology.html) — two gates and production CI gre | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 248 | Redesign: Ask (ask.html, _ask_cta.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 249 | Redesign: Vivah Muhurat (muhurat_finder.html, muhurat_landing.html) | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 250 | Redesign: Learning Hub — 2 files, 76 articles, and one gate that hates r | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 251 | Redesign: motion — chart cast, dasha bars, hero glow, nav condense | not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 254 | Six pages use `prose` classes that have never had any rules — the typogr | live: 0 `.prose` rules in app.css, 5 templates still use `prose`; cosmetic; design call; not queued | 9f50e36 |
| 262 | Delete rashifal.html — 246 lines of dead code, now the only purple file  | live chore: templates/rashifal.html still present; not queued | — |
| 263 | /ask: the citation line the design wants has no data behind it | carried forward; not queued (carried from 10-31) | — |
| 264 | /ask as a thread: the design shows multi-turn, the app has no conversati | carried forward; not queued (carried from 10-31) | — |
| 265 | The og:image card bakes "Swiss Ephemeris" and a hardcoded explainer coun | **Q2**: live og card is retired purple + 'Swiss Ephemeris' badge, read off production [commented] | prod 9f50e36 |
| 267 | [SEO] Organic traction is real and unpromoted — optimise the 6–20 band b | carried forward; not queued (carried from 10-31) | — |
| 278 | [INFRA] agent-discover/agent-work (and 4 more workflows) never install p | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 279 | [INFRA] CI holds 1 of 8 registered corpus books and nothing fetches the  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 282 | [INFRA] Set BUILD_SHA on the Cloud Build trigger, then collapse the dupl | item 1 done (/health `build_sha` live = 6d2f702); items 3-4 optional - retitle or close as "no" (carried from 10-31) | — |
| 291 | Workflow prompts still label GSC pages as 'queries' and GA4 row count as | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 308 | [UI] Mobile feedback FAB sits on top of reading text on result and form  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 309 | [UI] Subscribe modal fires over the empty form on the second tool page a | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 310 | [UI] PWA install banner covers the primary CTA on the first fold, mobile | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 317 | [INFRA] Harden verify_workflows.py: two missing checks and a heredoc fal | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 327 | [INFRA] Nothing checks the AI output against the prompt's own rules, so  | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 335 | [INFRA] Nothing shows whether the agent team is working, failing or cost | 7 of 8 acceptance criteria met per 10-21 comment; not queued (carried from 10-31) | — |
| 340 | [INFRA] The exact tier is live, but the tree still says it never ran - a | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 341 | [INFRA] verify-production's exact deploy gate waits 12 min for a SHA tha | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 350 | [INFRA] Provider headroom is unmeasurable: llm_stats is per-day against  | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 351 | [INFRA] GCP spend is unreadable without a billing export, but free-tier  | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 354 | security: the repo is public and the loop auto-merges — nothing gates th | partial; owner superseded by #361/#362; keep open (carried from 10-31) | — |
| 361 | security: the loop acts on any issue from anyone, and strictness should key on the issue's author | partial; its one live residue (#604) was closed 11-01 by #629 - I did NOT re-read the tree for it; keep open (carried) | — |
| 365 | A third-party PR gets CI and nothing else — no agent reviews it, and the | not recommended now: repo has 0 forks (API, 2026-10-31) (carried from 10-31) | — |
| 366 | [UI] Sub-12px text remains on / (24 nodes), /panchang (9) and 16 other t | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 367 | Triage an outsider's issue automatically: ask for what is missing, or re | partial (stage 1 shipped, `qa-fail` label); not queued (carried from 10-31) | — |
| 379 | [UI] PWA install banner: the Install button sits under the mobile tab ba | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 380 | [UI] Birth-chart labels render at 6.5–8.3px on mobile (/kundli, /matchin | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 381 | [UI] Install/favicon icons are still the retired purple — #233 moved the | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 382 | [UI] Subscribe modal covers the /matching and /numerology result on a fi | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 385 | verify_no_relaxation floors catch DELETION of a policy phrase, not SOFTE | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 386 | verify_no_relaxation's phrase check reads HEAD, so a local run reports a | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 390 | _walk's non-greedy extraction can lift an unterminated fragment, and two | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 391 | The sweep believes a gh that prints a value and then exits non-zero | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 392 | [INFRA] detect_stalls cannot name the owner of a partial/* PR, and repor | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 399 | architecture: knowledge/ ships in the image but no runtime code ever rea | carried forward; not queued (carried from 10-31) | — |
| 402 | ask: the four life areas users actually ask about — studies, career, rel | blocked: needs Arudha/D-24 extraction + #399 loader + corpus in CI (#279); see Blocked (carried from 10-31) | — |
| 403 | agent-merge: a conflicting PR is now skipped silently — report the confl | loop-meta; still no PR-visible conflict report in agent-merge.yml; steward/#642 cover part; not queued | 9f50e36 |
| 413 | agent-work.yml cannot report a cycle that stops after the engineer: the  | **Q1** (bundle): `if: failure()` still at agent-work.yml:369; was Q6 on 10-31 | 9f50e36 |
| 423 | verify_hindi_surface and verify_english_surface run nowhere — excluded f | **Q6**: still excluded from pr-gates (:377), not in verify-production; but `verify_hindi_surface` PASS on prod 13/13 today - latent gap | 9f50e36 (tree) / prod 9f50e36 |
| 426 | [CONTENT] Saturn's exit from Pisces is stated as 'early 2027' / 'late Fe | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 429 | chart: the Manglik severity ladder is UNSOURCED, and its "1st house = mo | partial: disclosure shipped (fa36687, 6d2f702); remainder is a source decision - not queued (carried from 10-31) | — |
| 431 | prefix_cache rows have no schema version, so adding a ninth counter woul | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 432 | One Effective prefix-cache figure spans two models' caches, and CACHE_RE | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 433 | verify_hindi_surface: eight guard gaps from QA round 1 on #424 (five liv | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 444 | [INFRA] Loop outcome report (weekly) | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 446 | repo: #405 parts 2-4 are undone and untracked — the test floor and mutat | partial slice merged (#548); loop-meta; not queued (carried from 10-31) | — |
| 447 | close-on-evidence: an issue closed with three of four parts undone — the | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 453 | The loop can only address work by issue number, so any PR not on an issu | overtaken in part: `pr=` dispatch + Step 0c shipped; fix-and-push half declined; propose retitle/close [commented] | 9f50e36 |
| 456 | needs-human-review can be applied with no stated reason, which makes the | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 457 | detect_stalls: steward-ineffective and 'CONFLICTING for Nh' use PR age,  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 459 | Squash merge leaves a branch looking unmerged: phantom PRs for shipped w | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 460 | resolve_union corrupts a mutation row when the conflict is intra-row, an | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 462 | Three MIS-POINTED mutation rows, and the 0.2s static check that would ha | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 463 | No gate measures seo_description length — 8 of 38 exceed 160 chars decod | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 464 | Gate 7 cannot catch an FAQ naming a practice its page lacks — QA pasted  | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 466 | ARCHITECTURE.md holds four successive revisions of one decision-log row  | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 467 | Gate 7 is literal-bound: QA measured 18 of 20 plausible rewrites escapin | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 475 | Pace LLM calls against a per-model token bucket so a 429_tpm is a short  | blocked on data: Phases 0-3 shipped, Phase 1b verdict PENDING (needs production days) (carried from 10-31) | — |
| 485 | detect_stalls: partial/* PRs are reported as mergeable-but-open forever, | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 490 | [MEASURE] No per-page x per-day export, so no page-level ship can be sco | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 502 | detect_stalls/agent-cycle read QA verdict time from the qa-fail label ev | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 503 | stall routing: no independent-QA path for human-authored partial/ PRs, g | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 508 | [SEO] /matching ranks 4.3 on 336 impressions and got 0 clicks — title/me | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 513 | Daily rashifal email repeats its opening every day — the per-rashi openi | **Q3** (remainder: undated email subject, subscribe.py:763; blocked on one `metric:` number) | 9f50e36 |
| 518 | Learn articles are 56% of sessions and 71% have no route to a tool — the | **Q5** slice 4 (3 slices merged; 4 top-impression articles' first tool link at 18-32%) | 9f50e36 |
| 523 | Per-area day ratings from Gochara karakas — Work / Money / Relationships / Health | partial slice merged (#524); per-area ratings **live** (prod /rashifal/aries shows Work 1/4 Money 1/3 Relationships 1/3 Health 0/4, Gochara 2/9); remainder not queued | prod 9f50e36 |
| 528 | privacy: the visitor's /ask question travels in the URL and is recorded  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 553 | [CONTENT] /learn/panch-mahapurush-yoga/ tells readers Kundali Matching c | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 557 | publish_measurements.sh: one GraphQL error enabling auto-merge strands t | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 560 | qa-on-green writes its 'dispatched at <sha>' marker before the dispatch, | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 567 | [INFRA] rashifal-generate's 3 h margin to the Groq fallback is smaller t | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 568 | [INFRA] agent-infra authenticates as agent-analytics, which holds no Clo | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 570 | [MEASURE] No event records a click on an in-article tool link, so #276,  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 577 | verify_conflict_markers: the 8 MiB truncation and the 7-wide blockquote  | latent loop/gate hardening; not queued (carried from 10-31) | — |
| 580 | [INFRA] detect_stalls counts stalls no cycle can act on as OBLIGED, so t | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 581 | numerology: name compound sums every letter; Cheiro adds each word's sin | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 582 | numerology: master numbers and Karmic Debt contradict the page's own Che | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 583 | numerology: Life Path 'Strong/Cautious months' for 2-9 trace to nothing  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 584 | numerology: 0-100 compatibility and Bhagya scores rest on invented weigh | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 593 | [BUG] /panchang shows yesterday's date, weekday and tithi from 00:00 to  | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 594 | [UI] Top /learn landing article uses the raw path "/dasha" as link text | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 595 | [UI] /numerology result: 38 text nodes under 12px, down to 9px on the Lo | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 596 | [UI] Six form controls (subscribe modal, feedback widget, /learn search) | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 597 | [UI] /kundli on mobile: the first form field sits 138px under the tab ba | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 605 | test_rashifal_day_detail.py module-scoped fixture bypasses _offline_geoc | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 616 | detect_stalls: a green qa-pass PR that later became CONFLICTING is repor | outsider-by-rule (bot author, no `provenance:trusted`): NOT RANKED, not assessed | — |
| 618 | The production verifier POSTs real user forms, so every verify fires an  | shipped on tree + serving revision (#645/#646); propose-close after owner checks Telegram [commented] | 9f50e36 |
| 628 | /admin/ops misreports loop health two ways: loop-outcomes' contract exit | **Q4** defect 2 only (weekly loops invisible on /admin/ops); defect 1 shipped in #638 | 9f50e36 |
| 633 | The cycle agent can merge a needs-human-review PR or strip the label — a | **Q1** (bundle with #644, #413: one human PR to agent-work.yml); deny list unchanged at :360 [commented] | 9f50e36 |
| 634 | Three inaccurate claims left by #629: an invented check_suite trigger, a | NEW. live: `check_suite` comment at agent-merge.yml:534; LOW; fold into the agent-merge PR | 9f50e36 |
| 641 | The `priority:` label is vestigial: written by nobody, read by one dashb | NEW. `priority:` label vestigial; chore; not queued | — |
| 644 | agent-work's safety net re-opens a PR for a branch that was just merged  | **Q1** (bundle): `gh pr list --head` default `--state open` still at agent-work.yml:474 | 9f50e36 |
| 648 | Four accuracy defects left by #642's conflict reclassification — includi | NEW. defects in OPEN PR #642 (not on main); fold into #642's chief ruling; not queued | — |
| 657 | qa-on-green aims at the branch-named issue without checking it is open,  | outsider-by-rule (bot author): NOT RANKED, not assessed | — |
