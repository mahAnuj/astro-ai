"""#1416: /matching declares `tool_error` {tool, kind} on its ChartError 400 render.

Rows target templates/error.html (opt-in block) and routes/matching.py, which
tests/test_analytics_tool_error_matching.py exercises through the real route. One area
file, a literal list (test_mutation_tables.py requires it)."""

_T = "src/astro_ai/templates/error.html"
_R = "src/astro_ai/routes/matching.py"

MUTATIONS = [
    ("#1416: error.html stops declaring tool_error",
     _T,
     "{{ analytics_event('tool_error', {'tool': 'matching', 'kind': _k}) }}\n",
     "",
     "test_a_refused_date_declares_tool_error_validation"),
    ("#1416: error.html declares tool_error on every error render (opt-in guard dropped)",
     _T,
     "{% if tool_error_tool == 'matching' %}",
     "{% if True %}",
     "test_other_error_renders_cannot_fire_it"),
    ("#1416: error.html declares tool_error for any route that sets some tool_error_tool",
     _T,
     "{% if tool_error_tool == 'matching' %}",
     "{% if tool_error_tool %}",
     "test_only_the_matching_opt_in_declares_it"),
    ("#1416: the template trusts the route's tool_error_kind instead of its whitelist",
     _T,
     "{% set _k = tool_error_kind if tool_error_kind in ['validation'] else 'validation' %}",
     "{% set _k = tool_error_kind %}",
     "test_the_template_only_ever_emits_a_known_kind"),
    ("#1416: the route reports a refused submit as a compute failure",
     _R,
     "\"tool_error_kind\": \"validation\",",
     "\"tool_error_kind\": \"compute\",",
     "test_the_route_context_sets_the_fixed_opt_in"),
    ("#1416: the route stops opting in to the marker",
     _R,
     "\"tool_error_tool\": \"matching\", \"tool_error_kind\": \"validation\",",
     "\"tool_error_kind\": \"validation\",",
     "test_a_refused_date_declares_tool_error_validation"),
    ("#1416: the tool_error marker carries the error text (echoes the typed place)",
     _T,
     "'kind': _k}",
     "'kind': _k, 'message': message}",
     "test_the_marker_carries_no_typed_text"),
    ("#1416: the tool_error marker carries the page title",
     _T,
     "'kind': _k}",
     "'kind': _k, 'title': title}",
     "test_the_marker_carries_no_typed_text"),
    ("#1416: the tool_error marker reports tool=numerology",
     _T,
     "{'tool': 'matching', 'kind': _k}",
     "{'tool': 'numerology', 'kind': _k}",
     "test_a_refused_date_declares_tool_error_validation"),
]
