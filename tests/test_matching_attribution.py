"""#914: `matching.py` may not credit a rule to a book this repo does not hold.

`matching.py` credited Brihat Parashara Hora Shastra in its module docstring (the
#216 defect) while `scripts/verify_rule_citations.py` printed PASS, because the gate
read `chart.py` and `muhurat.py` only. Check 8 scans the whole of `matching.py` as
text. Muhurta Chintamani, which `knowledge/matching.md` records as held but which
`fetch_corpus.py` does not register, passes through an EXACT ledger; these tests pin
the scan, the ledger's three failure modes and the fail-closed paths.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "verify_rule_citations", ROOT / "scripts" / "verify_rule_citations.py")
vrc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vrc)

MATCHING = ROOT / "src" / "astro_ai" / "matching.py"
_ANCHOR = "def compute_guna_milan"
_REAL_REGISTRY = set(vrc._registry()[0])


def _text() -> str:
    return MATCHING.read_text(encoding="utf-8")


def _with(line: str) -> str:
    text = _text()
    assert _ANCHOR in text
    return text.replace(_ANCHOR, f"{line}\n{_ANCHOR}", 1)


def test_the_real_matching_file_names_no_unheld_book():
    assert vrc._matching_problems(_text()) == []


def test_the_registry_still_lacks_muhurta_chintamani():
    # The ledger is only sanctioned while this is true. When #914 step 1 lands
    # this test goes red together with the gate, and both want the same edit:
    # delete `_MATCHING_HELD_UNREGISTERED`'s entry and this test.
    assert not any("chintamani" in t.lower() for t in _REAL_REGISTRY)


@pytest.mark.parametrize("line", [
    "# BPHS gives the 36-point weights.",
    "# Per Brihat Parashara Hora Shastra.",
    "# bphs awards these points.",
    "# Per B.P.H.S. here.",
    "# Per Parasara Hora Sastra.",
    "# Per Brihat\n# Parashara Hora Shastra.",    # wrapped across a comment line
    "# Sources: Phaladeepika.",
    "# Sources: Phaladipika.",
    "# See Jataka Parijata.",
    "# See Jataka Chandrika.",
    "# Sources: Ashvalayana Grihya Sutra.",
    '"""Per BPHS."""',                           # a docstring, not a comment
])
def test_each_unheld_name_and_spelling_is_red(line):
    assert vrc._matching_problems(_with(line)), line


def test_the_module_docstring_credit_that_shipped_is_red():
    # The literal defect #914 found, restored.
    text = _text()
    marker = "References: "
    assert marker in text
    bad = text.replace(marker, marker + "Brihat Parashara Hora Shastra; ", 1)
    fails = vrc._matching_problems(bad)
    assert fails and fails[0].startswith("matching.py:")


def test_the_failure_names_the_line_it_is_on():
    text = _with("# BPHS marks this.")
    expected = text.split("\n").index("# BPHS marks this.") + 1
    fails = vrc._matching_problems(text)
    assert any(f.startswith(f"matching.py:{expected}:") for f in fails), fails


def test_a_file_without_its_anchors_fails_closed():
    assert vrc._matching_problems("# nothing here\n")
    # Anchor moved: the other half of the pair is also required.
    assert vrc._matching_problems(_text().replace("MATCHING_RULES_VERSION", "X"))
    assert vrc._matching_problems(_text().replace(_ANCHOR, "def renamed"))


# --- the Muhurta Chintamani ledger is exact ---------------------------------

def test_the_ledger_has_exactly_one_entry_and_it_is_muhurta_chintamani():
    assert list(vrc._MATCHING_HELD_UNREGISTERED) == ["Muhurta Chintamani"]
    assert "#914" in vrc._MATCHING_HELD_UNREGISTERED["Muhurta Chintamani"]


def test_naming_muhurta_chintamani_without_a_ledger_entry_is_red():
    fails = vrc._matching_problems(_text(), ledger={}, registered=_REAL_REGISTRY)
    assert fails and "Muhurta Chintamani" in fails[0]


def test_a_new_ledger_entry_is_red():
    ledger = {**vrc._MATCHING_HELD_UNREGISTERED, "Phaladeepika": "to turn green"}
    fails = vrc._matching_problems(_text(), ledger=ledger, registered=_REAL_REGISTRY)
    assert any("Phaladeepika" in f for f in fails)


def test_a_stale_ledger_entry_is_red_once_the_registry_registers_the_book():
    reg = _REAL_REGISTRY | {"Muhurta Chintamani (Daivagya Ramacharya)"}
    fails = vrc._matching_problems(_text(), registered=reg)
    assert any("delete the entry" in f for f in fails), fails


def test_a_stale_ledger_entry_is_red_once_matching_stops_naming_the_book():
    text = _text()
    for _, pattern in vrc._MATCHING_MC:
        text = re.sub(pattern, "the source text", text, flags=re.I)
    assert text != _text()
    fails = vrc._matching_problems(text)
    assert any("no longer names it" in f for f in fails), fails


def test_a_registered_book_needs_no_ledger_entry():
    reg = _REAL_REGISTRY | {"Muhurta Chintamani (Daivagya Ramacharya)"}
    assert vrc._matching_problems(_text(), ledger={}, registered=reg) == []


def test_the_banned_list_is_derived_from_the_muhurat_list():
    muhurat = {n for n, _ in vrc._MUHURAT_UNHELD}
    matching = {n for n, _ in vrc._MATCHING_UNHELD}
    assert muhurat - matching == {"Muhurta Chintamani", "Chintamani"}
    assert matching <= muhurat and "BPHS" in matching


# --- the gate as a whole -----------------------------------------------------

def test_the_gate_self_test_is_green_on_the_real_file():
    assert vrc._matching_self_test(_text()) == []


def test_main_fails_when_matching_names_an_unheld_book(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "matching.py"
    bad.write_text(_with("# Per Phaladeepika."), encoding="utf-8")
    monkeypatch.setattr(vrc, "MATCHING", bad)
    assert vrc.main([]) == 1
    assert "FAIL — matching.py:" in capsys.readouterr().out


def test_main_fails_closed_when_matching_cannot_be_read(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(vrc, "MATCHING", tmp_path / "absent.py")
    assert vrc.main([]) == 1
    assert "cannot read" in capsys.readouterr().out


def test_main_passes_on_the_real_file(capsys):
    assert vrc.main([]) == 0
    assert "matching.py:" in capsys.readouterr().out
