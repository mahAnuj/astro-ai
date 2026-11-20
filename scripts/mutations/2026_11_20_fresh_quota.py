"""The chain reads the freshest quota (2026-11-20): scripts/chain_cycle.py fresh_reading and
freshest. Exercised by tests/test_chain_cycle.py. One area file, a literal list."""

MUTATIONS = [
    ("fresh quota: the chain decides on claude_usage.json alone again",
     "scripts/chain_cycle.py",
     "    usage = freshest(usage, fresh, now)\n",
     "",
     "test_a_stale_warning_does_not_block_a_chain_the_fresh_reading_allows"),
    ("fresh quota: an older log reading overwrites a newer file",
     "scripts/chain_cycle.py",
     "        newer = latest_at is None or _ts(fresh[\"at\"]) > _ts(latest_at)",
     "        newer = True",
     "test_an_older_fresh_reading_never_replaces_a_newer_file"),
    ("fresh quota: a fresh warning is ignored",
     "scripts/chain_cycle.py",
     "    if not got or got.get(\"seven_day\") is None:\n        return None\n",
     "    if not got or got.get(\"seven_day\") is None or got.get(\"status\") != \"allowed\":\n        return None\n",
     "test_a_fresh_warning_still_blocks_even_when_the_file_says_allowed"),
    ("fresh quota: a fresh reading is stamped with now, bypassing the age guard",
     "scripts/chain_cycle.py",
     "\"generated_at\": fresh[\"at\"], \"latest\": fresh}",
     "\"generated_at\": now.strftime(\"%Y-%m-%dT%H:%M:%SZ\"), \"latest\": fresh}",
     "test_a_stale_fresh_reading_still_trips_the_age_guard"),
]
