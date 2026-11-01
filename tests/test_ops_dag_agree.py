"""`/admin/ops` and the agent-cycle DAG must agree on what a failure is (#628).

THE DEFECT. `loop-outcomes.yml:22` documents its own exit codes -- "0 all
OK/IDLE; 1 something BROKEN" -- so exit 1 means it found something to report,
which is the job. GitHub records that as `conclusion: failure`, because GitHub
cannot know the difference.

`scripts/build_agent_cycle_dag.py` knew this and carried
`CONTRACT_NONZERO = {"loop-outcomes.yml"}`. `src/astro_ai/ops_today.py` had no
equivalent at all. So on 2026-10-31 the DAG page showed `loop-outcomes` as
`reporting` while `/admin/ops` counted all 4 of its runs that week as loop
failures: one fact, two surfaces, two answers, for weeks. A tile that is red
when nothing is wrong is a tile nobody reads, which is the failure mode
`ops_today`'s own `SUCCEEDED_CONCLUSIONS` comment was written to prevent one
layer up.

WHY THE FIX IS AN IMPORT AND NOT A SECOND LITERAL. Adding the same set to
`ops_today` would have fixed the count and left the next divergence free to
happen -- the two would drift again the first time one workflow was added to
either. `ops_today` declares it (that module ships in the app image; `scripts/`
does not) and the DAG builder imports it, so there is one object.
`test_both_surfaces_read_the_SAME_object` is what makes that structural rather
than a convention: it fails if either side goes back to a literal.

NARROW ON PURPOSE. Only `failure` is excused. A `startup_failure`,
`timed_out`, `cancelled` or `action_required` on one of these workflows is a
real failure -- the job did not run, or did not finish, and found nothing
either way. A set-membership test alone would have swallowed all four, which
would turn this fix into a blind spot in the one tile that is supposed to
notice an outage.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from astro_ai import ops_today

ROOT = Path(__file__).resolve().parent.parent
DAG_PATH = ROOT / "scripts" / "build_agent_cycle_dag.py"

_spec = importlib.util.spec_from_file_location("build_agent_cycle_dag", DAG_PATH)
dag = importlib.util.module_from_spec(_spec)
sys.modules["build_agent_cycle_dag"] = dag
_spec.loader.exec_module(dag)


def test_both_surfaces_read_the_SAME_object():
    """Not "are equal" -- the same object.

    Equality would pass on two literals that happen to match today, which is
    exactly the state this issue describes. Identity cannot.
    """
    assert dag.CONTRACT_NONZERO is ops_today.CONTRACT_NONZERO


def test_loop_outcomes_is_in_it_and_is_a_loop_leg():
    """Both halves matter.

    `rashifal-generate.yml` has the same non-zero-is-fine property and is
    handled the other way -- it is not a loop leg at all, so it sits in
    `NOT_LOOP_WORKFLOWS`. `loop-outcomes` IS a leg: whether it RAN is real
    health, so it has to stay counted while its exit code is excused.
    """
    assert "loop-outcomes.yml" in ops_today.CONTRACT_NONZERO
    assert "loop-outcomes.yml" in ops_today.LOOP_WORKFLOWS
    assert "loop-outcomes.yml" not in ops_today.NOT_LOOP_WORKFLOWS


def test_the_excused_conclusion_is_one_value_not_a_range():
    """A set-membership test alone would swallow `startup_failure`.

    That is a leg that never started, and excusing it would put a hole in the
    one tile meant to notice an outage.
    """
    assert ops_today.CONTRACT_NONZERO_CONCLUSION == "failure"
    assert ops_today.CONTRACT_NONZERO_CONCLUSION not in ops_today.SUCCEEDED_CONCLUSIONS


@pytest.mark.parametrize("wf", sorted(ops_today.CONTRACT_NONZERO))
def test_every_excused_workflow_documents_its_own_exit_codes(wf):
    """The excuse is only legitimate if the workflow SAYS non-zero is its contract.

    Otherwise this set becomes a place to silence a loop that is genuinely
    broken -- a one-line edit with no evidence required. `loop-outcomes.yml`
    earns its entry by documenting "0 all OK/IDLE; 1 something BROKEN" in its
    own header.
    """
    text = (ROOT / ".github" / "workflows" / wf).read_text(encoding="utf-8")
    assert "BROKEN" in text and "OK/IDLE" in text, (
        f"{wf} is excused from the failure count but its own file does not "
        f"document a non-zero exit as its contract")
