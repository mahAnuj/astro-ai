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

A conflict marker is a run of SEVEN OR MORE identical marker characters at the
START of a line, followed by whitespace or end-of-line. All three of git's
directional markers count, including the diff3/zdiff3 base marker that
`merge.conflictStyle` adds and which a scanner written from memory forgets:

    ours   -> N x '<' + ' <ref>'
    base   -> N x '|' + ' <ref>'       (diff3 and zdiff3 only)
    theirs -> N x '>' + ' <ref>'

SEVEN OR MORE, not seven. The first version of this gate matched exactly seven
and said the width was "git's, and not configurable". It is neither:
`conflict-marker-size` is a gitattribute, and git honours 1 through 80
(measured 2026-10-28, one real conflict per width). A nine-character marker
does not match a seven-character pattern -- after the seventh `<` comes an
eighth, not the whitespace the pattern requires -- so a committed, live
conflict block scored a clean PASS and the gate's entire purpose was defeated
by one line in `.gitattributes`.

`markers()` holds the floor and the one corroboration rule that keeps the
widening from costing false positives. Read it there; it is a decision, not a
regex.

The bare separator — a run of '=' alone on a line — is NOT a trigger. It is
also a legitimate Markdown setext heading rule, and git never writes it without
the directional markers around it. It IS printed as context when a file is
already flagged, so a human reading the output sees the whole block.

WHAT THIS WEAKENS, plainly:

  - a half-resolved file where someone deleted the directional markers by hand
    and left the bare separator behind passes. Nothing distinguishes that line
    from a setext rule, and guessing would make every `===` heading in `/learn`
    a blocker.
  - a marker narrower than seven characters passes. See `markers()` for why
    that floor is a judgment rather than a limit.
  - untracked files are not scanned at all. That is the point: the defect is
    what reaches `origin/main`, and the working tree during a live merge is
    *supposed* to contain markers. The INDEX is what this gate reads -- paths
    AND content, which the first version got only half right.
  - the paths in SKIP_PREFIXES are not scanned even if they become tracked.
    They are scratch space this repo deliberately keeps out of git; a marker
    inside one of them is a local mess, not a shipped artefact.
  - binary files are skipped. A marker in a PNG is not a merge someone forgot
    to finish.

EXIT CODES
  0  no tracked file carries a marker
  1  at least one does — every hit is printed with its path and line number
  2  could not run: not a git repository, `git ls-files` or `git cat-file`
     failed, or the scan excluded this gate's own source. NOT a pass.

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
#
# THE WIDTH IS NOT GIT'S TO FIX, and the first version of this file said it was
# ("`MARKER_WIDTH` is git's, and is not configurable"). That claim was wrong,
# and it was the whole gate: a regex anchored on exactly seven characters
# cannot match a nine-character marker, because after the seventh `<` comes an
# eighth, not the whitespace the pattern demands. A committed, live conflict
# block scored a clean PASS.
#
# `conflict-marker-size` is a gitattribute and a `git merge-file` option, and
# git honours the whole range. Measured 2026-10-28 in a scratch repository, one
# real conflict per width:
#
#     requested=1   actual=1        requested=7   actual=7
#     requested=3   actual=3        requested=20  actual=20
#     requested=6   actual=6        requested=80  actual=80
#
# So the floor is a JUDGMENT, not git's limit. 7 is kept as the floor because
# below it the marker characters are ordinary text — `> ` is a Markdown
# blockquote and `|` opens a table row — and a gate that flags those blocks
# every PR in a repository whose reasoning lives in Markdown.
MARKER_MIN = 7
OURS = "<" * MARKER_MIN
BASE = "|" * MARKER_MIN
THEIRS = ">" * MARKER_MIN
SEPARATOR = "=" * MARKER_MIN

DIRECTIONAL_CHARS = (OURS[0], BASE[0], THEIRS[0])
SEPARATOR_CHAR = SEPARATOR[0]

# A run of one marker character at the start of a line, followed by whitespace
# or the line end. The WIDTH IS NOT FIXED here; `markers()` applies the floor
# and the corroboration rule, because both are decisions and a regex is a bad
# place to hide a decision.
_CANDIDATE_RE = re.compile(r"^(<+|\|+|>+|=+)(?:\s|$)")

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


def index_entries(root: Path) -> list[tuple[str, str]]:
    """`(path, blob sha)` for every stage-0 entry in the index.

    THE INDEX, CONTENT AND ALL. The previous version took its PATHS from the
    index and then read each file from the WORKING TREE, which is a different
    question with a different answer -- and the docstring claimed the index,
    which is how the gap survived review. In CI the two coincide, because a
    fresh checkout's tree matches its commit; on a developer's machine they do
    not, and the gate's stated job is "what is about to be shipped".

    An UNMERGED path is skipped (`stage != 0`). That is not a loophole: git
    refuses to commit an index with unmerged entries at all, so such a path
    cannot reach `main` without first being resolved, and resolving it is what
    produces the stage-0 entry this gate then reads.

    A gitlink (mode 160000) is skipped: a submodule pointer has no blob here.

    `-z` because a path may contain anything but NUL.
    """
    out = subprocess.run(
        ("git", "-C", str(root), "ls-files", "-s", "-z"),
        capture_output=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError(
            f"git ls-files -s -> rc={out.returncode} "
            f"{out.stderr.decode('utf-8', 'replace').strip()[:300]}")
    entries: list[tuple[str, str]] = []
    for record in out.stdout.decode("utf-8", "replace").split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        parts = meta.split()
        if len(parts) != 3 or not path:
            continue
        mode, sha, stage = parts
        if stage != "0" or mode == "160000":
            continue
        entries.append((path, sha))
    return entries


def tracked_files(root: Path) -> list[str]:
    """Just the paths, for the self-honesty check at the end of `main`."""
    return [path for path, _ in index_entries(root)]


def blob_bytes(root: Path, shas: list[str]) -> dict[str, bytes]:
    """`sha -> content`, through ONE `git cat-file --batch`.

    One process, not one per file: 619 blobs at a process each is seconds of
    fork for a gate whose entire selling point is that it is cheap enough to
    run unconditionally, before `setup-uv`, on every pull request.

    `--batch` answers each request with `<oid> <type> <size>\n`, then exactly
    `size` bytes, then a newline. Parsed as BYTES throughout -- a blob is not
    text until this gate decides it is one, and decoding the stream to find the
    headers would corrupt every binary file in it.
    """
    if not shas:
        return {}
    out = subprocess.run(
        ("git", "-C", str(root), "cat-file", "--batch"),
        input=("\n".join(shas) + "\n").encode("ascii"),
        capture_output=True, timeout=300,
    )
    if out.returncode != 0:
        raise RuntimeError(
            f"git cat-file --batch -> rc={out.returncode} "
            f"{out.stderr.decode('utf-8', 'replace').strip()[:300]}")
    found: dict[str, bytes] = {}
    buf = out.stdout
    i = 0
    while i < len(buf):
        nl = buf.find(b"\n", i)
        if nl < 0:
            break
        header = buf[i:nl].decode("utf-8", "replace").split()
        i = nl + 1
        # `<oid> missing` for an object this repository does not have. Nothing
        # to read is not a marker, and it is not this gate's business to judge.
        if len(header) != 3:
            continue
        oid, _kind, size_s = header
        try:
            size = int(size_s)
        except ValueError:
            continue
        found[oid] = buf[i:i + size]
        i += size + 1          # the trailing newline --batch adds
    return found


def markers(text: str) -> list[tuple[int, str]]:
    """Every conflict-marker line in `text`, as `(1-based line number, line)`.

    WHY THE WIDTHS ARE NOT TREATED ALIKE

    At exactly `MARKER_MIN` — git's default, and the only width this repository
    has produced — a single directional line is damning on its own. Seven `<`
    or `>` followed by a space is not a shape that occurs in prose, and a
    half-resolved file where someone deleted the separator by hand still gets
    caught.

    Above it, a same-width companion with a DIFFERENT marker character is
    required, because git writes a BLOCK and prose does not. Nine `>` followed
    by a space is a nine-deep Markdown blockquote as readily as a marker; nine
    `>` with a matching nine-wide `=` or `<` somewhere in the same file is a
    merge nobody finished.

    MEASURED, so the trade is not a guess: scanned across the 619 tracked text
    files on `main` at 2026-10-28, lines matching a 7-or-wider run at line
    start followed by whitespace: **zero**. Widening the floor from "exactly 7"
    to "7 or more" newly flags nothing that is here today.

    WHAT THIS STILL LETS THROUGH, plainly:

      - a width below `MARKER_MIN`. Someone who sets
        `conflict-marker-size=3` and commits the result passes this gate. The
        alternative is flagging every blockquote and table row in `/learn`.
      - a lone wide marker with no companion — a hand-edited leftover at a
        non-default width.

    AND THE ONE FALSE POSITIVE IT ACCEPTS: a file carrying both a decorative
    rule and a blockquote at the SAME width above 7 — say twelve `<` on one
    line and twelve `>` on another — reads as a block and is flagged. It is
    stated rather than hidden; the output names the file and the line, and one
    space fixes it. That is the right way round for a gate whose miss shipped a
    corrupt `ARCHITECTURE.md` to `main`.
    """
    candidates: list[tuple[int, str, str, int]] = []
    for n, line in enumerate(text.splitlines(), start=1):
        m = _CANDIDATE_RE.match(line)
        if not m:
            continue
        run = m.group(1)
        if len(run) >= MARKER_MIN:
            candidates.append((n, line, run[0], len(run)))

    chars_at_width: dict[int, set[str]] = {}
    for _, _, ch, w in candidates:
        chars_at_width.setdefault(w, set()).add(ch)

    hits: list[tuple[int, str]] = []
    for n, line, ch, w in candidates:
        # The separator is context, never a trigger: a run of `=` alone on a
        # line is a legitimate Markdown setext heading rule, and git never
        # writes one without the directional markers around it.
        if ch == SEPARATOR_CHAR:
            continue
        if w == MARKER_MIN or len(chars_at_width[w]) > 1:
            hits.append((n, line))
    return hits


def separators(text: str) -> list[tuple[int, str]]:
    """Separator lines, for printing a condemned file's whole block."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        m = _CANDIDATE_RE.match(line)
        if m and m.group(1)[0] == SEPARATOR_CHAR and len(m.group(1)) >= MARKER_MIN:
            out.append((n, line))
    return out


def scan(root: Path) -> tuple[list[tuple[str, int, str]], list[str], int]:
    """Markers in `root`'s tracked text files.

    Returns (hits, scanned, skipped_count) where a hit is
    (relative path, 1-based line number, the line).
    """
    hits: list[tuple[str, int, str]] = []
    scanned: list[str] = []
    skipped = 0

    # One `git ls-files`, not two: the second call was a real cost on a gate
    # that justifies its unconditional `pr-gates` step by being cheap.
    all_entries = index_entries(root)
    entries = [(rel, sha) for rel, sha in all_entries if not _skipped(rel)]
    skipped += len(all_entries) - len(entries)
    content = blob_bytes(root, sorted({sha for _, sha in entries}))

    texts: dict[str, str] = {}
    for rel, sha in entries:
        data = content.get(sha)
        if data is None:
            skipped += 1
            continue
        data = data[:_READ_LIMIT]
        if b"\0" in data:
            skipped += 1
            continue
        scanned.append(rel)
        text = data.decode("utf-8", "replace")
        texts[rel] = text
        # Cheap pre-filter on the characters themselves, not on a fixed-width
        # marker string: the width is no longer known in advance.
        if not any(ch * MARKER_MIN in text for ch in DIRECTIONAL_CHARS):
            continue
        for n, line in markers(text):
            hits.append((rel, n, line.rstrip()))

    # The separator is context, not a trigger: only ever reported for a file
    # that a directional marker already condemned.
    for rel in {rel for rel, _, _ in hits}:
        for n, line in separators(texts[rel]):
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
