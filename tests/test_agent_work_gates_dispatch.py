"""`agent-work` must dispatch `pr-gates` only when nothing else will.

WHY THIS IS A TEST, given the charter in conftest.py.

Same footing as test_agent_work_push_net.py and test_agent_merge_sweep.py: the
control is a shell loop inside a YAML string, nothing type-checks it, and its
failure mode is invisible in the place that matters -- a green PR that simply
never merges, with no red run and nothing saying why.

WHAT WENT WRONG (#573)

The dispatch exists for #322: a PR opened with GITHUB_TOKEN emits no
`pull_request` event, so it is born with no checks and `agent-merge` refuses it
forever on "no checks reported". It was unconditional, and the step is reached
on EVERY cycle -- including the normal one where the App token already pushed
the branch and opened the PR, forty lines above the dispatch, where the real
runs already exist.

So the head SHA carried two runs named `PR gates`, and both halves hurt:

  * agent-merge reduces check runs to the LATEST per name (added for #319,
    where a superseded `cancelled` run blocked a QA'd fix). The dispatched run
    starts later, so it became the voting `gates` entry and the real green one
    stopped counting.
  * when it finished it supplied no edge: the merge job excludes
    `workflow_run.event == 'workflow_dispatch'` deliberately (#352 -- a
    dispatched run checks out the branch, not `refs/pull/N/merge`).

Measured on #556, 2026-10-28: `pull_request` gates green 03:15:35Z, dispatched
gates green 03:19:50Z, four merge edges between 03:11:32Z and 03:15:42Z each
reading `gates=in_progress:pending`, the last 7s after the real green. The PR
satisfied every merge condition and sat 2h36m.

WHAT THESE TESTS PIN

The guard, driven as the real shell with a fake `gh`, and the direction it
fails in: a redundant dispatch strands a PR until the sweep, while a MISSING
dispatch leaves a PR with no checks at all, which nothing clears. So anything
unreadable counts as "no run" and the rescue still fires.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".github" / "workflows" / "agent-work.yml"
MERGE = ROOT / ".github" / "workflows" / "agent-merge.yml"


def _guard() -> str:
    """The guard + dispatch out of the step, verbatim.

    Lifted rather than reimplemented: a copy of the logic in the test body
    would pass forever while the workflow shipped something else, which is the
    defect `mutate_behaviour_suite.py` has caught twice in this repo.
    """
    job = yaml.safe_load(WORK.read_text(encoding="utf-8"))["jobs"]
    steps = next(iter(job.values()))["steps"]
    step = next(s for s in steps
                if s.get("name") == "Push the branch and open the PR")
    # Anchored on a `fi` at column 0. YAML strips the block scalar's own
    # indentation, so inside `run` the step's statements start at column 0 and
    # the poll's inner `if`s close two columns deeper -- which is what stops a
    # non-greedy match from ending at the wrong `fi`.
    m = re.search(r"(sha=\$\(gh pr view.*?\nfi)\n", step["run"], re.S)
    assert m, "the #573 guard is no longer recognisable in agent-work.yml"
    return m.group(1)


GUARD = _guard()


def _run(tmp_path: Path, counts: str) -> tuple[str, int, int]:
    """Drive the real guard with a fake `gh`.

    `counts` is what successive `gh api` calls print, space separated. The
    token `ERR` makes that call exit non-zero with nothing on stdout; `JUNK`
    makes it print a non-numeric line, which is what a gh warning on stdout
    looks like. Returns (stdout, dispatches, api_calls).
    """
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (tmp_path / "counts").write_text(counts, encoding="utf-8")
    (tmp_path / "calls").write_text("0", encoding="utf-8")
    (tmp_path / "dispatches").write_text("0", encoding="utf-8")

    # A FILE-BACKED counter, not a shell variable: `$(...)` is a subshell, so a
    # variable the fake increments inside one is gone when it exits. An earlier
    # harness in this repo counted retries that way and always saw zero.
    (bindir / "gh").write_text(
        "#!/usr/bin/env bash\n"
        f'd="{tmp_path}"\n'
        'case "$1 $2" in\n'
        '  "pr view")  echo deadbeefcafe ; exit 0 ;;\n'
        '  "workflow run")\n'
        '      echo $(( $(cat "$d/dispatches") + 1 )) > "$d/dispatches"\n'
        '      exit 0 ;;\n'
        '  "api"*)\n'
        '      i=$(( $(cat "$d/calls") + 1 ))\n'
        '      echo "$i" > "$d/calls"\n'
        '      read -r -a seq < "$d/counts"\n'
        '      v="${seq[$((i-1))]:-${seq[-1]}}"\n'
        '      case "$v" in\n'
        '        ERR)  echo "gh: could not reach api" >&2 ; exit 1 ;;\n'
        '        JUNK) echo "a warning on stdout" ; exit 0 ;;\n'
        '        *)    echo "$v" ; exit 0 ;;\n'
        '      esac ;;\n'
        'esac\n'
        'exit 0\n',
        encoding="utf-8")
    # `git rev-parse HEAD` is only the fallback; it must never be the thing that
    # decides, so it answers with a DIFFERENT sha than `gh pr view`.
    (bindir / "git").write_text(
        "#!/usr/bin/env bash\necho 0000000000fallback\n", encoding="utf-8")
    # The guard waits 15s per empty poll. Six of those is 75s of test time for
    # a branch that is already proven by the call count.
    (bindir / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n",
                                  encoding="utf-8")
    for f in ("gh", "git", "sleep"):
        (bindir / f).chmod((bindir / f).stat().st_mode | stat.S_IEXEC)

    script = 'branch="partial/573-x"\nGH_REPO="o/r"\n' + GUARD + "\n"
    p = subprocess.run(
        ["bash", "-e", "-c", script],
        capture_output=True, text=True,
        env={"PATH": f"{bindir}:/usr/bin:/bin", "HOME": str(tmp_path)})
    assert p.returncode == 0, f"the guard exited {p.returncode}: {p.stderr}"
    return (p.stdout,
            int((tmp_path / "dispatches").read_text()),
            int((tmp_path / "calls").read_text()))


# --- 1. the defect: a run already there must not get a second ---------------

def test_an_existing_pr_gates_run_is_not_given_a_second_one(tmp_path):
    """#573. This is the whole bug: #556's SHA already had a green
    `pull_request` run, and the dispatch added the one run that outranks it in
    the merge job's dedup and cannot trigger the merge job at all."""
    out, dispatches, _ = _run(tmp_path, "1")
    assert dispatches == 0, out
    assert "not dispatching" in out


def test_the_guard_polls_rather_than_reading_once(tmp_path):
    """The real run is created ASYNCHRONOUSLY. On #556 it appeared 3s after
    `gh pr create` returned, so a single immediate read sees nothing and
    dispatches anyway -- the exact redundancy the guard exists to prevent."""
    out, dispatches, calls = _run(tmp_path, "0 0 1")
    assert dispatches == 0, out
    assert calls == 3, f"stopped polling after {calls} call(s)"


# --- 2. the #322 rescue it must not break ----------------------------------

def test_a_sha_with_no_pr_gates_run_still_gets_one(tmp_path):
    """#322: a GITHUB_TOKEN-authored PR emits no `pull_request` event and is
    born with no checks. `agent-merge` refuses it on "no checks reported" and
    nothing ever clears that, so this dispatch is the only rescue."""
    out, dispatches, calls = _run(tmp_path, "0 0 0 0 0 0")
    assert dispatches == 1, out
    assert calls == 6, f"gave up after {calls} poll(s)"
    assert "#322" in out


@pytest.mark.parametrize("answer", ["ERR", "JUNK"])
def test_an_unreadable_answer_falls_toward_the_rescue(tmp_path, answer):
    """The two failures are not symmetric, so the direction is pinned.

    A redundant dispatch strands the PR until the next sweep -- bad, and the
    sweep does clear it. A missing dispatch leaves a PR with NO checks, which
    `agent-merge` refuses forever and no sweep can help. So an API error, or a
    gh warning on stdout where a number was expected, counts as "no run".

    MEASURED, not assumed, because the obvious reason is the wrong one. The
    `case` that normalises a non-number to 0 is NOT what keeps the step alive:

        bash -e -c 'x="a warning"; if [ "$x" -gt 0 ]; then echo y; fi; echo AFTER'
          -> bash: [: a warning: integer expression expected
          -> AFTER, rc=0

    `[` exits 2, but it sits in an `if` CONDITION, which -e exempts, so the
    comparison is merely false and the rescue fires either way. Removing the
    `case` leaves every test here green. It stays because it keeps an
    `integer expression expected` line out of a cycle's log, where it reads
    exactly like a real failure -- this repo has twice sent someone after a
    defect that was a diagnostic artifact.

    What IS load-bearing is `|| echo 0` on the `gh api` call. Without it the
    assignment carries gh's exit status, and `out=$(failing_cmd)` as a
    standalone command under -e ends the script -- the same trap that made
    publish_measurements.sh's whole retry path unreachable on 2026-10-27.
    Dropping it fails the ERR case here with `the guard exited 1`.
    """
    out, dispatches, _ = _run(tmp_path, answer)
    assert dispatches == 1, out


# --- 3. the exclusion this fix must NOT reach for --------------------------

def test_agent_merge_still_refuses_a_dispatched_run_as_a_trigger():
    """The tempting other fix is to let agent-merge trigger on a
    `workflow_dispatch` gates run. #352 is why that is wrong: a dispatched run
    checks out the BRANCH, not `refs/pull/N/merge`, so it cannot see a conflict
    with a moved `main` and its green is a weaker assertion than it looks.

    Pinned here, in the test for the fix, so the next person to meet this
    strand fixes the cause instead of widening the authority."""
    doc = yaml.safe_load(MERGE.read_text(encoding="utf-8"))
    cond = doc["jobs"]["merge"]["if"]
    assert "workflow_run.event == 'pull_request'" in cond
    assert "workflow_dispatch'" not in cond.replace(
        "github.event_name == 'workflow_dispatch'", "")
