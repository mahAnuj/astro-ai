## 2026-10-30 — sync
Read from: `gh issue view --comments`, issue events API, PR bodies, `gh run list`, live `/health`.
Not read: AGENT_STATUS.md, BACKLOG.md (last scan 2026-08-25). No SYNC_LOG.md exists in the tree, so
"blocked 2x" is taken from the 2026-10-23 sync comments (#493, #505, #279), not from a log.
Checkout is shallow (1 commit): "merged this week" comes from `gh pr list`, not `git log`.

Week: 78 PRs merged (43 measurement, 21 owner, 14 loop). 136 open issues (30 filed this week, 57 untouched >14d).
Production serves `ff861450` (= #609 merge) per `/health`, so every merge before it is live.

decisions:
  - #362 — closure is wrong, propose REOPEN. Closed by owner 2026-10-24T00:00:50Z, one second after PR #492 merged.
    #492 said `refs #362` and "deliberately does not close #362". The last cycle comment lists what is still open:
    A2 (eval), Part B (PR-author provenance + `gate:prompt` label), AC4-6, AC8. No open issue carries any of it
    (searched titles; #327/#230 are adjacent, not these). That work is now orphaned. Not reopened by me: the
    close was an owner act, not close-on-evidence or project-manager. Owner call: reopen #362, or file the remainder.
  - #515 — same shape, propose REOPEN. Closed by owner at the merge second of #516 (2026-10-24T09:22:10Z).
    #516's body: "refs #513, #514, #515 — all three stay open", titled PARTIAL / unverified in production.
    #513 and #514 are still open; only #515 was closed. Analyst scored it NOT SCOREABLE on 10-25, 10-28 and 10-29
    (0 post-deploy days of data; rescore on/after 2026-11-21). A thesis with an unmeasured outcome is not closed.
  - #493 — closure stands, but the check set last sync is only half answered. 10-23 sync said: read the next
    `agent-prioritise` (10-25) and `agent-discover` (10-26) runs; reopen if green with no report. Neither is green:
      prioritise 10-25 FAILURE (exit 1 before any report; `measurements/prioritise/` still holds only 10-08.md)
      discover 10-26 FAILURE in `persist` ("could not enable auto-merge") — but `measurements/discover/2026-10-26.md`
      exists, so the dispatch now works; the failure is #557 (open), not #493.
    The "empty run goes red" half of #493 is observed working. "prioritise writes a non-empty report" is not:
    no prioritise report since 10-08 despite a 10-18 success. Needs an owner: someone to read run 40225736898.
  - Closure audit, 15 closed in the last 7 days. None is the #143 failure (a bare "fixed"). Breakdown:
      close-on-evidence: #388 — all three facts present (PR #600, verify-production success on c932a8bc,
        /health build_sha = c932a8bc). Clean.
      project-manager: none this week.
      keyword auto-close at merge (not either mechanism): #495, #607 — closed by github-actions[bot] at the merge
        second, while agent-merge's own comment on each says "Not closing this". The comment is false.
        Substance is fine (scripts/.claude only, never ships; #607's merge commit is the one `/health` reports).
        Same class PR #562 taught `loop-outcomes` to excuse. Defect is the contradictory comment, not the closure.
      owner closes at merge, no closing comment: #384, #387, #430, #493. #384 (scripts-only) fine. #387 and #430
        shipped under src/ and verify-production was green on 7e075538 / 2949686f, but nothing on the issue says so.
        #430's "left undone" item 3 (Gate 8 gap, cache-version-bump guard "worth its own issue") — I found no issue.
      owner "Audited complete 2026-10-30" batch, five closes in 12 seconds (17:25:09–20): #573, #510, #468, #465,
        #389. Comments name file:line, but only #389 quotes command output. I spot-checked from the
        tree: #510 `q-fold` present (17); #468 saturn/ketu wording matches the comment, `festival_registry` in
        verify_natal_prompt.py; #465 no "universal/classical/safe" on Vishnu Sahasranama, Sri Yantra keeps it.
        All consistent. NOT checked by me: #573's four criteria, #389's live 'rows 533 -> 535' output
        (`uv run` printed nothing here).
      owner decision: #505 — decision recorded verbatim, defect fixed by #507 (merged). Clean.
      #472 (10-22, test-only macOS fix) and #394 closed with 0 comments; low stakes, not reopened.

escalated:   none. Candidate contradiction checked and already ruled:
  - #518 (qa-pass, routes /learn traffic to /kundli /matching /numerology, 0 tokens, corpus n/a) vs open UNSOURCED
    findings on those tools (#581-#584 numerology; #429 Manglik; #175 Vashya). chief.md Standing ruling 3:
    "Authenticity wins on the claim; traffic wins on the roadmap … What to build next is ranked on traffic.
    What is already shipped is ranked on truth." So #518 may proceed and the claims are fixed on their own issues.
    Not escalated; no escalation budget spent (0 of 3 used).
  - #508 (/matching title/meta test) — no open UNSOURCED finding against /matching's copy (#397 closed). No conflict.

missed:
  - #515 / #516 — cannot score. Metric 1 (forbidden-planet share 31.0% → <5%) is a blob measurement nobody has taken;
    metric 2 has 2 post-deploy days. Idea vs execution: undeterminable until 2026-11-21. Baseline: 0 organic
    sessions to /rashifal*, GSC /rashifal 130 impressions, 0 clicks, position 10.2.
  - No shipped thesis scored a miss this week.

blocked 2x:
  - #279 (CI corpus) — owner ruled on 10-23 (#505): CI never needs data/; #507 merged. #279 itself still open with
    `needs-human-review`, untouched 7 days. Its own last comment says it can close as won't-do under the ruling
    "— that is the owner's call". Second consecutive sync with no owner action. PROPOSED CLOSURE: close #279 as
    won't-do under the 10-23 ruling, unless something other than citations reads data/ in CI.
  - #362 remainder (A2 eval, Part B) — see decisions; blocked on nobody because nothing tracks it.
    If not reopened or refiled by next sync it files `needs-human-review`.

carried:
  - Open PRs with `qa-fail`: #606, #564, #550, #544 (open 0-4 days; #564/#550/#544 updated 10-30 18:25Z).
    Not diagnosed here; steward owns it. Next sync: any still `qa-fail` with no new commit.
  - Four numerology UNSOURCED issues #581-#584 (filed 10-28, unworked) and #429 (Manglik ladder): shipped
    claims, ranked on truth per ruling 3. Highest-severity class this loop produces; none has a PR.
  - 57 issues untouched >14d; BACKLOG.md 2 months stale (36 vs 136 open) — /prioritise's job.
  - Worth a human look (new, not filed): agent-merge's "Not closing this" comment is emitted even when the PR carries
    `closes #N` and GitHub closes it in the same second. Either gate the comment or drop the sentence.
