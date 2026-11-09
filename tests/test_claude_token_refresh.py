"""The rescue push uses the publisher App token, not github.token (2026-11-09).

PR #804, run 42531382900: the cycle outlived its one-hour claude[bot] token,
the rescue step pushed its commits with github.token, and GitHub held the
pull_request runs that push started (actor github-actions[bot], #393) until the
owner approved them. A fresh publisher token cannot have expired, which was the
only reason this push used github.token.

A token refresher for the agent step was tried in the same PR and withdrawn:
QA found the OIDC request variables absent from the agent's Bash environment,
so it could never mint, and freshly minted tokens would not be masked in a
public log. That problem is recorded in its own issue.
"""
from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _steps():
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-work.yml").read_text())
    return doc["jobs"]["cycle"]["steps"]


def test_the_rescue_push_uses_the_publisher_token_not_github_token():
    step = next(s for s in _steps() if s.get("name") == "Push the branch and open the PR")
    assert 'x-access-token:${PR_TOKEN}@github.com' in step["run"]
    assert 'x-access-token:${GH_TOKEN}@github.com' not in step["run"], (
        "a github.token push starts pull_request runs GitHub holds for approval (#804)")
