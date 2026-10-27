"""The derived test-count floor, driven over a REAL temporary git repository.

WHY NOT A UNIT TEST WITH STUBBED GIT
------------------------------------
Everything hard about this gate is the git plumbing: which ref it compares
against, what happens when there is no base, and whether `git show` can read a
file at a commit that is not checked out. A stubbed `git` would assert my
beliefs about those, and my beliefs were wrong twice while writing it:

  * it fell back to LOCAL `main` when `origin/main` was unavailable, and this
    repository's local `main` is pre-rewrite history (CLAUDE.md records the
    703/751 divergence). `merge-base HEAD main` answered an ancient commit where
    `tests/` did not exist, the base count came back 0, and the floor reported
    `PASS (543 >= 0)`. A floor comparing against nothing passes everything,
    which is the exact failure mode it was written to replace.
  * it printed its count unlabelled next to `verify_behaviour.py`'s, and the two
    legitimately differ -- 543 `def test_*` against 767 pytest cases, because
    one parametrised function is one name and N cases. Unlabelled, that reads as
    a regression of 224 tests.

So these tests build a real repo, commit, branch, delete, rename, and read the
gate's exit code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[1] / "scripts" / "verify_test_floor.py"


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(("git", "-C", str(repo), *args),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, f"git {' '.join(args)}: {out.stderr}"
    return out.stdout


def _run(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(repo / "scripts" / "verify_test_floor.py")],
                          capture_output=True, text=True, timeout=300)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with `origin/main` carrying two test files, and a branch off it."""
    origin = tmp_path / "origin"
    (origin / "tests").mkdir(parents=True)
    (origin / "scripts").mkdir()
    (origin / "scripts" / "verify_test_floor.py").write_text(GATE.read_text())
    (origin / "tests" / "test_a.py").write_text(
        "def test_one():\n    pass\n\n\ndef test_two():\n    pass\n")
    (origin / "tests" / "test_b.py").write_text(
        "class TestThing:\n    def test_three(self):\n        pass\n")
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@t")
    _git(origin, "config", "user.name", "T")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-q", "-m", "base")

    clone = tmp_path / "clone"
    subprocess.run(("git", "clone", "-q", str(origin), str(clone)), check=True, timeout=120)
    _git(clone, "config", "user.email", "t@t")
    _git(clone, "config", "user.name", "T")
    _git(clone, "checkout", "-q", "-b", "work")
    return clone


def test_an_added_test_passes(repo: Path):
    (repo / "tests" / "test_c.py").write_text("def test_four():\n    pass\n")
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "add one")
    r = _run(repo)
    assert r.returncode == 0, r.stdout
    assert "+1 added, 0 removed" in r.stdout


def test_a_deleted_file_fails_and_names_every_test(repo: Path):
    _git(repo, "rm", "-q", "tests/test_a.py")
    _git(repo, "commit", "-q", "-m", "drop a file")
    r = _run(repo)
    assert r.returncode == 1, r.stdout
    # NAMING them is the point. The constant this replaces printed only a
    # number, and both times coverage vanished the hunt for WHICH test took
    # the time, not the discovery.
    assert "tests/test_a.py::test_one" in r.stdout
    assert "tests/test_a.py::test_two" in r.stdout


def test_a_test_renamed_out_of_the_test_prefix_fails(repo: Path):
    """The silent case: the file is still collected, the test is simply gone."""
    p = repo / "tests" / "test_a.py"
    p.write_text(p.read_text().replace("def test_two(", "def checks_two("))
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "rename out")
    r = _run(repo)
    assert r.returncode == 1, r.stdout
    assert "tests/test_a.py::test_two" in r.stdout


def test_a_method_removed_from_a_test_class_fails(repo: Path):
    (repo / "tests" / "test_b.py").write_text("class TestThing:\n    pass\n")
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "gut the class")
    r = _run(repo)
    assert r.returncode == 1, r.stdout
    assert "test_three" in r.stdout


def test_a_declared_drop_passes_and_prints_the_reason(repo: Path):
    _git(repo, "rm", "-q", "tests/test_a.py")
    _git(repo, "commit", "-q", "-m", "drop a file\n\nTest-Count-Drop: merged into test_b")
    r = _run(repo)
    assert r.returncode == 0, r.stdout
    assert "merged into test_b" in r.stdout


def test_a_declared_drop_needs_the_trailer_not_just_the_words(repo: Path):
    """Prose is not a declaration. Only the trailer counts, because only the
    trailer is a thing a reviewer can grep for."""
    _git(repo, "rm", "-q", "tests/test_a.py")
    _git(repo, "commit", "-q", "-m", "drop a file because the test count drop is fine")
    r = _run(repo)
    assert r.returncode == 1, r.stdout


def test_no_base_is_reported_and_not_silently_skipped(repo: Path):
    """On `main` itself there is no base. That must SAY so, loudly enough that
    nobody reads the PASS as an assertion that held."""
    _git(repo, "checkout", "-q", "main")
    r = _run(repo)
    assert r.returncode == 0
    assert "no base" in r.stdout.lower()
    assert "nothing is asserted" in r.stdout


def test_a_missing_tests_directory_exits_2_not_0(repo: Path):
    """`pr-gates` reads exit 2 as "the check did not run, which is not a pass"."""
    _git(repo, "rm", "-rq", "tests")
    _git(repo, "commit", "-q", "-m", "no tests at all")
    r = _run(repo)
    assert r.returncode == 2, r.stdout
    assert "NOT a pass" in r.stdout


def test_it_never_compares_against_local_main(repo: Path):
    """THE DEFECT, pinned. A fallback to local `main` is what made this gate
    report `543 >= 0` in the real repo, because local main there is pre-rewrite
    history with no `tests/`."""
    src = GATE.read_text()
    assert '"merge-base", "HEAD", "origin/main"' in src
    assert 'for remote in ("origin/main", "main")' not in src


# --- parametrize cases (#446 part 3 residual) --------------------------------
# Independent QA on PR #448 deleted one entry from the literal list in
# tests/test_dispatch_carrier.py and the gate printed `+9 added, 0 removed`,
# PASS, exit 0: it compared `def test_*` NAMES, and a parametrised function is
# one name however many cases it has. These pin the case-count comparison.

PARAM3 = ('import pytest\n\n\n@pytest.mark.parametrize("x", [1, 2, 3])\n'
          'def test_p(x):\n    pass\n')


def _commit_param(repo: Path, body: str, msg: str = "edit") -> None:
    (repo / "tests" / "test_p.py").write_text(body)
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", msg)


@pytest.fixture
def param_repo(repo: Path) -> Path:
    """`repo`, but with a 3-case parametrised test already on origin/main."""
    origin = repo.parent / "origin"
    (origin / "tests" / "test_p.py").write_text(PARAM3)
    _git(origin, "add", "-A"); _git(origin, "commit", "-q", "-m", "param")
    _git(repo, "fetch", "-q", "origin")
    _git(repo, "checkout", "-q", "-B", "work", "origin/main")
    return repo


def test_a_deleted_parametrize_case_fails_and_names_the_function(param_repo: Path):
    _commit_param(param_repo, PARAM3.replace("[1, 2, 3]", "[1, 2]"))
    r = _run(param_repo)
    assert r.returncode == 1, r.stdout
    assert "tests/test_p.py::test_p: 3 -> 2 cases" in r.stdout


def test_a_middle_case_deleted_is_still_a_drop(param_repo: Path):
    """Index-style IDs would only shift here; the count is what catches it."""
    _commit_param(param_repo, PARAM3.replace("[1, 2, 3]", "[1, 3]"))
    assert _run(param_repo).returncode == 1


def test_an_added_parametrize_case_passes(param_repo: Path):
    _commit_param(param_repo, PARAM3.replace("[1, 2, 3]", "[1, 2, 3, 4]"))
    r = _run(param_repo)
    assert r.returncode == 0, r.stdout


def test_stacked_parametrize_is_a_product(param_repo: Path):
    stacked = ('import pytest\n\n\n@pytest.mark.parametrize("y", ["a", "b"])\n'
               '@pytest.mark.parametrize("x", [1, 2, 3])\n'
               'def test_p(x, y):\n    pass\n')
    _commit_param(param_repo, stacked)             # 3 -> 6: fine
    assert _run(param_repo).returncode == 0
    _git(param_repo, "checkout", "-q", "-B", "work2", "origin/main")
    # [1] x [a, b] = 2 cases, below the base's 3.
    _commit_param(param_repo, stacked.replace("[1, 2, 3]", "[1]"))
    r = _run(param_repo)
    assert r.returncode == 1, r.stdout
    assert "3 -> 2 cases" in r.stdout


def test_a_name_bound_once_to_a_literal_is_followed(param_repo: Path):
    named = ('import pytest\n\nCASES = [1, 2, 3]\n\n\n'
             '@pytest.mark.parametrize("x", CASES)\n'
             'def test_p(x):\n    pass\n')
    _commit_param(param_repo, named)
    assert _run(param_repo).returncode == 0
    _git(param_repo, "checkout", "-q", "-B", "work2", "origin/main")
    _commit_param(param_repo, named.replace("[1, 2, 3]", "[1, 2]"))
    r = _run(param_repo)
    assert r.returncode == 1 and "3 -> 2 cases" in r.stdout


def test_computed_argvalues_do_not_crash_and_a_literal_turned_computed_fails(param_repo: Path):
    computed = ('import pytest\n\n\n@pytest.mark.parametrize("x", sorted({1, 2, 3}))\n'
                'def test_p(x):\n    pass\n')
    _commit_param(param_repo, computed)
    r = _run(param_repo)
    # 3 literal cases became uncountable: unverifiable, so not a pass.
    assert r.returncode == 1, r.stdout
    assert "cannot be counted" in r.stdout
    assert "Traceback" not in r.stderr


def test_a_computed_base_is_not_compared(repo: Path):
    """Nothing was verifiable at the base, so nothing can be said to be lost."""
    origin = repo.parent / "origin"
    computed = ('import pytest\n\n\n@pytest.mark.parametrize("x", sorted({1, 2, 3}))\n'
                'def test_p(x):\n    pass\n')
    (origin / "tests" / "test_p.py").write_text(computed)
    _git(origin, "add", "-A"); _git(origin, "commit", "-q", "-m", "param")
    _git(repo, "fetch", "-q", "origin")
    _git(repo, "checkout", "-q", "-B", "work", "origin/main")
    _commit_param(repo, computed.replace("{1, 2, 3}", "{1, 2}"))
    r = _run(repo)
    assert r.returncode == 0, r.stdout


def test_a_declared_drop_passes_a_case_drop(param_repo: Path):
    _commit_param(param_repo, PARAM3.replace("[1, 2, 3]", "[1, 2]"),
                  "trim\n\nTest-Count-Drop: case 3 duplicated case 2")
    r = _run(param_repo)
    assert r.returncode == 0, r.stdout
    assert "case 3 duplicated case 2" in r.stdout
