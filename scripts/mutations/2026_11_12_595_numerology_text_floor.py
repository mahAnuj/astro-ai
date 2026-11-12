"""#595: numerology.html holds the 12px mobile text floor and stays pinned in TEXT_FLOOR_CLEAN.

Each row re-breaks one property tests/test_numerology_text_floor.py holds."""

MUTATIONS = [
    ("#595: the Lo Shu 'Missing' tag goes back to 9px",
     "src/astro_ai/templates/numerology.html",
     '<div class="text-xs mt-1 text-bhagya-muted-2 uppercase tracking-wider">Missing</div>',
     '<div class="text-[9px] mt-1 text-bhagya-muted-2 uppercase tracking-wider">Missing</div>',
     "test_numerology_has_no_utility_text_under_12px"),
    ("#595: a Lo Shu count chip goes back to 10px",
     "src/astro_ai/templates/numerology.html",
     '<div class="text-xs mt-1 px-1.5 py-0.5 rounded-full bg-bhagya-night',
     '<div class="text-[10px] mt-1 px-1.5 py-0.5 rounded-full bg-bhagya-night',
     "test_missing_tag_and_count_chips_are_text_xs"),
    ("#595: numerology.html is dropped from TEXT_FLOOR_CLEAN",
     "scripts/verify_redesign_tokens.py",
     '    "src/astro_ai/templates/numerology.html",  # #595\n',
     '',
     "test_numerology_is_pinned_in_the_floor_clean_list"),
]
