"""#1313: the manglik-remedies intro and summary stop calling the seven remedies "classically-cited".

Each row restores the old claim on one surface and names the test that must go red."""

MUTATIONS = [
    ("#1313: manglik-remedies intro callout calls the seven remedies classically-cited again",
     "src/astro_ai/templates/learn/manglik-remedies.html",
     "Of the seven practices below, only one is a Manglik antidote in a book we hold",
     "This guide walks the seven classically-cited Manglik remedies",
     "test_manglik_remedies_does_not_call_the_seven_remedies_classically_cited"),
    ("#1313: manglik-remedies registry summary calls the seven remedies classically-cited again",
     "src/astro_ai/learn_registry.py",
     "Of the seven practices here, only matching another Manglik is a Manglik antidote in a book we hold",
     "This guide walks the seven classically-cited remedies",
     "test_manglik_remedies_does_not_call_the_seven_remedies_classically_cited"),
]
