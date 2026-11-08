"""#739: the workflow-permission gate must see a rename as a delete plus an add."""

MUTATIONS = [
    ("workflow gate: rename detection is left on, so a renamed agent-merge.yml is invisible to check 2",
     "scripts/verify_workflow_permissions.py",
     'git("diff", "--name-only", "--no-renames",',
     'git("diff", "--name-only",',
     "test_a_RENAMED_agent_merge_with_an_emptied_boundary_goes_red"),
    ("workflow gate: the HEAD~1 fallback is dropped from the base chain",
     "scripts/verify_workflow_permissions.py",
     'for cand in (args.base, "main", "origin/HEAD", "HEAD~1"):',
     'for cand in (args.base, "main", "origin/HEAD"):',
     "test_the_HEAD_minus_1_fallback_is_used_when_no_named_base_resolves"),
]
