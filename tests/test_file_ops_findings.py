"""scripts/file_ops_findings.py -- the carrier the ops detector never had.

Owner, 2026-11-03: "the agent monitoring the ops dashboard should look at these
data to take action and finetune". The detector existed; nothing ran it. These
tests drive the carrier against an in-memory GitHub so its anti-noise rules --
one issue per kind, comment only on change, one 'cleared' note -- are proven."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("file_ops_findings", ROOT / "scripts" / "file_ops_findings.py")
fo = importlib.util.module_from_spec(_spec)
sys.modules["file_ops_findings"] = fo
_spec.loader.exec_module(fo)

REPO = "o/r"


class FakeGh:
    def __init__(self):
        self.issues: dict[int, dict] = {}
        self.n = 700

    def __call__(self, args):
        if args[:3] == ["api", "-X", "POST"] and args[3].endswith("/issues"):
            self.n += 1
            title = args[5][len("title="):]
            body = args[7][len("body="):]
            labels = [a[len("labels[]="):] for a in args if a.startswith("labels[]=")]
            self.issues[self.n] = {"title": title, "body": body, "by": fo.WRITER, "comments": [],
                                   "labels": labels}
            return "{}"
        if args[:3] == ["api", "-X", "POST"] and args[3].endswith("/labels"):
            n = int(args[3].split("/issues/")[1].split("/")[0])
            for a in args:
                if a.startswith("labels[]=") and a[9:] not in self.issues[n]["labels"]:
                    self.issues[n]["labels"].append(a[9:])
            return "{}"
        if args[:3] == ["api", "-X", "DELETE"] and "/labels/" in args[3]:
            n = int(args[3].split("/issues/")[1].split("/")[0])
            name = args[3].rsplit("/", 1)[1]
            if name not in self.issues[n]["labels"]:
                raise RuntimeError("404")
            self.issues[n]["labels"].remove(name)
            return "{}"
        if args[:3] == ["api", "-X", "POST"] and args[3].endswith("/comments"):
            n = int(args[3].split("/issues/")[1].split("/")[0])
            self.issues[n]["comments"].append(args[5][len("body="):])
            return "{}"
        if args[:2] == ["api", "--paginate"] and "/comments" in args[2]:
            n = int(args[2].split("/issues/")[1].split("/")[0])
            return "\n".join(self.issues[n]["comments"])
        if args[:2] == ["api", "--paginate"] and "/issues?" in args[2]:
            # The API's own `creator=` filter, honoured as GitHub does: drop it
            # from the URL and every author's issue comes back.
            m = re.search(r"[?&]creator=([^&]+)", args[2])
            return "\n".join(json.dumps({"number": k, "body": v["body"]})
                             for k, v in self.issues.items() if m is None or v["by"] == m.group(1))
        raise AssertionError(args)


def F(kind="claude-quota", level="amber", title="Claude weekly quota 90% used", detail="levers"):
    return {"kind": kind, "level": level, "title": title, "detail": detail, "where": "/admin/ops"}


def test_a_new_finding_files_ONE_issue_with_its_marker():
    gh = FakeGh()
    s = fo.carry(gh, REPO, [F(), F()], "t1")
    assert s["filed"] == 1 and len(gh.issues) == 1
    (i,) = gh.issues.values()
    assert i["title"].startswith("[OPS] ") and "<!-- ops-finding: claude-quota -->" in i["body"]


def test_the_same_finding_on_the_next_run_is_SILENCE():
    gh = FakeGh()
    fo.carry(gh, REPO, [F()], "t1")
    s = fo.carry(gh, REPO, [F(detail="numbers moved")], "t2")
    assert s == {"filed": 0, "updated": 0, "unchanged": 1, "cleared": 0}
    assert all(not i["comments"] for i in gh.issues.values())


def test_a_changed_finding_is_ONE_comment_on_the_same_issue():
    gh = FakeGh()
    fo.carry(gh, REPO, [F()], "t1")
    fo.carry(gh, REPO, [F(level="red", title="Claude weekly quota 97% used")], "t2")
    fo.carry(gh, REPO, [F(level="red", title="Claude weekly quota 97% used")], "t3")
    (i,) = gh.issues.values()
    assert len(i["comments"]) == 1 and "97%" in i["comments"][0]


def test_a_finding_that_clears_gets_one_note_and_stays_OPEN():
    gh = FakeGh()
    fo.carry(gh, REPO, [F()], "t1")
    fo.carry(gh, REPO, [], "t2")
    fo.carry(gh, REPO, [], "t3")
    (i,) = gh.issues.values()
    assert len(i["comments"]) == 1 and fo.CLEARED in i["comments"][0]


def test_a_finding_that_RETURNS_after_clearing_is_commented_again():
    gh = FakeGh()
    fo.carry(gh, REPO, [F()], "t1")
    fo.carry(gh, REPO, [], "t2")
    s = fo.carry(gh, REPO, [F()], "t3")
    assert s["updated"] == 1 and len(gh.issues) == 1


def test_an_issue_someone_else_filed_with_the_marker_is_not_adopted():
    gh = FakeGh()
    gh.issues[5] = {"title": "x", "body": "<!-- ops-finding: claude-quota -->", "by": "drive-by",
                    "comments": []}
    fo.carry(gh, REPO, [F()], "t1")
    assert len(gh.issues) == 2, "only the workflow's own issues count"


def test_each_kind_gets_its_own_issue():
    gh = FakeGh()
    fo.carry(gh, REPO, [F(), F(kind="cycle-waste", title="47% of cycle time produced no result")], "t1")
    kinds = {re.search(r"ops-finding: (\S+) -->", i["body"]).group(1) for i in gh.issues.values()}
    assert kinds == {"claude-quota", "cycle-waste"}


def test_bad_input_is_exit_2(tmp_path):
    p = tmp_path / "f.json"
    p.write_text("not json")
    assert fo.main(["x", "--repo", REPO, "--findings", str(p)], gh=FakeGh()) == 2


def test_the_steward_runs_the_carrier_before_its_stall_check_without_new_permissions():
    doc = yaml.safe_load((ROOT / ".github" / "workflows" / "agent-steward.yml").read_text())
    steps = doc["jobs"]["steward"]["steps"]
    names = [s.get("name") for s in steps]
    i = names.index("File the ops dashboard's findings as issues")
    assert steps[i].get("continue-on-error") is True
    assert "detect_ops_regressions.py --json" in steps[i]["run"]
    assert "file_ops_findings.py" in steps[i]["run"]
    assert i < names.index("Is anything actually stuck?")
    assert doc["jobs"]["steward"]["permissions"]["issues"] == "write"


_ev = importlib.util.spec_from_file_location("verify_issue_evidence", ROOT / "scripts" / "verify_issue_evidence.py")
evidence = importlib.util.module_from_spec(_ev)
sys.modules["verify_issue_evidence"] = evidence
_ev.loader.exec_module(evidence)


def test_a_filed_issue_passes_the_loops_own_evidence_gate():
    """QA round 2 on #691: the carrier filed issues with no Evidence Block and no
    label, and verify_issue_evidence.check() refused them (exit 1, 6 problems), so
    agent-cycle labelled each needs-evidence and project-manager never ranked one.
    Filed and never worked. FakeGh hid it because nothing applied the loop's gate
    to what the carrier writes -- this does, on the issue as actually filed."""
    for kind in ("claude-quota", "cycle-waste", "loop-idle"):
        gh = FakeGh()
        fo.carry(gh, REPO, [F(kind=kind)], "2026-11-03T00:00:00Z")
        (i,) = gh.issues.values()
        assert i["labels"][0] == "chore" and "priority:medium" in i["labels"], i["labels"]
        rc, lines = evidence.check(i["body"], i["labels"], "2026-11-03T00:00:00Z")
        assert rc == 0, "\n".join(lines)



def test_a_number_wobble_is_SILENCE_not_a_comment():
    """#697 got four comments for "idle 90% -> 89% -> 88% -> 89%" while the
    finding itself never changed. Numbers are ignored; the level is not."""
    gh = FakeGh()
    fo.carry(gh, REPO, [F(kind="loop-idle", title="Build lane idle 90% of the last 7d")], "t1")
    for pct in (89, 88, 89):
        fo.carry(gh, REPO, [F(kind="loop-idle", title=f"Build lane idle {pct}% of the last 7d")], "t")
    (i,) = gh.issues.values()
    assert i["comments"] == [], i["comments"]


def test_findings_are_prioritised_by_severity_and_follow_a_level_change():
    """Owner, 2026-11-06: ops issues should also be prioritised."""
    gh = FakeGh()
    fo.carry(gh, REPO, [F(level="amber")], "t1")
    (n,) = gh.issues
    assert "priority:medium" in gh.issues[n]["labels"]
    fo.carry(gh, REPO, [F(level="red", title="Claude weekly quota 97% used")], "t2")
    assert "priority:high" in gh.issues[n]["labels"] and "priority:medium" not in gh.issues[n]["labels"]


def test_a_red_finding_is_filed_at_priority_high():
    gh = FakeGh()
    fo.carry(gh, REPO, [F(kind="loop-broken", level="red", title="agent-work failed 3 runs")], "t1")
    (i,) = gh.issues.values()
    assert "priority:high" in i["labels"]
