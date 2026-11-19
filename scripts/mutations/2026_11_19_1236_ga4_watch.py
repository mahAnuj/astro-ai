"""#1236 -- `fetch_ga4.py --anomalies` watch tier: days at or above median + 10 that are
not spikes get the same source breakdown. tests/test_ga4_watch_days.py."""

_GA = "scripts/fetch_ga4.py"

MUTATIONS = [
    ("#1236: the watch bar moves from median + 10 to median + 11 (a 32-user day is dropped)",
     _GA, 'r.get("active_users", 0) >= med + 10\n',
     'r.get("active_users", 0) >= med + 11\n',
     "test_a_day_at_the_bar_is_in_and_one_below_it_is_out"),
    ("#1236: watch stops excluding spike days (every spike is broken down twice)",
     _GA, ' and r["date"] not in taken]', ']',
     "test_the_five_days_under_the_spike_bar_come_back_most_extreme_first"),
    ("#1236: the watch cap is lifted (up to 2 requests per elevated day, unbounded)",
     _GA, "def watch_days(rows: list[dict], spikes: list[dict], top: int = 7)",
     "def watch_days(rows: list[dict], spikes: list[dict], top: int = 700)",
     "test_the_cap_keeps_the_most_extreme_days"),
    ("#1236: watch_omitted is no longer computed (a truncated tier reads as complete)",
     _GA, "watch_omitted = len(watch_days(rows, spikes, top=len(rows))) - len(watch)",
     "watch_omitted = 0",
     "test_the_request_count_is_bounded_and_the_truncation_is_reported"),
    ("#1236: a failing watch day is no longer caught (it erases the spike breakdown)",
     _GA, "        except ApiError as e:\n            by_source, by_tech = [], []",
     "        except KeyError as e:\n            by_source, by_tech = [], []",
     "test_a_failing_watch_day_leaves_the_spike_breakdown_intact"),
]
