"""The lessons ledger reads analyst verdicts only from analyst scores (QA FAIL on #747)."""

MUTATIONS = [
    ("lessons: any bot comment is read as an analyst score",
     "scripts/collect_lessons.py",
     "    if not _ANALYST_HEAD.match(first):\n        return None\n",
     "    pass\n",
     "test_a_sync_note_that_says_metric_and_inconclusive_is_not_a_verdict"),
    ("lessons: the order sort is dropped, so the API's newest-first order lets the oldest win",
     "scripts/collect_lessons.py",
     '    comments.sort(key=lambda c: c.get("created_at") or "")\n',
     '',
     "test_the_analyst_verdict_is_the_headline_of_the_latest_analyst_score"),
    ("lessons: NOT A PASS is read as PASS",
     "scripts/collect_lessons.py",
     '_CANON = {"NOT A PASS": "MISS", "NOT SCOREABLE": "UNSCOREABLE", "UNSCORED": "UNSCOREABLE"}\n',
     '_CANON = {"NOT SCOREABLE": "UNSCOREABLE", "UNSCORED": "UNSCOREABLE"}\n',
     "test_the_real_headline_vocabulary_is_mapped"),
    ("lessons: an unmapped newer score is skipped, so a stale one survives",
     "scripts/collect_lessons.py",
     '    word = m.group(1).upper() if m else "OTHER"\n',
     '    if not m:\n        return None\n    word = m.group(1).upper()\n',
     "test_a_newer_unmapped_score_still_replaces_an_older_one"),
]
