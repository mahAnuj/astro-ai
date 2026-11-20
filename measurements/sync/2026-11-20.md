## 2026-11-20 — sync
(first block: no SYNC_LOG.md exists in the tree, so there is no prior sync to compare against. Window 2026-11-13..20.)

decisions:    #1284 + #1221 are one component (main-red-report): #1284 stops false [MAIN-RED] on cancelled runs, #1221 fixes runs it never sees. Two false reds closed this week as cancelled-not-failing (#1146, #1307). Rank them together; #1284 first. No merge, different defects.
              #1243 stays open: the stale §29.14 row is a prose-only knowledge edit, so it needs its own trust-boundary PR and a QA round. #1242 shipped the code.
              #1076 closure proposed by project-manager (onset dated 2026-10-19, no on-site cause). Endorsed. /prioritise closes it.
              #1219 cleared; root cause (close-on-evidence only closed the verified SHA's own PR) fixed by the 2026-11-18 "a later live commit counts" change. No action.
escalated:    none to chief this cycle (0 of 3 used). Every candidate was already ruled: the fetch-depth chain is closed-list item 1 (CLAUDE.md, `chief` grant, #421), so the single act is the owner's, not chief's.
              Contradiction check Research vs Growth: none. Open growth issues are #1065, #1076, #1107, all structural/SEO and carrying no astrological claim. The unsourced-rule issues (#1028, #1029, #751, #178, #914) have no growth issue built on them.
missed:       #311 (MISS, old): title/meta test on 4 band pages, closed. Idea vs execution not re-judged here. The #1236 HIT (7/7) is the only HIT in the ledger.
              No new MISS this week: 18 of 38 verdicts are PENDING and 10 are UNSCOREABLE. #1217, #1226 and #1229 first score on 2026-12-19. #1178, #1176 and #1177 are structural counts and cannot be scored from GA4/GSC.
blocked 2x:   WORKFLOW CHECKOUT DEPTH: #974 (blocked at 3+ syncs already), #666, #1205, #953, #1237, #1208 and #1065's last step all wait on one `fetch-depth: 0` edit in agent-sync.yml and agent-measure.yml. Owner act #1 (App token has no `workflows` permission). Evidence this run: `git rev-list --count HEAD` -> 1 and `git rev-parse --is-shallow-repository` -> true, so this sync's own week.txt lists 1 merged commit while `gh pr list --state merged` shows 100 PRs merged since 11-13. #974 already carries needs-human-review and the owner's single act. project-manager (#1065, 11-19) proposed one session-authored PR carrying every workflow half. Endorsed; that is the one thing to do.
              #1207 round 3 stood down: the harness refused writes to `.claude/commands/agent-cycle.md` (plan step C, "a stand-down always leaves a trace"). The edit text is ready on the issue. Owner act: approve that exact `.claude/` text. Not on the closed list, so `chief` may rule on it.
carried:      seo-growth gap: seo-growth should file the 29 "Crawled - currently not indexed" /learn pages and the never-crawled /dasha, /muhurat and /panchang (from #1065's capture, noted as not yet filed). Quota: Claude weekly 85% (#949 amber, cleared once, left open). #1284, #1283 (high) and #1282 (high) are open QA follow-ups, rank them. Several qa-pass issues stay open after PARTIAL slices (#1105 and #1163 confirmed from their last comments): by design.

### Closure audit (closed since 2026-11-13, 40 inspected, last comment read)
- Most of the 40 (counts below are approximate, I did not tally them) were closed by close-on-evidence with PR, verify-production run and `/health` build_sha: evidence real. (#1301, #1300, #1294, #1292, #1277, #1261, #1232, #1188, #1185, #1178, #1177, #1176, #1167, #1160, #1159, #1141, #1139, ...).
- 7 [main-red] sentinels closed with "Green again at <sha>" + run URL: evidence real (#1274, #1249, #1216, #1211, #1191, #1181, #1152).
- Retrofit closes by project-manager with command output: #1307, #1146, #1192 (all cite `gh run view`/`git log` output). Real.
- #1186/#1187 closed by the owner's session sweep, with build_sha, compare=ahead and run id. Real. #1247 closed by the owner as duplicate of #1246 with cause. Real.
- #1111 and #1112: closed NOT_PLANNED by the owner on 2026-11-15 with 0 comments; the reason lives on the epic #1108 (Razorpay deferred, owner's words quoted). Owner decision, not a bare "fixed". No action.
- #1302: the last comment is a merge note saying "Not closing this", yet the issue is closed. I did not find the closing evidence in the last comment and did not read the earlier ones. /prioritise should re-read #1302. Nothing reopened.
- #1226, #1229, #1217 and #1236 are closed with analyst timers/scores last, not closure comments. Each had a close-on-evidence comment earlier. No reopen.
- No closure found that says only "fixed". No reopen proposed.

### Learning review (lessons.md, llm-usage.json)
- grounding (31 QA FAILs) and regression (32): action = no new action. Both are current-rule failures that QA catches before merge, and 0 reverts on main. Cheapest lever is already in the Evidence Block/QA gate.
- tests (29), tokens (21): action = issues #1254, #1255 and #1256 already exist (tokens: step-loading, 26/123 re-entered cycles, code index). Priority high. Rank them first among chores. No new issue.
- security (15): no action; #1172 shipped, privacy chain #1159/#1160/#1292 landed, #1293/#1315 follow-ups open.
- copy (20, QA FAILs from #536 to #1077): the week's cluster #1300/#1301/#1302/#1313 shows the same defect, "classical text/tradition" phrasing in templates, closed one page at a time. Proposed action (definition fix, to file): add to frontend-engineer.md a single `grep -rn "classical tradition\|text we follow\|/matching tool" src/astro_ai/templates` sweep before handing back, since 4 follow-ups came from a single phrase pattern. Not filed here: the sync token can't author `.claude/` text; the issue is for /prioritise to file with the ledger lines #1300 #1301 #1302 #1313.
- LLM budget: hit rate 79% (136/171). `ask` is 0% (22 calls, 2078 tokens/call, ~46k in). `ask` answers are personal, so caching is not available. No new Groq call proposed. `rashifal` shows null tokens on 28 calls (unmeasured): proposed action = #1208 (export LLM fallbacks/reasons) is the right lever and is blocked on the checkout-depth chain above. Peak day measured 43k tokens on 2026-11-18; #925 tracks the 83% daily-budget finding.
- Competitor patterns: only #835 (closed) listed; nothing untried. No action. No astrological claim imported.
