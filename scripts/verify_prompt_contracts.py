#!/usr/bin/env python3
r"""Gate: every `prompts/*.txt` still STATES the rules it is supposed to (#362 Part A1).

WHY THIS EXISTS
---------------
Eleven prompts are the system prompts of every LLM-backed page. Ten of them
could be rewritten, rule by rule, with every gate in the repo green: measured
2026-10-23 by applying 13 single-sentence deletions to a sandbox copy and
running the whole suite each time -- 13 of 13 gave `1084 passed`. Only
`natal.txt` had a content gate (`verify_natal_prompt.py`); `verify_token_budget`
bounds SIZE, which a compression pass satisfies while quietly dropping a safety
rule ("A cancelled dosha still scores ZERO", "Do NOT tell anyone to marry").
Compression is exactly where prompts lose rules, and a prompt change is a
reviewed-by-a-human diff in which a deleted sentence is the hardest thing to see.

So this is the natal gate's idea made table-driven for the other ten: for each
prompt, a list of rules, each rule a few short regexes plus a `why`. The table
is `scripts/prompt_contracts.toml` -- DATA, deliberately not under `prompts/`
(that tree is the trust boundary and ships in the image) and not a dict in this
file (the owner asked for data, and a dict in `.py` is code every reader has to
treat as code). A twelfth prompt with no row FAILS; it is not skipped.

WHAT IT ASSERTS, AND WHAT IT DOES NOT
-------------------------------------
That a prompt still SAYS its rule. Never that the rule is astrologically
correct, and never that the model obeys it (that is #362 Part A2, which spends
tokens and is not built here). Every pattern is read back from text already in
the file; nothing here adds a doctrine.

All matching is `re.IGNORECASE` + `re.search`. Per prompt:

  coverage   a `prompts/*.txt` with no row fails; a row with no file fails.
  natal.txt  carries `covered_by = "scripts/verify_natal_prompt.py"`. The gate
             requires that file to exist AND still name `natal.txt`, then
             REPORTS it as covered. It does not run it (pr-gates already does;
             twice buys nothing) and does not import it. A row cannot combine
             `covered_by` with rules/headings, so the table never pretends to
             double-cover.
  headings   the lines starting `## ` equal `headings` -- text, order, count.
             The routes split a reading on these, so they are a wire format.
  all        every regex must match somewhere in the file.
  same_line  ONE line must match every regex. For list-shaped rules (the nine
             planet names, the avoid-list): losing one ENTRY is the loss a
             file-wide search cannot see.
  forbid     NO regex may match (a sibling prompt's framing leaking in).
  length     there is no `length` key. "Length cap" is read as "the prompt
             still states an N-M words range", written as an ordinary `all`
             rule on `\d+-\d+ words` with the values NOT pinned: retuning
             260-360 to 280-380 is a legitimate edit and must not turn a
             build red (that alarm fatigue is why the sha256 manifest of
             PR #395 was rejected); deleting the range is the defect. Byte and
             token ceilings are NOT duplicated here -- `verify_token_budget`
             owns every size ceiling, and a second copy would be two numbers
             that have to change together.

THE PIN CHECK
-------------
A rule with `all` or `same_line` must have at least one pattern that lands on
exactly ONE line. Otherwise the instruction can be deleted while the same words
survive elsewhere in the file and the rule still "passes" -- anchored but
unprotected. `verify_natal_prompt`'s `sade-sati-named-with-phase` had exactly
this flaw until `mutate_natal_prompt_gate.py` found it by hand. A `forbid`-only
rule is exempt (it protects an absence). The failure says NOT PINNED and means:
sharpen one pattern until it is unique, do not delete the check.

TABLE SEMANTICS
---------------
`[groups.<name>]` holds a rule set that two or more prompts share (the shared
safety block of the two matching overlays, which already drifted once). A row
pulls it in with `include`. Rule ids are unique within a file, groups included.
Unknown keys, unknown groups, an invalid regex, a rule with no `why` and a rule
that declares nothing are each a NAMED failure, never a traceback. Every
failure begins `<file> :: <rule-id> - ` so a red run says what to look at.

NO --update, NO FLAGS
---------------------
There is no flag that regenerates the table, and there never should be: a gate
that writes its own expectations passes on anything (PR #395). Deliberately
rewording an anchored sentence trips this gate, and the same (human-held) PR
updates the row -- that is the intended behaviour, not a false alarm.

NO LLM, NO NETWORK, ZERO RUNTIME TOKENS
---------------------------------------
Standard library only (`tomllib`, `re`, `pathlib`, `sys`). It reads the
prompts and one TOML file.

Exit 0 pass / 1 fail / 2 could not run (table or prompts directory missing or
unparseable). **Exit 2 is NOT a pass.**

    uv run python scripts/verify_prompt_contracts.py
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "src" / "astro_ai" / "prompts"
TABLE_PATH = REPO_ROOT / "scripts" / "prompt_contracts.toml"

_ROW_KEYS = {"covered_by", "include", "headings", "rules"}
_RULE_KEYS = {"id", "why", "all", "same_line", "forbid"}
_PATTERN_KEYS = ("all", "same_line", "forbid")


class CouldNotRun(Exception):
    """The gate could not even look (exit 2). Never a pass."""


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def headings_of(text: str) -> list[str]:
    """The `## ` lines, as the routes split a reading on them."""
    return [line[3:].rstrip() for line in text.splitlines() if line.startswith("## ")]


def pin_lines(text: str, rule: dict) -> list[int]:
    """1-based numbers of lines that carry a rule's instruction ALONE.

    A pattern (or, for `same_line`, the whole list) that lands on exactly one
    line pins the rule to that line: delete the line and the rule must fail.
    Empty means the words can survive a deletion, i.e. NOT PINNED.
    """
    pins: list[int] = []
    for pattern in rule.get("all", []):
        hit = sorted({_line_of(text, m.start()) for m in _rx(pattern).finditer(text)})
        if len(hit) == 1:
            pins.append(hit[0])
    same = rule.get("same_line")
    if same:
        regexes = [_rx(p) for p in same]
        hit = [n for n, line in enumerate(text.splitlines(), 1)
               if all(r.search(line) for r in regexes)]
        if len(hit) == 1:
            pins.append(hit[0])
    return sorted(set(pins))


def resolve_rules(table: dict, name: str, spec: dict) -> tuple[list[dict], list[str]]:
    """The rules a row is held to (groups first, then its own) and any table errors."""
    rules: list[dict] = []
    errors: list[str] = []
    groups = table.get("groups", {})
    for group in spec.get("include", []):
        if group not in groups:
            errors.append(f"{name} :: include - no [groups.{group}] in the table")
            continue
        rules.extend(groups[group].get("rules", []))
    rules.extend(spec.get("rules", []))
    seen: set[str] = set()
    for rule in rules:
        rid = rule.get("id")
        if rid in seen:
            errors.append(f"{name} :: {rid} - duplicate rule id (ids are unique per file, groups included)")
        seen.add(rid)
    return rules, errors


def check_rule(name: str, text: str, rule: dict) -> list[str]:
    """Every failure for one rule against one prompt's text."""
    rid = rule.get("id") or "<rule with no id>"
    head = f"{name} :: {rid} - "
    unknown = sorted(set(rule) - _RULE_KEYS)
    if unknown:
        return [head + f"unknown key(s) {unknown}; a typo here would silently drop a check"]
    for key in _PATTERN_KEYS:
        if key in rule and not (isinstance(rule[key], list) and all(isinstance(p, str) for p in rule[key])):
            return [head + f"`{key}` must be a list of regex strings"]
    for pattern in [p for key in _PATTERN_KEYS for p in rule.get(key, [])]:
        try:
            _rx(pattern)
        except re.error as exc:
            return [head + f"invalid regex {pattern!r}: {exc}"]

    fails: list[str] = []
    if not rule.get("why"):
        fails.append(head + "no `why` (what breaks if this goes is the point of the row)")
    if not any(rule.get(key) for key in _PATTERN_KEYS):
        fails.append(head + "declares nothing (needs all, same_line or forbid)")

    missing = [p for p in rule.get("all", []) if not _rx(p).search(text)]
    if missing:
        fails.append(head + f"missing {len(missing)} required pattern(s): {missing}")

    same = rule.get("same_line")
    if same:
        regexes = [_rx(p) for p in same]
        if not any(all(r.search(line) for r in regexes) for line in text.splitlines()):
            fails.append(head + f"no single line states all of: {same}")

    for pattern in rule.get("forbid", []):
        m = _rx(pattern).search(text)
        if m:
            fails.append(head + f"forbidden phrase present (line {_line_of(text, m.start())}): {m.group(0)!r}")

    # Only judged when the rule otherwise holds: a rule that already failed
    # would report NOT PINNED for the very deletion it just caught.
    if (rule.get("all") or same) and not fails and not pin_lines(text, rule):
        fails.append(head + "NOT PINNED - no pattern lands on exactly one line, so the instruction "
                     "can be deleted while the same words survive elsewhere; sharpen one pattern")
    return fails


def check_covered(name: str, spec: dict, root: Path) -> tuple[list[str], list[str]]:
    """A row delegated to another gate: the delegate must exist and still name the file."""
    other = [k for k in ("include", "headings", "rules") if k in spec]
    if other:
        return [f"{name} :: covered_by - cannot combine with {other}; pick one so the table "
                f"never pretends to double-cover"], []
    delegate = root / spec["covered_by"]
    if not delegate.is_file():
        return [f"{name} :: covered_by - {spec['covered_by']} does not exist"], []
    if name not in delegate.read_text(encoding="utf-8"):
        return [f"{name} :: covered_by - {spec['covered_by']} no longer names {name}; "
                f"nothing is asserting this prompt"], []
    return [], [f"  covered  {name}  by {spec['covered_by']}"]


def check_prompt(table: dict, name: str, spec: dict, text: str) -> tuple[list[str], str]:
    """Failures and the report line for one asserted prompt."""
    unknown = sorted(set(spec) - _ROW_KEYS)
    if unknown:
        return [f"{name} :: row - unknown key(s) {unknown}"], f"  asserted {name}  (malformed row)"
    fails: list[str] = []
    want = spec.get("headings", [])
    got = headings_of(text)
    if got != want:
        fails.append(f"{name} :: headings - expected {want}, found {got}")
    rules, errors = resolve_rules(table, name, spec)
    fails.extend(errors)
    if not rules:
        fails.append(f"{name} :: row - declares no rules (a row that asserts nothing is a skip in disguise)")
    for rule in rules:
        fails.extend(check_rule(name, text, rule))
    return fails, f"  asserted {name}  {len(rules)} rules, {len(want)} headings"


def run(table: dict, prompts_dir: Path, root: Path = REPO_ROOT) -> tuple[list[str], list[str]]:
    """Pure core: (failures, report lines) for a table against a directory of prompts."""
    fails: list[str] = []
    report: list[str] = []
    on_disk = {p.name for p in prompts_dir.glob("*.txt")}
    rows = table.get("prompts", {})

    extra = sorted(on_disk - set(rows))
    for name in extra:
        fails.append(f"{name} :: coverage - no row in scripts/prompt_contracts.toml. Every "
                     f"prompts/*.txt needs one; a prompt covered by nothing cannot ship")
    stale = sorted(set(rows) - on_disk)
    for name in stale:
        fails.append(f"{name} :: coverage - a table row for a prompt file that does not exist")

    for name in sorted(on_disk & set(rows)):
        spec = rows[name]
        if "covered_by" in spec:
            problems, lines = check_covered(name, spec, root)
            fails.extend(problems)
            report.extend(lines)
            continue
        try:
            text = (prompts_dir / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            fails.append(f"{name} :: file - unreadable: {exc}")
            continue
        problems, line = check_prompt(table, name, spec, text)
        fails.extend(problems)
        report.append(line)
    return fails, report


def load_table(path: Path) -> dict:
    if not path.is_file():
        raise CouldNotRun(f"{path} is missing")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise CouldNotRun(f"{path} does not parse: {exc}") from exc


def main(table_path: Path = TABLE_PATH, prompts_dir: Path = PROMPTS_DIR, root: Path = REPO_ROOT) -> int:
    print("Prompt contract gate (#362 A1) - does each prompt still STATE its rules?")
    try:
        if not prompts_dir.is_dir():
            raise CouldNotRun(f"{prompts_dir} is not a directory")
        table = load_table(table_path)
    except CouldNotRun as exc:
        print(f"  COULD NOT VERIFY: {exc}")
        print("  -> SKIPPED (exit 2). This is NOT a pass - the check did not run.")
        return 2

    failures, report = run(table, prompts_dir, root)
    print("\n".join(report))
    delegated = sum(1 for line in report if line.startswith("  covered"))
    asserted = len(report) - delegated

    if failures:
        print(f"\nFAIL - {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nPASS - {asserted} asserted, {delegated} covered by another gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
