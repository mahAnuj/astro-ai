"""#716: `muhurat.py` may not credit a rule to a book this repo does not hold.

`muhurat.py` carried ten attributions in comments and docstrings -- BPHS, Muhurta
Chintamani, Phaladeepika, Ashvalayana -- none of them in `data/`, all of them
withdrawn or never held per `knowledge/SOURCES.md`. `scripts/verify_rule_citations.py`
read `chart.py`'s `source=` labels only, so it printed PASS over all ten. The gate now
scans the whole of `muhurat.py` as text; these tests pin that it does, against the
real file and against the names re-inserted.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "verify_rule_citations", ROOT / "scripts" / "verify_rule_citations.py")
vrc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vrc)

MUHURAT = ROOT / "src" / "astro_ai" / "muhurat.py"
_ANCHOR = "_TARA_BALA_NAMES = {"


def _with(line: str) -> str:
    text = MUHURAT.read_text(encoding="utf-8")
    assert _ANCHOR in text
    return text.replace(_ANCHOR, f"{line}\n{_ANCHOR}", 1)


def test_the_real_muhurat_file_names_no_unheld_book():
    assert vrc._muhurat_problems(MUHURAT.read_text(encoding="utf-8")) == []


def test_bphs_in_a_comment_is_red():
    fails = vrc._muhurat_problems(_with("# BPHS assigns each position a name."))
    assert fails and "BPHS" in fails[0]


def test_muhurta_chintamani_in_a_comment_is_red():
    assert vrc._muhurat_problems(_with("# Per Muhurta Chintamani."))


@pytest.mark.parametrize("line", [
    "# Per Brihat Parashara Hora Shastra.",
    "# Classical rule from Muhurtha Chintamani.",
    "# Per Muhurta\n# Chintamani.",          # wrapped across a comment line
    "# Sources: Phaladeepika.",
    "# Sources: Phaladipika.",
    "# See Jataka Parijata.",
    "# See Jataka Chandrika.",
    "# Sources: Ashvalayana Grihya Sutra.",
    "# Sources: Aswalayana.",
    "# bphs marks certain houses as good.",
    '"""Per BPHS."""',                       # a docstring, not a comment
])
def test_each_unheld_name_and_spelling_is_red(line):
    assert vrc._muhurat_problems(_with(line)), line


def test_the_failure_names_the_line_it_is_on():
    text = _with("# BPHS marks this.")
    expected = text.split("\n").index("# BPHS marks this.") + 1
    fails = vrc._muhurat_problems(text)
    assert any(f.startswith(f"muhurat.py:{expected}:") for f in fails), fails


def test_a_file_without_its_anchors_fails_closed():
    assert vrc._muhurat_problems("# nothing here\n")


def test_the_gate_self_test_is_green_on_the_real_file():
    assert vrc._muhurat_self_test(MUHURAT.read_text(encoding="utf-8")) == []


def test_main_fails_when_muhurat_names_an_unheld_book(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "muhurat.py"
    bad.write_text(_with("# Per Phaladeepika."), encoding="utf-8")
    monkeypatch.setattr(vrc, "MUHURAT", bad)
    assert vrc.main([]) == 1
    # The FAIL line itself, not just any mention of the file: main() also prints
    # "muhurat.py: N lines scanned", and the self-test fails on a bad file too.
    assert "FAIL \u2014 muhurat.py:" in capsys.readouterr().out


def test_main_fails_closed_when_muhurat_cannot_be_read(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(vrc, "MUHURAT", tmp_path / "absent.py")
    assert vrc.main([]) == 1
    assert "cannot read" in capsys.readouterr().out


def test_main_passes_on_the_real_file(capsys):
    assert vrc.main([]) == 0
    assert "muhurat.py:" in capsys.readouterr().out
