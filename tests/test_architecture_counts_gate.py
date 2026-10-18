"""scripts/verify_architecture_counts.py must be able to go red (#405).

Four of §1's rows are report-only: the count cell reads `measured` and the gate
prints the live value instead of comparing a hand-stored number. That removed
the merge conflicts and ALSO removed the comparison, so the property worth
testing is that the guard survived: a number on a report-only row, `measured`
on any other row, a report-only command that counts 0, a duplicated label or
command, and an unparseable row must each FAIL, and each with its own reason.

`main()` is driven end to end over a doctored temp ARCHITECTURE.md (DOC and ROOT
are monkeypatched, which only works because main() reads them at call time).
Commands in the doctored docs are `echo N`, so nothing here runs the real suite
or touches the real tree, and a mutation that neuters one check turns exactly
the matching test red.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "verify_architecture_counts", ROOT / "scripts" / "verify_architecture_counts.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_architecture_counts"] = gate
_spec.loader.exec_module(gate)

# (label, count cell, command). Six valued rows, four report-only; every command
# is distinct and prints a number > 0 so the clean doc passes.
CLEAN = [
    ("Python", "measured", "echo 101"),
    ("top-level modules", "measured", "echo 102"),
    ("route handlers", "3", "echo 3"),
    ("modules declaring a router", "4", "echo 4"),
    ("top-level templates", "5", "echo 5"),
    ("`/learn` articles", "6", "echo 6"),
    ("LLM prompt templates", "7", "echo 7"),
    ("knowledge files", "2 files, 90 lines", "echo 2; echo 90"),
    ("verification gates", "measured", "echo 103"),
    ("behaviour suite", "measured", "echo 104"),
]


def _doc(rows, extra: str = "") -> str:
    lines = ["# t", "", "## 1. What the system is", "", "| | count | command |", "|---|---|---|"]
    lines += [f"| {a} | {b} | `{c}` |" for a, b, c in rows]
    return "\n".join(lines) + "\n" + extra + "\n## 2. Next\n"


def _run(tmp_path, monkeypatch, capsys, rows=None, extra: str = ""):
    doc = tmp_path / "ARCHITECTURE.md"
    doc.write_text(_doc(CLEAN if rows is None else rows, extra))
    monkeypatch.setattr(gate, "DOC", doc)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    rc = gate.main()
    return rc, capsys.readouterr().out


def _with(label: str, **changes):
    """CLEAN with one row's cells replaced."""
    out = []
    for a, b, c in CLEAN:
        if a == label:
            b, c = changes.get("value", b), changes.get("cmd", c)
        out.append((a, b, c))
    return out


def test_clean_doc_passes_and_prints_the_measured_values(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, capsys)
    assert rc == 0, out
    assert "actual=[104]" in out          # a report-only row still shows its live value
    assert "PASS" in out


def test_wrong_number_on_a_valued_row_fails(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, capsys, _with("route handlers", value="9"))
    assert rc != 0
    assert "route handlers: doc says [9], command gives [3]" in out


def test_a_number_on_a_report_only_row_fails(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, capsys,
                   _with("behaviour suite", value="104 tests"))
    assert rc != 0
    assert "behaviour suite: volatile; a number here is what makes every PR conflict" in out


def test_measured_on_a_valued_row_fails(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, capsys, _with("route handlers", value="measured"))
    assert rc != 0
    assert "route handlers: `measured` is reserved for REPORT_ONLY rows" in out


def test_a_report_only_command_that_counts_zero_fails(tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, capsys, _with("Python", cmd="echo 0"))
    assert rc != 0
    assert "Python: report-only row's command printed [0]" in out


def test_a_duplicate_label_fails(tmp_path, monkeypatch, capsys):
    rows = CLEAN + [("route handlers", "8", "echo 8")]
    rc, out = _run(tmp_path, monkeypatch, capsys, rows)
    assert rc != 0
    assert "duplicate label: route handlers" in out


def test_a_duplicate_command_fails(tmp_path, monkeypatch, capsys):
    rows = CLEAN + [("an extra row", "3", "echo 3")]
    rc, out = _run(tmp_path, monkeypatch, capsys, rows)
    assert rc != 0
    assert "duplicate command: echo 3" in out


def test_an_unparseable_row_fails_rather_than_being_skipped(tmp_path, monkeypatch, capsys):
    # Five cells: it looks like a row (leading pipe, >= 4 pipes, a backticked
    # command) but the pattern cannot read it.
    rc, out = _run(tmp_path, monkeypatch, capsys, extra="| a | b | c | `echo 1` | d |\n")
    assert rc != 0
    assert "unparsed:" in out


def test_a_report_only_row_that_vanished_fails(tmp_path, monkeypatch, capsys):
    # Renamed, not deleted, so EXPECTED_ROWS (a floor) stays satisfied.
    rows = [("renamed", b, c) if a == "Python" else (a, b, c) for a, b, c in CLEAN]
    rc, out = _run(tmp_path, monkeypatch, capsys, rows)
    assert rc != 0
    assert "REPORT_ONLY row 'Python' is not in §1" in out


# What a report-only command may print. The valued rows parse with _numbers(),
# which ignores sign and splits decimals; the report-only check reads the last
# whitespace token whole, so each of these must fail on its own.
@pytest.mark.parametrize("cmd", [
    "echo hello",             # no number at all
    "echo 40; echo 0",        # first > 0, LAST is 0: "last number" is the rule
    "echo -5",                # sign was dropped by _numbers(): read as 5
    "echo 0.5",               # decimal was split: read as [0, 5]
    "echo 7 apples",          # trailing word: last token is not a number
])
def test_a_report_only_command_must_end_in_a_plain_positive_integer(
        cmd, tmp_path, monkeypatch, capsys):
    rc, out = _run(tmp_path, monkeypatch, capsys, _with("Python", cmd=cmd))
    assert rc != 0, out
    assert "Python: report-only row's command printed" in out
    assert "must be a plain positive integer" in out


def test_the_last_number_decides_not_the_first(tmp_path, monkeypatch, capsys):
    # The mirror of `echo 40; echo 0`: leading zero-ish noise is fine when the
    # LAST token is the count, which is what `wc -l` and `awk` really print.
    rc, out = _run(tmp_path, monkeypatch, capsys, _with("Python", cmd="echo 0; echo 40"))
    assert rc == 0, out
    assert "actual=[40]" in out


@pytest.mark.parametrize("cell", ["Measured", "MEASURED", "measured (~32k)"])
def test_measured_must_be_exactly_the_lowercase_word_on_a_report_only_row(
        cell, tmp_path, monkeypatch, capsys):
    # `measured (~32k)` would also smuggle a number back in.
    rc, out = _run(tmp_path, monkeypatch, capsys, _with("behaviour suite", value=cell))
    assert rc != 0, out
    assert "behaviour suite: volatile; a number here is what makes every PR conflict" in out
