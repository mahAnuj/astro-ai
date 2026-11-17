"""2026-11-16: a spike's automated share is judged per tech segment, not
averaged away. tests/test_analyst_levers.py."""

MUTATIONS = [
    ("spike explanation: zero-engagement segments are averaged into the readers again",
     "scripts/fetch_ga4.py",
     "elif tech_total and dead_n / tech_total >= 0.3:",
     "elif False:",
     "test_bots_inside_a_mostly_human_spike_are_called_out_not_averaged_away"),
]
