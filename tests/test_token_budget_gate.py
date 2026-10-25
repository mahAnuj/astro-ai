"""scripts/verify_token_budget.py must be able to go red (#400).

A gate that has never failed is not evidence. This one exists because two
request-size regressions (#212, 18.5% growth per call; #266, a natal request
bigger than the whole TPM bucket) shipped with nothing to stop them, so the
property worth testing is not "the shipped prompts pass" — pr-gates runs the
script for that — but "an oversized, fast-growing or unbudgeted prompt FAILS".

The tokenizer is faked. The real one downloads a 3.6 MB vocabulary on first use,
and a hermetic suite must not depend on that (nor skip when it is absent: a
skip reads as green). Nothing here asserts a real token count; every assertion
is about which comparison fired and what the message names. The pure comparison
(`evaluate`) is driven with invented numbers, and `main()` is driven end to end
over a temp copy of the prompts, so that a mutation which neuters either
comparison, the coverage check or the exit-2 branch turns this file red
(scripts/mutate_behaviour_suite.py has a row for each).
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "verify_token_budget", ROOT / "scripts" / "verify_token_budget.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_token_budget"] = gate
_spec.loader.exec_module(gate)

PROMPTS = ROOT / "src" / "astro_ai" / "prompts"


class _FakeEncoding:
    """~4 bytes per token. Only the SHAPE of the numbers matters here."""

    def encode(self, text: str) -> list[int]:
        return list(range(len(text.encode("utf-8")) // 4))


@pytest.fixture
def fake_tokenizer(monkeypatch):
    monkeypatch.setattr(gate, "load_encoding", lambda: _FakeEncoding())


@pytest.fixture
def prompts_copy(tmp_path):
    for f in PROMPTS.glob("*.txt"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


TABLE = {"route": (1000, 1500, "2026-10-17", "test")}


# --------------------------------------------------------------------------
# the comparison itself
# --------------------------------------------------------------------------


def test_a_route_at_its_baseline_passes():
    assert gate.evaluate({"route": (1000, 1100)}, TABLE, 5.0) == []


def test_a_route_over_its_ceiling_fails_naming_the_route_the_ceiling_and_the_value():
    (msg,) = [m for m in gate.evaluate({"route": (1600, 1700)}, TABLE, 500.0)]
    # growth is switched off (500%) so this isolates the ceiling comparison
    assert "route" in msg and "1,700" in msg and "1,500" in msg and "ceiling" in msg


def test_growth_under_the_ceiling_still_fails():
    """#212: each step was under any ceiling and the trend was the defect."""
    failures = gate.evaluate({"route": (1100, 1100)}, TABLE, 5.0)
    assert len(failures) == 1
    assert "growth allowance" in failures[0] and "+10.0%" in failures[0]
    assert "route" in failures[0] and "1,000" in failures[0]


def test_growth_inside_the_allowance_passes_and_the_allowance_is_configurable():
    assert gate.evaluate({"route": (1049, 1049)}, TABLE, 5.0) == []
    assert gate.evaluate({"route": (1051, 1051)}, TABLE, 5.0) != []
    assert gate.evaluate({"route": (1051, 1051)}, TABLE, 10.0) == []


def test_the_hindi_variant_is_judged_against_the_ceiling():
    """_LANG_SUFFIX['hi'] adds ~132 tok to every route, which is 18% of daily."""
    failures = gate.evaluate({"route": (1000, 1501)}, TABLE, 5.0)
    assert any("ceiling" in f and "1,501" in f for f in failures)


def test_a_measured_route_with_no_row_fails():
    failures = gate.evaluate({"route": (1000, 1000), "new": (10, 10)}, TABLE, 5.0)
    assert any(f.startswith("new:") and "no recorded ceiling" in f for f in failures)


def test_a_row_for_a_route_that_was_not_measured_fails():
    failures = gate.evaluate({}, TABLE, 5.0)
    assert any(f.startswith("route:") and "not measured" in f for f in failures)


# --------------------------------------------------------------------------
# the table
# --------------------------------------------------------------------------


def test_every_shipped_prompt_file_is_covered_and_every_route_has_a_row():
    from astro_ai.routes import deps

    routes = gate.route_files(deps)
    assert gate.uncovered_prompts(routes, deps.PROMPTS_DIR) == []
    # The two SYNTHETIC rows: a route's system prompt plus its user message.
    # `natal+payload` because #266 was the SUM crossing the TPM line, not the
    # prompt alone; `rashifal_single+payload` added 2026-10-24 (#523) for the
    # same reason in reverse -- that route was measured on its system prompt
    # only, so the row read "+0.0%" while ~120 tok per rashi went into the USER
    # message and the gate passed BECAUSE it could not see the change.
    assert set(gate.BUDGET) == set(routes) | {"natal+payload",
                                              "rashifal_single+payload"}
    assert len(routes) == 11  # one per prompts/*.txt, overlays as ask.txt + overlay


def test_the_table_is_internally_sane():
    from astro_ai import providers

    for route, (baseline, ceiling, on, why) in gate.BUDGET.items():
        assert 0 < baseline <= ceiling, route
        assert len(on) == 10 and on[4] == "-" and on[7] == "-", f"{route}: date {on!r}"
        assert why.strip(), f"{route}: a number with no reason is not reviewable"
    # The payload row's ceiling is the runtime guard's own budget, not a
    # figure that can drift above the TPM bucket without this noticing.
    assert (gate.BUDGET["natal+payload"][1]
            <= providers.REQUEST_TOKEN_CEILING - providers.REQUEST_TOKEN_MARGIN)


def test_the_gate_has_no_flag_that_rewrites_its_own_table():
    for flag in ("--update", "--write", "--rebaseline"):
        with pytest.raises(SystemExit) as exc:
            gate.main([flag])
        assert exc.value.code == 2
    src = (ROOT / "scripts" / "verify_token_budget.py").read_text()
    assert "write_text" not in src and "open(" not in src


# --------------------------------------------------------------------------
# end to end, over a temp copy of the prompts
# --------------------------------------------------------------------------


def test_a_twelfth_prompt_file_with_no_budget_fails(fake_tokenizer, prompts_copy, capsys):
    (prompts_copy / "brand_new.txt").write_text("a prompt nobody budgeted")
    assert gate.main(["--prompts-dir", str(prompts_copy)]) == 1
    out = capsys.readouterr().out
    assert "brand_new.txt" in out and "no route in this gate" in out


def test_an_inflated_prompt_fails_naming_the_route_and_the_ceiling(
    fake_tokenizer, prompts_copy, capsys
):
    natal = prompts_copy / "natal.txt"
    natal.write_text(natal.read_text() + "\nPADDING " * 20_000)
    assert gate.main(["--prompts-dir", str(prompts_copy)]) == 1
    out = capsys.readouterr().out
    assert "natal: " in out and "exceeds the ceiling 3,600" in out
    assert "natal+payload: " in out and "exceeds the ceiling 7,000" in out
    assert "OVERRIDE ACTIVE" in out


def test_an_override_that_is_empty_is_refused_not_skipped_past(
    fake_tokenizer, tmp_path, capsys
):
    empty = tmp_path / "natal.txt"
    empty.write_text("")
    assert gate.main(["--prompt", f"natal={empty}"]) == 1
    assert "refusing to fall back" in capsys.readouterr().out


def test_an_unavailable_tokenizer_is_exit_two_and_says_it_is_not_a_pass(monkeypatch, capsys):
    def boom():
        raise gate.CouldNotRun("no vocabulary")

    monkeypatch.setattr(gate, "load_encoding", boom)
    assert gate.main([]) == 2
    assert "NOT a pass" in capsys.readouterr().out


def test_the_natal_row_includes_the_chart_payload_not_only_the_system_prompt(
    fake_tokenizer, monkeypatch
):
    """#266 was the SUM crossing the bucket. A row that is the prompt alone
    cannot see the payload grow."""
    seen: dict = {}

    def capture(measured, budget, pct):
        seen.update(measured)
        return []

    monkeypatch.setattr(gate, "evaluate", capture)
    assert gate.main([]) == 0
    assert seen["natal+payload"][0] > seen["natal"][0] + 500
