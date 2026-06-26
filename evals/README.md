# evals/

Reserved for the **prompt evaluation sub-project** — a separate concern from
astro-ai's runtime. When we wire [prompteval](https://github.com/mahAnuj/prompteval)
in here, it will:

1. Snapshot whatever's currently in `src/astro_ai/prompts/` as `prompts/<name>_vN.txt`.
2. Hold a `dataset.jsonl` of fixture birth charts.
3. Hold an `eval.py` defining the scorers (groundedness, length, tone, etc).
4. Run `prompteval compare` on every prompt change to catch regressions.

Until prompteval is wired in, `prompts/v2.txt` is just an early draft kept here
for reference.

Nothing in this folder is imported by the production app. astro-ai loads its
prompts directly from `src/astro_ai/prompts/`.
