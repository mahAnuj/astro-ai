#!/usr/bin/env python3
"""Gate: every `src/astro_ai/prompts/*.txt` matches the hash committed in
`src/astro_ai/prompts/MANIFEST.json`.

WHY THIS EXISTS
---------------
`routes/deps.py` reads those files at runtime and they become the system prompt
of every LLM request. Nothing asserted anything about their content (#362):
`verify_natal_prompt.py` checks one prompt's structure, the behaviour suite
covers request paths, and a diff that rewrites a system prompt passed the same
gates as a diff that renames a variable. A prompt change was an ordinary text
hunk inside a larger PR.

The point is not the hash. It is that changing a prompt now needs a SECOND,
deliberate edit in the same commit, and that this gate's failure is a line in
the PR's check output naming the file that changed. A reviewer who skims the
diff still sees it; `qa` has something mechanical to read.

A gate rather than a hold, on purpose: a red check is information the loop can
act on and a human can read. The #354 path hold labels the PR and waits, which
is the right shape for provenance and the wrong shape for "did the text change".

WHAT IT CHECKS
--------------
  * every `*.txt` in the directory has a manifest entry (an unlisted file is a
    FAILURE, not a skip -- a new prompt must be declared);
  * every manifest entry names a file that exists;
  * sha256 of the file's RAW BYTES equals the entry. Bytes, not text: no
    newline translation, no decoding, so the answer cannot differ between a
    checkout and CI. (Measured 2026-10-16: no .gitattributes, no CRLF in any of
    the 11 prompts, Linux CI performs no eol conversion.)

Scope is `*.txt` only. `knowledge/*.md` is deliberately out of scope: no Python
opens it at runtime, so a hash there would assert the wrong thing.

EXIT CODES
----------
0 pass   1 the comparison failed   2 could not verify -- NOT a pass
A missing manifest, invalid JSON, or the wrong shape is exit 2: `pr-gates.yml`
treats 2 as a failure rather than a skip, so a gate that could not run cannot be
mistaken for one that passed.

CHANGING A PROMPT
-----------------
    uv run python scripts/verify_prompt_manifest.py --update

rewrites the manifest from what is on disk. It is an explicit flag and never the
default: a gate that regenerated its own expectations when run bare would pass
on anything. Commit the manifest with the prompt, in the same commit.

Runs with no arguments (pr-gates sweeps `scripts/verify_*.py` bare), stdlib
only, no network. `--dir PATH` points it at another directory; it exists so the
tests can drive THIS script against a temp copy instead of reimplementing it.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "src" / "astro_ai" / "prompts"
MANIFEST_NAME = "MANIFEST.json"
UPDATE_CMD = "uv run python scripts/verify_prompt_manifest.py --update"

_NAME = re.compile(r"^[A-Za-z0-9_.-]+\.txt$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CouldNotVerify(Exception):
    """The manifest cannot be read as a manifest. Exit 2, never 1."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _no_duplicate_keys(pairs):
    # json.loads keeps the LAST of a repeated key. Two entries for one prompt
    # is a manifest that says two things; refuse to pick one silently.
    out: dict = {}
    for k, v in pairs:
        if k in out:
            raise CouldNotVerify(f"duplicate manifest entry for {k!r}")
        out[k] = v
    return out


def load_manifest(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise CouldNotVerify(f"{path} does not exist")
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CouldNotVerify(f"{path} is not valid JSON ({exc})")
    if not isinstance(data, dict):
        raise CouldNotVerify(f"{path} must be an object mapping filename -> sha256, "
                             f"got {type(data).__name__}")
    for name, digest in data.items():
        if not _NAME.match(name):
            raise CouldNotVerify(f"manifest key {name!r} is not a bare *.txt filename")
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise CouldNotVerify(f"manifest value for {name} is not a lowercase "
                                 f"64-hex sha256 digest")
    return data


def prompt_files(directory: Path) -> dict[str, Path]:
    return {p.name: p for p in sorted(directory.glob("*.txt")) if p.is_file()}


def update(directory: Path) -> int:
    files = prompt_files(directory)
    if not files:
        print(f"could not update -- no *.txt files in {directory}")
        return 2
    fresh = {name: _sha256(p) for name, p in files.items()}
    try:
        old = load_manifest(directory / MANIFEST_NAME)
    except CouldNotVerify:
        old = {}
    (directory / MANIFEST_NAME).write_text(
        json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    changed = sorted(n for n in fresh if old.get(n) != fresh[n])
    dropped = sorted(set(old) - set(fresh))
    print(f"wrote {directory / MANIFEST_NAME} -- {len(fresh)} entries")
    for n in changed:
        print(f"  {'added  ' if n not in old else 'changed'} {n}")
    for n in dropped:
        print(f"  removed {n}")
    if not changed and not dropped:
        print("  (no change)")
    return 0


def check(directory: Path) -> int:
    if not directory.is_dir():
        print(f"COULD NOT VERIFY -- {directory} is not a directory")
        return 2
    try:
        manifest = load_manifest(directory / MANIFEST_NAME)
    except CouldNotVerify as exc:
        print(f"COULD NOT VERIFY -- {exc}.\n"
              f"  The manifest is part of the commit. Restore it, or regenerate with:\n"
              f"      {UPDATE_CMD}")
        return 2
    files = prompt_files(directory)
    if not files:
        print(f"COULD NOT VERIFY -- no *.txt files in {directory}; "
              f"a prompts directory with no prompts is not a pass")
        return 2

    problems: list[str] = []
    for name in sorted(files):
        if name not in manifest:
            problems.append(f"{name}: present on disk but not listed in {MANIFEST_NAME} "
                            f"(a new prompt must be declared)")
        elif _sha256(files[name]) != manifest[name]:
            problems.append(f"{name}: CONTENT CHANGED -- sha256 {_sha256(files[name])[:12]}... "
                            f"does not match the manifest's {manifest[name][:12]}...")
    for name in sorted(set(manifest) - set(files)):
        problems.append(f"{name}: listed in {MANIFEST_NAME} but missing from disk")

    print(f"prompt manifest -- {len(files)} prompt file(s), {len(manifest)} manifest entr"
          f"{'y' if len(manifest) == 1 else 'ies'}")
    if problems:
        print(f"\nFAIL -- {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        print("\nThese files are the system prompt of every LLM request. If the change is\n"
              "intended, update the manifest IN THE SAME COMMIT:\n"
              f"      {UPDATE_CMD}")
        return 1
    print(f"PASS ({len(files)} prompts match the committed hashes)")
    return 0


def main(argv: list[str]) -> int:
    directory = DEFAULT_DIR
    do_update = False
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--update":
            do_update = True
        elif a == "--dir" and args:
            directory = Path(args.pop(0))
        else:
            print(f"usage: verify_prompt_manifest.py [--update] [--dir PATH]  (got {a!r})")
            return 2
    return update(directory) if do_update else check(directory)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
