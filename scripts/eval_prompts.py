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

A RUN THAT DID NOT COMPLETE BLOCKS, AND SAYS IT WAS NOT A VERDICT. Measured
2026-11-15 on the pinned prompteval-delta 0.3.0: `prompteval run` exits 0 when
examples error ("errors 8 of 8 examples failed", rc 0), and `compare` silently
drops errored examples and judges the survivors. With 6 of 8 head readings
failing (a 429, or the shared subscription window running out mid-run) the
comparison ran on 2 charts and this script printed "no prompt got worse" and
exited 0 -- QA's FAIL on PR #1000. So the exit code is not trusted: the persisted
run file (.prompteval/runs/<tag>.json, one `examples[]` entry per chart, each
with `error` null or a message) and the saved judgement are read back, and any
errored example, missing chart or unreadable judge reply blocks the job as
"could not evaluate" -- distinct from "measurably worse", which is the only
outcome a `GATE FAILED:` line from compare may produce.

Writes eval-report.md (one section per prompt) and exits 1 if any prompt got
worse OR could not be evaluated, 0 otherwise (including when no prompt changed).
Exit 2: bad arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = "src/astro_ai/prompts"
OVERLAYS = ("ask_matching", "ask_matching_third_party", "ask_numerology")
GATE = ["--fail-on", "quality-5%", "--gate-mode", "significant"]
RUNS = ROOT / ".prompteval" / "runs"              # where `prompteval run` saves <tag>.json
JUDGEMENTS = ROOT / ".prompteval" / "judgements"  # where `compare --pairwise` saves its verdict
# What `prompteval compare` prints before it exits 1 on a --fail-on breach
# (prompteval/cli.py, `compare`). It also exits 1 on a ClickException ("only 0
# paired examples") and on a judge crash, so rc 1 alone is not a regression.
GATE_FAILED = "GATE FAILED:"
# Charts a run may lose and still be judged: none. At 8 charts one lost chart is
# 12.5% of the sample, and errors are not random -- they cluster on a 429 or an
# exhausted window -- so the survivors are not a fair sample of the prompt.
MAX_ERRORED = 0
OK, WORSE, NOT_EVALUATED = 0, 1, 2


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


def run(cmd: list[str], env: dict[str, str]) -> tuple[int, str]:
    """Run `cmd`, echoing its output live to the job log; return (rc, output)."""
    print("+", " ".join(cmd), flush=True)
    lines = []
    with subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True) as p:
        for line in p.stdout:
            print(line, end="", flush=True)
            lines.append(line)
    return p.returncode, "".join(lines)


def dataset_size(name: str) -> int:
    f = ROOT / "evals" / "datasets" / f"{name}.jsonl"
    return sum(1 for line in f.read_text(encoding="utf-8").splitlines() if line.strip()) if f.is_file() else 0


def run_problems(tag: str, expected: int) -> list[str]:
    """Why the saved run `tag` cannot be judged; empty when every chart answered."""
    path = RUNS / f"{tag}.json"
    try:
        examples = json.loads(path.read_text(encoding="utf-8"))["examples"]
        errored = [e for e in examples if e.get("error") is not None]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as err:
        return [f"`{tag}`: no readable run file at {path} ({type(err).__name__})"]
    problems = []
    if expected == 0 or len(examples) != expected:
        problems.append(f"`{tag}`: {len(examples)} charts recorded, the dataset has {expected}")
    if len(errored) > MAX_ERRORED:
        first = errored[0]
        problems.append(f"`{tag}`: {len(errored)} of {len(examples)} charts errored "
                        f"(first: `{first.get('id')}`: {str(first.get('error'))[:200]})")
    return problems


def judgement_problems(tag_a: str, tag_b: str, expected: int) -> list[str]:
    """Why the saved pairwise judgement is not a full one. prompteval counts a judge
    reply that is not A, B or TIE as a tie, and ties pull towards "not worse"."""
    path = JUDGEMENTS / f"{tag_a}__vs__{tag_b}.json"
    try:
        j = json.loads(path.read_text(encoding="utf-8"))
        judged, unreadable = int(j["judged"]), int(j["unreadable"])
    except (OSError, ValueError, KeyError, TypeError) as err:
        return [f"no readable judgement at {path} ({type(err).__name__})"]
    problems = []
    if judged != expected:
        problems.append(f"the judge compared {judged} of {expected} charts")
    if unreadable:
        problems.append(f"{unreadable} judge replies were not A, B or TIE")
    return problems


def not_evaluated(name: str, why: list[str], body: str = "") -> tuple[str, int]:
    reasons = "\n".join(f"- {w}" for w in why)
    return (f"## `{name}`\n\n**Could not evaluate: blocked, failing closed.** This is NOT a "
            f"verdict that the prompt is worse; the evaluation did not complete:\n\n{reasons}\n\n"
            f"Re-run the job once the cause is fixed (see the job log).\n\n{body}"), NOT_EVALUATED


def evaluate(name: str, base: str, work: Path, judge: str) -> tuple[str, int]:
    """One prompt's section of the report, and OK, WORSE or NOT_EVALUATED."""
    old, new = system_at(base, name), system_at(None, name)
    if new is None:
        return f"## `{name}`\n\nRemoved in this PR; nothing to evaluate.\n", OK
    if old is None:
        return f"## `{name}`\n\nNew in this PR; there is no earlier version to compare against.\n", OK
    if old == new:
        return f"## `{name}`\n\nThe system message production sends is unchanged.\n", OK
    d = work / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "base.txt").write_text(old, encoding="utf-8")
    (d / "head.txt").write_text(new, encoding="utf-8")
    env = dict(os.environ, EVAL_PROMPT=name)
    expected = dataset_size(name)
    tag_a, tag_b = f"{name}-base", f"{name}-head"
    report = d / "report.md"
    # A file left by an earlier run must never be read back as this run's result.
    for stale in (RUNS / f"{tag_a}.json", RUNS / f"{tag_b}.json",
                  JUDGEMENTS / f"{tag_a}__vs__{tag_b}.json", report):
        stale.unlink(missing_ok=True)
    for tag, f in ((tag_a, "base.txt"), (tag_b, "head.txt")):
        rc, _ = run(["prompteval", "run", "--prompt", str(d / f), "--tag", tag,
                     "--eval-file", "evals/eval.py", "--concurrency", "8"], env)
        if rc != 0:
            return not_evaluated(name, [f"`prompteval run` for `{tag}` exited {rc}"])
        if problems := run_problems(tag, expected):
            return not_evaluated(name, problems)
    rc, out = run(["prompteval", "compare", tag_a, tag_b, "--pairwise",
                   "--judge-base-url", "claude-code", "--judge-model", judge,
                   "--judge-context", str(d / "base.txt"), "--criteria", "evals/criteria/astro-reading.md",
                   "--markdown", str(report), *GATE], env)
    body = report.read_text(encoding="utf-8") if report.is_file() else "(no report written)\n"
    if rc == 1 and GATE_FAILED in out:
        return f"## `{name}`\n\n**Worse: this change makes readings measurably worse.**\n\n{body}\n", WORSE
    if rc != 0:
        return not_evaluated(name, [f"`prompteval compare` exited {rc} without a gate verdict"], body)
    if problems := judgement_problems(tag_a, tag_b, expected):
        return not_evaluated(name, problems, body)
    return f"## `{name}`\n\nNot measurably worse.\n\n{body}\n", OK


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
    sections, worse, failed = [], [], []
    for n in names:
        text, status = evaluate(n, base, ROOT / a.work, a.judge_model)
        sections.append(text)
        if status == WORSE:
            worse.append(n)
        elif status != OK:
            failed.append(n)
    verdicts = ([f"worse on {', '.join(worse)}"] if worse else []) + (
        [f"could not evaluate {', '.join(failed)} (blocked, failing closed)"] if failed else [])
    head = ("**Prompt evaluation: " + ("; ".join(verdicts) if verdicts else "no prompt got worse") + ".**"
            + f"\n\nCompared base `{base[:7]}` with this PR for {', '.join(f'`{n}`' for n in names)}. "
            "Each prompt ran on 8 fixture charts captured from the real routes; a judge compared the "
            "two readings per chart in both orders (disagreement is a tie). The check fails only when "
            "the new version is measurably worse (`--gate-mode significant`).\n\n")
    Path(a.out).write_text(head + "\n".join(sections), encoding="utf-8")
    return 1 if worse or failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
