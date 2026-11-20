"""#1277 (#1070 slice 4) -- `fetch_ga4.py --daily` carries returning users and per-day
admin landings from two optional requests. tests/test_ga4_daily_returning.py."""

_GA = "scripts/fetch_ga4.py"

MUTATIONS = [
    ("#1277: the returning request's ApiError is no longer caught (a 403 kills the base series)",
     _GA, "    except ApiError as e:\n        ret_status =",
     "    except KeyError as e:\n        ret_status =",
     "test_a_failing_returning_request_is_null_with_the_http_code_and_base_rows_intact"),
    ("#1277: share_pct loses its zero-denominator guard (0 / 0 raises instead of null)",
     _GA, "if ok_ret and total_users else None)", "if ok_ret else None)",
     "test_share_is_null_when_status_is_not_ok_and_when_the_denominator_is_zero"),
    ("#1277: a failed returning request reads 0 instead of null (\"nobody came back\")",
     _GA, 'row["returning_users"] = returning.get(iso, 0) if ok_ret else None',
     'row["returning_users"] = returning.get(iso, 0) if ok_ret else 0',
     "test_a_failing_returning_request_is_null_with_the_http_code_and_base_rows_intact"),
    ("#1277: the admin landing regex is dropped (every landing counts as an admin leak)",
     _GA, 'ADMIN_LANDING_RE = "/admin([/?].*)?"', 'ADMIN_LANDING_RE = ".*"',
     "test_request_bodies_use_newvsreturning_and_the_admin_regex_filter"),
]
