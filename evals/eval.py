"""The prompteval Eval for every astro-ai prompt (scripts/eval_prompts.py drives it).

One file for all eleven prompts: EVAL_PROMPT names the prompt (e.g. `natal`,
`ask_matching`), which picks its dataset in evals/datasets/ -- captured from the
real routes by evals/capture_datasets.py -- and every prompt is judged with
evals/criteria/astro-reading.md.

Models, owner's decision 2026-11-13: Claude through Claude Code for both, on the
subscription the loop already uses, so no new secret. Haiku writes the readings
(closer in strength to production's Groq model than Sonnet), Sonnet judges, so the
judge is never one of the models it compares. Quality is the pairwise verdict;
the one scorer here only catches an empty or truncated reply, which a judge
would otherwise have to notice.
"""
from __future__ import annotations

import os
from pathlib import Path

from prompteval import Eval, scorer

HERE = Path(__file__).resolve().parent
PROMPT = os.environ.get("EVAL_PROMPT", "natal")
MODEL = os.environ.get("EVAL_MODEL", "claude-haiku-5-5")
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-sonnet-5-5")


@scorer
def substantial_reply(output: str, expected: dict) -> float:
    """1 when the reply has real content (200+ characters), else 0."""
    return 1.0 if len((output or "").strip()) >= 200 else 0.0


eval = Eval(
    name=f"astro-{PROMPT}",
    dataset=HERE / "datasets" / f"{PROMPT}.jsonl",
    scorers=[substantial_reply],
    model=MODEL,
    base_url="claude-code",
    criteria=str(HERE / "criteria" / "astro-reading.md"),
)
