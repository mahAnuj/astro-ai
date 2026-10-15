"""`agent-merge` must hold a PR that touches the trust boundary (#354).

WHY THIS IS HERE, given the charter in conftest.py.

conftest says every test in this suite is a defect that shipped. This one is not,
and is admitted knowingly, on the same footing as test_health_deploy_marker.py:
the control lives in a YAML file, nothing type-checks it, and its failure mode is
silent in the worst way. A matcher that misses `src/astro_ai/prompts/sub/x.txt`,
or a downstream step whose `if:` still reads `steps.size` and so walks straight
past the new step, does not error. The PR just merges, unattended, on a public
repo, with a change to the system prompt in it.

So these tests execute the real thing: they lift the `is_protected` shell
function out of the workflow's own run block, and the real TRUST_BOUNDARY list
out of its env, and drive them with a table of paths. They do not reimplement
the matcher. Nothing from a PR is executed; the paths are literals below.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = (Path(__file__).resolve().parent.parent
            / ".github" / "workflows" / "agent-merge.yml")


def _job() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["merge"]


def _step(step_id: str) -> dict:
    return next(s for s in _job()["steps"] if s.get("id") == step_id)


def _is_protected(path: str) -> str | None:
    """Run the workflow's own `is_protected` with its own list. None = not held."""
    run = _step("boundary")["run"]
    m = re.search(r"^(\s*)is_protected\(\) \{\n.*?^\1\}\n", run, re.S | re.M)
    assert m, "is_protected() is gone from the Trust boundary step"
    script = m.group(0) + '\nis_protected "$1"\n'
    r = subprocess.run(
        ["bash", "-c", script, "bash", path],
        env={"TRUST_BOUNDARY": _job()["env"]["TRUST_BOUNDARY"], "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode in (0, 1), r.stderr
    return r.stdout.strip() if r.returncode == 0 else None


HELD = [
    ("src/astro_ai/prompts/natal.txt", "src/astro_ai/prompts/"),
    ("src/astro_ai/prompts/sub/x.txt", "src/astro_ai/prompts/"),
    ("src/astro_ai/knowledge/SOURCES.md", "src/astro_ai/knowledge/"),
    ("src/astro_ai/knowledge/a/b/c.md", "src/astro_ai/knowledge/"),
    (".github/workflows/agent-merge.yml", ".github/workflows/"),
    (".github/workflows/new.yml", ".github/workflows/"),
    ("src/astro_ai/events.py", "src/astro_ai/events.py"),
    ("src/astro_ai/notify.py", "src/astro_ai/notify.py"),
    ("src/astro_ai/email_sender.py", "src/astro_ai/email_sender.py"),
    ("src/astro_ai/storage.py", "src/astro_ai/storage.py"),
]

# Near-misses: each shares a prefix, a suffix or a directory name with a
# protected entry and must NOT be held, or the guard is a tax on every PR.
FREE = [
    "src/astro_ai/prompts_extra.py",
    "src/astro_ai/prompts",              # a file named like the directory
    "src/astro_ai/knowledge_index.py",
    "src/astro_ai/events_helper.py",
    "src/astro_ai/events.pyc",
    "src/astro_ai/notify.py.bak",
    "src/astro_ai/email_sender.pyi",
    "src/astro_ai/storage_gcs.py",
    "src/astro_ai/routes/events.py",     # same basename, different directory
    "src/astro_ai/routes/storage.py",
    "tests/test_events.py",
    "tests/prompts/natal.txt",
    "scripts/verify_workflows.py",
    ".github/workflows",                 # no trailing slash: not beneath it
    ".github/CODEOWNERS",
    ".github/workflows_old/x.yml",
    "docs/src/astro_ai/prompts/natal.txt",   # prefix must anchor at the root
    "CLAUDE.md",
    "",
]


@pytest.mark.parametrize("path,entry", HELD)
def test_protected_path_is_held(path, entry):
    assert _is_protected(path) == entry


@pytest.mark.parametrize("path", FREE)
def test_near_miss_is_not_held(path):
    assert _is_protected(path) is None


def test_glob_characters_in_a_filename_are_data():
    """A name is compared as a string. `*` in it must not match anything."""
    assert _is_protected("src/astro_ai/*") is None
    assert _is_protected("src/astro_ai/events.p?") is None


def test_every_step_after_the_boundary_waits_on_it():
    """Chain: size -> boundary -> {draft, merge, post-merge verify}. If any of
    them still read `steps.size`, it would run when the boundary step held the PR."""
    steps = _job()["steps"]
    ids = [s.get("id") for s in steps]
    b = ids.index("boundary")
    assert ids.index("size") < b
    assert _step("boundary")["if"] == "steps.size.outputs.ok == 'true'"
    for s in steps[b + 1:]:
        cond = s.get("if", "")
        if "gh pr merge" in s.get("run", "") or "gh pr ready" in s.get("run", "") \
                or "verify-production" in s.get("run", ""):
            assert "steps.boundary.outputs.ok == 'true'" in cond, s["name"]
            assert "steps.size.outputs.ok" not in cond, s["name"]


def test_merge_job_still_has_no_checkout():
    """pull_request_target with a write token: nothing from the PR may run."""
    for s in _job()["steps"]:
        assert "actions/checkout" not in s.get("uses", ""), s.get("name")


def test_step_never_interpolates_pr_data_into_the_script():
    """File names arrive through a file. `${{ }}` in the run block is allowed
    only for values GitHub itself computes (none are needed here)."""
    assert "${{" not in _step("boundary")["run"]
