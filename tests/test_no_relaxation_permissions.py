"""Rules 8 and 9 of `scripts/verify_no_relaxation.py`: a workflow's
`permissions:` may not widen, and `TRUST_BOUNDARY` may not lose a path (#610).

WHY THESE TWO RULES CARRY SO MUCH. Until 2026-11-01 a `.github/workflows/` PR
was held for the repo owner, and the reason stated in `chief.md` was blast
radius: "a workflow edit can grant the loop new powers, read secrets, or disable
the gates that constrain every other agent." The user then widened `chief`'s
Shape C to the whole trust boundary — *"I want the loop to not hold on me"* —
which converts that risk from "a human reads it" into "a gate catches it".

`chief.md` is now written against these two rules by name: a red
`verify_no_relaxation` is never chief's to rule on. So a hole here is not one
missing check, it is the only thing standing between an agent and its own
constraints. That is why every case below asserts the gate goes RED, and why
the narrowing cases exist too — a gate that fails on everything would be
"safe" and useless, and would be quietly disabled within a week.

EVERY END-TO-END CASE RUNS AGAINST A REAL TEMPORARY GIT REPOSITORY with two
commits, because the gate's whole subject is a DIFF: it reads `git show
<base>:<path>` on both sides. A fixture of loose files would exercise only the
exit-2 "no usable base" path and prove nothing.

`REQUIRED_SUBSTRINGS` IS EMPTIED IN EVERY END-TO-END CASE, deliberately. Rule 7
checks phrases in files like `.claude/commands/agent-cycle.md` on every run,
whether or not they are in the diff — so in a temp repo that holds only a
workflow file it reports them all missing and the gate goes red for the wrong
reason. The gate's own source records this exact trap from the other side: "A
gate validated by a rule other than the one under test is a vacuous pass, which
is the defect this whole repo keeps finding." `test_the_harness_isolates_rules_8_and_9`
proves the isolation is real rather than assumed.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = ROOT / "scripts" / "verify_no_relaxation.py"

_spec = importlib.util.spec_from_file_location("verify_no_relaxation", GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_no_relaxation"] = gate
_spec.loader.exec_module(gate)

AM = ".github/workflows/agent-merge.yml"

#: A minimal but STRUCTURALLY REAL agent-merge: the gate reads `permissions:`
#: at two levels and `TRUST_BOUNDARY` from inside a job's `env:`, so a fixture
#: that flattens either would test a shape the gate never meets.
def _agent_merge(top: str, job: str, boundary: tuple[str, ...]) -> str:
    tb = "".join(f"        {p}\n" for p in boundary)
    return (
        "name: Agent merge\n"
        "on:\n"
        "  workflow_dispatch:\n"
        f"permissions:\n{top}"
        "jobs:\n"
        "  merge:\n"
        "    runs-on: ubuntu-latest\n"
        f"    permissions:\n{job}"
        "    env:\n"
        "      TRUST_BOUNDARY: |\n"
        f"{tb}"
        "      OTHER: after-the-block\n"
        # The `own -> gates -> qa -> size` chain is carried verbatim because
        # rules 5 and 6 run on any diff that touches this path and would red
        # every case below on a fixture that omitted it — the "passed for the
        # wrong reason" trap, in the direction that hides a real green.
        "    steps:\n"
        "      - name: Who wrote it\n"
        "        id: own\n"
        "        run: echo ok=true >> \"$GITHUB_OUTPUT\"\n"
        "      - name: Checks\n"
        "        id: gates\n"
        "        if: steps.own.outputs.ok == 'true'\n"
        "        run: echo ok=true >> \"$GITHUB_OUTPUT\"\n"
        "      - name: QA verdict\n"
        "        id: qa\n"
        "        if: steps.gates.outputs.ok == 'true'\n"
        "        run: echo qa-pass qa-fail\n"
        "      - name: Size and path limits\n"
        "        id: size\n"
        "        if: steps.qa.outputs.ok == 'true'\n"
        "        run: echo ok=true >> \"$GITHUB_OUTPUT\"\n"
    )


BOUNDARY = ("src/astro_ai/prompts/", "src/astro_ai/knowledge/", ".github/workflows/")
READ_TOP = "  contents: read\n"
WRITE_TOP = "  contents: write\n"
JOB_READ = "      contents: read\n"
JOB_WRITE = "      contents: write\n"


def _repo(tmp_path: Path, before: dict[str, str], after: dict[str, str]) -> Path:
    """A git repo whose branch `base` holds `before` and whose HEAD holds `after`.

    `base` IS LEFT BEHIND ON THE FIRST COMMIT, which is the whole point. The
    first version of this fixture committed both states on a branch called
    `base`, so `git merge-base HEAD base` resolved to HEAD itself and the gate
    reported "no files changed against the merge base" — a PASS, on every case
    including the adversarial ones. A fixture that cannot produce a diff proves
    nothing about a gate whose only subject is a diff.

    Identity is passed with `-c` rather than configured, so the fixture never
    depends on — or writes to — the global git config of whatever machine runs
    the suite.
    """
    root = tmp_path / "repo"
    root.mkdir()
    run = lambda *a: subprocess.run(  # noqa: E731 - a local alias, not an API
        ("git", "-C", str(root),
         "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a),
        check=True, timeout=60, capture_output=True)
    subprocess.run(("git", "init", "-q", "-b", "work", str(root)), check=True, timeout=60)
    for i, state in enumerate((before, after)):
        for rel, body in state.items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "--allow-empty", "-m", f"state{i}")
        if i == 0:
            run("branch", "base")
    return root


def _run(root: Path, monkeypatch, capsys) -> tuple[int, str]:
    monkeypatch.chdir(root)
    monkeypatch.setattr(gate, "REQUIRED_SUBSTRINGS", {})   # see the module docstring
    rc = gate.main(["verify_no_relaxation.py", "--base", "base"])
    return rc, capsys.readouterr().out


# --------------------------------------------------------------------------
# _normalise_perms — the ladder every comparison rests on
# --------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (None, {}),
    ({}, {}),
    ("write-all", {"<all>": 2}),
    ("read-all", {"<all>": 1}),
    ({"contents": "write"}, {"contents": 2}),
    ({"contents": "read"}, {"contents": 1}),
    ({"contents": "none"}, {"contents": 0}),
    ({"contents": "write", "issues": "read"}, {"contents": 2, "issues": 1}),
])
def test_normalise_perms_maps_each_shape_onto_the_ladder(value, expected):
    assert gate._normalise_perms(value) == expected


@pytest.mark.parametrize("weird", ["banana", {"contents": "banana"}, ["contents"], 7])
def test_an_unrecognised_permissions_shape_ranks_as_WIDE_not_as_absent(weird):
    """Fail-wide, not fail-open.

    An unknown value ranking 0 would make `contents: <something new GitHub
    added>` read as a REVOCATION, and the gate would then report a widening as
    a tightening. Ranking it 2 can only produce a false red, which costs one
    human merge; the other direction costs the grant.
    """
    assert max(gate._normalise_perms(weird).values()) == 2


# --------------------------------------------------------------------------
# _perm_blocks — top-level and per-job must stay separate
# --------------------------------------------------------------------------

def test_top_level_and_job_permissions_are_reported_separately():
    doc = {"permissions": {"contents": "read"},
           "jobs": {"merge": {"permissions": {"issues": "write"}}}}
    assert gate._perm_blocks(doc) == {
        "<top-level>": {"contents": 1},
        "jobs.merge": {"issues": 2},
    }


def test_job_permissions_are_not_merged_into_the_top_level_block():
    """A job block OVERRIDES the top-level one; it does not add to it.

    Merging them would do both wrongs at once: a job that narrows would read as
    a widening of the top level, and a job that widens a scope the top level
    also names would be masked.
    """
    doc = {"permissions": {"contents": "write"},
           "jobs": {"a": {"permissions": {"contents": "read"}}}}
    blocks = gate._perm_blocks(doc)
    assert blocks["<top-level>"] == {"contents": 2}
    assert blocks["jobs.a"] == {"contents": 1}


@pytest.mark.parametrize("doc", [None, "a string", ["a", "list"], 3, {"jobs": "not-a-dict"}])
def test_a_document_with_no_permissions_anywhere_yields_no_blocks(doc):
    assert gate._perm_blocks(doc) == {}


def test_a_job_without_its_own_permissions_contributes_no_block():
    doc = {"jobs": {"merge": {"runs-on": "ubuntu-latest"}}}
    assert gate._perm_blocks(doc) == {}


# --------------------------------------------------------------------------
# _trust_boundary
# --------------------------------------------------------------------------

def test_the_boundary_is_read_from_the_SHIPPED_agent_merge_file():
    """Ties the parser to the real file, not to a fixture that resembles it.

    A parser proved only against hand-written YAML is the shape of defect this
    repo keeps finding: it passes until the real file's indentation differs.
    """
    paths = gate._trust_boundary((ROOT / AM).read_text(encoding="utf-8"))
    assert ".github/workflows/" in paths
    assert "src/astro_ai/prompts/" in paths
    assert "src/astro_ai/notify.py" in paths
    assert len(paths) >= 7


def test_the_block_ends_at_the_first_line_that_dedents():
    text = _agent_merge(READ_TOP, JOB_READ, BOUNDARY)
    assert gate._trust_boundary(text) == set(BOUNDARY)
    assert "OTHER: after-the-block" not in str(gate._trust_boundary(text))


def test_a_blank_line_inside_the_block_does_not_end_it():
    text = ("    env:\n      TRUST_BOUNDARY: |\n        a/\n\n        b/\n      NEXT: x\n")
    assert gate._trust_boundary(text) == {"a/", "b/"}


def test_no_block_at_all_reads_as_an_empty_set():
    assert gate._trust_boundary("name: x\njobs: {}\n") == set()


# --------------------------------------------------------------------------
# Rule 8, end to end — a widening goes RED
# --------------------------------------------------------------------------

@pytest.mark.parametrize("before_job,after_job,why", [
    (JOB_READ, JOB_WRITE, "read -> write"),
    (JOB_READ, "      contents: read\n      issues: write\n", "a scope appeared"),
    ("      contents: none\n", JOB_READ, "none -> read"),
])
def test_rule_8_goes_red_when_a_job_block_widens(before_job, after_job, why,
                                                 tmp_path, monkeypatch, capsys):
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, before_job, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, after_job, BOUNDARY)},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, f"{why} was accepted:\n{out}"
    assert "jobs.merge" in out and "permissions" in out


def test_rule_8_goes_red_on_write_all_replacing_a_narrow_block(tmp_path, monkeypatch, capsys):
    """`write-all` is the shortest possible way to grant everything.

    It is a STRING where a mapping was, so a comparison that only walked keys
    would see no scope widen and pass it.
    """
    narrow = _agent_merge(READ_TOP, JOB_READ, BOUNDARY)
    broad = narrow.replace("    permissions:\n      contents: read\n",
                           "    permissions: write-all\n")
    assert broad != narrow, "fixture did not substitute write-all"
    root = _repo(tmp_path, {AM: narrow}, {AM: broad})
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert "<all>" in out


def test_rule_8_goes_red_on_a_permissions_block_that_is_entirely_new(tmp_path, monkeypatch, capsys):
    """A new block grants without widening anything, so it must fail closed.

    The cost is bounded and already paid: the App token is refused the
    `workflows` permission, so every change under `.github/workflows/` already
    needs a human or a Claude session to push it.
    """
    before = _agent_merge(READ_TOP, JOB_READ, BOUNDARY)
    after = before + (
        "  second:\n"
        "    runs-on: ubuntu-latest\n"
        "    permissions:\n"
        "      actions: write\n"
        "    steps:\n"
        "      - run: echo second\n")
    root = _repo(tmp_path, {AM: before}, {AM: after})
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert "jobs.second" in out and "is new" in out


def test_rule_8_goes_red_on_a_brand_new_workflow_file(tmp_path, monkeypatch, capsys):
    other = ".github/workflows/agent-newthing.yml"
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY),
         other: _agent_merge(WRITE_TOP, JOB_WRITE, BOUNDARY)},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert other in out


def test_rule_8_goes_red_rather_than_quiet_on_a_workflow_it_cannot_parse(
        tmp_path, monkeypatch, capsys):
    """An unreadable gate is not a pass.

    This is the single most likely way to get a widening past rule 8: make the
    file unparseable and let the `except` swallow it.
    """
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY)},
        {AM: "permissions:\n  contents: write\n  - this is not valid yaml\n\t\tat all:\n"},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert "cannot be parsed as YAML" in out


# --------------------------------------------------------------------------
# Rule 8 — the other direction. A gate that reds on everything gets disabled.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("before_job,after_job,what", [
    (JOB_WRITE, JOB_READ, "write -> read"),
    (JOB_WRITE, "      contents: none\n", "write -> none"),
    ("      contents: write\n      issues: write\n", JOB_WRITE, "a scope removed"),
])
def test_rule_8_stays_green_when_permissions_narrow_or_hold(before_job, after_job, what,
                                                            tmp_path, monkeypatch, capsys):
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, before_job, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, after_job, BOUNDARY)},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 0, f"{what} was rejected:\n{out}"
    assert "permissions held" in out


def test_a_workflow_that_is_not_in_the_diff_is_not_judged(tmp_path, monkeypatch, capsys):
    """Rule 8 is diff-scoped, and that is deliberate for THIS rule.

    Rule 7 is not, because a phrase's absence is a fact about HEAD. A
    permissions widening is a fact about a CHANGE, and judging an untouched
    file would red every PR in the repo on the first pre-existing broad scope.
    """
    root = _repo(
        tmp_path,
        {AM: _agent_merge(WRITE_TOP, JOB_WRITE, BOUNDARY), "README.md": "a\n"},
        {AM: _agent_merge(WRITE_TOP, JOB_WRITE, BOUNDARY), "README.md": "b\n"},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 0, out
    assert "permissions held" not in out


# --------------------------------------------------------------------------
# Rule 9 — TRUST_BOUNDARY
# --------------------------------------------------------------------------

def test_rule_9_goes_red_when_a_boundary_path_is_removed(tmp_path, monkeypatch, capsys):
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, JOB_READ,
                          tuple(p for p in BOUNDARY if p != ".github/workflows/"))},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert "`TRUST_BOUNDARY` lost .github/workflows/" in out


def test_rule_9_goes_red_when_the_whole_block_disappears(tmp_path, monkeypatch, capsys):
    before = _agent_merge(READ_TOP, JOB_READ, BOUNDARY)
    after = "\n".join(l for l in before.splitlines()
                      if "TRUST_BOUNDARY" not in l and l.strip() not in BOUNDARY) + "\n"
    root = _repo(tmp_path, {AM: before}, {AM: after})
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert "`TRUST_BOUNDARY` block is gone" in out


def test_rule_9_stays_green_when_the_boundary_GROWS(tmp_path, monkeypatch, capsys):
    """A wider boundary holds more, never less, so it is not a relaxation.

    Checking it would punish the safest change available to this file.
    """
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY + ("src/astro_ai/billing.py",))},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 0, out
    assert "boundary intact" in out


def test_rule_9_reports_a_removal_even_when_another_path_is_added(tmp_path, monkeypatch, capsys):
    """Swapping one path for another keeps the COUNT identical.

    A length comparison would pass this, which is why the rule uses a set
    difference.
    """
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, JOB_READ,
                          ("src/astro_ai/prompts/", "src/astro_ai/knowledge/", "docs/"))},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 1, out
    assert "`TRUST_BOUNDARY` lost .github/workflows/" in out


# --------------------------------------------------------------------------
# The harness itself
# --------------------------------------------------------------------------

def test_the_harness_isolates_rules_8_and_9(tmp_path, monkeypatch, capsys):
    """Proves the clean case is clean BECAUSE rules 8 and 9 passed.

    Without emptying `REQUIRED_SUBSTRINGS` the gate reds in a temp repo on
    missing phrase files, so every red case above would pass for the wrong
    reason. This asserts the baseline is green and names the two rules that
    reported.
    """
    root = _repo(
        tmp_path,
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY)},
        {AM: _agent_merge(READ_TOP, JOB_READ, BOUNDARY).replace("echo qa-pass", "echo  qa-pass")},
    )
    rc, out = _run(root, monkeypatch, capsys)
    assert rc == 0, out
    assert "permissions held" in out
    assert "boundary intact" in out
    assert "PASS" in out


def test_the_gates_docstring_registers_both_new_rules():
    """A rule the docstring does not list is a rule the next reader will delete.

    `chief.md` cites `verify_no_relaxation.py` by name as the thing that makes
    its workflow-clearing grant non-circular; that citation is only as good as
    this file's own account of what it checks.
    """
    doc = GATE_PATH.read_text(encoding="utf-8")
    assert "8. A workflow's `permissions:` may not WIDEN" in doc
    assert "9. `TRUST_BOUNDARY` may not lose an entry" in doc
