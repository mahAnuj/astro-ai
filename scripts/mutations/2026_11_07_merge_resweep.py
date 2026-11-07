"""agent-merge re-dispatches its sweep after a merge (2026-11-07)."""

MUTATIONS = [
    ("resweep: the dispatch targets another workflow",
     ".github/workflows/agent-merge.yml",
     '          if gh workflow run agent-merge.yml --repo "$GH_REPO" --ref main; then\n',
     '          if gh workflow run agent-queue.yml --repo "$GH_REPO" --ref main; then\n',
     "test_a_successful_merge_dispatches_another_sweep"),
    ("resweep: every run dispatches, merged or not, so the chain never ends",
     ".github/workflows/agent-merge.yml",
     "        if: steps.boundary.outputs.ok == 'true' && success()\n        continue-on-error: true\n        env:\n          PR_NUMBER: ${{ steps.pr.outputs.number }}\n        run: |\n          if gh workflow run agent-merge.yml",
     "        if: always()\n        continue-on-error: true\n        env:\n          PR_NUMBER: ${{ steps.pr.outputs.number }}\n        run: |\n          if gh workflow run agent-merge.yml",
     "test_only_a_run_that_merged_dispatches_so_the_chain_ends"),
]
