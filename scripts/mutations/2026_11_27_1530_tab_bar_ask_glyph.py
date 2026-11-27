"""#1530: the mobile tab bar's Ask glyph is ASCII `?`, not a fullwidth form."""

MUTATIONS = [
    ("#1530: the Ask tab's glyph goes back to the fullwidth question mark (empty box without a CJK font)",
     "src/astro_ai/templates/_tab_bar.html",
     "('/ask',      'Ask',      '?'),",
     "('/ask',      'Ask',      '？'),",
     "test_ask_tab_glyph_is_ascii_question_mark"),
]
