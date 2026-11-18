"""2026-11-18: close-on-evidence closes every PR the live, verified commit
contains. tests/test_close_on_evidence_ancestors.py."""

_W = ".github/workflows/close-on-evidence.yml"

MUTATIONS = [
    ("close-on-evidence: a newer live deploy containing the commit no longer counts",
     _W, '            if [ "$rel" != "ahead" ]; then\n              echo "::notice::live commit $live does not contain',
     '            if true; then\n              echo "::notice::live commit $live does not contain',
     "test_a_newer_live_deploy_that_contains_the_commit_still_counts"),
    ("close-on-evidence: only the verified commit's own PR is considered again",
     _W, '            [ "$rel" = "ahead" ] && prs="$prs $pr"',
     '            [ "$rel" = "never" ] && prs="$prs $pr"',
     "test_every_pr_contained_in_the_verified_commit_closes_its_issue"),
    ("close-on-evidence: a 'Closes #a, #b and #c' list closes only the first again",
     _W, "#[0-9]+([[:space:]]*(,|and|&)[[:space:]]*#[0-9]+)*' \\",
     "#[0-9]+' \\",
     "test_a_list_of_issues_after_closes_closes_all_of_them"),
    ("close-on-evidence: every merged PR gets a compare call, not only those claiming an open issue",
     _W, "select(any($c[]; . as $x | $open | index($x)) or .m == env.SHA)",
     "select(true)",
     "test_only_prs_claiming_an_open_issue_cost_a_compare_call"),
]
