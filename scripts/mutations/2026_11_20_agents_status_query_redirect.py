"""#1261: /api/agents/status 301s any query string to the bare path, CORS intact.
tests/test_agent_status.py."""

_R = "src/astro_ai/routes/agents_status.py"

MUTATIONS = [
    ("#1261: the query-string redirect is removed (every ?x=N reaches snapshot())",
     _R, "if request.url.query:", "if False:",
     "test_a_query_string_is_redirected_before_snapshot_runs"),
    ("#1261: the redirect drops its CORS headers",
     _R, 'headers={**_CORS_HEADERS, "Cache-Control": "public, max-age=3600"},',
     'headers={"Cache-Control": "public, max-age=3600"},',
     "test_a_query_string_is_redirected_before_snapshot_runs"),
]
