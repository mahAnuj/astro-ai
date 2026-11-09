"""The rescue push uses the publisher App token (2026-11-09, #804)."""

MUTATIONS = [
    ("token refresh: the rescue push goes back to github.token",
     ".github/workflows/agent-work.yml",
     '            "https://x-access-token:${PR_TOKEN}@github.com/${GH_REPO}.git"\n',
     '            "https://x-access-token:${GH_TOKEN}@github.com/${GH_REPO}.git"\n',
     "test_the_rescue_push_uses_the_publisher_token_not_github_token"),
]
