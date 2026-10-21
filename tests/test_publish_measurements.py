"""The one path by which six scheduled loops write to `main` (#393).

WHY THIS FILE EXISTS
--------------------
On 2026-10-15 `main` acquired branch protection and six workflows that ended in
`git push origin HEAD:main` all broke at once. Only two of the six had run by
the time anyone noticed, so four breakages were still latent; `agent-measure`,
at eight runs a day, was the one that surfaced it -- by failing ~40 times in six
days while /admin/ops went on presenting 2026-10-14's numbers as today's.

That is the failure shape worth testing against: **a write that cannot happen
does not announce itself, it just stops moving.** Nothing here asserts that a
report is good; everything asserts that the publish path still exists and still
refuses what it is supposed to refuse.

These tests drive the REAL script through a fake `gh` on PATH and a real
temporary git repository, so every guard runs with no network and no Actions
minutes. `--dry-run` is what makes that possible and is the same device
`scripts/dispatch_cycle.sh` carries, for the same reason.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_measurements.sh"
WORKFLOWS = ROOT / ".github" / "workflows"

#: The six loops that wrote `measurements/**` straight to `main` before #393,
#: and the directory each one owns. Listed from the issue, not inferred.
LOOPS = {
    "agent-measure": "measurements",
    "agent-sync": "measurements/sync",
    "agent-design": "measurements/design",
    "agent-prioritise": "measurements/prioritise",
    "agent-discover": "measurements/discover",
    "agent-infra": "measurements/infra",
}


def _repo(tmp_path: Path) -> Path:
    """A real git repo with a `measurements/` directory and an origin."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(work), "config", k, v], check=True)
    (work / "measurements").mkdir()
    (work / "measurements" / "loop.json").write_text('{"a": 1}\n')
    (work / "src").mkdir()
    (work / "src" / "app.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(work), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(work), "remote", "add", "origin", str(remote)], check=True)
    return work


def _fake_gh(tmp_path: Path, *, fail_on: str = "") -> Path:
    """A `gh` that records its calls and can be told to fail one subcommand."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "gh $*" >> "{tmp_path}/gh.log"\n'
        f'case "$1" in {fail_on or "__none__"}) exit 1 ;; esac\n'
        "exit 0\n"
    )
    gh.chmod(0o755)
    return bindir


def _run(work: Path, bindir: Path, *args, dry=True) -> subprocess.CompletedProcess:
    env = {
        "PATH": f"{bindir}:/usr/bin:/bin:/usr/local/bin",
        "GH_TOKEN": "t0ken",
        "GH_REPO": "mahAnuj/astro-ai",
        "GITHUB_RUN_ID": "777",
        "HOME": str(work.parent),
    }
    cmd = ["bash", str(SCRIPT), *args] + (["--dry-run"] if dry else [])
    return subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# the guards
# --------------------------------------------------------------------------- #

def test_it_refuses_a_path_outside_measurements(tmp_path):
    """The boundary that keeps the pr-gates fast path honest.

    `measurements/**` is the one tree a PR can change while `pr-gates` skips the
    behaviour suite and all 29 verification gates -- the scope step matches
    `src/`, `tests/`, `scripts/`, `assets/`, `.github/workflows/` and the build
    manifests, and nothing else. So a caller that passed `src/astro_ai` here
    would be shipping application code to `main` with the gates skipped and
    auto-merge already enabled. Refused at the boundary, exit 2 (wired wrong),
    because six call sites is six chances to get an argument wrong.
    """
    work = _repo(tmp_path)
    r = _run(work, _fake_gh(tmp_path), "--path", "src/astro_ai", "--title", "x")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "only paths under measurements/" in r.stderr
    # and it refuses before touching git: nothing staged, no branch
    assert "main" == subprocess.run(
        ["git", "-C", str(work), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True).stdout.strip()


@pytest.mark.parametrize("sneaky", [
    "measurements/../src",       # traversal back out of the allowed tree
    "measurementsX",             # prefix match that is a different directory
    "../measurements",
    "/etc",
])
def test_it_refuses_paths_that_only_look_like_measurements(tmp_path, sneaky):
    work = _repo(tmp_path)
    r = _run(work, _fake_gh(tmp_path), "--path", sneaky, "--title", "x")
    assert r.returncode == 2, f"{sneaky!r} was accepted: {r.stdout}{r.stderr}"


def test_nothing_to_publish_is_success_not_failure(tmp_path):
    """An unchanged tree exits 0 and opens no PR.

    Eight runs a day, and most collector runs change nothing when the upstream
    APIs answer the same. A loop that went red on "no news" would train everyone
    to ignore its red.
    """
    work = _repo(tmp_path)
    bindir = _fake_gh(tmp_path)
    r = _run(work, bindir, "--path", "measurements", "--title", "measurement")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nothing to publish" in r.stdout
    assert "gh pr create" not in r.stdout, "it opened a PR for an empty diff"
    assert not (tmp_path / "gh.log").exists(), "it called gh for an empty diff"


def test_a_changed_file_is_pushed_opened_gated_and_set_to_auto_merge(tmp_path):
    """The whole happy path, in order, including the two dispatches.

    The dispatches are not optional decoration. A PR opened with GITHUB_TOKEN
    emits no `pull_request` event (#322, PR #318), so without them the required
    `gates` and `build-gates` contexts never report and auto-merge waits
    forever on checks that will never arrive -- which looks exactly like the
    stall this change exists to end.
    """
    work = _repo(tmp_path)
    bindir = _fake_gh(tmp_path)
    (work / "measurements" / "loop.json").write_text('{"a": 2}\n')

    r = _run(work, bindir, "--path", "measurements", "--title", "measurement")
    assert r.returncode == 0, r.stdout + r.stderr

    # --dry-run PRINTS each mutation rather than running it, so the transcript
    # is stdout, not the fake gh's log. That is the point of the flag: every
    # guard above this line ran for real, and nothing reached the network.
    log = r.stdout
    assert "gh pr create" in log
    assert "--base main" in log
    assert "gh workflow run pr-gates.yml" in log
    assert "gh workflow run verify-build.yml" in log
    assert "gh pr merge" in log and "--auto" in log and "--squash" in log
    # the gates are dispatched BEFORE auto-merge is enabled: enabling it first
    # would be harmless but reads as a race to anyone auditing the log
    assert log.index("workflow run pr-gates") < log.index("pr merge")

    out = r.stdout
    assert "git push -u origin measurements/777-1" in out
    assert "git checkout -b measurements/777-1" in out


def test_the_branch_name_avoids_the_two_patterns_other_workflows_claim(tmp_path):
    """`feat/**` makes pr-gates fire twice; `issue/*` makes agent-merge sweep it.

    agent-merge re-evaluates open `issue/*` PRs every 30 minutes looking for a
    `qa-pass` label, which no measurement PR will ever carry -- it would sit in
    that sweep forever being refused, and a refusal in a log reads like a fault.
    """
    work = _repo(tmp_path)
    (work / "measurements" / "loop.json").write_text('{"a": 3}\n')
    out = _run(work, _fake_gh(tmp_path), "--path", "measurements", "--title", "m").stdout
    branch = [l for l in out.splitlines() if "checkout -b" in l][0].split()[-1]
    assert not branch.startswith("feat/")
    assert not branch.startswith("issue/")
    assert branch.startswith("measurements/")


def test_a_failed_push_fails_the_step(tmp_path):
    """Exit 1 (could not publish), distinct from exit 2 (wired wrong).

    The two are different repairs -- one is a credential or a protected branch,
    the other is a bad argument at a call site -- and `dispatch_cycle.sh`
    documents its codes for the same reason.
    """
    work = _repo(tmp_path)
    (work / "measurements" / "loop.json").write_text('{"a": 4}\n')
    bindir = _fake_gh(tmp_path)
    # a real push to a path that is not a repo
    subprocess.run(["git", "-C", str(work), "remote", "set-url", "origin",
                    str(tmp_path / "nope.git")], check=True)
    r = _run(work, bindir, "--path", "measurements", "--title", "m", dry=False)
    assert r.returncode == 1, r.stdout + r.stderr


def test_a_missing_token_is_a_wiring_error_not_a_publish_failure(tmp_path):
    work = _repo(tmp_path)
    bindir = _fake_gh(tmp_path)
    r = subprocess.run(
        ["bash", str(SCRIPT), "--path", "measurements", "--title", "m", "--dry-run"],
        cwd=work, capture_output=True, text=True,
        env={"PATH": f"{bindir}:/usr/bin:/bin", "GH_REPO": "a/b", "HOME": str(tmp_path)},
    )
    assert r.returncode == 2, r.stdout + r.stderr


# --------------------------------------------------------------------------- #
# the wiring: all six loops, and the fast path they rely on
# --------------------------------------------------------------------------- #

def _commit_step(wf: str) -> dict:
    doc = yaml.safe_load((WORKFLOWS / f"{wf}.yml").read_text())
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if (step.get("name") or "").startswith("Commit"):
                return {"step": step, "perms": job.get("permissions") or {}}
    raise AssertionError(f"{wf}: no Commit step")


@pytest.mark.parametrize("wf,path", sorted(LOOPS.items()))
def test_every_loop_publishes_through_the_script_and_never_pushes_main(wf, path):
    """All six move together, because four of the six breakages were latent.

    Pinned as a NEGATIVE as well as a positive: a `git push origin HEAD:main`
    restored beside the script call would satisfy every assertion about the
    script and leave that loop red forever, and the only symptom is a report
    that stops being written.
    """
    got = _commit_step(wf)
    run_text = got["step"]["run"]
    code = "\n".join(l for l in run_text.splitlines() if not l.lstrip().startswith("#"))
    assert "scripts/publish_measurements.sh" in code
    assert f"--path {path} " in code or f"--path {path}\n" in code

    for forbidden in ("HEAD:main", "git push origin", "git pull --rebase origin main"):
        assert forbidden not in code, f"{wf} still pushes main: {forbidden}"

    # The script needs all three, and an omitted scope reads as `none` -- a 403
    # that writes nothing, quietly, which is this issue's whole failure mode.
    assert got["perms"].get("contents") == "write"
    assert got["perms"].get("pull-requests") == "write"
    assert got["perms"].get("actions") == "write"
    assert got["step"]["env"]["GH_TOKEN"] == "${{ github.token }}"


def test_pr_gates_still_skips_its_expensive_steps_for_a_measurements_only_diff():
    """The fast path these PRs depend on, pinned where it can be widened.

    `agent-measure` alone opens eight PRs a day. Each costs ~1 minute while the
    scope step reads `code=false`, and ~8 minutes if `measurements/` is ever
    added to that pattern -- a one-word edit, with no test failure to stop it
    and no symptom except the Actions bill. The gate itself is NOT relaxed
    here: nothing under `measurements/` is in the Docker image (it copies
    `pyproject.toml`, `uv.lock`, `README.md` and `src/`) or read at runtime, so
    there is nothing for the suite to assert about such a diff.
    """
    import re
    text = (WORKFLOWS / "pr-gates.yml").read_text()
    m = re.search(r"if echo \"\$changed\" \| grep -qE '([^']+)'", text)
    assert m, "the scope step's pattern moved; this test is the only thing pinning it"
    pattern = re.compile(m.group(1))
    for p in ("measurements/loop.json", "measurements/latest.md",
              "measurements/sync/2026-10-21.md", "measurements/agents.json"):
        assert not pattern.search(p), f"{p} now triggers the full gates"
    # the control: real code must still match, or the test above proves nothing
    for p in ("src/astro_ai/llm.py", "tests/test_x.py", "scripts/verify_x.py",
              "uv.lock", ".github/workflows/pr-gates.yml"):
        assert pattern.search(p), f"{p} stopped triggering the gates"
