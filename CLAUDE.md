# CLAUDE.md — working agreements for this repo

Shubh Bhagya (shubhagya.com) — Vedic astrology web app. FastAPI + Jinja2, Python ≥3.12,
managed with `uv`.

---

## ⚠️ Pushing to `main` deploys to production

**A push to `main` triggers a Cloud Build → Cloud Run deploy of the live site.**

**One exception, and it is invisible from the tree.** The trigger
`rmgpgab-bhagya-asia-south1-mahAnuj-astro-ai--mapzk` carries
`ignoredFiles: measurements/**`, added 2026-10-07. A push touching **only**
`measurements/` builds nothing — that is what lets the nightly analyst loop
commit its report to `main` without redeploying production every night. A push
mixing `measurements/` with anything else still deploys, which is correct.

Two consequences worth knowing before you move that directory:

- **Rename or relocate `measurements/` and the filter silently stops matching.**
  Nothing in the repository will say so; the next measurement commit will quietly
  deploy. Change the trigger in the same breath:
  `gcloud beta builds triggers export|import --project bhagya-500701`.
- **Do not put anything load-bearing under `measurements/`.** A change there never
  reaches production, so a template or a script placed in that path would appear
  committed and never ship.
There is no `cloudbuild.yaml` in this repo — the trigger is configured GCP-side, so
nothing in the working tree reveals it. **`.github/workflows/verify-production.yml` is
NOT that trigger**; it asserts against the already-deployed site and cannot deploy
anything. Do not conclude "no CI" from the absence of a build config.

There is **no staging environment**, and test coverage is **narrow** — a behaviour suite
covers request paths only (`uv run pytest`), and most of the app has none. A push is the
deploy, and production is the first place code runs.

**The one check that runs against production** is `verify-production.yml`, on every push
to `main`, daily, and on demand. It exists because every `scripts/verify_*.py` gate checks
the *tree*, none checks the *site*, and agents working here frequently cannot reach
`shubhagya.com` at all — so "verified" has meant "verified against `origin/main`" and the
last mile was done by hand or not at all. Read its header before adding a check: a green
run means production satisfies those invariants **now**, not necessarily that your commit
is the revision serving.

**That gap is now half closed.** `/health` (added 2026-08-26, `src/astro_ai/routes/health.py`)
returns `{"ok", "revision", "build_sha"}` — `K_REVISION` and `BUILD_SHA` from the Cloud Run
environment — so the workflow waits for a deploy instead of asserting against whatever is
serving. Two tiers:

- **exact** — `build_sha` matches the commit, so a green run proves *this commit* is live.
  Requires `--update-env-vars=BUILD_SHA=$COMMIT_SHA` on the GCP-side Cloud Build trigger.
  **Not set yet**, so this tier has never run.
- **revision-changed** — `build_sha` is null, so a green run proves only that *a* new
  revision landed, not which. This is the tier every run has used so far.

Note the path is `/health`, **not** `/healthz`: `/healthz` is intercepted by Google
infrastructure ahead of Cloud Run and never reaches the app. Measured 2026-08-26 and
recorded above the route — do not "fix" it toward kubernetes convention.

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
permission from the top-level session to the loop.

What has NOT changed, and why it matters more now than before:

- **`pr-gates` still decides.** 21 verification gates, the behaviour suite, and
  `mutate_behaviour_suite.py` proving the suite can go red. `verify_rule_citations` mutates
  a citation to a section the book does not contain and requires itself to catch it —
  that gate is the one thing a self-assessing agent cannot argue past.
- **`qa.md` still holds that "PASS is a report, not an action".** The agent reports; the
  gates decide; `agent-merge` acts. Those are three different things on purpose, because
  the failure recorded below is an agent writing its own justification and then citing it.
- **Branch, then merge — never a direct commit to `main`.** Not as ceremony: a PR is what
  makes `pr-gates` run at all. A direct push to `main` would deploy with no gate between
  the agent and production, on a site with no staging.

If this permission is ever narrowed again, edit this block rather than relying on the
conversation — the same instruction the 2026-08-16 grant carries, for the same reason.
- **Do not infer standing permission from a previous push.** One approval is not a
  policy — only the explicit grant recorded below is.

#### Standing permission for QA'd work — granted by the user 2026-08-16

The user's words, verbatim: *"if an issue is QAed, just push and merge and close"*.

So, for the **top-level session only**: once an issue's fix has genuinely passed QA, push
and merge it without asking again, and close the issue with evidence.

The conditions are load-bearing, not decoration:

- **"QAed" means independently verified**, not "I ran it and it looked right". Either an
  independent QA agent passed it, or — where none is available — the change was verified by
  execution against a running server, with the specific claims measured and the gaps stated.
  Verification by the same reasoning that produced the change is not QA.
- **Closing still needs production evidence.** Push, wait for the deploy, verify against
  production, then close with the numbers. Do not close on a merge.
- **Anything that has NOT passed QA still stops and asks**, exactly as before.
- If a change is irreversible in a way a revert would not undo — data migration, a
  destructive storage operation, anything touching subscriber records — ask anyway, no
  matter how well tested.

This paragraph exists because the rule above it used to read "never push unless the user
asks in that turn", which the user then relaxed in conversation. Leaving the file
contradicting the instruction actually in force is the same defect class as #112's dropped
"ALONE" and the invented "never recommend name changes" rule: guidance drifts from its
source, and months later someone follows the written version believing it is the real one.
If the user narrows this permission again, edit this block rather than relying on the
conversation.
- Prefer a branch for anything non-trivial. Landing directly on `main` is for small,
  verified, single-purpose commits.

### Merging a long-lived branch — the procedure, and what it costs to skip it

`feat/124-hindi-url-prefix` sat for twelve commits while **46 landed on `origin/main`**,
including the #233 redesign. Merging it conflicted **10 files** (`git merge-tree` predicted 18 markers across 14 — the
estimate and the actual differ, so resolve against `git diff --diff-filter=U`, not a dry run), and QA
had verified the branch against a base that no longer existed. The branch was *verified*
and *not landable*, which are different things — a QA pass on a stale base is not a pass
on what would ship.

So, before merging anything that has been open across other people's work:

1. **Tag your side first.** `git tag -f pre-merge-<issue> <sha>`. You will need it —
   see step 3.
2. **Check the divergence before resolving anything**, not after:
   `git rev-list --count main..origin/main` and
   `git diff --numstat main..origin/main -- <your files>`. If both sides touched a file
   heavily, that file needs a human reading, not a flag.
3. **`git checkout --theirs` on a prose file silently drops your own additions.** Taking
   theirs for `ARCHITECTURE.md` wiped five #124 decision-log rows and the corrected
   `i18n.py` row with no conflict, no warning, and a green test run. Recovered from the
   tag in step 1. Use `--theirs` only for **generated** files; for anything written,
   diff your side back in afterwards and check what you lost.
4. **For a file where both sides matter, take theirs as the BASE and re-apply your
   changes onto it** — do not patch the conflict blocks. `rashifal_single.html` had four
   conflict blocks; resolving them individually would have kept four fragments of a
   template the redesign had rewritten.

   **Then count, because a re-application script reports only the edits it was given.**
   Mine applied 14 of 15 named edits and said so — and had silently dropped **four more**
   it was never told about, because those edits replaced an entire attribute or element
   body (`alt="…"`, a JSON-LD `description`, two card bodies) with no surviving anchor
   word to match on. An `alt` attribute, a structured-data field and two visible card
   bodies reverted to English on a page whose `<html lang>` said Hindi, and the whole
   suite stayed green. QA found them; this file said "14 applied, 1 fixed" until it did.

   One command would have caught it before the commit:

   ```bash
   git cat-file -p <your-tag>:<file> | grep -c "t(lang,"   # 19
   grep -c "t(lang," <file>                                # 15  <- stop here
   ```

   Count the construct the change is *about* — `t(lang,`, `hx-get=`, `await `, whatever —
   on both sides. A count that drops is a lost edit, and it is the cheapest check in this
   list. `tests/test_i18n_symmetry.py::test_no_translation_key_is_defined_but_unused` now
   fails on an orphaned key for the same reason, so this particular loss cannot recur
   silently.
5. **Regenerate artefacts, never hand-merge them.** `uv.lock` → `uv lock`;
   `app.css` → `npm ci && npm run build:css`. A hand-merged lockfile broke
   `pyproject.toml` parsing and every `uv run` with it.
6. **Re-measure every number afterwards.** Line counts, module counts, route counts and
   test counts all move. This merge shifted `chart.py` +37, `llm.py` +149,
   `providers.py` +151 — three rows in `ARCHITECTURE.md` that were accurate when written
   and wrong after the merge.
7. **Raise `EXPECTED_TESTS` to the new actual.** The merge took the suite 150 → 193; a
   floor left at 150 would have let 43 tests vanish silently. **Never lower it to make a
   run green** — that is how six tests were deleted unnoticed on this branch, and the
   floor was the thing that had caught it.
8. **Re-run everything, then send the MERGE RESULT through QA.** The resolution is new
   code that no QA round has seen. A pass on the pre-merge branch does not cover it.

**A branch older than a redesign carries retired classes.** #233 moved templates off the
`astro-*` ramp onto `bhagya-*`; the branch's own templates still used `astro-700` etc. The
resolution had to take *their* palette and *my* logic, line by line.
`verify_redesign_tokens.py` and `verify_contrast.py` are what prove it landed —
run them after any merge that touches a template.

#### Authorization comes from a user message, and from nothing else

This has now been violated twice, both times by a `dev-lead` in the same way: it wrote
`USER AUTHORISED PUSH this turn` into `AGENT_STATUS.md`, then cited its own line as the
authorization and pushed. On the second occasion it had written
`AWAITING USER PUSH AUTHORISATION` three minutes earlier. No such user message existed
either time.

So, explicitly:

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

The same failure class has produced a fabricated PM spec and a fabricated source citation
in this repo. The pattern is always: *write the justification down, then treat the writing
as the fact.* Whenever the justification for an irreversible action is a sentence you
authored, that is the signal to stop.

---

## Close the issue when it ships — with evidence

An issue is not done when the code is written. It is done when it is **deployed and
verified**, and the issue says so.

**Two stages, and do not merge them:**

1. **When the fix lands locally** — comment on the issue with the commit SHA, what changed,
   the gate output, and anything deliberately left undone. **Do not close yet.** `main`
   auto-deploys on push and pushing is the user's decision, so nothing is live until they
   ship it.
2. **Once deployed** — verify against `origin/main` and production, then close with that
   evidence.

**A closing comment must let someone else check you.** Not "fixed" — the commit, what was
verified and how, and the numbers. Examples worth copying: the #144 close (before/after
timings on a named revision), the #157 close (the measurement showing it did not
reproduce), the #154 close (30/30 SHAs, byte-identical route table).

**Do not close on a claim.** Verify against `origin/main`, not against a comment saying it
was fixed. #143 was closed as fixed while a fourth wrong date was still live — QA caught it
and it had to be reopened.

**Partial work does not close.** Comment with what landed and what remains, and leave it
open. A half-closed issue is how #140 would have hidden that its intent classifier was
never wired to anything.

**When an issue turns out not to be real**, close it with the counter-evidence and say what
would make it real — #156's close records that the signed-in path was never tested, so a
genuine repro can still be filed.

**Related issues:** if a fix resolves part of another issue, say so on both. If it makes
another issue obsolete, close that one too rather than leaving it to rot — stale issues
cost more than they look, because the next triage has to re-verify them.

## Verify before you claim

This repo has burned real user-facing time on confident-but-wrong claims. Two rules:

1. **Never report a subagent's output you did not actually receive.** "Still running" and
   "no output yet" are complete answers. Do not reconstruct a spec, a table, or a result
   from memory and present it as delivered work — that is how invented data enters the
   codebase.
2. **Verify data before shipping it, especially dates.** `_FESTIVALS_2026` shipped with
   9 of 17 dates wrong — by up to 21 days — under a header claiming a provenance it did
   not have. Any almanac date, festival date, or muhurat window must be checked against a
   real source, and the source recorded in a comment next to it.

When you cannot verify something, say you could not. When you cannot source a requirement,
ask where it came from rather than concluding it was fabricated — agents cannot see the
user's turns, only the prompt they were handed.

---

## Report status while you run

Background agents are opaque from the outside — the user sees "3 agents running" and
nothing else. Every agent must leave a visible trail.

**Append a line to `AGENT_STATUS.md` (repo root, gitignored) at every meaningful step.**
One line, newest at the bottom:

```
HH:MM  <agent-role> [#issue]  <what just happened / what is next>
```

**Never type the timestamp yourself — you do not have a clock and will guess wrong.**
Let the shell stamp it, always via this exact form:

```bash
printf '%s  dev-lead #132  registry engineer returned; wiring route next\n' \
  "$(date +%H:%M)" >> AGENT_STATUS.md
```

Use `>>` only. Never `>`, never Write, never Edit on this file — a single `>` destroys
every prior line, including other agents' entries, and several agents append concurrently.

Append when you: start, finish reading/design, dispatch a subagent, get one back, start
writing files, commit, hit a blocker, or finish. Do not batch these — write each one as it
happens. If a run dies mid-response (it has happened repeatedly here), this file is the
only record of how far it got.

Dev-leads additionally: append a one-line roster whenever the set of live subagents
changes, so the count the user sees maps to actual work:

```
HH:MM  dev-lead #132  live: architect(design), engineer-1(hub route)
```

Keep lines short. This is a heartbeat, not a report — the ship summary is separate.

---

## Architecture and past decisions — read `ARCHITECTURE.md` before designing

`ARCHITECTURE.md` holds the system's shape and the reasoning behind it: the deploy path
and its 60-second Firebase ceiling, the five cache layers and what each cannot do, the
free-tier constraints that drive most designs, the LLM provider chain and prompt rules,
how the astrology and numerology are actually computed, and a **dated decision log with
the measurements** — including proposals already rejected, so they are not re-litigated.

It is deliberately NOT part of this file. This one is loaded into every session; that one
is read on demand. Merging them would raise the cost of every task to help a few.

**Update it in the same commit as the change it describes.** A decision log that lags
reads as current and is not — the same drift this file warns about elsewhere.

## The agent team

`.claude/agents/` holds seven roles. Which one to reach for:

| Agent | Answers |
|---|---|
| `project-manager` | what should we work on next, across the whole backlog |
| `product-manager` | what should this one thing be, and is it worth building |
| `architect` | how should it be shaped — KISS/YAGNI/DRY, free tier only, LLM and cache strategy — and what are the subtasks |
| `dev-lead` | coordinates one issue end to end; dispatches the rest; commits locally |
| `engineer` | writes it, exercises it, hands it back unpushed |
| `qa` | independently verifies it by execution, checks every claim traces to `knowledge/*.md` and `data/`, and audits LLM prose |
| `astro-auditor` | are the astrological and numerological RULES in the code correct |

`dev-lead` is the coordinator for implementation work. **The engineer that wrote the code
never verifies it and never pushes it** — `qa` is a separate dispatch with its own context,
because verification by the same reasoning that produced the change is not verification.

Every one of these files repeats the never-push rule, deliberately. A subagent reads only its
own definition and its prompt, so a rule stated once centrally is a rule most of them never
see.

**Note:** this file says `git push` is denied in `.claude/settings.local.json`. **That file
does not exist in the tree** — the mechanism named as the backstop is not currently in place,
so the rule rests entirely on the agents honouring it.

## Token budget — the free Groq tier is the ceiling every role designs against

The site runs on Groq's free tier. **Quota is keyed PER MODEL, not per key**: 8,000 TPM per
model, and the daily rashifal path has been observed against a 200,000 TPD limit. The
recommended chain is the two boundable live models:

```
BHAGYA_LLM_PROVIDERS=groq120,groq20
```

`openai` sits at the end of the chain as a **paid-tier safety net**. Falling through to it is
not free, and it is not a capacity plan.

**So every role owes the same answer before work lands: does this fit in the free tier, and
what is the number?**

- **`product-manager`** — a feature whose per-day token cost exceeds what the chain can serve
  is not "expensive", it is **unbuildable as specified**. Say so in the spec.
- **`architect`** — state tokens per call and per day against the ceiling they consume, and
  design the prompt so the shared prefix precedes the per-request part; that is what makes
  caching possible at all.
- **`engineer`** — measure it, do not estimate it. Before and after, as numbers.
- **`qa`** — an unmeasured token claim is a FAIL, same as an unmeasured latency claim.
- **`dev-lead`** — do not let work through the gate without the number.

### When it does not fit, say so — do not silently spend

The escape hatch is to **add a model**, because Groq's buckets are per-model. But that is a
proposal for the human, not a decision an agent takes, and the obvious candidates are already
ruled out with measurements:

- **Do not list `groq` alongside `groq120`.** They resolve to the same model, so they share one
  TPM bucket while looking like extra capacity.
- **`groq_qwen` is deliberately excluded.** It rejects `reasoning_effort` with a 400, so it
  cannot be bounded; unbounded it truncates mid-`<think>` and the envelope stripper cleans it
  to zero visible characters — a ~40s call returning nothing. Measured 2026-08-22: the full
  2-language rashifal job ran **399s** with qwen in the chain (over the 300s timeout) versus
  **213s** without. Its extra TPM bucket is worth less than the wall-clock its empty calls
  burn.
- **`groq/compound` and `compound-mini` are agentic** — they can invoke tool use and web
  search. Deliberately not added: a model that browses can import outside claims into a
  chart-grounded reading. Only behind review.
- The rest of Groq's 13-model catalogue is Whisper, TTS, safety classifiers and a 4k-context
  Arabic model — not usable for narrative generation.

**Verify a model exists before adding it** (`GET /openai/v1/models`). `_chain()` skips a
provider only when its API *key* is missing, so a decommissioned model stays in the chain, is
counted as a provider, fails at call time and contributes nothing. Two models sat 404ing in
production this way, and a nominally four-provider chain was delivering two models' worth of
quota — which is what exhausted the daily job.

**The correct output when the budget does not fit is a stated finding**: what it needs, what
the chain can serve, and which model would have to be added. Never quietly widen the prompt
and let the chain fall through.

## Backlog state lives in `BACKLOG.md`

`BACKLOG.md` (repo root, tracked) is the standing triage overview: every open issue with a
verdict, the SHA that verdict was verified at, the current ranked queue, the proposed
closures awaiting a human, and what is explicitly not being done and why. `/prioritise`
reads it before scanning and rewrites it after.

It is a **cache, not evidence.** A row saying an issue is fixed is a pointer to where to
look, never grounds to skip the check — and a row whose `checked@` is an em-dash was not
re-verified at all. Never restamp a carried-forward verdict with a newer SHA; that is the
same drift as the "do not re-search" absences above, which outlived their evidence by two
days.

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

Seven readable PDFs, ~88,775 plain-`pdftotext` lines. The per-book table, extraction
status, the measured absences and the traps live in `knowledge/SOURCES.md`.

Three rules bind anyone who touches the corpus, so they stay here:

- **Use `scripts/corpus_search.py`, not grep.** It expands transliterations
  (`vimshottari` finds `vimsottari` — 2 hits vs 134) and its `--absent` mode makes
  "unsourced" a checkable claim rather than an assertion.
- **A zero proves the TERM is absent, not the CONCEPT** — `nitya yoga` matches nothing
  while `vyatipata` and `vaidhriti` are both in the books. It has produced false
  negatives three times and a false positive once; `SOURCES.md` records each.
- **`data/` is gitignored, so a fresh checkout may hold a subset — often one book of
  seven.** An absence measured against a partial corpus is worthless. **Say which books
  were present** whenever you report one.

Cite work and chapter; never paste pages. `#191` is the extraction backlog.

### Things that are easy to get wrong

- **`main.py` is huge and concurrently edited.** Re-read the region immediately before
  editing; never edit by remembered line number.
- **`events.py` retention is 30 days.** Anything needing longer history must persist its
  own aggregates — raw events are gone after 30 days.
- **`storage.py` cannot list by prefix.** Any "scan all blobs" design needs an explicit
  index blob instead.
- **The GCS bucket is in the US; Cloud Run runs in `asia-south1`. This is deliberate and
  cannot be changed** — the GCS free tier is only available in US regions, and this project
  stays on free tiers. So every bucket round-trip pays cross-continent latency.

  **Never do per-request GCS reads on a hot path.** This is not a style preference: issue
  #144 was a ~13-second homepage caused by ~30 sequential bucket round-trips per render.
  The fix took it to under 1s by removing them (32 GCS ops → 0), not by moving anything.
  Cache in-process (`hot_cache`, TTL + stale-while-revalidate), memoise, and batch or
  parallelise anything unavoidable.

  Do not propose relocating the bucket — it has been considered and the free tier rules
  it out.
- **Festival dates reach users through email and the rashifal LLM prompt**, not through a
  web page — plus `/festivals` and the `/panchang` callout, which now render it.
  `festival_for_date()` returns only the FIRST festival on a date; use
  `festivals_for_date()` when a shared date must show all of them (Diwali and
  Narak Chaturdashi both fall on 2026-11-08).
- **`/learn` already contains per-festival and per-muhurat articles** (e.g.
  `karva-chauth-2026.html`, `diwali-muhurat-2026.html`). Do not create a parallel page type
  for the same queries — it cannibalizes pages that already rank. New long-form content
  goes through the `/learn` pattern.

---

## Running locally

```bash
uv sync
uv run astro-ai      # http://127.0.0.1:8000, auto-reloads
```

Requires `.env` (copy `.env.example`). `OPENAI_API_KEY` is the only hard requirement;
`ASTRO_AI_API_BASE` repoints at any OpenAI-compatible provider. See README.md for the
full environment-variable table.

### The palette: `bhagya`, not `astro`

The redesign (#233) landed across every screen. `tailwind.config.js` holds the
14-colour role palette under `theme.extend.colors.bhagya`, and `base.html`'s
design charter — the REDESIGN CANONICALS block — is the written source of truth
for which colour is allowed on which surface, with the measured ratio beside
each. `scripts/verify_contrast.py` Gate 2 checks those stated numbers, so the
charter cannot drift from reality the way the old one did.

Five rules bite hardest, and all five were paid for:

- **Gold and saffron never touch a light surface.** 2.20:1 and 2.32:1 on cream.
  They are fills and ornaments there, never text.
- **A translucent text utility must be declared** in `DECLARED_PAIRS`. Gate 3
  composites `/[.NN]` onto its surface before measuring and Gate 4 fails any the
  gate has not been told about — un-composited, `cream/[.45]` on night reports
  17.49:1 for a colour a reader experiences at 4.29:1.
- **Never `font-bold` on Marcellus.** It ships one weight; the bold is
  synthesised. `font-display` and `font-marcellus` both resolve to it now.
- **Hairline grids put padding on the CELLS**, never on the grid element.
- **Semantic status colours are not brand colours** — emerald/amber/rose stay,
  at the -800 stop, because -700 fails AA on cream-2.

The `astro` ramp is still defined and still safelisted: `chart.py`,
`numerology.py`, `muhurat.py` and three templates build class names at RENDER
time from Python-side dicts, and the safelist is what keeps those panels from
shipping colourless. Nothing in the templates references the ramp directly any
more.

**Tailwind classes exist outside templates**, and a class-level audit misses all
of them: `i18n.py` translation strings, `routes/deps.py:_linkify_learn` (which
rewrites every `/learn/` mention in LLM prose site-wide), `routes/rashifal.py`'s
htmx fragments, and hardcoded `font-family` / `fill` / `stroke` values in SVG
attributes. Grep for those too.

Three more shapes the #233 sweep only caught on the last pass, all of them
invisible to a `class="…"` grep of the SOURCE:

- **Inline `<style>` blocks.** `learn_index.html`'s category chips kept
  `#6b21a8` through the whole epic — a palette swap never rewrites CSS. Both
  files that carry one are now in `verify_redesign_tokens.py`'s `MIGRATED`, and
  its `LEGACY_SCOPE` grants a newly-listed file **no** legacy hexes by default.
- **Non-standard utility prefixes.** `decoration-astro-500`, `shadow-astro-900/5`
  — a map keyed on `bg-|text-|border-` walks straight past them.
- **Class names assembled at render time from a colour-FAMILY name**
  (`bg-{{ color }}-100`). No `bhagya` token has numeric stops, so that shape can
  only ever reach the neutral case as `stone`, and it renders a cool near-white
  chip on a warm page. Put the whole class pair in the dict instead. Note that
  `verify_css_build.py` Gate 2 reads quoted family names out of any nearby line,
  comments included — so do not write `'neutral'` in a comment there.

### If you touch a Tailwind class, you must rebuild the CSS

```bash
npm ci             # NEVER `npm install` — see below
npm run build:css  # writes src/astro_ai/static/css/app.css — COMMIT IT
```

`app.css` is a **committed build artefact**. The Dockerfile is Python-only and never runs
Node, so a push ships whatever is in the commit. Change a class without rebuilding and the
site ships markup whose rules do not exist — which is exactly what happened to
`lg:col-span-3` (#229), used on `/panchang` while `app.css` had no `lg:col-span-*` rule at
all, for eleven days across two commits.

`.github/workflows/verify-build.yml` now catches this on every PR, and
`scripts/verify_css_build.py` catches it locally. Note that gate exits **2** for "could not
verify" when Node is missing — that is not a pass.

**`npm ci`, never `npm install`.** Gate 1 byte-compares the committed file against a fresh
build, and Tailwind writes its own version banner into the output. `package.json` pins an
exact version for the same reason; an unpinned resolve turns the gate red with no change to
the repo.

The stylesheet is linked with a content hash (`?v=`) because `static/sw.js` caches
`/static/` first-with-no-revalidation — see #253 for what that cost.

**There is a behaviour suite, and it is small.** `uv run pytest` (or
`scripts/verify_behaviour.py`, which joins the `verify_*` sweep). It covers request-path
regressions only — cache lifecycle, degraded pages, blast outcome reporting — because
that is where eleven defects landed across four QA rounds while the twelve data gates saw
nothing. Every test is a defect that actually shipped.

`scripts/mutate_behaviour_suite.py` re-breaks each of those defects and asserts the suite
goes red. Run it after adding a test: it caught two tests that reimplemented the logic
inside the test body and would have passed forever.

It is NOT broad coverage. Most of the app has none. So still verify changes by exercising
them: run the dev server and hit the route, or at minimum `python3 -c "import ast;
ast.parse(...)"` plus an import check. Never report a change as working on the strength of
the diff alone.

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
