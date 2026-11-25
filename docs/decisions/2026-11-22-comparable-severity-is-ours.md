# Comparable-severity Manglik cancellation is called Shubh Bhagya's own convention on every surface, and a gate keeps it so

- **Date:** 2026-11-22
- **PR / issue:** #1369 (related: #1321, #1368, #429)

## Why, measured

Six /learn pages, the FAQPage JSON-LD built from `learn_registry.py`, the matching notes, the natal
LLM instruction (`chart.py`) and `vedic_reference.md` rule 20 said that classical texts "require"
Manglik-with-Manglik partners to be of comparable severity ("the classical requirement", "ONLY
when ... comparable severity", "the qualifier is the whole rule").

`astro-auditor` ruled on the held corpus. Raman's antidote list (`knowledge/grahas.md` section 12.4,
book line 3642) cancels the dosha when both partners are Manglik and **names no severity
condition**. No held book states a comparable-severity condition, so the claim is **unsourced as
classical**. `data/` is absent from the working tree here, so the finding is "not found in a held
book", not "not classical": the surfaces now say exactly that ("we have not found that condition in a
book we hold") and never the stronger claim.

## Decision

- Copy and engine voice attribute the unconditional rule to one held antidote list and call the
  comparable-severity band **Shubh Bhagya's own convention**, not scripture (commits 5be850f,
  bab20db, 3a0336f).
- **Behaviour is unchanged.** `_severity_comparable`, `_BRANCH_COMPATIBLE` and the badges are
  untouched: a low-versus-high Manglik pair still does not cancel in the matching tool. Whether such a
  pair should cancel at all is an owner product call (`CLAUDE.md`, the `chief` hand-back table, row 4:
  which school a reading follows). It is raised, not decided, here.
- `tests/test_comparable_severity_not_classical.py` is the gate: a sentence-level scan of the
  **sources** (string constants in `learn_registry.py`, `matching.py`, `chart.py`; every template;
  `vedic_reference.md` per line), so the JSON-LD is covered without a request. HARD phrases ("texts
  require", "the classical requirement", "ONLY when" ...) fail even beside a disclosure; SOFT words
  ("classical", "the tradition", "the texts") fail unless the same sentence says it is ours or that the
  list names no severity condition. Positive pins: the manglik-dosh page says the list "names no
  severity condition", and both both-Manglik notes from `mangal_dosh_verdict` say "no severity
  condition". **It is a phrase test**: it catches the wording it names, not every rewording.
  Calibrated on the wording before the fix (7b29d1a): it flags the old `matching.py`,
  `learn_registry.py`, `chart.py`, `manglik-dosh.html`, `result.html` and `vedic_reference.md`, and
  passes the current tree with no sentence tripping it.
- Nine rows (seven from the first rounds, two from QA round 2) in `scripts/mutations/2026_11_22_1369_comparable_not_classical.py` restore the old
  sentences; the five #429 learn-page rows whose anchors the rewording replaced were re-pointed, not
  removed.

## Consequences

- A future page, FAQ or prompt line that calls the band classical in the named phrasings goes red.
  One that states it in a new way does not; the positive pins and review carry that half.
- Known blind spot of the sentence split: it splits on `.`, `;`, `!`, `?`, bullets and newlines but
  deliberately **not** on `:` (a colon once separated "classical" from "comparable" and let a claim
  through), so a claim carried across a semicolon from the sentence holding "comparable" is not
  joined to it.
- **QA round 2 (head 4407c6d):** two sentences gave the cancellation a mechanism and a matchmaker
  preference ("meets itself", "the evenness of the match does the neutralising", "traditional
  matchmakers prefer") that no held book states, on `manglik-dosh` and `manglik-remedies`. They never
  say "comparable", so the trigger never fired. Both were cut, and
  `test_no_surface_invents_a_mechanism_for_mutual_manglik_cancellation` scans every surface for that
  phrase family with no trigger (two more mutation rows). "Many retellings add ..." is kept: it names
  where the idea comes from without claiming it, but it is itself not traced to a held book. Raised on
  #1376 with `matching.html:201`.
- **Token cost** (tiktoken `o200k_base`): `_COMPARABILITY_BAND_SENTENCE` 41 to 43 (+2); the natal
  instruction sentence in `chart.py` 64 to 68 (+4); a whole both-Manglik note 154 to 160 (+6,
  comparable) and 170 to 175 (+5, incomparable). The matching note reaches the model once per
  both-Manglik pair, the natal line once per Manglik chart. Negligible against the 8,000 TPM per-model
  ceiling; no model or chain change.

## Supersedes

The "comparable" framing in the `ARCHITECTURE.md` section 10 row dated 2026-11-07 (#429), which
described the cancellation as one of comparable severity. That row is not edited: section 10 is frozen
after 2026-11-09 and an old row is never rewritten to say something it did not say then.
