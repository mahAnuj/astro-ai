"""#1087 -- an /ask?q= link whose cached answer is gone must show a notice.

Each row re-breaks one property and names the test
(tests/test_ask_expired_answer.py) that must go red."""

_ASK = "src/astro_ai/routes/ask.py"
_HTML = "src/astro_ai/templates/ask.html"

MUTATIONS = [
    ("#1087: the route never flags a cache miss (silent blank page returns)",
     _ASK,
     '"answer_expired": bool(q) and answer is None,',
     '"answer_expired": False,',
     "test_cache_miss_renders_a_notice_not_a_silent_page"),
    ("#1087: the flag is raised even when the answer was found",
     _ASK,
     '"answer_expired": bool(q) and answer is None,',
     '"answer_expired": bool(q),',
     "test_cache_hit_shows_the_answer_and_no_notice"),
    ("#1087: the flag is raised on a plain form visit with no question",
     _ASK,
     '"answer_expired": bool(q) and answer is None,',
     '"answer_expired": answer is None,',
     "test_plain_form_visit_shows_no_notice"),
    ("#1087: the template drops the notice block",
     _HTML,
     "{% elif answer_expired %}",
     "{% elif false %}",
     "test_cache_miss_renders_a_notice_not_a_silent_page"),
]
