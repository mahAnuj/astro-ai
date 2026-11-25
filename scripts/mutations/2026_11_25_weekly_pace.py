"""The weekly pace (2026-11-25): scripts/chain_cycle.py pace_reason spreads the Claude
quota across the week. Exercised by tests/test_chain_cycle.py. One area file, a literal list."""

MUTATIONS = [
    ("pace: the chain ignores the weekly line again",
     "scripts/chain_cycle.py",
     "    return pace_reason(latest, used, now)\n",
     "    return None\n",
     "test_use_ahead_of_the_weekly_line_waits"),
    ("pace: no burst at the start of the week",
     "scripts/chain_cycle.py",
     "PACE_MARGIN = 0.05\n",
     "PACE_MARGIN = 0.0\n",
     "test_the_week_starts_with_a_burst_and_ends_at_the_ceiling"),
    ("pace: the window is measured from the reset instead of the week's start",
     "scripts/chain_cycle.py",
     "    elapsed = min(max((now - (reset - WEEK)) / WEEK, 0.0), 1.0)\n",
     "    elapsed = min(max((now - reset) / WEEK, 0.0), 1.0)\n",
     "test_use_on_or_behind_the_line_chains"),
    ("pace: a reading with no reset time blocks instead of falling back to the ceiling",
     "scripts/chain_cycle.py",
     "    except (KeyError, TypeError, ValueError, OverflowError, OSError):\n        return None\n    elapsed",
     "    except (KeyError, TypeError, ValueError, OverflowError, OSError):\n        return \"no reset time\"\n    elapsed",
     "test_a_reading_with_no_reset_time_is_judged_by_the_ceiling_alone"),
]
