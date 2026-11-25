# infra-reviewer report — 2026-11-25
Focus: free-tier headroom, deploy truth, latency. Read-only; no GCP or workflow changes made. No issues filed.

## Guidance row
`measurements/sync/chief-guidance.md` does not exist (measurements/sync has dated files and chief-2026-11-*.md). chief-2026-11-19.md has no infra row. No guidance followed or overridden.

## Deploy truth (exact tier) — holds
- Live /health, this run: revision bhagya-00866-fkf, build_sha 25a17ab55473a682df7af977bc7f8c988bb5ba48. `git log -1` on main is 25a17ab55473a682df7af977bc7f8c988bb5ba48. Exact match, so this commit is live.
- Last 30 verify-production runs: 30 success, 0 failed (29 workflow_dispatch, 1 schedule). Newest 2026-11-25T02:27Z.
- Anomaly, not investigated: no `push`-event runs among those 30. Dispatch is probably how the pipeline triggers them, but I did not check this.
- The trigger itself is unreadable (#568), so the tier is verified from /health and run results only.
- Stale text, already tracked in #340 (open, last updated 2026-11-10): .github/workflows/verify-production.yml lines 27, 207 and 838 still print `--set-env-vars=BUILD_SHA=...`. CLAUDE.md forbids that form because it wipes the Groq keys. Line 207 also describes a "REVISION-CHANGED" fallback. A reader who follows that text could break production. A workflow edit is outside this run's read-only scope; #340 stays the owner.

## Latency (probe taken this run, single samples)
- /probe.txt: / 0.65s, /kundli 0.61s, /matching 0.56s, /numerology 0.65s, /learn 308 at 0.51s (redirect to /learn/).
- My own curls: /health 0.42s, /learn/ 0.88s, /rashifal/mesha 1.04s, /static/sw.js 0.46s, /kundli GET 3x at 0.60–0.65s, all 200.
- These are page loads, not the natal POST. The 26s kundli figure and #266's 503s concern the LLM request, which I did not exercise because it spends the Groq budget. No new latency finding; I have no measurement of the natal path this run.

## Standing items (no new measurement, nothing re-filed)
- #266: now CLOSED. I did not re-measure the natal path, so I cannot say whether the capacity failure is fixed or the issue was closed on another basis. Needs a production natal POST measurement before the ceiling is called resolved.
- #212: still OPEN. I did not measure per-request tokens this run.
- #232 and #253: not in the open-issue search results (not confirmed open or closed). No measurement taken.
- Groq TPM/TPD, Cloud Run and GCS usage: not measured this run, because I have no access to those consoles from here. I give no multiples or headroom figures.

## GitHub Actions
- Recent 30 runs: no failures. "Report a red main" skipped (correct, main is green). One "Agent work" run is pending and one is in progress, which I take to be normal queueing.

## Recommendation
Nothing new. Next run should measure one natal POST with token counts to settle #266 and #212 with numbers.
