"""#607: every agent definition says where its output goes.

The rule this pins was stated once in `CLAUDE.md`, pointed at a gitignored
file, and 12 of 15 agent definitions ended up with no instruction to write
anywhere durable. These tests exist because a rule with no gate is exactly how
that happened — stating it again without pinning it would repeat the mistake.

They are written about the PROPERTY, not the wording: each asserts that a
definition names both surfaces and says the heartbeat file is local, so a
rewrite that keeps the substance passes.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS = sorted((ROOT / ".claude/agents").glob("*.md"))
GATE = ROOT / "scripts/verify_agent_trail.py"


def _run_gate(root: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the gate that lives under `root`.

    It locates the repo from its OWN path (`__file__`), so a copy must be
    invoked at its copied path — invoking the original with a different cwd
    checks the real tree, which is how the first draft of these two tests
    passed a mutated copy.
    """
    base = root or ROOT
    return subprocess.run((sys.executable, str(base / "scripts" / GATE.name)),
                          cwd=base, capture_output=True, text=True)


def test_there_are_agents_to_check():
    # a gate that finds nothing must not report success
    assert len(AGENTS) >= 10, f"only {len(AGENTS)} agent definitions found"


def test_every_agent_names_where_its_output_goes():
    missing = [p.stem for p in AGENTS if "## Where your output goes" not in p.read_text()]
    assert missing == [], (
        f"{len(missing)} agent definition(s) do not say where their output goes: {missing}. "
        "A subagent reads only its own file, so a rule stated once centrally is one most "
        "of them never see."
    )


def test_every_agent_names_both_the_issue_and_the_pr():
    bad = []
    for p in AGENTS:
        s = p.read_text()
        block = s[s.index("## Where your output goes"):]
        if "**On the issue:**" not in block or "**On the PR:**" not in block:
            bad.append(p.stem)
    assert bad == [], (
        f"these name only one surface: {bad}. Both markers are LITERAL: `**On the issue:**` "
        "and `**On the PR:**`. The word 'issue' alone is not enough — the section heading "
        "contains it, which made this check near-vacuous until QA on #609 found it. "
        "The issue is the durable decision record and "
        "the PR is the review; 'nothing routinely' is an acceptable answer for the PR, "
        "silence is not."
    )


def test_no_agent_is_told_the_heartbeat_file_is_the_record():
    bad = [p.stem for p in AGENTS
           if "local heartbeat" not in p.read_text()[p.read_text().index("## Where your output goes"):]]
    assert bad == [], (
        f"these do not say AGENT_STATUS.md is local only: {bad}. It is gitignored, so a line "
        "written there is not evidence and never leaves this machine."
    )


def test_claude_md_no_longer_presents_the_gitignored_file_as_the_record():
    c = (ROOT / "CLAUDE.md").read_text()
    assert "### The three surfaces" in c, "CLAUDE.md must name the three surfaces"
    assert "Nothing written there leaves this" in c, (
        "CLAUDE.md must say outright that AGENT_STATUS.md does not leave the machine"
    )


def test_the_gate_passes_on_the_real_tree():
    r = _run_gate()
    assert r.returncode == 0, f"the gate fails on the repo it ships in:\n{r.stdout}\n{r.stderr}"


def test_the_gate_fails_when_a_definition_drops_the_rule(tmp_path):
    """The gate must bite. Proven by removing the section from a copy."""
    import shutil
    work = tmp_path / "repo"
    (work / ".claude/agents").mkdir(parents=True)
    (work / "scripts").mkdir()
    shutil.copy(GATE, work / "scripts" / GATE.name)
    for p in AGENTS:
        shutil.copy(p, work / ".claude/agents" / p.name)
    shutil.copy(ROOT / "CLAUDE.md", work / "CLAUDE.md")

    assert _run_gate(work).returncode == 0, "the copy should start green"

    victim = work / ".claude/agents" / AGENTS[0].name
    s = victim.read_text()
    victim.write_text(s[:s.index("## Where your output goes")])
    r = _run_gate(work)
    assert r.returncode == 1, (
        f"the gate did not notice a definition losing the rule:\n{r.stdout}"
    )
    assert AGENTS[0].stem in r.stdout, "the failure must name the file"


def test_the_gate_fails_when_a_sixteenth_agent_arrives_without_the_rule(tmp_path):
    """The list is derived, not hardcoded — a new agent is checked too."""
    import shutil
    work = tmp_path / "repo"
    (work / ".claude/agents").mkdir(parents=True)
    (work / "scripts").mkdir()
    shutil.copy(GATE, work / "scripts" / GATE.name)
    for p in AGENTS:
        shutil.copy(p, work / ".claude/agents" / p.name)
    shutil.copy(ROOT / "CLAUDE.md", work / "CLAUDE.md")

    (work / ".claude/agents" / "newcomer.md").write_text(
        "---\nname: newcomer\ndescription: a new role that forgot the rule\n---\n\n# newcomer\n")
    r = _run_gate(work)
    assert r.returncode == 1, (
        f"a new agent with no rule passed, so the count is hardcoded somewhere:\n{r.stdout}"
    )
    assert "newcomer" in r.stdout
