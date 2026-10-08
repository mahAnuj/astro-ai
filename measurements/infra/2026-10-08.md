# infra-lead report — #285: agent-cycle dispatches an engineer and nothing happens

Run 37738950382 (`agent-infra.yml`, claude-code-action, CLI 2.1.293). Every claim marked
**measured** was run in this session. Everything else is labelled inference.

## Verdict

**The issue's hypothesis is refuted.** The `Agent` tool is callable inside claude-code-action,
and the repo's `.claude/agents/*` definitions register there. Dispatch is not what is broken.

**Probable cause (inference, strongly supported by the action's source and by a reproduction
in this run): the parent ends its turn while the engineer is still running.** `Agent` dispatches
in the **background by default**. The action stops reading the moment the parent produces its
first `result` message, so a parent that dispatches and then ends its turn kills the engineer
and still exits `success`.

I could **not** read the three failing runs' logs (see "What I could not determine"), so the
link between this mechanism and those three runs is inferred, not observed.

## Question 1 — is `Agent` callable inside the action?  YES (measured)

This run is inside `anthropics/claude-code-action` (`GITHUB_ACTION=__anthropics_claude-code-action`,
`CLAUDE_CODE_ENTRYPOINT=claude-code-github-action`). `~/.claude/agents/` does not exist on the
runner (`ls ~/.claude/` shows no `agents`).

- Background dispatch of a trivial probe returned `Async agent launched successfully` instantly.
  A completion notification arrived later with the result `PROBE-OK <type>`.
- Foreground dispatch (`run_in_background: false`) of an engineer that ran `sleep 8; date +%s`
  returned inline after 10.2 s: `FG-PROBE-OK 1791441839`, `tool_uses: 1`.
- A **nested** dispatch from a `dev-lead` subagent was accepted too (it had an `Agent` tool).

**`Agent` is not in this workflow's `--allowedTools`** (`Read,Write,Glob,Grep,TodoWrite,Skill,
WebFetch,Bash`) **and it still worked.** `agent-work.yml` lists `Agent`; that entry is neither the
cause nor needed. I did not test whether `--disallowedTools Agent` would block it.

## Question 2 — which `subagent_type` values resolve?  ALL 14 repo agents (measured)

The harness's own "available agents" list, quoted from the error returned for a bad type:

```
Agent type 'no-such-agent-type' not found. Available agents: analyst, architect, astro-auditor,
chief, claude, claude-code-guide, conversion-lead, dev-lead, engineer, Explore, frontend-engineer,
general-purpose, infra-lead, numerologist, Plan, product-manager, project-manager, qa, qa-lead,
statusline-setup
```

`ls .claude/agents/` has exactly 14 files: analyst, architect, astro-auditor, chief,
conversion-lead, dev-lead, engineer, frontend-engineer, infra-lead, numerologist, product-manager,
project-manager, qa-lead, qa. **All 14 are in the list**, with no global-agent dependency.

Dispatched and answered with `PROBE-OK`: `engineer`, `qa`, `architect`, `frontend-engineer`.
That covers both the names that also exist globally and a project-only name. I did not dispatch
the other ten individually; the list shows them registered, but registered is not proof they run.

The `Agent type 'infra-lead' not found` quoted in #285 was a **local** session whose list was
`~/.claude/agents/` only. It does not transfer to CI: the CI list above includes `infra-lead`.

## Question 3 — does a failed dispatch surface?

Two different failures, which behave differently:

| failure | what the caller sees | loud? |
|---|---|---|
| Bad `subagent_type` | immediate tool **error** naming the available agents (measured above) | **Yes** — the parent can't miss it |
| Dispatched fine, parent ends its turn before the agent finishes | nothing. The tool result said `launched successfully`; the run concludes `success` | **No** |

The second is the dangerous one, and nothing in the workflow checks the outcome. The action
marks the run by `resultMessage.subtype === "success"` only
(`base-action/src/run-claude-sdk.ts:253-256`). Nothing asks whether the work happened.

## The mechanism, and why it fits all three runs

1. `Agent` returns at once with `Async agent launched successfully … You will be notified
   automatically when it completes`. Dispatch is background unless `run_in_background: false`
   is passed. `.claude/commands/agent-cycle.md:82` shows `Agent(subagent_type=…, description=…,
   prompt=…)` with no such argument, and the string `run_in_background` appears nowhere in
   `.claude/`, `.github/` or `CLAUDE.md` (measured by grep).
2. The action loops `for await (const message of query(...))` and does `break` on the first
   `result` message (`run-claude-sdk.ts:198-210`). The comment there says the iterator is
   abandoned deliberately. The first `result` is emitted when the parent ends its turn.
3. The step-3 comment on #272 in all three runs reads "engineer dispatched … QA will be a
   separate dispatch". That is a parent that wrote its trail and ended, believing the dispatch
   was the work.
4. Run 3's numbers fit: 7 turns of 150, 0 denials, $0.30. Seven turns is step 0, a few reads, a
   comment and a dispatch. An engineer doing four acceptance criteria across two scripts costs
   far more than $0.30, so the engineer's work was not in that bill.
5. **Reproduced in this run.** I dispatched a `dev-lead` with "make one call to `engineer`, report
   the result". It dispatched, received the async-launched text, and ended with *"the engineer's
   actual reply has not reached me … whether it replied correctly is still unknown."* That is the
   same shape, one level down: a coordinator that ends its turn with a dispatch outstanding and
   reports that as done. It also means `/bug` and `/feature` through `dev-lead` are exposed in
   the same way.

What would confirm it for the three real runs: in each run's log, the `tool_result` for the
engineer `Agent` call should start `Async agent launched successfully`, followed shortly by the
`result` message with no later engineer activity.

```bash
gh run view 37737070840 --log | grep -n 'Async agent launched\|"type":"result"\|num_turns'
```

I could not run this (below).

## Proposed diffs — not applied

### 1. `.claude/commands/agent-cycle.md` — dispatches are foreground, and a dispatch is not a deliverable

This keeps the roles separate. The engineer still writes, `qa` is still a different dispatch.
Only the waiting changes.

```diff
@@ ## Step 2 — rank
-Agent(subagent_type="project-manager", description="Rank the eligible backlog",
-      prompt="""Rank what to work on next in <cwd>. ...""")
+Agent(subagent_type="project-manager", description="Rank the eligible backlog",
+      run_in_background=false,
+      prompt="""Rank what to work on next in <cwd>. ...""")
@@ ## Step 3 — build it
+### Every dispatch is foreground. This is not optional.
+
+`Agent` runs in the **background by default** and returns `Async agent launched successfully`
+at once. In CI the run ends when you end your turn, which kills every agent still running.
+Three runs on #272 did exactly this: each commented "engineer dispatched", ended, and left
+no branch, no commit and no PR.
+
+- Pass `run_in_background=false` on **every** `Agent` call in this loop.
+- If a result says `launched successfully` or `working in the background`, you have **not**
+  dispatched anything yet. Do not end your turn, and do not comment that you dispatched.
+- Comment "engineer returned" only after the call returns, and quote what came back.
+- **Post-condition after the engineer returns, before `qa` is dispatched:**
+  `git log origin/main..HEAD --oneline` must show at least one commit on `issue/<n>-*`.
+  Zero commits means the engineer produced nothing: comment that, label `needs-human-review`,
+  and stop. Never dispatch `qa` on an empty branch and never write the code yourself.
```

### 2. `.github/workflows/agent-work.yml` — make "produced nothing" red

The existing safety-net step says `no commits … the cycle produced nothing` and `exit 0`.
That is the silent success. Fail it when the run was asked to work a named issue.

```diff
       - name: Push the branch and open the PR
         if: always()
         env:
           GH_TOKEN: ${{ github.token }}
           GH_REPO: ${{ github.repository }}
+          ISSUE: ${{ github.event.inputs.issue }}
         run: |
           branch=$(git rev-parse --abbrev-ref HEAD)
           case "$branch" in
             issue/*) ;;
-            *) echo "on '$branch', not an issue branch — nothing to push"; exit 0 ;;
+            *)
+              echo "on '$branch', not an issue branch — nothing to push"
+              # A run asked to work issue N that ends on main did not work it.
+              if [ -n "$ISSUE" ]; then
+                echo "::error::issue #$ISSUE was requested and no issue/ branch exists — the cycle produced nothing"
+                exit 1
+              fi
+              exit 0 ;;
           esac
           if [ -z "$(git log origin/main..HEAD --oneline)" ]; then
-            echo "no commits on $branch — the cycle produced nothing"
-            exit 0
+            echo "::error::no commits on $branch — the cycle produced nothing"
+            exit 1
           fi
```

Caveat: this fails the run, and `agent-merge` gates on this workflow concluding `success`, so a
red no-op run now blocks nothing it should not (nothing was produced to merge). A scheduled run
with no `issue` input that legitimately finds nothing eligible still exits 0.

### 3. `.github/workflows/agent-infra.yml` — so the next diagnosis can read logs

`gh run view` returned `HTTP 403 Resource not accessible by integration` on all three runs,
although this job has `actions: read`. The action runs `gh` with its own app token
(`claude[bot]`), not `github.token`. Fetch the logs in a step that has the right token and
hand them to the agent as files:

```diff
+      - name: Fetch recent agent-work logs
+        continue-on-error: true
+        env:
+          GH_TOKEN: ${{ github.token }}
+        run: |
+          mkdir -p /tmp/runlogs
+          for id in $(gh run list --workflow agent-work.yml --limit 5 --json databaseId --jq '.[].databaseId'); do
+            gh run view "$id" --log > "/tmp/runlogs/$id.log" 2>&1 || true
+          done
+          ls -la /tmp/runlogs
       - uses: anthropics/claude-code-action@v1
```

### 4. `.github/workflows/agent-infra.yml` — gcloud is granted but not authenticated

See the next section. Not a #285 item, but it blocks the BUILD_SHA work.

## What I could not determine

- **The three failing runs' logs.** All `actions/runs/...` calls return 403 under the action's
  token. So the claim that those runs ended on an async-launch result is inference from the
  action's source plus a reproduction here, not an observation of those runs.
- **Whether the CLI would hold the `result` message open for a running background agent.** Here,
  background completions arrived as notifications because I kept working. If the CLI waited for
  background agents before emitting `result`, the three runs would not have died this way. I
  have set up a probe for that (next section) but cannot read its result myself.
- **Whether `--disallowedTools Agent` or a missing `Agent` entry changes anything.** Not tested.
- **Whether the engineer would then succeed** in `agent-work.yml`. A foreground engineer here
  ran Bash; I did not test `Write`/`Edit` or `git commit` under that workflow's grant, so
  "engineer then hits a permission wall" remains possible and is a different failure.
- **`agent-work.yml` itself.** I read it; I did not run it.

## Pending probe — does the CLI wait for background agents when the parent ends its turn?

As the last action of this run I dispatch one background `engineer` that sleeps 100 s and then
appends a single line to `/tmp/report.md` beginning `BG-PROBE:`.

- If that line appears at the foot of this report in the run summary or the `infra-report`
  artifact: the CLI **did wait**, and the background-exit theory for #285 is weakened. Look
  for another cause (a permission wall in the engineer is the next candidate).
- If it is absent: the engineer was killed when the parent ended. The theory stands.

Nobody should treat the absence of the line as proof without checking the run finished more
than 100 s after the report was written.

## Not done this run: the `BUILD_SHA` fix  (blocked, measured)

`gcloud auth list` → `No credentialed accounts`. `agent-infra.yml` has no
`google-github-actions/auth` step (`agent-work.yml` has one; this file does not). The comment in
the workflow says gcloud is granted, but the runner cannot reach GCP at all. So I did not
export or change the trigger, and nothing in CLAUDE.md changed.

To make the grant real, add the same keyless WIF step `agent-work.yml:71-74` uses. That
service account (`agent-analytics@…`) was set up for analytics; whether it holds
`cloudbuild.builds.editor` or the trigger-edit permission is unknown. If it does not, granting it
is an IAM change and a human's call.

Live state measured this run (probe, taken before I started): `/health` →
`{"ok":true,"revision":"bhagya-00393-grd","build_sha":null}`. `build_sha` is still null, so the
`exact` tier still has not run. The routes in `/tmp/probe.txt`: `/` 200 0.76 s, `/kundli` 200
0.70 s, `/matching` 200 0.56 s, `/numerology` 200 0.56 s, `/learn` 307 0.38 s.

## Free tier

None of the proposals add Cloud Run, GCS or Groq usage. They change what the CI agent waits for
and whether an empty run is red. Diff 3 adds five `gh run view --log` calls per infra run, which
the Actions API serves free. Foreground dispatch does not change tokens per dispatch, but a
parent that now waits for the engineer will actually spend the engineer's tokens. Run 3 spent
$0.30 because the engineer's work never happened; expect the real figure to be several times
that on the first run that works. That is the Claude subscription cap in the `agent-work.yml`
header, not the Groq or GCP free tier. I did not measure it.
