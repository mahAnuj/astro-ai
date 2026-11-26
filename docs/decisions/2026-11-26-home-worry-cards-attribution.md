# The home-page worry cards attribute the opinions the site holds itself, and the lead names "the books we hold"

- **Date:** 2026-11-26
- **PR / issue:** #1501

## Why, measured

The "Don't fear your Kundali" section of `src/astro_ai/templates/index.html` opened with "what
the classical texts actually say about them" and then stated three things as if the texts said
them. astro-auditor's ruling (`knowledge/vedic_reference.md` sections 1.6.1, 2.7.1-2 and 3.4;
`knowledge/grahas.md` section 12.4) is that two of the three claims are in no held book and the
third misstates a disagreement.

**`data/` (the source books) was ABSENT on the runner that made this change.** Nothing was
re-read from the books. The sources below are the `knowledge/*.md` extracts, as cited by the
auditor; no corpus absence is claimed beyond what those files already record.

Occurrences on the rendered `/` (tags stripped, entities unescaped, whitespace collapsed,
lowercased), measured with the real route before and after:

| Phrase | Before | After |
|---|---|---|
| "what the classical texts actually say" | 1 | 0 |
| "most lives are better on the other side" | 1 | 0 |
| "actually aren" | 1 | 0 |
| "over-diagnosed" | 1 | 0 |
| "what the books we hold actually say about them" | 0 | 1 |
| "in our view" | 0 | 1 |

The decision: **an opinion the site holds itself is attributed to the site ("we read it", "in our
view"), and the lead names "the books we hold", not "the classical texts".** Each sentence and
what backs it:

- **Sade Sati:** "a transit, not a curse -- we read it as a course in maturity, and how hard it
  feels depends on your chart." The transit definition is `vedic_reference.md` section 2.7.1; that
  the natal position is the main thing is section 2.7.2. The maturity framing is the site's own
  approach (already said so on the Sade Sati article), so "we read it" attributes it. "Most lives
  are better on the other side of it" is in no held book and is gone.
- **Manglik:** "Sources disagree -- one lists cancellation rules, one rejects them -- but both say
  don't over-weight the dosha." `grahas.md` section 12.4 (Raman's antidote list, "much importance
  need not be given") against `vedic_reference.md` section 1.6.1 (Vasudev rejects the rules and
  calls excessive importance wrong). "A lot of people labelled Manglik actually aren't" is in no
  held book and is gone.
- **Kaal Sarp:** "Online checkers over-flag it, in our view -- a pattern to understand, not a
  sentence to fear." `vedic_reference.md` section 3.4: "over-diagnosed" is in **no** held book. It
  is the site's view, so the sentence says so. The card does not contradict Rao, who calls the
  yoga "highly problematic".

## Rejected

- **A softer verb on "the classical texts"** (for example "what the classical texts suggest"):
  the sentences still ride on a classical authority that two of the three claims do not have.
- **Deleting the cards:** the section is the home page's answer to hesitation and the Sade Sati
  and Manglik halves are sourced. Fix the claims, keep the cards.
- **Rewording the `/learn` pages in this change:** out of scope for a home-page issue.

## Out of scope, to be filed separately

The same claims are still stated on the learn pages and in the registry:
`learn/sade-sati.html` L7, `learn/manglik-dosh.html` L7, `learn/kaal-sarp-dosh.html`
L7, L20-21 and L133-136, and `learn_registry.py` L671 and L725-726. A follow-up issue carries
them.

## Not caught by a gate

`tests/test_home_worry_cards_attribution.py` is a phrase test: it catches only the wording it
names. A reworded unsourced claim on `/` would pass it.
