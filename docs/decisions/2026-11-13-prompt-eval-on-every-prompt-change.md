# Every prompt change is evaluated: base vs head, judged pairwise, a worse prompt cannot merge

- **Date:** 2026-11-13
- **PR / issue:** this PR (owner, in a session: *"integrate prompteval in astro-ai properly, ensuring every prompt change is properly evaluated"*; models: *"Claude for everything"*; on a worse verdict: *"Block the merge"*)

## Why

`src/astro_ai/prompts/*.txt` is the system prompt production sends, and a change to it was
reviewed by reading the diff. Nothing ran the old and new versions on the same charts and said
which readings were better. `evals/README.md` had promised this since the start.

## What it does

On a PR that changes `src/astro_ai/prompts/`, four steps inside `pr-gates`' `gates` job:

1. **Capture the datasets at this commit** (`evals/capture_datasets.py`). It drives the real
   routes in-process (`/kundli`, `/today`, `/monthly`, `/yearly`, `/dasha/deep-dive`,
   `/matching`, `/ask` in three contexts, `/rashifal/<sign>`) with the suite's offline isolation
   and records exactly what each would send, for 8 fixture charts with real coordinates. All 11
   prompts, 8 rows each. A PR that also changes a message builder is evaluated on its own inputs.
2. **Run base and head** of each changed prompt (`scripts/eval_prompts.py` + `evals/eval.py`), as
   production composes them: an `/ask` overlay runs under `ask.txt`, and an `ask.txt` change
   re-evaluates all four.
3. **Judge pairwise**: Sonnet reads both readings per chart, in both orders (disagreement is a
   tie), against `evals/criteria/astro-reading.md` and the **base** prompt's rules. The criteria add
   no astrology: chart facts must come from the input, the prompt's hard rules hold, it answers
   what was asked.
4. **Gate**: `--fail-on quality-5% --gate-mode significant` fails the job only when the new prompt
   is measurably worse, and `agent-merge` merges nothing whose checks are not all green.

**Why the base prompt's rules, measured:** replacing `dasha_deep_dive.txt` with one vague line
("Write a short paragraph about this person's current dasha") and judging against the HEAD prompt,
the judge preferred the ruined version **0.88 to 0.50** and the gate passed, because the full
deep-dives "broke" the new rule to be short. Against the base prompt the same runs scored **0.06**
and the gate failed (p<0.001). A PR must not redefine what good means for its own evaluation. The
cost: a deliberate rule change is judged by the old rule and can lose; the report says why, and
the PR is already held for chief, since prompts are in `TRUST_BOUNDARY`.

**Why `significant`, not prompteval's default `bound`:** `bound` fails any eval too small to rule
a 5-point drop out. At 8 charts that is every eval, so it would block every prompt change and
mean nothing.

**Why steps in `gates`, not a new workflow:** a new job fails `verify_workflow_permissions.py`
closed (and a red run there is the owner's, never chief's), and a separate check would not be
required anywhere. These steps need nothing beyond the job's `contents: read`; the report goes to
the job summary and a `prompt-eval` artifact, not a PR comment.

## Cost, measured

Claude Code calls took 17 to 49 s each (2026-11-13, Haiku). One prompt: 16 generations at
concurrency 8 plus 16 judge calls at 4, about 5 minutes. An `ask.txt` change evaluates four
prompts, about 20, so the `gates` job timeout rose from 35 to 60 minutes; every other PR skips
the steps. All on the Claude subscription the loop already uses (`CLAUDE_CODE_OAUTH_TOKEN`), no new
secret, 0 Groq tokens.

**Known limits:** Haiku is not production's Groq model, so this measures the prompt's intent on a
comparable model, not production output exactly (owner's choice, recorded). Only English is
evaluated. A change to `knowledge/remedies.md`, which reaches the natal user message, is not a
prompt change and is not evaluated. The token is exposed to `gates` on same-repo PRs only (forks
get no secrets), and same-repo authors are the loop and the owner.
