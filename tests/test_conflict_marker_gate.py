"""scripts/verify_conflict_markers.py must go red on a committed marker (#384).

`ARCHITECTURE.md` reached `origin/main` with a live conflict block in its table
of measured counts, and 27 gates passed over it — `verify_architecture_counts.py`
reads that very file and reported PASS, because it matches each row by label and
takes the first hit, so a row duplicated behind a marker is invisible to it. In
Python or Jinja the same defect dies at `ast.parse` or a template render; in
Markdown nothing looked.

EVERY CASE RUNS AGAINST A REAL TEMPORARY GIT REPOSITORY under `tmp_path`. The
gate reads the INDEX — paths from `git ls-files -s`, content from
`git cat-file` — so a fixture must be a genuine repo; a directory of files
would exercise nothing but the exit-2 path. The repository under test is never
touched.

THE WIDTH CASES MERGE FOR REAL rather than writing markers into a file. The
claim under test there is about what GIT WRITES at a given
`conflict-marker-size`, and a hand-written fixture at width 9 would prove the
pattern while proving nothing about whether git ever emits one. The shipped
gate's comment asserted the width was "git's, and is not configurable"; it is a
gitattribute, and git honours 1 through 80.

NO MARKER IS WRITTEN LITERALLY IN THIS FILE, and that is the point rather than a
style choice. A marker-scanner is the one gate that trivially flags itself, and
the tempting fix — exempt `scripts/` and `tests/` — would hide a real marker in
exactly the two places that implement and prove the gate. So the gate assembles
its patterns at runtime and these tests assemble their fixtures the same way;
both files are then scanned on the same terms as every other tracked file.
`test_the_gate_quotes_no_marker_so_it_can_scan_its_own_source` asserts that
property directly, and `test_a_marker_in_the_gates_own_source_is_still_caught`
proves the absence of an exemption from the other side.

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
GATE_PATH = ROOT / "scripts" / "verify_conflict_markers.py"

_spec = importlib.util.spec_from_file_location("verify_conflict_markers", GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_conflict_markers"] = gate
_spec.loader.exec_module(gate)

# Assembled, never quoted — see the module docstring.
OURS = "<" * 7
BASE = "|" * 7
THEIRS = ">" * 7
SEPARATOR = "=" * 7

CONFLICTED = (
    "# doc\n"
    f"{OURS} HEAD\n"
    "| behaviour suite | 570 tests |\n"
    f"{SEPARATOR}\n"
    "| behaviour suite | 570 tests |\n"
    f"{THEIRS} origin/main\n"
)


def _repo(tmp_path: Path, files: dict[str, str | bytes],
          untracked: dict[str, str] | None = None) -> Path:
    """A real git repo whose index holds `files`, plus optional untracked ones.

    `git add -f` because a global `core.excludesFile` on the machine running
    this must not decide what the fixture contains — `data/` is a real path in
    this repo's own ignore list and one case needs it tracked.

    Nothing is committed: `git ls-files` reads the index, which is precisely
    the state the gate is meant to judge ("about to be shipped"). Skipping the
    commit also keeps the fixture free of user identity and signing config.
    """
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(("git", "init", "-q", str(root)), check=True, timeout=60)
    for rel, body in {**files, **(untracked or {})}.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            p.write_bytes(body)
        else:
            p.write_text(body, encoding="utf-8")
    if files:
        subprocess.run(("git", "-C", str(root), "add", "-f", "--", *files),
                       check=True, timeout=60)
    return root


def _run(root: Path, capsys) -> tuple[int, str]:
    rc = gate.main([str(root)])
    return rc, capsys.readouterr().out


def test_a_clean_repository_passes(tmp_path, capsys):
    root = _repo(tmp_path, {"docs/clean.md": "# fine\n", "src/app.py": "x = 1\n"})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out
    assert "2 tracked text files" in out


@pytest.mark.parametrize("marker", [OURS, THEIRS], ids=["ours", "theirs"])
def test_a_planted_directional_marker_turns_the_gate_red(tmp_path, capsys, marker):
    root = _repo(tmp_path, {"ARCHITECTURE.md": f"# doc\n{marker} HEAD\nrow\n"})
    rc, out = _run(root, capsys)
    assert rc == 1, out
    assert "FAIL" in out
    assert "ARCHITECTURE.md:2:" in out, out


def test_the_diff3_base_marker_alone_turns_the_gate_red(tmp_path, capsys):
    """`merge.conflictStyle = diff3`/`zdiff3` writes a THIRD marker, and a
    scanner written from memory lists only two. The fixture carries the base
    marker and nothing else, so a gate that forgot it reports a clean tree."""
    root = _repo(tmp_path, {
        "ARCHITECTURE.md": f"# doc\n{BASE} merged common ancestors\nrow\n"})
    rc, out = _run(root, capsys)
    assert rc == 1, out
    assert "ARCHITECTURE.md:2:" in out, out


def test_a_bare_separator_is_a_setext_rule_not_a_conflict(tmp_path, capsys):
    """Seven `=` alone on a line is valid Markdown for an h1 underline, and git
    never writes it without the directional markers. Triggering on it would
    block every setext heading in `/learn`."""
    root = _repo(tmp_path, {
        "docs/setext.md": f"Heading\n{SEPARATOR}\nbody\n"})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_a_marker_quoted_mid_line_is_not_a_conflict(tmp_path, capsys):
    """Prose about conflicts, and `>>>` in a heredoc or a doctest, must pass.

    git writes a marker at column 0; anything indented or embedded is someone
    talking about one. A gate matching anywhere in the line would condemn this
    repository's own documentation of the defect."""
    root = _repo(tmp_path, {
        "docs/prose.md": f"the merge left `{OURS} HEAD` in the file\n"
                         f"    {THEIRS} indented, so not a marker\n"})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


# --- the width is not seven, and that was the whole defect ------------------

def _merge_conflict(tmp_path: Path, width: int, name: str = "f.md") -> Path:
    """A repository whose index holds a REAL git conflict block of `width`.

    Built by actually merging, never by writing markers into a file, because
    the claim under test is about what GIT WRITES. A hand-written fixture at
    width 9 would prove the regex and nothing about whether git ever emits one.
    """
    root = tmp_path / f"repo{width}"
    root.mkdir()
    g = ("git", "-C", str(root))
    subprocess.run(("git", "init", "-q", str(root)), check=True, timeout=60)
    for k, v in (("user.email", "gate@test"), ("user.name", "gate")):
        subprocess.run((*g, "config", k, v), check=True, timeout=60)
    (root / ".gitattributes").write_text(
        f"{name} conflict-marker-size={width}\n", encoding="utf-8")
    (root / name).write_text("base\n", encoding="utf-8")
    subprocess.run((*g, "add", "-A"), check=True, timeout=60)
    subprocess.run((*g, "commit", "-qm", "base"), check=True, timeout=60)
    subprocess.run((*g, "checkout", "-qb", "other"), check=True, timeout=60)
    (root / name).write_text("theirs\n", encoding="utf-8")
    subprocess.run((*g, "commit", "-qam", "theirs"), check=True, timeout=60)
    subprocess.run((*g, "checkout", "-q", "-"), check=True, timeout=60)
    (root / name).write_text("ours\n", encoding="utf-8")
    subprocess.run((*g, "commit", "-qam", "ours"), check=True, timeout=60)
    # Conflicts, so a non-zero return is the expected outcome.
    subprocess.run((*g, "merge", "other"), capture_output=True, timeout=60)
    # `git add` is what a person does next, and it is what puts the unfinished
    # merge into the index -- the state this gate judges.
    subprocess.run((*g, "add", name), check=True, timeout=60)
    return root


@pytest.mark.parametrize("width", [9, 20])
def test_git_writes_whatever_marker_width_it_is_asked_for(tmp_path, width):
    """The premise the shipped gate got wrong, measured rather than asserted.

    Its comment read "`MARKER_WIDTH` is git's, and is not configurable".
    `conflict-marker-size` is a gitattribute; git honours 1 through 80. This
    pins the premise so the floor in `markers()` stays a stated judgment
    instead of drifting back into a claim about git.
    """
    root = _merge_conflict(tmp_path, width)
    body = (root / "f.md").read_text(encoding="utf-8")
    opener = next(ln for ln in body.splitlines() if ln.startswith("<"))
    assert len(opener.split()[0]) == width, opener


@pytest.mark.parametrize("width", [9, 20])
def test_a_real_conflict_at_a_non_default_width_turns_the_gate_red(
        tmp_path, capsys, width):
    """THE DEFECT. The shipped gate scored `PASS (2 tracked text files, no
    conflict markers)` on exactly this repository: a committed, live conflict
    block, defeated by one line in `.gitattributes`."""
    root = _merge_conflict(tmp_path, width)
    rc, out = _run(root, capsys)
    assert rc == 1, out
    assert "f.md:1:" in out


def test_a_lone_wide_marker_needs_a_companion_of_its_own_width(tmp_path, capsys):
    """Above the floor a single run is not enough, and that is what pays for
    the widening.

    git writes a BLOCK; prose does not. Twelve `>` followed by a space is a
    twelve-deep Markdown blockquote as readily as a marker, so on its own it
    passes -- which is why widening the floor from "exactly 7" to "7 or more"
    costs no false positives on the 619 tracked text files measured on `main`.
    """
    root = _repo(tmp_path, {"docs/quote.md": f"{THEIRS}{'>' * 5} deep quote\n"})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_a_wide_block_is_caught_once_its_companion_is_there(tmp_path, capsys):
    """The other side of the same rule: a wide run WITH a same-width companion
    of a different marker character is a merge nobody finished."""
    root = _repo(tmp_path, {
        "docs/x.md": f"{OURS}{'<' * 5} HEAD\na\n{SEPARATOR}{'=' * 5}\nb\n"})
    rc, out = _run(root, capsys)
    assert rc == 1, out
    assert "docs/x.md:1:" in out


def test_a_marker_below_the_floor_is_not_a_conflict(tmp_path, capsys):
    """The floor is a judgment and it is stated as one: below seven, `>` is a
    blockquote and `|` opens a table row, and flagging those would block every
    PR in a repository whose reasoning lives in Markdown. Someone who sets
    `conflict-marker-size=3` and commits the result gets past this gate."""
    root = _repo(tmp_path, {
        "docs/six.md": f"{'<' * 6} HEAD\na\n{'=' * 6}\nb\n{'>' * 6} other\n"})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


# --- the index, content and all -------------------------------------------

def test_the_gate_reads_the_index_not_the_working_tree(tmp_path, capsys):
    """The shipped gate took its PATHS from the index and read each file's
    CONTENT from the working tree, while its docstring claimed the index. In CI
    the two coincide; on a developer's machine they do not, and "what is about
    to be shipped" is the index.

    Here the block is staged and then tidied up on disk only. The gate must
    still fail: `git commit` would ship the marker.
    """
    root = _repo(tmp_path, {"ARCHITECTURE.md": CONFLICTED})
    (root / "ARCHITECTURE.md").write_text("# resolved on disk only\n",
                                          encoding="utf-8")
    rc, out = _run(root, capsys)
    assert rc == 1, out
    assert "ARCHITECTURE.md:2:" in out


def test_an_unmerged_index_entry_is_skipped_not_reported(tmp_path, capsys):
    """A conflict mid-merge has unmerged (stage 1/2/3) index entries and no
    stage-0 entry. That is not a loophole: `git commit` refuses an index with
    unmerged paths, so nothing can reach `main` until it is resolved -- and
    resolving it is what creates the stage-0 entry the test above catches."""
    root = _merge_conflict(tmp_path, 9, name="g.md")
    # Undo the `git add` the helper does, putting the path back to unmerged.
    subprocess.run(("git", "-C", str(root), "checkout", "-m", "--", "g.md"),
                   check=True, timeout=60)
    stages = subprocess.run(
        ("git", "-C", str(root), "ls-files", "-s", "--", "g.md"),
        capture_output=True, text=True, check=True, timeout=60).stdout
    assert " 0\t" not in stages, f"fixture is not unmerged: {stages!r}"
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_the_separator_is_reported_as_context_in_a_condemned_file(tmp_path, capsys):
    """The separator cannot trigger a failure, but a human reading the output
    needs the whole block, not two of its three lines.

    BOTH halves are asserted, because "it appears" alone was too weak to be a
    gate. Making the separator a trigger as well as context left this test
    green while the line was reported twice -- and a separator that triggers
    turns every setext heading in `/learn` into a blocked pull request. So the
    count is pinned too: three marker lines, each exactly once.
    """
    root = _repo(tmp_path, {"ARCHITECTURE.md": CONFLICTED})
    rc, out = _run(root, capsys)
    assert rc == 1, out
    for line in ("ARCHITECTURE.md:2:", "ARCHITECTURE.md:4:", "ARCHITECTURE.md:6:"):
        assert out.count(line) == 1, out
    assert "3 conflict-marker line(s)" in out, out


def test_an_untracked_file_carrying_a_marker_is_ignored(tmp_path, capsys):
    """During a live merge the working tree is SUPPOSED to hold markers. A gate
    that read the working tree would be red for the whole of every conflict
    resolution, which is how a gate gets commented out."""
    root = _repo(tmp_path, {"docs/clean.md": "# fine\n"},
                 untracked={"mid-merge.md": CONFLICTED})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_a_binary_file_carrying_a_marker_is_skipped(tmp_path, capsys):
    """A byte run inside a PNG is not an unfinished merge, and decoding every
    tracked blob as text would make the output unreadable when it is."""
    blob = b"\x89PNG\x00\x00" + f"\n{OURS} HEAD\n".encode()
    root = _repo(tmp_path, {"docs/clean.md": "# fine\n", "static/i.png": blob})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "1 skipped" in out, out


def test_a_marker_inside_a_skip_prefix_path_is_not_scanned(tmp_path, capsys):
    """`data/` and the agent scratch paths are untracked by intention. Forcing
    one into the index must not turn the gate red — and the exclusion is a
    literal prefix list, so widening it is a visible diff line."""
    assert "data/" in gate.SKIP_PREFIXES
    root = _repo(tmp_path, {"docs/clean.md": "# fine\n",
                            "data/daily_cache/x.md": CONFLICTED})
    rc, out = _run(root, capsys)
    assert rc == 0, out
    assert "PASS" in out


def test_a_directory_that_is_not_a_git_repository_exits_two(tmp_path, capsys):
    """Exit 2, never 0. `pr-gates` treats 2 as "did not run" and fails the
    sweep; a gate that cannot list tracked files reporting PASS is the failure
    mode this whole file exists to prevent."""
    (tmp_path / "loose").mkdir()
    (tmp_path / "loose" / "ARCHITECTURE.md").write_text(CONFLICTED)
    rc, out = _run(tmp_path / "loose", capsys)
    assert rc == 2, out
    assert "COULD NOT RUN" in out


def test_a_repository_with_no_tracked_text_files_exits_two(tmp_path, capsys):
    """An empty scan prints the same "no markers found" as a working one."""
    root = _repo(tmp_path, {})
    rc, out = _run(root, capsys)
    assert rc == 2, out
    assert "COULD NOT RUN" in out


def test_the_gate_quotes_no_marker_so_it_can_scan_its_own_source():
    """The mechanism that replaces a self-exemption, asserted rather than
    trusted to a comment.

    If a future edit pastes a literal marker into either file — the natural
    thing to do when documenting this gate — the honest options are to keep it
    assembled or to accept that the gate now reports its own source. This test
    makes that a decision instead of an accident.
    """
    for path in (GATE_PATH, Path(__file__).resolve()):
        body = path.read_text(encoding="utf-8")
        for marker in (OURS, BASE, THEIRS):
            assert marker not in body, (
                f"{path.name} contains a literal conflict marker, so the gate "
                f"now flags it. Assemble it at runtime, as everything else in "
                f"these two files does.")
        assert not any(l.startswith(SEPARATOR) for l in body.splitlines()), (
            f"{path.name} opens a line with the separator")


def test_a_marker_in_the_gates_own_source_is_still_caught(tmp_path, capsys):
    """The other direction: no path-based exemption hides the gate from itself.

    The fixture is the gate's REAL source, at its real repo-relative path, with
    one marker line planted inside a string literal so the copy stays valid
    Python. A gate carrying `scripts/` on an allowlist would pass this.
    """
    planted = GATE_PATH.read_text(encoding="utf-8") + (
        '\n_PROBE = """\n' + OURS + ' HEAD\n"""\n')
    root = _repo(tmp_path, {"docs/clean.md": "# fine\n",
                            "scripts/verify_conflict_markers.py": planted})
    rc, out = _run(root, capsys)
    assert rc == 1, out
    assert "scripts/verify_conflict_markers.py:" in out, out


def test_a_gate_that_excluded_its_own_source_exits_two(tmp_path):
    """Narrowing the scan until it no longer covers the scanner is exit 2.

    Run as a SUBPROCESS from inside the temporary repository, because the check
    compares the gate's own `__file__` against the scanned set — in-process that
    path points at the real tree and the check correctly declines to fire.
    """
    src = GATE_PATH.read_text(encoding="utf-8")
    needle = "SKIP_PREFIXES = (\n"
    assert needle in src
    narrowed = src.replace(needle, needle + '    "scripts/",\n', 1)
    root = _repo(tmp_path, {"docs/clean.md": "# fine\n",
                            "scripts/verify_conflict_markers.py": narrowed})
    r = subprocess.run(
        (sys.executable, str(root / "scripts" / "verify_conflict_markers.py"),
         str(root)),
        capture_output=True, text=True, timeout=120)
    assert r.returncode == 2, f"{r.stdout}\n{r.stderr}"
    assert "exempted itself" in r.stdout, r.stdout
