"""#581: name_compound stays the all-letter total and the caption stays truthful.

Each row re-breaks one claim and names the test that must go red."""

MUTATIONS = [
    ("#581: name_compound switches to a sum of word singles (moves every Bhagya score)",
     "src/astro_ai/numerology.py",
     "    name_raw = sum(_CHALDEAN.get(c, 0) for c in letters)\n",
     "    name_raw = sum(_reduce(sum(_CHALDEAN.get(c, 0) for c in _clean_name(w)), preserve_masters=False)\n"
     "                   for w in name.split()) or sum(_CHALDEAN.get(c, 0) for c in letters)\n",
     "test_name_compound_is_the_all_letter_total"),
    ("#581: caption calls the whole-name compound 'the unreduced total of a name' again",
     "src/astro_ai/templates/numerology.html",
     "the total of the letters of a name (10&ndash;52) carries a secondary vibration alongside",
     "the unreduced total of a name (10&ndash;52) carries a secondary vibration alongside",
     "test_caption_does_not_claim_an_unreduced_whole_name_total_is_the_tradition"),
]
