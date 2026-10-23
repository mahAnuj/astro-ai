"""scripts/verify_prompt_contracts.py must be able to go red (#362 Part A1).

A gate that has never failed is not evidence. This one exists because ten of
the eleven prompts could be rewritten, sentence by sentence, with every other
gate green (13 sandbox deletions, 13 x `1084 passed`, 2026-10-23). So the
property worth testing is not "the shipped prompts pass" -- pr-gates runs the
script for that, and the first test below is the target the prompt-deletion
rows in scripts/mutate_behaviour_suite.py aim at -- it is "deleting a rule
FAILS, and the failure names the file and the rule".

Everything runs over a temp COPY of the prompts. The real tree is never
written to. The engine is also driven with tiny synthetic tables, because the
shipped table cannot exercise a malformed rule (it has none) and a test that
re-implemented the matching inside its own body would pass forever. Each
engine check has its own test so a mutation that neuters one turns exactly
that test red (mutate_behaviour_suite.py has a row for each).
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "verify_prompt_contracts", ROOT / "scripts" / "verify_prompt_contracts.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_prompt_contracts"] = gate
_spec.loader.exec_module(gate)

PROMPTS = ROOT / "src" / "astro_ai" / "prompts"
TABLE = gate.load_table(gate.TABLE_PATH)


@pytest.fixture
def prompts_copy(tmp_path):
    for f in PROMPTS.glob("*.txt"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def _synthetic(tmp_path, text, rule, *, name="x.txt"):
    """Run the engine over one invented prompt and one invented rule."""
    (tmp_path / name).write_text(text, encoding="utf-8")
    table = {"prompts": {name: {"rules": [{"id": "r", "why": "because", **rule}]}}}
    return gate.run(table, tmp_path, root=tmp_path)[0]


def _delete_line(path: Path, number: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    del lines[number - 1]
    path.write_text("".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# the shipped tree, and the target of the prompt-deletion mutation rows
# --------------------------------------------------------------------------


def test_every_shipped_prompt_satisfies_its_contract():
    failures, report = gate.run(TABLE, PROMPTS)
    assert failures == []
    assert sum(1 for line in report if "asserted" in line) == 10


# --------------------------------------------------------------------------
# coverage (AC1)
# --------------------------------------------------------------------------


def test_a_prompt_with_no_row_fails_naming_the_file(prompts_copy):
    (prompts_copy / "twelfth.txt").write_text("a prompt nobody wrote a contract for")
    failures, _ = gate.run(TABLE, prompts_copy)
    assert len(failures) == 1
    assert failures[0].startswith("twelfth.txt :: ") and "no row" in failures[0]


def test_a_row_for_a_deleted_prompt_fails(prompts_copy):
    (prompts_copy / "daily.txt").unlink()
    failures, _ = gate.run(TABLE, prompts_copy)
    assert len(failures) == 1
    assert failures[0].startswith("daily.txt :: ") and "does not exist" in failures[0]


# --------------------------------------------------------------------------
# AC2 -- deleting any declared rule fails, naming the file and the rule
# --------------------------------------------------------------------------


def test_deleting_any_declared_rule_fails_and_names_the_file_and_the_rule(prompts_copy):
    checked = 0
    unnamed: list[str] = []
    for name, spec in TABLE["prompts"].items():
        if "covered_by" in spec:
            continue
        original = (PROMPTS / name).read_text(encoding="utf-8")
        rules, errors = gate.resolve_rules(TABLE, name, spec)
        assert errors == []
        for rule in rules:
            if not (rule.get("all") or rule.get("same_line")):
                continue  # forbid-only rules protect an absence; test_a_forbidden_phrase_fires
            pins = gate.pin_lines(original, rule)
            assert pins, f"{name} :: {rule['id']} has no pin line, so it cannot be tested"
            (prompts_copy / name).write_text(original, encoding="utf-8")
            _delete_line(prompts_copy / name, pins[0])
            failures, _ = gate.run(TABLE, prompts_copy)
            checked += 1
            if not any(f.startswith(f"{name} :: {rule['id']} - ") for f in failures):
                unnamed.append(f"{name} :: {rule['id']} (line {pins[0]})")
        (prompts_copy / name).write_text(original, encoding="utf-8")
    assert checked > 100, "the table shrank; this test is no longer sweeping the contract"
    assert unnamed == []


def test_removing_the_school_declaration_fails(prompts_copy):
    """AC3: ask_numerology must still say which numerology this is."""
    path = prompts_copy / "ask_numerology.txt"
    text = path.read_text(encoding="utf-8")
    assert "modern Chaldean" in text
    path.write_text(text.replace("modern Chaldean", ""), encoding="utf-8")
    failures, _ = gate.run(TABLE, prompts_copy)
    assert any(f.startswith("ask_numerology.txt :: school-declared-modern-chaldean - ")
               for f in failures)


# --------------------------------------------------------------------------
# natal.txt is accounted for, not skipped
# --------------------------------------------------------------------------


def test_natal_is_reported_as_covered_not_skipped():
    failures, report = gate.run(TABLE, PROMPTS)
    assert failures == []
    assert "  covered  natal.txt  by scripts/verify_natal_prompt.py" in report


def test_a_delegate_that_no_longer_names_natal_fails(prompts_copy, tmp_path_factory):
    root = tmp_path_factory.mktemp("root")
    (root / "scripts").mkdir()
    delegate = root / "scripts" / "verify_natal_prompt.py"
    delegate.write_text("# this gate has been repointed at some other prompt\n")
    failures, _ = gate.run(TABLE, prompts_copy, root=root)
    assert len(failures) == 1
    assert failures[0].startswith("natal.txt :: covered_by - ") and "no longer names" in failures[0]
    delegate.unlink()
    failures, _ = gate.run(TABLE, prompts_copy, root=root)
    assert len(failures) == 1 and "does not exist" in failures[0]


def test_covered_by_cannot_be_combined_with_rules(prompts_copy):
    table = {"prompts": {**TABLE["prompts"]}}
    table["prompts"]["natal.txt"] = {
        "covered_by": "scripts/verify_natal_prompt.py",
        "rules": [{"id": "r", "why": "w", "all": ["x"]}],
    }
    failures, _ = gate.run(table, prompts_copy)
    assert any(f.startswith("natal.txt :: covered_by - ") and "pick one" in f for f in failures)


# --------------------------------------------------------------------------
# headings
# --------------------------------------------------------------------------


def test_a_renamed_or_reordered_heading_fails(prompts_copy):
    path = prompts_copy / "monthly.txt"
    original = path.read_text(encoding="utf-8")

    path.write_text(original.replace("## Money & Wealth", "## Money and Wealth"), encoding="utf-8")
    failures, _ = gate.run(TABLE, prompts_copy)
    assert any(f.startswith("monthly.txt :: headings - ") for f in failures)

    swapped = original.replace("## Money & Wealth", "## @@").replace(
        "## Health", "## Money & Wealth").replace("## @@", "## Health")
    assert swapped != original
    path.write_text(swapped, encoding="utf-8")
    failures, _ = gate.run(TABLE, prompts_copy)
    assert any(f.startswith("monthly.txt :: headings - ") for f in failures)


# --------------------------------------------------------------------------
# the matchers, one test each
# --------------------------------------------------------------------------


def test_a_forbidden_phrase_fires(prompts_copy):
    path = prompts_copy / "ask_matching_third_party.txt"
    path.write_text(path.read_text(encoding="utf-8") + "\nSpeak about you and your partner.\n",
                    encoding="utf-8")
    failures, _ = gate.run(TABLE, prompts_copy)
    assert any(f.startswith("ask_matching_third_party.txt :: first-party-framing-must-not-leak - ")
               and "forbidden phrase" in f for f in failures)


def test_every_pattern_of_an_all_rule_must_match(tmp_path):
    assert _synthetic(tmp_path, "alpha\nbeta\n", {"all": ["alpha", "beta"]}) == []
    (failure,) = _synthetic(tmp_path, "alpha\n", {"all": ["alpha", "beta"]})
    assert failure.startswith("x.txt :: r - ") and "beta" in failure


def test_same_line_needs_one_line_to_state_every_token(tmp_path):
    assert _synthetic(tmp_path, "alpha beta\n", {"same_line": ["alpha", "beta"]}) == []
    (failure,) = _synthetic(tmp_path, "alpha\nbeta\n", {"same_line": ["alpha", "beta"]})
    assert failure.startswith("x.txt :: r - ") and "no single line" in failure


def test_a_rule_whose_words_survive_elsewhere_is_not_pinned(tmp_path):
    """The natal gate's sade-sati flaw: delete the instruction, the words remain."""
    rule = {"all": ["do the thing"]}
    assert _synthetic(tmp_path, "do the thing\nunrelated\n", rule) == []
    (failure,) = _synthetic(tmp_path, "do the thing\nelsewhere, do the thing again\n", rule)
    assert failure.startswith("x.txt :: r - NOT PINNED")
    # a forbid-only rule protects an absence and has nothing to pin
    assert _synthetic(tmp_path, "fine\nfine\n", {"forbid": ["bad"]}) == []


def test_a_row_that_declares_nothing_fails(tmp_path):
    (tmp_path / "x.txt").write_text("anything\n")
    failures, _ = gate.run({"prompts": {"x.txt": {}}}, tmp_path, root=tmp_path)
    assert len(failures) == 1 and failures[0].startswith("x.txt :: row - declares no rules")
    (failure,) = _synthetic(tmp_path, "anything\n", {})
    assert failure.startswith("x.txt :: r - declares nothing")


def test_a_rule_with_no_why_fails(tmp_path):
    (tmp_path / "x.txt").write_text("anything\n")
    table = {"prompts": {"x.txt": {"rules": [{"id": "r", "all": ["anything"]}]}}}
    failures, _ = gate.run(table, tmp_path, root=tmp_path)
    assert failures and failures[0].startswith("x.txt :: r - no `why`")


def test_an_invalid_regex_is_a_named_failure_not_a_traceback(tmp_path):
    (failure,) = _synthetic(tmp_path, "anything\n", {"all": ["unclosed ("]})
    assert failure.startswith("x.txt :: r - invalid regex")


def test_a_misspelt_key_is_a_failure_not_a_silently_dropped_check(tmp_path):
    (failure,) = _synthetic(tmp_path, "anything\n", {"all": ["anything"], "forbd": ["x"]})
    assert failure.startswith("x.txt :: r - unknown key")


def test_an_unknown_group_and_a_duplicate_id_fail(tmp_path):
    (tmp_path / "x.txt").write_text("anything\n")
    table = {"prompts": {"x.txt": {"include": ["nope"], "rules": [
        {"id": "r", "why": "w", "all": ["anything"]},
        {"id": "r", "why": "w", "all": ["anything"]},
    ]}}}
    failures, _ = gate.run(table, tmp_path, root=tmp_path)
    assert any(f.startswith("x.txt :: include - ") for f in failures)
    assert any(f.startswith("x.txt :: r - duplicate rule id") for f in failures)


# --------------------------------------------------------------------------
# exit codes
# --------------------------------------------------------------------------


def test_a_missing_table_is_exit_two_not_zero(tmp_path, capsys):
    assert gate.main(table_path=tmp_path / "absent.toml", prompts_dir=PROMPTS) == 2
    assert "NOT a pass" in capsys.readouterr().out


def test_an_unparseable_table_and_a_missing_prompts_dir_are_exit_two(tmp_path, capsys):
    bad = tmp_path / "bad.toml"
    bad.write_text("this is = = not toml")
    assert gate.main(table_path=bad, prompts_dir=PROMPTS) == 2
    assert gate.main(table_path=gate.TABLE_PATH, prompts_dir=tmp_path / "nowhere") == 2


def test_main_exits_one_on_a_failure_and_zero_on_the_shipped_tree(prompts_copy, capsys):
    assert gate.main() == 0
    (prompts_copy / "twelfth.txt").write_text("x")
    assert gate.main(prompts_dir=prompts_copy) == 1
    assert "twelfth.txt :: " in capsys.readouterr().out


def test_the_gate_has_no_flag_that_rewrites_its_own_table():
    src = (ROOT / "scripts" / "verify_prompt_contracts.py").read_text(encoding="utf-8")
    assert "argparse" not in src and "write_text" not in src and "open(" not in src
