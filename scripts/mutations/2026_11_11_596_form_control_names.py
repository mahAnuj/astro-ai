"""#596 -- every visible form control needs an accessible name. Each row strips one
`aria-label` the issue added, and requires the rendered-HTML scan to go red on it."""

_T = "src/astro_ai/templates"

MUTATIONS = [
    ("#596: the subscribe modal's city field loses its aria-label (placeholder only, screen reader says 'edit text')",
     f"{_T}/_subscribe_modal.html",
     "aria-label=\"{% if lang == 'hi' %}आपका शहर (वैकल्पिक){% else %}Your city (optional){% endif %}\"",
     "",
     "test_partial_controls_are_named"),
    ("#596: the feedback textarea loses its aria-label",
     f"{_T}/_feedback_widget.html",
     "aria-label=\"{% if lang == 'hi' %}आप क्या सोच रहे हैं?{% else %}Your feedback message{% endif %}\"",
     "",
     "test_partial_controls_are_named"),
    ("#596: the /learn search box loses its aria-label",
     f"{_T}/learn_index.html",
     "aria-label=\"Search articles\"",
     "",
     "test_learn_index_search_is_named"),
]
