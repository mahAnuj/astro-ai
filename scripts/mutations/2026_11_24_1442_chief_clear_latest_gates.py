"""#1442: chief_clear.py judges the LATEST `gates` run, not every run joined together."""

_ANY_SUCCESS = ('    if not latest or not any(json.loads(l).get("conclusion") == "success"\n'
                '                             for l in gates.splitlines() if l.strip()):')

MUTATIONS = [
    ("chief clear: the OLDEST gates run decides instead of the latest",
     "scripts/chief_clear.py",
     'return max(runs, key=lambda r: (r.get("started_at") or "~", r["id"])) if runs else None',
     'return min(runs, key=lambda r: (r.get("started_at") or "~", r["id"])) if runs else None',
     "test_a_superseded_red_run_does_not_veto_a_green_rerun"),
    ("chief clear: equal started_at is not broken by the higher run id",
     "scripts/chief_clear.py",
     '(r.get("started_at") or "~", r["id"])',
     '(r.get("started_at") or "~",)',
     "test_equal_started_at_is_decided_by_the_higher_id"),
    ("chief clear: a queued run with no started_at sorts first, so an older green wins",
     "scripts/chief_clear.py",
     'r.get("started_at") or "~"',
     'r.get("started_at") or ""',
     "test_a_queued_rerun_with_no_start_time_is_the_latest"),
    ("chief clear: any green run clears, a later red one is ignored",
     "scripts/chief_clear.py",
     '    if not latest or not (latest.get("status") == "completed"\n'
     '                          and latest.get("conclusion") == "success"):',
     _ANY_SUCCESS,
     "test_a_green_run_followed_by_a_red_one_is_refused"),
    ("chief clear: the gates request is not paginated",
     "scripts/chief_clear.py",
     'gates = gh(["api", "--paginate",',
     'gates = gh(["api",',
     "test_the_gates_request_is_paginated_and_filtered_to_gates"),
]
