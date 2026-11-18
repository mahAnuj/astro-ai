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
]
