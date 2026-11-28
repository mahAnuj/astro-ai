"""#1324: the owner's Telegram muhurat alert counts what the finder headline counts.
tests/test_muhurat_honest_count_and_zone.py."""

MUTATIONS = [
    ("#1324: the alert's good_count goes back to every non-avoid date, caution included",
     "src/astro_ai/routes/muhurat.py",
     "_good_count = sum(1 for c in candidates if c.rating in _muhurat.AUSPICIOUS_RATINGS)",
     '_good_count = sum(1 for c in candidates if c.rating != "avoid")',
     "test_alert_count_equals_the_headline_count_with_a_caution_date"),
]
