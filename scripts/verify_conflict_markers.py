#!/usr/bin/env python3
"""Gate: no TRACKED file carries an unresolved merge-conflict marker (#384).

WHY THIS EXISTS

`ARCHITECTURE.md` sat on `origin/main` with a live conflict block in the §1
table of measured counts — both sides byte-identical, so no content decision
had been skipped, just the markers left in. It survived because none of the
27 `scripts/verify_*.py` gates grepped any tracked file for a marker:

    git grep -lE '<' -- scripts/      # nothing matched; see the note below

`verify_architecture_counts.py` reads that exact file and passed the whole
time: it matches each row by its label and takes the first hit, so a row
duplicated behind a marker is invisible to it.

The same defect in Python or Jinja is caught by `ast.parse` or a template
render. In Markdown it is silent — and Markdown is where this repo keeps its
reasoning. `CLAUDE.md` tells every agent to read `ARCHITECTURE.md` before
designing, so the corrupted file was the one whose entire job is to be read by
a fresh context that cannot tell a decision log from a merge artefact.

THE MARKERS ARE NEVER WRITTEN DOWN IN THIS FILE

A marker-scanner is the one gate that trivially flags itself: its patterns, its
docstring and its tests all want to quote the thing they look for. The obvious
fix — exempt `scripts/` and `tests/` — is the wrong one, because it would also
hide a REAL marker in exactly the files that implement and prove the gate.

So nothing is exempted. The marker strings are ASSEMBLED AT RUNTIME from a
character and a repeat count (below), so this file and its tests genuinely
contain no marker, and the scan covers them on the same terms as every other
tracked file. A literal marker pasted into either one is therefore caught.
`tests/test_conflict_marker_gate.py` asserts that property directly, so the
mechanism cannot rot into a comment nobody honours. The `git grep` line in the
paragraph above is deliberately truncated for the same reason.

The scan also refuses to be narrowed into uselessness: if this file is tracked
but was not among the files scanned, that is exit 2, not a pass.

WHAT IT MATCHES

A conflict marker is seven identical characters at the START of a line,
followed by whitespace or end-of-line. All three of git's directional markers
count, including the diff3/zdiff3 base marker that `merge.conflictStyle` adds
and which a scanner written from memory forgets:

    ours   -> 7x '<' + ' <ref>'
    base   -> 7x '|' + ' <ref>'        (diff3 and zdiff3 only)
    theirs -> 7x '>' + ' <ref>'

The bare separator — 7x '=' alone on a line — is NOT a trigger. It is also a
legitimate Markdown setext heading rule, and git never writes it without the
directional markers around it. It IS printed as context when a file is already
flagged, so a human reading the output sees the whole block.

WHAT THIS WEAKENS, plainly:

  - a half-resolved file where someone deleted the directional markers by hand
    and left the bare separator behind passes. Nothing distinguishes that line
    from a setext rule, and guessing would make every `===` heading in `/learn`
    a blocker.
  - untracked files are not scanned at all. That is the point: the defect is
    what reaches `origin/main`, and the working tree during a live merge is
    *supposed* to contain markers.
  - the paths in SKIP_PREFIXES are not scanned even if they become tracked.
    They are scratch space this repo deliberately keeps out of git; a marker
    inside one of them is a local mess, not a shipped artefact.
  - binary files are skipped. A marker in a PNG is not a merge someone forgot
    to finish.

EXIT CODES
  0  no tracked file carries a marker
  1  at least one does — every hit is printed with its path and line number
  2  could not run: not a git repository, `git ls-files` failed, or the scan
     excluded this gate's own source. NOT a pass.

USAGE
  python scripts/verify_conflict_markers.py          # this repository
  python scripts/verify_conflict_markers.py <path>   # another checkout

Stdlib only, on purpose: `pr-gates` installs `uv` and the dev group behind the
`code == 'true'` scope check, and the defect this gate exists for arrived in a
DOCS-ONLY diff. It has to be runnable with bare `python3` before any install.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Assembled, never quoted — see "THE MARKERS ARE NEVER WRITTEN DOWN" above.
# `MARKER_WIDTH` is git's, and is not configurable.
MARKER_WIDTH = 7
OURS = "<" * MARKER_WIDTH
BASE = "|" * MARKER_WIDTH
THEIRS = ">" * MARKER_WIDTH
SEPARATOR = "=" * MARKER_WIDTH

DIRECTIONAL = (OURS, BASE, THEIRS)
MARKER_RE = re.compile(
    "^(?:" + "|".join(re.escape(m) for m in DIRECTIONAL) + r")(?:\s|$)")
SEPARATOR_RE = re.compile("^" + re.escape(SEPARATOR) + r"[ \t]*$")

# Untracked by intention: agent scratch space, worktrees, run artefacts and
# local caches. Listed as literal prefixes so adding one is a visible diff line
# rather than a pattern that quietly widens.
SKIP_PREFIXES = (
    ".local/",
    ".serena/",
    "QA_LOG.md",
    ".claude/worktrees/",
    "verify-main/",
    ".agents/",
    ".codex/",
    "AGENTS.md",
    ".rashifal-run/",
    "data/",
)

# Read in chunks: a marker is a short line, and the whole point is to be cheap
# enough to run unconditionally on every pull request.
_READ_LIMIT = 8 * 1024 * 1024


def _skipped(rel: str) -> bool:
    return rel == "" or any(
        rel == p or rel.startswith(p) for p in SKIP_PREFIXES)


def tracked_files(root: Path) -> list[str]:
    """Every path in the index, as repo-relative POSIX strings.

    The INDEX, not the working tree: a marker only matters once it is committed
    and shipped, and during a real merge the working tree is expected to carry
    them. `-z` because a path may contain anything but NUL.
    """
    out = subprocess.run(
        ("git", "-C", str(root), "ls-files", "-z"),
        capture_output=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(
            f"git ls-files -> rc={out.returncode} "
            f"{out.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


def scan(root: Path) -> tuple[list[tuple[str, int, str]], list[str], int]:
    """Markers in `root`'s tracked text files.

    Returns (hits, scanned, skipped_count) where a hit is
    (relative path, 1-based line number, the line).
    """
    hits: list[tuple[str, int, str]] = []
    scanned: list[str] = []
    skipped = 0
    for rel in tracked_files(root):
        if _skipped(rel):
            skipped += 1
            continue
        path = root / rel
        try:
            data = path.read_bytes()[:_READ_LIMIT]
        except (OSError, ValueError):
            # Tracked but not readable here: a deleted-not-staged path, a
            # submodule gitlink, a broken symlink. Nothing to read is not a
            # marker, and it is not this gate's business to judge.
            skipped += 1
            continue
        if b"\0" in data:
            skipped += 1
            continue
        scanned.append(rel)
        text = data.decode("utf-8", "replace")
        if not any(m in text for m in DIRECTIONAL):
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            if MARKER_RE.match(line):
                hits.append((rel, n, line.rstrip()))
    # The separator is context, not a trigger: only ever reported for a file
    # that a directional marker already condemned.
    condemned = {rel for rel, _, _ in hits}
    for rel in condemned:
        text = (root / rel).read_bytes()[:_READ_LIMIT].decode("utf-8", "replace")
        for n, line in enumerate(text.splitlines(), start=1):
            if SEPARATOR_RE.match(line):
                hits.append((rel, n, line.rstrip()))
    hits.sort(key=lambda h: (h[0], h[1]))
    return hits, scanned, skipped


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else ROOT

    print("Merge-conflict markers in tracked files (#384)")
    print(f"  root    : {root}")
    try:
        hits, scanned, skipped = scan(root)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"\nCOULD NOT RUN (exit 2) — {type(exc).__name__}: {exc}")
        print("A scan that did not run is not a scan that passed.")
        return 2

    print(f"  scanned : {len(scanned)} tracked text files "
          f"({skipped} skipped: binary, unreadable, or SKIP_PREFIXES)")

    if not scanned:
        print("\nCOULD NOT RUN (exit 2) — nothing was scanned. An empty scan")
        print("reports no markers for the same reason a broken one does.")
        return 2

    # THE SELF-HONESTY CHECK. This gate quotes no marker, which is the only
    # reason it can scan its own source; the matching obligation is that it
    # actually does. If it is tracked and was not scanned, something excluded
    # it — and an exempted scanner is how a marker hides in the file that looks
    # for markers.
    me = Path(__file__).resolve()
    try:
        mine = me.relative_to(root).as_posix()
    except ValueError:
        mine = None
    if mine and mine in tracked_files(root) and mine not in scanned:
        print(f"\nCOULD NOT RUN (exit 2) — {mine} is tracked but was not")
        print("scanned, so this gate has exempted itself. Remove whatever")
        print("excludes it; do not let the marker-scanner be the one file a")
        print("marker can hide in.")
        return 2

    if not hits:
        print(f"\nPASS ({len(scanned)} tracked text files, no conflict markers)")
        return 0

    files = sorted({rel for rel, _, _ in hits})
    print(f"\nFAIL — {len(hits)} conflict-marker line(s) in {len(files)} "
          f"tracked file(s):")
    for rel, n, line in hits:
        print(f"  {rel}:{n}: {line[:88]}")
    print("\nThis is an unfinished merge that was committed. Open each file,")
    print("decide which side is right (they may be identical — ARCHITECTURE.md's")
    print("was), delete the markers, and commit the resolution. Do not silence")
    print("this gate: a marker in a Markdown file is invisible to every other")
    print("check in this repository, which is why it reached main once already.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
