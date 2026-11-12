# One repository variable, LOOP_PAUSED, pauses every Claude-spending loop job

- **Date:** 2026-11-11
- **PR / issue:** #903

## Why, measured

**The owner's words.** "there should be a pause/resume button for loop. If I want to save the
tokens for claude."

**Before this change.** Ten jobs run `claude-code-action`. Nine belong to the loop:

- `agent-work`
- `agent-steward`
- `agent-prioritise`
- `agent-discover`
- `agent-design`
- `agent-infra`
- `agent-research`
- `agent-sync`
- `agent-measure`'s analyst

Pausing meant disabling each one in the Actions tab and re-enabling each one later. Meanwhile the
deterministic dispatchers kept firing into the disabled workflows and spent their
one-per-commit markers on runs that never happened.

**Decision:**
- **The switch.** The repository variable `LOOP_PAUSED`. Set it to `true` to pause; delete it, or
  set anything else, to resume. It lives in Settings → Secrets and variables → Actions →
  Variables, and /admin/ops links to it from the Claude quota strip.
- **Every loop job that runs Claude** carries `vars.LOOP_PAUSED != 'true'` at the front of its job
  `if:`, so a paused run is skipped and spends nothing.
- **Their persist and propose jobs** (`if: always()`) also skip when the parent was skipped. They
  would otherwise run on no output.
- **`dispatch_cycle.sh` treats "paused" as "busy".** A QA round or a steward or chief ruling made
  while paused is QUEUED (`cycle_queue.py`), not dropped. Every step that calls the script is
  passed the variable.
- **`agent-queue` neither drains nor chains while paused.** After resume, the first `agent-work`
  completion drains the queue as usual.

**Deliberately not paused:**
- **`rashifal-generate`.** Pausing it hands the day to Groq. That is a separate decision from
  saving loop tokens.
- **The jobs with no Claude cost:** `agent-measure`'s collectors (they keep the quota reading the
  owner pauses on fresh), `pr-gates`, `verify-build`, `agent-merge`, `close-on-evidence`,
  `qa-on-green`.

**Rejected:**
- **A button inside /admin/ops.** The public web app would have to hold a GitHub token that can
  write repository settings: a new secret and scope (owner act #3) and new attack surface, for a
  click the Settings page already gives.
- **A "pause" workflow that flips the variable.** `GITHUB_TOKEN` cannot write repository
  variables, so that needs the same new secret.

**Known limit.** `agent-merge` wakes `agent-steward` once per held head. If that wake lands while
paused, the steward run is skipped and chief hears of the hold at the next steward run after
resume.
