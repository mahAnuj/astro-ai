"""#1089: a name that mixes scripts is refused, not scored on its Latin words alone.

Each row re-breaks one claim and names the test that must go red."""

MUTATIONS = [
    ("#1089: /numerology scores a mixed-script name on its Latin words again",
     "src/astro_ai/routes/numerology.py",
     "    if len(_num._clean_name(name)) < 2 or _dropped:\n",
     "    if len(_num._clean_name(name)) < 2:\n",
     "test_a_name_with_a_letter_that_cannot_be_scored_is_refused"),
    ("#1089: the refusal no longer says which characters it would have ignored",
     "src/astro_ai/routes/numerology.py",
     "        if _dropped:\n            _msg +=",
     "        if False:\n            _msg +=",
     "test_the_refusal_names_the_characters_it_would_have_ignored"),
    ("#1089: the compatibility form scores a mixed-script name on either side again",
     "src/astro_ai/routes/numerology.py",
     "        if len(_num._clean_name(value)) < 2 or _num.unscored_letters(value)\n",
     "        if len(_num._clean_name(value)) < 2\n",
     "test_compatibility_refuses_a_mixed_script_name_on_either_side"),
    ("#1089: a Devanagari vowel sign (category M) is not counted as a dropped letter",
     "src/astro_ai/numerology.py",
     '''unicodedata.category(ch)[0] in ("L", "M")''',
     '''unicodedata.category(ch)[0] in ("L",)''',
     "test_unscored_letters_ignores_spaces_hyphens_and_accents"),
    ("#1089: an accented Latin name is reported as unscoreable",
     "src/astro_ai/numerology.py",
     "and not _clean_name(ch) and ch not in out",
     "and ch not in out",
     "test_names_that_are_wholly_latin_are_still_scored"),
]
