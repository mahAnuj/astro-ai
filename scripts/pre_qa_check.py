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

THEME CHECKS (#1255) -- the three themes QA fails on most
measurements/lessons.json, 2026-11-25, counted by FAIL theme: regression 31,
grounding 30, tests 26 (copy and tokens 17). `THEME_CHECKS` below holds, per theme,
the checks that can see that class of defect in a diff in seconds, so a round is not
spent finding it. They run after the gates and before pytest and print one line,
`themes: regression PASS grounding PASS tests PASS`. They are narrow on purpose: a
check that cried wolf would be waived by habit. GROUNDING IS A PROXY -- it can see
that a claim-bearing file changed with no `corpus:` line in a commit and no citation in
this change's docs/decisions file, never whether the claim is true; `qa`, `astro-auditor`
and `verify_rule_citations` judge that.

EXIT CODES
  0  every fast gate passed and the diff's tests passed
  1  something failed -- the tail of each failing gate is printed
  2  something COULD NOT RUN (a gate exited 2, timed out or is missing; the
     diff could not be computed; pytest could not collect). Never a pass.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
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


# --- THEME CHECKS (#1255) ----------------------------------------------------

class CannotCompute(Exception):
    """A theme check could not decide. Exit 2, never a pass."""


@dataclass
class DiffContext:
    """What a theme check may look at: the diff against the merge base, nothing else."""
    changed: list[str]
    added: dict[str, list[str]] = field(default_factory=dict)     # path -> added lines
    removed: dict[str, list[str]] = field(default_factory=dict)   # path -> removed lines
    commits: list[str] = field(default_factory=list)              # base..HEAD messages


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          timeout=60, check=True).stdout


def diff_context(changed: list[str]) -> DiffContext | None:
    """The diff's added and removed lines. None when git cannot say -- the caller
    turns that into exit 2. An empty diff needs no git at all."""
    if not changed:
        return DiffContext([])
    try:
        base = _git("merge-base", BASE_REF, "HEAD").strip()
        diff = _git("diff", "--unified=0", "--no-color", base)
        log = _git("log", "--format=%B%x1e", f"{base}..HEAD")
        untracked = _git("ls-files", "--others", "--exclude-standard")
    except (subprocess.SubprocessError, OSError):
        return None
    ctx = DiffContext(list(changed), commits=[m.strip() for m in log.split("\x1e") if m.strip()])
    old = new = ""
    header = False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            header = True
        elif line.startswith("@@"):
            header = False
        elif header and line.startswith("--- "):
            old = line[4:].removeprefix("a/")
        elif header and line.startswith("+++ "):
            new = line[4:].removeprefix("b/")
        elif not header and line.startswith("+"):
            ctx.added.setdefault(old if new == "/dev/null" else new, []).append(line[1:])
        elif not header and line.startswith("-"):
            ctx.removed.setdefault(new if old == "/dev/null" else old, []).append(line[1:])
    for p in untracked.splitlines():
        f = ROOT / p
        if p.endswith((".py", ".html", ".md", ".txt")) and f.is_file():
            ctx.added[p] = f.read_text(encoding="utf-8", errors="replace").splitlines()
    return ctx


_CODE_ROOTS = ("src/astro_ai/", "scripts/")
_DEF = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+\w+")


def check_tests_accompany_code(ctx: DiffContext) -> list[str]:
    """Code that gained a def or class with no file under tests/ in the diff."""
    if any(p.startswith("tests/") for p in ctx.changed):
        return []
    hits = [p for p, lines in ctx.added.items()
            if p.endswith(".py") and p.startswith(_CODE_ROOTS) and not p.startswith("scripts/mutations/")
            and any(_DEF.match(x) for x in lines)]
    return [f"{p} gained a def or class and the diff touches no file under tests/" for p in sorted(hits)]


def _mutation_rows(path: Path) -> list:
    """Load a mutation file the way `mutate_behaviour_suite._load_area_rows` does (exec it into a
    namespace), because a third of the files build rows from module constants (`_GA = "..."`)
    that `ast.literal_eval` cannot resolve (QA FAIL on #1475: 95 of 263 files)."""
    ns: dict = {}
    try:
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)  # noqa: S102 - data-only table, as the suite does
    except Exception as e:  # noqa: BLE001 - any failure to load is "cannot compute", never a pass
        raise CannotCompute(f"{path.name}: cannot be loaded ({type(e).__name__}: {e})") from e
    table = ns.get("MUTATIONS")
    if not isinstance(table, list):
        raise CannotCompute(f"{path.name}: no MUTATIONS list")
    return table


def check_mutation_rows_live(ctx: DiffContext) -> list[str]:
    """A changed mutation row whose anchor is not in its file exactly once, or whose
    test exists nowhere, can never be killed -- the static form of `survived`."""
    problems: list[str] = []
    tests_text = None
    for p in sorted(ctx.changed):
        path = ROOT / p
        if not (p.startswith("scripts/mutations/") and p.endswith(".py") and path.is_file()):
            continue
        for row in _mutation_rows(path):
            if not (isinstance(row, (tuple, list)) and len(row) == 5):
                problems.append(f"{p}: a row is not a (label, file, old, new, test) 5-tuple")
                continue
            label, rel, old, _new, test = row
            target = ROOT / rel
            if not target.is_file():
                problems.append(f"{p}: '{label[:50]}' targets {rel}, which does not exist")
                continue
            n = target.read_text(encoding="utf-8").count(old)
            if n != 1:
                problems.append(f"{p}: '{label[:50]}' anchor occurs {n}x in {rel}, needs exactly 1")
            if tests_text is None:
                tests_text = "\n".join(t.read_text(encoding="utf-8", errors="replace")
                                       for t in (ROOT / "tests").rglob("*.py"))
            name = str(test).split("[", 1)[0]
            if not re.search(rf"\bdef {re.escape(name)}\b", tests_text):
                problems.append(f"{p}: '{label[:50]}' names test {name}, which is defined nowhere in tests/")
    return problems


def check_python_parses(ctx: DiffContext) -> list[str]:
    problems = []
    for p in sorted(ctx.changed):
        if p.endswith(".py") and (ROOT / p).is_file():
            try:
                ast.parse((ROOT / p).read_text(encoding="utf-8"))
            except SyntaxError as e:
                problems.append(f"{p}:{e.lineno}: {e.msg}")
    return problems


def check_templates_parse(ctx: DiffContext) -> list[str]:
    paths = [p for p in sorted(ctx.changed)
             if p.startswith("src/astro_ai/templates/") and p.endswith(".html") and (ROOT / p).is_file()]
    if not paths:
        return []
    try:
        import jinja2
    except ImportError as e:
        raise CannotCompute(f"jinja2 is not importable ({e})") from e
    env, problems = jinja2.Environment(), []
    for p in paths:
        try:
            env.parse((ROOT / p).read_text(encoding="utf-8"))
        except jinja2.TemplateSyntaxError as e:
            problems.append(f"{p}:{e.lineno}: {e.message}")
    return problems


_TOP_NAME = re.compile(r"^(?:async\s+)?(?:def|class)\s+(\w+)|^([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=(?!=)")


def _top_names(lines: list[str]) -> set[str]:
    return {m.group(1) or m.group(2) for m in map(_TOP_NAME.match, lines) if m}


def _referenced(name: str, stem: str) -> list[str]:
    """Where `name` is USED in code (never in a string): a bare name, an import, or
    `<module stem>.name`. Attribute access on anything else is not counted -- a removed
    `load` must not fail on every other object's `.load`."""
    out: list[str] = []
    for root in ("src/astro_ai", "scripts", "tests"):
        for f in sorted((ROOT / root).rglob("*.py")):
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                hit = ((isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load))
                       or (isinstance(n, ast.ImportFrom) and any(a.name == name for a in n.names))
                       or (isinstance(n, ast.Attribute) and n.attr == name
                           and isinstance(n.value, ast.Name) and n.value.id == stem))
                if hit:
                    out.append(f"{f.relative_to(ROOT)}:{n.lineno}")
    return out


def check_removed_names_unreferenced(ctx: DiffContext) -> list[str]:
    """A top-level def, class or CONSTANT the diff removed (and nothing re-added) that code
    still names -- the shape of a regression a rename or a deletion leaves behind."""
    readded = set()
    for p, lines in ctx.added.items():
        if p.endswith(".py"):
            readded |= _top_names(lines)
    problems = []
    for p, lines in sorted(ctx.removed.items()):
        if not p.endswith(".py"):
            continue
        for name in sorted(_top_names(lines) - readded):
            if name.startswith(("test_", "Test")):
                continue
            refs = _referenced(name, Path(p).stem)
            if refs:
                problems.append(f"{p} removed `{name}`, still used at {', '.join(refs[:3])}"
                                f"{' ...' if len(refs) > 3 else ''}")
    return problems


_CLAIM_DIRS = ("src/astro_ai/knowledge/", "src/astro_ai/prompts/", "src/astro_ai/templates/learn/")
_CLAIM_FILES = re.compile(r"^src/astro_ai/(?:chart|matching|muhurat\w*)\.py$")
# #1478: a squash merge drops commit-message lines, so the decision file is the other
# place a change records where a claim came from. README.md is the format guide, not a decision.
_DECISION = re.compile(r"^docs/decisions/(?!README\.md$)[^/]+\.md$")
_CITES = re.compile(r"(?i)^\s*corpus:|\bknowledge/[A-Za-z0-9_.-]+\.md\b")


def check_grounding_proxy(ctx: DiffContext) -> list[str]:
    """PROXY. A claim-bearing path changed, no commit since the merge base carries a
    `corpus:` line, and no knowledge/*.md changed. It cannot tell whether a claim is
    TRUE -- `qa`, `astro-auditor` and verify_rule_citations do that -- only that nobody
    wrote down where it came from. Where it may be written down (#1478): a `corpus:` line in
    a commit, or an ADDED line of a changed docs/decisions/*.md that has a `corpus:` line or
    names a knowledge/*.md file. The file merely existing never passes, and a negative
    mention of knowledge/x.md passes too -- the proxy cannot see negation."""
    touched = [p for p in ctx.changed if p.startswith(_CLAIM_DIRS) or _CLAIM_FILES.match(p)]
    if not touched:
        return []
    if any(p.startswith("src/astro_ai/knowledge/") and p.endswith(".md") for p in ctx.changed):
        return []
    if any(_CITES.search(line)
           for p in ctx.changed if _DECISION.match(p)
           for line in ctx.added.get(p, ())):
        return []
    if any(re.search(r"(?im)^\s*corpus:", m) for m in ctx.commits):
        return []
    return [f"{p} can carry an astrological claim; no commit since the merge base has a "
            f"`corpus:` line, no knowledge/*.md changed and no added line of this change's "
            f"docs/decisions/*.md cites one (put a `corpus:` line in a commit, or cite "
            f"`knowledge/<file>.md`, or `corpus: n/a -- why`, in the decision file)"
            for p in sorted(touched)[:5]]


#: theme -> the checks that can see that class of defect in a diff.
THEME_CHECKS: dict[str, tuple] = {
    "regression": (check_python_parses, check_templates_parse, check_removed_names_unreferenced),
    "grounding": (check_grounding_proxy,),
    "tests": (check_tests_accompany_code, check_mutation_rows_live),
}


def run_themes(ctx: DiffContext) -> tuple[dict[str, list[str]], list[str]]:
    """({theme: problems}, [themes that could not compute])."""
    results: dict[str, list[str]] = {}
    unrun: list[str] = []
    for theme, checks in THEME_CHECKS.items():
        problems: list[str] = []
        try:
            for check in checks:
                problems += check(ctx)
        except CannotCompute as e:
            unrun.append(theme)
            problems.append(f"COULD NOT RUN: {e}")
        results[theme] = problems
    return results, unrun


def _themes_into(changed: list[str], failed: list[str], unrun: list[str]) -> None:
    ctx = diff_context(changed)
    if ctx is None:
        print(f"  {'themes':<34} COULD NOT RUN    -- no diff against {BASE_REF}")
        unrun.append("themes")
        return
    results, cannot = run_themes(ctx)
    cells = []
    for theme, problems in results.items():
        verdict = "COULD NOT RUN" if theme in cannot else "FAIL" if problems else "PASS"
        cells.append(f"{theme} {verdict}")
        if verdict == "FAIL":
            failed.append(f"theme:{theme}")
        elif verdict != "PASS":
            unrun.append(f"theme:{theme}")
    line = "themes: " + " ".join(cells)
    print(line)
    for theme, problems in results.items():
        for prob in problems:
            print(f"    [{theme}] {prob}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(f"- pre-QA {line}\n")
        except OSError:
            pass


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
        _themes_into(changed, failed, unrun)
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
    print(f"pre-QA check: PASS ({len(gates)} gates + themes + diff tests) in {total:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
