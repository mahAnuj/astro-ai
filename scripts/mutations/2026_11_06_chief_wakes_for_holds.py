"""A trust-boundary hold wakes chief even while a cycle runs (2026-11-06, #706 held 52h)."""

MUTATIONS = [
    ("chief wake: an in-flight cycle stands chief down again, holds or not",
     ".github/workflows/agent-steward.yml",
     '          if [ "$rulings" -gt 0 ]; then\n',
     '          if false; then\n',
     "test_a_boundary_hold_wakes_chief_while_a_cycle_is_in_flight"),
    ("chief wake: every in-flight cycle wakes chief",
     ".github/workflows/agent-steward.yml",
     '          rulings=${rulings:-0}\n',
     '          rulings=1\n',
     "test_an_in_flight_cycle_still_stands_chief_down_when_no_hold_needs_ruling"),
    ("chief wake: the detector stops counting holds",
     "scripts/detect_stalls.py",
     "    print(f\"CHIEF_RULINGS={sum(1 for x in obliged if x['kind'] in OBLIGED_RULING_KINDS)}\")\n",
     "    print(\"CHIEF_RULINGS=0\")\n",
     "test_the_detector_counts_holds_only_chief_can_clear"),
    ("chief wake: chief is not told to fetch the independent round",
     ".github/workflows/agent-steward.yml",
     "            verdict with `scripts/qa_verdict.sh --provenance independent`. Then\n",
     "            verdict. Then\n",
     "test_chief_is_told_to_get_the_independent_round_itself"),
]
