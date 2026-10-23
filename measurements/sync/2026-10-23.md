## 2026-10-23 — sync

decisions:    #446 REOPENED (closed on merge of #448 with parts 2 and 4 undone and part 3's QA FAIL unaddressed — `ARCHITECTURE.md:758` still says "strictly stronger"; same shape as #405→#446, #447 open on it)
              #485 folded into #392 (same defect — chief's 10-22 ruling already calls it a duplicate); #457/#502/#503 are the same file, fold into the one cycle
              #278 stays folded into #279 (poppler half landed, `pr-gates.yml:157`)
              #426 (wrong Saturn/Jupiter dates, 3rd-ranked band page) — Standing ruling 3: "corrected or qualified, never left standing because the page earns traffic" — no escalation, ruling answers it
escalated:    none to chief (0 of 3 used). Checked: #426, #429, #430 → Ruling 3; #392 → Ruling 4 cl.3 already decided. The one real conflict is not chief's: chief ruled "dispatch a cycle at #392", and the owner's own provenance rule (`resolve_provenance.py`, bot author = OUTSIDER, no allowlist) refused it 2 min later. A ruling cannot cure that; only a human label can.
              → HUMAN: #505 (new, `needs-human-review`) for #279; `provenance:trusted` on #392, #426, #490
missed:       none declarable. #311/#329/#276 UNSCORED/INCONCLUSIVE ≥9 days — no export splits a page at its deploy date (#490, bot-authored, unbuildable). #124 (shipped 10-07) window closes ~11-04 with no per-page reader. #329: 3 organic sessions vs a floor of 10 — the metric, not the link, is the problem (idea untested, not wrong; measurement wrong).
              analyst scores this week: #400 HIT (count only), #397 PASS (first clause), #396 PASS (first clause), #373 PARTIAL, #374 UNSCORED (window ends 10-24) — behavioural clauses all "not checked"
blocked 2x:   #279 — THREE syncs (10-09, 10-16, 10-23), 0 assignees, 0 movement since 10-16. CI now holds 0/8 books (was 1/8). Costs: #402 (rank 1) not startable, QA runs without `data/`, citation mutation likely NOT EXERCISED. → #505 filed.
              #392 — outsider-labelled since 10-16; steward woke on it every run for a week; chief's one dispatch burned (agent-work run 39818019465 green, built nothing). First sync to name it; if unlabeled at 10-30 → needs-human-review issue.
              #402 — waits on #279 + #399 (no loader) + Arudha/D-24 extraction; nobody assigned to any.
closure audit: 20 closed since 10-16.
              evidence-backed (14): #452 #449 #473 #372 #476 #405 #400 #408 #397 #373 #393 #374* #421 #442   (*analyst UNSCORED, rescore ≥10-24)
              thin, stands (4): #409 (XSS fix in tree + serving build f8696b5 contains #425; no probe sent), #493 (effect unobserved — read 10-25 prioritise + 10-26 discover runs; discover's last run 10-19 FAILED), #472 (tests-only, macOS unverifiable here), #394 (merged with `qa-fail` still on PR; collector reasons 2–3 remain in `collect_loop_measurements.py:135,372` but tile now reads API via `ops_today.py` — not probed, /admin 401)
              residual w/o home (1): #396 — closed on merge of #410 while round 8 FAIL (L-1 tooltip, 8/12 mutants surviving) is still in tree (`admin_dashboard.html:257,323`) → propose one issue at /prioritise
              reopened (1): #446
pattern:      5 PRs merged by hand this week with `qa-fail` still on them (#425 #410 #454 #455 #448); label is write-only (#406), so the label no longer separates "failed" from "failed and fixed". 4 of the 5 closed their issue on merge with no comment.
              Machinery vs objective (Ruling 6): of 20 closures only 4 touch visitors (#409 #408 #397 #373); 0 are SEO/content against #267. 21 of 116 open issues are bot-authored (20 `app/claude`, 1 `app/github-actions`) and none can be built by the loop.
carried:      ~110 open unchanged. BACKLOG.md last prioritise run 10-18 (next 10-25). Prior-sync items still open: #124 (proposed closure 10-09; thesis unscored, needs 11-04), #278 (→#279), #361 (reopened 10-16; qa-pass + needs-human-review), #355 residuals.
note:         No SYNC_LOG.md exists in the tree; prior syncs (10-09, 10-16) live only as issue comments. This record is at /tmp/report.md as instructed; not committed. Local clone is shallow (1 commit), so "merged this week" in /tmp/week.txt lists only #504 — merges were read from `gh pr view` instead (#494 #481 #482 #487 #480 #474 #455 #454 #448 #443 #428 #425 #412 #410).
