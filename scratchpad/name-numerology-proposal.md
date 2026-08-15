# Name numerology in the product — a design note

**Status:** proposal only. Nothing here is built. No route, template or `numerology.py`
change was made in producing it.
**Source for every astrological claim below:** `knowledge/numerology.md` §14 (Cheiro,
*Book of Numbers*), added in the same commit. Section references are to that file.
**Scope:** what a fuller treatment of the Name Number should look like, with reasoning,
rough effort, and the one thing I recommend we do *not* do.

---

## 1. Where we are today

`/numerology` takes **"Full name (as commonly used)"** + birth date + a Chaldean/Pythagorean
toggle, and returns Life Path, Birthday, Expression, Heart Desire, Personality, Name Number,
Name Compound, a Lo Shu grid, Karmic Debt flags and a Bhagya score. There is a compatibility
sub-route at `/numerology/compatibility`.

Two things about the current name treatment matter for anything we do next.

**First, the name is already the largest input and the smallest output.** Four of the seven
headline numbers (Expression, Heart Desire, Personality, Name Number) derive from the name,
plus the Name Compound. But they are rendered as five sibling cards in one flat grid
alongside the birth-date numbers. Nothing tells the user that these five are *one thing seen
five ways*, and nothing tells them the name they typed is the variable they control.

**Second, there is a hard existing policy against name-change advice**, stated twice:

- `numerology.py` module docstring: *"Never recommend name changes based on numerology"*,
  under an Editorial heading, alongside *"no lucky-name upsell"*.
- `numerology.html` footer: *"This calculator does not recommend name changes or wearing
  gems based on numerology alone — both practices can carry unintended consequences."*

This is the crux of the whole design problem, because **Cheiro's name apparatus culminates
in name correction.** §14.2's central mechanic is adding a middle initial so the Name number
accords with the Birth number. If we import Cheiro's name material wholesale we walk
straight into a policy the repo set deliberately.

I think the policy is right and should stay. The rest of this note is about how to get most
of Cheiro's value without crossing it.

---

## 2. The headline recommendation

> **Build a "Your Name" section inside the existing `/numerology` reading — a grouped,
> explanatory block that treats the name as one subject with several facets, adds Cheiro's
> most-used-name rule, the word-by-word breakdown, and the Name↔Birth accord verdict.
> Ship one `/learn` article to carry the search demand. Do not build a name-correction
> tool, and do not build a separate name page.**

Reasoning in §3–§6. Effort in §7.

---

## 3. Why a richer in-reading section rather than a dedicated page

**`/learn` currently contains zero numerology articles.** I listed all 75; every one is
Vedic — nakshatras, doshas, dashas, yogas, muhurats, remedies. So the CLAUDE.md prohibition
("do not create a parallel page type for queries `/learn` already serves") does *not* bite
here in the way it bites for festivals: there is no numerology page to cannibalise. But the
rule's *intent* still governs the choice of vehicle — when we do want long-form numerology
content, it belongs in `/learn`, not in a third page type invented for it.

That splits the work cleanly:

| Need | Right vehicle | Why |
|---|---|---|
| Explain the name apparatus to someone already holding their reading | **Section inside `/numerology` result** | Contextual, personalised, needs their numbers |
| Rank for "name numerology calculator", "chaldean name number", "lucky name number" | **One `/learn` article** | Established pattern, already ranks, no new page type |
| Let someone try a different name | **Already exists** — the template has a "Try another name →" link | Zero build |

A dedicated `/numerology/name` route would be the worst of the three: it splits the
name-derived numbers away from the birth-date numbers whose *accord with them* is the entire
point (§14.2), it competes with `/numerology` for the same queries, and it creates a fourth
page type.

---

## 4. What the section should contain

Ordered by value-per-unit-effort. Everything below is sourced; nothing requires an LLM call,
consistent with the module's "pure math + fixed interpretation strings" design.

### 4.1 The accord verdict — the single highest-value addition

Cheiro's whole framework reduces to one question we can already answer with data we already
compute: **does the Name number accord with the Birth number?** (§14.2, Ch. XIV `-layout`
3829–3832.)

Three states, each with sourced copy:

- **In accord** — the strongest result, and Cheiro adds a second reason to like it that is
  genuinely useful to a user: agreement is *evidence you picked the right name to score*
  ("then one can be absolutely certain that no mistake is being made", §14.2, `-layout`
  4067–4079).
- **Not in accord** — describe the symptom Cheiro describes, which is notably mild and
  non-catastrophising: *"there would always be a muddle or jumble in his affairs, and he
  would also not be able to decide which number to act on"* (`-layout` 3862–3868). No doom.
- **Both are 4 or 8, or one of each** — the §14.8 case, which is the only place Cheiro
  raises his voice.

This is a small amount of code — both numbers are already on `NumerologyReading` — and it
converts five inert cards into a reading.

### 4.2 The "which name did you type?" prompt

Cheiro's rule is that the name to score is **the one you are most known by**, not the legal
one, and he is unusually candid that this is the weak link: *"the Name number is more
difficult to be sure of… mistakes may easily be made and a number allotted which is not the
true one"* (§14.2, `-layout` 4053–4066).

The form label already says "as commonly used", which is correct and better than most
competitors. What is missing is the *consequence*. A short block after the result should
say: if people mostly call you by a nickname, a surname alone, or a title + surname, that is
the name this reading is about — and offer the re-run link that already exists.

Cheiro's trade-name/private-name split (§14.2) is the most interesting idea here and I would
surface it as explanatory copy rather than as a second calculation: a person can hold two
name numbers, one for professional life and one for private life, and they are supposed to
differ. That reframes "which name do I enter?" from a data-entry anxiety into a feature.

### 4.3 Word-by-word breakdown

Cheiro never sums a name in one pass. Each word gets its own single and compound number, and
those are read individually before being combined (§14.2 — Lloyd 18/9 + George 25/7 → 16;
Ramsay 12/3 + MacDonald 32/5 → 44). We currently show only the whole-name totals.

Rendering per-word values is arithmetically trivial (the letter table is already there) and
it does three things at once: it shows the user *how* the number was derived, which is a
trust move; it makes the Chaldean/Pythagorean toggle legible instead of magic; and it
unlocks the one genuinely actionable, policy-safe piece of advice in Cheiro — see §5.

### 4.4 Give the Name Compound its due

The compound card exists but sits at the bottom under a wall of caveats. §14.3 supplies the
framing it is missing: the compound is a *different plane*, not a finer-grained single; it
is read *alongside* its root, never instead of it; the symbols are pictorial because they
are Tarot-adjacent, which is why they read as images rather than adjectives; and the series
stops at 52 for the weeks of the year. The template already says several of these things —
it needs the "distinct from the number 3" point (`-layout` 3447–3452) and it needs to be
higher up.

### 4.5 Explicitly out of scope for the name section

- **Lucky-day calculation** (§14.4). It is a clean algorithm and tempting. But Cheiro
  himself limits it — it "would not work out with such certainty" once another person is
  involved (`-layout` 5428–5446) — and it would need a date picker, a results calendar and a
  caveat longer than the answer. If we ever build it, it is its own feature, not part of the
  name section.
- **Per-number colours/stones/days** (§14.6). The module docstring forbids the
  "wear this gem for your number" pitch and the footer repeats it. §14.6 is recorded in the
  corpus as reference and for `/learn` prose; it should not become a product panel.
- **Place and house numbers** (§14.9). Real, sourced, and a different feature.

---

## 5. Name correction — the hard call, and what I recommend instead

Cheiro's remedy is specific: add an initial worth the right value, and *insist on being
called by it* (§14.2). It is not a legal name change; it is a change of what people call
you. He also states the exceptions — if the name already accords, leave it alone even when
the shared number is unlucky (accord outranks favourability), and if you are a 4-or-8 case,
move away from both.

**I recommend we do not ship a name-correction tool.** Reasons, in order of weight:

1. **It is the existing policy, stated twice and in two files.** Reversing it is a product
   decision for the user, not something a knowledge-mining pass should smuggle in.
2. **It is the classic numerology upsell**, and the module docstring names it as such
   ("no lucky-name upsell"). A "suggest an initial that fixes your number" widget is exactly
   the mechanic that monetised numerology sites use.
3. **It is unfalsifiable and behaviourally demanding.** Cheiro's own success condition is
   that the person gets everyone around them to adopt the new name, over months (§14.10:
   he cites a correspondent who saw change "towards the middle of the third month"). We
   would be asking users to restructure their social identity on the strength of a page.
4. **Our own §14 records that Cheiro contradicts himself on the target numbers** — Ch. XIV
   says change toward 1/3/6/9, Ch. XV says 1/3/5/6, both verified on page images (§14.8).
   We would have to pick, and the picking would be ours, not the source's.

**What I recommend instead, and it captures most of the value:** the word-by-word breakdown
from §4.3 makes visible which *part* of a name carries which number. That supports Cheiro's
own best advice, which is not "change your name" but **"change which part of your name
people use"** — his read on Lloyd George ("if he had become known as plain George he would
have retained the position he gained") and on Ramsay MacDonald ("he should have insisted on
being called MacDonald, with its magical number of 32"), both at §14.2.

That is descriptive, not prescriptive; it costs the user nothing; it does not touch their
legal identity; and it is closer to what the source actually demonstrates. If we ever want
to go further, it is the natural next increment and it can be user-approved then.

---

## 6. Voice and framing constraints

- **Do not merge Cheiro with Johari.** §14.6, §14.7 and §10 record three live disagreements:
  gems and colours per number, group vs pairwise compatibility, and 4/7 vs 4/8 as the
  numbers to avoid. `numerology.html` already handles this well ("These are separate systems,
  not two views of the same underlying method"). Any new copy must hold that line.
- **CLAUDE.md's cite-the-tradition rule applies to user-facing prose.** The page already
  names Cheiro by name in the origin note, which is correct — he is the provenance of the
  letter table, not an astrological authority being quoted for a claim. New prose should
  keep naming the *tradition* ("in the compound-number tradition…") and reserve the personal
  name for provenance statements.
- **Inherit Cheiro's own honesty.** §14.10 collects it: expect months not days, say when a
  rule is weaker, say when a number is hard to be sure of, and debunk rather than exploit
  (his chapter arguing 13 is not unlucky). This is unusually good raw material for copy that
  is both sourced and non-predatory, and it aligns with §12's guardrails.

---

## 7. Rough effort

Rough, and deliberately so — these are sizings to prioritise against, not estimates to
commit to. No dependency on anything outside `numerology.py`, the `/numerology` template,
and one new `/learn` file.

| Item | Files | Effort | Notes |
|---|---|---|---|
| 4.1 Accord verdict | `numerology.py` (one derived field + 3–4 strings), `numerology.html` | **S** | Both inputs already computed. Highest value in the set |
| 4.2 "Which name" explainer | `numerology.html` only | **XS** | Pure copy; re-run link already exists |
| 4.4 Compound reframing | `numerology.html` only | **XS** | Reorder + two sentences from §14.3 |
| 4.3 Word-by-word breakdown | `numerology.py` (per-word helper), `numerology.html` | **M** | Needs a small table UI; must respect the Chaldean/Pythagorean toggle, and note that `name_compound` is Chaldean-only by design |
| Regroup the five name cards under one heading | `numerology.html` | **S** | Layout change to the existing grid |
| `/learn` article on name numerology | one new template + hub entry | **M** | Follow the established `/learn` pattern; read two existing articles first per CLAUDE.md |
| Name correction tool | — | **not recommended** | §5 |
| Lucky-day feature | — | **deferred** | §4.5; own feature if ever |

A sensible first slice is **4.1 + 4.2 + 4.4 + the regroup** — all template-and-strings work
with one small computed field, no new UI primitives, and it delivers the framing change that
makes the rest optional rather than necessary.

---

## 8. Open questions for the user

1. **Is the "never recommend name changes" policy load-bearing, or was it a default?** §5
   assumes load-bearing. If it was a default, the §4.3 breakdown is still the right first
   step, but the roadmap after it changes.
2. **Do we want numerology in `/learn` at all?** It would be the first non-Vedic content
   there. The SEO case is good and there is no cannibalisation risk, but it is a positioning
   decision above my pay grade.
3. **Should the trade-name / private-name split (§14.2) ever become two calculations rather
   than copy?** It is the most distinctive idea in Cheiro's name material and no competitor
   I am aware of surfaces it. It is also a second form field and a second result set.
