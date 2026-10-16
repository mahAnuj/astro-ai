"""Prompt manifest gate (#362): every test is a way a system-prompt change could go unseen.

WHY THESE EXIST. `src/astro_ai/prompts/*.txt` is the system prompt of every LLM request and
nothing gated its content. `scripts/verify_prompt_manifest.py` compares each file's sha256
with the committed `MANIFEST.json`. These tests run THAT SCRIPT, as a subprocess so the exit
codes are the real ones, against a temp copy of the real prompts directory -- they do not
reimplement its logic, which is how a test passes forever against a gate that cannot fail.
The `#362` rows of `scripts/mutate_behaviour_suite.py` re-break each clause to prove it.

Hermetic: stdlib only, no network, the repo's own prompts are copied and never modified.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "scripts" / "verify_prompt_manifest.py"
REAL_PROMPTS = ROOT / "src" / "astro_ai" / "prompts"
UPDATE_CMD = "scripts/verify_prompt_manifest.py --update"


def _run(directory: Path, *flags: str):
    return subprocess.run([sys.executable, str(GATE), "--dir", str(directory), *flags],
                          capture_output=True, text=True)


@pytest.fixture
def prompts(tmp_path):
    """A temp copy of the real prompts with a freshly generated manifest."""
    d = tmp_path / "prompts"
    d.mkdir()
    for f in REAL_PROMPTS.glob("*.txt"):
        shutil.copy(f, d / f.name)
    assert _run(d, "--update").returncode == 0
    return d


REAL_NAMES = sorted(p.name for p in REAL_PROMPTS.glob("*.txt"))


def test_there_are_real_prompts_to_protect():
    # Parametrising over an empty list would pass vacuously.
    assert len(REAL_NAMES) >= 11


def test_a_clean_copy_passes(prompts):
    r = _run(prompts)
    assert r.returncode == 0, r.stdout + r.stderr


def test_update_writes_the_sha256_of_the_raw_bytes(prompts):
    manifest = json.loads((prompts / "MANIFEST.json").read_text())
    assert sorted(manifest) == REAL_NAMES
    for name in REAL_NAMES:       # independent oracle: hashlib on bytes, not the gate's code
        assert manifest[name] == hashlib.sha256((prompts / name).read_bytes()).hexdigest()


@pytest.mark.parametrize("name", REAL_NAMES)
def test_a_one_character_change_to_any_prompt_fails_and_names_the_file(prompts, name):
    p = prompts / name
    p.write_bytes(p.read_bytes() + b"x")
    r = _run(prompts)
    assert r.returncode == 1, r.stdout + r.stderr
    assert name in r.stdout
    assert UPDATE_CMD in r.stdout          # the failure says how to fix it
    others = [n for n in REAL_NAMES if n != name]
    assert not any(f"- {n}:" in r.stdout for n in others)   # and names ONLY the changed one


def test_updating_the_manifest_in_the_same_commit_passes(prompts):
    p = prompts / "natal.txt"
    p.write_bytes(p.read_bytes() + b"x")
    assert _run(prompts).returncode == 1
    assert _run(prompts, "--update").returncode == 0
    assert _run(prompts).returncode == 0


def test_update_is_never_the_default(prompts):
    # A bare run that regenerated its own expectations would pass on anything.
    before = (prompts / "MANIFEST.json").read_bytes()
    p = prompts / "daily.txt"
    p.write_bytes(p.read_bytes() + b"x")
    assert _run(prompts).returncode == 1
    assert (prompts / "MANIFEST.json").read_bytes() == before


def test_an_unlisted_prompt_on_disk_fails_and_names_it(prompts):
    (prompts / "brand_new.txt").write_text("a new system prompt\n")
    r = _run(prompts)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "brand_new.txt" in r.stdout and "not listed" in r.stdout


def test_a_listed_prompt_missing_from_disk_fails_and_names_it(prompts):
    (prompts / "yearly.txt").unlink()
    r = _run(prompts)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "yearly.txt" in r.stdout and "missing from disk" in r.stdout


def test_line_endings_are_part_of_the_hash(prompts):
    # Raw bytes, so a CRLF checkout is a change rather than a silent re-hash.
    p = prompts / "matching.txt"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    r = _run(prompts)
    assert r.returncode == 1 and "matching.txt" in r.stdout


def test_a_missing_manifest_is_could_not_verify_not_fail(prompts):
    (prompts / "MANIFEST.json").unlink()
    r = _run(prompts)
    assert r.returncode == 2, r.stdout + r.stderr


@pytest.mark.parametrize("body", [
    "{ this is not json",                                   # unparseable
    "",                                                     # empty file
    "[]",                                                   # wrong shape: not an object
    json.dumps({"natal.txt": 123}),                         # value not a string
    json.dumps({"natal.txt": "abc123"}),                    # not a 64-hex digest
    json.dumps({"natal.txt": "A" * 64}),                    # upper-case is not the committed form
    json.dumps({"../escape.txt": "0" * 64}),                # key is not a bare filename
    '{"natal.txt": "%s", "natal.txt": "%s"}' % ("0" * 64, "1" * 64),   # duplicate entry
], ids=["bad-json", "empty", "list", "int-value", "short-digest", "upper-digest",
        "path-key", "duplicate-key"])
def test_an_unusable_manifest_exits_two(prompts, body):
    (prompts / "MANIFEST.json").write_text(body)
    r = _run(prompts)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Traceback" not in r.stderr          # refused deliberately, not crashed into


def test_a_directory_with_no_prompts_is_not_a_pass(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    (d / "MANIFEST.json").write_text("{}")
    assert _run(d).returncode == 2


def test_the_gate_runs_with_no_arguments_the_way_pr_gates_runs_it():
    r = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
