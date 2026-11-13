## 2026-11-13 — sync
Read from the issue trail, `measurements/` and `gh`, not from `AGENT_STATUS.md` or `BACKLOG.md`. `SYNC_LOG.md` is not in the checkout; the previous block on disk is `measurements/sync/2026-11-06.md`, and "blocked twice" is judged from that and from `chief-2026-11-10.md`. `data/` is absent here, so no corpus absence is claimed. `/tmp/week.txt` lists 1 merged commit; the PR list in the same file shows ~48 merged code PRs plus ~25 measurement PRs.

decisions:
- **Escalate the depth-1 checkout (#974, `needs-human-review`).** Named at three syncs running (11-06 sync, 11-10 chief, today) and unactionable by any agent: it is a workflow edit (owner act #1, #421). #666 covers `agent-measure.yml` only; `agent-sync.yml:41` has the same defect and had no issue. The owner's single act is in the first sentence of #974.
- **Do not merge #911, #918, #931, #664, #657, #770 into one issue.** All six strand a cleared PR, but the roots differ (sweep order; a cancelled pending slot; a missing `workflows` permission; a conflict; an unchecked branch name; a gates re-run). Merging them would hide which fix is which. Each carries its own repro.
- **#777 (Manglik tier ladder, unsourced) is answered by standing ruling 3, not an owner decision.** Quoted on the issue: *"A user-facing claim that cannot be sourced is corrected or qualified… Qualify first."* The owner is needed only to REMOVE or REGRADE (act #4). The qualification is buildable now. Escalations used: 0 of 3.
- **Contradiction check: none that two leads cannot resolve.** Research says the ladder is UNSOURCED (#429/#777); nothing Growth filed this week promotes a Manglik feature (the SEO work is #835 on debilitated-sun-career, whose unsourced court framing #941 was fixed by #948 before the FAQ shipped as #940). #150's remainder (Yamaganda, Brahma Muhurta) is blocked on sources, and nobody promotes it.
- **#966/#967/#970/#972 are slices of #327, not duplicates.** #966 closed correctly on production evidence at `f0358a5`; #327 stays open for the rest.

escalated: **#974 → owner (act #1).** Not to chief: chief cannot author a workflow and the ruling is already made.

missed:
- **#311 scored by the analyst on 2026-11-13: MISS, 0.937% (53/5,658) vs the 1.5% bar, baseline 0.574%.** Verdict unchanged from 11-06: **the idea was wrong, not the execution.** CTR improved (+63% relative) but the bar sat above what position 6.75 yields; position, not title copy, is the objective metric ("top 5"; 0 of the ten highest-impression pages are at or under 5.0). Same remedy: no title-only issue until #685 is scored (about 12-04). #835 is an answer-first FAQ, not a title test, and is pending to 12-14.
- #276 and #329 are not scoreable until 11-14 and will likely be unscoreable at 3 organic sessions. No other new verdicts.

blocked 2x (or worse):
- **#974 (checkout depth): three syncs, now filed.**
- **The `needs-human-review` design queue: #263, #233, #203, #198 (and #733, 0 comments since 11-06) untouched since August/September, third review in a row.** Chief's 11-10 instruction (one comment per issue naming a single owner act, or close) was not followed. Proposed for `/prioritise` rather than another chief round: **#233 and its ten sub-issues #242–#251 look overtaken.** CLAUDE.md says the #233 redesign "landed across every screen", yet all eleven are open with no activity since 09-04. I did not verify this against production; `/prioritise` must, and close with evidence or say what remains.
- **Source acquisition: #178 (10+ weeks), #751 and the rest of #150 wait on books the corpus lacks.** Progress this week: #914 extracted Muhurta Chintamani and #962 put `matching.py` under the citation gate. #178's own thread recommends dropping the `[BLOCKER]` label since it gates nothing.

closure audit (66 issues closed 2026-11-06T22:00Z → 11-13, closing comments read; closer and time from issue events):
- **A checkable record on 62 of 66** (the other four are below; #876 is the thinnest of the 62: a PR but no closing comment). 49 carry `close-on-evidence`'s comment naming `verify-production` and `build_sha` (checked by string, not re-verified against `/health` per SHA). Three `[main-red]` sentinels (#865, #919, #935) closed by the carrier with a green gates run link. #795 and #726 closed by `/prioritise` with live probe output. Session closures with a command and a SHA: #868 (`688681 143` vs `0 119` when filed), #803, #782 (`cta_click`: 4 events), #580, #560, #503.
- **Four closed within 3s of their PR merging, before `verify-production` could run: #732, #826, #852, #912.** All four PR bodies say `closes #N`, which `agent-cycle.md:584` mandates. Filed as **#975** with a table. It is NOT a one-line fix: 44 other closures in the same window did wait for the carrier, and their bodies say the same, so the keyword does not discriminate; 3 of the 4 were merged by the owner's account.
  - **#732:** closed directly under the carrier's own "Not closing this" comment (the #518 shape from last sync). Outcome fine: the focus rule is on `main` (6 hits) and production is on later commits.
  - **#912:** merged carrying `qa-fail` after an independent QA FAIL on a wording defect that **is still on `main`** (`qa-on-green.yml:49` and the decision file describe a `red` job; only `consider` exists). Behaviour passed (4091 tests). Commented; proposed a small follow-up, which needs a pushing session. Not reopened.
  - **#852:** closed at merge; thesis (Groq rashifal tokens down) unmeasured: `llm-usage.json` is a 7-day window ending before the fix. Commented; **reopen if the first window after 2026-11-12 does not show rashifal Groq input tokens down about tenfold.**
  - **#826:** closed at merge with no closing comment (only the retrofit Evidence Block). Substance is in PR #846. Not reopened.
- **No "fixed"-only closures found.** #876 was closed by the owner with only an ops-state comment above it, after PR #899; the same finding re-fired as #936 (cleared by the carrier at 19:42Z, still open).

learning review (`lessons.md`, `llm-usage.json`):
- **QA-FAIL themes (copy 18, grounding 18, regression 19, tests 18, tokens 17, i18n 8, performance 8, security 9; 81 FAILs in 30 days).** The ledger is a cumulative 30-day count and I did not diff it against 11-06, so I cannot say which themes grew this week. Action: **no definition fix.** The week's FAILs I read that cited a cause were caught as intended by `qa` (#913 wording; #853 mutation row that could not go red; #833/#845/#859 grounding), i.e. the check working rather than an instruction causing the repeat. Chief's 11-10 instruction stands: a new mutation row is shown red before PASS.
- **Definition fix: none proposed.** #975 points at `agent-cycle.md:584` but the root cause is not established, so no `.claude/` edit is proposed yet. Proposing one now would be a guess.
- **MISS #311:** above. **Competitor patterns:** one in 30 days (#835, tried, shipped as #940 on 11-13, scoreable 12-14). No untried pattern exists; the pipeline is thin on this input. Action: none; `/discover` should file more competitor-pattern issues if it wants this review to have anything to read. No astrological claim imported.
- **token-ceiling (#925, 83% peak, 166,053 tokens on 2026-11-09):** that day precedes #853 (merged 11-11), which moves rashifal generation into a scheduled Claude Code job, the cheapest lever. Rashifal is 87% of Groq input tokens (599k of 689k). **No action until a post-fix window exists**; then re-read, and close #925 if the peak is under 80%. `cache-low` not raised: overall 76%, natal 91%, rashifal 64%, `ask` 0 of 13 (each question is unique; no action).
- **Quota:** `seven_day` reached 85% (#949) and 86% (#726) in the last two windows, and is 0.12 at 21:43Z on 11-13, 15.7h after the 06:00Z reset. That is about 0.18/day linearly, so another ~85% week is the likely outcome. The 70% chain guard stops chaining, not QA rounds or merges. So the weekly window binds: **do not open a second build lane** (#697's lever), and read idle build hours against that. Carry.

proposed closures (for `/prioritise`, each a carrier that cleared itself, not closed by me): **#949** (quota reset, `ops-cleared` 15:27Z, 0.12), **#807** (`ops-cleared` 11-10; last six `agent-work` runs success), **#936** (`ops-cleared` 19:42Z). **#151** stays open (remainder is the significance layer, narrowed 11-08). **#925** after its post-fix window.

carried:
- #697 (idle 76% with the quota binding), #151, #685/#426/#835 scoring (12-04, 12-14), #570 (`cta_click` readable since #782, window clean 12-04), #666 (now with #974).
- #971 (natal.txt Manglik frame, trust-boundary hold) is `qa-pass` with green gates and waits for chief at 22:46Z; not stalled.
- #402 (priority:high, 23 comments, `qa-pass`, open since 10-17) not re-read; flagged for `/prioritise`.
- Unchanged and not re-read: about 75 other open issues (103 open).

filed this sync: #974 (`needs-human-review`, owner act #1), #975. Commented on #912, #852, #666, #777. Nothing closed, reopened, labelled or pushed.
