"""2026-11-11: the Team header's 'last run failed' test asserts on the marker,
not the bare phrase (a real issue title carrying it went red on main).

The row proves the narrowed assertion still catches the defect it guards."""

MUTATIONS = [
    ("#628: the Team header shows 'N loops last run failed' even when none failed",
     "src/astro_ai/templates/admin_ops.html",
     '{% elif A.last_failed %}<span style="color:var(--failed)">',
     '{% elif true %}<span style="color:var(--failed)">',
     "test_the_team_header_is_unchanged_when_nothing_failed"),
]
