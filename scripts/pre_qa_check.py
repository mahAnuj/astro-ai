#!/usr/bin/env python3
"""The cheap half of pr-gates, run by a build cycle BEFORE it dispatches QA.

WHY THIS EXISTS

A QA round is a separate agent with its own full context: millions of cached
tokens and minutes of wall-clock. Measured on agent-work run 44020807802
(#1067 / PR #1150): THREE rounds, and rounds 1 and 2 each failed only on a
stale `ARCHITECTURE.md` line -- a stale sentence, then the template count
58 -> 59 -- which `verify_architecture_counts.py` reports in seconds. Two
rounds were spent being a slow, expensive copy of a script.

So `/agent-cycle` runs this first and dispatches QA only on PASS. It does NOT
replace pr-gates, and a PASS here is not a verdict: it is the subset of
pr-gates that needs no network, no LLM, no running server and no long sweep,
so a failure it can see never costs a round.

NOT NAMED `verify_*` ON PURPOSE. pr-gates runs every `scripts/verify_*.py`
with no arguments as a gate, and a mis-named script turned PR #1063 red.

THE GATE LIST LIVES HERE, AND IS PINNED TO pr-gates

pr-gates' sweep is `scripts/verify_*.py` minus `NEEDS_LIVE_LLM`. Every one of
those scripts is classified below as FAST (run here) or SLOW (left to pr-gates,
with the reason). `tests/test_pre_qa_check.py` fails if a verify script is in
neither, in both, or named here and absent from the sweep -- so a new gate
cannot be silently skipped by this check, and a renamed one cannot leave a
dead entry behind.

Timings are wall-clock from one sequential local run on 2026-11-17 (this
script runs FAST in parallel, so the whole check is shorter than their sum).

EXIT CODES
  0  every fast gate passed and the diff's tests passed
  1  something failed -- the tail of each failing gate is printed
  2  something COULD NOT RUN (a gate exited 2, timed out or is missing; the
     diff could not be computed; pytest could not collect). Never a pass.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: pr-gates gates that are cheap and need nothing outside the checkout.
#: Seconds measured locally 2026-11-17, sequential.
FAST_GATES: tuple[str, ...] = (
    "verify_adhik_maas",               # 13.7s
    "verify_agent_cycle_doc",          # 0.5s
    "verify_agent_trail",              # 0.1s
    "verify_architecture_counts",      # 8.5s  <- the #1067 rounds 1 and 2
    "verify_conflict_markers",         # 0.3s
    "verify_contrast",                 # 0.2s
    "verify_corpus_search",            # 0.1s
    "verify_css_build",                # 3.1s  (exit 2 without node; agent-work runs npm ci)
    "verify_egress",                   # 0.5s
    "verify_email_templates",          # 0.8s
    "verify_festivals",                # 0.1s
    "verify_gochar_table",             # 4.9s
    "verify_issue_evidence",           # 0.1s
    "verify_learn_article_dates",      # 11.5s
    "verify_lo_shu_attribution",       # 0.1s
    "verify_lunar_observances",        # 0.7s
    "verify_manglik_coherence",        # 22.1s
    "verify_muhurat_tables",           # 39.8s  (the long pole of the parallel run)
    "verify_natal_prompt",             # 9.3s
    "verify_no_relaxation",            # 0.1s
    "verify_numerology_copy",          # 1.0s
    "verify_numerology_reduction",     # 3.1s
    "verify_panchang_angas",           # 7.4s
    "verify_pii_egress",               # 9.2s
    "verify_prompt_contracts",         # 0.1s
    "verify_redesign_tokens",          # 0.1s
    "verify_rule_citations",           # 2.3s
    "verify_seo_copy",                 # 0.1s
    "verify_test_floor",               # 0.4s
    "verify_token_budget",             # 2.9s
    "verify_workflow_permissions",     # 0.1s
    "verify_workflows",                # 0.8s
)

#: pr-gates gates deliberately NOT run here, each with its reason.
SLOW_GATES: dict[str, str] = {
    "verify_behaviour": "the whole behaviour suite, 152.7s; the diff's own tests run instead",
    "verify_devanagari_serif": "needs the app serving on 127.0.0.1:8000 (NEEDS_SERVER in pr-gates)",
    "verify_lang_switch_browser": "drives Chromium against the app (NEEDS_SERVER in pr-gates)",
}

#: Not in pr-gates' sweep at all (NEEDS_LIVE_LLM there); listed so the
#: partition test can account for every verify_*.py.
LIVE_LLM_GATES: tuple[str, ...] = ("verify_english_surface", "verify_hindi_surface")

GATE_TIMEOUT = 300
TAIL = 25
BASE_REF = "origin/main"

#: A change to any of these can break any test, so the whole suite runs.
_HARNESS = ("tests/conftest.py", "pyproject.toml", "uv.lock")


def _run(cmd: list[str], timeout: int = GATE_TIMEOUT) -> tuple[int, str, float]:
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        out, rc = (r.stdout or "") + (r.stderr or ""), r.returncode
    except subprocess.TimeoutExpired:
        out, rc = f"TIMED OUT after {timeout}s -- the check did not finish", 2
    except OSError as e:
        out, rc = f"could not start: {e}", 2
    return rc, out, time.monotonic() - t0


def run_gate(name: str) -> tuple[str, int, str, float]:
    path = ROOT / "scripts" / f"{name}.py"
    if not path.is_file():
        return name, 2, f"{path} does not exist -- the gate list is stale", 0.0
    rc, out, dt = _run([sys.executable, str(path)])
    return name, rc, out, dt


def changed_files() -> list[str] | None:
    """Files changed against the merge base with origin/main, committed or not.

    None when the diff cannot be computed -- the caller turns that into exit 2,
    never into "nothing changed".
    """
    try:
        base = subprocess.run(["git", "merge-base", BASE_REF, "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=60, check=True).stdout.strip()
        diff = subprocess.run(["git", "diff", "--name-only", base], cwd=ROOT,
                              capture_output=True, text=True, timeout=60, check=True).stdout
        new = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT,
                             capture_output=True, text=True, timeout=60, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    return sorted({p for p in (diff + new).splitlines() if p})


def tests_for(changed: list[str]) -> list[str] | str:
    """The test files the diff touches: changed tests, plus tests that name a
    changed module. Returns "ALL" when a harness file changed.

    The mapping is textual on purpose -- a test that names `chart.py`,
    `astro_ai.chart` or `import chart` is selected -- because it is cheap and
    over-selects rather than under-selects. pr-gates still runs the full suite.
    """
    if any(p in _HARNESS for p in changed):
        return "ALL"
    tests_dir = ROOT / "tests"
    picked = {p for p in changed
              if p.startswith("tests/") and Path(p).name.startswith("test_")
              and p.endswith(".py") and (ROOT / p).is_file()}
    needles: list[re.Pattern[str]] = []
    for p in changed:
        if not p.endswith(".py") or p.startswith("tests/"):
            continue
        stem = Path(p).stem
        if stem == "__init__":
            continue
        pats = [rf"\b{re.escape(stem)}\.py\b", rf"\bimport\s+{re.escape(stem)}\b",
                rf"\bfrom\s+\S*\b{re.escape(stem)}\s+import\b",
                rf"\bfrom\s+[\w.]+\s+import\s+[^\n]*\b{re.escape(stem)}\b"]
        if p.startswith("src/"):
            dotted = p[len("src/"):-len(".py")].replace("/", ".")
            pats.append(rf"\b{re.escape(dotted)}\b")
        needles.append(re.compile("|".join(pats)))
    if needles:
        for t in sorted(tests_dir.glob("test_*.py")):
            text = t.read_text(encoding="utf-8", errors="replace")
            if any(n.search(text) for n in needles):
                picked.add(f"tests/{t.name}")
    return sorted(picked)


def main(gates: tuple[str, ...] | None = None) -> int:
    gates = FAST_GATES if gates is None else gates
    t0 = time.monotonic()
    failed: list[str] = []
    unrun: list[str] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run_gate, gates))
    for name, rc, out, dt in results:
        verdict = {0: "PASS", 2: "COULD NOT RUN"}.get(rc, f"FAIL (exit {rc})")
        print(f"  {name:<34} {verdict:<16} {dt:6.1f}s")
        if rc == 0:
            continue
        (unrun if rc == 2 else failed).append(name)
        print("    " + "\n    ".join(out.rstrip().splitlines()[-TAIL:]))

    changed = changed_files()
    if changed is None:
        print(f"  {'pytest (diff tests)':<34} COULD NOT RUN    -- no diff against {BASE_REF}")
        unrun.append("pytest")
    else:
        sel = tests_for(changed)
        if sel == []:
            print(f"  {'pytest (diff tests)':<34} none touched by the diff")
        else:
            args = [] if sel == "ALL" else list(sel)
            rc, out, dt = _run([sys.executable, "-m", "pytest", "-q", "-x", *args], timeout=600)
            label = "pytest (whole suite)" if sel == "ALL" else f"pytest ({len(args)} files)"
            verdict = {0: "PASS", 1: "FAIL"}.get(rc, f"COULD NOT RUN (exit {rc})")
            print(f"  {label:<34} {verdict:<16} {dt:6.1f}s")
            if rc != 0:
                (failed if rc == 1 else unrun).append("pytest")
                print("    " + "\n    ".join(out.rstrip().splitlines()[-TAIL:]))

    total = time.monotonic() - t0
    if failed:
        print(f"pre-QA check: FAIL ({', '.join(failed)}) in {total:.0f}s -- fix before dispatching QA")
        return 1
    if unrun:
        print(f"pre-QA check: COULD NOT RUN ({', '.join(unrun)}) in {total:.0f}s -- this is NOT a pass")
        return 2
    print(f"pre-QA check: PASS ({len(gates)} gates + diff tests) in {total:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
