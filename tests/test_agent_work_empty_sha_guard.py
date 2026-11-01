"""An empty head SHA must never reach the runs query (#602).

`gh pr view ... --jq .headRefOid` can exit 0 and print NOTHING, and
`|| git rev-parse HEAD` does not fire on empty stdout -- only on a non-zero
exit. The URL then reads:

    repos/OWNER/REPO/actions/runs?head_sha=&per_page=100

and GitHub treats an empty filter VALUE as no filter at all, returning the most
recent 100 runs in the repository. "PR gates" runs are always among them, so
the count is large, the retry loop breaks on its first attempt, and the #322
rescue dispatch never fires -- leaving a PR with no checks, which `agent-merge`
refuses forever.

WHY THE EXISTING GUARD CANNOT CATCH IT. The step already has:

    case "$gates_runs" in ''|*[!0-9]*) gates_runs=0 ;; esac

written so an error string or an empty body falls TOWARD the rescue. That is
correct and is not this bug: here the count is a legitimately large NUMBER, so
the guard passes it through and the fallback is never reached. A guard against
malformed output is not a guard against well-formed output about the wrong
thing -- the same class as #604 (a label read on one path) and #550 round 5
(an implicit `success()` read as a verdict).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".github" / "workflows" / "agent-work.yml"


def _step_run() -> str:
    doc = yaml.safe_load(WORK.read_text())
    steps = doc["jobs"]["cycle"]["steps"]
    hits = [s for s in steps if "head_sha=" in str(s.get("run", ""))]
    assert len(hits) == 1, f"expected one step querying head_sha, found {len(hits)}"
    return hits[0]["run"]


def _fake_bin(tmp_path: Path, pr_view_stdout: str) -> Path:
    """`gh` that prints `pr_view_stdout` for `pr view` and logs every `api` URL."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "pr" ] && [ "$2" = "view" ]; then\n'
        '  printf "%s" "$PR_VIEW_STDOUT"\n'
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "api" ]; then\n'
        '  printf "%s\\n" "$2" >> "$API_LOG"\n'
        '  echo 7\n'      # a plausible, well-formed, LARGE count
        "  exit 0\n"
        "fi\n"
        "exit 0\n")
    (bin_dir / "gh").chmod(0o755)
    (bin_dir / "git").write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "rev-parse" ]; then echo deadbeefdeadbeefdeadbeefdeadbeefdeadbeef; exit 0; fi\n'
        "exit 0\n")
    (bin_dir / "git").chmod(0o755)
    return bin_dir


QUERY = 'repos/$GH_REPO/actions/runs?head_sha=$sha&per_page=100'


def _resolved_query(pr_view_stdout: str, tmp_path: Path) -> str:
    """Run ONLY the SHA-resolution fragment, then print the query the step
    would build from `$sha`.

    The fragment is sliced out rather than retyped, so the test cannot drift
    from the shell. It stops at `gates_runs=0` because the retry loop after it
    cannot be sliced mid-body -- `for ... do` without its `done` is a syntax
    error. `test_the_query_line_still_interpolates_sha` is what ties this
    fragment back to the real query.
    """
    bin_dir = _fake_bin(tmp_path, pr_view_stdout)
    script = _step_run()
    start = script.index("sha=$(gh pr view")
    end = script.index("gates_runs=0")
    frag = script[start:end] + f'\nprintf "%s" "{QUERY}"\n'
    p = subprocess.run(
        ["bash", "-c", frag],
        capture_output=True, text=True,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "PR_VIEW_STDOUT": pr_view_stdout,
            "API_LOG": str(tmp_path / "api.log"),
            "GH_REPO": "mahAnuj/astro-ai",
            "branch": "issue/999-x",
        },
    )
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout.strip().splitlines()[-1]


def test_the_query_line_still_interpolates_sha():
    """The fragment above is only meaningful while the real query is built from
    `$sha`. If someone rewrites the query, this fails rather than letting the
    behavioural tests quietly assert about nothing."""
    run = _step_run()
    assert "head_sha=$sha" in run, (
        "the runs query no longer interpolates $sha — the guard tests below "
        "are now testing a URL the step does not build")


def test_an_empty_head_sha_never_reaches_the_query(tmp_path):
    """THE DEFECT. An empty `head_sha=` is GitHub-speak for 'every run'."""
    q = _resolved_query("", tmp_path)
    assert "head_sha=&" not in q and not q.endswith("head_sha="), (
        f"an empty head_sha reached the query: {q!r} — GitHub reads this as NO "
        "filter and returns every run in the repo, suppressing the #322 rescue")


def test_the_fallback_sha_is_used_when_pr_view_prints_nothing(tmp_path):
    assert "deadbeef" in _resolved_query("", tmp_path)


def test_a_real_sha_is_passed_through_unchanged(tmp_path):
    """The fix must not override a SHA that was read correctly."""
    sha = "a" * 40
    q = _resolved_query(sha, tmp_path)
    assert f"head_sha={sha}" in q, q
    assert "deadbeef" not in q, "the fallback fired on a SHA that was read fine"


def test_whitespace_only_output_is_also_treated_as_empty(tmp_path):
    """`--jq` on a null field prints a bare newline, not nothing."""
    q = _resolved_query("\n", tmp_path)
    assert "head_sha=&" not in q and not q.endswith("head_sha="), q
