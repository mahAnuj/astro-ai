"""#1411: the three dosha checks declare `tool_error` {tool, kind} on a refused submit.

Rows target templates/dosha_check_form.html and routes/dosha.py, which
tests/test_analytics_tool_error_dosha.py exercises through the real routes. One area
file, a literal list (test_mutation_tables.py requires it)."""

_T = "src/astro_ai/templates/dosha_check_form.html"
_R = "src/astro_ai/routes/dosha.py"

MUTATIONS = [
    ("#1411: dosha_check_form.html stops declaring tool_error",
     _T,
     "{% if _tool %}{{ analytics_event('tool_error', {'tool': _tool, 'kind': _k}) }}{% endif %}\n",
     "",
     "test_a_refused_date_declares_tool_error_validation"),
    ("#1411: dosha_check_form.html declares tool_error on every render (error guard dropped)",
     _T,
     "{% if error %}\n    <div class=\"mb-4 p-3 bg-red-50",
     "{% if True %}\n    <div class=\"mb-4 p-3 bg-red-50",
     "test_no_marker_on_a_get_or_a_success"),
    ("#1411: the template trusts the route's error_kind instead of its whitelist",
     _T,
     "{% set _k = error_kind if error_kind in ['validation'] else 'validation' %}",
     "{% set _k = error_kind %}",
     "test_the_template_only_ever_emits_a_known_kind"),
    ("#1411: the route reports a refused submit as a compute failure",
     _R,
     "\"error_kind\": \"validation\" if error else None,",
     "\"error_kind\": \"compute\" if error else None,",
     "test_the_route_context_names_the_fixed_kind_only_on_an_error"),
    ("#1411: the tool_error marker carries the error text (echoes the typed place)",
     _T,
     "'kind': _k}",
     "'kind': _k, 'message': error}",
     "test_the_marker_carries_no_typed_text"),
    ("#1411: the tool_error marker carries the birth city",
     _T,
     "'kind': _k}",
     "'kind': _k, 'city': prefill.birth_place}",
     "test_the_marker_carries_no_typed_text"),
    ("#1411: every dosha page reports tool=manglik (the three checks are indistinguishable)",
     _T,
     "'tool': _tool, 'kind': _k}",
     "'tool': 'manglik', 'kind': _k}",
     "test_a_refused_date_declares_tool_error_validation"),
    ("#1411: an unrecognised form action declares tool_error with tool=None",
     _T,
     "{% if _tool %}{{ analytics_event('tool_error'",
     "{% if True %}{{ analytics_event('tool_error'",
     "test_an_unrecognised_form_action_declares_nothing_and_does_not_raise"),
]
