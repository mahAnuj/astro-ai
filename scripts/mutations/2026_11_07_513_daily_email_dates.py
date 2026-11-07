"""#513 -- the daily email must name its day, and the cross-day opening check must
compare the right things. Each row re-breaks one half."""

_SUB = "src/astro_ai/routes/subscribe.py"
_Q = "src/astro_ai/rashifal_quality.py"
_PUB = "scripts/publish_rashifal.py"

MUTATIONS = [
    ("#513: the subject drops the date again (every send is one mail-client thread)",
     _SUB,
     '    return f"{head} · {when} — Shubh Bhagya"',
     '    return f"{head} — Shubh Bhagya"',
     "test_the_subject_names_the_day_in_both_languages"),
    ("#513: the blast ignores the helper and sends the constant subject",
     _SUB,
     "            subject = daily_rashifal_subject(lang, date.fromisoformat(today_iso))",
     "            subject = \"आज का राशिफल — Shubh Bhagya\" if lang == \"hi\" else \"Today's Rashifal — Shubh Bhagya\"",
     "test_the_blast_sends_the_dated_subject"),
    ("#513: the opening check reads the whole reading, not the first sentence",
     _Q,
     "    return {w for w in _WORD.findall(m.group(1).lower()) if w not in _STOP}",
     "    return {w for w in _WORD.findall((body or '').lower()) if w not in _STOP}",
     "test_only_the_first_sentence_counts"),
    ("#513: the opening check stops filtering stop words (every pair shares 'with')",
     _Q,
     "if w not in _STOP}",
     "if True}",
     "test_unrelated_openings_report_nothing"),
    ("#513: publish compares every rashi with one fixed rashi's yesterday",
     _PUB,
     'before.get(_rashi_of(title), "")',
     'next(iter(before.values()), "")',
     "test_publish_compares_a_rashi_with_its_own_yesterday_only"),
]
