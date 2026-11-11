"""#309 -- the subscribe modal must not open over an EMPTY calculator form. Each row
re-breaks one way the path exclusion can rot: a tool dropping out of the list, the
check deleted, the check running after the visit is counted, and the list growing to
cover pages the modal is meant to reach (which only the control test can see)."""

_M = "src/astro_ai/templates/_subscribe_modal.html"

_LOOP = """      var here = window.location.pathname || '';
      for (var j = 0; j < TOOL_FORM_PATHS.length; j++) {
        if (TOOL_FORM_PATHS[j].test(here)) return;
      }
"""
_TAIL = """      if (document.querySelector('[data-subscribe-defer]')) return;
      var visits = parseInt(localStorage.getItem(VISITS_KEY) || '0', 10) + 1;
      localStorage.setItem(VISITS_KEY, String(visits));
"""
# The #382 comment block sits between the two; the anchor spans it exactly.
_BETWEEN = """      // #382: a load that IS a tool result (matching, numerology) must not be
      // covered by this modal — the visitor has just received what they came
      // for. It is not counted as a visit either, so the very next load is the
      // one that reaches the show threshold instead of the prompt being lost.
"""
_LIST_END = """      /^\\/panchang(\\/|$)/,
    ];
    try {
"""

MUTATIONS = [
    ("#309: /panchang drops out of the tool-path list (modal covers the panchang page on visit 2)",
     _M,
     _LIST_END,
     "    ];\n    try {\n",
     "test_empty_calculator_forms_never_open_the_modal"),
    ("#309: the tool-path check is deleted (modal opens over every empty calculator again)",
     _M,
     "        if (TOOL_FORM_PATHS[j].test(here)) return;",
     "        if (false) return;",
     "test_empty_calculator_forms_never_open_the_modal"),
    ("#309: the tool-path check runs after the visit is counted (a tool load burns visit 2, prompt slips to 5)",
     _M,
     _LOOP + _BETWEEN + _TAIL,
     _BETWEEN + _TAIL + _LOOP,
     "test_empty_calculator_forms_never_open_the_modal"),
    ("#309: the exclusion grows to /rashifal, where the prompt is on topic (the control sees the modal vanish)",
     _M,
     _LIST_END,
     "      /^\\/panchang(\\/|$)/,\n      /^\\/rashifal(\\/|$)/,\n    ];\n    try {\n",
     "test_the_modal_still_opens_on_the_next_load_outside_the_tools"),
]
