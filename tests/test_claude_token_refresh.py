"""A cycle longer than an hour keeps pushing and commenting as claude[bot] (2026-11-09).

PR #804, run 42531382900 (22:40-00:26 UTC): the one claude[bot] token
claude-code-action mints expired mid-cycle, the cycle's pushes and QA comments
stopped, and the rescue step pushed its commits with github.token, whose
`pull_request` runs GitHub held for a human. These tests drive the wrappers
and the refresher with stubs: no network, no real token.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import subprocess
import textwrap

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WRAPPERS = ROOT / "scripts" / "ci" / "token-wrappers"

_spec = importlib.util.spec_from_file_location("claude_token", ROOT / "scripts" / "claude_token.py")
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)


# --- the refresher -----------------------------------------------------------

def test_mint_does_the_actions_oidc_exchange_with_no_body():
    calls = []

    def fetch(url, headers, method="GET"):
        calls.append((url, headers, method))
        return {"value": "oidc-jwt"} if method == "GET" else {"token": "ghs_fresh"}

    env = {"ACTIONS_ID_TOKEN_REQUEST_URL": "https://t.example/req?x=1",
           "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "rt"}
    assert ct.mint(env, fetch) == "ghs_fresh"
    assert calls[0] == ("https://t.example/req?x=1&audience=claude-code-github-action",
                        {"Authorization": "bearer rt"}, "GET")
    # Same audience, endpoint and (absent) body as claude-code-action's
    # token.ts, so the identity and scopes are the action's own.
    assert calls[1] == (ct.EXCHANGE, {"Authorization": "Bearer oidc-jwt"}, "POST")


def test_mint_refuses_without_the_oidc_request_env():
    with pytest.raises(RuntimeError, match="id-token"):
        ct.mint({}, lambda *a, **k: {})


def test_a_fresh_cached_token_is_reused(tmp_path):
    cache = tmp_path / "token"
    assert ct.cached(cache, lambda: "first", now=1000.0) == "first"
    os.utime(cache, (1000.0, 1000.0))
    assert ct.cached(cache, lambda: "second", now=1000.0 + ct.MAX_AGE_S - 1) == "first"
    assert oct(cache.stat().st_mode & 0o777) == "0o600"


def test_a_token_older_than_45_minutes_is_reminted(tmp_path):
    cache = tmp_path / "token"
    ct.cached(cache, lambda: "first", now=1000.0)
    os.utime(cache, (1000.0, 1000.0))
    assert ct.cached(cache, lambda: "second", now=1000.0 + ct.MAX_AGE_S + 1) == "second"
    assert ct.MAX_AGE_S < 60 * 60, "must re-mint before GitHub's 60-minute expiry"


# --- the wrappers ------------------------------------------------------------

def _sandbox(tmp_path, origin="https://github.com/o/r.git", mint_ok=True):
    """wrap/ holds the wrappers and a stub claude_token.py; real/ holds stub
    git and gh that log their argv and environment."""
    wrap, real, log = tmp_path / "wrap", tmp_path / "real", tmp_path / "log"
    wrap.mkdir(); real.mkdir()
    for name in ("git", "gh"):
        shutil.copy(WRAPPERS / name, wrap / name)
    (wrap / "claude_token.py").write_text(
        "import sys\n" + ("print('tok123')\n" if mint_ok else "sys.exit(1)\n"))
    (real / "git").write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        if [ "$*" = "remote get-url origin" ] || [ "$3 $4 $5" = "remote get-url origin" ]; then
          echo {origin}; exit 0
        fi
        echo "git $*" >> {log}
        """))
    (real / "gh").write_text(f"#!/usr/bin/env bash\necho \"gh GH_TOKEN=$GH_TOKEN $*\" >> {log}\n")
    for f in (real / "git", real / "gh", wrap / "git", wrap / "gh"):
        f.chmod(0o755)
    return wrap, real, log


def _run(wrap, real, cmd, refresh=True):
    env = {"PATH": f"{wrap}:{real}:/usr/bin:/bin", "GITHUB_REPOSITORY": "o/r",
           "GH_TOKEN": "expired"}
    if refresh:
        env["CLAUDE_TOKEN_REFRESH"] = "1"
    subprocess.run([str(wrap / cmd[0]), *cmd[1:]], env=env, check=True)


def _log(log):
    return log.read_text().splitlines() if log.exists() else []


def test_a_push_in_the_agent_step_refreshes_origin_first(tmp_path):
    wrap, real, log = _sandbox(tmp_path)
    _run(wrap, real, ["git", "push", "origin", "issue/1-x"])
    assert _log(log) == [
        "git remote set-url origin https://x-access-token:tok123@github.com/o/r.git",
        "git push origin issue/1-x"]


def test_options_before_the_subcommand_are_kept_for_the_refresh(tmp_path):
    wrap, real, log = _sandbox(tmp_path)
    _run(wrap, real, ["git", "-C", "/w", "fetch", "origin", "main"])
    assert _log(log)[0].startswith("git -C /w remote set-url origin https://x-access-token:tok123@")
    assert _log(log)[1] == "git -C /w fetch origin main"


def test_a_local_command_never_mints(tmp_path):
    wrap, real, log = _sandbox(tmp_path)
    _run(wrap, real, ["git", "commit", "-m", "x"])
    assert _log(log) == ["git commit -m x"]


def test_outside_the_agent_step_the_wrapper_is_inert(tmp_path):
    wrap, real, log = _sandbox(tmp_path)
    _run(wrap, real, ["git", "push", "origin", "b"], refresh=False)
    _run(wrap, real, ["gh", "pr", "view"], refresh=False)
    assert _log(log) == ["git push origin b", "gh GH_TOKEN=expired pr view"]


def test_another_repositorys_origin_is_never_rewritten(tmp_path):
    wrap, real, log = _sandbox(tmp_path, origin="https://github.com/anthropics/claude-code-action.git")
    _run(wrap, real, ["git", "fetch"])
    assert _log(log) == ["git fetch"]


def test_a_failed_mint_runs_the_command_unchanged(tmp_path):
    wrap, real, log = _sandbox(tmp_path, mint_ok=False)
    _run(wrap, real, ["git", "push", "origin", "b"])
    _run(wrap, real, ["gh", "pr", "view"])
    assert _log(log) == ["git push origin b", "gh GH_TOKEN=expired pr view"]


def test_gh_in_the_agent_step_gets_the_fresh_token(tmp_path):
    wrap, real, log = _sandbox(tmp_path)
    _run(wrap, real, ["gh", "pr", "comment", "1"])
    assert _log(log) == ["gh GH_TOKEN=tok123 pr comment 1"]


# --- the workflow ------------------------------------------------------------

def _steps():
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-work.yml").read_text())
    return doc["jobs"]["cycle"]["steps"]


def test_the_refresher_is_installed_on_path_before_the_agent_step():
    steps = _steps()
    names = [s.get("name") or s.get("uses", "") for s in steps]
    i = names.index("Install the token refresher")
    agent = next(n for n, s in enumerate(steps)
                 if str(s.get("uses", "")).startswith("anthropics/claude-code-action"))
    assert i < agent
    run = steps[i]["run"]
    assert '>> "$GITHUB_PATH"' in run and "scripts/ci/token-wrappers/git" in run


def test_only_the_agent_step_turns_the_wrappers_on():
    on = [s.get("name") or s.get("uses") for s in _steps()
          if (s.get("env") or {}).get("CLAUDE_TOKEN_REFRESH") == "1"]
    assert on == ["anthropics/claude-code-action@v1"], on


def test_the_rescue_push_uses_the_publisher_token_not_github_token():
    step = next(s for s in _steps() if s.get("name") == "Push the branch and open the PR")
    assert 'x-access-token:${PR_TOKEN}@github.com' in step["run"]
    assert 'x-access-token:${GH_TOKEN}@github.com' not in step["run"], (
        "a github.token push starts pull_request runs GitHub holds for approval (#804)")
