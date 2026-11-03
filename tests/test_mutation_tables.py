"""Mutation rows live in per-area tables now, and the central one is frozen
(owner, 2026-11-03: fix the merge churn in this PR).

Every PR used to append to the ONE `MUTATIONS` table in
scripts/mutate_behaviour_suite.py, so two open PRs conflicted there by
construction -- #636, #649, #671 and #675 each needed `main` merged in and a
fresh QA round in two days -- and because that file is in `_ALWAYS_FULL`, every
PR that added a row paid the full ~55-minute sweep."""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "mutate_behaviour_suite.py"
AREA_DIR = ROOT / "scripts" / "mutations"

#: The central table's size when it was frozen. Re-anchoring or editing a row
#: keeps the count; ADDING one here is what this test refuses.
CENTRAL_FROZEN_AT = 734

_spec = importlib.util.spec_from_file_location("verify_no_relaxation", ROOT / "scripts" / "verify_no_relaxation.py")
vnr = importlib.util.module_from_spec(_spec)
sys.modules["verify_no_relaxation"] = vnr
_spec.loader.exec_module(vnr)


def _labels(text: str) -> list[str]:
    for n in ast.walk(ast.parse(text)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "MUTATIONS" for t in n.targets):
            return [ast.literal_eval(e.elts[0]) for e in n.value.elts]
    raise AssertionError("no MUTATIONS literal")


def _area_files():
    return sorted(p for p in AREA_DIR.glob("*.py") if not p.name.startswith("_"))


def test_the_central_table_does_not_grow():
    n = vnr.mutation_rows(HARNESS.read_text())
    assert n is not None, "the central MUTATIONS must stay a countable literal"
    assert n <= CENTRAL_FROZEN_AT, (
        f"scripts/mutate_behaviour_suite.py's MUTATIONS grew to {n} (frozen at "
        f"{CENTRAL_FROZEN_AT}). Put new rows in scripts/mutations/<area>.py instead -- one "
        f"literal `MUTATIONS = [...]` per file -- so PRs stop conflicting in one table and "
        f"stop paying the full sweep.")


def test_every_area_table_is_a_literal_the_relaxation_gate_can_count():
    """A table built by a call or concatenation reads as ZERO rows to
    verify_no_relaxation's floor -- i.e. as rows deleted."""
    assert _area_files(), "no area tables at all"
    for f in _area_files():
        assert vnr.mutation_rows(f.read_text()), f"{f.name}: MUTATIONS is not a countable literal"
        assert vnr._in_harness(f.relative_to(ROOT).as_posix()), f"{f.name} is outside the counted harness"


def test_labels_are_unique_across_the_central_and_area_tables():
    labels = _labels(HARNESS.read_text())
    for f in _area_files():
        labels += _labels(f.read_text())
    dup = sorted({l for l in labels if labels.count(l) > 1})
    assert not dup, f"duplicate mutation labels: {dup}"


def test_the_harness_actually_runs_the_area_rows():
    """The preflight resolves every row it will run; its count must include
    the area tables, or the split silently dropped them from every sweep."""
    central = vnr.mutation_rows(HARNESS.read_text())
    area = sum(vnr.mutation_rows(f.read_text()) for f in _area_files())
    r = subprocess.run([sys.executable, str(HARNESS), "--preflight-only"], capture_output=True,
                       text=True, cwd=ROOT, timeout=600)
    assert f"anchor pre-flight: {central + area} rows" in r.stdout, r.stdout[-800:] + r.stderr[-800:]


def test_a_changed_area_table_selects_its_own_rows_in_a_scoped_run():
    src = HARNESS.read_text()
    body = src[src.index("def _scope_rows("):src.index("_scope_base = \"\"")]
    assert "AREA_ROWS" in body and "id(row) in from_area" in body
