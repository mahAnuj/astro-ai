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
overlap.) These are **phrase-test match counts, not a read of the pages**: "92 to 0" says the named
families no longer match, not that every unsourced sentence is gone; `qa` and the auditor read the
rest. The table was measured with the families as first written. A QA round then found outcome and
prevalence sentences those families missed, and added `almost always`, `rarely`, `lots of people`,
`better careers`, `most simple calculators`, `nobody mentions` and `many charts that look like`; the
"after" column is 0 for them too, and their "before" counts were not measured.

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

## Addendum 2026-11-26 (#1513): round 2, the pages #1511's QA round found

Same rule (attribute to the site, label as practice, or delete); no new astrological claim. Four
templates (`rahu-remedies`, `mars-remedies`, `kundali-matching-ashtakoot-guna-milan`,
`shani-saturn`) and six registry spots (the `shani-saturn` FAQ, the Venus-in-8th FAQ under
`second-marriage-yoga-kundli`, and the Rahu, Pitru and Kaal Sarp remedies summaries). The Mars price
sentence names the one antidote list we hold (Raman, *Muhurtha*, `grahas.md` section 12.4: both
partners Manglik, sign exceptions, Mars with Jupiter or the Moon) and says Hanuman Chalisa is
practice. `grahas.md` holds no "Saturn as teacher" claim, so that stays only as the site's reading.

Phrase-match counts (`exploiting|exploited|preys? on|over-?diagnos|fear is misplaced|life-defining|
exploitation happens|\bscam|₹5-25K|₹50K`, case-insensitive; a phrase count, not a read of the pages):

| file | before | after |
| --- | --- | --- |
| `rahu-remedies.html` | 4 | 0 |
| `mars-remedies.html` | 1 | 0 |
| `kundali-matching-ashtakoot-guna-milan.html` | 1 | 0 |
| `shani-saturn.html` | 2 | 0 |
| `learn_registry.py` | 15 | 4 |

The four registry matches left are outside this issue: line ~1642 ("Foreign-yoga scams"), ~1914
("life-defining opportunity", a figure of speech, not a claim) and the two "heavily exploited" bullets
at ~2038 and ~2174 (see the follow-up below).

The gate gives the round-2 pages only the #1513 families (`_BANNED_R2`), not the broad #1509 list:
that list trips on sentences this issue does not name ("most people" in the Rahu and Shani prose,
"K.N. Rao lineage" in the astrologer-choosing advice on kundali-matching). Widening the diff to
rewrite those was out of scope.

Beyond the plan's list, the Kaal Sarp remedies `llm_summary` also lost its "scamming" cost line and
the "₹5-25K" Nagbali price, because the new `\bscam` and price patterns match them and they are the
same family.

### Out of scope, to be filed separately

The "selling anxiety / tens of thousands" family on about ten more surfaces: templates
`venus-remedies`, `mercury-remedies`, `jupiter-remedies`, `santan-prapti`, `10th-lord-in-6th`; registry
lines near 1022, 1203, 1250, 1975, 2038, 2079 and 2174 (grep before editing; the numbers move).
**Done in #1525, see the addendum below.** Checked there: `10th-lord-in-6th` has no "selling anxiety"
line, but it did carry "exploiting the placement's discomfort", which the same family names.

## Addendum 2026-11-26 (#1525): the price-and-motive family

Same three-way rule (attribute to the site, label as practice, or delete); no new astrological claim.
The family is a remedy **price band** ("tens of thousands", "under ₹500", "₹5-15K", "costs almost
nothing"), a **motive** stated as fact ("selling anxiety", "exploiting fear", "trading on fear",
"exploitative", "heavily exploited") and a **prevalence** claim about vendors ("the vendor manipulation
that dominates online content", "the vendor-scam version is rampant"). Thirteen templates
(`financial-struggles`, `marriage-delayed`, `mercury-remedies`, `venus-remedies`, `jupiter-remedies`,
`saturn-remedies`, `pitru-dosh`, `rahu-mahadasha-career-problems`, `10th-lord-in-6th-house-career`,
`saturn-in-10th-house-career`, `chronic-health-issues-kundli`, `santan-prapti-children-in-kundli`,
`pitru-dosh-remedies`) and seven registry entries (`jupiter-remedies`, `saturn-remedies`,
`marriage-delayed`, `santan-prapti-children-in-kundli`, `chronic-health-issues-kundli`, `pitru-dosh`,
`pitru-dosh-remedies`). Each puja-package bullet now says what the live #1513 pages say: *be cautious of
a very large quote for "<X>": we hold no source for what a fair price is, so ask what it covers*. The
positive content of the bullet (mantras, Vishnu worship, a havan) stays, labelled practice where it
had been called "genuine".

Safety lines were kept, not traded away with the claim: skip no medical care (`chronic-health`,
`santan-prapti`, and the registry never-replace-medical-care line), consult a chart before blue
sapphire (`saturn-remedies`), before hessonite (`rahu-mahadasha`), before gemstones at all (the
`marriage-delayed` FAQ). The test pins each, so a rewrite that deletes the caution instead of the claim
goes red.

**Evidence base: `data/` was ABSENT on the build runner; books present: none.** Nothing here asserts
absence from a book. The pages say "we hold no source", the same wording #1513 used, and the one
sentence this change cannot source either way (whether Rao, *Lessons*, ch. 34 says anything about cost)
is not claimed.

### Corrections to the issue

- `knowledge/vedic_reference.md` section 3.4 is the Kala Sarpa entry (Rao, *Lessons*), not a record
  that "no held book prices a remedy". The nearest held statements are section 3.3 ("we hold no source
  for the removal pujas sold around Kaal Sarp"), the site's own #1513 wording and `remedies.md` 1.2 /
  1.4 (what is held: Rao on belief, and on gemstones).
- 13 templates, not 12: the issue's count missed `10th-lord-in-6th-house-career` ("exploiting the
  placement's discomfort") and `pitru-dosh-remedies`, whose page said "every remedy below can be done
  for under ₹500" beside the FAQ the issue did name; changing the FAQ alone would have left the page
  and its own FAQ JSON-LD disagreeing. The registry also had a price band the issue missed (the
  `pitru-dosh-remedies` FAQ and `llm_summary`: "under ₹500 ... ₹5-15K"; #1509's gate missed it because
  `5-15K` is not `5-25K`).
- **A quotation that was not Rao's.** The `saturn-remedies` FAQ said *The classical framing from Rao:
  'Remedies are devotional acts, not transactional payments.'* `remedies.md` 1.2 holds no such quote;
  the sentence is this repo's own. It now reads "In our reading, remedies are devotional acts, ...".
  Rao's held words there are "Those who have no belief in Vedic remedies may skip this chapter", which
  the page keeps. The same FAQ's "often makes the underlying pattern worse" is `remedies.md` 1.2's own
  gloss, not a Rao quote, and is cut.
- "Almost never" opened four FAQ answers (Jupiter, Saturn, marriage and santan-prapti); it is an
  outcome and prevalence claim of the `almost always` / `rarely` family #1509 removed, so those
  answers now open with the caution.

### Phrase-match counts, before and after

Counted with the gate's own patterns (`_BANNED_R3` on the registry, `_BANNED_R3` plus `_BANNED_R3_PAGE`
on the rendered page body; a phrase count, not a read of the pages). "Before" is main at `f57cde5`.

| surface | before | after |
| --- | --- | --- |
| 13 rendered pages (sum) | 56 | 0 |
| 7 registry entries (sum; `summary`, `llm_summary`, `faqs`) | 27 | 0 |
| issue repro `grep -rciE "selling anxiety\|tens of thousands\|exploiting fear"` over `templates/learn` + `learn_registry.py` | 11 templates + the registry (5 lines) | empty |
| wider `selling anxiety\|tens of thousands\|exploiting fear\|heavily exploited\|exploitative\|trading on\|exploiting the\|emotional urgency\|not a classical astrologer\|misrepresenting\|rampant` over `templates` + `learn_registry.py` | 12 templates + the registry (8 lines) | empty |

The gate adds a separate tuple (`_BANNED_R3`), not an addition to `_BANNED`: `_BANNED_R2` is sliced off
the end of `_BANNED` (`_BANNED[-7:]`), so appending there would silently change which patterns round 2
pins, and would run the broad "most people" and "K.N. Rao" families over pages this issue does not
name. A one-line assert on `len(_BANNED_R2)` makes that edit loud.

### The unresolved conflict with `knowledge/remedies.md` 1.3

`remedies.md` 1.3 states a price band ("tens of thousands") and a motive ("selling anxiety, not
tradition") as a rule, and says every remedy article "must explicitly warn". It cites no passage of
Rao (1.2 quotes him on belief, 1.4 on gemstones, 1.3 quotes nothing), so it is the site's own
editorial written into a knowledge file. It is **not edited here**: it is a trust-boundary file, it is
not shown to readers, and the diff stays reviewable. Confirmed it cannot reintroduce the claim:
`knowledge_lookup.py` reads only `remedies.md` 5.1 and 7.1 (`_read_remedies`), and its one caller is
`llm.py` (about line 293); no route or prompt file loads 1.3. The articles still *warn*, in the live
wording, which satisfies "must warn" without asserting a price or a motive as fact. An auditor reading
1.3 may nonetheless flag the pages as missing the warning it describes; this paragraph is the answer.

**Follow-up to file:** reword `knowledge/remedies.md` 1.3 to a caution, then check
`scripts/verify_natal_prompt.py` / `scripts/mutate_natal_prompt_gate.py` fixtures if they quote it
(both use "selling anxiety" only as a seeded bad string and a comment, so neither needs the live copy to
contain it). Related: `prompts/natal.txt` line 68 ("never suggest paying a large sum for a puja") is an
instruction to the model, not a reader-facing assertion; left as is, since prompts are a trust boundary.

### Out of scope here

- `seo_description` and `<title>` / `seo_title` are untouched (#311 scored a title change a miss;
  description risk is unmeasured). Still saying "without vendor manipulation": the `seo_description` of
  `jupiter-remedies`, `mercury-remedies`, `venus-remedies`, `mars-remedies` and `saturn-remedies`; the
  `pitru-dosh-remedies` `seo_description` still says "every remedy under ₹500". The gate skips
  `seo_description` for these seven entries for that reason.
- The same family on surfaces the issue did not name and this change did not touch:
  `mars-remedies` (intro, and the registry `summary`, "without the vendor manipulation that dominates
  online content"), `career-during-sade-sati` (page and registry FAQ: "the vendor manipulation around
  Sade Sati is enormous", "A ₹50,000 puja"), `foreign-career-yoga-kundli` ("one of the most heavily
  scammed areas"). Not gated; file them. (`career-during-sade-sati` and `foreign-career-yoga-kundli`
  were done in #1528, below; `mars-remedies` is still open.)
- The `rahu-remedies` and `mars-remedies` "Do not overpay for ..." headings stay on purpose: neutral
  caution, already live from #1513. `saturn-remedies` registry "at no cost" (a lone, mild price claim)
  and the other "most people" prose #1523 named are also left.
- `tests/test_learn_worry_claims_attribution.py` is a phrase test. It catches what it names; `qa` and
  `astro-auditor` read the rest.

## Addendum 2026-11-27 (#1528): the price-and-motive family, round 4

The QA round on PR #1526 found the same family on four pages #1525 did not name. Same three-way rule
(attribute to the site, label as practice, or delete); no new astrological claim. Pattern wording is
#1526's: *be cautious of a very large quote for "<X>": we hold no source for what a fair price is, so
ask what it covers.* The page and its registry FAQ were changed together, because the registry feeds
the FAQPage JSON-LD.

Families: a rupee **price band** ("A ₹50,000 puja", "₹2,000-10,000", "₹500-2000", "₹2K-10K",
"₹500-2K"), a **vendor motive and prevalence** claim ("the vendor manipulation around Sade Sati is
enormous", "one of the most heavily scammed areas", "scams are common"), a **price claim about a stone**
("always overpriced", "inflated prices") and a **provider-quality** label ("from legitimate priests").
Four slugs: `career-during-sade-sati` (page and FAQ), `foreign-career-yoga-kundli` (page and FAQ),
`manglik-remedies` (page, FAQ), `kaal-sarp-dosh-remedies` (page, `llm_summary`). Safety lines are kept
and pinned: blue sapphire "never without proper chart consultation ... walk away" (career page and FAQ),
and the foreign page's "anyone who guarantees visa approval" and "MUST wear a specific gemstone" cautions.
The foreign page now also says we hold no source that a puja or a gemstone is required to activate the
yoga; the old "Classical Vedic tradition does not support any of these claims" asserted what no held
book was checked for. `title`, `seo_title` and `seo_description` are untouched.

**Evidence base: `data/` was ABSENT on the build runner; books present: none.** No corpus-absence
claim is made; the pages say "we hold no source".

### Corrections to the issue

- `knowledge/vedic_reference.md` section 3.4 is the Kala Sarpa entry, not a record that no held book
  prices a remedy (the same correction #1526 recorded above). The nearest held statement is section 3.3.
- The issue's `₹500-2K` (registry about line 2991) is on `kaal-sarp-dosh-remedies`, not
  `manglik-remedies`; the issue's list put it under the wrong slug.
- A fourth page: `kaal-sarp-dosh-remedies` also said "Cost: ₹500-2000 for the silver pair" and "mostly
  inexpensive". The issue's repro grep misses it, because `₹500-2000` is not `₹500-2K`. It also said
  "we give no figure" at line 23 and gave one at line 65, so the page contradicted itself.
- `grep -rnE "₹ ?[0-9]" src/astro_ai/templates/learn`: 3 lines before (career, kaal-sarp, manglik), not
  4; 0 after. The foreign page's price claim has no rupee sign ("always overpriced").

### Phrase-match counts, before and after

Counted with the gate's own patterns (`_BANNED_R3` plus `_BANNED_R4` on the registry fields `summary`,
`llm_summary` and `faqs`; plus `_BANNED_R3_PAGE` on the rendered page body). "Before" is main at
`7b0ee2f`.

| surface | before | after |
| --- | --- | --- |
| 4 rendered pages (sum of patterns that fire) | 14 | 0 |
| 4 registry entries (sum) | 6 | 0 |
| issue repro grep (5 phrases) over `templates/learn` + `learn_registry.py` | 6 lines | 0 |
| `grep -rnE "₹ ?[0-9]" templates/learn` | 3 lines | 0 |
| `grep -n "₹" learn_registry.py` | 3 lines | 1 (deferred, below) |

The gate is a separate tuple (`_BANNED_R4`), again not appended to `_BANNED` (`_BANNED_R2` slices its end).
Bare `expensive` is not banned: the kept cautions ("a very large quote", "costly Kaal Sarp offers") are not
claims about a price.

### Left alone on purpose

- `pitru-dosh-remedies` registry `seo_description` ("Every remedy under ₹500"), and the
  `seo_description` of `kaal-sarp-dosh-remedies`: search snippets are deferred (#311). The registry scan
  skips `seo_description`, so the one remaining `₹` in `learn_registry.py` is the `pitru-dosh-remedies` line.
- `kaal-sarp-dosh-remedies` line 7, "expensive remedy offer ... be cautious": a caution, kept in #1526.
- `mars-remedies`: the leftovers named under #1525 are still open.
