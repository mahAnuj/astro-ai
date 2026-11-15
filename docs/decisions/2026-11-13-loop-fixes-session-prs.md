# The loop fixes session PRs: a QA FAIL or red gates on a no-issue branch gets one fix run

- **Date:** 2026-11-13
- **PR / issue:** this PR (owner, in a session: *"yes, let the loop fix session PRs too"*)

## Why, measured

A PR whose branch names no issue (`claude/…`, `feat/…`, any session's) got a judge-only QA
round (`agent-cycle.md` Step 0c) and nothing after it. On a FAIL nothing pushed a fix, and
nothing ever would: `qa-on-green` fires when the GATES complete, a judge-only round pushes
nothing, so the gates never ran again. Red gates on such a branch got `qa-on-green: red gates
noted` and "a session has to push the fix". Measured on #951 on 2026-11-13: QA FAIL at
`8fc8642` naming one precise defect and its fix, and the PR waited for a session.

## What changed

| path | before | now |
| --- | --- | --- |
| QA round FAILS on a no-issue PR | nothing | `scripts/pr_fix_after_qa.py` (a `run:` step after the round) writes the marker and hands `fix_pr=<n>` to `dispatch_cycle.sh` |
| red gates on a no-issue PR | one "noted" comment | `scripts/red_gates.py` returns `target=fix_pr=<n>` |
| `fix_pr=<n>` | did not exist | `agent-work.yml` input, title "Agent work: fix PR #n", build lane; `/agent-cycle --fix-pr <n>` (Step 0d) fixes exactly the findings and pushes to the PR's branch |

The fix run writes **no verdict**. Its push re-runs the gates, and `qa-on-green`'s existing
"a fix landed after the FAIL" path dispatches a separate judge-only round on the new head, so
the independence rule holds: the run that wrote the fix never judges it.

**Limits, all enforced in code and pinned by tests and mutation rows
(`scripts/mutations/2026_11_13_fix_session_prs.py`):** at most **three** automatic fixes per PR,
counted from the `qa-on-green: fix dispatched at <sha>` markers both paths share, then a person
is told; one per head; only a FAIL from `claude[bot]` that names the PR's current head; never a
diff touching `.github/workflows/` (the App token cannot push one); never a fork, never an author
outside `AGENT_AUTHORS`. An issue branch is unchanged: the steward still routes its fix through
`issue=<n>`, and red gates on it still aim at the issue, with no cap.

**Cost:** one build cycle per failed round on a session PR, at most three per PR, from the same
Claude weekly window as every cycle. Before, that cost was a person's session.

**Rejected:** letting the Step 0c round push its own fix in the same run. It is cheaper by one
dispatch but makes the reviewer the author of the change it then has to pass, which is the
failure `qa` was split out to prevent.
