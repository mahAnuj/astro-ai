"""Option 1: name the supported areas, never "0/4" (2026-11-09)."""

MUTATIONS = [
    ("supported areas: the card lists every area, supported or not",
     "src/astro_ai/templates/_rashifal_card_content.html",
     "{%- set sup = day_detail.areas|selectattr('favourable')|list %}",
     "{%- set sup = day_detail.areas|list %}",
     "test_the_card_names_only_the_supported_areas"),
    ("supported areas: a day with no support prints nothing",
     "src/astro_ai/templates/_rashifal_card_content.html",
     "No area has extra support from the planets today",
     "",
     "test_a_day_with_no_support_says_so_without_a_zero"),
]
