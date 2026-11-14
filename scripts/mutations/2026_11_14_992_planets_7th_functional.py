"""#992: the planets-in-the-7th guide stops asserting functional verdicts by Ascendant and ranking Venus BEST.

Each row restores one defect and names the test that must go red."""

_T = "src/astro_ai/templates/learn/planets-in-7th-house-marriage.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#992: Sun is a 'functional malefic' for Capricorn/Aquarius again",
     _T,
     "so this page does not call the Sun a functional malefic for either.",
     "so the Sun becomes a functional malefic for these Ascendants.",
     "test_no_functional_verdict_by_ascendant_is_asserted"),
    ("#992: Saturn 'is not a functional malefic' for Cancer again",
     _T,
     "so this page does not rule on whether that lordship softens or sharpens the reading.",
     "and Saturn is not a functional malefic for Cancer.",
     "test_no_functional_verdict_by_ascendant_is_asserted"),
    ("#992: the Jupiter late-marriage softening loses its practice label",
     _T,
     "That is practice, not something the sources we hold state.</li>\n  <li><strong>Capricorn or Aquarius",
     "</li>\n  <li><strong>Capricorn or Aquarius",
     "test_jupiter_caveat_is_labelled_practice"),
    ("#992: Saturn's Leo-Ascendant lordship is stated as the 8th house (false: it is the 6th)",
     _T,
     "rules the 6th house from a Leo Ascendant",
     "rules the 8th house from a Leo Ascendant",
     "test_house_lordships_stated_are_the_true_ones"),
    ("#992: the llm_summary ranks Venus in the 7th BEST again",
     _R,
     "• Venus in 7th: Malavya Yoga only when Venus is in her own sign or exalted there",
     "• Venus in 7th: BEST — Malavya Yoga only when Venus is in her own sign or exalted there",
     "test_venus_is_not_ranked_best_and_malavya_is_conditional"),
]
