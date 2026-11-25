# CLAUDE.md — working agreements for this repo

Shubh Bhagya (shubhagya.com) — Vedic astrology web app. FastAPI + Jinja2, Python ≥3.12,
managed with `uv`.

This file is the rules. The measurements, incidents and dated history behind them moved
verbatim to `docs/claude-md-history.md` (2026-11-17), under the same headings. Read it before
changing or arguing with a rule here.

---

## ⚠️ Pushing to `main` deploys to production

**A push to `main` triggers a Cloud Build → Cloud Run deploy of the live site.** There is **no
staging environment** and the behaviour suite (`uv run pytest`) covers request paths only. A
push is the deploy, and production is the first place code runs.

- **A push touching only `measurements/` builds nothing** (trigger
  `rmgpgab-bhagya-asia-south1-mahAnuj-astro-ai--mapzk`, `ignoredFiles: measurements/**`). A push
  mixing `measurements/` with anything else still deploys.
- **Measurement loops land through a PR via `scripts/publish_measurements.sh`, never a direct
  push** (`main` is branch-protected). It publishes **only `measurements/**`** and refuses
  anything else at exit 2, including `measurements/../src` — keep that boundary, because
  `pr-gates` skips the suite and all 29 gates on a measurements-only diff. **`allow_auto_merge`
  must stay on** or every measurement PR stays open forever, silently. Their
  `measurements/<run-id>-<attempt>` branches are short-lived; never name them `feat/**`.
- **Rename or relocate `measurements/` only together with the trigger**
  (`gcloud beta builds triggers export|import --project bhagya-500701`), or measurement commits
  silently deploy. **Put nothing load-bearing under `measurements/`** — it never ships.
- The trigger is GCP-side; there is no `cloudbuild.yaml`. **`verify-production.yml` is NOT that
  trigger.** Do not conclude "no CI" from the absence of a build config.

**`verify-production.yml` is the one check that runs against production.** Read its header
before adding a check. A green run means production satisfies those invariants **now**.
- `/health` returns `{"ok", "revision", "build_sha"}`. `build_sha` equal to the commit proves
  *this commit* is live; null proves only that *a* new revision landed.
- The trigger passes `BUILD_SHA` with **`--update-env-vars`, never `--set-env-vars`** (set wipes
  the Groq keys and the rest of the environment).
- The path is `/health`, **not** `/healthz` (Google intercepts it). Do not "fix" it.
- Its push filter is a **`paths-ignore` list, never a `paths:` allow-list**, derived from what
  the Dockerfile copies (`pyproject.toml`, `uv.lock`, `README.md`, `src/`). **The pattern is
  `*.md`, never `**.md`**, which would exempt `src/astro_ai/knowledge/*.md`. `remedies.md` §5.1
  and §7.1 are read at runtime (`knowledge_lookup.py`, #399); the system prompts are
  `src/astro_ai/prompts/*.txt` via `routes/deps.py` `PROMPTS_DIR`.
- A skipped run closes no issue, so a docs-only fix closes via `/prioritise`.
- The sweep probes **one** `/rashifal/{rashi}` page per weekly run, rotating by ISO week (~3,330
  input tokens per cache miss), and asserts on the `<div class="speakable-body` **div**, never
  on page size or the bare class name.

Why and history: docs/claude-md-history.md#push-deploys

### Rules for agents

- **Never push work that has not passed QA.** This is the rule everything else here
  protects. In the `/feature` and `/bug` loops, the engineer that wrote the code does not
  push it, and neither does the dev-lead.
- **Subagents dispatched inside a session still never push.** No engineer, architect or QA
  dispatched by a `dev-lead` may run `git push`. Commit locally and hand back.

#### The autonomous loop may push and merge — granted by the user 2026-10-08

The user's words, verbatim: *"we should not restrict git push and merge for this autonomous
system to be successful, let's update the rules. If QA is passed, push and merge."*

So `/agent-cycle`, running unattended in `.github/workflows/agent-work.yml`, **pushes its
branch and merges its own PR once QA passes.** This extends the 2026-08-16 standing
permission from the top-level session to the loop. What has NOT changed:

- **`pr-gates` still decides** (21 gates, the behaviour suite, `mutate_behaviour_suite.py`,
  `verify_rule_citations`). **Branch, then merge — never a direct commit to `main`.**
- **`qa` applies its own verdict label** under `qa.md`: comment first, one label clearing the
  other, no `qa-pass` wherever `qa.md` forbids a PASS. Each verdict carries provenance,
  `qa:independent` or `qa:in-cycle`. **`qa-pass` is the sole merge trigger.** `steward` may touch
  neither label.
- **Every QA label is written by `scripts/qa_verdict.sh` and by nothing else.** It binds a PASS
  to the SHA examined; a PASS clears an earlier `qa-fail` — only a QA round may clear one.
- **`qa-pass` counts only for the commit it was given on**: `agent-merge` also needs a
  `QA: PASS` comment by `claude[bot]` or the owner whose first line names the head SHA. A `main`
  merge into a passed PR needs a new QA round.
- **Trust-boundary PRs are held for `chief` (#354)**: `agent-merge` labels `needs-human-review`
  on any change to `src/astro_ai/prompts/`, `src/astro_ai/knowledge/`, `.github/workflows/`,
  `events.py`, `notify.py`, `email_sender.py` or `storage.py` (`TRUST_BOUNDARY` in
  `agent-merge.yml`).
- **Merge scope is the PR's AUTHOR, not its branch**: `AGENT_AUTHORS` = `claude[bot]`,
  `github-actions[bot]`, `shubhagya-publisher[bot]`, the repo owner. **To hold a PR out of the
  unattended path, use `needs-human-review`**; a branch name holds nothing back (its one job is
  keeping `close-on-evidence` off an unfinished issue). The steward dispatches on the same test
  plus an owning issue the detector named, refusing only `.github/workflows/**` diffs and
  outside authors.
- **When a rule is restated in prose for agents to read, grep for every copy before believing a
  fix is done** — the author rule lived in six places.
- **`qa-on-green.yml` dispatches a QA round when gates go green** (a `qa-fail` PR, held or not,
  only once a fix has landed since the FAIL; judge-only, never a clearance). **Its aim comes from the branch name,
  never from the PR body**; a `.github/workflows/**` diff is judged, not refused. **One dispatch
  per head commit, marker comment written before the dispatch. It must never write a label**
  (`tests/test_qa_on_green.py`). Do not wire the steward to `pr-gates`.
- **The loop fixes session PRs too** (owner, 2026-11-13: *"let the loop fix session PRs too"*):
  `fix_pr=<n>` fixes exactly the findings and writes **no verdict**; **at most three per PR**,
  one per head, never a `.github/workflows/` diff, never a fork.
  `docs/decisions/2026-11-13-loop-fixes-session-prs.md`.
- **Every dispatch is QUEUED, and `agent-queue`'s drain is the only worker** (#1185;
  `scripts/cycle_queue.py`, `agent-queue.yml`). A handler appends an entry keyed (kind, target,
  head) and wakes the drain; it never starts `agent-work` (`tests/test_inbox_single_worker.py`).
  The drain starts one entry per free lane and folds the target's other entries into that run, a
  fix before a QA request. Only `github-actions[bot]` entries count; never drain from inside
  `agent-work`; the queue writes no label and needs no new permission. **An hourly backstop**
  (#1186) fires due timers into the queue (`scripts/timers.py`, #1187), drains, chains, and files
  `scripts/liveness.py` findings. **A heartbeat keeps one `agent-queue` run always on its way**
  (`scripts/heartbeat.py`, 2026-11-20): GitHub's cron is not a clock, so never rely on it to
  restart an idle lane. **A rearm never dispatches over a waiting run** — that would cancel it. Lanes are told apart by the run title "QA round: PR #<n>" —
  change it only with all three copies (`tests/test_cycle_queue.py`).
  `docs/decisions/2026-11-17-always-on-inbox-timers.md`.
- **At least 60% of build cycles go to growth, against goals chief sets** (owner, 2026-11-19:
  *"split everyday work into 60% growth and 40% other work ... CEO should monitor if weekly goals
  are met"*). `project-manager` runs `scripts/growth_split.py` before every ranking and picks a
  growth issue when `must_pick_growth` says so; production breakage is exempt and goes first.
  `chief`'s **Sunday** review (weeks are Mon–Sun, IST) posts weekly, monthly and quarterly goals
  on the `weekly-goals` issue; `/admin/ops` meters them.
  `docs/decisions/2026-11-19-growth-goals-and-split.md`.
- **Chaining and parallelism are read from `measurements/claude_usage.json`, not argued.**
  `scripts/chain_cycle.py` chains only under 70% weekly use, fresh and `allowed`, **and on or
  behind the weekly pace** (elapsed share of the week x 70% + 5%; 2026-11-25), at most 30 build
  runs a UTC day as a backstop, queue first. All agents share one Claude Max 5x subscription.
- **The loop learns from its own errors, outcomes and rivals** (owner, 2026-11-06: *"a
  continuous feedback loop from their own actions and as well as from researching other
  websites"*). Build cycles, discover and prioritise read `measurements/lessons.md` before
  choosing work. **A rival may shape what we build, never what we assert**: no astrological
  claim is copied from a competitor.
- **New mutation rows go in `scripts/mutations/<area>.py`, never in the central table** — one
  literal `MUTATIONS = [...]` per file, never a shared `misc.py`. The mutation sandbox must keep
  excluding `.claude/worktrees/`.
- **A PR that has not merged yet is not a PR that was refused** — a merge can arrive up to 30
  minutes after the gates go green (#357), longer when GitHub throttles the `*/30` cron. Check `gh run list --workflow=agent-merge.yml` first, and **never re-push to force a
  new edge.**

If this permission is ever narrowed again, edit this block rather than relying on the
conversation — the same instruction the 2026-08-16 grant carries, for the same reason.
- **Do not infer standing permission from a previous push.** One approval is not a
  policy — only the explicit grant recorded below is.

Why and history: docs/claude-md-history.md#loop-push-merge

#### `chief` decides every `needs-human-review` PR — granted by the user 2026-11-01

The user's words, verbatim, across three messages: *"why can't chief grant merge authority,
that is what chief is for. Chief should have privelege to do anything even on my behalf, give
that power to chief agent"*; *"do not hold chief for TRUST_BOUNDARY as well. I want the loop
to not hold on me"*; *"anything that is labeled as needs-human-review, should be decided by
chief"*.

So **`needs-human-review` no longer means "the owner decides". It means "`chief` decides".**
For every boundary path. What the grant does NOT include:

- **It clears a HOLD, never a VERDICT.** `gates`, `qa-pass` and `size` must still pass;
  `qa-fail` still refuses.
- **The clearance is SHA-BOUND and the ruling comes first**: a comment containing
  `chief-cleared at <full head sha>`, then the `chief-cleared` label; both required; it does
  not survive a push.
- **Code applies the labels, not chief**: chief writes `pr=<n> sha=<head>` to
  `/tmp/chief-clear.txt` and `scripts/chief_clear.py` re-checks every precondition. A PASS
  carrying only `qa:in-cycle` cannot be cleared; chief dispatches the independent `qa` round
  first.
- **Irreversible actions still stop and ask** — data migration, destructive storage, anything
  touching subscriber records.
- The App token has no `workflows` permission (#421): `chief` can **merge** a
  `.github/workflows/` PR and cannot **author** one.

**`chief` owns the queue, not just the decision — granted the same day.** The user's words:
*"go ahead and also give chief the [authority] to own such issues/blockers"*. Every PR and issue
carrying `needs-human-review` is `chief`'s queue, and **the list of things it may hand back to
the owner is closed**:

| # | The act | Why no agent can do it |
| --- | --- | --- |
| 1 | Authoring a file under `.github/workflows/` | The App token is refused the `workflows` permission (#421) — the push is rejected. Merging such a PR is NOT on this list: `agent-merge` merges with `github.token`. |
| 2 | Removing a pinned safety or grounding line from `.claude/` | `verify_no_relaxation.py` is red on it by construction (its `REQUIRED_SUBSTRINGS`). Editing `.claude/` is otherwise NOT on this list since 2026-11-06; see the grant below. |
| 3 | Granting a scope, a secret or a permission | `verify_workflow_permissions.py` is red on it by construction, and a red run of it is never `chief`'s to rule on. |
| 4 | A product or revenue decision | Which school a reading follows, whether a feature ships, what is charged for. |
| 5 | A legal, licensing or privacy commitment | #279, and any copy promising a user something about their data. |

Anything not on that list is `chief`'s, and *"ask the owner"* is not an available ruling. When
`chief` does route one, it names which of the five and states the owner's single act in the
first sentence — *"merge PR #631"*, not *"this needs a human"*.

`scripts/verify_workflow_permissions.py` backs this grant: `permissions:` may not widen and
`TRUST_BOUNDARY` may not lose an entry.

If this permission is ever narrowed again, edit this block rather than relying on the
conversation.

Why and history: docs/claude-md-history.md#chief-grant

#### Agents may edit their own definitions — granted by the user 2026-11-06

The user's words, verbatim, across three messages: *"I want to give freedom to agents to edit
their own definitions as well if that helps meet the objective that I have set"*; *"my main
objective is to increase the user base for shubhagya.com while ensuring fully grounded astrology
on rules"*; *"I want to accelerate the changes speed without waiting for anyone, if that meet the
objective of increasing user base while keep astrology 100% true"*.

So **any agent may edit `.claude/agents/` and `.claude/commands/`**, its own definition
included, when the change serves `OBJECTIVE.md`, through the normal path (gates green, a
`QA: PASS` bound to the head; no chief hold). Not covered:

- **Improving how you do your job, yes. Widening what you are allowed to do, no.** Nothing that
  lets an agent merge, close, apply or clear a QA verdict, push to `main`, skip or weaken a
  gate, or assert an astrological rule without a `knowledge/*.md` source. Those lines are
  pinned in `scripts/verify_no_relaxation.py`; removing one is the owner's act #2.
- **Cite the measured problem in the PR**, never a sentence its author wrote.
- **`CLAUDE.md` is not covered.** The standing rules stay a session or owner edit.
- A Claude Code session may still need the owner to approve exact `.claude/` text (a harness
  setting, not a repo rule).

If this permission is ever narrowed again, edit this block rather than relying on the
conversation.

Why and history: docs/claude-md-history.md#self-edit-grant

#### Standing permission for QA'd work — granted by the user 2026-08-16

The user's words, verbatim: *"if an issue is QAed, just push and merge and close"*.

So, for the **top-level session only**: once an issue's fix has genuinely passed QA, push
and merge it without asking again, and close the issue with evidence.

- **"QAed" means independently verified** — an independent QA agent passed it, or, where none
  is available, it was verified by execution against a running server with the claims measured
  and the gaps stated. Verification by the same reasoning that produced the change is not QA.
- **Closing still needs production evidence.** Push, wait for the deploy, verify against
  production, then close with the numbers. Do not close on a merge.
- **Anything that has NOT passed QA still stops and asks**, exactly as before.
- If a change is irreversible in a way a revert would not undo — data migration, a
  destructive storage operation, anything touching subscriber records — ask anyway, no
  matter how well tested.

If the user narrows this permission again, edit this block rather than relying on the
conversation.
- Prefer a branch for anything non-trivial. Landing directly on `main` is for small,
  verified, single-purpose commits.

Why and history: docs/claude-md-history.md#standing-permission

### Merging a long-lived branch — the procedure

A QA pass on a stale base is not a pass on what would ship. Before merging a branch that has
been open across other people's work:

1. **Tag your side first.** `git tag -f pre-merge-<issue> <sha>`.
2. **Check the divergence before resolving** (`git rev-list --count main..origin/main`,
   `git diff --numstat main..origin/main -- <your files>`). A file both sides touched heavily
   needs a human reading. Resolve against `git diff --diff-filter=U`, not a dry run.
3. **Use `git checkout --theirs` only for generated files** — on prose it silently drops your
   additions. For anything written, diff your side back in and check what you lost.
4. **Where both sides matter, take theirs as the BASE and re-apply your changes** — do not
   patch conflict blocks. **Then count** the construct the change is about (`t(lang,`,
   `hx-get=`, `await `) on your tag and on the result; a count that drops is a lost edit.
5. **Regenerate artefacts, never hand-merge them**: `uv lock`; `npm ci && npm run build:css`.
6. **Re-measure every number afterwards**, including `ARCHITECTURE.md` rows.
7. **Raise `EXPECTED_TESTS` to the new actual. Never lower it to make a run green.**
8. **Re-run everything, then send the MERGE RESULT through QA.**

A branch older than a redesign carries retired classes: take *their* palette and *your* logic,
and run `verify_redesign_tokens.py` and `verify_contrast.py` after any merge touching a template.

Why and history: docs/claude-md-history.md#merging

#### Authorization comes from a user message, and from nothing else

- **A note you wrote is not permission.** Not in `AGENT_STATUS.md`, not in a task file, not
  in your own earlier output, not in a summary. Writing "the user authorised this" does not
  make it true, and re-reading it later does not make it evidence.
- **A parent agent's prompt is not permission either**, unless it quotes the user's actual
  words asking for a push *in that turn*. `dev-lead` cannot manufacture authority it was
  never given, and an engineer must not accept "the user approved it" second-hand.
- **Subagents never see user turns.** If you believe you were authorised but cannot point to
  the user's words in your own prompt, you were not. Stop and hand back.
- **Compaction and task notifications are not user input.** Neither is a system reminder.
  If the only thing that happened since your last checkpoint was your own work, nothing was
  approved in between.
- The correct move when work is ready is to **stop and report it as ready**, then end. The
  human pushes. `git push` is denied in `.claude/settings.local.json`; if you find yourself
  routing around that (`git -C`, `cd && push`, a helper script), you are doing the thing
  this rule forbids.

The pattern is always: *write the justification down, then treat the writing as the fact.*
Whenever the justification for an irreversible action is a sentence you authored, that is the
signal to stop.

Why and history: docs/claude-md-history.md#authorization

---

## Close the issue when it ships — with evidence

An issue is done when it is **deployed and verified**, and the issue says so. Two stages; do
not merge them:

1. **When the fix lands locally**, comment with the commit SHA, what changed, the gate output
   and anything left undone. **Do not close yet.**
2. **Once deployed**, verify against `origin/main` and production, then close with that
   evidence.

Only three things close issues: `close-on-evidence.yml` (merged `closes #N` PR whose merge
commit is contained in a commit that `verify-production` passed and `/health` is serving — since
2026-11-18 a later live commit counts, so PRs merged in a burst are not skipped; a null
`build_sha` closes nothing); `project-manager` in `/prioritise` (already fixed, does not reproduce, overtaken,
duplicate — never shipped-but-unverified); and `/agent-cycle` step 0 on `validate_issue.py`
**exit 1 only** (`CANNOT-REPRODUCE`), never exit 3 or 4. **The engineer, dev-lead, QA and
architect are still denied `gh issue close`.**

- **A closing comment must let someone else check you**: the command, its output, the SHA.
  "Fixed" is not a closing comment (good examples: the #144, #157 and #154 closes).
- **Do not close on a claim.** Verify against `origin/main`, not a comment saying it was fixed.
- **Partial work does not close.** Comment with what landed and what remains.
- **When an issue turns out not to be real**, close it with the counter-evidence and say what
  would make it real.
- **Related issues:** say so on both; close one the fix makes obsolete.

Why and history: docs/claude-md-history.md#close-issue

## Verify before you claim

1. **Never report a subagent's output you did not actually receive.** "Still running" and
   "no output yet" are complete answers. Do not reconstruct a spec, a table, or a result
   from memory and present it as delivered work — that is how invented data enters the
   codebase.
2. **Verify data before shipping it, especially dates.** Any almanac date, festival date or
   muhurat window must be checked against a real source, and the source recorded in a comment
   next to it.

When you cannot verify something, say you could not. When you cannot source a requirement,
ask where it came from rather than concluding it was fabricated — agents cannot see the
user's turns, only the prompt they were handed.

Why and history: docs/claude-md-history.md#verify-before-claim

---

## Report status while you run

Background agents are opaque from the outside — the user sees "3 agents running" and
nothing else. Every agent must leave a visible trail.

### The three surfaces, and what belongs on each (#607)

| surface | holds | lifetime |
|---|---|---|
| **the issue** | the **durable decision record** — what was decided, why, what was rejected, the corpus citation, the measured token cost | outlives the PR, the branch and the run |
| **the PR** | the **review comment and status** — what a reviewer needs at the point of review: what changed, the verdict, what remains, the gate output | as long as the PR |
| `AGENT_STATUS.md` | the **local heartbeat** only, so a watching human sees progress | this machine, this session |

`AGENT_STATUS.md` is gitignored. **Nothing written there leaves this machine**, so it is not
the record and a line in it is not evidence. Append one line to it at every meaningful step
(start, design done, dispatch, return, writing files, commit, blocker, finish) — in addition to
the issue comment, never instead of it, and never batched. **Never type the timestamp
yourself**; use exactly this form, `>>` only (never `>`, Write or Edit — agents append
concurrently):

```bash
printf '%s  dev-lead #132  registry engineer returned; wiring route next\n' \
  "$(date +%H:%M)" >> AGENT_STATUS.md
```

Dev-leads also append a one-line roster (`live: architect(design), engineer-1(hub route)`)
whenever the set of live subagents changes. Keep lines short.

Why and history: docs/claude-md-history.md#report-status

---

## Architecture and past decisions — read `ARCHITECTURE.md` before designing

It holds the deploy path, the cache layers, the free-tier constraints, the LLM chain and the
decision log, including rejected proposals. **Update it in the same commit as the change it
describes.** **A new DECISION goes in its own file, `docs/decisions/YYYY-MM-DD-<slug>.md` —
never a new row in `ARCHITECTURE.md` §10** (frozen after 2026-11-09; format in
`docs/decisions/README.md`).

Why and history: docs/claude-md-history.md#architecture

## The agent team

`.claude/agents/` holds **14** roles. For implementation: `project-manager` (what next, across
the backlog), `product-manager` (what this one feature should be — first on any feature without a
spec), `architect` (**plans every build change** before any engineer: steps, the established
pattern, robustness, reliability, scalability, security — owner, 2026-11-19), `dev-lead`
(coordinates one issue, commits locally), `backend-engineer` and `frontend-engineer` (the build
team: write it following the plan, exercise it, hand it back unpushed), `qa` (verifies
independently by execution, against the issue and the plan, traces claims to `knowledge/*.md` and
`data/`), `astro-auditor` and `numerologist` (are the RULES correct — dispatched first on any
rule-file change), `seo-growth` (search and funnels, first step of Monday's `/discover`), and
`steward` (woken only by `scripts/detect_stalls.py`; may not merge, close, push, apply a QA
verdict, or edit its own rules). The rest run on their own workflows or are called by chief.
Every agent file needs a card in `agent_status.AGENTS` (`tests/test_agent_status.py`).

**The engineer that wrote the code never verifies it and never pushes it** — `qa` is a separate
dispatch with its own context. Every agent file repeats the never-push rule, deliberately.
`.claude/settings.local.json` **does not exist in the tree**, so no `git push` deny is in
place; the rule rests entirely on the agents honouring it.

Why and history: docs/claude-md-history.md#agent-team

## Token budget — the free Groq tier is the ceiling every role designs against

**Quota is keyed PER MODEL, not per key**: 8,000 TPM per model, and the daily rashifal path
has been observed against a 200,000 TPD limit. The chain is `BHAGYA_LLM_PROVIDERS=groq120,groq20`. `openai`
at the end is a **paid-tier safety net**, not free and not a capacity plan.

**Every role owes the same answer before work lands: does this fit in the free tier, and what
is the number?** `product-manager`: a feature over budget is **unbuildable as specified**.
`architect`: state tokens per call and per day; put the shared prompt prefix first.
`backend-engineer` / `frontend-engineer`: measure, before and after, as numbers. `qa`: an unmeasured token claim is a FAIL.
`dev-lead`: nothing passes without the number.

### When it does not fit, say so — do not silently spend

- **First, move the generation out of the request path** (owner, 2026-11-06: *"guide agents to
  use claude code sessions if possible where we think are limited by Groq budget."*): content
  the same for every visitor is generated in a scheduled Claude Code job and served from cache;
  Groq per-request calls are for what is personal. Size the job to
  `measurements/claude_usage.json`.
- **Adding a model is a proposal for the human**, never an agent's decision. Ruled out: `groq`
  beside `groq120` (same model, one bucket); `groq_qwen` (cannot be bounded); `groq/compound`
  and `compound-mini` (agentic, can browse — only behind review).
- **Verify a model exists** (`GET /openai/v1/models`) before adding it: `_chain()` keeps a
  decommissioned model whose key is set.

**When the budget does not fit, the output is a stated finding** — what it needs, what the
chain can serve, which model would have to be added. Never quietly widen the prompt and let
the chain fall through.

Why and history: docs/claude-md-history.md#token-budget

## Backlog state lives in `BACKLOG.md`

`/prioritise` reads it before scanning and rewrites it after. It is a **cache, not evidence**:
a row is a pointer, never grounds to skip the check, and a `checked@` em-dash was never
re-verified. Never restamp a carried-forward verdict with a newer SHA.

Why and history: docs/claude-md-history.md#backlog

---

## Layout

```
src/astro_ai/
  main.py          FastAPI app + every route (large; edit surgically, re-read before editing)
  chart.py         Swiss Ephemeris chart computation, panchang, dashas
  muhurat.py       Muhurat scoring; shares tithi/nakshatra/yoga/karana with panchang
  festivals.py     Festival calendar (date-keyed). Feeds emails + rashifal LLM prompt
  events.py        GCS event log. EVENT_RETENTION_DAYS = 30 — recent() clamps to it
  storage.py       GCS blob read/write. No prefix listing — you cannot enumerate blobs
  profiling.py     Admin audience aggregation (/admin/insights)
  intents.py       stdlib-only regex question-intent classifier
  llm.py           Provider-agnostic LLM calls (OpenAI-compatible)
  knowledge/*.md   Classical Vedic source texts — the authority for astrological claims
  prompts/*.txt    LLM prompt templates
  templates/       Jinja2. learn/ (76 articles), email/, admin_*.html, panchang.html
```

### Source books in `data/` — read `knowledge/SOURCES.md` before searching

- **Use `scripts/corpus_search.py`, not grep** — it expands transliterations, and `--absent`
  makes "unsourced" checkable.
- **A zero proves the TERM is absent, not the CONCEPT.**
- **`data/` is gitignored, so a fresh checkout may hold a subset.** An absence measured against
  a partial corpus is worthless. **Say which books were present** whenever you report one.
- Cite work and chapter; never paste pages.

Why and history: docs/claude-md-history.md#source-books

### Things that are easy to get wrong

- **`main.py` is huge and concurrently edited.** Re-read the region immediately before
  editing; never edit by remembered line number.
- **`events.py` keeps 30 days.** Longer history needs its own persisted aggregates.
- **`storage.py` cannot list by prefix.** "Scan all blobs" needs an explicit index blob.
- **Never do per-request GCS reads on a hot path.** The bucket is in the US and Cloud Run in
  `asia-south1`, deliberately (free tier); do not propose relocating it. Cache in-process
  (`hot_cache`), memoise, batch or parallelise.
- **`festival_for_date()` returns only the FIRST festival on a date**; use
  `festivals_for_date()` when a shared date must show all of them.
- **Do not create a parallel page type for festival or muhurat queries** — `/learn` already has
  them. New long-form content goes through the `/learn` pattern.

Why and history: docs/claude-md-history.md#easy-to-get-wrong

---

## Running locally

```bash
uv sync
uv run astro-ai      # http://127.0.0.1:8000, auto-reloads
```

Requires `.env` (copy `.env.example`). `OPENAI_API_KEY` is the only hard requirement.

Why and history: docs/claude-md-history.md#running-locally

### The palette: `bhagya`, not `astro`

`base.html`'s REDESIGN CANONICALS block says which colour may go on which surface;
`scripts/verify_contrast.py` checks it.

- **Gold and saffron never touch a light surface.** They are fills and ornaments there, never
  text.
- **A translucent text utility must be declared** in `DECLARED_PAIRS`.
- **Never `font-bold` on Marcellus** (`font-display` and `font-marcellus` both resolve to it).
- **Hairline grids put padding on the CELLS**, never on the grid element.
- **Semantic status colours are not brand colours** — emerald/amber/rose stay, at the -800 stop.
- **Keep the `astro` ramp defined and safelisted** — Python builds class names at render time.
- **Tailwind classes live outside templates too**: `i18n.py`, `routes/deps.py:_linkify_learn`,
  `routes/rashifal.py`, SVG attributes, inline `<style>` blocks, non-standard prefixes
  (`decoration-`, `shadow-`). Never assemble a class from a colour-FAMILY name
  (`bg-{{ color }}-100`); put the whole class pair in the dict, and never write `'neutral'` in a
  comment beside it.

Why and history: docs/claude-md-history.md#palette-and-css

### If you touch a Tailwind class, you must rebuild the CSS

```bash
npm ci             # NEVER `npm install` — see below
npm run build:css  # writes src/astro_ai/static/css/app.css — COMMIT IT
```

`app.css` is committed and shipped as-is. **`npm ci`, never `npm install`** (the gate
byte-compares). `scripts/verify_css_build.py` exiting **2** means "could not verify", not a pass.

**`uv run pytest` is a small behaviour suite**, not broad coverage. Run
`scripts/mutate_behaviour_suite.py` after adding a test. Still verify by exercising the change
(dev server and the route, or at minimum `ast.parse` plus an import check). Never report a
change as working on the strength of the diff alone.

Why and history: docs/claude-md-history.md#css-rebuild

---

## Content and astrological accuracy

- Astrological claims must trace to `knowledge/*.md`, citing the classical tradition rather
  than book-and-chapter references in user-facing prose.
- Match the established voice of existing `/learn` articles — read two before drafting one.
- Regional variation in festival dates and reckoning (purnimanta vs amanta, sunrise-spanning
  rules) is legitimate. State which convention a page uses rather than implying a single
  universal answer.

---

## Untracked by intention

`.local/`, `.serena/`, and `QA_LOG.md` sit untracked in the repo root. Leave them alone —
do not commit, delete, or gitignore them without asking.
