"""The sweep must pick only a PR every downstream step would also accept (#357).

WHY THIS IS HERE, given the charter in conftest.py.

Admitted on the same footing as test_agent_merge_trust_boundary.py: the control
lives in a jq filter inside a YAML string, nothing type-checks it, and both of
its failure modes are silent.

  * Too loose, and the sweep spends every run on an ineligible PR -- it picks
    the lowest number, so one unlabelled PR sitting below an eligible one
    starves the eligible one forever and the loop looks fixed while nothing
    merges.
  * Too loose in the other direction and it picks a PR a human is holding
    (`needs-human-review`, `too-large-to-automerge`), re-labels it, and the
    hold becomes a 30-minute comment loop.
  * Too strict, and it silently never fires, which looks exactly like "the bug
    never recurred".

So these tests run the real filter: they lift the jq out of the workflow's own
run block and drive it with synthetic `/pulls` payloads. They do not
reimplement it. The sweep's job is candidate SELECTION -- the authority to
merge stays with the `own`/`gates`/`qa`/`size`/`boundary` steps, which re-read
everything from the API -- so what is pinned here is exactly that the candidate
is worth those steps' time, and that a held PR is not one.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

import pytest
import yaml

WORKFLOW = (Path(__file__).resolve().parent.parent
            / ".github" / "workflows" / "agent-merge.yml")
REPO = "mahAnuj/astro-ai"


def _sweep_filter() -> str:
    """The jq program out of the `Find the pull request` step, verbatim."""
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]
    run = next(s for s in job["steps"] if s.get("id") == "pr")["run"]
    # The filter is the single-quoted argument to `--jq` on the sweep's gh call.
    m = re.search(r"pulls\?state=open[^\n]*--jq\s+'(.*?)'\)", run, re.S)
    assert m, "the sweep's gh api --jq call is no longer recognisable in the `pr` step"
    return m.group(1)


FILTER = _sweep_filter()


def _agent_authors() -> str:
    """`AGENT_AUTHORS` out of the job env, with the owner expression resolved.

    Read rather than hardcoded: the whole point of the 2026-10-25 change is that
    this list -- not a branch name -- decides what the sweep will consider, so a
    test asserting against its own copy of the list would pass while the
    workflow shipped a different one.
    """
    env = yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]["env"]
    authors = env["AGENT_AUTHORS"]
    assert "${{ github.repository_owner }}" in authors, (
        "the owner must come from the context, not a literal: a hardcoded owner "
        "silently empties or widens the set on a rename or a fork"
    )
    return authors.replace("${{ github.repository_owner }}", REPO.split("/")[0])


AUTHORS = _agent_authors()
AGENT = AUTHORS.split(",")[0]


def _pick(pulls: list[dict]) -> str:
    """Run the workflow's own jq over a /pulls payload.

    Returns the SHORTLIST, space separated, lowest first -- `` when empty. The
    filter no longer selects: since #374 it hands a list to a shell loop that
    walks it asking each candidate for `mergeable`, because the `pulls` LIST
    endpoint does not carry that field. `_walk` below drives that loop.
    """
    shell = (
        'printf %s "$PULLS" | jq --raw-output \''
        + FILTER.replace("'\"$GH_REPO\"'", REPO)
                .replace("'\"$AGENT_AUTHORS\"'", AUTHORS)
        + "'"
    )
    p = subprocess.run(["bash", "-c", shell], capture_output=True, text=True,
                       env={"PULLS": json.dumps(pulls), "PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def pr(number: int, *, labels=("qa-pass",), branch=None, draft=False, repo=REPO,
       user=None) -> dict:
    return {
        "number": number,
        "draft": draft,
        "user": {"login": user or AGENT},
        "head": {"ref": branch or f"issue/{number}-x", "repo": {"full_name": repo}},
        "labels": [{"name": n} for n in labels],
    }


# --- 1. the eligible case ---------------------------------------------------

def test_an_eligible_pr_is_picked():
    assert _pick([pr(356)]) == "356"


def test_the_shortlist_is_sorted_so_the_queue_drains_in_order():
    # Lowest first, and ALL of them: the walk needs the rest to fall through to
    # when a lower one turns out to be unmergeable (#374).
    assert _pick([pr(360), pr(352), pr(356)]) == "352 356 360"


def test_no_open_prs_yields_no_candidate():
    # The live state on 2026-10-15 after #356 was merged by hand. The step
    # treats an empty value as "nothing to merge" and exits 0.
    assert _pick([]) == ""


# --- 2. qa-pass is required ------------------------------------------------

def test_a_pr_without_qa_pass_is_not_a_candidate():
    assert _pick([pr(356, labels=())]) == ""


def test_an_unlabelled_lower_pr_does_not_starve_an_eligible_higher_one():
    # The starvation case. `sort | first` over ALL open PRs would pick 300 and
    # the sweep would stop at the `qa` step every 30 minutes forever.
    assert _pick([pr(300, labels=()), pr(356)]) == "356"


# --- 3. the three human-hold labels ----------------------------------------

@pytest.mark.parametrize("hold", ["qa-fail", "needs-human-review", "too-large-to-automerge"])
def test_a_pr_a_human_is_holding_is_not_a_candidate(hold):
    assert _pick([pr(356, labels=("qa-pass", hold))]) == ""


def test_a_held_pr_does_not_block_the_next_eligible_one():
    assert _pick([pr(352, labels=("qa-pass", "needs-human-review")), pr(356)]) == "356"


# --- 4. the things the job `if:` also refuses -------------------------------

def test_a_fork_head_is_never_a_candidate():
    # Belt and braces with the job-level fork guard (#358): a fork PR must not
    # reach a job holding contents+actions write by any path, including this one.
    assert _pick([pr(356, repo="someone/astro-ai")]) == ""


def test_the_candidate_is_chosen_by_author_and_not_by_branch_name():
    """The 2026-10-25 change, pinned in both directions.

    This test used to assert the opposite -- that `chore/hand-edit` and `main`
    were refused *because of their names*. The name was carrying a meaning it
    could not carry: cycles name a slice `partial/<n>-<slug>` whenever work
    remains that the loop cannot do, and that name made the PR unmergeable on
    spelling alone. #480, #482 and #487 each had `qa-pass` on green gates and
    waited for a human; between 2026-10-21 and 2026-10-25 every code PR did.
    """
    # Any namespace an agent cycle may produce is a candidate.
    for ref in ("issue/523-x", "partial/523-x", "fix/515-x", "chore/hand-edit"):
        assert _pick([pr(356, branch=ref)]) == "356", ref

    # Authorship is what refuses one. A third-party bot is not in the list even
    # though it opens PRs on this repo every day -- the measurement publisher.
    assert _pick([pr(356, user="shubhagya-publisher[bot]")]) == ""
    assert _pick([pr(356, user="dependabot[bot]")]) == ""
    assert _pick([pr(356, user="drive-by-contributor")]) == ""


def test_a_near_miss_on_the_author_name_is_not_a_candidate():
    """Exact membership, not a substring or prefix match.

    `claude[bot]` contains `[`, which is a glob metacharacter in a shell `case`
    and a regex metacharacter almost everywhere else, so a filter written with
    either would admit names it never meant to.
    """
    for impostor in ("claude[bot]-x", "xclaude[bot]", "claude", "notmahAnuj",
                     "mahAnuj-evil", "Claude[bot]"):
        assert _pick([pr(356, user=impostor)]) == "", impostor


def test_the_owner_is_a_candidate_where_a_branch_name_used_to_refuse_them():
    """The one widening here that is not purely a bug fix.

    Before this, a branch the owner pushed by hand was refused by the name test,
    so `AGENT_AUTHORS` including the owner puts their PRs in scope. Nothing
    downstream is relaxed -- gates, qa-pass, size and the trust boundary are all
    re-read -- but the sweep will now spend a run on one, so it is pinned
    deliberately rather than left as a side effect.
    """
    owner = REPO.split("/")[0]
    assert _pick([pr(356, user=owner, branch="chore/hand-edit")]) == "356"
    # And `needs-human-review` is the way to hold one, since a name no longer is.
    assert _pick([pr(356, user=owner, labels=("qa-pass", "needs-human-review"))]) == ""


def test_a_draft_is_never_a_candidate():
    # The `Take it out of draft` step exists for the edge-triggered path, where
    # gates and qa-pass are already known good. The sweep has no such context,
    # so it does not ready anything.
    assert _pick([pr(356, draft=True)]) == ""


# --- the walk: mergeability, and not stopping at the first (#374) ---

def _walk(shortlist: str, mergeable: dict[int, str]) -> tuple[str, str]:
    """Run the workflow's own candidate loop. Returns (picked, stderr+stdout).

    The loop is lifted out of the `pr` step rather than reimplemented, and `gh`
    is replaced by a script on PATH that answers `pr view <n> --json mergeable`
    from the table passed in. Nothing from a PR is executed; the values are
    literals below.
    """
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]
    run = next(s for s in job["steps"] if s.get("id") == "pr")["run"]
    m = re.search(r'(\n\s*n=""\n\s*for cand in \$candidates; do.*?\n\s*done\n)', run, re.S)
    assert m, "the sweep's candidate loop is no longer recognisable in the `pr` step"
    loop = textwrap.dedent(m.group(1))

    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = pathlib.Path(tmp) / "bin"
        bin_dir.mkdir()
        table = ";".join(f"{k}={v}" for k, v in mergeable.items())
        gh = bin_dir / "gh"
        gh.write_text(
            "#!/bin/bash\n"
            'for p in $@; do case "$p" in [0-9]*) n="$p"; break;; esac; done\n'
            f'for e in $(echo "{table}" | tr ";" " "); do\n'
            '  k="${e%%=*}"; v="${e#*=}"\n'
            '  if [ "$k" = "$n" ]; then printf "%s" "$v"; exit 0; fi\n'
            "done\n"
            "exit 1\n")
        gh.chmod(0o755)
        script = f'candidates="{shortlist}"\nGH_REPO=x\n{loop}\nprintf "PICKED=%s" "$n"\n'
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                           env={"PATH": f"{bin_dir}:/usr/bin:/bin"})
    out = r.stdout + r.stderr
    picked = re.search(r"PICKED=(\d*)", out)
    return (picked.group(1) if picked else ""), out


def test_a_conflicting_candidate_is_skipped_for_the_next_one():
    # The #360 case, 2026-10-15: selected while CONFLICTING, ran the whole
    # chain, and stopped only because the trust boundary held it.
    picked, _ = _walk("352 356", {352: "CONFLICTING", 356: "MERGEABLE"})
    assert picked == "356"


def test_a_conflicting_pr_does_not_block_the_queue_forever():
    # The starvation shape the cron introduced and the edge trigger never had.
    picked, _ = _walk("300 352 356", {300: "CONFLICTING", 352: "CONFLICTING",
                                      356: "MERGEABLE"})
    assert picked == "356"


def test_unknown_is_not_treated_as_mergeable():
    # GitHub computes mergeability lazily. Accepting UNKNOWN would make the
    # failure intermittent, which is worse than reliable.
    picked, _ = _walk("352", {352: "UNKNOWN"})
    assert picked == ""


def test_an_unreadable_candidate_is_skipped_not_assumed_good():
    picked, _ = _walk("352 356", {356: "MERGEABLE"})   # 352 absent -> gh exits 1
    assert picked == "356"


def test_every_skip_says_why():
    # A sweep that found candidates and took none must not read like "nothing
    # to do" -- #357 exists because silence hid four stranded PRs.
    _, out = _walk("352 356", {352: "CONFLICTING", 356: "MERGEABLE"})
    assert "skipping #352" in out and "CONFLICTING" in out


def test_nothing_eligible_yields_no_candidate():
    picked, _ = _walk("352 356", {352: "CONFLICTING", 356: "CONFLICTING"})
    assert picked == ""


# --- the filter's own shape -------------------------------------------------

def test_the_sweep_only_supplies_a_number_and_decides_nothing_else():
    # If the filter ever returned an object, or the step consumed anything but
    # a number, the sweep would start carrying state the later steps should be
    # re-reading. `.number` is the whole contract.
    assert ".number" in FILTER
    out = _pick([pr(356)])
    assert out.isdigit()


def test_the_schedule_leg_cannot_be_reached_without_the_sweep_filter():
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]
    run = next(s for s in job["steps"] if s.get("id") == "pr")["run"]
    assert '"$EVENT_NAME" = "schedule"' in run
    assert '"$EVENT_NAME" = "workflow_dispatch"' in run
    # And the already-handled guard, which is what keeps a sweep racing an edge
    # from reaching `gh pr merge` on a merged PR.
    assert '"$state" != "OPEN"' in run
