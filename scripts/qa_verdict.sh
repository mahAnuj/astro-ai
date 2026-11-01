#!/usr/bin/env bash
# Record a QA verdict as labels, on the PR and on its issue, in ONE transition.
#
# WHY THIS IS A SCRIPT AND NOT THREE `gh` LINES IN A PROMPT
#
# `agent-merge` merges on labels, so the labels ARE the gate. agent-cycle.md
# Step 3.5 used to spell the writes out as loose `gh` calls, and that shape has
# two failure modes a gate cannot afford:
#
#   1. A PARTIAL TRANSITION. The PR gets the label and the issue does not, or
#      the add lands and the remove does not. Every `gh` line is a separate API
#      call that can fail on its own, and a cycle that runs out of turns
#      between two of them leaves the gate in a state no rule describes.
#   2. A STALE FAILURE THAT NOTHING COULD CLEAR. `qa-fail` wins in
#      `agent-merge` over everything, deliberately -- a PR QA failed must not
#      merge because something later added `qa-pass` beside it. But nothing
#      removed `qa-fail` when a later round actually passed, so the first
#      failed round was terminal and the loop could only ever hand the PR to a
#      human. #530 sat in exactly that state: `qa-fail` + draft, fix still to
#      come.
#
# Both are the same bug -- the verdict was written as independent facts rather
# than as a state change. So: ONE entry point, the only thing that writes these
# labels, moving PR and issue from whatever they hold to what the verdict means.
#
#   PASS  ->  +qa-pass  -qa-fail   (and `gh pr ready`)
#   FAIL  ->  +qa-fail  -qa-pass    (and the draft STAYS a draft)
#
# plus exactly one provenance label, `qa:independent` or `qa:in-cycle`, the
# other removed. Provenance is NOT a verdict and a pass must not clear it:
# qa.md calls it "a trust gradient, not bookkeeping" -- `qa:independent` means
# the reviewer had no hand in the work, `qa:in-cycle` means it reviewed its own
# cycle's. Each round restates it for itself, because the round that cleared a
# failure may be weaker or stronger than the one that set it.
#
# `qa-fail` keeps winning in `agent-merge`, and that is now a check against a
# stale failure rather than a fixed one, because a pass cannot leave `qa-fail`
# behind.
#
# WHY A PASS IS BOUND TO A SHA
#
# A label records that QA passed; it does not record WHAT QA passed. Push to the
# branch and the label survives, now asserting a verdict about code nobody ran
# -- and `agent-merge` re-checks the GATES on the new head but reads the label
# as-is. So `--sha` is compared against the PR's current head and a pass is
# refused if the branch moved underneath it. Pass the SHA QA actually examined,
# not `HEAD` read at the end.
#
# Usage:
#   qa_verdict.sh --pr <n> --verdict PASS|FAIL [--issue <n>] [--sha <sha>]
#                 [--provenance independent|in-cycle] [--note "<one line>"]
#                 [--dry-run]
#
# --provenance defaults to `in-cycle`, the WEAKER claim, because qa.md says so:
# "If you cannot tell which you are, you are qa:in-cycle." A default that
# overstated independence would be the same error as claiming an unsupported
# PASS.
#
# --issue is derived from the branch name (`issue/<n>-*`, `partial/<n>-*`,
# `fix/<n>-*`) when omitted. That is a convenience only: the branch name decides
# nothing here, and `--issue` always wins. `--issue none` records the verdict on
# the PR alone, for a PR with no owning issue.
#
# EXIT CODES, so a workflow step or a cycle can route on them:
#   0  the verdict is recorded (or already was -- this is idempotent)
#   2  bad usage
#   3  refused: --sha does not match the PR's current head (a pass would be
#      asserting a verdict about code QA never saw)
#   4  an API call failed and the transition is INCOMPLETE -- read the output,
#      because this is the partial state the script exists to prevent
#
# A `qa_verdict: mode=` line on STDERR says whether this run looks like the
# loop or like a top-level session, and names the variables it read. It is
# printed as soon as the mode is known -- BEFORE the exits for a bad argument,
# an unreadable PR or a stale `--sha` -- so every run leaves the reading,
# including one that then fails. The summary line at the end repeats the mode
# beside the provenance, where a reader of the outcome wants it.
set -euo pipefail

# WHICH CONTEXT IS RECORDING THIS VERDICT, and why the script needs to know.
#
# `--provenance` defaults to the WEAKER claim, `in-cycle`, because qa.md says
# "If you cannot tell which you are, you are qa:in-cycle". That default is right
# for the loop and wrong for a top-level session: a session that simply omits
# the flag records `qa:in-cycle` on work it may well have written itself, and
# nothing anywhere notices. The owner ruled on 2026-11-01 that a top-level
# session may record a verdict ONLY with `--provenance independent`.
#
# THIS COMMIT ADDS THE DIAGNOSTIC AND NOT THE REFUSAL, deliberately. Whether
# these variables reach a script run by the agent inside `claude-code-action`
# is not established: no agent-invoked script in this repo reads a `GITHUB_*`
# variable, and `agent-work.yml` hands the action only two env vars of its own
# while this script already falls back to `gh repo view` rather than trusting
# `$GITHUB_REPOSITORY`. If the assumption is wrong, a refusal here would reject
# every in-cycle PASS the loop makes and stop it merging -- the one part of this
# system that currently works unattended. So the mode is PRINTED first, read
# from a real `agent-work` log, and only then enforced.
#
# TWO VARIABLES, BOTH REQUIRED. GitHub sets both in the environment of every
# step. Requiring the pair means a stray `export GITHUB_ACTIONS=true` in a shell
# profile is not on its own enough to claim to be the loop.
#
# `$CI` IS DELIBERATELY NOT CONSULTED. It is the one of the three that is not
# GitHub's: every local tool that fancies it sets it, and so do pre-commit and
# `act`. Reading it would widen "I am the loop" to any machine with a
# conventional environment variable.
#
# This is not, and cannot be, a security boundary: a caller holding Bash can
# write `GITHUB_ACTIONS=true GITHUB_RUN_ID=1 scripts/qa_verdict.sh ...` in one
# line. What it can do is make the weaker claim impossible to make BY ACCIDENT
# or BY DEFAULT. The real boundary is unchanged and lives elsewhere: this script
# is the only writer of these labels, and the permission system decides who may
# run it.
IN_LOOP=0
if [ "${GITHUB_ACTIONS:-}" = "true" ] && [ -n "${GITHUB_RUN_ID:-}" ]; then
  IN_LOOP=1
fi
MODE=top-level
[ "$IN_LOOP" = 1 ] && MODE=loop

# EMITTED HERE, BEFORE THE FIRST EXIT, and that placement is the whole point.
#
# Found by the QA round on PR #649 (2026-11-01): this line used to live beside
# the summary at the end, after the exits for a bad argument (2), an unreadable
# PR (1) and a stale `--sha` (3). So a run that died early left NO mode reading
# at all -- and the reason this diagnostic exists is to settle, from one real
# `agent-work` log, whether GITHUB_ACTIONS and GITHUB_RUN_ID reach a script run
# inside `claude-code-action`. A loop run that exits 2 on a typo is exactly the
# run whose mode we would still want to know.
#
# On stdout, where the rest of this script's reporting goes and where the
# tests read it; an Actions log merges both streams anyway, so stderr would buy
# nothing and split the output of one run across two places. `--dry-run`
# reaches it too, because it is printed before anything is read.
#
# The variables are NAMED, not just their conclusion: a line saying only
# `mode=top-level` inside a runner leaves the reader guessing which was missing.
# `GITHUB_RUN_ID` is reported set/unset rather than echoed -- a run id is not a
# secret, but the shape is what the rule reads and the value would be noise.
echo "qa_verdict: mode=$MODE" \
     "(GITHUB_ACTIONS=${GITHUB_ACTIONS:-unset}" \
     "GITHUB_RUN_ID=$([ -n "${GITHUB_RUN_ID:-}" ] && echo set || echo unset)" \
     "CI=${CI:-unset})"

PR=""; ISSUE=""; VERDICT=""; SHA=""; NOTE=""; PROV="in-cycle"; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --pr)      PR="${2:-}"; shift 2 ;;
    --issue)   ISSUE="${2:-}"; shift 2 ;;
    --verdict) VERDICT="${2:-}"; shift 2 ;;
    --sha)     SHA="${2:-}"; shift 2 ;;
    --note)    NOTE="${2:-}"; shift 2 ;;
    --provenance) PROV="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "qa_verdict.sh: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

: "${GH_REPO:=}"
if [ -z "$GH_REPO" ]; then
  GH_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)
fi
[ -n "$GH_REPO" ] || { echo "qa_verdict.sh: set GH_REPO (owner/name)" >&2; exit 2; }

case "$VERDICT" in
  PASS|FAIL) ;;
  *) echo "qa_verdict.sh: --verdict must be PASS or FAIL, got '${VERDICT:-}'" >&2; exit 2 ;;
esac
case "$PR" in
  ''|*[!0-9]*) echo "qa_verdict.sh: --pr must be a number, got '${PR:-}'" >&2; exit 2 ;;
esac
case "$PROV" in
  independent|in-cycle) ;;
  *) echo "qa_verdict.sh: --provenance must be independent or in-cycle, got '$PROV'" >&2; exit 2 ;;
esac

BRANCH=$(gh pr view "$PR" --repo "$GH_REPO" --json headRefName --jq .headRefName)
HEAD=$(gh pr view "$PR" --repo "$GH_REPO" --json headRefOid --jq .headRefOid)

# A PASS about a head that no longer exists is the stale-label bug. Refuse it.
# A FAIL is not checked: "this branch had defects" stays true after a push, and
# a cycle that pushes a fix then re-runs QA passes a fresh --sha anyway.
if [ -n "$SHA" ] && [ "$VERDICT" = PASS ]; then
  case "$HEAD" in
    "$SHA"*) ;;
    *) echo "qa_verdict.sh: REFUSED — QA examined $SHA but PR #$PR is now at $HEAD." >&2
       echo "  The branch moved after QA ran, so a qa-pass here would assert a" >&2
       echo "  verdict about code nobody verified. Re-run QA on $HEAD." >&2
       exit 3 ;;
  esac
fi

# The owning issue. The branch name is a HINT and nothing more -- --issue wins,
# and `none` means the PR carries the verdict by itself.
if [ -z "$ISSUE" ]; then
  # Only the three namespaces that carry an issue number by construction
  # (agent-cycle.md Step 4). A bare `[a-z]*` would read
  # `measurements/40140256532-1` as issue 40140256532 and label a stranger.
  # `sed -E`, NOT a BRE with `\|`: alternation and `+` in a basic regex are GNU
  # extensions that match NOTHING on BSD sed, which is what runs on the
  # maintainer's macOS. detect_stalls.py carries the same warning, measured.
  # Caught here by this script returning `issue=none` on a `partial/` branch.
  # `#` as the delimiter, not `|`: `|` is both the s-command delimiter and the
  # alternation operator, and BSD sed reads the first alternation `|` as the
  # closing delimiter -- "RE error: parentheses not balanced".
  ISSUE=$(printf '%s' "$BRANCH" | sed -nE 's#^(issue|partial|fix)/([0-9]+).*#\2#p')
  [ -n "$ISSUE" ] || ISSUE=none
fi

if [ "$VERDICT" = PASS ]; then
  ADD="qa-pass"; DROP="qa-fail"
else
  ADD="qa-fail"; DROP="qa-pass"
fi
# This round's provenance replaces the previous round's, whichever way it goes.
if [ "$PROV" = independent ]; then
  ADD="$ADD qa:independent"; DROP="$DROP qa:in-cycle"
else
  ADD="$ADD qa:in-cycle";    DROP="$DROP qa:independent"
fi

# Only touch what is actually there. `--remove-label` on an absent label is an
# API 404 and, under `set -e`, would abort the transition half-done -- turning
# the idempotent re-run this script promises into failure mode 1 above.
plan_flags() {
  local have="$1" flags="" l
  for l in $ADD; do
    case ",$have," in *",$l,"*) ;; *) flags="$flags --add-label $l" ;; esac
  done
  for l in $DROP; do
    case ",$have," in *",$l,"*) flags="$flags --remove-label $l" ;; esac
  done
  printf '%s' "$flags"
}

pr_have=$(gh pr view "$PR" --repo "$GH_REPO" --json labels --jq '[.labels[].name]|join(",")')
pr_flags=$(plan_flags "$pr_have")

issue_flags=""
if [ "$ISSUE" != none ]; then
  issue_have=$(gh issue view "$ISSUE" --repo "$GH_REPO" --json labels \
                 --jq '[.labels[].name]|join(",")' 2>/dev/null || echo "__missing__")
  if [ "$issue_have" = "__missing__" ]; then
    echo "::warning::issue #$ISSUE not readable — recording the verdict on PR #$PR only"
    ISSUE=none
  else
    issue_flags=$(plan_flags "$issue_have")
  fi
fi

echo "qa_verdict: PR #$PR ($BRANCH @ ${HEAD:0:7}) verdict=$VERDICT issue=$ISSUE"
# The mode is REPEATED here beside the provenance, which is the pairing a
# reader of the outcome wants: "a top-level session recorded an in-cycle PASS"
# is one fact, not two. The authoritative early reading is on stderr above,
# printed before any exit could suppress it.
echo "qa_verdict: mode=$MODE provenance=$PROV"
echo "  PR labels now: ${pr_have:-none}"
echo "  PR change:     ${pr_flags:-none needed}"
[ "$ISSUE" = none ] || echo "  issue change:  ${issue_flags:-none needed}"

if [ "$DRY" = 1 ]; then
  echo "qa_verdict: --dry-run, nothing written"
  exit 0
fi

fail() { echo "qa_verdict: $1 FAILED — transition is INCOMPLETE" >&2; exit 4; }

# shellcheck disable=SC2086  # word splitting is the point: these are flag pairs
[ -z "$pr_flags" ]    || gh pr edit    "$PR"    --repo "$GH_REPO" $pr_flags    || fail "pr edit"
# shellcheck disable=SC2086
[ -z "$issue_flags" ] || gh issue edit "$ISSUE" --repo "$GH_REPO" $issue_flags || fail "issue edit"

# A draft cannot merge, and only a PASS earns the un-drafting. agent-cycle.md:
# "A DRAFT CARRYING qa-fail STAYS A DRAFT" -- the draft is a gate somebody shut
# because a round found defects.
if [ "$VERDICT" = PASS ]; then
  if [ "$(gh pr view "$PR" --repo "$GH_REPO" --json isDraft --jq .isDraft)" = true ]; then
    gh pr ready "$PR" --repo "$GH_REPO" || fail "pr ready"
  fi
fi

# The comment is the audit trail the label cannot carry: which head, and why.
body="QA: $VERDICT — verified at \`${SHA:-$HEAD}\`"
[ -z "$NOTE" ] || body="$body
$NOTE"
if [ "$VERDICT" = PASS ]; then
  case ",$pr_have," in
    *",qa-fail,"*) body="$body

\`qa-fail\` from an earlier round removed on the PR and on issue #$ISSUE: this round passed on \`${SHA:-$HEAD}\`. Recorded by \`scripts/qa_verdict.sh\`." ;;
  esac
fi
gh pr comment "$PR" --repo "$GH_REPO" --body "$body" || fail "pr comment"

echo "qa_verdict: recorded"
