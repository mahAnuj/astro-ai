"""2026-11-12: the research loop's corpus PR is opened as the publisher (#915)."""

MUTATIONS = [
    ("research: the corpus PR goes back to github.token (checks held, #915)",
     ".github/workflows/agent-research.yml",
     "          GH_TOKEN: ${{ steps.app-token.outputs.token || github.token }}\n          GH_REPO: ${{ github.repository }}\n        run: |\n          if [ ! -d /tmp/corpus-out/knowledge ]; then",
     "          GH_TOKEN: ${{ github.token }}\n          GH_REPO: ${{ github.repository }}\n        run: |\n          if [ ! -d /tmp/corpus-out/knowledge ]; then",
     "test_the_pr_is_pushed_and_opened_with_it"),
]
