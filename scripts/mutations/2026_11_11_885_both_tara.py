"""#885 (chief, Option A): the Vivah couple verdict's "avoid only when BOTH partners are on an avoid
Tara" rule is unsourced either way, so the grades stay and the finder says it is its own convention
(no book gives a combining rule). These rows re-break the two halves: the verdict moving, and the
disclosure going missing or claiming a source."""

_BOTH = '    both_tara_avoid = (bride.tara_bala == "avoid" and g_tara == "avoid")\n'
_OWN = "is this finder's own convention, not a rule from a book"
_NO_RULE = "without saying how a bride's and a groom's days combine"

MUTATIONS = [
    ("#885: one partner's avoid Tara makes the couple day avoid (the unsourced 'either' reading ships)",
     "src/astro_ai/muhurat.py",
     _BOTH,
     '    both_tara_avoid = (bride.tara_bala == "avoid" or g_tara == "avoid")\n',
     "test_one_partner_on_an_avoid_tara_is_still_mixed_not_avoid"),
    ("#885: both partners on an avoid Tara stop being avoid",
     "src/astro_ai/muhurat.py",
     _BOTH,
     '    both_tara_avoid = False\n',
     "test_both_partners_on_an_avoid_tara_is_avoid"),
    ("#885: the finder stops saying the 'both' rule is its own convention",
     "src/astro_ai/templates/muhurat_finder.html",
     _OWN,
     "is the rule of the classical texts",
     "test_the_finder_says_the_both_rule_is_its_own_convention"),
    ("#885: the finder drops that Raman gives no combining rule",
     "src/astro_ai/templates/muhurat_finder.html",
     _NO_RULE,
     "and says both partners must avoid",
     "test_the_finder_says_the_both_rule_is_its_own_convention"),
    ("#885: the finder claims a source for the 'both' rule",
     "src/astro_ai/templates/muhurat_finder.html",
     "not a rule from a book:",
     "not a rule from a book, though the classical texts say both:",
     "test_the_note_claims_no_source_for_the_both_rule"),
]
