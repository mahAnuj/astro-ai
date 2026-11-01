"""`qa_verdict.sh` reports which context is recording the verdict (#641 follow-on).

WHY THIS FILE EXISTS, AND WHY IT IS THE FIRST ONE

`scripts/qa_verdict.sh` writes `qa-pass`, and `qa-pass` is the sole merge
trigger -- `agent-merge.yml`'s `QA verdict` step merges on it and nothing else.
It is the single most consequential script in this repository and, until this
file, **the only gate-critical script with no behaviour test at all**:
`grep -rln qa_verdict tests/ scripts/mutate*.py` matched one assertion *message*
in `tests/test_qa_on_green.py` and nothing else.

WHAT IS BEING BUILT, AND WHY ONLY HALF OF IT IS HERE

The owner ruled on 2026-11-01 that a top-level session may record a verdict only
with `--provenance independent`. `--provenance` defaults to the WEAKER claim,
`in-cycle`, so today a session that merely omits the flag records `qa:in-cycle`
on work it may have written itself and nothing notices.

Enforcing that needs the script to know whether it is the loop or a session, and
the signal is `GITHUB_ACTIONS` + `GITHUB_RUN_ID`. **Whether those reach a script
the agent runs inside `claude-code-action` is not established.** No
agent-invoked script in this repo reads a `GITHUB_*` variable; `agent-work.yml`
hands the action only two env vars of its own; and this script already prefers
`gh repo view` over `$GITHUB_REPOSITORY`. If the assumption is wrong, a refusal
would reject every in-cycle PASS the loop makes and **stop it merging** -- the
one part of this system that works unattended today.

So this commit ships the DIAGNOSTIC and not the refusal: the mode is printed,
read from a real `agent-work` log, and only then enforced. These tests pin the
reading, the naming of the variables, and -- most importantly -- that nothing
yet refuses anything.

PRINTED BEFORE THE FIRST EXIT, which the QA round on this PR had to point out.
The line used to sit beside the end-of-run summary, after the exits for a bad
argument (2), an unreadable PR (1) and a stale `--sha` (3) -- so a run that
died early left NO reading at all, and the one thing this diagnostic exists to
settle is what a REAL loop run reports. A loop run that exits 2 on a typo is
exactly the run whose mode is still worth knowing.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "qa_verdict.sh"

HEAD = "bf2b17d4e7c1a09d3f6b5e8a2c4d1f0e9b8a7c6d"


def _fake_gh(tmp_path: Path, *, branch="issue/536-a-slug", head=HEAD) -> Path:
    """A `gh` answering only what this script asks, dispatched on its argv.

    `--dry-run` stops before any write, so only the three reads need answers.
    Anything unrecognised exits 9, so a new call added to the script surfaces
    as a loud failure here rather than being silently stubbed.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
case "$*" in
  *"--json headRefName"*) echo '{branch}' ;;
  *"--json headRefOid"*)  echo '{head}' ;;
  *"--json labels"*)      echo '' ;;
  *"--json state"*)       echo 'OPEN' ;;
  *) echo "UNEXPECTED gh $*" >&2; exit 9 ;;
esac
""")
    gh.chmod(0o755)
    return bindir


def _run(tmp_path: Path, *args, env_extra=None, scrub=True, **kw):
    """Drive the real script with `--dry-run`, controlling the runner variables.

    `scrub` removes GITHUB_* and CI from the inherited environment, because the
    suite itself may well be running inside Actions -- and a test whose result
    depended on where it ran would be worthless for exactly the question under
    test.
    """
    env = dict(os.environ)
    if scrub:
        for k in ("GITHUB_ACTIONS", "GITHUB_RUN_ID", "CI"):
            env.pop(k, None)
    env["PATH"] = f"{_fake_gh(tmp_path, **kw)}:{env['PATH']}"
    env["GH_REPO"] = "owner/repo"
    env.update(env_extra or {})
    cmd = ["bash", str(SCRIPT), "--pr", "536", "--verdict", "PASS",
           "--dry-run", *args]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)


LOOP = {"GITHUB_ACTIONS": "true", "GITHUB_RUN_ID": "41263211947"}


# ------------------------------------------------------------ the reading

def test_the_loop_is_read_as_the_loop(tmp_path):
    r = _run(tmp_path, env_extra=LOOP)
    assert r.returncode == 0, r.stderr
    assert "mode=loop" in r.stdout


def test_a_scrubbed_environment_is_read_as_top_level(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "mode=top-level" in r.stdout


@pytest.mark.parametrize("env_extra,why", [
    ({"GITHUB_ACTIONS": "true"}, "GITHUB_ACTIONS alone"),
    ({"GITHUB_RUN_ID": "1"}, "GITHUB_RUN_ID alone"),
    ({"GITHUB_ACTIONS": "false", "GITHUB_RUN_ID": "1"}, "ACTIONS=false"),
    ({"GITHUB_ACTIONS": "TRUE", "GITHUB_RUN_ID": "1"}, "wrong case"),
    ({"GITHUB_ACTIONS": "1", "GITHUB_RUN_ID": "1"}, "ACTIONS=1 not true"),
    ({"GITHUB_ACTIONS": "true", "GITHUB_RUN_ID": ""}, "RUN_ID empty"),
])
def test_half_the_runner_evidence_is_not_the_loop(env_extra, why, tmp_path):
    """BOTH variables, and `GITHUB_ACTIONS` exactly `true`.

    Requiring the pair means a stray `export GITHUB_ACTIONS=true` in a shell
    profile is not on its own enough to claim to be the loop.
    """
    r = _run(tmp_path, env_extra=env_extra)
    assert r.returncode == 0, r.stderr
    assert "mode=top-level" in r.stdout, f"{why} was read as the loop"


def test_CI_is_deliberately_not_consulted(tmp_path):
    """`$CI` is the one of the three that is not GitHub's.

    Every local tool that fancies it sets it, and so do pre-commit and `act`.
    Reading it would widen "I am the loop" to any machine with a conventional
    environment variable.
    """
    r = _run(tmp_path, env_extra={"CI": "true"})
    assert "mode=top-level" in r.stdout, "$CI alone was read as the loop"


# ------------------------------------------------- the diagnostic's content

def test_the_line_NAMES_the_variables_it_read(tmp_path):
    """Not just the conclusion.

    A line that said only `mode=top-level` inside a runner would leave the
    reader guessing which of the two was missing -- and the whole purpose of
    shipping this before the refusal is that one log settles the question.
    """
    r = _run(tmp_path, env_extra={"GITHUB_ACTIONS": "true"})
    assert "GITHUB_ACTIONS=true" in r.stdout
    # `GITHUB_RUN_ID=` alone was the assertion, and the QA round on PR #649
    # showed what it bought: mutating the field's VALUE to anything at all --
    # it tried `:+x` -- passed all 24 tests, because the prefix survives any
    # right-hand side. The value is the whole fact here; assert it.
    assert "GITHUB_RUN_ID=unset" in r.stdout, r.stdout
    assert "CI=" in r.stdout


def test_the_run_id_is_reported_as_SET_when_it_is_set(tmp_path):
    """The other half, and the one the refusal in A2 will read.

    `mode=loop` requires GITHUB_ACTIONS=true AND a non-empty GITHUB_RUN_ID, so
    "which of the two was missing" is only answerable if the field distinguishes
    set from unset. A test asserting the bare prefix cannot tell them apart.
    """
    r = _run(tmp_path, env_extra=LOOP)
    assert "GITHUB_RUN_ID=set" in r.stdout, r.stdout
    assert "GITHUB_RUN_ID=unset" not in r.stdout


def test_an_empty_run_id_reads_as_unset_not_as_set(tmp_path):
    """`GITHUB_ACTIONS=true` with `GITHUB_RUN_ID=` is top-level by the rule, and
    the diagnostic has to agree with the rule it is diagnosing -- otherwise the
    log would say `mode=top-level GITHUB_RUN_ID=set`, which is incoherent and
    is exactly the ambiguity this field exists to remove."""
    r = _run(tmp_path, env_extra={"GITHUB_ACTIONS": "true", "GITHUB_RUN_ID": ""})
    assert "mode=top-level" in r.stdout
    assert "GITHUB_RUN_ID=unset" in r.stdout, r.stdout


def test_an_unset_variable_is_reported_as_unset_not_as_blank(tmp_path):
    """`GITHUB_ACTIONS=` would read as "set to empty", which is a different fact."""
    r = _run(tmp_path)
    assert "GITHUB_ACTIONS=unset" in r.stdout


def test_the_run_id_VALUE_is_not_printed(tmp_path):
    """Whether it is set is the fact; the id itself is noise in every log line."""
    r = _run(tmp_path, env_extra=LOOP)
    assert "41263211947" not in r.stdout


def test_the_provenance_is_reported_beside_the_mode(tmp_path):
    """The pair is the thing being judged, so the pair is what gets logged."""
    r = _run(tmp_path, "--provenance", "independent")
    assert "provenance=independent" in r.stdout
    r2 = _run(tmp_path)
    assert "provenance=in-cycle" in r2.stdout, "the default is not reported"


def test_the_mode_is_reported_under_dry_run(tmp_path):
    """Every case above relies on this, so it is asserted directly rather than
    assumed: a diagnostic that only appeared on a real write could not be read
    from a dry run."""
    r = _run(tmp_path, env_extra=LOOP)
    assert "--dry-run, nothing written" in r.stdout
    assert "mode=" in r.stdout


# --------------------------------------- THIS COMMIT REFUSES NOTHING YET

@pytest.mark.parametrize("args,env_extra,what", [
    ((), None, "top-level, default in-cycle provenance"),
    (("--provenance", "in-cycle"), None, "top-level, explicit in-cycle"),
    (("--provenance", "independent"), None, "top-level, independent"),
    ((), LOOP, "loop, default in-cycle"),
    (("--provenance", "independent"), LOOP, "loop, independent"),
])
def test_nothing_is_refused_by_the_diagnostic(args, env_extra, what, tmp_path):
    """THE POINT OF THIS COMMIT.

    The refusal lands separately, after a real `agent-work` log confirms the
    reading. Until then every combination must still be accepted -- including
    the one the owner's rule will later forbid. A diagnostic that silently began
    refusing would be the regression this staging exists to avoid.
    """
    r = _run(tmp_path, *args, env_extra=env_extra)
    assert r.returncode == 0, f"{what} was refused:\n{r.stdout}\n{r.stderr}"


def test_the_existing_stale_sha_refusal_is_untouched(tmp_path):
    """The one refusal that DOES exist must keep working, in both modes.

    `--sha` is checked only on a PASS, by prefix, against the live head. It is
    the strongest guard this script has and the staging must not disturb it.
    """
    for env_extra in (None, LOOP):
        r = _run(tmp_path, "--sha", "0123456789abcdef0123456789abcdef01234567",
                 env_extra=env_extra)
        assert r.returncode == 3, r.stdout + r.stderr
        assert "REFUSED" in r.stderr


def test_a_matching_sha_still_passes(tmp_path):
    r = _run(tmp_path, "--sha", HEAD, env_extra=LOOP)
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------- the decision, recorded

def test_the_script_documents_why_the_refusal_is_not_here_yet():
    """A staging decision nobody can find is a staging decision that gets
    undone. The next reader must meet the reason in the file."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "DIAGNOSTIC AND NOT THE REFUSAL" in src
    assert "stop it merging" in src, (
        "the script does not record the blast radius that motivated staging")


def test_the_script_says_this_is_not_a_security_boundary():
    """It cannot be one: a caller holding Bash can set both variables in the
    same command. Claiming otherwise in a later read would be worse than the
    gap itself."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "not, and cannot be, a security boundary" in src


def test_there_is_no_env_escape_hatch_yet():
    """Pinned before the refusal exists, so the refusal cannot arrive with one.

    An environment variable that re-opens the hole IS the hole, and it is the
    first thing an agent under turn pressure reaches for.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    for bad in ("ALLOW_IN_CYCLE", "QA_VERDICT_FORCE", "SKIP_PROVENANCE", "--force"):
        assert bad not in src, f"{bad} exists in the script"


# ------------------------------------- the reading survives an early exit

@pytest.mark.parametrize("args,why,code", [
    (["--pr", "abc", "--verdict", "PASS"], "a non-numeric --pr", 2),
    (["--verdict", "BOGUS", "--pr", "1"], "an invalid verdict", 2),
    (["--pr", "1", "--verdict", "PASS", "--provenance", "nope"], "a bad provenance", 2),
])
def test_the_mode_is_reported_even_when_the_run_exits_early(tmp_path, args, why, code):
    """THE QA ROUND'S FIRST FINDING ON THIS PR, executed.

    The line used to sit beside the end-of-run summary, after the exits for a
    bad argument, an unreadable PR and a stale `--sha`. So the runs that died
    early -- `{why}` here -- left NO mode reading at all.

    That matters because the whole plan is to read `mode=` out of ONE real
    `agent-work` log and only then ship the refusal. A loop run that exits 2 on
    a typo is exactly the run whose mode is still worth knowing, and under the
    old placement it answered nothing either way.
    """
    env = dict(os.environ)
    for k in ("GITHUB_ACTIONS", "GITHUB_RUN_ID", "CI"):
        env.pop(k, None)
    env.update(LOOP)
    env["GH_REPO"] = "owner/repo"
    env["PATH"] = f"{_fake_gh(tmp_path)}:{env['PATH']}"
    r = subprocess.run(["bash", str(SCRIPT), *args],
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == code, (r.returncode, r.stdout, r.stderr)
    assert "mode=loop" in r.stdout, (
        f"no mode reading after exiting on {why}; stdout={r.stdout!r}"
    )


def test_the_mode_is_printed_before_the_argument_parsing():
    """Static, and it is what makes the cases above hold for exits this file
    does not enumerate. The reading has to be emitted where no later `exit` can
    suppress it, which means before the `while` that parses arguments."""
    src = SCRIPT.read_text(encoding="utf-8")
    first_echo = src.index('echo "qa_verdict: mode=$MODE"')
    parse = src.index("while [ $# -gt 0 ]")
    assert first_echo < parse, (
        "the mode line is emitted after argument parsing begins, so an early "
        "exit suppresses it again"
    )
