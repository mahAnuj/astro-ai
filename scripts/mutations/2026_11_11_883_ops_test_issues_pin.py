"""#883: the Team-header test must not read the committed issues.json (2026-11-11).

`/admin/ops` also renders every open `[OPS] <loop>: last run failed` issue, so
`test_the_team_header_is_unchanged_when_nothing_failed`, which asserts the page
lacks that phrase, went red on main the moment #876 was open and every PR's
pr-gates failed with it. The fix pins `issues.json` inside the test's `_page`.
This row restores the defect deterministically: it seeds the snapshot with the
very row that broke main instead of pinning it away, so it stays red whatever
the committed file holds on the day the harness runs.

DATA ONLY. `MUTATIONS` must stay a literal list (verify_no_relaxation counts it
by parsing).
"""

MUTATIONS = [
    ("ops test: the issues snapshot is no longer pinned, so an open "
     "'[OPS] ...: last run failed' issue turns the Team-header test red",
     "tests/test_ops_last_run_failed.py",
     '    issues = {**(real("issues.json") or {}), "rows": [], "open": 0,\n',
     '    issues = {**(real("issues.json") or {}), "open": 1, "rows": [{"number": 876, '
     '"title": "[OPS] agent-prioritise.yml: last run failed", "ask": "", "area": "OPS", '
     '"type": "chore", "priority": "medium", "labels": ["priority:medium", "chore"], '
     '"created": "2026-11-11T02:08:27Z", "updated": "2026-11-11T02:38:47Z", '
     '"blocked": False, "needs_evidence": False}],\n',
     "test_the_team_header_is_unchanged_when_nothing_failed"),
]
