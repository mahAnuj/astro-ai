"""#1176: the trailing-slash redirect is 308 for a GET/HEAD slash toggle, and nothing else.
tests/test_slash_redirect_308.py."""

_M = "src/astro_ai/main.py"

MUTATIONS = [
    ("#1176: the slash toggle goes back to Starlette's 307",
     _M, 'message = {**message, "status": 308}', 'message = {**message, "status": 307}',
     "test_get_trailing_slash_is_308_to_the_bare_path"),
    ("#1176: the GET/HEAD guard is dropped (a POST redirect becomes 308)",
     _M, 'or scope.get("method") not in ("GET", "HEAD"):', 'or False:',
     "test_post_to_a_slash_variant_stays_307"),
    ("#1176: the toggle check is dropped (any 307 becomes 308)",
     _M, "if location is not None and self._is_slash_toggle(scope, location):",
     "if location is not None:",
     "test_a_307_that_is_not_a_slash_toggle_is_untouched"),
    ("#1176: the query comparison is dropped (a redirect carrying a new query becomes 308)",
     _M, 'if parts.query != scope.get("query_string", b"").decode("latin-1"):\n            return False\n',
     "",
     "test_the_query_must_match_for_the_toggle_to_count"),
    ("#1176: only a 307 is rewritten becomes any status (a 301 turns 308)",
     _M, 'message.get("status") == 307:', 'message.get("status") in (301, 302, 303, 307):',
     "test_only_a_307_is_rewritten"),
    ("#1176: the middleware is not installed",
     _M, "app.add_middleware(_SlashRedirect308Middleware)\n", "",
     "test_get_missing_slash_is_308_to_the_slashed_path"),
]
