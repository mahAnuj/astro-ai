"""#1377: the Manglik pairing copy attributes both-Manglik cancellation instead of asserting it."""

MUTATIONS = [
    ("#1377: trivia says Mangal Dosh only matters if both have it and they cancel out again",
     "src/astro_ai/trivia.py",
     "One modern textbook on auspicious times lists Mangal Dosh antidotes: the dosha is cancelled when both partners are Manglik.",
     "Mangal Dosh only matters in marriage if both partners have it — they cancel each other out.",
     "test_trivia_drops_the_inverted_cancellation_claim"),
    ("#1377: marriage-delayed calls matching another Manglik the classical remedy again",
     "src/astro_ai/templates/learn/marriage-delayed.html",
     "(2) a match that is read against the cancellation rules (one held antidote list says the dosha is cancelled when both partners are Manglik);",
     "(2) preference for matching with another Manglik partner (this is the classical remedy, not the anxiety-driving one online vendors push);",
     "test_marriage_delayed_does_not_call_manglik_pairing_the_classical_remedy"),
]
