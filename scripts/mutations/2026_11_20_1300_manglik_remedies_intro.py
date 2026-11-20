"""#1300: the manglik-remedies intro callout stops attributing the house list to "classical tradition".

The row restores the old template fragment and names the test that must go red."""

MUTATIONS = [
    ("#1300: manglik-remedies intro says classical tradition flags the houses for marriage friction again",
     "src/astro_ai/templates/learn/manglik-remedies.html",
     "and that the modern books we work from link to marriage friction, though they disagree on how much weight the dosha deserves",
     "that classical tradition flags for marriage friction",
     "test_manglik_remedies_summary_carries_the_clause"),
]
