"""2026-11-25 (#1255): an `issue` queue entry is stood down when a cycle already ran on
it and nothing is new (scripts/reentry.py, wired from cycle_queue.stale_reason).

The danger is the OTHER direction: a wrongly dropped entry is permanent. Each row
re-breaks one condition of the rule, or the fail-open rule, and names the test that
must go red. tests/test_reentry.py and tests/test_cycle_queue.py."""

MUTATIONS = [
    ("re-entry: the entry-vs-trace test is inverted, so a red-gates entry queued AFTER the last cycle is dropped",
     "scripts/reentry.py",
     "    if t_last <= entry_created:\n",
     "    if t_last > entry_created:\n",
     "test_an_entry_queued_AFTER_the_last_cycle_still_runs"),

    ("re-entry: a commit pushed after the last cycle no longer counts as new",
     "scripts/reentry.py",
     "    if head_date > t_last:\n",
     "    if False:\n",
     "test_a_commit_after_the_last_cycle_is_new_work"),

    ("re-entry: a QA verdict after the last cycle no longer counts as new",
     "scripts/reentry.py",
     "if any(v and when > t_last for _who, when, v, _qa in comments):",
     "if any(False and when > t_last for _who, when, v, _qa in comments):",
     "test_a_QA_verdict_after_the_last_cycle_is_new"),

    ("re-entry: a PR that needs main merged in is dropped like a settled one",
     "scripts/reentry.py",
     "    if state in NEEDS_MAIN:\n",
     "    if False:\n",
     "test_a_PR_that_needs_main_merged_in_still_runs"),

    ("re-entry: a read error answers with a reason, so an unreadable entry is dropped for good",
     "scripts/reentry.py",
     "    except Exception:  # noqa: BLE001 -- fail OPEN: any read or parse problem re-enters\n        return None\n",
     "    except Exception:  # noqa: BLE001 -- fail OPEN: any read or parse problem re-enters\n        return 'unreadable'\n",
     "test_a_read_error_starts_the_cycle"),

    ("re-entry: any author's comment is a cycle trace, so an outsider can make the loop skip an issue",
     "scripts/reentry.py",
     "if who == TRACE_BOT and not qa]",
     "if not qa]",
     "test_only_claude_bot_can_write_the_trace"),

    ("re-entry: a `QA:` comment from claude[bot] counts as a cycle trace",
     "scripts/reentry.py",
     "if who == TRACE_BOT and not qa]",
     "if who == TRACE_BOT]",
     "test_a_QA_comment_from_claude_bot_is_not_a_cycle_trace"),

    ("re-entry: two owned PRs are resolved by guessing the first",
     "scripts/reentry.py",
     "    if len(owned) != 1 or not owned[0].get(\"sha\"):\n",
     "    if len(owned) < 1 or not owned[0].get(\"sha\"):\n",
     "test_without_exactly_one_owned_open_PR_the_entry_runs"),

    ("re-entry: the rule widens to `fix_pr`, an explicit request",
     "scripts/reentry.py",
     "    if e.kind != \"issue\":\n        return None\n    try:\n",
     "    if e.kind not in (\"issue\", \"fix_pr\"):\n        return None\n    try:\n",
     "test_only_issue_entries_are_stood_down"),

    ("re-entry: stale_reason never calls the rule, so a no-news entry still costs a cycle",
     "scripts/cycle_queue.py",
     "            return reentry.nothing_new(gh, repo, e)\n",
     "            return None\n",
     "test_an_ISSUE_entry_a_cycle_already_ran_on_with_nothing_new_is_dropped"),
]
