"""#1008: the Guru-Jupiter guide stops asserting a yellow-sapphire verdict by Ascendant.

Each row restores one defect and names the test that must go red."""

_T = "src/astro_ai/templates/learn/guru-jupiter-in-vedic-astrology.html"

MUTATIONS = [
    ("#1008: Guru-Jupiter guide tells Capricorn Ascendant to avoid yellow sapphire again",
     _T,
     "this page issues no verdict by Ascendant.",
     "this page issues no verdict by Ascendant. <strong>Avoid for Capricorn Ascendant</strong> (functional malefic).",
     "test_guru_jupiter_gem_bullet_asserts_no_verdict_by_ascendant"),
    ("#1008: Guru-Jupiter guide drops the sourced functional-benefic rule from the gem bullet",
     _T,
     "wear only the gemstone of a functional benefic for your chart",
     "wear whichever gemstone you like for your chart",
     "test_guru_jupiter_gem_bullet_keeps_the_sourced_rule_and_the_consult_warning"),
]
