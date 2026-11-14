# evals/ -- every prompt change is evaluated

On a PR that changes `src/astro_ai/prompts/`, `pr-gates` runs the old and new version of each
changed prompt on the same 8 fixture charts and has a judge compare the readings
([prompteval](https://github.com/mahAnuj/prompteval), pairwise, both orders). The `gates` check
fails when the new version is measurably worse. Why and what it costs:
`docs/decisions/2026-11-13-prompt-eval-on-every-prompt-change.md`.

| file | what it is |
| --- | --- |
| `capture_datasets.py` | drives the real routes with the model call recorded, writes `datasets/<prompt>.jsonl` (all 11 prompts, 8 rows each) |
| `datasets/` | the exact user messages production sends, captured; re-captured in CI at the PR's commit |
| `eval.py` | the prompteval Eval: `EVAL_PROMPT` picks the dataset; Haiku writes, Sonnet judges, via Claude Code |
| `criteria/astro-reading.md` | how the judge decides which reading is better |
| `../scripts/eval_prompts.py` | the driver: base vs head for each changed prompt, report, gate |

Run it locally (needs `claude` signed in and `uv tool install prompteval-delta==0.3.0`):

```bash
PYTHONPATH=tests uv run pytest -p conftest -q evals/capture_datasets.py
python3 scripts/eval_prompts.py --base origin/main
```

`generate_dataset.py`, `dataset.jsonl` and `prompts/v2.txt` are the earlier hand-built draft,
kept for reference. Nothing here is imported by the production app.
