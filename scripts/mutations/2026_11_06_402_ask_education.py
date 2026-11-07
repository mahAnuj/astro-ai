"""#402 AC1/AC6 -- the `education` focus area on /ask and the line that says the
chart cannot settle whether an exam is passed.

Each row re-breaks one property and names the test (tests/test_ask_education.py)
that must go red. The prompt rows put back the wrong claims the CORRECTION comment
on #402 refuted (the 6th house as the exam house) or the verdict the entry exists
to refuse. They prove the TEXT is guarded; no model is called, so they say nothing
about whether a model obeys it."""

_ASK = "src/astro_ai/routes/ask.py"
_HTML = "src/astro_ai/templates/ask.html"
_PROMPT = "src/astro_ai/prompts/ask.txt"

_ENTRY = ("- education: read schooling, intelligence and higher studies "
          "(4th, 5th, 9th; never say these numbers). This chart cannot settle "
          "whether an exam is passed: say so, give no pass/fail, improvise none. "
          "Speak to how supportive the period is for learning and focus.")

MUTATIONS = [
    ("#402 AC1: education is dropped from the accepted categories (coerced to general)",
     _ASK,
     '"spiritual", "travel", "relationships", "education"}',
     '"spiritual", "travel", "relationships"}',
     "test_education_is_an_accepted_category"),
    ("#402 AC1: the education chip is dropped from the template",
     _HTML,
     "'travel', 'relationships', 'education'] %}",
     "'travel', 'relationships'] %}",
     "test_the_education_chip_renders_and_is_checked_when_selected"),
    ("#402 AC1: the category allow-list is removed (any string passes through)",
     _ASK,
     "    if category not in _ASK_CATEGORIES:\n        category = \"general\"\n    if _ask_quota_remaining",
     "    if _ask_quota_remaining",
     "test_an_unknown_category_is_still_coerced_to_general"),
    ("#402 AC1: the prompt loses its education entry",
     _PROMPT,
     _ENTRY + "\n",
     "",
     "test_the_entry_says_the_chart_cannot_settle_an_exam_and_gives_no_verdict"),
    ("#402 AC1: the entry reads the 6th house as the exam house (refuted by the corpus)",
     _PROMPT,
     "(4th, 5th, 9th; never say these numbers)",
     "(4th, 5th, 6th, 9th; never say these numbers)",
     "test_the_entry_names_only_the_bhavas_the_corpus_gives_for_learning"),
    ("#402 AC6: the entry drops the 'cannot settle whether an exam is passed' limit",
     _PROMPT,
     "This chart cannot settle whether an exam is passed: say so, give no pass/fail, improvise none.",
     "Say whether the exam will be passed.",
     "test_the_entry_says_the_chart_cannot_settle_an_exam_and_gives_no_verdict"),
    ("#402 AC6: the entry tells the model to improvise a D-24 reading",
     _PROMPT,
     "improvise none.",
     "read the D-24 from Arudha Lagna.",
     "test_the_entry_does_not_teach_the_model_jargon_it_is_forbidden_to_emit"),
    ("#402 AC6: the entry stops telling the model not to say house numbers",
     _PROMPT,
     "(4th, 5th, 9th; never say these numbers)",
     "(4th, 5th, 9th)",
     "test_the_entry_does_not_teach_the_model_jargon_it_is_forbidden_to_emit"),
    ("#402 AC1: the entry is moved out of CATEGORY GUIDANCE (after the cross-link rule)",
     _PROMPT,
     _ENTRY + "\n\nCROSS-LINK RULE",
     "\n\nCROSS-LINK RULE",
     "test_the_entry_sits_inside_category_guidance_and_the_prompt_still_forbids_house_numbers"),
]
