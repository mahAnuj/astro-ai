"""#1501: the home-page worry cards stop asserting classical backing the held books do not give.

Each row restores one piece of the old text (or removes the attribution) and names the test that
must go red. Anchors are the NEW wording, each occurring exactly once in index.html."""

_INDEX = "src/astro_ai/templates/index.html"

MUTATIONS = [
    ("#1501: home lead says 'the classical texts' again instead of 'the books we hold'",
     _INDEX,
     "what the books we hold actually say about them",
     "what the classical texts actually say about them",
     "test_home_page_no_longer_asserts_unsourced_classical_backing"),
    ("#1501: Sade Sati card claims most lives are better on the other side again",
     _INDEX,
     "we read it as a course in maturity, and how hard it feels depends on your chart.",
     "a structured course in maturity, and most lives are better on the other side of it.",
     "test_home_page_no_longer_asserts_unsourced_classical_backing"),
    ("#1501: Manglik card says people labelled Manglik actually aren't again",
     _INDEX,
     "Sources disagree &mdash; one lists cancellation rules, one rejects them &mdash; but both say don&rsquo;t over-weight the dosha.",
     "The tradition repeats many cancellation rules &mdash; a lot of people labelled Manglik actually aren&rsquo;t.",
     "test_home_page_no_longer_asserts_unsourced_classical_backing"),
    ("#1501: Kaal Sarp card says 'most over-diagnosed' again",
     _INDEX,
     "Online checkers over-flag it, in our view &mdash; a pattern to understand, not a sentence to fear.",
     "One of the most over-diagnosed conditions in modern astrology &mdash; a structure for understanding a pattern, not a sentence to fear.",
     "test_home_page_no_longer_asserts_unsourced_classical_backing"),
    ("#1501: Kaal Sarp card drops the 'in our view' attribution",
     _INDEX,
     "over-flag it, in our view &mdash;",
     "over-flag it &mdash;",
     "test_home_worry_cards_name_the_books_we_hold_and_attribute_our_own_view"),
]
