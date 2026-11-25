"""#1320: the /manglik-check remedies card stops calling the practices classical.

The row restores the old blurb and names the test that must go red."""

MUTATIONS = [
    ("#1320: the /manglik-check remedies card calls the practices classical again",
     "src/astro_ai/templates/dosha_check_form.html",
     "Traditional remedies for Mars in a marriage chart, and which of them a source we hold supports",
     "Classical practices to soften Mars in a marriage chart",
     "test_manglik_check_remedies_card_does_not_call_the_practices_classical"),
]
