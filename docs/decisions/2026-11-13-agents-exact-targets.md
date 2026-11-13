# Agent cards name the exact PR or issue, and the ops page lists every running workflow

- **Date:** 2026-11-13
- **PR / issue:** this PR (owner's request in a session: *"show exact PR, issue on which agent is working ... can we also see the workflow running on which task"*)

## Why, measured

The first version of the cards (`2026-11-13-agents-right-now.md`) named the developer's target
by guessing: "the newest open `issue/`, `partial/` or `fix/` PR". With two cycle PRs open the
guess named the wrong one, and a ranked cycle that had not opened a PR yet was shown working on
an older one. Nothing on the page said which workflows were running or on what.

Now every target comes from something GitHub states, never from inference:

| run | target, and where it comes from |
| --- | --- |
| `QA round: PR #n` | PR #n, title from the open-PR list, issue from its cycle branch |
| `Agent work: issue #n` | issue #n, title read from `issues/n` |
| plain `Agent work` (ranked) | "picking the next issue from the ranked backlog": the issue is chosen inside the Claude step, so nothing outside it knows until a PR opens |
| any run whose `head_branch` is an open PR's head | that PR (`PR gates`, `verify-build`, ...) |
| any run on an `issue/n-` branch with no PR | issue #n |
| otherwise | the trigger: scheduled, started by another workflow, push to a branch |

The `Agent work: issue #n` title needs `agent-work.yml`'s `run-name` to carry the `issue`
input. That is a workflow file, so it ships as its own PR, held for chief. Until it merges,
dispatched cycles keep the title `Agent work` and show as "picking", which is honest but less
specific; this PR changes nothing else about that.

**Cost:** the same 3 GitHub reads per refresh, plus one `issues/n` read per issue a running
cycle names, capped at `MAX_ISSUE_READS = 3` (one in practice: build cycles run one at a time).
`/api/agents/status` gains a `workflows` array; existing fields are unchanged. 0 LLM tokens.

**Also from QA's notes on the first version:** an `agents.json` row whose conclusion is still
`in_progress` (collected while the run was live) now reads "started", and `skipped` reads
"was skipped", instead of "finished"; a failed refresh logs one line instead of a traceback.

**Rejected:** naming the PR a running merge sweep is checking. `agent-merge` picks one eligible PR
inside the job (lowest number first, skipping any it cannot merge) and its run carries no PR in its
title or branch, so any name would be a guess. QA round 1 on this PR measured exactly that guess
naming the wrong PR (#950 shown, #940 taken). While the sweep runs, the card counts the PRs that
passed QA instead; when it is not running, it names the first one waiting, which is a fact.
