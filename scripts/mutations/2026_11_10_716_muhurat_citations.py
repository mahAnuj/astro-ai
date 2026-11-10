"""#716: muhurat.py stops crediting rules to books this repo does not hold, and
scripts/verify_rule_citations.py scans it for them."""

MUTATIONS = [
    ("#716: a comment in muhurat.py credits BPHS again",
     "src/astro_ai/muhurat.py",
     "_TARA_BALA_NAMES = {",
     "# BPHS assigns each position a name.\n_TARA_BALA_NAMES = {",
     "test_the_real_muhurat_file_names_no_unheld_book"),
    ("#716: a comment in muhurat.py credits Muhurta Chintamani again",
     "src/astro_ai/muhurat.py",
     "_TARA_BALA_NAMES = {",
     "# Per Muhurta Chintamani.\n_TARA_BALA_NAMES = {",
     "test_the_real_muhurat_file_names_no_unheld_book"),
    ("#716: the gate's muhurat result is computed and then dropped in main()",
     "scripts/verify_rule_citations.py",
     "        fails += _muhurat_problems(mtext)\n",
     "        pass\n",
     "test_main_fails_when_muhurat_names_an_unheld_book"),
    ("#716: the gate's name scan iterates nothing",
     "scripts/verify_rule_citations.py",
     "    for label, pattern in _MUHURAT_UNHELD:\n",
     "    for label, pattern in ():\n",
     "test_bphs_in_a_comment_is_red"),
]
