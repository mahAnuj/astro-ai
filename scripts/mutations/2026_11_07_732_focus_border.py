"""#732: the focused form-field border is >= 3:1 (WCAG 1.4.11), not saffron's 2.50:1."""

MUTATIONS = [
    ("#732: the focus border is saffron again (2.50:1 on white)",
     "src/astro_ai/templates/base.html",
     "    border-color: #4A4238;\n",
     "    border-color: #E4913C;\n",
     "test_served_page_carries_a_focus_border_rule_that_passes_3_to_1"),
    ("#732: the override rule is removed from the page",
     "src/astro_ai/templates/base.html",
     'input[class*="focus:border-bhagya-saffron"]:focus,\n',
     'input[class*="focus:border-bhagya-saffron-x"]:focus,\n',
     "test_served_page_carries_a_focus_border_rule_that_passes_3_to_1"),
    ("#732: the override repaints the night-nav language picker dark-on-dark",
     "src/astro_ai/templates/base.html",
     ':not([name="lang"]):focus',
     ':focus',
     "test_language_picker_keeps_its_saffron_border_on_the_night_nav"),
]
