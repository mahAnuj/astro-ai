"""There is exactly ONE pacing mechanism on the rashifal path (#475 Phase 3).

WHY THIS IS HERE, given the charter in conftest.py.

Phase 3 of #475 is worded as an instruction rather than a feature: *"re-derive
`_RASHIFAL_MIN_INTERVAL_S` and `_RASHIFAL_CONCURRENCY` from measurement, or
delete them if the bucket subsumes them. **Do not leave two pacing mechanisms
disagreeing.**"* An instruction is not enforceable, so this file is what makes
the outcome stick.

The deleted mechanism was `_StartPacer`, which spaced call STARTS. It was the
weaker instrument by construction -- it could not tell a 3,210-token call from
a 900-token one -- and it had been disabled (0.0) for long enough that its
docstring carried a standing instruction to switch it back on if token
pressure returned. Token pressure did return, and the answer that shipped was
the per-model token bucket, not the pacer. Re-enabling the pacer now would add
wall-clock against the same 300s Cloud Run timeout while buying no TPM
protection the bucket does not already give.

The failure this guards against is therefore not a crash. It is someone
reintroducing a second pacer in good faith, and the two then disagreeing
quietly: one spacing starts, one metering tokens, each unaware of the other's
waits, against a timeout neither of them owns.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from astro_ai import llm

LLM = Path(inspect.getfile(llm))


def _tree() -> ast.Module:
    return ast.parse(LLM.read_text())


def test_the_start_pacer_is_gone_from_the_code() -> None:
    """Checked at the AST level, so the prose that explains the removal is free
    to name it. A grep would fail on the docstring that documents the history,
    which would make recording the reasoning impossible."""
    tree = _tree()
    classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    assert "_StartPacer" not in classes

    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "_RASHIFAL_MIN_INTERVAL_S" not in names
    assert not hasattr(llm, "_RASHIFAL_MIN_INTERVAL_S")
    assert not hasattr(llm, "_StartPacer")


def test_no_function_on_this_path_still_takes_a_pacer() -> None:
    """A leftover parameter is the quiet half of the failure: the argument
    stops being passed, the parameter keeps its default, and nothing errors."""
    tree = _tree()
    offenders = [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        for a in n.args.args + n.args.kwonlyargs
        if a.arg == "pacer"
    ]
    assert not offenders, f"these still take a `pacer`: {offenders}"


def test_the_rashifal_fanout_sleeps_for_nobody_but_the_bucket() -> None:
    """`generate_rashifal` must not block on its own schedule.

    `providers` owns every wait on this path, so a `time.sleep` (or a
    `threading.Event().wait`) appearing in the fan-out is a second pacer by
    another name, whatever it is called.
    """
    tree = _tree()
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "generate_rashifal")
    sleeps = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr in ("sleep", "wait"))
            or (isinstance(node.func, ast.Name) and node.func.id == "sleep")
        )
    ]
    assert not sleeps, (
        "generate_rashifal blocks on its own schedule; the token bucket in "
        "providers.py is the only thing that may pace this path"
    )


def test_concurrency_survives_and_is_still_a_concurrency_cap() -> None:
    """Deleting the pacer must not take the in-flight cap with it.

    They are different controls, and the bucket subsumes only the first.
    Pinned as a bound rather than an exact number so re-deriving it stays
    allowed -- what is not allowed is removing it or letting it grow into a
    fan-out wide enough to hold twelve responses in memory at once.
    """
    assert isinstance(llm._RASHIFAL_CONCURRENCY, int)
    assert 1 <= llm._RASHIFAL_CONCURRENCY <= 4


def test_the_single_call_still_hands_its_wait_to_the_bucket() -> None:
    """The positional-argument shift is the real hazard in this change.

    `pacer` sat immediately before `pace_deadline`, and both were passed
    positionally from the fan-out. Dropping one and leaving the call site alone
    would have slid the deadline into the removed slot -- silently, since both
    were optional. This pins that `pace_deadline` still arrives.
    """
    sig = inspect.signature(llm._generate_rashifal_single)
    assert "pacer" not in sig.parameters
    assert "pace_deadline" in sig.parameters

    tree = _tree()
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "generate_rashifal")
    submits = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "submit"
    ]
    assert submits, "the fan-out no longer submits anything"
    passed = {a.id for s in submits for a in s.args if isinstance(a, ast.Name)}
    assert "pace_deadline" in passed, (
        "generate_rashifal stopped passing pace_deadline to the per-rashi call; "
        "the job would silently fall back to the interactive wait budget"
    )
