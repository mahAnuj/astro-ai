# The ten worry-topic /learn pages attribute the site's own opinions and stop asserting what no held book says

- **Date:** 2026-11-26
- **PR / issue:** #1509 (follows #1501, which did the same for the home-page cards)

## Why, measured

#1501 fixed the home-page worry cards and left the pages they link to. Those pages stated the same
families of sentence as fact: prevalence ("most online calculators ignore ...", "a lot of people
labelled Manglik actually aren't"), outcome ("most lives are better on the other side", delayed
marriage "usually after 28-30"), motive ("the industry preys on fear"), and attribution that no
held book gives ("K.N. Rao states it has no scriptural basis", "20th-century innovation").
`knowledge/vedic_reference.md` section 3.4 records that the held Rao (*Lessons on Vedic
Astrology*) teaches Kala Sarpa as a yoga and calls it "highly problematic", so the old Kaal Sarp
page also contradicted the book it leaned on.

**`data/` (the source books) was ABSENT on the runner that made this change. Books present: none.**
Nothing was re-read from the books. the astro-auditor ruled from `knowledge/vedic_reference.md`
sections 1.6.1, 1.6.3, 2.7, 3.2 and 3.4 and `knowledge/grahas.md` section 12.4, and from the page
text; this change applies that ruling claim by claim. No corpus absence is claimed beyond what those
files already record.

Matches of the families in `tests/test_learn_worry_claims_attribution.py` (rendered page with head
and scripts stripped, tags removed, entities unescaped, lowercased; plus every string field of the
learn_registry Article except `title` and `seo_title`), measured on the real routes before (main
383be9b) and after:

| Slug | Page before | Page after | Registry before | Registry after |
|---|---|---|---|---|
| sade-sati | 9 | 0 | 3 | 0 |
| manglik-dosh | 14 | 0 | 2 | 0 |
| kaal-sarp-dosh | 25 | 0 | 12 | 0 |
| manglik-remedies | 3 | 0 | 1 | 0 |
| marriage-delayed | 7 | 0 | 1 | 0 |
| kaal-sarp-dosh-remedies | 13 | 0 | 3 | 0 |
| pitru-dosh-remedies | 7 | 0 | 2 | 0 |
| ketu-remedies | 2 | 0 | 0 | 0 |
| planets-in-7th-house-marriage | 4 | 0 | 1 | 0 |
| career-during-sade-sati | 8 | 0 | 1 | 0 |
| saturn-remedies (registry only) | - | - | 2 | 0 |
| mars-remedies (registry only) | - | - | 1 | 0 |
| **Total** | **92** | **0** | **29** | **0** |

(The rendered count includes the registry summary where the page shows it, so the two columns
overlap.)

The decision: **an opinion the site holds itself is attributed to the site ("in our view", "our
reading"), a claim that only the web repeats is labelled "repeated online", and a claim in no held
book is removed or says "no book we hold".** The held evidence used, by page:

- **Kaal Sarp** (and its remedies page): Rao, *Lessons*, teaches it as a yoga, "highly problematic",
  usually working up to about age 40; while it is present "the other yogas may not function"; the
  reverse order is Kala Amrita, "saintly" (`vedic_reference.md` section 3.4). The K.N. Rao
  attribution is removed: K.N. Rao is not held, and the two Raos are easily conflated. BPHS, Brihat
  Jataka, Saravali, Phaladeepika and Jataka Parijata are not held, so the pages say "we cannot say
  whether they name it" instead of "they do not". "20th-century innovation" has no held source and
  is dropped. The page now declares that Shubh Bhagya counts either node order as the pattern,
  where Rao distinguishes them.
- **Manglik** (and marriage-delayed, planets-in-7th, manglik-remedies): the one dedicated antidote
  list held (Raman, *Muhurtha*, `grahas.md` section 12.4) has both partners Manglik, per-house sign
  exceptions, and Mars with Jupiter or the Moon (a conjunction), with "much importance need not be
  given". The Cancer/Leo Lagna rule, a Jupiter aspect and own-sign Mars are labelled "repeated
  online, not in the antidote list we hold". Raman ranks the dosha weakest from the Lagna, a little
  stronger from the Moon and strongest from Venus (section 1.6.3), so "from only one, the dosha is
  mild" is replaced; the low/moderate/high grades are named as the site's own. Vasudev (section
  1.6.1) names family quarrels, ego and argument with separation if malefics join, harm to the
  husband (8th) and bed-comfort friction (12th); delayed marriage is in none of them and is
  labelled "the usual online claim".
- **Sade Sati:** the one sourced softening is Rao's "hardly going to trouble the person" for a
  lagna lord or yogakaraka Saturn (section 2.7.2). Rao names no phases and ranks none (section
  2.7.3), so the "most intense phase" ordering and "people often look back" sentences are deleted;
  "course in maturity" is attributed to the site.
- **Pitru Dosh and Ketu:** no held book defines Pitru Dosh or links Pitru Paksha to Ketu; the
  pages say so and call the chart signatures practice. The outcome timelines ("year 1-2 ... closure")
  are deleted. Price ranges, where a rule needed none, are deleted too: no held source gives a fair
  price.

Beyond the auditor's list, the same families were removed wherever the gate found them (for
example `career-during-sade-sati` prevalence sentences and the exploitation callouts on the two
remedies pages), by the same rule: attribute to the site, label as practice, or delete.

## Rejected

- **A three-page PR with sub-issues for the rest:** the issue names all ten and the size gate does
  not bind. One engineer, one commit per page.
- **A runtime sanitiser or a claims-metadata table:** static copy, rollback is a revert.
- **Rewording `<title>` or `seo_title`:** untouched everywhere (#311 scored a title change on the
  Manglik page a MISS). The Manglik `seo_description` ("calculators ignore") and the Sade Sati
  "most-feared ... most misunderstood" line are also left, as the auditor rated them low risk.
- **A rendered-page-only scan:** the registry feeds the FAQ JSON-LD, the cards and the LLM summary,
  so the gate reads both.

## Out of scope, to be filed separately

- `i18n.py` `ksy_caveat_body_*` (EN and HI), shown on `/kaal-sarp-check`, and
  `knowledge/vedic_reference.md` section 3.2 (a trust-boundary file) carry the same "20th-century
  innovation" and "no scriptural basis" claim. `tests/test_kaal_sarp_unsourced_quotes.py` still
  pins the i18n copy, so the `/kaal-sarp-check` caveat and the article now disagree until that
  follow-up lands.
- Claims the auditor could not rule on (the Rahu and Ketu "traditional friends", a Manglik
  prevalence figure, any Pitru Dosh concept) are left as they were.

## Not caught by a gate

`tests/test_learn_worry_claims_attribution.py` is a phrase test: it catches the families it names,
not every rewording, and the ten pages carry other unsourced practice prose that is labelled as
practice. `qa` and `astro-auditor` read the rest.
