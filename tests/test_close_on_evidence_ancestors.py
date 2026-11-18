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
case "$*" in
  *"compare/"*) # compare/X...Y -> ahead when X is A and Y is B, identical when equal
     spec=$(echo "$*" | grep -oE 'compare/[0-9a-f]+\.\.\.[0-9a-f]+'); x=${spec#compare/}; x=${x%%...*}; y=${spec##*...}
     if [ "$x" = "$y" ]; then echo identical; elif [ "$x" = "$A" ] && [ "$y" = "$B" ]; then echo ahead; else echo behind; fi ;;
  *"pulls?state=closed"*) printf '%s\n' "1077:$A" "1200:$B" "999:$C" ;;
  "pr view 1077"*"headRefName"*) echo "issue/1056-x" ;;
  "pr view 1200"*"headRefName"*) echo "issue/1201-y" ;;
  "pr view 999"*"headRefName"*) echo "issue/998-z" ;;
  "pr view 1077"*) printf 'title\ncloses #1056\n' ;;
  "pr view 1200"*) printf 'title\nfixes #1201\n' ;;
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
           "C": "c" * 40, "GH_REPO": "o/r", "CALLS": str(calls), "GITHUB_OUTPUT": str(out),
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
