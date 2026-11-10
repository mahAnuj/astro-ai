"""#584: the numerology 0-100 is disclosed as editorial, and compounds carry no score term.

Each row re-breaks one claim and names the test that must go red."""

MUTATIONS = [
    ("#584: the +2 'good compound' tier is back in the Bhagya score",
     "src/astro_ai/numerology.py",
     "    # Clamp + bucket label\n",
     "    if reading.name_compound in (10, 19, 23, 27, 28, 37, 46, 49):\n"
     "        _add(+2, \"nbs_py_harmony\")\n"
     "    # Clamp + bucket label\n",
     "test_name_compound_does_not_move_the_score"),
    ("#584: the -2 'challenging compound' tier is back in the Bhagya score",
     "src/astro_ai/numerology.py",
     "    # Clamp + bucket label\n",
     "    if reading.name_compound in (13, 14, 16, 26, 43):\n"
     "        _add(-2, \"nbs_py_grind\")\n"
     "    # Clamp + bucket label\n",
     "test_name_compound_does_not_move_the_score"),
    ("#584: /numerology no longer renders the editorial-weighting disclosure",
     "src/astro_ai/templates/numerology.html",
     "<p class=\"mt-2 text-xs text-bhagya-muted leading-relaxed\">{{ t(lang, 'num_score_disclosure') }}</p>",
     "",
     "test_reading_page_discloses_the_score_is_editorial"),
    ("#584: /numerology/compatibility no longer renders the editorial-weighting disclosure",
     "src/astro_ai/templates/numerology_compat.html",
     "<p class=\"mt-3 text-xs text-bhagya-muted max-w-xl mx-auto leading-relaxed\">{{ t(lang, 'num_score_disclosure') }}</p>",
     "",
     "test_compat_page_discloses_the_score_is_editorial"),
    ("#584: the English disclosure stops saying the score is an editorial weighting",
     "src/astro_ai/i18n.py",
     "This 0–100 score is Bhagya's own editorial weighting, not a classical computation",
     "This 0–100 score is a classical computation",
     "test_disclosure_text_is_editorial_in_english"),
    ("#584: the Hindi pages lose the Hindi disclosure (fall back to the English text)",
     "src/astro_ai/i18n.py",
     "यह 0–100 स्कोर भाग्य का अपना संपादकीय भारांकन है, कोई शास्त्रीय गणना नहीं",
     "This 0–100 score is Bhagya's own editorial weighting, not a classical computation",
     "test_hindi_pages_carry_the_hindi_disclosure"),
]
