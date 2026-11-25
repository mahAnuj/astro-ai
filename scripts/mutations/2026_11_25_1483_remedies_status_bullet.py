"""#1483 (residual, with #1376): the /learn/manglik-remedies/ 'Cancelled' status bullet names
"matching with another Manglik of comparable severity" among the cancellation rules, with no
disclosure that the band is Shubh Bhagya's own. It said no "classical", so the soft-word rule
never saw it; the templates-only UNDISCLOSED rule does. Each row restores one shipped shape and
names the test that must go red. A phrase test: it proves the wording it names, not every rewording."""

_TEMPLATE = "src/astro_ai/templates/learn/manglik-remedies.html"
_TEST = "test_no_surface_calls_comparable_severity_classical"

MUTATIONS = [
    ("#1483: the remedies status bullet lists comparable-severity matching among the cancellation rules again",
     _TEMPLATE,
     "a cancellation rule we implement applies (Cancer/Leo Lagna Yogakaraka rule, Jupiter aspect, own-sign Mars, or matching with another Manglik &mdash; one held antidote list cancels the dosha when both partners carry it and names no severity condition, and the comparable-severity band our matching tool applies is Shubh Bhagya's own convention, not scripture). Remedies",
     "the cancellation rules we implement apply (Cancer/Leo Lagna Yogakaraka rule, Jupiter aspect, own-sign Mars, matching with another Manglik of comparable severity). Remedies",
     _TEST),
    ("#1483: the reworded remedies status bullet loses its disclosure clause",
     _TEMPLATE,
     "or matching with another Manglik &mdash; one held antidote list cancels the dosha when both partners carry it and names no severity condition, and the comparable-severity band our matching tool applies is Shubh Bhagya's own convention, not scripture). Remedies",
     "or matching with another Manglik &mdash; the comparable-severity band cancels the dosha when both partners carry it). Remedies",
     _TEST),
]
