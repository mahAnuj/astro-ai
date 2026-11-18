"""close-on-evidence closes every PR the live, verified commit CONTAINS (2026-11-18).

Measured: #1056 (PR #1077, verify-production green 2026-11-15) and #1080 (PR #1118,
its own verify run failed on the deploy wait) never closed. The step required
/health == the run's SHA and looked only at that SHA's own PR, so a PR merged in a
burst -- a later merge already serving when its run finished -- was skipped forever.
These tests run the workflow's real shell with fake `gh` and `curl`.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "close-on-evidence.yml"
A, B = "a" * 40, "b" * 40          # A = older merge, B = newer merge (contains A)

FAKE_GH = r'''#!/usr/bin/env bash
echo "$*" >> "$CALLS"
if [ -n "${FAIL_ON:-}" ] && [[ "$*" == *"$FAIL_ON"* ]]; then echo "HTTP 403" >&2; exit 1; fi
case "$*" in
  *"compare/"*) # compare/X...Y -> ahead when X is A and Y is B, identical when equal
     spec=$(echo "$*" | grep -oE 'compare/[0-9a-f]+\.\.\.[0-9a-f]+'); x=${spec#compare/}; x=${x%%...*}; y=${spec##*...}
     if [ "$x" = "$y" ]; then echo identical; elif [ "$x" = "$A" ] && [ "$y" = "$B" ]; then echo ahead; else echo behind; fi ;;
  *"issues?state=open"*) echo '[1056, 1201, 1202, 1203, 998]' ;;
  *"pulls?state=closed"*)
     printf '%s\n' "{\"n\":1077,\"m\":\"$A\",\"t\":\"x closes #1056\",\"b\":\"issue/1056-x\"}" \
                   "{\"n\":1200,\"m\":\"$B\",\"t\":\"Closes #1201, #1202 and #1203\",\"b\":\"issue/1201-y\"}" \
                   "{\"n\":999,\"m\":\"$C\",\"t\":\"closes #998\",\"b\":\"issue/998-z\"}" \
                   "{\"n\":555,\"m\":\"$D\",\"t\":\"chore: measurement\",\"b\":\"measurements/1-1\"}" ;;
  *"/events"*) # one page; prints what --jq would: reopens after the PR merged
     if [ -n "${REOPENED:-}" ] && [[ "$*" == *"issues/$REOPENED/events"* ]]; then echo 1; else echo 0; fi ;;
  "pr view"*"mergedAt"*) echo "2026-11-15T10:00:00Z" ;;
  "pr view 1077"*"headRefName"*) echo "issue/1056-x" ;;
  "pr view 1200"*"headRefName"*) echo "issue/1201-y" ;;
  "pr view 999"*"headRefName"*) echo "issue/998-z" ;;
  "pr view 1077"*) printf 'title\ncloses #1056\n' ;;
  "pr view 1200"*) printf 'title\nCloses #1201, #1202 and #1203\n' ;;
  "pr view 999"*) printf 'title\ncloses #998\n' ;;
  "issue view"*) echo OPEN ;;
  "issue close"*) echo closed ;;
  *) echo "" ;;
esac
'''


def _step(name):
    doc = yaml.safe_load(WF.read_text())
    return next(s for s in doc["jobs"]["close"]["steps"] if s.get("name") == name)


def _bin(tmp, live):
    b = tmp / "bin"; b.mkdir()
    (b / "gh").write_text(FAKE_GH)
    (b / "curl").write_text(f'#!/usr/bin/env bash\necho \'{{"build_sha": "{live}"}}\'\n')
    for f in b.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return b


def _run(tmp, script, sha, live, extra_env=None):
    b = _bin(tmp, live)
    out = tmp / "out"; out.write_text("")
    calls = tmp / "calls"; calls.write_text("")
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}", "SHA": sha, "A": A, "B": B,
           "C": "c" * 40, "D": "d" * 40, "GH_REPO": "o/r", "CALLS": str(calls), "GITHUB_OUTPUT": str(out),
           "RUN_URL": "", **(extra_env or {})}
    r = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, text=True)
    return r, out.read_text(), calls.read_text()


def test_a_newer_live_deploy_that_contains_the_commit_still_counts(tmp_path):
    r, out, _ = _run(tmp_path, _step("Is this exact commit serving?")["run"], sha=A, live=B)
    assert r.returncode == 0 and "ok=true" in out and f"live={B}" in out


def test_a_live_deploy_that_does_not_contain_the_commit_closes_nothing(tmp_path):
    r, out, _ = _run(tmp_path, _step("Is this exact commit serving?")["run"], sha=B, live=A)
    assert r.returncode == 0 and "ok=true" not in out


def test_every_pr_contained_in_the_verified_commit_closes_its_issue(tmp_path):
    r, _, calls = _run(tmp_path, _step("Close what this commit shipped")["run"], sha=B, live=B,
                       extra_env={"LIVE": B})
    assert r.returncode == 0, r.stderr
    closed = [ln for ln in calls.splitlines() if ln.startswith("issue close")]
    assert any("1056" in c for c in closed), "the burst-merged PR #1077's issue must close"
    assert any("1201" in c for c in closed), "the run's own PR still closes"
    assert not any("998" in c for c in closed), "a PR not in the verified history must not close"


def test_a_list_of_issues_after_closes_closes_all_of_them(tmp_path):
    """PR #1196 said 'Closes #1185, #1186 and #1187'; only #1185 closed."""
    r, _, calls = _run(tmp_path, _step("Close what this commit shipped")["run"], sha=B, live=B,
                       extra_env={"LIVE": B})
    closed = " ".join(ln for ln in calls.splitlines() if ln.startswith("issue close"))
    for n in ("1201", "1202", "1203"):
        assert n in closed, n


def test_only_prs_claiming_an_open_issue_cost_a_compare_call(tmp_path):
    """~400 PRs in 14 days: a PR claiming nothing open (PR 555) gets no compare."""
    r, _, calls = _run(tmp_path, _step("Close what this commit shipped")["run"], sha=B, live=B,
                       extra_env={"LIVE": B})
    assert r.returncode == 0, r.stderr
    compares = [ln for ln in calls.splitlines() if "compare/" in ln]
    assert compares and not any("d" * 40 in c for c in compares), "PR 555 claims nothing open"
    assert "--paginate" in next(ln for ln in calls.splitlines() if "pulls?state=closed" in ln)


# --- a failing listing must turn the run red (QA FAIL on #1212 at 349a6e8) ----

def _close(tmp, fail_on):
    return _run(tmp, _step("Close what this commit shipped")["run"], sha=B, live=B,
                extra_env={"LIVE": B, "FAIL_ON": fail_on})


def test_a_failed_pr_listing_exits_non_zero_and_closes_nothing(tmp_path):
    r, _, calls = _close(tmp_path, "pulls?state=closed")
    assert r.returncode != 0 and "could not list merged PRs" in r.stdout
    assert "issue close" not in calls


def test_a_failed_open_issue_listing_exits_non_zero_and_closes_nothing(tmp_path):
    r, _, calls = _close(tmp_path, "issues?state=open")
    assert r.returncode != 0 and "could not list open issues" in r.stdout
    assert "issue close" not in calls


def test_a_failed_compare_still_closes_the_rest_then_exits_non_zero(tmp_path):
    r, _, calls = _close(tmp_path, "compare/")
    assert r.returncode != 0 and "compare call(s) failed" in r.stdout
    closed = " ".join(ln for ln in calls.splitlines() if ln.startswith("issue close"))
    assert "1201" in closed, "the verified commit's own PR needs no compare and still closes"
    assert "1056" not in closed, "a PR whose compare failed is not closed on a guess"


# --- a reopened issue stays open (QA FAIL on #1212 at f71d4db) ----------------

def test_an_issue_reopened_after_its_pr_merged_is_not_closed_again(tmp_path):
    r, _, calls = _run(tmp_path, _step("Close what this commit shipped")["run"], sha=B, live=B,
                       extra_env={"LIVE": B, "REOPENED": "1056"})
    assert r.returncode == 0, r.stderr
    closed = " ".join(ln for ln in calls.splitlines() if ln.startswith("issue close"))
    assert "1056" not in closed and "reopened after PR #1077 merged" in r.stdout
    assert "1201" in closed, "issues nobody reopened still close"
    assert "events" in calls and "reopened" in calls


def test_an_unreadable_timeline_closes_nothing_for_that_issue_and_exits_non_zero(tmp_path):
    r, _, calls = _close(tmp_path, "issues/1056/events")
    assert r.returncode != 0 and "timeline read(s) failed" in r.stdout
    closed = " ".join(ln for ln in calls.splitlines() if ln.startswith("issue close"))
    assert "1056" not in closed and "1201" in closed
