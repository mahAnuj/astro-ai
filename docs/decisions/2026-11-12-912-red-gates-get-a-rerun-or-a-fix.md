# A red PR gets a re-run if the runner flaked, a fix cycle if the code failed

- **Date:** 2026-11-12
- **PR / issue:** #912

## Why, measured

**The symptom.** Five open PRs sat with red gates for 9–20 hours:
- #899, #900 and #901 failed on a runner DNS blip. `apt-get install poppler-utils` could not
  resolve `security.ubuntu.com` (exit 100), so no test ever ran.
- #892 failed on a real `verify_architecture_counts` mismatch.
- #884 failed on a real `verify_behaviour` skip: a corpus test that can only skip in CI.

**Why nothing acted:**
- `qa-on-green` exits on red by design ("a red gate is information, not a stall").
- `detect_stalls.py` has no red-gates kind among its 15.
- Re-triggering CI with an empty commit is forbidden.

So every red PR waited for a human.

**Decision.** A new `red` job in `qa-on-green.yml` runs on `PR gates` **and** `verify-build`
concluding `failure` for a pull request. The existing green-path job is now gated to
`PR gates` only. `scripts/red_gates.py` decides:
- **rerun:** the failed jobs' logs show an infrastructure flake (DNS, apt fetch, runner shutdown,
  connection reset) and no test or gate verdict, so the code was never judged. Only on
  `run_attempt == 1`, so an outage is re-run once, not forever. An unreadable log is never called
  a flake.
- **fix:** a real failure on a branch naming its issue (`issue/`, `partial/` or `fix/` followed by
  `<n>-`), whose diff does not touch `.github/workflows/` (the cycle token cannot push there).
  One build cycle `issue=<n>` per head, through `dispatch_cycle.sh`, with a marker comment
  written first.
- **notify:** a real failure no cycle can fix, such as an owner branch or a workflows diff. One
  comment per head names the failing jobs.

The logic is deterministic and makes no Claude call. A fix spends one normal build cycle. No
permission changes: `qa-on-green` already holds `actions: write` and `pull-requests: write`.

**Checked against the real logs from that day:** both #899 jobs classify as flakes; #892 and #884
classify as real.

**Rejected:**
- **Retrying apt inside `pr-gates` and `verify-build`.** It narrows one flake source, but a red PR
  of any cause would still strand. Worth adding separately.
- **A `gates-red` kind for the steward.** It would cost a Claude run to decide what this script
  decides deterministically, and only after the steward's 4h age gate.
