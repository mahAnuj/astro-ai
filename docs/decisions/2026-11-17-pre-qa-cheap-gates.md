# A build cycle runs pr-gates' cheap checks itself before it dispatches QA

- **Date:** 2026-11-17
- **PR / issue:** none yet. Owner's item, 2026-11-17: "Run the cheap gates before QA. The cycle
  runs the fast checks (counts, citations, permissions) itself before dispatching QA."

## Why, measured

agent-work run 44020807802 (#1067 / PR #1150) took three QA rounds. Rounds 1 and 2 each failed
only on a stale `ARCHITECTURE.md` line (a stale sentence, then the template count 58 -> 59). That
is a `scripts/verify_architecture_counts.py` failure, and that script finishes in 8.5s. Each QA round
is a separate agent with full context, so two rounds were spent on what a script could have caught.

`scripts/pre_qa_check.py` runs the 32 `scripts/verify_*.py` gates in pr-gates' sweep that need no
server, browser or live LLM, four at a time, plus `pytest -q -x` on the tests the diff touches.
`/agent-cycle` runs it before every QA dispatch, re-QA after a fix included, and before Step 0d's
push (that push earns a QA round). Measured locally: the slowest gate is 39.8s
(`verify_muhurat_tables`), and the sequential sum is about 170s.

Left to pr-gates: `verify_behaviour` (the whole suite, 152.7s; the diff's own tests run instead),
`verify_devanagari_serif` and `verify_lang_switch_browser` (both need the app serving), the two
live-LLM gates, the mutation sweep and prompt evaluation.

Rejected: parsing the gate list out of `pr-gates.yml` at run time. pr-gates has no list, only a
glob minus exclusions, so the script keeps an explicit FAST/SLOW partition instead.
`tests/test_pre_qa_check.py` fails when a `verify_*.py` is missing from that partition, so a new
gate cannot be skipped silently.

Not named `verify_*`, because pr-gates runs every such script as a gate (PR #1063 went red that way).
