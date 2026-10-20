#!/usr/bin/env bash
# Carry out a recorded dispatch ruling: ONE `agent-work` cycle at ONE issue.
#
# WHY A SCRIPT, AND WHY BOTH ROLES SHARE IT
#
# An agent inside `claude-code-action` holds the Claude GitHub App token, and
# `gh workflow run` answers it HTTP 403 "Resource not accessible by integration"
# (#442, same root as closed #323). The `actions: write` in the workflow belongs
# to `github.token`, which is handed to `run:` steps and never to the agent. So
# an agent cannot dispatch; it can only RECORD a decision that a later step
# executes with a credential that works.
#
# chief had such a carrier from 2026-10-11 and the steward did not, although
# `steward.md` tells the steward to dispatch in six routing rows. The result was
# measured on 2026-10-20: the steward diagnosed four stalls correctly, was
# refused by the API, produced no action, and the accountability step woke chief
# to carry out a mechanical dispatch -- a full extra agent invocation to reach an
# outcome the steward had already decided. chief said so itself while ruling:
# this "makes chief the dispatcher by construction, which chief.md calls out as
# not its role".
#
# This is ONE script rather than a second copy of chief's step, because this
# repository's most reliable defect is a copied file diverging: `id-token: write`
# was missing from four agent loops that had each been copied from a fifth. A
# carrier whose two instances drift is the same bug with a worse blast radius.
#
# Usage:  dispatch_cycle.sh <ruling-file> <who> [--dry-run]
#
# EXIT CODES, so a workflow step can route on them:
#   0  dispatched and verified running; or nothing was recorded (a legitimate
#      ruling); or a cycle is already in flight, so this one defers.
#   1  a ruling was recorded and could NOT be carried out: unparseable, the
#      issue is not open, no run appeared, or the run died on arrival.
#   2  could not run: bad arguments.
set -uo pipefail

FILE="${1:-}"
WHO="${2:-a role}"
DRY=""
[ "${3:-}" = "--dry-run" ] && DRY=1

if [ -z "$FILE" ]; then
  echo "::error::dispatch_cycle.sh needs a ruling file path"
  exit 2
fi
if [ -z "${GH_REPO:-}" ]; then
  # Explicit, not `${GH_REPO:?}`: under `set -u` that exits 1, which this
  # script's own header documents as "a ruling could not be carried out" --
  # a different thing from "the step was wired wrong", and the caller routes
  # on the difference. A documented exit code that lies is a defect.
  echo "::error::dispatch_cycle.sh needs GH_REPO"
  exit 2
fi

if [ ! -s "$FILE" ]; then
  echo "$WHO recorded no dispatch. That is a ruling, not a failure."
  exit 0
fi

# STRICT PARSE. Anything that is not exactly `issue=<digits>` on the first line
# is refused rather than guessed at: the failure mode of a lenient parser here is
# dispatching a cycle at the wrong issue, which is ~50 Actions minutes spent on
# work nobody ruled on.
line=$(head -1 "$FILE" | tr -d '[:space:]')
issue=$(printf '%s' "$line" | grep -oE '^issue=[0-9]+$' | cut -d= -f2)
if [ -z "$issue" ]; then
  echo "::error::$WHO wrote an unparseable dispatch line: '$line'. Refusing to guess."
  exit 1
fi

# The issue must be OPEN. A cycle at a closed issue is the `cannot-reproduce`
# path burned at full cycle cost.
state=$(gh issue view "$issue" --repo "$GH_REPO" --json state --jq .state 2>/dev/null || echo MISSING)
if [ "$state" != "OPEN" ]; then
  echo "::error::$WHO ruled a dispatch at #$issue, which is $state. Not dispatching."
  exit 1
fi

# Never queue a second cycle behind one in flight. An unreadable answer counts as
# busy: guessing "not busy" is what spends the quota twice.
busy=$(gh run list --repo "$GH_REPO" --workflow agent-work.yml --limit 10 \
         --json status --jq '[.[] | select(.status != "completed")] | length' 2>/dev/null || echo unknown)
if [ "$busy" != "0" ]; then
  echo "::warning::a cycle is in flight (or the check failed: '$busy'). ${WHO}'s ruling at #$issue stands; it waits for the next run rather than queueing behind this one."
  exit 0
fi

if [ -n "$DRY" ]; then
  echo "DRY RUN: would dispatch agent-work at #$issue on ${WHO}'s ruling"
  exit 0
fi

before=$(gh run list --repo "$GH_REPO" --workflow agent-work.yml \
           --limit 1 --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || echo 0)
gh workflow run agent-work.yml --repo "$GH_REPO" -f issue="$issue"
echo "::notice::requested agent-work at #$issue on ${WHO}'s ruling; verifying it started"

# `gh workflow run` EXITS 0 ONCE THE RUN IS CREATED and says nothing about
# whether it then did anything. That is how #421 stayed invisible for three days:
# the action refused a Bot actor 1.5s in, the run concluded `failure` in ~33s, and
# the step reported "carried out" every time. A dispatch nobody can tell from a
# no-op is worse than no dispatch, because the stall detector then sees that a
# cycle was tried.
run_id=""
for _ in $(seq 1 12); do          # up to ~60s for the run to appear
  sleep 5
  cand=$(gh run list --repo "$GH_REPO" --workflow agent-work.yml \
           --limit 1 --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || echo 0)
  if [ "$cand" != "0" ] && [ "$cand" != "$before" ]; then run_id="$cand"; break; fi
done
if [ -z "$run_id" ]; then
  echo "::error::dispatch at #$issue created no new agent-work run within 60s. Not reporting it as carried out."
  exit 1
fi

# A real cycle runs for tens of minutes, so anything `completed` inside this
# window concluded without doing a cycle's work.
for _ in $(seq 1 18); do
  sleep 5
  read -r status conclusion <<<"$(gh run view "$run_id" --repo "$GH_REPO" \
    --json status,conclusion --jq '"\(.status) \(.conclusion // "")"' 2>/dev/null || echo "unknown ")"
  if [ "$status" = "completed" ]; then
    echo "::error::agent-work run $run_id concluded '$conclusion' within 90s of dispatch at #$issue -- it did not run a cycle. See #421."
    exit 1
  fi
done

echo "::notice::agent-work run $run_id is running a cycle at #$issue"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "DISPATCHED=$issue" >> "$GITHUB_ENV"
  echo "DISPATCHED_RUN=$run_id" >> "$GITHUB_ENV"
  echo "DISPATCHED_BY=$WHO" >> "$GITHUB_ENV"
fi
