"""#1073: the Jupiter-in-10th guide answers its long-tail queries (Pisces, Sagittarius, aspects, marriage age).

Held: knowledge/aspects.md (Jupiter's 5th/7th/9th aspects), knowledge/houses.md (Rao's house significations),
knowledge/vedic_reference.md 5.5 (marriage-timing indicators). No held source gives a marriage AGE for Jupiter in the
10th. Each row re-breaks one claim and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_J = "src/astro_ai/templates/learn/jupiter-in-10th-house-career.html"

MUTATIONS = [
    ("#1073: the Pisces H3 loses its searched phrasing",
     _J,
     "<h3>Jupiter in Pisces in the 10th house (Gemini ascendant)</h3>",
     "<h3>Gemini ascendant: the Pisces placement</h3>",
     "test_the_two_own_sign_placements_have_their_own_h3"),
    ("#1073: the aspect section names the wrong houses (3rd, 5th, 7th instead of 2nd, 4th, 6th)",
     _J,
     "So Jupiter in the 10th aspects the 2nd, 4th and 6th houses of the chart.",
     "So Jupiter in the 10th aspects the 3rd, 5th and 7th houses of the chart.",
     "test_the_aspect_h2_exists_and_names_the_2nd_4th_6th"),
    ("#1073: the aspect section says Jupiter in the 10th aspects the 7th house",
     _J,
     "he does not aspect the 7th house or the 10th house he sits in.",
     "he also aspects the 7th house.",
     "test_the_aspect_h2_exists_and_names_the_2nd_4th_6th"),
    ("#1073: ascendant arithmetic wrong (Sagittarius called the 10th from Gemini's neighbour, aspects on the wrong signs)",
     _J,
     "fall on Aries, Gemini and Leo, which are the 2nd, 4th and 6th houses of a Pisces-ascendant chart.",
     "fall on Taurus, Cancer and Virgo, which are the 2nd, 4th and 6th houses of a Pisces-ascendant chart.",
     "test_the_sign_sections_keep_the_ascendant_arithmetic_right"),
    ("#1073: the marriage section states an age window nothing held gives",
     _J,
     "This page gives no age or age range for marriage because we hold no source that ties one to Jupiter in the 10th.",
     "Marriage typically happens between 27-32 with Jupiter in the 10th.",
     "test_the_marriage_section_exists_gives_the_held_indicators_and_no_age"),
    ("#1073: the marriage section drops the held indicators (the transit over the natal Moon)",
     _J,
     "a <strong>transit of Jupiter</strong> through the 7th house or over the natal Moon.",
     "a <strong>transit of Jupiter</strong> through the 7th house.",
     "test_the_marriage_section_exists_gives_the_held_indicators_and_no_age"),
    ("#1073: the marriage section loses its link to the timing guide",
     _J,
     '<a href="/learn/marriage-mahadasha-timing/">Marriage timing by Mahadasha</a>',
     "Marriage timing by Mahadasha",
     "test_the_marriage_section_links_the_timing_guide"),
]
