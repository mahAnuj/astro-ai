"""#1072: the dasha-explained page answers 'which mahadasha is best for career' with the sourced rule, no ranking.

Each row removes one property of the answer and names the test that must go red."""

_T = "src/astro_ai/templates/learn/vimshottari-dasha-explained.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#1072: the answer is a ranking again, not 'no Mahadasha is best for everyone'",
     _T,
     "<strong>No Mahadasha is the best career period for everyone.</strong>",
     "<strong>Saturn is the best career Mahadasha.</strong>",
     "test_answer_is_no_single_best_and_cites_the_three_factors"),
    ("#1072: the Sun/Mercury/Saturn patterns lose their 'practice, not guarantee' label",
     _T,
     "which are reading habits and not guarantees:",
     "which classical texts guarantee:",
     "test_career_patterns_are_labelled_practice_and_nine_dashas_are_not_ranked"),
    ("#1072: the 'we do not rank the nine dashas' sentence is dropped",
     _T,
     "We do not rank the nine dashas for career, and the books we hold do not support a ranking.",
     "Each dasha has its own career story.",
     "test_career_patterns_are_labelled_practice_and_nine_dashas_are_not_ranked"),
    ("#1072: the link to the /dasha tool is removed from the section",
     _T,
     '<a href="/dasha">open your dasha timeline</a>',
     "open your dasha timeline",
     "test_section_links_to_the_dasha_tool"),
    ("#1072: the FAQ entry is removed from the registry",
     _R,
     '"q": "Which Mahadasha is best for career?",',
     '"q": "Which Mahadasha is best for the career question?",',
     "test_page_asks_the_question_in_a_heading_and_in_the_faq"),
]
