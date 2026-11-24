"""chain_cycle._ts raised AttributeError on a non-string stamp, past quota_reason's except (#1372)."""

MUTATIONS = [
    ("chain: a non-string timestamp is not rejected by _ts (AttributeError escapes)",
     "scripts/chain_cycle.py",
     "    if not isinstance(s, str):\n",
     "    if False:\n",
     "test_a_non_string_timestamp_stops_the_chain_instead_of_crashing"),
]
