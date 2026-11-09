#!/usr/bin/env python3
"""Print a `claude[bot]` installation token that is never more than 45 minutes old.

WHY THIS EXISTS
---------------
`claude-code-action` mints ONE `claude[bot]` token when it starts, and GitHub
expires it after an hour. A build cycle that runs longer keeps working on the
branch and then cannot push or comment. Measured on PR #804, run 42531382900,
22:40 to 00:26 UTC on 2026-11-08: the cycle's last QA verdict was posted at
23:27; after ~23:40 its pushes and its `gh` calls failed; the commits sat
local until the rescue step pushed them at 00:26:05 with `github.token`, and
GitHub held the `pull_request` runs that push started (actor
`github-actions[bot]`, #393) until the owner approved them by hand.

So the cycle's `git` and `gh` go through two wrappers
(`scripts/ci/token-wrappers/`) that call this, and this re-mints the SAME
identity the action mints, the same way it mints it:

  1. a GitHub OIDC token for audience `claude-code-github-action`
     (`ACTIONS_ID_TOKEN_REQUEST_URL`/`_TOKEN`, present because the job has
     `id-token: write`);
  2. POST it to Anthropic's exchange endpoint, no body -- exactly what
     `src/github/token.ts` does when no `additional_permissions` is set, so the
     scopes are the action's defaults (contents, pull-requests, issues: write).

The identity must stay `claude[bot]`: `agent-merge`, `chief_clear.py` and
`qa-on-green` trust only `claude[bot]`'s (or the owner's) `QA:` comments, so a
publisher-App token would let the cycle push but silently discard its verdicts.

It grants nothing new. Every input is already in the cycle's environment, and
the cycle has Bash, so it could run these two requests itself today.

Cached in a 0600 file under RUNNER_TEMP, so `git status` and the like never
pay a network call; only the wrappers' network subcommands ask for a token.

EXIT CODES: 0 printed a token   1 could not mint (stderr says why; the wrapper
then runs the command unchanged, which is exactly today's behaviour)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

AUDIENCE = "claude-code-github-action"
EXCHANGE = "https://api.anthropic.com/api/github/github-app-token-exchange"
#: GitHub installation tokens live 60 minutes; re-mint well before that.
MAX_AGE_S = 45 * 60


def _post_json(url: str, headers: dict[str, str], method: str = "GET") -> dict:
    req = urllib.request.Request(url, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed hosts)
        return json.loads(resp.read().decode())


def mint(env: dict[str, str] | None = None,
         fetch: Callable[..., dict] = _post_json) -> str:
    env = os.environ if env is None else env
    url, bearer = env.get("ACTIONS_ID_TOKEN_REQUEST_URL"), env.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not bearer:
        raise RuntimeError("no ACTIONS_ID_TOKEN_REQUEST_URL/TOKEN (needs `id-token: write`)")
    sep = "&" if "?" in url else "?"
    oidc = fetch(f"{url}{sep}audience={AUDIENCE}", {"Authorization": f"bearer {bearer}"}).get("value")
    if not oidc:
        raise RuntimeError("the OIDC response carried no token")
    data = fetch(EXCHANGE, {"Authorization": f"Bearer {oidc}"}, "POST")
    token = data.get("token") or data.get("app_token")
    if not token:
        raise RuntimeError("the exchange response carried no token")
    return token


def cached(cache: Path, mint_fn: Callable[[], str], now: float | None = None) -> str:
    now = time.time() if now is None else now
    try:
        if now - cache.stat().st_mtime < MAX_AGE_S:
            tok = cache.read_text().strip()
            if tok:
                return tok
    except OSError:
        pass
    tok = mint_fn()
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".tmp")
    tmp.write_text(tok)
    tmp.chmod(0o600)
    tmp.replace(cache)               # atomic: a concurrent reader sees old or new, never half
    return tok


def main() -> int:
    cache = Path(os.environ.get("RUNNER_TEMP") or "/tmp") / "claude-token" / "token"
    try:
        print(cached(cache, mint))
    except Exception as exc:          # noqa: BLE001 -- any failure means "run unchanged"
        print(f"claude_token: could not mint ({exc.__class__.__name__}: {str(exc)[:160]})",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
