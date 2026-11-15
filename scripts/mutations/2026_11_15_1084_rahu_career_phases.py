"""#1084: /learn/rahu-mahadasha-career-problems phase lengths equal the sum of their antardashas (Rahu 18y:
5.1 + 9.45 + 3.45), Rahu is never called combust, and Sagittarius is Rahu's debilitation not an exaltation.

Each row restores one removed false claim and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_T = "src/astro_ai/templates/learn/rahu-mahadasha-career-problems.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#1084: 'The middle 8 years' heading is back (the antardashas under it sum to 9.45 years)",
     _T,
     "Phase 2: The middle 9 years 5 months (Saturn",
     "Phase 2: The middle 8 years (Saturn",
     "test_phase_headings_equal_the_sum_of_their_antardashas"),
    ("#1084: 'The final 5 years' heading is back (the antardashas under it sum to 3.45 years)",
     _T,
     "Phase 3: The final 3 years 5 months (Sun",
     "Phase 3: The final 5 years (Sun",
     "test_phase_headings_equal_the_sum_of_their_antardashas"),
    ("#1084: the page says Rahu is 'combust with Sun' again",
     _T,
     "If Rahu is afflicted — tightly conjunct Mars or Saturn,",
     "If Rahu is afflicted — combust with Sun, tightly conjunct Mars or Saturn,",
     "test_rahu_is_never_called_combust_and_sagittarius_is_not_an_exaltation"),
    ("#1084: the registry FAQ says an afflicted Rahu is 'combust' again",
     _R,
     "An afflicted Rahu (badly aspected by Mars or Saturn,",
     "An afflicted Rahu (combust, badly aspected by Mars or Saturn,",
     "test_rahu_is_never_called_combust_and_sagittarius_is_not_an_exaltation"),
    ("#1084: 'some traditions hold Sagittarius as exaltation' is back",
     _T,
     "Rahu's debilitation is Sagittarius (some texts say Scorpio).",
     "some traditions hold Sagittarius as exaltation, some Taurus.",
     "test_rahu_is_never_called_combust_and_sagittarius_is_not_an_exaltation"),
    ("#1084: 'the classical career-launch placement' for Rahu in the 10th is back",
     _T,
     "in practice often read as a career-visibility placement (the classical texts we draw on give no separate rule for it).",
     "the classical career-launch placement.",
     "test_unsourced_classical_attributions_are_labelled_as_practice"),
    ("#1084: the registry summary again names 'Best sub-periods for major decisions: Rahu-Jupiter and Rahu-Mercury'",
     _R,
     "• The three phases: Rahu-Jupiter about 5 years,",
     "• Best sub-periods for major decisions: Rahu-Jupiter and Rahu-Mercury Antardashas\\n\"\n            \"• The three phases: Rahu-Jupiter about 5 years,",
     "test_registry_has_no_unsourced_best_subperiods_and_no_blue_cloth"),
    ("#1084: 'blue cloth' donation is back in the registry FAQ",
     _R,
     "donate black gram daal, donate to a research organisation,",
     "donate black gram daal or blue cloth on Saturdays, donate to a research organisation,",
     "test_registry_has_no_unsourced_best_subperiods_and_no_blue_cloth"),
]
