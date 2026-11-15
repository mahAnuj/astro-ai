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
# The ruling file's first line is EXACTLY ONE of:
#   issue=<digits>   work this issue -- a full delivery cycle
#   pr=<digits>      run ONE QA round on this pull request
#   fix_pr=<digits>  FIX this pull request's QA FAIL or red gates and push to
#                    its own branch (agent-cycle.md Step 0d, since 2026-11-13)
#
# The second form exists because a QA ROUND NEEDS A PR, NOT AN ISSUE. See the
# parse below for the two PRs that proved it and for why the target is never
# read out of a PR body.
#
# EXIT CODES, so a workflow step can route on them:
#   0  dispatched and verified running; or nothing was recorded (a legitimate
#      ruling); or a cycle is already in flight, so this one is QUEUED
#      (scripts/cycle_queue.py) and started when that cycle completes.
#   1  a ruling was recorded and could NOT be carried out: unparseable, the
#      target is not open, an `issue=` ruling named a pull request, no run
#      appeared, the run died on arrival, or it could not be queued.
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

# STRICT PARSE. Anything that is not exactly `issue=<digits>` or `pr=<digits>`
# on the first line is refused rather than guessed at: the failure mode of a
# lenient parser here is dispatching a cycle at the wrong target, which is ~50
# Actions minutes spent on work nobody ruled on.
#
# TWO RULING FORMS SINCE 2026-11-01, because A QA ROUND NEEDS A PR, NOT AN ISSUE.
# `qa-on-green` could only aim a round at an issue number read out of the branch
# name, so a green PR on a branch carrying no number -- `feat/ops-watcher-detector`
# (#639), `fix/mutation-row-floor-total` (#647) -- was never dispatched at all,
# and `agent-merge` will not merge without `qa-pass`. Both sat green, unlabelled
# and unmergeable by anything, permanently.
#
# THE TARGET IS NEVER SCRAPED FROM A PR BODY, and that was measured rather than
# assumed. Reading `closes #N` / `refs #N` out of the body was the cheap
# alternative; run against the two real PRs it gives nothing at all for #639,
# and for #647 it yields `638` and `640` -- from the prose line
# "#636  resolved   #638  resolved" -- BOTH OF WHICH ARE PULL REQUESTS, #638
# merged and #640 closed. `gh issue view` answers for a PR number, so the
# openness check below would pass and this script would dispatch a ~50-minute
# cycle at a merged pull request. That is exactly what the strict parse exists
# to refuse, so the leniency is kept out of the caller too.
#
# `tr -d '[:space:]'` already collapses the line, so `pr=647 issue=1` becomes
# one token that matches neither anchored pattern. Exactly one key, exactly
# digits, or refused.
line=$(head -1 "$FILE" | tr -d '[:space:]')
# A third form since 2026-11-13: `fix_pr=<n>`, a FIX on a PR whose branch
# names no issue (owner: "let the loop fix session PRs too"). It pushes, so
# it runs in the build lane below, and it is checked as a PR, not an issue.
match=$(printf '%s' "$line" | grep -oE '^(issue|pr|fix_pr)=[0-9]+$' || true)
kind=$(printf '%s' "$match" | cut -d= -f1)
target=$(printf '%s' "$match" | cut -d= -f2)
if [ -z "$target" ]; then
  echo "::error::$WHO wrote an unparseable dispatch line: '$line'. Refusing to guess."
  exit 1
fi

# The target must be OPEN. A cycle at a closed issue is the `cannot-reproduce`
# path burned at full cycle cost; a round on a merged PR is worse, because there
# is nothing left to label.
#
# THE NUMBER SPACES OVERLAP, which is why the two arms do not share a lookup.
# `gh issue view <pr>` ANSWERS for a pull request, so an `issue=638` ruling
# passed this check whenever PR #638 happened to be open -- latent before, and
# newly reachable now that a `pr=` form exists beside it. So an `issue=` ruling
# additionally checks the URL: a `/pull/` in it means the ruling named a PR
# while claiming an issue, and guessing which was meant is the thing this
# script does not do.
case "$kind" in
  issue)
    state=$(gh issue view "$target" --repo "$GH_REPO" --json state --jq .state 2>/dev/null || echo MISSING)
    url=$(gh issue view "$target" --repo "$GH_REPO" --json url --jq .url 2>/dev/null || echo "")
    case "$url" in
      */pull/*)
        echo "::error::$WHO ruled \`issue=$target\`, but #$target is a PULL REQUEST ($url)."
        echo "::error::Issues and PRs share one number space. Rule \`pr=$target\` if a round was meant."
        exit 1 ;;
    esac ;;
  pr|fix_pr)
    state=$(gh pr view "$target" --repo "$GH_REPO" --json state --jq .state 2>/dev/null || echo MISSING)
    ;;
esac
if [ "$state" != "OPEN" ]; then
  echo "::error::$WHO ruled a dispatch at $kind #$target, which is $state. Not dispatching."
  exit 1
fi

# Never DISPATCH a second cycle behind one in flight. An unreadable answer counts as
# busy: guessing "not busy" is what spends the quota twice.
#
# PER LANE since 2026-11-03: a `pr=` QA round runs in `agent-work-qa` and is
# busy only behind another QA round; everything else is the build lane. Runs
# are told apart by title ("QA round: PR #<n>", agent-work.yml `run-name:`)
# because `gh run list` cannot show inputs. scripts/cycle_queue.py `lane_jq`
# carries the same selects; tests pin that the two agree.
if [ "$kind" = pr ]; then
  lane_sel='select(.displayTitle | startswith("QA round"))'
else
  lane_sel='select(.displayTitle | startswith("QA round") | not)'
fi
busy=$(gh run list --repo "$GH_REPO" --workflow agent-work.yml --limit 20 \
         --json status,displayTitle \
         --jq "[.[] | select(.status != \"completed\") | $lane_sel] | length" 2>/dev/null || echo unknown)
# PAUSED IS BUSY (#903). With the repository variable LOOP_PAUSED=true every
# Claude-spending loop job is skipped, so a dispatch now would start a run that
# does nothing while spending the caller's one-per-commit marker. Queue it
# instead: agent-queue drains it after the owner resumes the loop.
if [ "${LOOP_PAUSED:-}" = "true" ]; then
  busy="paused"
fi
#
# BUSY MEANS QUEUED, NOT DROPPED -- since 2026-11-02. This used to print "it
# waits for the next run" and exit, and nothing ever came back for the ruling:
# GitHub keeps one pending run per concurrency group and CANCELS the older one
# when a third arrives, so dispatching behind a running cycle loses work, and
# not dispatching lost it too (#560: qa-on-green's marker was already spent).
# `scripts/cycle_queue.py` records the ruling as a marker comment and
# `agent-queue.yml` starts the oldest entry when the running cycle completes.
# QUEUE_ON names where the entry may be written -- `qa-on-green` can comment on
# its PR but not on an issue -- and defaults to the target itself.
if [ "$busy" != "0" ]; then
  echo "::notice::a cycle is in flight (or the check failed: '$busy'). ${WHO}'s ruling at $kind #$target is QUEUED, not dropped."
  if [ -n "$DRY" ]; then
    echo "DRY RUN: would queue agent-work at $kind #$target on ${WHO}'s ruling"
    exit 0
  fi
  if ! python3 "$(dirname "$0")/cycle_queue.py" enqueue \
         --kind "$kind" --target "$target" --by "$WHO" --on "${QUEUE_ON:-$target}"; then
    echo "::error::${WHO}'s ruling at $kind #$target could NOT be queued. It is lost unless re-ruled."
    exit 1
  fi
  exit 0
fi

if [ -n "$DRY" ]; then
  echo "DRY RUN: would dispatch agent-work at $kind #$target on ${WHO}'s ruling"
  exit 0
fi

before=$(gh run list --repo "$GH_REPO" --workflow agent-work.yml \
           --limit 1 --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || echo 0)
# ONE `-f`, composed from the key. A hardcoded `-f issue=` here would
# silently dispatch a `pr=` ruling as an issue number -- and because the
# number spaces overlap, the cycle would then work whatever issue happens
# to carry that number.
t0=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # comments after this are the run's own
gh workflow run agent-work.yml --repo "$GH_REPO" -f "$kind=$target"
echo "::notice::requested agent-work at $kind #$target on ${WHO}'s ruling; verifying it started"

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
  echo "::error::dispatch at $kind #$target created no new agent-work run within 60s. Not reporting it as carried out."
  exit 1
fi

export_dispatch() {
  if [ -n "${GITHUB_ENV:-}" ]; then
    # DISPATCHED keeps its name and its value: `agent-steward.yml` reads it to
    # say "agent-work at #${DISPATCHED}". DISPATCHED_KIND is added beside it so a
    # reader can tell an issue cycle from a QA round without re-deriving it.
    echo "DISPATCHED=$target" >> "$GITHUB_ENV"
    echo "DISPATCHED_KIND=$kind" >> "$GITHUB_ENV"
    echo "DISPATCHED_RUN=$run_id" >> "$GITHUB_ENV"
    echo "DISPATCHED_BY=$WHO" >> "$GITHUB_ENV"
  fi
}

# A real cycle runs for tens of minutes, so anything `completed` inside this
# window concluded without doing a cycle's work -- UNLESS it ran and stood down.
#
# A QUICK, SUCCESSFUL STOP THAT LEFT A TRACE IS NOT A FAILED START (2026-11-08).
# A cycle that reads its target and finds nothing it may build (the only
# remaining act is a workflow edit, closed-list item 1) comments and stops in
# well under 90s. Read as #421, that stop turned agent-queue red twice on issue
# #782 and retried a cycle that had already ruled correctly. #421's shape is
# different and still caught: a run that FAILS, or succeeds having written
# nothing. The trace is a `claude[bot]` comment on the target posted after this
# dispatch -- the cycle writes one even when it stands down.
for _ in $(seq 1 18); do
  sleep 5
  read -r status conclusion <<<"$(gh run view "$run_id" --repo "$GH_REPO" \
    --json status,conclusion --jq '"\(.status) \(.conclusion // "")"' 2>/dev/null || echo "unknown ")"
  if [ "$status" = "completed" ]; then
    if [ "$conclusion" = "success" ]; then
      left=$(gh api "repos/$GH_REPO/issues/$target/comments?since=$t0&per_page=100" \
               --jq '[.[] | select(.user.login == "claude[bot]")] | length' 2>/dev/null || echo 0)
      case "$left" in ''|*[!0-9]*) left=0 ;; esac
      if [ "$left" -gt 0 ]; then
        echo "::notice::agent-work run $run_id finished within 90s and left $left claude[bot] comment(s) on #$target since dispatch: the cycle ran and stood down. Not a failed start."
        export_dispatch
        exit 0
      fi
    fi
    echo "::error::agent-work run $run_id concluded '$conclusion' within 90s of dispatch at $kind #$target -- it did not run a cycle. See #421."
    exit 1
  fi
done

echo "::notice::agent-work run $run_id is running a cycle at $kind #$target"
export_dispatch
