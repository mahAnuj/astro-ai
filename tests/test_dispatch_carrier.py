"""The carrier that turns a recorded ruling into an `agent-work` cycle (#442).

WHY THIS FILE EXISTS
--------------------
An agent inside `claude-code-action` holds the Claude GitHub App token, and
`gh workflow run` answers it HTTP 403. So `steward.md` spent its whole life
telling the steward to do something its credential cannot do, in six routing
rows, and the only working dispatch path was chief's -- which made chief the
dispatcher for every mechanical repair.

`scripts/dispatch_cycle.sh` is now that path for BOTH roles. It is one script
rather than two copies because this repository's most reliable defect is a
copied file diverging: `id-token: write` was missing from four agent loops that
had each been copied from a fifth.

These tests drive the real script through a FAKE `gh` on PATH, so every guard is
exercised with no network and no Actions minutes. The guards are the point: the
script refuses a lenient parse, a closed issue and a second concurrent cycle,
and it refuses to report a dispatch whose run died on arrival (#421, which hid
for three days behind `gh workflow run` exiting 0).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dispatch_cycle.sh"


def _fake_gh(tmp_path: Path, *, state="OPEN", busy=0, runs=("11", "22"),
             status_seq=("in_progress",), pr_state=None, issue_url=None) -> Path:
    """A `gh` that answers only what the script asks, from shell case matching.

    `issue view` and `pr view` are answered SEPARATELY because the script must
    not use one for the other: GitHub shares one number space and
    `gh issue view <pr>` answers for a pull request, so a fake that conflated
    them could not detect the bug the separation exists to prevent
    (#638's number, which is a merged PR).

    `--json url` is matched BEFORE `--json state`, because the script asks for
    both on an `issue=` ruling and the url answer is what distinguishes an
    issue from a PR wearing an issue's number.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
case "$*" in
  *"issue view"*"--json url"*) echo '{issue_url or "https://github.com/owner/repo/issues/1"}' ;;
  *"pr view"*)            echo '{pr_state or state}' ;;
  *"issue view"*)         echo '{state}' ;;
  *"--json status --jq"*'select(.status != "completed")'*) echo '{busy}' ;;
  *"--limit 1 --json databaseId"*)
      if [ -f "{tmp_path}/dispatched" ]; then echo '{runs[1]}'; else echo '{runs[0]}'; fi ;;
  *"workflow run"*)       : > "{tmp_path}/dispatched"; echo 'dispatched' ;;
  *"run view"*)           echo '{status_seq[0]} ' ;;
  *) echo "UNEXPECTED gh $*" >&2; exit 9 ;;
esac
""")
    gh.chmod(0o755)
    # A NO-OP `sleep` ON PATH. The script's two verification loops sleep 5s up
    # to 12 and 18 times (#421's liveness checks), so a non-dry test would take
    # ~90s of wall clock doing nothing. Shimming `sleep` exercises the REAL
    # loops at full iteration count in milliseconds -- the alternative was to
    # assert on the script's source text, which would not have run them at all.
    (bindir / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n")
    (bindir / "sleep").chmod(0o755)
    return bindir


def _run(tmp_path: Path, contents: str | None, *, who="steward", dry=True, **kw):  # noqa: D103
    f = tmp_path / "ruling.txt"
    if contents is not None:
        f.write_text(contents)
    env = dict(os.environ)
    env["PATH"] = f"{_fake_gh(tmp_path, **kw)}:{env['PATH']}"
    env["GH_REPO"] = "owner/repo"
    env.pop("GITHUB_ENV", None)
    cmd = ["bash", str(SCRIPT), str(f), who] + (["--dry-run"] if dry else [])
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)


def test_no_ruling_is_a_ruling_not_a_failure(tmp_path):
    """The common case. A steward that found nothing dispatchable must exit 0,
    or every quiet run would read as a broken carrier."""
    r = _run(tmp_path, None)
    assert r.returncode == 0, r.stderr
    assert "recorded no dispatch" in r.stdout


def test_an_empty_file_is_also_no_ruling(tmp_path):
    r = _run(tmp_path, "")
    assert r.returncode == 0
    assert "recorded no dispatch" in r.stdout


@pytest.mark.parametrize("line", [
    "dispatch issue 409 please",
    "issue=409 and also issue=410",
    "issue=abc",
    "409",
    "ISSUE=409",
])
def test_anything_but_issue_equals_digits_is_refused(tmp_path, line):
    """A LENIENT PARSER HERE DISPATCHES AT THE WRONG ISSUE, which is ~50 Actions
    minutes on work nobody ruled on. `issue=409 and also issue=410` is the one
    that matters: a greedy match would take 409 and silently drop the rest."""
    r = _run(tmp_path, line)
    assert r.returncode == 1, r.stdout
    assert "unparseable" in r.stdout


def test_a_closed_issue_is_refused(tmp_path):
    """A cycle at a closed issue is the `cannot-reproduce` path at full cost."""
    r = _run(tmp_path, "issue=409", state="CLOSED")
    assert r.returncode == 1
    assert "CLOSED" in r.stdout


def test_a_cycle_already_in_flight_defers_rather_than_queueing(tmp_path):
    r = _run(tmp_path, "issue=409", busy=1)
    assert r.returncode == 0, r.stdout
    assert "in flight" in r.stdout
    assert "waits for the next run" in r.stdout


def test_an_unreadable_concurrency_check_counts_as_busy(tmp_path):
    """Guessing "not busy" is what spends the quota twice."""
    r = _run(tmp_path, "issue=409", busy="unknown")
    assert r.returncode == 0
    assert "in flight" in r.stdout


def test_the_ruling_names_whoever_recorded_it(tmp_path):
    """Both roles share this script, so the message may not hardcode `chief` --
    the report step attributes the dispatch from it."""
    r = _run(tmp_path, "issue=409", who="steward")
    assert "steward" in r.stdout and "chief" not in r.stdout


def test_a_missing_gh_repo_exits_2_as_documented(tmp_path):
    """Exit 2 is "wired wrong", exit 1 is "a ruling could not be carried out".
    The caller routes on the difference, so a documented code that lies is a
    defect. `${GH_REPO:?}` exited 1 here and that is why the guard is explicit."""
    f = tmp_path / "r.txt"
    f.write_text("issue=409")
    env = dict(os.environ)
    env["PATH"] = f"{_fake_gh(tmp_path)}:{env['PATH']}"
    env.pop("GH_REPO", None)
    r = subprocess.run(["bash", str(SCRIPT), str(f), "steward", "--dry-run"],
                       capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)


def test_no_arguments_exits_2(tmp_path):
    r = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 2


def test_a_dry_run_never_dispatches(tmp_path):
    """The flag exists so these guards can be exercised for real. If it leaked
    into a dispatch, the test suite would spend Actions minutes."""
    r = _run(tmp_path, "issue=409", dry=True)
    assert r.returncode == 0
    assert "DRY RUN" in r.stdout
    assert not (tmp_path / "dispatched").exists()

# ---------------------------------------- the second ruling form (#639, #647)
#
# A QA ROUND NEEDS A PR, NOT AN ISSUE. `qa-on-green` could only aim a round at
# an issue number read out of the branch name, so a green PR on a branch
# carrying no number was never dispatched at all -- and `agent-merge` will not
# merge without `qa-pass`. Measured: #639 (`feat/ops-watcher-detector`) and #647
# (`fix/mutation-row-floor-total`) both had ZERO dispatches while green.

def test_a_pr_ruling_dispatches_at_the_pr(tmp_path):
    r = _run(tmp_path, "pr=647\n")
    assert r.returncode == 0, r.stderr
    assert "would dispatch agent-work at pr #647" in r.stdout


def test_a_pr_ruling_is_checked_with_pr_view_and_NOT_issue_view(tmp_path):
    """THE NUMBER-SPACE TRAP, executed.

    `gh issue view <pr>` answers for a pull request, so a carrier that reached
    for `issue view` on a `pr=` ruling would read the wrong object's state. Here
    `issue view` says OPEN and `pr view` says MERGED: the carrier must refuse.
    This is #647's own measurement turned into a test -- scraping its body
    yields `638`, a MERGED pull request.
    """
    r = _run(tmp_path, "pr=638\n", state="OPEN", pr_state="MERGED")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "pr #638, which is MERGED" in r.stderr + r.stdout


def test_an_issue_ruling_that_names_a_PULL_REQUEST_is_refused(tmp_path):
    """The same overlap from the other side, and it was LATENT before this change.

    `issue=638` passed the openness check whenever PR #638 happened to be open,
    because `gh issue view` answers for a PR. Adding a `pr=` form makes that
    newly reachable, so the `issue=` arm now checks the url too.
    """
    r = _run(tmp_path, "issue=638\n",
             issue_url="https://github.com/owner/repo/pull/638")
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert "is a PULL REQUEST" in out
    assert "Rule `pr=638`" in out, "the refusal does not say what to rule instead"


@pytest.mark.parametrize("line,why", [
    ("pr=647 issue=1\n", "two keys on one line"),
    ("prr=647\n", "a near-miss key"),
    ("pr=\n", "no digits"),
    ("pr=abc\n", "non-digits"),
    ("pr=-1\n", "a negative"),
    ("PR=647\n", "wrong case"),
    ("pull=647\n", "a plausible synonym"),
    ("pr=647extra\n", "trailing text"),
])
def test_the_strict_parse_still_refuses_everything_else(line, why, tmp_path):
    """`tr -d '[:space:]'` collapses the line, so `pr=647 issue=1` becomes one
    token matching neither anchored pattern. Exactly one key, exactly digits."""
    r = _run(tmp_path, line)
    assert r.returncode == 1, f"{why} was accepted:\n{r.stdout}"
    assert "unparseable dispatch line" in r.stdout + r.stderr


def test_the_issue_form_is_unchanged(tmp_path):
    """The path that works today, pinned explicitly rather than inferred from
    the other cases staying green."""
    r = _run(tmp_path, "issue=536\n")
    assert r.returncode == 0, r.stderr
    assert "would dispatch agent-work at issue #536" in r.stdout


def test_a_closed_pr_is_refused(tmp_path):
    r = _run(tmp_path, "pr=640\n", pr_state="CLOSED")
    assert r.returncode == 1, r.stdout
    assert "pr #640, which is CLOSED" in r.stdout + r.stderr


def test_an_unreadable_pr_is_refused_not_guessed(tmp_path):
    """MISSING is the fallback when the API call fails, and it is not OPEN."""
    r = _run(tmp_path, "pr=99999\n", pr_state="MISSING")
    assert r.returncode == 1, r.stdout
    assert "MISSING" in r.stdout + r.stderr


def test_the_real_dispatch_composes_the_key_it_was_given(tmp_path):
    """`-f "$kind=$target"`, not a hardcoded `-f issue=`.

    A hardcoded key would silently dispatch a `pr=` ruling as an issue number,
    and because the number spaces overlap the cycle would then work whatever
    issue happens to carry that number -- a ~50-minute cycle on work nobody
    ruled on, which is the failure the strict parse exists to prevent.
    """
    calls = tmp_path / "calls"
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    (bindir / "gh").write_text(f"""#!/usr/bin/env bash
case "$*" in
  *"issue view"*"--json url"*) echo 'https://github.com/owner/repo/issues/1' ;;
  *"pr view"*)            echo 'OPEN' ;;
  *"issue view"*)         echo 'OPEN' ;;
  *"--json status --jq"*) echo '0' ;;
  *"--limit 1 --json databaseId"*)
      if [ -f "{tmp_path}/d" ]; then echo '22'; else echo '11'; fi ;;
  *"workflow run"*)       echo "gh $*" >> "{calls}"; : > "{tmp_path}/d" ;;
  *"run view"*)           echo 'in_progress ' ;;
  *) echo "UNEXPECTED gh $*" >&2; exit 9 ;;
esac
""")
    (bindir / "gh").chmod(0o755)
    (bindir / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n")
    (bindir / "sleep").chmod(0o755)
    f = tmp_path / "ruling.txt"
    f.write_text("pr=647\n")
    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["GH_REPO"] = "owner/repo"
    env.pop("GITHUB_ENV", None)
    subprocess.run(["bash", str(SCRIPT), str(f), "qa-on-green"],
                   capture_output=True, text=True, env=env, timeout=300)
    recorded = calls.read_text() if calls.exists() else ""
    assert "-f pr=647" in recorded, f"dispatched with the wrong key: {recorded!r}"
    assert "-f issue=" not in recorded


def test_the_dispatched_kind_is_exported_beside_the_number(tmp_path):
    """`DISPATCHED` keeps its name and value -- `agent-steward.yml` reads it --
    and `DISPATCHED_KIND` is added so a reader can tell a QA round from a
    delivery cycle without re-deriving it."""
    genv = tmp_path / "github_env"
    genv.write_text("")
    f = tmp_path / "ruling.txt"
    f.write_text("pr=647\n")
    env = dict(os.environ)
    env["PATH"] = f"{_fake_gh(tmp_path)}:{env['PATH']}"
    env["GH_REPO"] = "owner/repo"
    env["GITHUB_ENV"] = str(genv)
    subprocess.run(["bash", str(SCRIPT), str(f), "qa-on-green"],
                   capture_output=True, text=True, env=env, timeout=300)
    written = genv.read_text()
    assert "DISPATCHED=647" in written
    assert "DISPATCHED_KIND=pr" in written


def test_the_header_documents_both_forms_and_why_the_body_is_never_read():
    """A decision nobody can find is a decision that gets undone.

    The next reader must meet the measurement -- #647's body yields a merged
    pull request -- in the file, or the cheap body-scraping alternative gets
    re-proposed.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    assert "issue=<digits>" in src and "pr=<digits>" in src
    assert "NEVER SCRAPED FROM A PR BODY" in src
    assert "BOTH OF WHICH ARE PULL REQUESTS" in src, (
        "the file does not record the measurement that disqualified body scraping")


def test_the_cycle_doc_carries_the_qa_round_mode():
    """The carrier can emit `pr=` the moment this lands, and `agent-work.yml`
    will pass it through as `--qa-pr <n>` once PR C lands. If the cycle doc does
    not describe that mode, a dispatched round reads the token as noise and
    works an issue instead -- so the token and the doc are pinned together.

    `CLAUDE.md` records that this exact coupling once lived in six places:
    "When a rule is restated in prose for agents to read, grep for every copy
    before believing a fix is done."
    """
    doc = (Path(__file__).resolve().parents[1]
           / ".claude" / "commands" / "agent-cycle.md").read_text(encoding="utf-8")
    assert "--qa-pr" in doc, "agent-cycle.md does not describe the QA-round mode"
    assert "isCrossRepository" in doc, (
        "the mode does not refuse a fork PR -- a cycle reading an outsider's "
        "diff with write credentials is #361 wearing a pull request's clothes")
    assert "NEVER read the owning issue out of the PR body" in doc
    assert "qa:independent" in doc, (
        "the mode does not say which provenance it claims, and the wider claim "
        "would make chief's Shape C hold loop-satisfiable")
