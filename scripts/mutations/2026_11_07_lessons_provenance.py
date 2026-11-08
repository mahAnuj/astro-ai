"""Only this repo's identities may put a competitor pattern into the ledger (independent QA FAIL on #747)."""

MUTATIONS = [
    ("lessons: any author's competitor-pattern issue enters the ledger",
     "scripts/collect_lessons.py",
     "                and author in trusted):\n",
     "                ):\n",
     "test_a_competitor_pattern_from_an_outsider_never_reaches_the_ledger"),
    ("lessons: the owner is not trusted, so only bots count",
     "scripts/collect_lessons.py",
     '    trusted = LOOP_IDENTITIES | {repo.split("/", 1)[0].lower()}\n',
     '    trusted = LOOP_IDENTITIES\n',
     "test_a_competitor_pattern_from_an_outsider_never_reaches_the_ledger"),
    ("lessons: titles are printed raw",
     "scripts/collect_lessons.py",
     '    return " ".join(_UNSAFE.sub("", title or "").split())[:100]\n',
     '    return title or ""\n',
     "test_a_trusted_title_is_printed_as_one_plain_line"),
]
