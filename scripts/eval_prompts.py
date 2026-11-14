#!/usr/bin/env python3
"""Evaluate every prompt a PR changes: its base version vs its head version (prompteval).

WHY THIS EXISTS
---------------
Owner, 2026-11-13: "integrate prompteval in astro-ai properly, ensuring every
prompt change is properly evaluated". `src/astro_ai/prompts/*.txt` IS the system
prompt production sends, and until now a change to it was reviewed by reading
the diff: nothing ran the old and new versions on the same charts and said which
readings were better. evals/README.md had promised exactly this since the start.

WHAT IT DOES, per changed prompt
--------------------------------
  1. Works out what production would send as the system message, at the merge
     base and at HEAD: the prompt file, plus `ask.txt` underneath an /ask overlay
     (llm._system_prompt; English adds no suffix). A change to `ask.txt` therefore
     re-evaluates `ask` and all three overlays.
  2. Runs both versions over the prompt's dataset (evals/datasets/<prompt>.jsonl,
     captured from the real routes by evals/capture_datasets.py) with evals/eval.py.
  3. Compares them pairwise -- a judge reads both readings for each chart, in both
     orders, against evals/criteria/astro-reading.md and the BASE prompt's rules --
     and gates with `--fail-on quality-5% --gate-mode significant`: it fails only
     when the new prompt is MEASURABLY worse. The default `bound` mode fails any
     eval too small to rule a 5-point drop out, which at 8 charts is every eval,
     so it would block every prompt change and mean nothing.

WHY THE BASE PROMPT'S RULES, NOT THE HEAD'S. Measured 2026-11-13 by replacing
dasha_deep_dive.txt with one vague line ("Write a short paragraph about this
person's current dasha"): judged against the HEAD prompt, the judge preferred the
ruined version 0.88 to 0.50 and the gate passed, because the full deep-dives
"broke" the new rule to be short. A PR must not get to redefine what good means
for its own evaluation. Against the base prompt the same change scored 0.06 and
the gate failed. The cost: a PR that changes a rule on purpose is judged by the
old one, and can lose; the report says why, and chief rules on it.

Writes eval-report.md (one section per prompt) and exits 1 if any prompt got
worse, 0 otherwise (including when no prompt changed). Exit 2: bad arguments.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = "src/astro_ai/prompts"
OVERLAYS = ("ask_matching", "ask_matching_third_party", "ask_numerology")
GATE = ["--fail-on", "quality-5%", "--gate-mode", "significant"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def changed_prompts(base: str) -> list[str]:
    names = {Path(p).stem for p in git("diff", "--name-only", f"{base}...HEAD", "--", f"{PROMPTS}/*.txt").split()}
    if "ask" in names:
        names.update(OVERLAYS)
    return sorted(names)


def prompt_at(ref: str | None, name: str) -> str | None:
    """The file's text at `ref` (None = the working tree), or None if absent."""
    path = f"{PROMPTS}/{name}.txt"
    if ref is None:
        f = ROOT / path
        return f.read_text(encoding="utf-8") if f.is_file() else None
    try:
        return git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def system_at(ref: str | None, name: str) -> str | None:
    """What llm._system_prompt sends for this prompt in English at `ref`."""
    text = prompt_at(ref, name)
    if text is None:
        return None
    if name in OVERLAYS:
        base = prompt_at(ref, "ask")
        return None if base is None else base + "\n" + text
    return text


def run(cmd: list[str], env: dict[str, str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, env=env).returncode


def evaluate(name: str, base: str, work: Path, judge: str) -> tuple[str, int]:
    old, new = system_at(base, name), system_at(None, name)
    if new is None:
        return f"## `{name}`\n\nRemoved in this PR; nothing to evaluate.\n", 0
    if old is None:
        return f"## `{name}`\n\nNew in this PR; there is no earlier version to compare against.\n", 0
    if old == new:
        return f"## `{name}`\n\nThe system message production sends is unchanged.\n", 0
    d = work / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "base.txt").write_text(old, encoding="utf-8")
    (d / "head.txt").write_text(new, encoding="utf-8")
    env = dict(os.environ, EVAL_PROMPT=name)
    for tag, f in ((f"{name}-base", "base.txt"), (f"{name}-head", "head.txt")):
        if run(["prompteval", "run", "--prompt", str(d / f), "--tag", tag,
                "--eval-file", "evals/eval.py", "--concurrency", "8"], env) != 0:
            return f"## `{name}`\n\nThe `{tag}` run failed; see the job log. Not judged.\n", 1
    report = d / "report.md"
    rc = run(["prompteval", "compare", f"{name}-base", f"{name}-head", "--pairwise",
              "--judge-base-url", "claude-code", "--judge-model", judge,
              "--judge-context", str(d / "base.txt"), "--criteria", "evals/criteria/astro-reading.md",
              "--markdown", str(report), *GATE], env)
    body = report.read_text(encoding="utf-8") if report.is_file() else "(no report written)\n"
    verdict = "**Worse: this change makes readings measurably worse.**" if rc else "Not measurably worse."
    return f"## `{name}`\n\n{verdict}\n\n{body}\n", rc


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="origin/main", help="ref to compare against (merge base is used)")
    ap.add_argument("--out", default="eval-report.md")
    ap.add_argument("--work", default=".prompteval/pr")
    ap.add_argument("--judge-model", default=os.environ.get("EVAL_JUDGE_MODEL", "claude-sonnet-5-5"))
    a = ap.parse_args(argv[1:])
    try:
        base = git("merge-base", a.base, "HEAD").strip()
    except subprocess.CalledProcessError:
        print(f"::error::cannot find a merge base with {a.base}")
        return 2
    names = changed_prompts(base)
    if not names:
        Path(a.out).write_text("No prompt changed in this PR; nothing evaluated.\n", encoding="utf-8")
        print("no prompt changed")
        return 0
    sections, worse = [], []
    for n in names:
        text, rc = evaluate(n, base, ROOT / a.work, a.judge_model)
        sections.append(text)
        if rc:
            worse.append(n)
    head = ("**Prompt evaluation: " + (f"worse on {', '.join(worse)}.**" if worse else "no prompt got worse.**")
            + f"\n\nCompared base `{base[:7]}` with this PR for {', '.join(f'`{n}`' for n in names)}. "
            "Each prompt ran on 8 fixture charts captured from the real routes; a judge compared the "
            "two readings per chart in both orders (disagreement is a tie). The check fails only when "
            "the new version is measurably worse (`--gate-mode significant`).\n\n")
    Path(a.out).write_text(head + "\n".join(sections), encoding="utf-8")
    return 1 if worse else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
