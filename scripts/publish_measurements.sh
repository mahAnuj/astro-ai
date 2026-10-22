#!/usr/bin/env bash
#
# Publish files under measurements/ to `main` THROUGH A PULL REQUEST.
#
# WHY THIS EXISTS (#393)
# ----------------------
# Six scheduled loops wrote their reports with `git push origin HEAD:main`.
# On 2026-10-15 `main` acquired classic branch protection -- a pull request
# plus the `gates` and `build-gates` checks -- and every one of those pushes
# started coming back as:
#
#   remote: error: GH006: Protected branch update failed for refs/heads/main.
#   remote: - Changes must be made through a pull request.
#
# `agent-measure` runs eight times a day and failed all ~40 times between
# 2026-10-15 and 2026-10-21, while /admin/ops went on presenting 2026-10-14's
# numbers as today's. That shape is the reason this script is shared rather
# than pasted six times: a file that cannot be written does not announce
# itself, it just stops moving, and the loop whose job is to report what is
# broken was the thing that was broken.
#
# Only `agent-measure` and `agent-design` had run since protection went on.
# The other four are weekly, so four of the six breakages were still latent
# when this was written -- which is why all six move together.
#
# ONE SCRIPT, SIX CALLERS
# -----------------------
# The six `Commit the report` steps were already near-identical copies that
# had drifted in small ways. This repo's most reliable defect is a copied
# block diverging from its siblings (`id-token: write` missing from four loops
# each copied from a fifth; `scripts/dispatch_cycle.sh` exists for the same
# reason). A bug fixed here is fixed for all six.
#
# THE TOKEN TRAPS, BOTH PAID FOR ALREADY
# --------------------------------------
#   * `git push` needs the remote URL to carry GITHUB_TOKEN. Inside a job that
#     ran claude-code-action the remote still points at that action's GitHub
#     App installation token, which expires after exactly one hour -- run
#     37749887640 worked for 63 minutes and died with "Invalid username or
#     token". GITHUB_TOKEN is minted per job and lives as long as the job.
#   * A PR opened with GITHUB_TOKEN emits NO `pull_request` event, so it is
#     born with no checks and its required contexts never report -- it would
#     sit unmergeable forever (#322, PR #318). `workflow_dispatch` is the one
#     documented exception to that recursion guard, so this dispatches
#     `pr-gates` and `verify-build` explicitly. Their runs attach check runs to
#     the head SHA, which is what the branch protection reads.
#
# A dispatched run tests the BRANCH, not `refs/pull/N/merge`, so it cannot
# catch a conflict with a moved `main`. That is weaker than a real
# `pull_request` run and is stated here so nobody reads this green as the
# stronger one. For a diff confined to `measurements/**` there is nothing for
# the merge result to break that the branch does not already show.
#
# Auto-merge rather than waiting: the job exits in seconds and GitHub lands the
# PR when both checks go green. Waiting would hold a runner ~9 minutes per run,
# eight times a day, and turn every slow gate into a red loop.
#
# USAGE
#   publish_measurements.sh --path measurements/sync --title "sync report"
#   publish_measurements.sh --path measurements --title "measurement" --dry-run
#
#   --path     repeatable; what to stage. Must be under measurements/.
#   --title    the commit subject and PR title, stamped with the UTC date.
#   --dry-run  print every gh/git mutation instead of running it. This is what
#              makes the guards testable with no network and no Actions minutes.
#
# EXIT CODES -- the caller routes on these, so they mean different things:
#   0  published, or there was nothing to publish (both are success)
#   1  could not publish: the push, the PR or the merge enablement failed
#   2  wired wrong: a bad argument, a path outside measurements/, no GH_TOKEN
#
set -euo pipefail

die_wiring() { echo "::error::$*" >&2; exit 2; }
fail()       { echo "::error::$*" >&2; exit 1; }

PATHS=()
TITLE=""
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --path)    [ $# -ge 2 ] || die_wiring "--path needs a value"; PATHS+=("$2"); shift 2 ;;
    --title)   [ $# -ge 2 ] || die_wiring "--title needs a value"; TITLE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *)         die_wiring "unknown argument: $1" ;;
  esac
done

[ ${#PATHS[@]} -gt 0 ] || die_wiring "at least one --path is required"
[ -n "$TITLE" ]        || die_wiring "--title is required"

# EVERY PATH MUST BE UNDER measurements/, and this is not bookkeeping.
# `measurements/**` is on the Cloud Build trigger's ignoredFiles and on
# verify-production's paths-ignore, and the `gates` fast path in pr-gates.yml
# exits green early for a diff confined to it. A caller that passed
# `src/astro_ai` here would be publishing application code to `main` with the
# gates skipped. Refuse at the boundary rather than trust six call sites.
#
# `case "$p" in measurements/*)` is NOT sufficient and the test that proves it
# is in tests/test_publish_measurements.py: `measurements/../src` matches that
# glob and escapes the tree. Reject any `..` component and anything absolute
# first, then require the prefix.
for p in "${PATHS[@]}"; do
  case "$p" in
    /*)                   die_wiring "refusing '$p': an absolute path is never a repository path" ;;
    ..|../*|*/..|*/../*)  die_wiring "refusing '$p': '..' can leave measurements/ entirely" ;;
  esac
  case "$p" in
    measurements|measurements/*) ;;
    *) die_wiring "refusing to publish '$p': only paths under measurements/ may go this way" ;;
  esac
done

# NOT `${GH_TOKEN:?...}`. That exits 1, which this header documents as "could
# not publish" -- a credential or a protected branch, a different repair from
# "the step was wired wrong". `scripts/dispatch_cycle.sh` shipped with exactly
# this mismatch and ARCHITECTURE.md records the correction; the shorthand is
# the trap, not the author.
[ -n "${GH_TOKEN:-}" ] || die_wiring "GH_TOKEN is required (use \${{ github.token }})"
[ -n "${GH_REPO:-}" ]  || die_wiring "GH_REPO is required (use \${{ github.repository }})"

run() {   # every mutation goes through here so --dry-run covers all of them
  if [ "$DRY_RUN" = "1" ]; then printf 'DRY-RUN:'; printf ' %q' "$@"; printf '\n'; return 0; fi
  "$@"
}

stamp=$(date -u +%Y-%m-%d)
git config user.name  "shubhagya-agent"
git config user.email "agent@users.noreply.github.com"

git add -- "${PATHS[@]}"
if git diff --cached --quiet; then
  echo "nothing to publish: ${PATHS[*]} unchanged since the last run"
  exit 0
fi

# The branch name carries the run id, so two loops publishing in the same
# minute cannot collide and a stranded branch names the run that made it.
# NOT `feat/**` and NOT `issue/*`: `pr-gates` fires on a push to `feat/**`
# (a second, redundant run) and `agent-merge` sweeps open `issue/*` PRs
# looking for a `qa-pass` label it will never find on one of these.
branch="measurements/${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"

run git checkout -b "$branch"
run git commit -q -m "$TITLE $stamp

measurements/** is on the Cloud Build trigger's ignoredFiles and on
verify-production's paths-ignore, so landing this deploys nothing and
verifies nothing against production. Opened and merged by
scripts/publish_measurements.sh; see #393."

# See the header: the remote may still carry claude-code-action's expiring App
# token, which cannot push once it is an hour old.
run git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/${GH_REPO}.git"
run git push -u origin "$branch" || fail "could not push $branch"

run gh pr create --repo "$GH_REPO" --base main --head "$branch" \
  --title "$TITLE $stamp" \
  --body "Automated measurement publish from \`${GITHUB_WORKFLOW:-local}\`, run \`${GITHUB_RUN_ID:-local}\`.

Touches \`${PATHS[*]}\` only. \`measurements/**\` is outside the Docker image, outside the Cloud Build trigger, and outside verify-production's paths, so this changes nothing that runs. See #393 for why this goes through a pull request at all." \
  || fail "could not open a PR for $branch"

# #322: born without checks, because GITHUB_TOKEN emits no `pull_request`
# event. These two dispatches are what make the required contexts report.
# A dispatch that fails is NOT fatal -- the PR is open and a human or the
# steward can dispatch it -- but it is a warning, because an undispatched PR
# never merges and the only symptom is a dashboard that stops moving, which is
# the exact failure this whole change exists to end.
for wf in pr-gates.yml verify-build.yml; do
  if run gh workflow run "$wf" --repo "$GH_REPO" --ref "$branch"; then
    echo "::notice::dispatched $wf on $branch (#322: a GITHUB_TOKEN PR carries no checks)"
  else
    echo "::warning::could not dispatch $wf on $branch. The PR is open and may carry no $wf check, so it will never auto-merge. Dispatch by hand: gh workflow run $wf --ref $branch"
  fi
done

run gh pr merge --repo "$GH_REPO" --auto --squash --delete-branch "$branch" \
  || fail "could not enable auto-merge on $branch; the PR is open and needs a hand"

echo "published ${PATHS[*]} on $branch; auto-merge is set and will land it when both checks are green"

# ---------------------------------------------------------------------------
# TIDY UP THE PREVIOUS RUNS' BRANCHES.
#
# GitHub did not delete the head branch after either of the first two
# auto-merges -- PR #477 and #478, both left `measurements/<run>-1` behind --
# although `delete_branch_on_merge` is true on the repo, the `deletion` rule in
# `main-history-integrity` is conditioned on `refs/heads/main` alone, and
# `--delete-branch` is passed above. A plain `git push origin --delete` then
# removed both with no complaint, so nothing was blocking it. `--auto` enables
# auto-merge through `enablePullRequestAutoMerge`, which carries no
# delete-branch option, so the flag above is most likely being ignored.
#
# This run CANNOT delete its own branch however it is written: auto-merge lands
# the PR minutes after this script has exited, and waiting for it is the very
# thing the comment at the top refuses to do. So it collects the PREVIOUS runs'
# instead. That is self-healing in the way that matters -- a publish that dies
# before its merge leaves a branch for the next publish to collect, and a
# cleanup that fails is retried every publish rather than never.
#
# ONLY a ref whose PR actually merged. An open PR's branch would take its own
# pull request down with it, and the branch this run just created has a PR that
# has not merged yet BY CONSTRUCTION -- `$branch` is skipped explicitly rather
# than relying on the MERGED test to cover it, because the two guards fail
# differently and this one must not depend on timing.
#
# `--state all` is not optional: `gh pr list --head` defaults to `--state open`
# and would report NO pr for every merged branch here, which reads as "not
# merged" and deletes nothing. That default is the same one that produced the
# phantom PRs in #458 and #470.
#
# Cleanup never fails the publish. The measurement is already pushed, the PR is
# already open and auto-merge is already set by the time this runs; a leaked
# branch is untidy, and failing the step over one would turn a tidy-up into the
# red loop this script exists to end.
# ---------------------------------------------------------------------------
gh api "repos/$GH_REPO/git/matching-refs/heads/measurements/" \
     --jq '.[].ref | sub("^refs/heads/"; "")' 2>/dev/null \
| while read -r ref; do
    [ -n "$ref" ] || continue
    # NOT `[ "$ref" = "$branch" ] && continue`. Under `set -e` that AND-list
    # returns non-zero whenever the test is FALSE -- which is the ordinary
    # case, every ref that is not this run's -- and killed the loop on its
    # first iteration, silently, with the sweep still reading as wired up.
    if [ "$ref" = "$branch" ]; then continue; fi
    state=$(gh pr list --repo "$GH_REPO" --state all --head "$ref" \
              --json state --jq '.[0].state' 2>/dev/null) || continue
    [ "$state" = "MERGED" ] || continue
    if run gh api -X DELETE "repos/$GH_REPO/git/refs/heads/$ref"; then
      echo "::notice::deleted $ref, whose PR merged (GitHub left it behind)"
    else
      echo "::warning::could not delete merged branch $ref; harmless, retried next publish"
    fi
  done || true
# ^ `|| true` is load-bearing, not defensive noise. `set -o pipefail` is on, so
# a `gh api` that cannot reach GitHub makes the whole pipeline non-zero, and
# `set -e` would then fail the step -- turning a cosmetic tidy-up into a red
# publish, on a loop whose entire defect was that a failure nobody saw stopped
# the dashboard moving. Nothing below this line may fail the publish.
