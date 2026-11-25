"""`qa_verdict.sh` posts the verdict comment BEFORE any label, and binds a full SHA (#1285).

WHY THIS FILE EXISTS

`tests/test_qa_verdict_mode.py` drives the script with `--dry-run`, so it never
reaches a write and cannot see the ORDER of the writes. The script used to edit
the labels, then un-draft, then comment. `qa-pass` is the sole merge trigger and
`agent-merge` binds it to a comment naming the FULL head sha, so:

  1. the `labeled` edge could start `agent-merge` with no verdict comment yet,
     and a failed comment post left a label nothing bound -- the shape the
     owner's rule ("the comment comes first, then the label") forbids;
  2. `--sha 35589700` passed the prefix check but was written to the comment
     verbatim, so `agent-merge`'s full-sha match never bound it and a passed PR
     stalled silently.

Here a real subprocess runs the real script against a `gh` stub that LOGS every
write in order, so the order is read from what was called and not from the text
of the script. The stub exits 9 on any call it does not know, so a new `gh`
call in the script is a loud failure rather than a silent pass.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "qa_verdict.sh"

HEAD = "bf2b17d4e7c1a09d3f6b5e8a2c4d1f0e9b8a7c6d"
OLDER = "0123456789abcdef0123456789abcdef01234567"

# The same reader `detect_stalls.py` applies to the first line of a verdict
# comment; copied here (not imported) because a changed pattern there should
# fail loudly in its own tests, and this file only needs the shape.
_VERDICT_LINE = re.compile(r"^QA: (PASS|FAIL) — verified at `?([0-9a-f]{7,40})`?")

WRITES = ("pr comment", "pr ready", "pr edit", "issue edit")


def _gh_stub(bindir: Path) -> None:
    """A `gh` that answers the script's reads and LOGS its writes, in order.

    Behaviour is steered by env vars, so one stub serves every case:
      GH_LOG       file a line per write is appended to ("<verb> <args...>")
      GH_BODY      file the `pr comment --body` text is written to
      GH_FAIL      a write ("pr comment", "pr edit", ...) that must exit 1
      PR_LABELS / ISSUE_LABELS   comma-joined labels the reads report
      IS_DRAFT     `true` / `false`
    """
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
verb="$1 $2"
case "$*" in
  *"--json headRefName"*) echo 'issue/1285-a-slug'; exit 0 ;;
  *"--json headRefOid"*)  echo '{HEAD}'; exit 0 ;;
  *"--json isDraft"*)     echo "${{IS_DRAFT:-false}}"; exit 0 ;;
  *"--json labels"*)
    if [ "$1" = issue ]; then echo "${{ISSUE_LABELS:-}}"; else echo "${{PR_LABELS:-}}"; fi
    exit 0 ;;
esac
case "$verb" in
  "pr comment"|"pr ready"|"pr edit"|"issue edit")
    echo "$*" >> "$GH_LOG"
    if [ "$verb" = "pr comment" ]; then
      while [ $# -gt 0 ]; do
        if [ "$1" = --body ]; then printf '%s' "$2" > "$GH_BODY"; fi
        shift
      done
    fi
    [ "${{GH_FAIL:-}}" = "$verb" ] && {{ echo "stub: $verb failing" >&2; exit 1; }}
    exit 0 ;;
esac
echo "UNEXPECTED gh $*" >&2
exit 9
""")
    gh.chmod(0o755)


def _run(tmp_path: Path, *args, verdict="PASS", env_extra=None, script=None):
    """Run the real script (not `--dry-run`) and return (result, calls, body)."""
    bindir = tmp_path / "bin"
    _gh_stub(bindir)
    log, bodyf = tmp_path / "gh.log", tmp_path / "body.txt"
    log.write_text("")
    env = dict(os.environ)
    # The suite may run inside Actions; the result must not depend on where.
    for k in ("GITHUB_ACTIONS", "GITHUB_RUN_ID", "CI"):
        env.pop(k, None)
    env.update(PATH=f"{bindir}:{env['PATH']}", GH_REPO="owner/repo",
               GH_LOG=str(log), GH_BODY=str(bodyf), PR_LABELS="", ISSUE_LABELS="",
               IS_DRAFT="false")
    env.update(env_extra or {})
    cmd = ["bash", str(script or SCRIPT), "--pr", "536", "--verdict", verdict, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    calls = [ln for ln in log.read_text().splitlines() if ln]
    body = bodyf.read_text() if bodyf.exists() else ""
    return r, calls, body


def _idx(calls, verb):
    return [i for i, c in enumerate(calls) if c.startswith(verb)]


# ------------------------------------------------------------- write order

def test_the_comment_is_posted_before_any_label_write(tmp_path):
    r, calls, _ = _run(tmp_path, "--sha", HEAD, env_extra={"IS_DRAFT": "true"})
    assert r.returncode == 0, r.stdout + r.stderr
    comment, ready = _idx(calls, "pr comment"), _idx(calls, "pr ready")
    pr_edit, issue_edit = _idx(calls, "pr edit"), _idx(calls, "issue edit")
    assert comment and ready and pr_edit and issue_edit, calls
    assert comment[0] < ready[0] < pr_edit[0], calls
    assert comment[0] < issue_edit[0], calls
    # the label is the LAST write: it is what starts agent-merge
    assert max(comment + ready) < min(pr_edit + issue_edit), calls


def test_a_fail_comment_precedes_labels_and_a_draft_is_not_readied(tmp_path):
    r, calls, _ = _run(tmp_path, "--sha", HEAD, verdict="FAIL",
                       env_extra={"IS_DRAFT": "true"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert not _idx(calls, "pr ready"), f"a FAIL readied the draft: {calls}"
    comment = _idx(calls, "pr comment")
    labels = _idx(calls, "pr edit") + _idx(calls, "issue edit")
    assert comment and labels and comment[0] < min(labels), calls


# --------------------------------------------------------- the bound sha

def test_an_abbreviated_sha_is_written_as_the_full_head(tmp_path):
    r, _, body = _run(tmp_path, "--sha", HEAD[:7])
    assert r.returncode == 0, r.stdout + r.stderr
    first = body.splitlines()[0]
    assert first == f"QA: PASS — verified at `{HEAD}`", first
    # what detect_stalls reads, and what agent-merge's `contains` needs
    m = _VERDICT_LINE.match(first)
    assert m and m.group(2) == HEAD, first
    assert HEAD in body


def test_an_omitted_sha_is_written_as_the_head(tmp_path):
    r, _, body = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert body.splitlines()[0] == f"QA: PASS — verified at `{HEAD}`"


def test_a_fail_with_an_abbreviated_prefix_sha_is_also_expanded(tmp_path):
    r, _, body = _run(tmp_path, "--sha", HEAD[:12], verdict="FAIL")
    assert r.returncode == 0, r.stdout + r.stderr
    assert body.splitlines()[0] == f"QA: FAIL — verified at `{HEAD}`"


def test_a_fail_naming_a_different_commit_keeps_it_verbatim(tmp_path):
    """QA examined an older commit and the branch moved: that is what was seen."""
    r, _, body = _run(tmp_path, "--sha", OLDER[:10], verdict="FAIL")
    assert r.returncode == 0, r.stdout + r.stderr
    assert body.splitlines()[0] == f"QA: FAIL — verified at `{OLDER[:10]}`"
    assert HEAD not in body


def test_a_pass_on_a_moved_branch_is_still_refused_and_writes_nothing(tmp_path):
    r, calls, _ = _run(tmp_path, "--sha", OLDER)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "REFUSED" in r.stderr
    assert calls == [], calls


def test_a_too_short_or_non_hex_sha_is_bad_usage_and_writes_nothing(tmp_path):
    for bad in ("b", "bf2b1", "bf2b17z", "bf2b17d\nQA: PASS"):
        r, calls, _ = _run(tmp_path, "--sha", bad)
        assert r.returncode == 2, (bad, r.stdout, r.stderr)
        assert calls == [], (bad, calls)


# ------------------------------------------------------------- failures

def test_a_failed_comment_writes_no_label_and_exits_4(tmp_path):
    r, calls, _ = _run(tmp_path, "--sha", HEAD, env_extra={"GH_FAIL": "pr comment",
                                                          "IS_DRAFT": "true"})
    assert r.returncode == 4, r.stdout + r.stderr
    assert "pr comment FAILED" in r.stderr
    assert _idx(calls, "pr comment"), calls
    assert not _idx(calls, "pr edit"), calls
    assert not _idx(calls, "issue edit"), calls
    assert not _idx(calls, "pr ready"), calls


def test_a_label_failure_after_the_comment_exits_4_with_the_comment_posted(tmp_path):
    r, calls, body = _run(tmp_path, "--sha", HEAD, env_extra={"GH_FAIL": "pr edit"})
    assert r.returncode == 4, r.stdout + r.stderr
    assert "pr edit FAILED" in r.stderr
    assert body.startswith("QA: PASS"), body
    assert not _idx(calls, "issue edit"), calls


def test_a_rerun_with_labels_already_present_still_exits_0_and_writes_no_label(tmp_path):
    """Idempotent for labels; the comment is simply posted again (accepted:
    detect_stalls reads the newest verdict and agent-merge needs only one)."""
    r, calls, _ = _run(tmp_path, "--sha", HEAD, env_extra={
        "PR_LABELS": "qa-pass,qa:in-cycle", "ISSUE_LABELS": "qa-pass,qa:in-cycle"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "recorded" in r.stdout
    assert len(_idx(calls, "pr comment")) == 1, calls
    assert not _idx(calls, "pr edit") and not _idx(calls, "issue edit"), calls


# ------------------------------------------------------ the comment's words

def test_the_removal_paragraph_does_not_claim_the_removal_already_happened(tmp_path):
    """The paragraph is now written BEFORE the label removal, and the removal can
    still fail: past tense would be a justification ahead of the act."""
    r, calls, body = _run(tmp_path, "--sha", HEAD[:7], env_extra={
        "PR_LABELS": "qa-fail,qa:in-cycle", "ISSUE_LABELS": "qa-fail"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "qa-fail" in body, body
    assert "removed" not in body, body
    assert "is being cleared" in body, body
    assert "issue #1285" in body, body
    assert body.count(HEAD) == 2, body  # first line + the "this round passed on" line


def test_the_removal_paragraph_does_not_name_issue_none(tmp_path):
    r, _, body = _run(tmp_path, "--sha", HEAD, "--issue", "none",
                      env_extra={"PR_LABELS": "qa-fail"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "qa-fail" in body and "none" not in body, body

