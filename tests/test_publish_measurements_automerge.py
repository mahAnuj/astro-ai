"""Enabling auto-merge must not be a single shot, and a failed enable must
never leave the report PR stranded (#554, 2026-10-27).

WHY THIS IS HERE, given the charter in conftest.py.

PR #554 was lost to one transient GitHub 500 on `gh pr merge --auto`:

    GraphQL: Something went wrong while executing your query (BC05:26EDFD:...)
    ::error::could not enable auto-merge on measurements/40420451019-1

It then sat open and green while the NEXT report merged past it. 31 of the 32
publisher PRs merged; nothing ever came back for that one. `agent-merge`'s
sweep cannot rescue it either -- these PRs are authored by the publisher App,
which is not in that workflow's AGENT_AUTHORS, so this script is the only
thing that will ever merge them, and its failure is terminal.

The second trap is subtler and is why a plain retry is not the fix. Once the
checks have gone green, GitHub REFUSES to queue an auto-merge at all:

    $ gh pr merge --auto --squash --delete-branch 554
    GraphQL: Pull request Pull request is in clean status

That is not transient and retrying can never clear it, so the fallback has to
be a direct merge -- and a direct merge is exactly where an unverified change
could reach a `main` that auto-deploys. "Clean status" is also true of a PR
carrying NO checks (#322, the failure the two dispatches exist to prevent), so
what is pinned hardest below is the REFUSALS: the script must read the gates
itself and decline to merge anything that is not actually green.

These tests drive the REAL script, with a fake `gh` that reproduces each of
GitHub's three answers verbatim.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "publish_measurements.sh"
REAL_GIT = shutil.which("git")


def _repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(work), "config", k, v], check=True)
    (work / "measurements").mkdir()
    (work / "measurements" / "loop.json").write_text('{"a": 1}\n')
    subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(work), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(remote)],
                   check=True)
    return work


def _gh(tmp_path: Path, *, auto_reply: str, checks: str,
        auto_succeeds_on: int = 0) -> Path:
    """A `gh` reproducing GitHub's answers. `checks` is the check-runs output.

    `auto_succeeds_on` lets `pr merge --auto` fail transiently and then
    succeed on the Nth attempt, counted through a file because the script
    reads the call in a command substitution (a subshell, so a variable
    would not survive).
    """
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    # `sleep` is an external command, so shadowing it on PATH keeps the
    # backoff from making this test take 15 seconds.
    (bindir / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n")
    (bindir / "sleep").chmod(0o755)
    # The script repoints `origin` at github.com so its push carries the token
    # (see THE TOKEN TRAPS in the script). That is correct in CI and fatal in a
    # test, so `push` and `remote` become no-ops and EVERY OTHER git command
    # runs for real -- the branch, the commit and the diff are all genuine.
    (bindir / "git").write_text(
        "#!/usr/bin/env bash\n"
        'for a in "$@"; do\n'
        '  case "$a" in push|remote) exit 0 ;; -C) ;; *) ;; esac\n'
        '  break\n'
        "done\n"
        f'exec {REAL_GIT} "$@"\n'
    )
    (bindir / "git").chmod(0o755)

    gh = bindir / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
echo "gh $*" >> "{tmp_path}/gh.log"
line="$*"
case "$line" in
  *"pr merge"*--auto*)
      n=$(cat "{tmp_path}/tries" 2>/dev/null || echo 0); n=$((n+1))
      echo "$n" > "{tmp_path}/tries"
      if [ "{auto_succeeds_on}" -gt 0 ] && [ "$n" -ge "{auto_succeeds_on}" ]; then
        echo "auto-merge enabled"; exit 0
      fi
      echo "{auto_reply}"; exit 1 ;;
  *"pr view"*headRefOid*) echo "deadbeefcafe"; exit 0 ;;
  *check-runs*) printf '%s\\n' {checks or '""'}; exit 0 ;;
esac
exit 0
""")
    gh.chmod(0o755)
    return bindir


def _run(work: Path, bindir: Path) -> subprocess.CompletedProcess:
    env = {
        "PATH": f"{bindir}:/usr/bin:/bin:/usr/local/bin",
        "GH_TOKEN": "t0ken",
        "GH_REPO": "mahAnuj/astro-ai",
        "GITHUB_RUN_ID": "777",
        "HOME": str(work.parent),
    }
    return subprocess.run(
        ["bash", str(SCRIPT), "--path", "measurements", "--title", "m"],
        cwd=work, env=env, capture_output=True, text=True)


def _publish(work: Path):
    (work / "measurements" / "loop.json").write_text('{"a": 2}\n')


CLEAN = "GraphQL: Pull request Pull request is in clean status (enablePullRequestAutoMerge)"
FIVEHUNDRED = "GraphQL: Something went wrong while executing your query"


def _log(tmp_path: Path) -> str:
    return (tmp_path / "gh.log").read_text()


def _direct_merges(tmp_path: Path) -> list[str]:
    """`pr merge` calls that are NOT `--auto` -- i.e. a real merge."""
    return [l for l in _log(tmp_path).splitlines()
            if "pr merge" in l and "--auto" not in l]


def test_a_clean_status_refusal_falls_back_to_merging_the_green_pr(tmp_path):
    """GitHub will not QUEUE a merge it could do now, so do it now."""
    work = _repo(tmp_path)
    _publish(work)
    bindir = _gh(tmp_path, auto_reply=CLEAN,
                 checks='"gates=completed:success" "build-gates=completed:success"')
    r = _run(work, bindir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _direct_merges(tmp_path), (
        "the PR was green and auto-merge was refused as redundant, but nothing "
        f"merged it -- this is #554 recurring.\n{_log(tmp_path)}")


def test_it_refuses_to_merge_when_a_check_is_still_running(tmp_path):
    """The fallback must not become "merge whatever GitHub calls clean"."""
    work = _repo(tmp_path)
    _publish(work)
    bindir = _gh(tmp_path, auto_reply=CLEAN,
                 checks='"gates=completed:success" "build-gates=in_progress:pending"')
    r = _run(work, bindir)
    assert r.returncode == 1, r.stdout + r.stderr
    assert not _direct_merges(tmp_path), (
        "merged with build-gates still running -- `main` auto-deploys.\n"
        f"{_log(tmp_path)}")


def test_it_refuses_to_merge_a_pr_that_carries_no_checks_at_all(tmp_path):
    """#322: a GITHUB_TOKEN PR is born with no checks, which also reads CLEAN."""
    work = _repo(tmp_path)
    _publish(work)
    bindir = _gh(tmp_path, auto_reply=CLEAN, checks="")
    r = _run(work, bindir)
    assert r.returncode == 1, r.stdout + r.stderr
    assert not _direct_merges(tmp_path), (
        f"merged a PR with no checks at all.\n{_log(tmp_path)}")


def test_it_refuses_to_merge_when_a_check_failed(tmp_path):
    work = _repo(tmp_path)
    _publish(work)
    bindir = _gh(tmp_path, auto_reply=CLEAN,
                 checks='"gates=completed:success" "build-gates=completed:failure"')
    r = _run(work, bindir)
    assert r.returncode == 1, r.stdout + r.stderr
    assert not _direct_merges(tmp_path), (
        f"merged over a failing gate.\n{_log(tmp_path)}")


def test_a_transient_error_is_retried_rather_than_stranding_the_pr(tmp_path):
    """#554's actual failure: one 500, and the PR was abandoned."""
    work = _repo(tmp_path)
    _publish(work)
    bindir = _gh(tmp_path, auto_reply=FIVEHUNDRED, checks="", auto_succeeds_on=3)
    r = _run(work, bindir)
    assert r.returncode == 0, (
        "a transient 500 still strands the PR -- #554 unfixed.\n"
        + r.stdout + r.stderr)
    assert int((tmp_path / "tries").read_text()) == 3
    assert not _direct_merges(tmp_path), (
        "auto-merge was enabled, so nothing should have been merged outright.\n"
        f"{_log(tmp_path)}")


def test_a_persistent_transient_error_fails_loudly(tmp_path):
    """Retries must end. Silence is what made #554 invisible for a day."""
    work = _repo(tmp_path)
    _publish(work)
    bindir = _gh(tmp_path, auto_reply=FIVEHUNDRED, checks="")
    r = _run(work, bindir)
    assert r.returncode == 1
    assert "needs a hand" in (r.stdout + r.stderr)
