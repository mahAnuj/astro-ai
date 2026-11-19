---
description: The build-cycle steps of /agent-cycle (Steps 0, 1, 2, 2.5, 3, 3.6, 4, 4.5). Read by /agent-cycle; not run on its own.
---

# /agent-cycle — the build-cycle steps

Read in full by a build cycle, right after `.claude/commands/agent-cycle.md`, which holds Step 0a,
Step 3.5, Step 5, the shared section and the non-negotiables. QA rounds and fix rounds do not read
this file (Step 0d reads only Step 3). Split from the one file on 2026-11-19 (#1254).

## Step 0 — validate against live production. Before anything else.

**An open issue is not evidence that the problem still exists.** `BACKLOG.md` recorded 36 open
against 50 actual. `project-manager`'s own definition says *"Do not rank from issue titles. Titles
lie."*

This has already bitten: #266 was asserted to be a total outage from its `OPEN` state alone. One
page load looked fine. Two probes with different birth data showed a 200 and a 503, and a retry of
the failing one succeeded 26 seconds later. **It is intermittent** — so a single request would have
closed it falsely, and a single page load would have left it open and misdescribed.

```bash
uv run python scripts/validate_issue.py <n> --samples 5
```

- **Does not reproduce in 5 samples** → **close it**, with every request and response in the
  closing comment, and label `cannot-reproduce`.

  **UNLESS AN OPEN PR ALREADY EXISTS FOR THIS ISSUE. Then do not close, and do not probe for a
  verdict at all — skip to Step 2.5.**

  ```bash
  gh pr list --repo "$GH_REPO" --state open --search "<n> in:body" --json number,headRefName
  git ls-remote --heads origin "issue/<n>-*" "partial/<n>-*" "fix/<n>-*"
  ```

  The reasoning is one sentence: **production cannot show work that has not merged.** A cycle
  dispatched at a PR carrying `qa-fail` is there to fix the findings, and the PR is the state of
  that work — not the deployed site. Probing production and closing on the result would close an
  issue whose fix is sitting in an open PR with named defects, and the `cannot-reproduce` label
  would be true of production and false of the repository.

  This is not hypothetical: every PR in the 2026-10-20 queue (#410, #418, #419, #425) is an
  unmerged feature whose issue production cannot demonstrate either way. Most return `NO-REPRO`
  (exit 3) and are safe by accident; a feature that happens to have an executable `repro:` would
  have been closed.

  Granted 2026-10-08: five probes against live production, with varied inputs, is stronger
  evidence than any claim in a comment — and it is the same standard `project-manager` closes
  "does not reproduce" on. #156 and #157 sat open for weeks having been filed against a local
  tree.

  **Only on `CANNOT-REPRODUCE` (exit 1).** Never on `NO-REPRO` (exit 3) — that means the issue has
  no executable `repro:` and was never probed, so it is not evidence of anything. Never on
  `INCONCLUSIVE` (exit 4) — a prober that could not run has proved nothing, and an earlier
  revision of `validate_issue.py` crashed on every sample and confidently reported
  `REPRODUCES — deterministic`.

  The closing comment carries the command, all five samples with their status codes and inputs,
  and the date. Anything less is the #143 failure: closed as fixed while a fourth wrong date was
  still live.
- **Reproduces intermittently** → say so with the hit rate. Intermittent is a different bug from
  deterministic, with a different cause and a different fix, and conflating them wastes the cycle.
- **Reproduces differently** from the description → comment with both, label `needs-evidence`,
  return it to discovery rather than hand an engineer a stale premise.
- **Confirmed** → proceed.

One sample is not a validation. Five is the floor, with varied inputs where the issue takes any.

### `NO-REPRO` is not the same as `cannot-reproduce` — do not stop on it

`validate_issue.py` exits **3, `NO-REPRO`**, when the issue carries no executable `repro:` line.
That means *"this cannot be checked by an HTTP probe"*, not *"the problem is not there"*. Most of
this backlog is in that category: a tooling gap, a missing dimension in an export, an unsourced
rule, a refactor, an empty `seo_title` on 38 articles. None of them is a page you can curl.

Treating `NO-REPRO` as a stop blocked #272 on 2026-10-08 — the agent probed, got `NO-REPRO`,
reported honestly that *"there is nothing to sample on shubhagya.com"*, and ended the cycle with no
work done. The gate was written for bugs and applied to everything.

**So: on `NO-REPRO`, establish the premise some other way, say how, and proceed.** The obligation
is unchanged — *do not take the issue's word for it* — only the method is:

- A missing export dimension → run the fetch script and show the field is absent.
- A claim about the code → read it and quote the lines.
- A claim about content → count it (`grep -c`, the registry, the template).
- A claim about a gate or a workflow → run it, or read the run log.

Comment with whatever you used. A premise established by reading is still established; a premise
assumed because an issue asserts it is not. Stop only when you **cannot** establish it at all —
then label `needs-evidence` and move on.

## Step 1 — eligibility

```bash
uv run python scripts/verify_issue_evidence.py <n>
```

No Evidence Block, or a failing one → label `needs-evidence` and move on. An agent must not reach
an engineer on a guess.

**Issues filed before the Evidence Block existed are exempt**, provided you establish the premise
yourself under step 0 and record what you used. Every one of the 50 issues open on 2026-10-08
predates the convention; enforcing it strictly would mean the loop can never work any of them, and
a gate that blocks the entire backlog is not a gate, it is an outage.

**Bugs are exempt from `gsc:`/`ga4:`** — a broken feature needs no traffic thesis to justify
fixing. They still need `corpus:` and `tokens:`.

## Step 2 — rank

```
Agent(subagent_type="project-manager", description="Rank the eligible backlog",
      prompt="""Rank what to work on next in <cwd>. Staleness sweep FIRST, and probe with
scripts/validate_issue.py rather than reading titles. Rank only confirmed-live, evidence-complete
items. Read BACKLOG.md as a cache, not evidence. Read-only — propose closures, do not close.
STARTED WORK FIRST: an open issue with a merged partial/<n>- PR and no open PR outranks any
unstarted issue of the same or lower priority -- finish it, or say exactly which item of the
closed 'cannot do' list in agent-cycle.md Step 4 still blocks it.
THE 60/40 GROWTH SPLIT (owner, 2026-11-19): run python3 scripts/growth_split.py first and follow
'The 60/40 growth split' in your definition -- when must_pick_growth is true the top item is a
growth issue, unless production is broken. Quote today's split in your answer.""")
```

Take its top item. Never queue work another loop is already doing — check `AGENT_STATUS.md` and
live branches.

**Started work comes first — since 2026-11-06.** Measured that day: 38 PRs had been opened on
`partial/` branches, and 14 open issues carried `qa-pass` from slices that had merged. #518 had
three merged slices with about 27 articles still to route. Nothing ever came back to them. The
ranking had no preference for half-finished work, so every cycle started something new and the
backlog stayed at about 130 while the loop merged four PRs a day. When the top item has merged
partial PRs, read what each one said remains. Then do one of two things: **build what remains
and use `issue/<n>-` with `closes #<n>`**, or, if what remains is entirely on the closed list in
Step 4, comment that on the issue and move to the next item.

## Step 2.5 — check what a previous cycle already did, and continue from it

Cycles die. A token expires at sixty minutes, a job times out at a hundred and twenty, a quota
runs out. Starting from scratch each time is how the same work gets paid for twice — run
37749887640 spent $5.34 and 63 minutes on #270 and lost all of it, and a naive re-dispatch would
have spent it again.

Before dispatching anyone, establish what exists:

```bash
git ls-remote --heads origin "issue/<n>-*" "partial/<n>-*" "fix/<n>-*"   # a branch from an earlier cycle? (all three forms; see Step 4)
gh issue view <n> --comments                        # a design? a QA verdict? a failure?
gh pr list --repo "$GH_REPO" --head "<branch>"      # a PR already open?
```

Then:

- **A branch on `origin` with commits** (`issue/<n>-*`, `partial/<n>-*` or `fix/<n>-*`) — continue from it. `git switch` to it and carry on;
  do not start a parallel branch. The commits on it are real work that survived.
- **An architect design in the comments and no branch** — the design stands. **Skip the architect
  and hand that design straight to the engineer.** #270 carries a complete one: 18 i18n keys, EN
  output pinned to hash `04118625184f5800`, the token delta measured against the free tier. Paying
  for that analysis twice is waste, and a second architect may reach a *different* design, which
  is worse than waste.
- **An open PR** — push to its branch rather than opening another.
- **A QA verdict from a previous round, or a branch touching `.github/workflows/`** — follow
  "Shared by every mode" in `.claude/commands/agent-cycle.md`, which this run has already loaded.


**Say in your issue comment what you found and what you are reusing.** A cycle that silently
redoes finished work looks identical to one doing it for the first time, and the only way anyone
notices is the bill.

If you deliberately discard earlier work — the design was wrong, the branch is stale against a
moved `main` — say which and why. Discarding is a legitimate choice; discarding silently is not.

## Step 3 — build it

Follow `/bug` or `/feature` internals exactly, whichever fits. In particular:

The order, every build (owner, 2026-11-19):

```
[product-manager, features only] -> [astro-auditor / numerologist, rule files only] -> architect -> backend-engineer / frontend-engineer -> qa
```

- **`product-manager` first for a FEATURE** whose issue lacks a user story, checkable acceptance
  criteria or a success metric. A bug fix skips it. Measured 2026-11-19: 1 call in 365 cycles,
  so specs were being invented by whoever built them.
- `astro-auditor` **first** for any astrological constant; `numerologist` first for any numerological
  one. Before the code is written, not after. **Mechanically: if the change will touch `chart.py`,
  `muhurat.py`, `matching.py`, `panchang`/`festivals` tables or anything under `knowledge/`,
  dispatch `astro-auditor`; if it touches `numerology.py`, dispatch `numerologist`.** Their ruling
  goes to the architect.
- **`architect` on EVERY build, before any engineer.** It reads what else is changing in the repo,
  names the established pattern to follow, checks robustness, reliability, scalability and
  security, and returns ordered steps. A one-file change gets a short plan, never none.
  Measured 2026-11-19: architect ran in 6 of 365 cycles. See `architect.md`.
- **The build team follows the plan:** `frontend-engineer` for templates, CSS, client JS and the
  service worker; `backend-engineer` for routes, chart and rule maths, LLM paths, storage and
  scripts. A change spanning both is two dispatches, backend first. Pass each the architect's
  steps verbatim.
- **`qa` as a separate dispatch, always.** Verification by the reasoning that produced the change is
  not verification. This project has run fifteen QA passes and *every one failed its first
  submission*, twice on defects the fix itself introduced. Budget two or three rounds.
- **Run the cheap gates before EVERY `qa` dispatch, a re-QA after a fix included.** Commit, then
  `uv run python scripts/pre_qa_check.py`. It runs the pr-gates checks that need no network, LLM
  or server, plus the tests the diff touches. FAIL: fix and re-run. Exit 2: it did not run, which
  is not a pass. **Dispatch `qa` only on PASS.** Run 44020807802 (#1067) spent three rounds, and
  rounds 1 and 2 each failed only on a stale `ARCHITECTURE.md` count that
  `verify_architecture_counts.py` reports in seconds. A PASS here is not a verdict; it only means
  the round will not be spent on what a script could see.

### Dispatch in the FOREGROUND and wait. This is not a style preference.

Every `Agent` call in this cycle must pass **`run_in_background: false`**.

`Agent` dispatches in the background by default, and `claude-code-action` stops reading the moment
the parent produces its first `result` message. So a parent that dispatches an engineer and then
ends its turn **kills the engineer mid-work and exits `success`**. Three runs against #272 did
exactly that: dispatched, wrote an honest issue comment, ended at 7 of 150 allowed turns, and left
no branch, no commits and no PR behind a green tick.

Measured in run 37738950382: a foreground dispatch returned inline in 10.2s with real output; the
background one returned `Async agent launched successfully` instantly and its result arrived only
because that run stayed alive to receive it.

So: dispatch, **wait for the result**, read it, then dispatch the next role. A cycle is slow because
it is sequential — architect, then engineer, then QA, two or three rounds. That is the shape, and
rushing it by not waiting produces nothing at all. (Pass `qa` the architect's plan too: it checks
the diff against the plan as well as the issue.)

## Step 3.6 — push the branch as soon as the FIRST commit exists

Do not hold the work until the end. The moment the engineer hands back a commit:

```bash
git push -u origin issue/<n>-<slug>        # or partial/<n>-<slug> — see Step 4 for which
```

Then keep pushing after each subsequent commit — QA rounds included.

**Push after every commit anyway — the net is a net, not the plan.** As of 2026-10-25 the three
steps in `.github/workflows/agent-work.yml` that used to recognise only `issue/*` — the safety-net
step ("Push the branch and open the PR"), the "Report an unfinished cycle" summary and the loop
receipt — cover `issue/`, `partial/` and `fix/` alike. The net now refuses only `main` and a
detached HEAD, and asks the question it was always meant to ask: *are there commits here that
would be lost?*

Until then a `partial/` branch hit a `case` on `issue/*`, was told "Cycle shipped nothing", and was
**discarded unpushed** inside a runner about to be destroyed — the exact loss this step exists to
prevent, in the namespace that needed it most.

**Why, measured:** the GitHub App token the action gives you **expires after one hour**. Run
37749887640 spent 63 minutes on #270 — architect, engineer, QA — produced a complete branch, and
died at the push with `Invalid username or token`. 25 turns and $5.34 of finished work, lost,
because it was all still on a runner that was about to be destroyed. The earlier cycle that
produced PR #292 took 19 turns and pushed inside the hour, which is the only reason it survived.

A pushed branch survives the runner, the token and the job timeout. An unpushed one survives
nothing.

Open the PR as soon as the branch is pushed, in draft if QA has not run yet, and let the later
pushes update it. A PR that exists and is not ready is recoverable; work that never left the
runner is not.

## Step 4 — branch and PR

Two branch forms, and the choice is made by whether the PR **fully closes** the issue.

**The name no longer decides whether it can merge** — changed 2026-10-25. `agent-merge` gates on
the PR's **author** (`AGENT_AUTHORS`), so both forms are merged by the loop on the same evidence:
gates green on the head SHA, `qa-pass`, no `qa-fail`, inside the size limit, no trust-boundary
path. What the name still decides is whether the **issue** closes, which is a different question
and the only one a name was ever able to answer.

| | branch | PR body | what happens at merge |
|---|---|---|---|
| fixes every acceptance criterion | `issue/<n>-<slug>` | `closes #<n>` | `agent-merge` may merge it (provenance permitting); `close-on-evidence` may close the issue after verifying production |
| acceptance criteria remain that are on the closed "cannot do" list below — nothing else | `partial/<n>-<slug>` | `refs #<n>`, plus what remains | `agent-merge` may merge it on the same evidence; **nothing closes the issue** — `close-on-evidence` and the merge comment both read `^issue/<n>` and find nothing, which is correct while work remains |

**So choose the name by what is left to do, never by what you want to happen to the PR.** Naming a
finished fix `partial/` leaves its issue open forever; naming an unfinished one `issue/` closes an
issue whose acceptance criteria are not met. Between 2026-10-21 and 2026-10-25 the name also
silently decided mergeability, and every `partial/` PR in that window — #480, #482 and #487 among
them, each carrying `qa-pass` on green gates — waited for a human. That is the coupling this change
removed.

### "The loop cannot do it" is a closed list — since 2026-11-06

**`partial/` is right ONLY when what remains is on this list:**

1. **An act only the owner can take** — the five in CLAUDE.md's `chief` table: authoring a file
   under `.github/workflows/`, removing a pinned safety or grounding line, granting a scope or
   secret, a product or revenue decision, a legal or privacy commitment. **Editing `.claude/` is
   no longer on it** (owner grant 2026-11-06): improve a definition in the PR when that is what
   the issue needs.
2. **A source the corpus does not have.** Use `corpus_search.py --absent`, and say which books were
   present (CLAUDE.md: an absence measured against a partial corpus is worthless).
3. **A ruling from `chief` that has not been given yet**, on a question you raised under Step 4.5.

**Not on the list, and each one has been used as a reason:**

- **"The file is in the trust boundary."** You may edit `prompts/`, `knowledge/`, `notify.py` and
  the rest. The boundary holds the MERGE for `chief`; it does not stop the edit. #717 left
  `prompts/matching.txt` undone as "trust boundary, chief's". That was wrong: the change belonged
  in the PR, and chief rules on the PR.
- **"It will not fit this cycle."** If the issue is too large for one cycle, split it into GitHub
  **sub-issues** (one per independently shippable part, each with its own acceptance criteria)
  and close them one by one with `closes #<sub>`. The parent closes when its last sub-issue does.
  A `partial/` slice of a parent that never closes is how #518 reached a fourth slice. The
  one-hour token is a reason to **push early** (above), not a reason to **stop early**: push the
  branch as a draft and keep working on it.
- **"The metric can only be measured after deploy."** The Evidence Block's `metric:` and any
  "N days after deploy" criterion are **post-ship measurements**, not acceptance criteria a PR can
  meet. #508 shipped every buildable change and stays open forever, because its metric is a 28-day
  click-through rate. When everything a PR *can* deliver is delivered, write `closes #<n>`. The
  `analyst` scores closed issues against their thesis afterwards; if the metric fails, that is a
  new finding, not a reason to keep this issue open.
- **"A disclosure fix ships today, the value later."** That is two issues. Ship the disclosure
  with `closes` on a sub-issue that says so, and leave the value question as its own issue, where
  it ranks on its own evidence.

**The last slice closes.** When your PR delivers what earlier `partial/` PRs said remained, it is an
`issue/<n>-` branch with `closes #<n>`, whoever did the earlier slices.

```bash
git switch -c issue/<n>-<slug>             # or partial/<n>-<slug>
git push -u origin issue/<n>-<slug>        # or partial/<n>-<slug>
gh pr create --base main --title "<what changed> (#<n>)" --body "closes #<n>

<the rest>"                                # partial: `refs #<n>` instead of `closes #<n>`
```

**`closes #<n>` must be in the PR BODY, and `--fill` will not put it there.** `--fill` takes the
body from the commit messages, which name the issue but do not use a closing keyword.

This stranded #304 on 2026-10-09. PR #312 was titled *"Lift the learn sticky CTA above the
mobile tab bar (#304)"* — a **mention**, not a claim. It merged, production verified it, and
`close-on-evidence` ran, concluded success and closed nothing: *"PR #312 claims no issue"*. A
green run that did exactly nothing, which is this system's signature failure.

`close-on-evidence` now also falls back to the `issue/<n>-` branch name, so forgetting this no
longer strands an issue. Write it anyway — the keyword is what makes the link visible on
GitHub to a human reading the PR, and the fallback is a net, not the mechanism.

**That is the only `git push` in this system, and it is to a branch.** A push to `main` is the
deploy, there is no staging, and production is the first place code runs. `agent-merge` decides
what lands, on green gates and a QA PASS.

If you find yourself pushing to `main`, or routing around a refusal, stop and file
`needs-human-review`.

**The table above is the rule; this is the reason.** A PR for a PARTIAL fix must not carry
`closes #<n>` and must not use an `issue/<n>-` branch.
`close-on-evidence` falls back to the branch name when the body has no closing keyword, so
`issue/<n>-…` alone is enough for it to close an issue the PR only half-delivered. Name a partial
branch `partial/<n>-<slug>`, say in the body what remains, and reference the issue as `refs #<n>`.

Note what this costs you now and did not before: the name used to be load-bearing twice over, and
a `partial/` name bought you a human reviewer. It no longer does — `agent-merge` gates on
authorship — so the branch name's **only** remaining job is to keep `close-on-evidence` off an
issue that is not finished. If a slice needs a human to look at it for some other reason, say so
with `needs-human-review`, which the sweep and the label check both refuse. Do not reach for a
branch name to express it.

## Step 4.5 — blocked on a CHOICE, not on a conflict? Escalate to `chief`.

**Do not label `needs-human-review` because a decision is needed.** That label is for work
you cannot establish, not for work you can establish and are not authorised to choose
between. Using it for a choice is how decisions queue up on the human while the PR sits.

Measured 2026-10-10: cycles on #322 and #323 each reproduced the defect from inside their
own run — one of them finding the bug was wider than the issue claimed — then stopped
after 60 seconds with `needs-human-review`, because every fix option lived in
`.github/workflows/` and choosing between them was nobody's authority. Two correct stops
that shipped nothing, and two decisions parked.

`chief` holds **Standing ruling 4**, a precedence written for exactly this: free tier,
then minimum permissions, then robustness over brevity, then minimum code, then minimum
entropy, then the objective. So escalate, in **Shape B** — a decision request. Dispatch
`chief` as a subagent with `run_in_background: false`, and give it:

- **the enumerated options**, each with what it changes, what permission or credential it
  adds, and roughly how many lines. An option with no cost stated is not an option
- **what is blocked**, and since when
- **the Evidence Block**, or an explicit note of which fields do not apply and why
- **the issue number**
- **your own recommendation and reasoning**

Ask it to rule under Standing ruling 4 and to name the clause that decided it.

Then **implement what it rules**, and quote the ruling in your issue comment. If it
returns `insufficient-evidence` it will say what an acceptable option would have to look
like — go and find one, or then label `needs-human-review` with its words attached.

Three things this does not do:

- **It does not give you a third option.** `chief` may not invent one, and neither may you
  by reading a ruling loosely. If every option loses, say so.
- **It does not exempt the result from the gates.** `verify_no_relaxation.py` runs on your
  PR regardless of who ruled, and `chief` is explicitly forbidden from ruling that a
  guardrail should be relaxed.
- **It is not for two options you invented to look thorough.** One real option and one
  straw man wastes a full agent invocation. Offer what you would actually build.

**Three escalations per cycle, maximum** — `chief`'s own limit. A fourth means the issue is
underspecified, and *that* is `needs-human-review`.
