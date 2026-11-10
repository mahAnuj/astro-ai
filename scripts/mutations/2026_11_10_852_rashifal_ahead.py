"""#852 (2026-11-10): tomorrow's rashifal is written the day before.

Measured: the 22:00 UTC job started 00:50-03:59 UTC, after the 01:00 UTC Groq
warm, so Groq generated every day (177 calls / 778,261 input tokens a week).
Each row re-breaks one piece of the fix."""

MUTATIONS = [
    ("#852: a scheduled run writes today again, so it lands after the Groq warm",
     "scripts/rashifal_target_date.py",
     '    if event == "schedule":\n',
     '    if False:\n',
     "test_a_scheduled_run_writes_the_next_ist_day_it_can_still_beat"),
    ("#852: 'tomorrow' instead of 'IST now + 18h', so a run after IST midnight writes the day after",
     "scripts/rashifal_target_date.py",
     "LEAD = timedelta(hours=18)\n",
     "LEAD = timedelta(hours=24)\n",
     "test_a_scheduled_run_writes_the_next_ist_day_it_can_still_beat"),
    ("#852: a manual run writes tomorrow too, so a bad day cannot be regenerated",
     "scripts/rashifal_target_date.py",
     "    return ist.date().isoformat()\n",
     "    return (ist + LEAD).date().isoformat()\n",
     "test_a_manual_run_writes_today_so_a_bad_day_can_be_regenerated"),
    ("#852: an unvalidated --date reaches the scripts",
     "scripts/rashifal_target_date.py",
     '        if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", given):\n',
     '        if False:\n',
     "test_a_given_date_wins_and_a_bad_one_is_refused"),
    ("#852: the cron goes back to 22:00 UTC",
     ".github/workflows/rashifal-generate.yml",
     '    - cron: "17 6 * * *"\n',
     '    - cron: "0 22 * * *"\n',
     "test_the_cron_lands_before_ist_midnight_even_at_the_worst_measured_delay"),
    ("#852: the publish step drops --date and writes the runner's guess of the day",
     ".github/workflows/rashifal-generate.yml",
     '            --date "$RASHIFAL_DATE" --file $RUNDIR/rashifal-${{ matrix.lang }}.txt $MERGE\n',
     '            --file $RUNDIR/rashifal-${{ matrix.lang }}.txt $MERGE\n',
     "test_the_day_is_computed_once_and_passed_to_every_script_call"),
    ("#852: an unread run record reads as 'no run recorded' again",
     "src/astro_ai/ops_data.py",
     "                                        fetch, initial=None)",
     "                                        fetch, initial={})",
     "test_an_unread_record_is_loading_not_never_ran"),
]
