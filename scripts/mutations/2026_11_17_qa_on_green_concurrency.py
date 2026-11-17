"""2026-11-17: qa-on-green must not share one concurrency group across PRs --
GitHub cancels the older pending run, dropping a PR's QA decision (#1165).
tests/test_qa_on_green.py."""

MUTATIONS = [
    ("qa-on-green: back to one global concurrency group",
     ".github/workflows/qa-on-green.yml",
     "  group: qa-on-green-${{ github.event.workflow_run.head_branch }}-${{ github.event.workflow_run.name }}",
     "  group: qa-on-green",
     "test_it_is_serialised_so_two_pushes_do_not_race"),
]
