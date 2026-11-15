"""The research queue comes from open issues, not a hand-typed list (#1030)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("research_queue", ROOT / "scripts" / "research_queue.py")
rq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rq)


def issue(n, labels=(), corpus=None, pr=False):
    body = "## Evidence Block\n" + (f"- **corpus:** {corpus}\n" if corpus else "")
    i = {"number": n, "title": f"t{n}", "labels": [{"name": x} for x in labels], "body": body}
    if pr:
        i["pull_request"] = {}
    return i


def gh_for(issues):
    def gh(args):
        assert "page=1" in args[-1]
        return json.dumps(issues)
    return gh


def nums(picked):
    return [i["number"] for i, _ in picked]


def test_a_labelled_or_unsourced_issue_is_queued_and_nothing_else():
    gh = gh_for([issue(1), issue(2, ["skill:knowledge-integrator"]),
                 issue(3, corpus="[UNSOURCED] — knowledge/ has none"),
                 issue(4, corpus="knowledge/a.md L1-9"),
                 issue(5, ["skill:knowledge-integrator"], pr=True)])
    assert nums(rq.build(gh, "o/r")) == [2, 3]


def test_priority_then_explicit_request_then_oldest():
    gh = gh_for([issue(10, corpus="[UNSOURCED]"),
                 issue(11, ["skill:knowledge-integrator"]),
                 issue(12, ["priority:high"], corpus="[UNSOURCED]"),
                 issue(13, ["priority:low", "skill:knowledge-integrator"]),
                 issue(9, ["skill:knowledge-integrator"])])
    assert nums(rq.build(gh, "o/r")) == [12, 9, 11, 10, 13]


def test_the_list_is_capped():
    gh = gh_for([issue(n, ["skill:knowledge-integrator"]) for n in range(1, 30)])
    assert len(rq.build(gh, "o/r")) == rq.CAP


def test_a_dispatch_can_pin_the_list_and_bad_input_is_refused():
    gh = gh_for([issue(7), issue(8, corpus="[UNSOURCED]")])
    assert nums(rq.build(gh, "o/r", only=[7])) == [7]
    with pytest.raises(ValueError):
        rq.parse_only("1027; rm -rf /")
    assert rq.main(["--repo", "o/r", "--only", "x"], gh=gh) == 2


def test_an_unreadable_issue_list_exits_2():
    def gh(args):
        raise RuntimeError("HTTP 502")
    assert rq.main(["--repo", "o/r"], gh=gh) == 2


def test_an_empty_queue_says_to_fall_back():
    assert "standing queue" in rq.render([])


# --- the wiring --------------------------------------------------------------

def test_the_workflow_builds_the_queue_before_the_agent_and_reads_it():
    wf = ROOT / ".github/workflows/agent-research.yml"
    doc = yaml.safe_load(wf.read_text())
    steps = doc["jobs"]["research"]["steps"]
    q = next(i for i, s in enumerate(steps) if "research_queue.py" in (s.get("run") or ""))
    agent = next(i for i, s in enumerate(steps) if "claude-code-action" in (s.get("uses") or ""))
    assert q < agent
    assert "${{ inputs.issues }}" not in steps[q]["run"], "dispatch input reaches the shell through env"
    assert steps[q]["env"]["ONLY"] == "${{ inputs.issues }}"
    assert "/tmp/research-queue.md" in steps[agent]["with"]["prompt"]
    assert "#1027" not in steps[agent]["with"]["prompt"], "no hand-typed issue numbers for new work"
