"""#382 -- the subscribe modal must not open over a tool result. Each row re-breaks
one half of the fix: a result page losing its marker, or the gate checking it too late."""

_T = "src/astro_ai/templates"

MUTATIONS = [
    ("#382: /matching result stops carrying the defer marker (modal covers the Guna Milan score)",
     f"{_T}/matching_result.html",
     "<span data-subscribe-defer hidden></span>",
     "",
     "test_matching_result_carries_the_defer_marker"),
    ("#382: /numerology result stops carrying the defer marker (modal covers the Bhagya score)",
     f"{_T}/numerology.html",
     "{% if reading %}<span data-subscribe-defer hidden></span>{% endif %}",
     "",
     "test_numerology_result_carries_the_defer_marker"),
    ("#382: the marker is rendered on the empty numerology form too (modal never shows there)",
     f"{_T}/numerology.html",
     "{% if reading %}<span data-subscribe-defer hidden></span>{% endif %}",
     "<span data-subscribe-defer hidden></span>",
     "test_numerology_empty_form_does_not"),
    ("#382: the gate checks the marker after counting the visit (result burns visit 2, prompt waits for 5)",
     f"{_T}/_subscribe_modal.html",
     "      if (document.querySelector('[data-subscribe-defer]')) return;\n      var visits = parseInt(localStorage.getItem(VISITS_KEY) || '0', 10) + 1;\n      localStorage.setItem(VISITS_KEY, String(visits));",
     "      var visits = parseInt(localStorage.getItem(VISITS_KEY) || '0', 10) + 1;\n      localStorage.setItem(VISITS_KEY, String(visits));\n      if (document.querySelector('[data-subscribe-defer]')) return;",
     "test_the_gate_checks_the_marker_before_it_counts_the_visit"),
]
