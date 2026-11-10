"""#843: per-word compounds on /numerology.

Each row re-breaks one claim and names the test that must go red."""

MUTATIONS = [
    ("#843: a one-word name gets a word panel that only repeats the whole-name compound",
     "src/astro_ai/numerology.py",
     "    if len(words) < 2:\n        return ()\n",
     "    if len(words) < 1:\n        return ()\n",
     "test_one_word_name_has_no_word_panel"),
    ("#843: words outside Cheiro's 10-52 series are given a compound anyway",
     "src/astro_ai/numerology.py",
     "        if 10 <= total <= 52:\n            out.append((w, total, _get_compound_meaning(total)))",
     "        if True:\n            out.append((w, total, _get_compound_meaning(total)))",
     "test_word_outside_the_10_52_series_is_left_out"),
    ("#843: the per-word total drops a letter, so Lloyd is no longer 18",
     "src/astro_ai/numerology.py",
     "        total = sum(_CHALDEAN.get(c, 0) for c in _clean_name(w))\n",
     "        total = sum(_CHALDEAN.get(c, 0) for c in _clean_name(w)[1:])\n",
     "test_lloyd_george_words_are_18_and_25"),
    ("#843: the panel is wired to nothing, so no word is rendered",
     "src/astro_ai/templates/numerology.html",
     "{% for word, compound, meaning in reading.word_compounds %}",
     "{% for word, compound, meaning in [] %}",
     "test_template_renders_the_panel_only_with_words"),
]
