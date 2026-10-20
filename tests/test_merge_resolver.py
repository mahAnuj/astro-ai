"""The conflict resolver's parser, against the shapes that actually broke it.

WHY THIS FILE EXISTS
--------------------
`scripts/merge_main_into_branch.py` is what `steward.md` routes every
`pr-conflicting` stall to. On 2026-10-20, the first time a conflict actually
needed it (PR #443 against #425), it could not run AT ALL and its parser was
wrong on two of the three shapes it would have met:

  * its dirty-tree check used `git status --porcelain`, which lists UNTRACKED
    files -- and CLAUDE.md names five that this repo carries permanently by
    intention. So the check was unsatisfiable in the only tree it was written
    for. An instruction the system cannot execute: #442's defect class.
  * `text.index("\n=======\n")` raises on an EMPTY THEIRS side, and
    `text.index("\n=======")` raises on an EMPTY OURS side. Both raise
    ValueError, which reads as "no conflict here" rather than "an empty side" --
    a parse bug that presents as a clean file.
  * each side was returned WITHOUT its trailing newline when it was the last
    line of the hunk, so `resolve_union_dated` re-joined two decision-log rows
    into ONE: a row's text ended up inside another and a third stopped being a
    row. Every test green; found by eye, in ARCHITECTURE.md, the same morning.

The third is the one with teeth, because the resolver exists specifically to
stop `git checkout --theirs` dropping rows -- and it was dropping rows itself.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

SPEC = importlib.util.spec_from_file_location(
    "mmib", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "merge_main_into_branch.py")
mmib = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mmib)

MARK = "origin/main"


def test_an_empty_theirs_side_parses():
    """PR #443's actual shape: our 4 new mutation rows, nothing on their side."""
    t = "a\n<<<<<<< HEAD\nmine\n=======\n>>>>>>> origin/main\nz\n"
    h = mmib.hunks(t, MARK)
    assert len(h) == 1
    assert h[0][3] == "mine\n"
    assert h[0][4] == ""


def test_an_empty_ours_side_parses():
    t = "a\n<<<<<<< HEAD\n=======\ntheirs\n>>>>>>> origin/main\nz\n"
    h = mmib.hunks(t, MARK)
    assert len(h) == 1
    assert h[0][3] == ""
    assert h[0][4] == "theirs\n"


def test_both_sides_keep_their_trailing_newline():
    t = "<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> origin/main\n"
    _, _, _, ours, theirs = mmib.hunks(t, MARK)[0]
    assert ours.endswith("\n") and theirs.endswith("\n")


def test_a_dated_union_never_absorbs_one_row_into_another():
    """THE DEFECT, restored. This is what shipped into ARCHITECTURE.md."""
    t = ("<<<<<<< HEAD\n| 2026-10-20 | mine |\n=======\n"
         "| 2026-10-19 | theirs |\n>>>>>>> origin/main\n")
    out = mmib.resolve_union_dated(t, MARK)
    rows = [l for l in out.splitlines() if l.startswith("| 20")]
    assert len(rows) == 2, f"a row was absorbed: {rows}"
    assert all(l.count("| 20") == 1 for l in rows), rows
    assert rows[0].split("|")[1].strip() == "2026-10-19", "dated rows must sort by date"


def test_a_union_drops_nothing():
    """`verify_no_relaxation.py` fails on a falling mutation-row count, and it is
    right to -- so the resolver for that file may never drop a side."""
    t = "<<<<<<< HEAD\nrow_a\nrow_b\n=======\nrow_c\n>>>>>>> origin/main\n"
    out = mmib.resolve_union(t, MARK)
    for row in ("row_a", "row_b", "row_c"):
        assert row in out, f"{row} was dropped"


def test_several_hunks_in_one_file_are_all_found():
    t = ("<<<<<<< HEAD\na\n=======\nb\n>>>>>>> origin/main\n"
         "middle\n"
         "<<<<<<< HEAD\nc\n=======\nd\n>>>>>>> origin/main\n")
    assert len(mmib.hunks(t, MARK)) == 2


def test_a_hunk_with_no_separator_raises_rather_than_returning_nothing():
    """Silence is the failure mode this whole file is about: a parser that
    returns `[]` on a malformed hunk reports a clean file."""
    with pytest.raises(RuntimeError):
        mmib.hunks("<<<<<<< HEAD\nmine\n>>>>>>> origin/main\n", MARK)


def test_the_dirty_check_ignores_untracked_files():
    """`--untracked-files=no` is the difference between "can run here" and
    "refuses in the only repo it was written for"."""
    src = pathlib.Path(SPEC.origin).read_text()
    assert '"--untracked-files=no"' in src, (
        "the dirty check must ignore untracked files; CLAUDE.md names five this "
        "repo carries permanently, so the plain form can never be satisfied")
