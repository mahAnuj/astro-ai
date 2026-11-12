"""The research loop opens its corpus PR as the publisher, not github-actions[bot].

#915 (2026-11-12): opened with github.token, its pull_request suites were held
in `action_required` (#393) and it sat 14h with no check run.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "agent-research.yml"


def _steps():
    return {s.get("name"): s for s in yaml.safe_load(WF.read_text())["jobs"]["propose"]["steps"]}


def test_a_publisher_token_is_minted_and_cannot_fail_the_job():
    mint = _steps()["Mint a publisher token"]
    assert mint["uses"].startswith("actions/create-github-app-token@")
    assert mint.get("continue-on-error") is True


def test_the_pr_is_pushed_and_opened_with_it():
    step = _steps()["Open a PR for any corpus additions"]
    assert step["env"]["GH_TOKEN"] == "${{ steps.app-token.outputs.token || github.token }}"
    assert 'x-access-token:${GH_TOKEN}@github.com' in step["run"]
    assert 'git push -u origin "$branch"' not in step["run"]
