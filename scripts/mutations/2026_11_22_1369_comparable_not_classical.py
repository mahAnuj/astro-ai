"""#1369: no surface calls Manglik-Manglik "comparable severity" classical.

Raman's held antidote list (knowledge/grahas.md 12.4, line 3642) cancels the dosha when both
partners are Manglik and names no severity condition; the band is Shubh Bhagya's own. Each row
restores one sentence that shipped before the fix (7b29d1a) and names the test that must go red.
A phrase test: the rows prove it catches the wording it names, not every rewording."""

MUTATIONS = [
    ("#1369: the matching band sentence says classical texts require comparable severity again",
     "src/astro_ai/matching.py",
     '    "One held antidote list names no severity condition; comparable severity is "\n'
     '    "Bhagya\'s own condition, not scripture — Bhagya treats equal or adjacent "\n'
     '    "grades as comparable, and a low-versus-high pairing as not comparable."\n',
     '    "Classical texts require \'comparable "\n'
     '    "severity\' for this mutual cancellation but do not define the band — Bhagya "\n'
     '    "treats equal or adjacent grades as comparable, and a low-versus-high "\n'
     '    "pairing as not comparable."\n',
     "test_no_surface_calls_comparable_severity_classical"),
    ("#1369: the Manglik keypoint says comparable severity is the classical requirement again",
     "src/astro_ai/learn_registry.py",
     "• Comparable severity is Bhagya's own condition, not scripture — the one held antidote list names no severity condition; state it as ours: equal or adjacent grades",
     "• 'Comparable severity' is the classical requirement; the texts set no band, so Bhagya's own convention (state it as ours, not scripture) is that equal or adjacent grades",
     "test_no_surface_calls_comparable_severity_classical"),
    ("#1369: manglik-dosh opens 'Classical tradition holds ... of comparable severity' again",
     "src/astro_ai/templates/learn/manglik-dosh.html",
     "<p>One held antidote list says the dosha is cancelled when both partners carry Manglik Dosh, and it names no severity condition. The dosha",
     "<p>Classical tradition holds that when both partners carry Manglik Dosh <em>of comparable severity</em>, the two doshas neutralise each other. The dosha",
     "test_no_surface_calls_comparable_severity_classical"),
    ("#1369: the result page says classical texts require the two partners to be of comparable severity again",
     "src/astro_ai/templates/result.html",
     "but one held antidote list names no severity condition; comparable severity is Bhagya's own condition, not scripture, so Bhagya treats",
     "but classical texts require the two partners to be of comparable severity, and they do not define the band, so Bhagya treats",
     "test_no_surface_calls_comparable_severity_classical"),
    ("#1369: the natal LLM instruction says the remedy classically holds only at comparable strength again",
     "src/astro_ai/chart.py",
     '            "One held antidote list cancels it when both partners carry it, naming no "\n'
     '            "severity condition; comparable strength is Shubh Bhagya\'s own condition, so "\n'
     '            "give it as ours and never as \'marry any Manglik\'. Only this one chart is in "\n'
     '            "scope, so say comparability is settled by a compatibility check of both "\n'
     '            "charts. "\n',
     '            "The traditional remedy — a partner who also carries the dosha — classically "\n'
     '            "holds only when both carry it at comparable strength, so give it as that "\n'
     '            "condition and never as \'marry any Manglik\'. Only this one chart is in scope, "\n'
     '            "so say comparability is settled by a compatibility check of both charts. "\n',
     "test_no_surface_calls_comparable_severity_classical"),
    ("#1369: vedic_reference rule 20 is 'of comparable severity | Classical compatibility rule' again",
     "src/astro_ai/knowledge/vedic_reference.md",
     "| 20 | **Both partners are Manglik** | cancels for the marriage match | One held antidote list (Raman, `grahas.md` §12.4, line 3642): both partners Manglik cancels, **no severity condition**. The comparable-severity condition is Shubh Bhagya's own (`matching._severity_comparable`), not scripture |",
     "| 20 | **Both partners are Manglik** of comparable severity | cancels for the marriage match | Classical compatibility rule |",
     "test_no_surface_calls_comparable_severity_classical"),
]
