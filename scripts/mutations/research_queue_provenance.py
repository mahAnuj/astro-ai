"""QA on #1063: an outsider's issue must never reach the research agent, which
may Write knowledge/*.md. tests/test_research_queue.py."""

MUTATIONS = [
    ("research queue: every open issue is queued whoever filed it",
     "scripts/research_queue.py",
     "issues = [i for i in open_issues(gh, repo) if trusted(i, repo)]",
     "issues = open_issues(gh, repo)",
     "test_an_outsiders_issue_never_reaches_the_research_agent"),
]
