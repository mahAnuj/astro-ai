"""#446 AC3: a declared `Test-Count-Drop:` is honoured only with a SHA-bound ruling.

Before this, the trailer alone passed `verify_test_floor.py`, so on the
unattended path the author of a PR could lower the floor by typing a line in
their own commit. The gate now needs a comment on the PR, by `claude[bot]` or the
repository owner, containing `test-count-drop-ruled at <full head sha>`.

These drive the REAL gate (copied into a real temporary git repo, as
test_test_floor_gate.py does) in-process, with the comment lookup injected as
`main(fetch=...)`. There is deliberately no env var or file that overrides the
lookup in the gate itself: that would be the bypass this closes.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[1] / "scripts" / "verify_test_floor.py"
REPO = "owner1/proj"
OWNER = "owner1"


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(("git", "-C", str(repo), *args), capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, f"git {' '.join(args)}: {out.stderr}"
    return out.stdout


@pytest.fixture
def gate(tmp_path: Path):
    """The gate module loaded from a temp repo whose branch deleted a test and
    declared it, so ROOT (derived from __file__) is that repo."""
    origin = tmp_path / "origin"
    (origin / "tests").mkdir(parents=True)
    (origin / "scripts").mkdir()
    (origin / "scripts" / "verify_test_floor.py").write_text(GATE.read_text())
    (origin / "tests" / "test_a.py").write_text("def test_one():\n    pass\n\n\ndef test_two():\n    pass\n")
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
    (clone / "tests" / "test_a.py").write_text("def test_one():\n    pass\n")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "drop\n\nTest-Count-Drop: duplicate of test_one")
    spec = importlib.util.spec_from_file_location("floor_under_test", clone / "scripts" / "verify_test_floor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CLONE = clone
    mod.HEAD = _git(clone, "rev-parse", "HEAD").strip()
    return mod


def _comment(login: str, body: str, cid: int = 1) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body}


class Fetch:
    """Records calls; returns canned comments or raises."""

    def __init__(self, comments=(), error: Exception | None = None):
        self.comments, self.error, self.calls = list(comments), error, []

    def __call__(self, repo, sha, pr):
        self.calls.append((repo, sha, pr))
        if self.error:
            raise self.error
        return self.comments


def _env(**kw) -> dict:
    return {"GITHUB_REPOSITORY": REPO, **kw}


def _ruling(sha: str) -> str:
    return f"Ruled after reading the deleted test.\n\ntest-count-drop-ruled at {sha}"


def test_a_ruling_by_claude_bot_passes(gate, capsys):
    f = Fetch([_comment("claude[bot]", _ruling(gate.HEAD), 77)])
    assert gate.main(fetch=f, env=_env()) == 0
    out = capsys.readouterr().out
    assert "duplicate of test_one" in out and "claude[bot]" in out and "77" in out


def test_a_ruling_by_the_repository_owner_passes(gate):
    assert gate.main(fetch=Fetch([_comment(OWNER, _ruling(gate.HEAD))]), env=_env()) == 0


def test_a_ruling_by_anyone_else_fails(gate, capsys):
    """The PR author is exactly who must not be able to authorise their own drop."""
    f = Fetch([_comment("some-contributor", _ruling(gate.HEAD)),
               _comment("claude-bot-lookalike", _ruling(gate.HEAD))])
    assert gate.main(fetch=f, env=_env()) == 1
    assert f"test-count-drop-ruled at {gate.HEAD}" in capsys.readouterr().out


def test_a_ruling_for_another_sha_fails(gate):
    old = "0123456789abcdef0123456789abcdef01234567"
    assert gate.main(fetch=Fetch([_comment("claude[bot]", _ruling(old))]), env=_env()) == 1


def test_a_short_sha_does_not_count(gate):
    assert gate.main(fetch=Fetch([_comment("claude[bot]", _ruling(gate.HEAD[:7]))]), env=_env()) == 1
    assert gate.main(fetch=Fetch([_comment("claude[bot]", _ruling(gate.HEAD[:39]))]), env=_env()) == 1


def test_a_longer_hex_string_starting_with_the_sha_does_not_count(gate):
    assert gate.main(fetch=Fetch([_comment("claude[bot]", _ruling(gate.HEAD + "ab"))]), env=_env()) == 1


def test_no_comments_fails(gate):
    assert gate.main(fetch=Fetch([]), env=_env()) == 1


def test_an_api_error_is_exit_2_not_a_pass(gate, capsys):
    f = Fetch(error=RuntimeError("HTTP Error 403: rate limit exceeded"))
    assert gate.main(fetch=f, env=_env()) == 2
    assert "NOT a pass" in capsys.readouterr().out


def test_no_repository_is_exit_2(gate):
    f = Fetch([_comment("claude[bot]", _ruling(gate.HEAD))])
    assert gate.main(fetch=f, env={}) == 2
    assert f.calls == [], "with no repo there is nothing to ask"


def test_a_trailer_with_nothing_removed_never_touches_the_network(gate):
    """The common path stays network-free: a declaration on a PR that deleted
    nothing must not cost an API call."""
    clone = gate.CLONE
    (clone / "tests" / "test_a.py").write_text(
        "def test_one():\n    pass\n\n\ndef test_two():\n    pass\n")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "restore\n\nTest-Count-Drop: no longer needed")
    f = Fetch(error=RuntimeError("must not be called"))
    assert gate.main(fetch=f, env=_env()) == 0
    assert f.calls == []


def test_the_head_sha_comes_from_the_event_payload_not_from_HEAD(gate, tmp_path):
    """On a pull_request run HEAD is the refs/pull/N/merge commit. A ruling that
    names it is a ruling nobody could have written; the PR head is what counts."""
    pr_head = "a" * 40
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 9, "head": {"sha": pr_head}}}))
    env = _env(GITHUB_EVENT_PATH=str(event))

    f = Fetch([_comment("claude[bot]", _ruling(pr_head))])
    assert gate.main(fetch=f, env=env) == 0
    assert f.calls == [(REPO, pr_head, 9)]

    assert gate.main(fetch=Fetch([_comment("claude[bot]", _ruling(gate.HEAD))]), env=env) == 1


def test_an_unreadable_event_file_is_exit_2(gate, tmp_path):
    bad = tmp_path / "event.json"
    bad.write_text("not json")
    assert gate.main(fetch=Fetch([]), env=_env(GITHUB_EVENT_PATH=str(bad))) == 2


def test_the_gate_has_no_override_for_the_lookup():
    """An env var or file the gate reads to replace the comment lookup would be
    a bypass on a path where the author controls neither but the loop does."""
    src = GATE.read_text()
    assert "fetch: Fetch = fetch_comments" in src
    for forbidden in ("TEST_DROP_RULING", "TEST_COUNT_DROP_RULING", "RULING_FILE", "SKIP_RULING"):
        assert forbidden not in src


def test_a_quoted_phrase_is_a_mention_not_a_ruling(gate):
    """#747, 2026-11-07: the author's note, posted as the owner, quoted the phrase in
    backticks to say it was NOT ruling, and the gate went green on it."""
    note = (f"Since #753 a declared drop needs a ruling comment containing "
            f"`test-count-drop-ruled at {gate.HEAD}` from chief or the owner. "
            f"As the author I am not posting it.")
    quoted = f"Chief wrote:\n> test-count-drop-ruled at {gate.HEAD}"
    for body in (note, quoted):
        assert gate.main(fetch=Fetch([_comment(OWNER, body)]), env=_env()) == 1, body


def test_the_phrase_on_its_own_line_is_a_ruling_even_with_a_full_stop(gate):
    body = f"Read both deleted tests; obsolete subject.\n\ntest-count-drop-ruled at {gate.HEAD}."
    assert gate.main(fetch=Fetch([_comment("claude[bot]", body)]), env=_env()) == 0
