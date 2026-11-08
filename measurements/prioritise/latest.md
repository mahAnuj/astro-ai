# /prioritise report — 2026-11-08

**Verified against** `origin/main` = `aa2e62fbea2558bcecf14bc3f5e740011648601c` (local `main` clean, equal to origin, nothing ahead). **Production serves it:** `curl https://shubhagya.com/health` -> `{"ok":true,"revision":"bhagya-00618-m6n","build_sha":"aa2e62fb..."}` at scan time (exact tier, so pushed = live and tree checks = production revision).
Read-only apart from **2 closures and 7 triage comments** (listed below). `BACKLOG.md` and every tracked file untouched, nothing pushed, no label applied.

**Which input I used.** `measurements/prioritise/latest.md` (the 2026-11-01 scan, `9f50e36`, 283 lines) is newer than `BACKLOG.md` (last full scan 2026-08-25 `c14093c`, header "36 open"). **I used `latest.md` as the cache; both are caches.** `git log --oneline 9f50e36..origin/main` = **101 commits**, so most carried verdicts are one week and 101 commits old.
`AGENT_STATUS.md` is absent (gitignored). `measurements/sync/chief-guidance.md` **does not exist** in this checkout; `measurements/sync/` holds `2026-10-09.md`, `2026-10-23.md`, `2026-10-30.md`, `2026-11-06.md` and `latest.md` (= 11-06). I read the 11-06 sync; nothing in this report is attributed to a chief-guidance file.
Analyst input: `/tmp/measure/report.md` (2026-11-08, window 2026-10-09..11-05, GSC 20,334 impressions, 231 clicks, GA4 539 sessions) and `measurements/lessons.md` (generated 2026-11-08T11:44Z) read first.

**Count.** `gh issue list --state open` = **116** at the start (not ~60, not BACKLOG's 36). **114 after my two closures.** Arithmetic against `latest.md`: 130 - 39 closed since 11-01 + 25 new = 116.

## Environment gaps — which verdicts are narrower than they look

| Gap | Effect |
|---|---|
| **`data/` absent** (`ls data` fails); no `pdftotext`; `corpus_search.py` not run. **Zero of the registered books present.** | Every Raman/Cheiro/Rao quotation in #713-#716, #581-#584 is the filer's, unrechecked by me. I verified only what the CODE does (it reproduces) and what `knowledge/*.md` says (counts). No corpus absence is claimed anywhere here. |
| **Production reachable, GET only**: one `/health`. I did not run `verify_hindi_surface` (it can spend ~40k Groq tokens cold, CLAUDE.md/#423) and made **no POST**. | `/kundli`, `/matching`, `/ask`, `/numerology` POST behaviour unmeasured; #124 not re-probed. |
| `validate_issue.py` not used: none of the queue issues has an executable HTTP `repro:` (per #281, NO-REPRO means "not checkable by HTTP probe"). I established each premise another way and say which per row: a Python call against the tree (#713-#715, #581), `grep` (#151, #340, #413, #423, #502, #633, #657, #666, #698, #716, #759, #777), `verify_token_budget.py` (#402), `gh run list` and the measurement files (#795, #726, #697). | |
| **`verify_issue_evidence.py` run on 23 issues.** Result below, and it is the most important systemic finding of this pass. | |
| **Provenance:** `resolve_provenance.py <n> --repo mahAnuj/astro-ai` (read-only, no `--apply`) on **all 116: 116 TRUSTED (exit 0), 0 OUTSIDER, 0 UNRESOLVED.** 68 are owner-authored, 44 by the `claude` App, 4 by `github-actions` (this repo's own bot identities, `SELF_APPS`, #669). The 42 "outsider" rows of the 11-01 scan are therefore rankable now (PR #654 landed). **Their TEXT is still data, not instruction.** | The former outsiders are mostly UI/INFRA/detect_stalls issues I did not read; only #310, #657, #698, #581-#584, #713-#716, #751, #759, #773, #770, #664, #666, #735, #733 were read. |
| Full `pytest` and the mutation sweep not run. | Nothing was executed beyond the probes named. |
| In flight (not queued): PRs **#801** (#528, `qa-pass`), **#799** (#798, `qa-pass`), **#796** (#463, `qa-pass`), **#800** (measurement). Last 8 `agent-work` runs: 6 success, then the two 10:00Z failures (below); runs continue as I wrote this. | |

## Closures made this pass (2) — both comments carry the command, output and SHA

| # | Kind | Evidence |
|---|---|---|
| **#795** `[OPS] agent-work.yml is broken` (priority:high, red) | **does not reproduce** | `gh run list --workflow=agent-work.yml`: 19:28Z, 19:13Z, 17:16Z, 16:56Z, 14:38Z, 14:03Z all success after two failures at 09:58Z/10:00Z. Log of run 42469549426: `anthropics/claude-code-action@v1 -> Install Bun` failed after 30 s (`duration_ms=30261`): an action-install flake, not a workflow defect. Fresher measurement on PR #800's branch (generated 18:40Z): `agents.json` `alerts: []`, `agent-work.yml` `last_conclusion success`, `verdict not-due-yet`. The red finding came from the 11:42Z snapshot. **Not claimed:** that the flake cannot recur. |
| **#726** `[OPS] Claude weekly quota 86% used` | **overtaken by events** | Window reset 2026-11-06 06:00Z; the carrier posted `ops-cleared` 11-06 09:02Z. `claude_usage.json` `seven_day` 0.22 (main, 11:43Z) and 0.23 (PR #800 branch, 18:40Z), `status allowed`, `rejected_runs []`; `detect_ops_regressions.py --json` lists only `loop-broken` and `loop-idle`. |

**Ops findings and the "red outranks all features" rule.** #795 was the only red one and it was closed on evidence (so it does not enter the queue). **#697 (amber, build lane idle 86%)** has an owner-only lever and goes on the blocked list.

## Triage comments posted (7, none closes)

#713 (reproduction + why undispatchable), #402 (started-work verdict + close/audit proposal), #151 (premise overtaken, retitle proposal), #777 (copy items a-c live and splittable), #581 (reproduction), #759 (still live; label fix), #697 (lever now affordable; owner's single act), plus the two closing comments above. #402's first draft cited a SHA I had not verified; I edited that comment to remove it.

## THE SYSTEMIC FINDING of this pass (drives Queue 2)

`uv run python scripts/verify_issue_evidence.py <n>` returns **FAIL (6 problems) on #713 #714 #715 #716 #581 #582 #583 #584 #657 #664 #698 #770** and 3-5 problems on #777 #751 #773 #633 #340; #759 and #666 fail on exactly one. `agent-cycle` Step 0 refuses to dispatch a FAIL. That means **every astrology-correctness finding the research loop has filed since 2026-11-05 — the "fully grounded astrology" half of OBJECTIVE.md, and the only issues I verified to be wrong in front of users — cannot be built by the loop**, and the cycles that ranked #581 (11-03) and #583 (11-05) stopped at this gate and said so. Two causes, both in text agents may edit:
1. `.claude/agents/astro-auditor.md:105` ("File one issue per finding, tagged `astrology-correctness`") and `.claude/agents/numerologist.md` say nothing of the key: value Evidence Block (`grep -in "evidence block"` in both: no hits; none in `agent-research.yml` either). #733 is the same defect for `agent-design.yml`.
2. `verify_issue_evidence.py:148` exempts `bug`, `chore`, `category:technical` from `gsc:/ga4:` and does not exempt `astrology-correctness`. Cheapest fix that does **not** touch the gate: have the auditor add `bug` (an auditor finding is a defect). Weakening the gate itself is not covered by the 2026-11-06 grant.

## Started work first (open issue with a merged `partial/<n>-` PR and no open PR)

Merged `partial/` PRs on `origin/main` whose issue is still open and which have no open PR: **#402** (#706, #758), **#150** (#725, #776), **#782** (#785). (#177, #184, #429, #446, #508, #518, #628, #231, #399 also had partial PRs and are now closed.)

| Issue | What finishing means | Verdict |
|---|---|---|
| **#402** | AC1/AC3/AC4/AC5/AC6 shipped. Only AC2 (sourced rule blocks) remains, as sub-issue #741, which two premise checks (#740 11-07, #741 11-08) showed is not buildable as written: `ask.txt` carries no recalled-rule text to delete and `ask+payload` has **+0 headroom** (re-measured today). No Step 4 closed-list item applies (it is neither an owner act, nor a missing source, nor an unmade chief ruling). | **Ranked Queue 1**: a bounded decision step, not a build. |
| **#150** | Moonrise, Gulika Kaal, Gate 8 weekday rows all shipped. Yamaganda and Brahma Muhurta remain: Step 4 closed-list **item 2** (a source the corpus lacks; the owner measured 0 hits 2026-11-06). | Blocked on a source. Propose retitle to those two. Not queued. |
| **#782** | Every acceptance criterion's act is done (#785, #788, the owner's GA4 custom dimensions today). What closes it is a post-deploy measurement: an `agent-measure` run writing `measurements/ga4-events.json` (absent from the tree at `aa2e62f`). That is not on the closed list. | **Propose closing** when that file lands, with #785/#788 as the evidence. I did not close it: the file does not exist yet, so the kind is not proven. |

## The queue (7 items, ordered by user harm, then unblocking power)

**What is wrong in front of a user right now (probed):** the muhurat finder's verdicts (#713-#715) and the numerology name-compound number (#581) reproduce on the tree at `aa2e62f`, which `/health` says is live; the Manglik FAQ and matching copy (#777 a-b) state a six-house rule and an unsourced cancellation flatly. Nothing in the `/`, `/panchang`, `/rashifal` surface was re-probed (GET `/health` only), so "nothing else is wrong" is **not** a claim of this scan.
**Traffic context (analyst 2026-11-08):** 20,334 impressions, 231 clicks, 539 sessions; **0 of the ten biggest queries in the top 5**; weighted band CTR 1.10%; #311 reads 0.88% against a 1.5% bar (the 11-06 sync called it a MISS on the idea: title copy does not move position). **No ship is scoreable inside a window at this volume, so I rank correctness and unblocking over anything justified by a CTR delta, and I queue no title/meta test** (the sync forbids a new one until #685 scores ~2026-12-04). `/muhurat/griha-pravesh` is the best organic tool landing (11-06 sync), which is why the muhurat defects outrank new growth work there.

### 1. #402 remainder — decide AC2 on one measurement, or close #741 and #402
- **Broken:** `/ask` answers the owner's most common questions (studies, career, relationships, money) with one AC left, "rule blocks that trace to `knowledge/`", whose retrieval design was refuted twice.
- **Why here:** started work ranks first by definition. It is cheap, and it unblocks three issues at once (#740, #741, #742 all sit on the same missing measured case).
- **Step:** `astro-auditor` samples ~10 realistic questions per area through the ask path and looks for a Gochara/dasha rule stated from recall that is in neither the payload nor `knowledge/`. Found -> re-scope AC2 on that finding. None -> close #741 and #402 with #706 and #758 as evidence (propose; I may not close these kinds).
- **Tokens:** ~2k input per `ask+payload` call (1,936 measured), ~20k for 10 calls = ~10% of the 200k TPD; run once, off-peak. Not run by me; model behaviour unverified.
- **Size:** S. **Loop:** `astro-auditor` via `/agent-cycle` with `issue=402`. **Gate:** no code; the output is an audit comment.

### 2. NEW issue to file — auditor/design findings must be dispatchable (Evidence Block + `bug` label), then retrofit #713-#716, #581-#584, #777, #733
- **Broken:** see "systemic finding" above: 12 issues fail the loop's own dispatch gate with 6 problems.
- **Why here:** gating issue; it outranks its own severity because items 3, 4 and 5 below cannot start without it, and it is the cause, not the symptom, of cycles ranking #581/#583 and stopping.
- **Shape (not acceptance criteria, that is product-manager's):** edit `astro-auditor.md`, `numerologist.md` (and #733's `agent-design.yml` prompt) to emit the key: value block and to add `bug`; one pass by `steward` or `chief` rewriting the body of #713, #581 and #777(a-c) (the steward did this for #759 on 11-07, so it is an available act). **Blocks:** Q3, Q4, Q5 (and #759, one label away). **Blocked by:** nothing.
- **Size:** S (`.claude/` text, covered by the 2026-11-06 grant; must not touch `REQUIRED_SUBSTRINGS`). **Loop:** `/bug` or steward. **Gate:** `uv run python scripts/verify_issue_evidence.py <n>` exits 0 on each retrofitted issue; `verify_agent_trail.py`, `verify_no_relaxation.py` green. Tokens: 0.

### 3. #713 + #715 + #714 + #716 — one PR to `muhurat.py` (shared file)
- **Broken (all reproduced at `aa2e62f`):** `_PANCHAK_NAKSHATRAS` flags the whole of Dhanishta (`muhurat.py:44`; the issue quotes Raman as starting at its third quarter); a groom's own birth star yields `good-for-both` in the Vivah verdict (`:64`, `:1113`); the 6th from the birth sign scores `strong` for the finder (`:77`), against the muhurta rule the filer quotes (Rao's gochara table supports it for the Rashifal). `muhurat.py` still cites BPHS in 3 places and `verify_rule_citations.py` has 0 references to `muhurat` (#716).
- **Why here:** wrong in front of a user, on the page the 11-06 sync names as the best tool landing, and the sync ruled these rank ahead of any new `/muhurat` growth build. They change what a couple is told about a wedding day. Silent: nobody checks a muhurat verdict.
- **Blocked by:** Q2 (dispatch gate). #713's correct value is sourced in the filer's quote; #714 and #715 need a convention call (ship the per-event table, or state the simplification), which is `chief`'s, not the owner's (not on the closed five). **Unblocked disclosure half:** state the simplification on the page as its own sub-issue that can close.
- **Caveat:** the quotations are unverified here (`data/` absent); QA must re-read them on a machine with the books or the PR must say they are unverified. A `knowledge/vedic_reference.md` edit (§29.9 says `panchak` is "a different concept") is a trust-boundary change held for `chief`.
- **Size:** M. **Loop:** `/bug` -> architect (split `_chandra_bala` into a muhurta and a gochara function; Rashifal keeps Rao's table, so its prompt is unchanged). **Gate: yes** — tests on each value, mutation rows in a new `scripts/mutations/muhurat_*.py`, and extend `verify_rule_citations.py` to scan `muhurat.py` (that is #716's own AC, so a gate that can see the file lands with the fix). **Tokens: 0** (deterministic); confirm `rashifal_single` row unchanged (2,927 en, ceiling 3,350).

### 4. #581 — the numerology name compound is the wrong number
- **Broken:** `numerology.py:1869-1870` sums every letter of the whole name; reproduced `LLOYDGEORGE` = 43, while per-word singles 18->9 and 25->7 give 16, the figure the code's own comment cites. Shown on `/numerology` (`numerology.html:681-689`) and fed to the Bhagya score (`:650-652`).
- **Why here:** a confidently wrong number in the one page that shows it, and the code comment claims a source that says otherwise. Behind Q3 because the muhurat verdicts decide a wedding or house-entry date; traffic does not separate them (`/numerology` 11 sessions, 82% bounce; `/muhurat/griha-pravesh` 12 sessions per the 11-06 sync).
- **Blocked by:** Q2. #582 (master numbers, Cheiro vs Kumar) is a separate ruling and is not bundled. **Size:** S. **Loop:** `/bug`. **Gate: yes** — a test that reproduces Cheiro's worked names (Lloyd George 16, David Lloyd George 23, Austen Chamberlain 11 per the issue's table; check against `data/` where present), plus `verify_numerology_copy.py` anchors. **Tokens:** deterministic; the `ask+numerology+payload` row has headroom +0, so re-run `verify_token_budget.py` after.

### 5. #777 items (a)-(c) — Manglik copy: a sub-issue that can close
- **Broken (probed):** `learn_registry.py:1184` and `templates/matching.html:201` state the six-house Manglik rule flatly and list "Mars combust" as a cancellation `vedic_reference.md` §1.6.2 marks unsourced; `manglik-dosh.html:21,28` already say the 1st house is optional, so the pages disagree with each other.
- **Why here:** a claim standing on a ranking page because it performs (OBJECTIVE.md: authenticity wins on the claim). `/learn/manglik-dosh` has 513 impressions at 0.58% CTR. One-line copy edits. **Blocked by:** Q2 (label/evidence). The tier ladder and Venus downgrade stay blocked (see blocked list).
- **Size:** XS. **Loop:** `/bug`. **Gate:** yes — extend the numerology/learn copy gate so the six-house sentence cannot return. **Tokens:** 0. Note `/learn` Gate 7 is literal-bound (#467), so state the rewritten phrase exactly.

### 6. #759 — a chief-cleared PR waits for a throttled sweep (loop speed)
- **Broken:** `scripts/chief_clear.py` applies `chief-cleared` with `github.token` and never dispatches `agent-merge`; four instances measured by the steward (#749 and #750 waited 13-14h; #767 and #758 each sat until the next sweep, #758 for 2h50m+). The 11-07 "a merge re-dispatches the sweep" only helps after another merge.
- **Why here:** unblocking power. Every trust-boundary PR (any `prompts/`, `knowledge/`, `notify.py` fix, i.e. Q3 and Q4's `knowledge` edits) waits on this path. **Blocked by:** one parse failure, `no gsc:/ga4:`, cleared by adding `chore` (probed). No new permission: `agent-steward.yml:86` already holds `actions: write`.
- **Size:** S (a script and a test; the loop may author `scripts/`; **if the dispatch step must live in the workflow file, that part is a human push**). **Gate: yes** — a test in the shape of `tests/test_qa_on_green.py` pinning that `chief_clear.py` dispatches and that no label verb appears in a dispatcher. Tokens: 0.

### 7. #633 + #413 + #698 — one PR to `.github/workflows/agent-work.yml` (a human push)
- **Broken (re-read at `aa2e62f`):** `--disallowedTools` (`:400`) still lacks `gh pr merge`, `gh pr edit`, `gh pr close`, `gh issue close`, which the steward and chief both deny (#633); `if: failure()` (`:409`) means a cycle that runs out of turns concludes `success` (#413); the cycle step has no `GH_REPO` env and `Bash(gh repo:*)` blocks the read-only `gh repo view` the agent improvises, so a session can end 44 s in (#698). (#644 is closed; `--state all` is at `:586`.)
- **Why seventh:** silent, and it is the one actor able to route around the `needs-human-review` hold on a site where a merge deploys, but nothing shows it has. Measured cost today is small: `loop.json` `waste.minutes_by_outcome` has `nothing` 64.4 min and `failed` 18.6 min of 2,012 in 7 days (4.1% without a result). **The two 10:00Z failures were an Install-Bun flake, not #698** (I read that log).
- **Blocked by:** nothing; the App token cannot author a workflow file (#421), so a human or top-level session pushes and `chief` merges. #633's own caution stands: the cycle legitimately uses `gh pr ready`, and Step 0 may `gh issue close` on `CANNOT-REPRODUCE`, so the deny set is a decision. **Size:** S. **Gate: yes** (`verify_workflows.py`, `verify_workflow_permissions.py`, a test that fails if the chosen verbs vanish, a mutation row).

## Blocked list

| Issue | Blocked on | Unblocked disclosure / what ships today |
|---|---|---|
| **#697** build lane idle 86% (amber) | owner's single act: push a second `cron:` line in `agent-work.yml`, or say the 2026-11-06 chain (`chain_cycle.py`) is enough. Quota now 22-23%, so it is affordable (#726 closed on that). | n/a |
| **#777** Manglik tier ladder / Venus-only downgrade | owner/product call (closed-list act 4): keep the ladder as Bhagya's disclosed weighting or change grades | items (a)-(c) are Queue 5; user copy already says the grades are Bhagya's own |
| **#751** five matching rules | a source the corpus lacks (acquisition task: second Muhurta Chintamani edition, bands, 5/9 source) | disclosed on `/matching` since #635/#656 |
| **#773** AnkitNotes / K.N. Rao caveat | `data/` (absent on the loop runner) | two copy items from QA (numerology.html:132 "1908-1940s") are buildable only with a source or a softer wording |
| **#150** Yamaganda, Brahma Muhurta | a source the corpus lacks | Gulika, moonrise, Gate 8 live |
| **#782** | an `agent-measure` run writing `measurements/ga4-events.json` | propose close then |
| **#582** master numbers (Cheiro vs Kumar) | a `chief` ruling | n/a |
| **#310** PWA banner vs CTA | product decision (installs vs first-visit conversion), act 4 | #766 already lifted the banner; overlap with the #304 CTA remains |
| **#740 / #741 / #742** retrieval | a measured recall case (Queue 1) | n/a |
| **#402** | Queue 1 | AC1/3/4/5/6 live |
| **#175, #201, #219, #209, #475, #178** | tradition rulings, `data/`, or production days (carried from 11-01, not re-read) | as listed in the 11-01 scan |

## Stale / propose-close list (I closed only #795 and #726)

| # | Proposal | Why not closed by me |
|---|---|---|
| **#782** | Close when `measurements/ga4-events.json` lands (all ACs' acts done) | file absent today; not proven |
| **#402 + #741** | Close both if the Queue 1 audit finds no recall case | needs the audit |
| **#151** | Retitle to "panchang significance strings unsourced, see §29.10" | partial work does not close; `data/` absent so no absence measured |
| **#150** | Retitle to Yamaganda + Brahma Muhurta, blocked on a source | remainder real |
| **#124** | Close on shipped scope (13 Hindi URLs, owner narrowed it on purpose) | an owner decision; `/hi` pages not re-probed this pass |
| **#178** | Close, drop `[BLOCKER]` (its own thread recommends it; gates nothing) | `data/` absent, unverified |
| **#185** | Close as "no" | owner decision |
| **#648** | Re-read then close or fold: PR #642 **merged 11-02** (latest.md said "open"), the named test no longer exists | I did not re-verify the four defects against current `detect_stalls.py` |
| **#453** | Retitle (11-01 proposal) | carried, not re-read |
| **#502** | Keep open, narrowed: the `detect_stalls` half shipped (#708), `agent-cycle.md:323` still reads the label-event time | an `.claude/` edit the loop may make |
| **#282** | Retitle; close items 3-4 as "no" | carried |

## Explicitly NOT recommended

- **A title/meta test for `/learn/debilitated-sun-career/`** (the analyst's biggest CTR outlier, 0.53% at position 6.6): the analyst declined to file it, #311 (0.88% vs 1.5%, a MISS on the idea) and #685 have no clean score before 11-13 and 12-04, and #685's body says to stop filing title tests for this band if it misses. This is lessons.md's rule: do not repeat a kind of change that missed without saying why this time differs; I cannot.
- **A second build lane / more parallelism:** the build lane is idle but 46 PRs shipped in 7 days; #697 is the owner's call.
- **#310, #308, #309, #380, #381, #366, #595, #596, #594** (UI): former outsiders, now trusted by provenance; #310 is a product tradeoff; none read in full beyond #310. Not queued, not dismissed.
- **#233, #242-#251, #114, #115, #128, #129, #131, #198, #203** design/feature: no user is lied to; carried from 11-01.
- **#743, #744** new security gates split from #354: latent. **#431-#433, #446-#467 family, #577, #385, #386, #390, #391, #317, #327, #351, #456, #459, #460, #403, #634, #641, #657, #666, #335, #444** loop/gate hardening or report issues: latent.
- **#740 / #742** retrieval issues: the cycle already refuted #740's thesis.
- **Anything scored on a CTR window** (see traffic context).

## What I could not determine

- Whether the Raman/Cheiro quotations in #713-#716/#581-#584 are accurate (`data/` absent).
- Any production behaviour beyond `/health`: no `/muhurat`, `/numerology`, `/ask` page was fetched, so the muhurat and name-compound claims are "reproduces on the tree at the serving SHA", not "observed on the site".
- How many of the 44 `claude`-authored issues I did not read are real defects.
- Whether #648's four defects still hold on current `detect_stalls.py`.
- Whether the 10:00Z Install-Bun flake recurs (nothing in the tree retries it).
- #150's and #124's current production state (threads read, not re-probed).

## Deltas against the prior scans

- **Prior input:** BACKLOG.md header scan 2026-08-25 `c14093c` (36 open) is 75 days stale; `latest.md` 2026-11-01 `9f50e36` (130 open). Used `latest.md`.
- **39 issues closed since 11-01** (not in my open list): 177 184 200 209 231 254 262 265 278 279 350 354 361 367 379 382 392 399 426 429 431 432 446 466 475 485 508 513 518 523 553 557 570 593 597 616 618 628 644. I did not audit them; the 11-06 sync audited 33 of the earlier ones.
- **25 new since 11-01:** 664 666 697 698 700 713 714 715 716 726 733 735 740 741 742 743 744 751 759 770 773 777 782 795 798. Of these I closed 795 and 726.
- **Verdicts that changed:** #648 "defects in an open PR" -> PR merged 11-02. #151 "carried" -> premise overtaken (§29). #633 position 1 (11-01) -> position 7: nothing verified wrong in front of a user then; now four things are. #644 -> closed (fixed). #413 Q1-bundle -> still live, bundle now with #698 instead. #423 unchanged (still excluded at `pr-gates.yml:377`). #513 closed (not re-audited). #402 "blocked on Arudha/D-24" -> shipped slices, remainder reframed.
- **The 42 "outsider" rows of 11-01:** now TRUSTED (PR #654 landed, `claude` App is in `SELF_APPS`); the 11-01 note "wait for #654" is resolved. Those still open are carried with em-dash and "not assessed this pass".
- **Re-verified this pass (stamped `aa2e62f`):** 22 by command or grep, 5 by PR state or a partial read (marked in the table): 151 340 402 413 423 502 581 633 634 657 666 697 698 713 714 715 716 759 777 782 and the two closures 795 726; partial: 463 528 798 (PR list only), 648 (PR state + one grep), 741 (headroom re-measured).
- **Carried forward unchecked: 89 rows, `—`.** Their states are copied from `latest.md` and say so.

## Full open-issue index (116 at the start; #795 and #726 closed this pass => 114 open)

`checked@`: the SHA at which this pass verified the row, else `—` (not individually re-verified; state text says where it came from). "pr-list 11-08" means only `gh pr list` was read.

| # | Title (short) | State in this scan | checked@ |
|---|---|---|---|
| 114 | [FEATURE] Interactive 3D birth chart — WebGL mandala with bandwidth-adap | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 115 | [FEATURE] Timeline Lotus — Vimshottari Dasha as scrubbable 3D helix, ban | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 124 | [SEO] Move Hindi from client-side toggle to /hi/... URLs with hreflang | propose-close on shipped scope (owner: scope narrowed on purpose); /health serving aa2e62f; /hi pages not re-probed this pass | — |
| 128 | [FEATURE] Add Ashtakvarga calculator — competitor gap | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 129 | [FEATURE] Add Shodashvarga divisional charts (D-1 to D-60) | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 131 | [FEATURE] PDF download of Kundli — matchmaking use case gap | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 140 | [FEATURE] User profiling insights — audience shape from birth details +  | carried from 11-01 scan: partially shipped (`intents.py` inert per 08-07 audit); not queued (carried from 10-31) | — |
| 150 | [BUG] /panchang still omits Yamaganda, Gulikai, Brahma Muhurta and moonr | started work (#725, #776 merged, no PR): Yamaganda + Brahma Muhurta remain, closed-list item 2 (source absent). Propose retitle. Read threads, tree not re-probed | — |
| 151 | [BUG] knowledge/*.md has no Panchang-anga material — astrological claims | title stale: knowledge/vedic_reference.md §29 (five angas) exists since 2026-08-26; remainder = significance layer (§29.10). Propose retitle. comment posted | aa2e62f |
| 159 | [FEATURE] Local RAG index over knowledge/*.md + data/ books for citation | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 175 | matching: Vashya koota collapses the 5x5 matrix to 3 tiers and ignores t | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 178 | [BLOCKER] Ashtakoota + Lo Shu + Rudraksha rules have no source in repo — | propose-close, drop [BLOCKER] (carried; data/ absent so unverified) | — |
| 185 | [CHORE] Decide whether the #154 route-table guard should become a perman | carried from 11-01 scan: owner decision (route-table gate); recommend close as "no"; not queued (carried from 10-31) | — |
| 194 | [TASK] Nothing verifies that a cited quotation appears within its cited  | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 198 | [DESIGN] Mobile hero has no motion — and after #195 the sample chart now | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 201 | numerology: resolving #163's 23 pair disagreements needs a directional 9 | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 203 | [DESIGN] Name numerology: build a "Your Name" section inside the /numero | carried from 11-01 scan: not recommended now (feature/design; unchanged verdict) (carried from 10-31) | — |
| 211 | rashifal: the 12 daily readings differ because the prompt says to, not b | carried from 11-01 scan: largely shipped; table now keyed on h_from_moon (chart.py:2994-3030); gochara.md AC unmet (lives in vedic_reference §2A); owner confirms | — |
| 212 | rashifal: prompt input grew 18.5%/call on the path that caused the 21-da | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 219 | muhurat combustion: degree-orb model vs the days-from-heliacal model, an | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 233 | Epic: visual redesign — modern devotional identity (desktop + mobile) | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 242 | Redesign: homepage (index.html) | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 243 | Redesign: Kundli result (result.html, _south_indian_chart.html) | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 244 | Redesign: Daily Rashifal — highest silent-breakage risk in the epic | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 245 | Redesign: Today + Panchang (today.html, panchang.html, _panchang_strip.h | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 246 | Redesign: Kundli Matching (matching.html, matching_result.html) | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 247 | Redesign: Numerology (numerology.html) — two gates and production CI gre | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 248 | Redesign: Ask (ask.html, _ask_cta.html) | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 249 | Redesign: Vivah Muhurat (muhurat_finder.html, muhurat_landing.html) | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 250 | Redesign: Learning Hub — 2 files, 76 articles, and one gate that hates r | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 251 | Redesign: motion — chart cast, dasha bars, hero glow, nav condense | carried from 11-01 scan: not recommended now (redesign; reopened 09-04; "ABSENT" lists partly stale, re-audit before use) (carried from 10-31) | — |
| 263 | /ask: the citation line the design wants has no data behind it | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 264 | /ask as a thread: the design shows multi-turn, the app has no conversati | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 267 | [SEO] Organic traction is real and unpromoted — optimise the 6–20 band b | carried from 11-01 scan: carried forward; not queued (carried from 10-31) | — |
| 282 | [INFRA] Set BUILD_SHA on the Cloud Build trigger, then collapse the dupl | carried from 11-01 scan: item 1 done (/health `build_sha` live = 6d2f702); items 3-4 optional - retitle or close as "no" (carried from 10-31) | — |
| 291 | Workflow prompts still label GSC pages as 'queries' and GA4 row count as | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 308 | [UI] Mobile feedback FAB sits on top of reading text on result and form  | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 309 | [UI] Subscribe modal fires over the empty form on the second tool page a | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 310 | [UI] PWA install banner covers the primary CTA on the first fold, mobile | design-proposal, product decision (installs vs first-visit conversion) = closed-list act #4; thread read to 11-07, not re-probed; not queued | — |
| 317 | [INFRA] Harden verify_workflows.py: two missing checks and a heredoc fal | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 327 | [INFRA] Nothing checks the AI output against the prompt's own rules, so  | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 335 | [INFRA] Nothing shows whether the agent team is working, failing or cost | carried from 11-01 scan: 7 of 8 acceptance criteria met per 10-21 comment; not queued (carried from 10-31) | — |
| 340 | [INFRA] The exact tier is live, but the tree still says it never ran - a | live, text only: `--set-env-vars` still printed at verify-production.yml:27,207,838 and health.py:61; workflow edit = human. Not queued | aa2e62f |
| 341 | [INFRA] verify-production's exact deploy gate waits 12 min for a SHA tha | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 351 | [INFRA] GCP spend is unreadable without a billing export, but free-tier  | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 365 | A third-party PR gets CI and nothing else — no agent reviews it, and the | carried from 11-01 scan: not recommended now: repo has 0 forks (API, 2026-10-31) (carried from 10-31) | — |
| 366 | [UI] Sub-12px text remains on / (24 nodes), /panchang (9) and 16 other t | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 380 | [UI] Birth-chart labels render at 6.5–8.3px on mobile (/kundli, /matchin | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 381 | [UI] Install/favicon icons are still the retired purple — #233 moved the | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 385 | verify_no_relaxation floors catch DELETION of a policy phrase, not SOFTE | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 386 | verify_no_relaxation's phrase check reads HEAD, so a local run reports a | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 390 | _walk's non-greedy extraction can lift an unterminated fragment, and two | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 391 | The sweep believes a gh that prints a value and then exits non-zero | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 402 | ask: the four life areas users actually ask about — studies, career, rel | QUEUE 1 (started work): #706 + #758 merged, no open PR; AC2 only remains (#741, premise refuted twice). Audit-or-close step; comment posted | aa2e62f |
| 403 | agent-merge: a conflicting PR is now skipped silently — report the confl | carried from 11-01 scan: loop-meta; still no PR-visible conflict report in agent-merge.yml; steward/#642 cover part; not queued | — |
| 413 | agent-work.yml cannot report a cycle that stops after the engineer: the  | QUEUE 7 (bundle): `if: failure()` still at agent-work.yml:409; Evidence Block PASS | aa2e62f |
| 423 | verify_hindi_surface and verify_english_surface run nowhere — excluded f | live latent gap: pr-gates.yml:377 NEEDS_LIVE_LLM still excludes both Hindi/English surface gates; workflow edit | aa2e62f |
| 433 | verify_hindi_surface: eight guard gaps from QA round 1 on #424 (five liv | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 444 | [INFRA] Loop outcome report (weekly) | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 447 | close-on-evidence: an issue closed with three of four parts undone — the | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 453 | The loop can only address work by issue number, so any PR not on an issu | carried from 11-01 scan: overtaken in part: `pr=` dispatch + Step 0c shipped; fix-and-push half declined; propose retitle/close [commented] | — |
| 456 | needs-human-review can be applied with no stated reason, which makes the | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 457 | detect_stalls: steward-ineffective and 'CONFLICTING for Nh' use PR age,  | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 459 | Squash merge leaves a branch looking unmerged: phantom PRs for shipped w | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 460 | resolve_union corrupts a mutation row when the conflict is intra-row, an | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 462 | Three MIS-POINTED mutation rows, and the 0.2s static check that would ha | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 463 | No gate measures seo_description length — 8 of 38 exceed 160 chars decod | IN FLIGHT: PR #796 (qa-pass) open. Do not queue | pr-list 11-08 |
| 464 | Gate 7 cannot catch an FAQ naming a practice its page lacks — QA pasted  | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 467 | Gate 7 is literal-bound: QA measured 18 of 20 plausible rewrites escapin | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 490 | [MEASURE] No per-page x per-day export, so no page-level ship can be sco | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 502 | detect_stalls/agent-cycle read QA verdict time from the qa-fail label ev | live, small: agent-cycle.md:323 still reads the `labeled` event time `| last` (half 2 of #502; detect_stalls half shipped in #708). .claude/ edit, loop may do it. Not queued (capacity) | aa2e62f |
| 503 | stall routing: no independent-QA path for human-authored partial/ PRs, g | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 528 | privacy: the visitor's /ask question travels in the URL and is recorded  | IN FLIGHT: PR #801 (qa-pass) open. Do not queue | pr-list 11-08 |
| 560 | qa-on-green writes its 'dispatched at <sha>' marker before the dispatch, | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 567 | [INFRA] rashifal-generate's 3 h margin to the Groq fallback is smaller t | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 568 | [INFRA] agent-infra authenticates as agent-analytics, which holds no Clo | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 577 | verify_conflict_markers: the 8 MiB truncation and the 7-wide blockquote  | carried from 11-01 scan: latent loop/gate hardening; not queued (carried from 10-31) | — |
| 580 | [INFRA] detect_stalls counts stalls no cycle can act on as OBLIGED, so t | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 581 | numerology: name compound sums every letter; Cheiro adds each word's sin | QUEUE 4: name compound sums every letter (43 vs Cheiro's 16 for 'Lloyd George') reproduced; Evidence Block 6 FAIL. comment posted | aa2e62f |
| 582 | numerology: master numbers and Karmic Debt contradict the page's own Che | CONTESTED Cheiro vs Kumar: needs a chief ruling; Evidence Block 6 FAIL; not queued | — |
| 583 | numerology: Life Path 'Strong/Cautious months' for 2-9 trace to nothing  | astrology-correctness, needs-evidence; body read; tree not re-run; Evidence Block chain (Queue 2) then Queue 4 family | — |
| 584 | numerology: 0-100 compatibility and Bhagya scores rest on invented weigh | UNSOURCED weights; disclosure-shaped (cf #429); Evidence Block 6 FAIL; not queued behind Q4 | — |
| 594 | [UI] Top /learn landing article uses the raw path "/dasha" as link text | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 595 | [UI] /numerology result: 38 text nodes under 12px, down to 9px on the Lo | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 596 | [UI] Six form controls (subscribe modal, feedback widget, /learn search) | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 605 | test_rashifal_day_detail.py module-scoped fixture bypasses _offline_geoc | carried from 11-01 scan: outsider-by-rule on 11-01; NOW TRUSTED (author=claude App, resolve_provenance exit 0 @aa2e62f); not assessed this pass | — |
| 633 | The cycle agent can merge a needs-human-review PR or strip the label — a | QUEUE 7 (bundle w/ #413, #698): --disallowedTools at agent-work.yml:400 still lacks gh pr merge/edit/close, gh issue close | aa2e62f |
| 634 | Three inaccurate claims left by #629: an invented check_suite trigger, a | live, LOW: check_suite comment now at agent-merge.yml:566; fold into next agent-merge PR | aa2e62f |
| 641 | The `priority:` label is vestigial: written by nobody, read by one dashb | carried from 11-01 scan: NEW. `priority:` label vestigial; chore; not queued | — |
| 648 | Four accuracy defects left by #642's conflict reclassification — includi | PR #642 MERGED 2026-11-02 (latest.md said open); the test named at :169 no longer exists (grep empty) and detect_stalls was restructured; defects 1-4 NOT re-verified; likely partly overtaken; not queued | aa2e62f (PR state + one grep only) |
| 657 | qa-on-green aims at the branch-named issue without checking it is open,  | live: qa-on-green.yml still sets target=issue=$issue with no open check; low; fold into next qa-on-green PR | aa2e62f |
| 664 | [INFRA] No dispatch can clear a CONFLICTING PR that also carries a refix | loop-meta; merge_main_into_branch dispatch gap; not re-read; not queued | — |
| 666 | [MEASURE] The analyst job checks out at depth 1, so the required `git lo | live: agent-measure.yml checkout default depth (:74); analyst confound check; low; workflow edit | aa2e62f |
| 697 | [OPS] Build lane idle 89% of the last 7d | BLOCKED (owner lever: a cron line in agent-work.yml). detector: loop-idle 86%; quota now 22% so lever is affordable. comment posted | aa2e62f |
| 698 | [INFRA] agent-work's cycle step has no GH_REPO, so the agent runs `gh re | QUEUE 7 (bundle): cycle step env has no GH_REPO; `Bash(gh repo:*)` denies `gh repo view` (agent-work.yml:400-405). Install-Bun flake at 10:00Z is a different cause | aa2e62f |
| 700 | [CHORE] Retire the six legacy verify_contrast DECLARED_PAIRS rows, the c | chore: retire six legacy verify_contrast rows (follow-up to #262, whose file is gone); needs independent QA; not queued | — |
| 713 | muhurat: Panchak flags all of Dhanishta; Raman's Nakshatra Panchaka star | QUEUE 3: Panchak whole-Dhanishta reproduced; blocked from dispatch by Evidence Block (6 FAIL). comment posted | aa2e62f |
| 714 | muhurat: Janma Tara is scored a flat 'ok' — Raman makes it event- and se | QUEUE 3: Janma Tara 'ok' for groom reproduced; convention call (table vs disclose). Evidence Block 6 FAIL | aa2e62f |
| 715 | muhurat: Chandra Bala matches neither Raman's muhurta rule nor Rao's goc | QUEUE 3: Chandra Bala 6th='strong' in finder reproduced; split function; Evidence Block 6 FAIL | aa2e62f |
| 716 | verify_rule_citations scans only chart.py — muhurat.py still cites BPHS, | QUEUE 3 (same file): muhurat.py still cites BPHS (3 hits); verify_rule_citations.py has 0 muhurat refs. Evidence Block 6 FAIL | aa2e62f |
| 726 | [OPS] Claude weekly quota 86% used | CLOSED this pass (overtaken: quota window reset, seven_day 0.22/0.23, carrier posted ops-cleared 11-06) | aa2e62f |
| 733 | [CHORE] agent-design.yml never asks for an Evidence Block, so every desi | chore, needs-human-review: agent-design.yml never asks for an Evidence Block. SAME ROOT CAUSE FAMILY as Queue 2 -- fold in | — |
| 735 | [MEASURE] 14 GA4 sessions landed on /admin/* (13 on /admin/ops, a page d | measure: /admin/* GA4 sessions; admin_ops.html carries no analytics (template read) so source unknown; low | — |
| 740 | retrieval: key natal knowledge/ retrieval on yogas and doshas, not only  | needs-evidence: cycle premise-check 11-07 refuted thesis (yoga/dosha effect text is code, no recalled rule to delete; natal over TPM bucket). Not queued; part of #402 audit chain | — |
| 741 | retrieval: ground the ask* prompts in knowledge/ retrieval, after #706 ( | needs-evidence: cycle premise-check 11-08 refuted thesis (ask.txt has no recalled rules; ask+payload headroom +0). Sub-issue of #402 AC2. See #402 comment | — (read; headroom re-measured @aa2e62f) |
| 742 | retrieval: move the remaining prompts' recalled rules to knowledge/ retr | not queued: same family as #740/#741 (retrieval without a measured recall case) | — |
| 743 | security: verify_egress.py, an allow-list of runtime outbound hosts (spl | not recommended now: new security gate (split from #354), latent | — |
| 744 | security: verify_pii_egress.py, a sentinel sweep over every sink that le | not recommended now: new security gate (split from #354), latent | — |
| 751 | matching: five rules blocked on a source the corpus lacks (split from #1 | BLOCKED on a source the corpus lacks (acquisition task; #177 split). Evidence Block 3 FAIL | — |
| 759 | chief-cleared is applied with github.token, so agent-merge's label edge  | QUEUE 6: chief_clear.py never dispatches agent-merge; 1 FAIL left (no gsc/ga4; add `chore`). comment posted | aa2e62f |
| 770 | A test-count-drop ruling comment cannot turn gates green: nothing re-run | loop-meta, live per body (comment can't re-run gates); Evidence Block 6 FAIL; not queued | — |
| 773 | numerology.md: re-check AnkitNotes description and the K.N. Rao / Dasa c | BLOCKED: needs data/ (absent on loop runner) to re-check AnkitNotes + K.N. Rao claims; plus 2 copy items from QA (numerology.html:132 '1908-1940s') | — |
| 777 | Manglik tier ladder and the Venus-only downgrade need a source and an ow | QUEUE 5 (copy items a-c only; tier ladder stays BLOCKED on owner). comment posted | aa2e62f |
| 782 | [MEASURE] fetch_ga4.py cannot export events, so #570's cta_click metric  | started work (#785, #788 merged): every AC act done; propose CLOSE once an agent-measure run writes measurements/ga4-events.json (absent from tree @aa2e62f) | aa2e62f |
| 795 | [OPS] agent-work.yml is broken | CLOSED this pass (does not reproduce: 6 successes after 2 Install-Bun flakes; PR #800 measurement alerts=[]) | aa2e62f |
| 798 | [BUG] /festivals window starts at the UTC date (same shape as #593/#794) | IN FLIGHT: PR #799 (qa-pass) open. Do not queue | pr-list 11-08 |

## Scan-history row for BACKLOG.md

| 2026-11-08 | `aa2e62f` | 116 open at start, 114 after 2 closures (#795 does-not-reproduce, #726 overtaken); 7-item queue led by #402's remainder and a new "make auditor findings dispatchable" issue; 27 rows stamped, 89 carried as `—`; `data/` absent, production GET `/health` only, `measurements/sync/chief-guidance.md` absent |
