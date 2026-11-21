# Muhurat finder rows say why a date rated as it did, from a registry that marks every factor sourced, contested or site convention

- **Date:** 2026-11-21
- **PR / issue:** #1017 (R3; refs, does not close). Related: #1342 (top pick, open at the time), #1346 (Abujha precedence, a rule change, not touched here)

## Why, measured

Each auspicious row of `POST /muhurat` now carries a collapsed "Why this date" list: what
counted (tithi, star, weekday, peak day, boosters, a deducted weekday) and what was checked and
not excluded at local noon. One legend below the table states each factor's sentence once.
Every item carries one of three statuses, so no factor reaches the page unlabelled:
`sourced` (a held book states it; a knowledge file and heading name it), `contested` (the held
books differ, shown as "traditions differ"), `site_convention` (this finder's own rule, shown
as "site convention"). No scoring rule changed: `muhurat.py` and `routes/muhurat.py` have zero
edits.

**Where it lives: `src/astro_ai/muhurat_factors.py`, not "a dict in muhurat.py".** The issue
text says a dict in `muhurat.py`. Rejected for four reasons: PR #1342 edits the same regions
(`_soft_scoring`, `rank_key`, the finder template), so a registry there conflicts by
construction; `muhurat.py` is about 1,966 lines and concurrently edited;
`scripts/verify_rule_citations.py` check 7 scans `muhurat.py` WHOLE FILE for unheld book names,
and a registry full of source strings would sit inside that scan; and a registry is data plus
a renderer, a separate concern from scoring. Two Jinja globals in `routes/deps.py`
(`muhurat_why`, `muhurat_why_legend`, lazy imports, following `muhurat_auspicious_ratings`)
and two partials (`_muhurat_why.html`, `_muhurat_why_legend.html`) carry it to the page.

**Soft factors are recomputed, with a parity test; not parsed, not emitted.** The scorer
emits no structured key for good tithi, good star, good weekday or peak day; they exist only in
its `reason` prose. `explain` recomputes them from `EVENT_RULES` and the candidate's own
tithi, star, weekday and paksha, mirroring `score_event`'s branches (peak day only inside the
good-weekday branch, the deduction only in the `elif`). Drift is controlled by
`tests/test_muhurat_factor_parity.py`: the full grid (5 events x 30 tithis x 27 stars x 2
pakshas x 7 weekdays) and a real 200-day Delhi scan for all five events, with the weights
(+2, +2, +1, +1, -1) and tiers (5, 4, 3) written out literally. Rejected: parsing
`candidate.reason` at runtime (couples a data path to prose; breaks silently on a reworded
reason); editing the scorer to emit structured keys (the right end state, but it edits what
#1342 just refactored; a guaranteed conflict); a new `MuhuratCandidate` field (collides with
#1342's `score`). **Follow-up, not this change:** after #1342 merges, have `_soft_scoring`
emit structured keys, `explain` read them, and the parity test shrink.

**Boosters are "present", never "raised".** Booster flags are emitted even when the grade was
already excellent, and the reason text is inserted only when the grade changes; Sarvartha and
Ravi lift caution to good, not excellent. Saying "raised the grade" would need the 5/4/3
cut-offs a second time. The page says "Amrit Siddhi present" and the sentence ends "Whether
and how this finder lifts a grade for it is its own convention." A test forbids "raise" and
"lift" in the item text.

**The cleared list is derived and qualified at local noon.** It is read per row from the
event's `check_*` flags and `avoid_*` keys, never a static list (namkaran runs 7 of 15
exclusions; vivah 14). Tithi, star, pada, yoga, Sun-in-sign and combustion are read at
`MUHURTA_INSTANT_HOUR = 12`, so the heading is "Checked and not excluded at local noon" and
the legend carries "the Moon's star, the tithi and the yoga can change later in the day,
so confirm the exact hour with your priest". Never "clear all day". A row with no nakshatra
drops the panchak, star and pada items together (the finder degrades them together).
`_in_chaturmas` returns False on any exception, so that item means "not flagged", not
"verified".

**Abujha rows get an honest override.** The `abujha_name` branch of `find_candidates` skips
every hard exclusion and every booster. The explanation for such a row is therefore
`[abujha_muhurat]` scored, nothing cleared, no boosters, and the auditor's sentence verbatim:
"Listed as an Abujha date, a regional almanac custom this finder includes; no book it holds
names it. The usual exclusion checks were not run for this date, so confirm the tithi, star and
Panchak with your priest or panchang." The code's "universally auspicious" is not echoed. A
test pins this against today's branch using 2026-11-21 (Moon in Revati, a Panchak star, rated
excellent as an Abujha date); it goes red on purpose when #1346 changes the branch. The
override is keyed on the flag, so afterwards the cleared list follows what actually ran.

**Caution rows and avoid rows get no list.** The page labels caution rows "use with caution,
not recommended"; a "checked and not excluded" list beside that would read as an endorsement.
Avoid rows live in the restricted-dates table with their own reason; untouched.

**The scorer's one flag `avoid_weekday` is two rules.** The hard Tuesday exclusion and the soft
Saturday/Sunday deduction share the string. `registry_key_for_flag(flag, weekday)` splits them
on `weekday in _HARD_AVOID_WEEKDAYS` (they never share a row, because the hard check returns
first); a test AST-scans `muhurat.py` for every flag literal and requires an entry for each, so
a flag added later fails there.

### Status by event (S sourced, C contested, X site convention; defaults, `when` qualifiers in brackets)

Columns: vivah, griha_pravesh, namkaran, vidyarambh, business. Only the events that score or
run the factor show it on a page (peak day: business and vidyarambh; Sunday deduction:
vidyarambh; chaturmas: vivah and griha_pravesh; and so on, per `EVENT_RULES`).

| key | vivah | griha | namkaran | vidyarambh | business |
|---|---|---|---|---|---|
| good_tithi | S (dark-half credit C) | S | S | S (Dwadashi C) | X |
| good_nakshatra | S | S | S (Chitra C) | S (Rohini, Revati, Anuradha C; Pushya S) | X |
| good_weekday | S | S | C | S | X |
| peak_day | X | X | X | X | X |
| avoid_weekday_soft (Saturday) | C | C | C | S (Saturday and Sunday) | X |
| amrit_siddhi | C | C | C | C | C |
| sarvartha_siddhi, ravi_yoga, abujha_muhurat | X | X | X | X | X |
| adhik_maas, eclipse, kharmas, dagdha | X | X | X | X | X |
| nitya_yoga_block, panchak | S | S | S | S | S |
| chaturmas | C | X | X | X | X |
| jupiter_combust | X | C | X | X | X |
| venus_combust (vivah only), mercury_combust (business only) | X | X | X | X | X |
| avoid_nakshatra | C | S | C | S | X |
| avoid_nakshatra_pada (vivah only), avoid_krishna_tithi (vivah only) | S | S | S | S | S |
| avoid_tithi (Purnima C for vivah, Navami C for namkaran, Navami X for griha and business) | S | S | S | S | S |
| avoid_weekday (hard Tuesday) | S | S | S | S | S |
| soft_scoring_weights | X | X | X | X | X |

Sources: `knowledge/vedic_reference.md` (the vivah rules sit in section 29.9 and the 29.14
table; the other four events have their own `####` headings; business is the heading marked
UNSOURCED) and `knowledge/grahas.md` (combustion orbs, 12.1 and 12.5). The orbs are sourced;
treating combustion as a veto is this finder's convention for every event except
griha_pravesh, where Raman asks for a strong Guru and Shukra and it is contested. Headings
are stored as line prefixes (`"### 29.9 "`, with the trailing space so it cannot match
29.90) and a test reads the knowledge files to prove each still exists. No user-facing
sentence cites a chapter, a section number or a file name.

### The two astro-auditor passes

**Pass 1** ruled every key and wrote the page sentences; the registry transcribes it. **Pass 2
(a second review of the shipped registry) corrected what the first transcription got wrong
or overclaimed**, and the registry now carries it:

- Vidyarambh Rohini, Revati, Anuradha: "listed by one tradition, not both" was false for
  Rohini (Raman holds it neutral and Rao's row omits it); each star now has its own contested
  sentence. Pushya is sourced to Raman's list alone; "and the Vedic tables" overclaimed.
- Namkaran: good tithi was "listed by both" but only Rao's row lists it (Raman gives an avoid
  list), so its own sourced sentence; Chitra is contested (Rao lists it, Raman does not).
- Vidyarambh good weekday: Rao lists Monday, Wednesday, Thursday, Friday exactly; Raman only
  rejects Tuesday, Saturday, Sunday. "In the Muhurtha tradition" overclaimed.
- Soft Saturday deduction: the default sentence was Vivah's ("another calls it middling"),
  false for griha_pravesh and namkaran; each now has its own contested sentence.
- avoid_tithi: "is the exception" could read as "allowed"; now "Purnima is contested..." and
  "Navami is contested...".
- Lowercase openers capitalised; "worded here" marks added to four accurate deviations
  (business weekday extras, the weights list, the amrit closing clause, the Namkaran Tuesday
  sentence); the business Saturday sentence says "the Muhurtha tradition"; Vivah's Guru and
  Shukra veto sentences end "The two wedding lists the books give do not ask for it."

### Rejected alternatives

- Registry inside `muhurat.py`: see above.
- Parse `candidate.reason`: runtime coupled to prose.
- LLM-written explanations: out of scope, costs tokens on a path budgeted at zero, can invent a
  source.
- A static cleared list: would claim exclusions that never ran (and keep claiming them on an
  Abujha row).
- Per-row full sentences or `title=` tooltips: about 10x the page growth, and no hover on a
  phone. One legend instead, collapsed.
- A status enum class, dataclass hierarchy or config file: three strings and a dict literal.
- Recomputing the un-boosted tier to say "raised the grade": duplicates the cut-offs or depends
  on #1342's table.

### Measured

- Tokens: 0 per call, 0 per day. No LLM, no GCS, no new route, no request field reaches the
  module (the only dynamic values are tithi, star and weekday names and the event label).
- `explain` over 200 real vivah rows (Delhi, 2026-11-21 + 200 days): 0.48 ms; `legend` over the
  same 200 rows: 0.58 ms. The binding cost of the page stays the ephemeris scan.
- Page, 180-day Delhi vivah search: raw 313,205 -> 362,773 bytes (+49,568); gzip 47,094 ->
  49,930 (+2,836). The legend is 9,660 bytes once; a row's list averages 1,814 bytes.
- Gates run: the registry, parity and page tests, `verify_muhurat_tables.py`,
  `verify_rule_citations.py`, `verify_architecture_counts.py`. The headless render at 375 px and
  1280 px (no horizontal overflow) was run when the partials landed, not re-run for this
  wording change.

### Not done

- Top-pick card (#1342) carries no list yet; one include line after that merges.
- Structured keys from `_soft_scoring` (the follow-up above).
- Avoid rows, the restricted-dates table and the `/muhurat/<event>` landing pages.
- Abujha rows for griha_pravesh, vidyarambh and business appear unfiltered until #1346.
