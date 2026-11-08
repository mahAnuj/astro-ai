"""qa-on-green re-checks a held PR once a fix lands after its QA FAIL (2026-11-07, #747)."""

MUTATIONS = [
    ("held refix: every held PR is declined again, fix or not",
     ".github/workflows/qa-on-green.yml",
     '              if [ "$refix" != true ]; then\n                say "PR #$num carries \\`needs-human-review\\` — someone has been told."; exit 0\n',
     '              if true; then\n                say "PR #$num carries \\`needs-human-review\\` — someone has been told."; exit 0\n',
     "test_a_held_PR_with_a_fix_since_its_fail_gets_a_round"),
    ("held refix: a held PR with no fix is dispatched too",
     ".github/workflows/qa-on-green.yml",
     '              if [ "$refix" != true ]; then\n                say "PR #$num carries \\`needs-human-review\\` — someone has been told."; exit 0\n',
     '              if false; then\n                say "PR #$num carries \\`needs-human-review\\` — someone has been told."; exit 0\n',
     "test_a_held_PR_with_no_fix_is_still_left_alone"),
]
