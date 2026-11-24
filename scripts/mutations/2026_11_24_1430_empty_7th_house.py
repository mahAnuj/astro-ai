"""#1430: the empty-7th-house section on /learn/planets-in-7th-house-marriage/ stays a signpost.

`knowledge/*.md` holds no rule for reading a 7th house with no planet in it, so the section says
only where to look (the 7th lord), labels that as practice in its own callout, and links the
7th-lord guide. Each row restores one thing the astro-auditor ruling forbade, or removes one
thing the section must keep, and names the test that must go red."""

_P = "src/astro_ai/templates/learn/planets-in-7th-house-marriage.html"

_PRACTICE = "In practice, practitioners commonly look at that planet's sign, house and aspects when no planet sits in the 7th."
_CHART = "an empty house is still part of your chart."
_CALLOUT = "The sources we hold do not set out how to read a 7th house with no planet in it. What we can trace to them is narrower:"
_LINK = '<a href="/learn/7th-lord-placement-marriage-guide/">the 7th lord guide</a>'
_OPENER = "A house is read whether or not a planet sits in it, so a 7th house with no planet in it is still read."

MUTATIONS = [
    ("#1430: the empty-7th section again states 'an empty 7th is read through the 7th lord' as a plain rule",
     _P,
     _PRACTICE,
     "An empty 7th is read through the 7th lord.",
     "test_block_makes_none_of_the_claims_the_corpus_cannot_back"),
    ("#1430: the practice callout loses its 'sources we hold do not set out' sentence",
     _P,
     _CALLOUT,
     "What we can trace to them is narrower:",
     "test_block_has_one_practice_callout_with_the_audited_body"),
    ("#1430: the empty-7th section promises 'a smoother marriage'",
     _P,
     _CHART,
     "an empty house is still part of your chart, and often gives a smoother marriage.",
     "test_block_makes_none_of_the_claims_the_corpus_cannot_back"),
    ("#1430: the empty-7th section loses its link to the 7th-lord guide",
     _P,
     _LINK,
     "the 7th lord guide",
     "test_block_points_to_the_7th_lord_guide_and_the_kundli_in_words"),
    ("#1430: the empty-7th section asserts Malavya Yoga unconditionally",
     _P,
     _CHART,
     "an empty house is still part of your chart, and Venus in the 7th always gives Malavya Yoga.",
     "test_block_makes_none_of_the_claims_the_corpus_cannot_back"),
    ("#1430: the empty-7th opener again asserts 'does not mean no marriage'",
     _P,
     _OPENER,
     "A 7th house with no planet in it does not mean no marriage, and it is not a verdict on whether or when you marry.",
     "test_block_makes_none_of_the_claims_the_corpus_cannot_back"),
]
