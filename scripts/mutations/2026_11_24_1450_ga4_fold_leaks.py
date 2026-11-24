"""#1450 -- `fetch_ga4.py fold_location` leaks that #1237's guards did not reach: a bare query
token emitted as a name, a token-shaped name, a double-encoded address in a path and a
/r/<id> kundli snapshot id.

Each row re-breaks one guard and names the test (tests/test_ga4_page_locations_export.py)
that must go red. The over-broad rows (the PII_PARAMS exemption dropped, the /r/ collapse
applied to any segment) and the threshold rows pin the other side: a fix that redacts
ordinary names and slugs would also report no leak. None touches GA4."""

_GA = "scripts/fetch_ga4.py"
_BARE = '    if "=" not in part and name not in PII_PARAMS:\n'
_SHAPED = ("    if len(name) >= _TOKEN_MIN and any(c.isdigit() for c in name) "
           "and any(c.isalpha() for c in name):\n")
_R = '    if len(segs) > 2 and segs[1] == "r" and segs[2]:\n        segs[2] = SNAPSHOT_ID\n'

MUTATIONS = [
    ("#1450: a bare query token is no longer treated as a value (R1a removed)",
     _GA,
     _BARE,
     "    if False:\n",
     "test_a_bare_query_token_as_a_name_is_redacted"),
    ("#1450: every bare name is redacted, the watched ?token and ?email included (R1a over-broad)",
     _GA,
     _BARE,
     '    if "=" not in part:\n',
     "test_watched_names_are_kept_with_a_value_bare_or_decoded"),
    ("#1450: a token-shaped name with a value is no longer redacted (R1b removed)",
     _GA,
     _SHAPED,
     "    if False:\n",
     "test_a_token_shaped_name_with_a_value_is_redacted"),
    ("#1450: the token-shaped threshold is raised to 21 characters",
     _GA,
     "    if len(name) >= _TOKEN_MIN and",
     "    if len(name) >= _TOKEN_MIN + 1 and",
     "test_the_token_shaped_name_threshold_is_exactly_twenty_mixed_characters"),
    ("#1450: the token-shaped threshold is lowered to 19 characters",
     _GA,
     "    if len(name) >= _TOKEN_MIN and",
     "    if len(name) >= _TOKEN_MIN - 1 and",
     "test_the_token_shaped_name_threshold_is_exactly_twenty_mixed_characters"),
    ("#1450: a long name is redacted for holding a digit alone (all-digit name over-redacted)",
     _GA,
     "any(c.isdigit() for c in name) and any(c.isalpha() for c in name):\n",
     "any(c.isdigit() for c in name):\n",
     "test_the_token_shaped_name_threshold_is_exactly_twenty_mixed_characters"),
    ("#1450: a long name is redacted for holding a letter alone (all-letter name over-redacted)",
     _GA,
     "any(c.isdigit() for c in name) and any(c.isalpha() for c in name):\n",
     "any(c.isalpha() for c in name):\n",
     "test_the_token_shaped_name_threshold_is_exactly_twenty_mixed_characters"),
    ("#1450: a path segment holding %25 (a double-encoded address) is no longer redacted",
     _GA,
     '    if "%25" in seg.lower():\n',
     "    if False:\n",
     "test_a_double_encoded_address_in_a_path_is_redacted"),
    ("#1450: the /r/<id> snapshot id is no longer collapsed",
     _GA,
     _R,
     "    if False:\n        segs[2] = SNAPSHOT_ID\n",
     "test_a_snapshot_id_is_collapsed"),
    ("#1450: the snapshot collapse applies to a segment named r at any depth (/learn/r/x)",
     _GA,
     _R,
     '    for i in range(1, len(segs) - 1):\n'
     '        if segs[i] == "r" and segs[i + 1]:\n'
     '            segs[i + 1] = SNAPSHOT_ID\n',
     "test_only_a_top_level_r_with_an_id_is_collapsed"),
]
