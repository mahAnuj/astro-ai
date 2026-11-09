"""#813: the two audit agents file findings the loop can actually work.

`/agent-cycle` Step 1 refuses an issue that fails `verify_issue_evidence.py`.
astro-auditor and numerologist filed with no Evidence Block, so #713, #581 and
#777 (rule defects confirmed wrong in front of users) failed it and could never
be dispatched. Each definition now carries a template.

This runs the template THROUGH the gate rather than checking that some words
are present, so a template the gate would reject fails here. Deleting the
template or the `bug` label instruction fails too.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS = [".claude/agents/astro-auditor.md", ".claude/agents/numerologist.md"]
MARKER = "<!-- evidence-block-template -->"

_spec = importlib.util.spec_from_file_location("vie", ROOT / "scripts/verify_issue_evidence.py")
vie = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vie)


def _template(path: str) -> str:
    s = (ROOT / path).read_text()
    assert MARKER in s, f"{path} carries no Evidence Block template"
    m = re.search(r"```\n(.*?)```", s[s.index(MARKER):], re.S)
    assert m, f"{path}: no fenced template after the marker"
    return m.group(1)


def _filled(path: str) -> str:
    # `<N>` is documented as "a number you measured"; a tester measures 3.
    return _template(path).replace("<N>", "3")


@pytest.mark.parametrize("path", AGENTS)
def test_template_passes_the_gate_for_a_bug_labelled_finding(path):
    code, lines = vie.check(_filled(path), ["astrology-correctness", "bug"], "2026-11-09")
    assert code == 0, "\n".join(lines)


@pytest.mark.parametrize("path", AGENTS)
def test_gate_goes_red_without_the_bug_label(path):
    # Without `bug` the gate wants gsc:/ga4:, which a rule defect cannot have.
    code, _ = vie.check(_filled(path), ["astrology-correctness"], "2026-11-09")
    assert code == 1


@pytest.mark.parametrize("path", AGENTS)
@pytest.mark.parametrize("field", ["corpus", "tokens", "repro", "thesis", "metric"])
def test_dropping_any_field_turns_the_gate_red(path, field):
    body = "\n".join(
        ln for ln in _filled(path).splitlines() if not ln.startswith(f"- **{field}:**")
    )
    code, _ = vie.check(body, ["astrology-correctness", "bug"], "2026-11-09")
    assert code == 1


@pytest.mark.parametrize("path", AGENTS)
def test_definition_tells_the_agent_to_label_bug(path):
    s = (ROOT / path).read_text()
    assert re.search(r"Label `bug`", s), f"{path} does not instruct the `bug` label"
