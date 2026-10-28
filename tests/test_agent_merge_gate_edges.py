"""`agent-merge` must be triggered by EVERY workflow that publishes a required
gate, not just the one that is usually slowest (#356, recurred 2026-10-27).

WHY THIS IS HERE, given the charter in conftest.py.

The trigger list is a YAML string that nothing type-checks, and getting it
wrong is silent in the worst way: the workflow still runs, still passes, and
still says "not all checks are green yet -- leaving the PR open". There is no
error anywhere. The only symptom is a PR that is green, `qa-pass` and never
merged, which is indistinguishable from "nothing was ready to merge".

Measured on PR #562, a code PR:

    gates        7m43s   -> workflow_run fired here; build-gates still queued
    build-gates 10m25s   -> finished last, and NOTHING was listening

`build-gates` is published by verify-build.yml, a different workflow. The
original list named only "PR gates" on the reasoning that it is the slow one
and inverts only for docs-only changes. #562 shows the ordering is a race, not
a property of the change, so both gate publishers have to be edges.

The sweep is not a substitute. Measured over the 71 scheduled runs to
2026-10-27 the `*/30` cron delivered min 126m / mean 244m / max 444m gaps, so
relying on it means a stranded PR waits hours.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
MERGE = WORKFLOWS / "agent-merge.yml"


def _on(path: Path) -> dict:
    """`on:` is parsed by YAML 1.1 as the boolean True, so look it up by name."""
    doc = yaml.safe_load(path.read_text())
    key = next(k for k in doc if str(k) in ("on", "True"))
    return doc[key]


def _declared_name(path: Path) -> str:
    return yaml.safe_load(path.read_text())["name"]


def _workflow_publishing(check: str) -> Path:
    """The workflow file whose job id is `check` -- that job id IS the check name."""
    hits = [
        p
        for p in sorted(WORKFLOWS.glob("*.yml"))
        if check in (yaml.safe_load(p.read_text()).get("jobs") or {})
    ]
    assert len(hits) == 1, f"expected exactly one workflow with job `{check}`, got {hits}"
    return hits[0]


def test_both_required_gates_trigger_the_merge_workflow() -> None:
    """Every workflow publishing a required check must be a workflow_run edge.

    `gates` and `build-gates` are the two contexts branch protection requires,
    and they live in different workflows. Whichever finishes LAST is the one
    that has to fire this job, and which that is cannot be predicted.
    """
    listens_to = set(_on(MERGE)["workflow_run"]["workflows"])

    for check in ("gates", "build-gates"):
        publisher = _workflow_publishing(check)
        name = _declared_name(publisher)
        assert name in listens_to, (
            f"required check `{check}` is published by {publisher.name} "
            f"(name: {name!r}), which agent-merge does not listen to. "
            f"When {check} finishes last, no edge fires and the PR strands. "
            f"Currently listening to: {sorted(listens_to)}"
        )


def test_every_trigger_names_a_real_workflow() -> None:
    """A `workflows:` entry matches a `name:` field, not a filename.

    A typo here does not fail anything -- the trigger simply never fires. The
    repo gate `verify_workflows.py` also checks this; it is pinned here too
    because this file is what documents why the list has two entries.
    """
    declared = {_declared_name(p) for p in WORKFLOWS.glob("*.yml")}
    for named in _on(MERGE)["workflow_run"]["workflows"]:
        assert named in declared, (
            f"{named!r} names no workflow in this repo, so that trigger never "
            f"fires. Declared names: {sorted(declared)}"
        )


def test_the_sweep_is_still_only_a_backstop() -> None:
    """The cron must stay, and must not be the thing the design leans on.

    Pinned because the fix for a stranded PR is always tempting to write as
    "lower the cron interval". GitHub throttles short-interval cron on public
    repos -- `*/30` was measured delivering a 126m best case over 71 runs -- so
    a shorter interval buys nothing and the edges above are what must be right.
    """
    schedule = _on(MERGE)["schedule"]
    assert any("cron" in entry for entry in schedule), "the sweep backstop was removed"
