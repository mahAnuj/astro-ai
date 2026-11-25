"""#1376 (a): the /matching Manglik paragraph stops listing "comparable severity" as a classical cancellation.

Each row restores the old wording on that paragraph and names the test that must go red."""

_T = "src/astro_ai/templates/matching.html"

MUTATIONS = [
    ("#1376: /matching lists both-Manglik comparable severity among the implemented cancellations again",
     _T,
     "cancellations it implements &mdash; Mars in own or exalted sign;",
     "cancellations it implements &mdash; both partners Manglik at comparable severity; Mars in own or exalted sign;",
     "test_matching_page_does_not_list_comparable_severity_among_implemented_cancellations"),
    ("#1376: /matching calls the comparable-severity band a classical condition again",
     _T,
     "which is Bhagya's own condition, not a classical one.",
     "which is the classical condition.",
     "test_matching_page_names_the_comparable_band_as_bhagyas_own"),
    ("#1376: /matching stops saying the antidote list names no severity condition",
     _T,
     "says the dosha is cancelled and names no severity condition; Bhagya",
     "says the dosha is cancelled; Bhagya",
     "test_matching_page_says_the_antidote_list_names_no_severity_condition"),
]
