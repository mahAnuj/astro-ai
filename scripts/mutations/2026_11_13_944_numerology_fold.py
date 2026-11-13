"""#944: /numerology keeps its first input above the mobile tab bar.

Each row re-breaks one part of the fix and names the test that must go red."""

MUTATIONS = [
    ("#944: the long lede is shown at every width again (7 lines push the form under the tab bar)",
     "src/astro_ai/templates/numerology.html",
     '<p class="hidden sm:block text-base sm:text-lg',
     '<p class="block text-base sm:text-lg',
     "test_long_lede_is_hidden_below_sm"),
    ("#944: the short mobile lede is dropped (a mobile visitor sees no lede at all)",
     "src/astro_ai/templates/numerology.html",
     '<p class="sm:hidden text-base text-bhagya-muted',
     '<p class="text-base text-bhagya-muted',
     "test_a_short_lede_shows_only_below_sm"),
    ("#944: the tradition note is trimmed to hide its lead sentence",
     "src/astro_ai/templates/numerology.html",
     "<strong>Note:</strong> Numerology is a modern Western tradition, not classical Vedic Jyotish. <span",
     "<strong>Note:</strong> Numerology is a modern tradition. <span",
     "test_tradition_note_is_untouched_and_stays_visible"),
]
