"""#970: natal.txt line 54's DO NOT phrases are checked, not just requested.

Each row removes or narrows the one `forbidden_phrase` rule and names a DISTINCT test that must go red."""

MUTATIONS = [
    ("#970: the forbidden-phrase rule is dropped from the rule table",
     "src/astro_ai/reading_quality.py",
     '    ("forbidden_phrase", _PHRASE_RULE),\n',
     "",
     "test_each_jargon_phrase_fails_the_verdict_as_a_forbidden_phrase"),
    ("#970: the phrase rule matches only 'transit', so the other four phrases escape",
     "src/astro_ai/reading_quality.py",
     "r\"\\b(?:transit|gochar|natal\\s+Lagna|Bhava|lord\\s+of\\s+the)\\b\", re.I)",
     "r\"\\b(?:transit)\\b\", re.I)",
     "test_every_phrase_natal_txt_line_54_bans_is_caught"),
    ("#970: the phrase rule loses its word boundaries, so 'transitory' and 'Bhavana' are flagged",
     "src/astro_ai/reading_quality.py",
     "r\"\\b(?:transit|gochar|natal\\s+Lagna|Bhava|lord\\s+of\\s+the)\\b\", re.I)",
     "r\"(?:transit|gochar|natal\\s+Lagna|Bhava|lord\\s+of\\s+the)\", re.I)",
     "test_ordinary_prose_is_not_a_forbidden_phrase"),
    ("#970: the phrase rule is case-sensitive and whitespace-exact, so 'Transit' and a wrapped 'natal\\nLagna' escape",
     "src/astro_ai/reading_quality.py",
     "r\"\\b(?:transit|gochar|natal\\s+Lagna|Bhava|lord\\s+of\\s+the)\\b\", re.I)",
     "r\"\\b(?:transit|gochar|natal Lagna|Bhava|lord of the)\\b\")",
     "test_phrases_match_case_insensitively_and_across_a_line_wrap"),
]
