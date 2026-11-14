"""#998: the Saturn and Jupiter remedies guides stop asserting functional verdicts by Ascendant.

Each row restores one defect and names the test that must go red."""

_S = "src/astro_ai/templates/learn/saturn-remedies.html"
_J = "src/astro_ai/templates/learn/jupiter-remedies.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#998: Saturn page says blue sapphire should be avoided for Aries as a verdict again",
     _S,
     "<strong>Do not wear it without a chart consultation.</strong>",
     "<strong>Aries Ascendant: Saturn is a functional malefic. Blue sapphire should be avoided.</strong>",
     "test_saturn_page_asserts_no_verdict_by_ascendant"),
    ("#998: Jupiter page lists Taurus and Libra as functional malefic again",
     _J,
     "<strong>Sagittarius or Pisces Ascendant:</strong>",
     "<strong>Taurus and Libra Ascendants: Jupiter is a functional malefic (rules dusthanas).</strong>",
     "test_jupiter_page_asserts_no_verdict_by_ascendant"),
    ("#998: Jupiter page loses its consult-a-chart warning",
     _J,
     "<strong>Do not skip yellow sapphire consultation.</strong>",
     "<strong>Skip it.</strong>",
     "test_consult_a_chart_warning_survives"),
    ("#998: Saturn's Cancer-Ascendant lordship stated as the 6th and 7th (true: 7th and 8th)",
     _S,
     "the 7th and 8th from Cancer",
     "the 6th and 7th from Cancer",
     "test_house_lordships_stated_are_the_true_ones"),
    ("#998: Saturn registry FAQ lists Aries as a functional malefic again",
     _R,
     "he rules the 10th and 11th from Aries, for example",
     "he is a functional malefic for Aries, for example",
     "test_registry_faqs_assert_no_verdict_by_ascendant"),
]
