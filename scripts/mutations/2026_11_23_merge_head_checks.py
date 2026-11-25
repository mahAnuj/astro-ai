"""agent-merge's HEAD_CHECKS_FN and the sweep that uses it (2026-11-23): a superseded or
self-authored check run never votes, and a red candidate never blocks the green ones above
it. Exercised by tests/test_agent_merge_head_checks.py and tests/test_agent_merge_sweep.py.
One area file, a literal list."""

MUTATIONS = [
    ("merge checks: agent-merge's own earlier runs vote again",
     ".github/workflows/agent-merge.yml",
     '            [ "$path" = "$self" ] && continue\n',
     "            true\n",
     "test_this_workflows_own_runs_never_vote"),
    ("merge checks: a superseded run's cancelled check votes again",
     ".github/workflows/agent-merge.yml",
     '             | select($rid == null or ($ok | index($rid)))]\n',
     "             | select(true)]\n",
     "test_the_1335_shape_is_green"),
    ("merge checks: an unreadable check list reads as no checks, not as unreadable",
     ".github/workflows/agent-merge.yml",
     '          runs=$(gh api "repos/$GH_REPO/commits/$sha/check-runs?per_page=100") || return 2\n',
     '          runs=$(gh api "repos/$GH_REPO/commits/$sha/check-runs?per_page=100") || true\n',
     "test_unreadable_checks_or_runs_are_never_a_pass"),
    ("merge sweep: a red candidate is picked and blocks the queue again",
     ".github/workflows/agent-merge.yml",
     '                if [ -z "$clines" ] || [ -n "$cred" ]; then\n',
     "                if false; then\n",
     "test_a_red_candidate_is_skipped_so_it_cannot_block_the_green_ones_above_it"),
]
