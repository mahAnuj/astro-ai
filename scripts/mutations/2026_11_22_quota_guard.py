"""The chain_cycle quota guard fails closed (2026-11-22, #1282): scripts/chain_cycle.py
quota_reason and freshest, exercised by tests/test_chain_cycle.py. One area file, a literal list."""

MUTATIONS = [
    # The bounds are written as `not 0 <= used <= 1`, which is True for NaN, so dropping
    # math.isfinite alone is an equivalent mutant. The real defect shape is the NEGATED
    # comparison (`used < 0 or used > 1`), which NaN slips through.
    ("quota guard: the bounds are written so NaN passes them (negated comparison)",
     "scripts/chain_cycle.py",
     "    if not math.isfinite(used) or not 0 <= used <= 1:\n",
     "    if used < 0 or used > 1:\n",
     "test_a_malformed_seven_day_reading_stops_the_chain"),
    ("quota guard: an out-of-range seven_day (negative, above 1) passes the bounds check",
     "scripts/chain_cycle.py",
     "    if not math.isfinite(used) or not 0 <= used <= 1:\n",
     "    if not math.isfinite(used):\n",
     "test_a_malformed_seven_day_reading_stops_the_chain"),
    ("quota guard: a future generated_at is read as a fresh reading",
     "scripts/chain_cycle.py",
     '    for what, ahead in (("generated_at", -age), ("latest.at", at_ahead)):\n',
     '    for what, ahead in (("latest.at", at_ahead),):\n',
     "test_a_future_generated_at_stops_it"),
    ("quota guard: a future latest.at is read as a fresh reading",
     "scripts/chain_cycle.py",
     '    for what, ahead in (("generated_at", -age), ("latest.at", at_ahead)):\n',
     '    for what, ahead in (("generated_at", -age),):\n',
     "test_a_future_reading_at_stops_it"),
    ("quota guard: no clock skew is tolerated, so a runner a minute ahead stops the loop",
     "scripts/chain_cycle.py",
     "QUOTA_FUTURE_SKEW = timedelta(minutes=5)\n",
     "QUOTA_FUTURE_SKEW = timedelta(0)\n",
     "test_a_future_generated_at_stops_it"),
    ("quota guard: windows_reset runs before validation, so NaN plus past resets opens the chain",
     "scripts/chain_cycle.py",
     "    if not math.isfinite(used) or not 0 <= used <= 1:\n",
     "    if windows_reset(latest, now):\n        return None\n    if not math.isfinite(used) or not 0 <= used <= 1:\n",
     "test_a_nan_reading_with_expired_windows_still_stops_it"),
    ("quota guard: a future-dated file reading shields itself from a real fresh one",
     "scripts/chain_cycle.py",
     "        newer = (latest_at is None or _ts(latest_at) > now + QUOTA_FUTURE_SKEW\n"
     "                 or _ts(fresh[\"at\"]) > _ts(latest_at))\n",
     "        newer = latest_at is None or _ts(fresh[\"at\"]) > _ts(latest_at)\n",
     "test_a_future_pinned_reading_does_not_shield_itself_from_a_real_one"),
]
