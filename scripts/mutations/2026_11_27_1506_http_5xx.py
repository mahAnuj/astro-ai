"""#1506: per-route HTTP 5xx count (src/astro_ai/http_errors.py, scripts/collect_llm_usage.py).
tests/test_http_errors.py and tests/test_collect_llm_usage.py.

Not mutated, deliberately: the `>= 500` gate in HttpErrorMiddleware.__call__. `count()` filters
to 500-599 a second time, so loosening only the gate is an equivalent mutant; the filter row
below is the one that bites."""

_H = "src/astro_ai/http_errors.py"
_M = "src/astro_ai/main.py"
_C = "scripts/collect_llm_usage.py"

MUTATIONS = [
    ("#1506: label by the raw path, not the route template (unbounded keyspace, one row per URL)",
     _H, "return f\"{method} {path if isinstance(path, str) and path else 'unmatched'}\"",
     "return f\"{method} {scope.get('path') or 'unmatched'}\"",
     "test_5xx_counts_under_the_template_and_the_response_is_unchanged"),
    ("#1506: the middleware moves below the host rewrite (route reads None behind Firebase)",
     _M, "app.add_middleware(http_errors.HttpErrorMiddleware)\napp.add_middleware(_RewriteHostFromForwardedMiddleware)\n",
     "app.add_middleware(_RewriteHostFromForwardedMiddleware)\napp.add_middleware(http_errors.HttpErrorMiddleware)\n",
     "test_the_template_survives_the_forwarded_host_rewrite"),
    ("#1506: the middleware swallows an unhandled exception instead of re-raising it",
     _H, "            await _flush_if_due()\n            raise\n",
     "            await _flush_if_due()\n",
     "test_an_unhandled_exception_is_counted_and_re_raised_unchanged"),
    ("#1506: a client disconnect is counted as a server 5xx",
     _H, "        except ClientDisconnect:\n            raise                        # the client left; not a server fault\n",
     "",
     "test_a_client_disconnect_is_not_a_server_fault"),
    ("#1506: count() books 4xx as well as 5xx (scanner 404s bury the signal)",
     _H, "_STATUS_KEYS = frozenset(str(s) for s in range(500, 600))",
     "_STATUS_KEYS = frozenset(str(s) for s in range(400, 600))",
     "test_count_books_only_status_500_to_599"),
    ("#1506: the flush interval gate is removed (one storage write per 5xx)",
     _H, "        if now - _LAST_FLUSH < FLUSH_MIN_INTERVAL_S:\n            return\n",
     "        if False:\n            return\n",
     "test_a_burst_inside_one_interval_is_one_write_and_no_count_is_lost"),
    ("#1506: a failed write drops the drained batch instead of re-queuing it",
     _H, "        if not landed:\n", "        if False:\n",
     "test_a_storage_failure_never_changes_the_response_and_the_count_is_kept"),
    ("#1506: a bool in a hand-edited blob counts as 1",
     _H, "    if isinstance(v, bool) or not isinstance(v, int) or v < 0:",
     "    if not isinstance(v, int) or v < 0:",
     "test_range_summary_skips_what_a_hand_edited_blob_got_wrong"),
    ("#1506: the label cap is lifted (a bug could grow the blob without bound)",
     _H, "    if label in by_route or len(by_route) < MAX_ROUTES - 1:\n        return label\n",
     "    return label\n",
     "test_distinct_raw_paths_share_one_label_and_labels_are_capped"),
    ("#1506: a day with no recorded blob reports a stated 0 instead of unknown",
     _C, "return {**unknown, \"http_5xx_window\": window, \"http_5xx_days_recorded\": 0}",
     "return {**unknown, \"http_5xx_total\": 0, \"http_5xx_by_route\": [], \"http_5xx_window\": window, \"http_5xx_days_recorded\": 0}",
     "test_no_recorded_day_means_total_and_routes_are_unknown_not_zero"),
    ("#1506: slim drops the stated window from the export",
     _C, "\"http_5xx_window\": window, \"http_5xx_days_recorded\": recorded}",
     "\"http_5xx_window\": None, \"http_5xx_days_recorded\": recorded}",
     "test_http_5xx_is_carried_with_its_window_and_coverage"),
    ("#1506: the 5xx route list is no longer capped",
     _C, "\"http_5xx_by_route\": rows[:_HTTP_5XX_MAX_ROUTES],", "\"http_5xx_by_route\": rows,",
     "test_http_5xx_routes_are_sorted_capped_and_clean"),
    ("#1506: an unreadable 5xx record fails the whole collect",
     _C, "    except Exception as exc:  # noqa: BLE001\n        print(f\"::warning::HTTP 5xx record not read",
     "    except KeyError as exc:  # noqa: BLE001\n        print(f\"::warning::HTTP 5xx record not read",
     "test_the_default_summary_attaches_http_errors_and_a_failed_read_is_none"),
]
