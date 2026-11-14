# Lessons — last 30 days (generated 2026-11-14T03:37:19Z)

Read this before planning, specifying or ranking. It is the loop's memory of what
failed, what moved nothing, and what rivals do. Built by `scripts/collect_lessons.py`;
deterministic, no LLM.

> **Grounding rule.** A competitor pattern may suggest what to BUILD (structure, tools,
> wording, speed). It never imports an astrological claim: a rule seen on a rival site
> ships only once it traces to `knowledge/*.md`.

## Repeated error themes: act on these

- **copy** — 18 QA FAIL(s): #536, #544, #550, #564, #649, #654, #675, #691, #815, #833, #841, #884, #960
- **grounding** — 18 QA FAIL(s): #524, #536, #635, #701, #706, #713, #747, #772, #815, #833, #841, #845, #859, #875
- **i18n** — 8 QA FAIL(s): #448, #524, #564, #737, #815, #875
- **performance** — 8 QA FAIL(s): #524, #536, #565, #675, #747, #815
- **regression** — 19 QA FAIL(s): #536, #544, #636, #649, #654, #660, #675, #691, #704, #712, #737, #745, #747, #815, #841, #884
- **security** — 9 QA FAIL(s): #544, #564, #636, #712, #747, #841, #846
- **tests** — 18 QA FAIL(s): #448, #536, #544, #550, #701, #713, #747, #754, #801, #804, #833, #841, #846, #913
- **tokens** — 17 QA FAIL(s): #536, #564, #649, #654, #660, #675, #747, #815, #841, #846, #913

## Our errors

- QA FAIL verdicts: 82
- reverted commits on main: 0
- failed verify-production runs: 5
- ops findings now: 1
  - [amber] token-ceiling: Peak day used 83% of the Groq daily budget

## Our outcomes (analyst verdicts, latest per issue)

counts: HIT 1, MISS 1, OTHER 1, PARTIAL 1, PASS 5, PENDING 9, UNSCOREABLE 11
- #272: PASS — PASS on shape; the query-level half is NOT MET
- #276: OTHER — BAR MET, not attributable to the CTA
- #311: MISS — MISS
- #329: UNSCOREABLE — UNSCOREABLE at this traffic: 3 vs 10
- #338: PASS — PASS
- #345: UNSCOREABLE — UNSCORED (not determinable this run)
- #349: UNSCOREABLE — UNSCORED (not determinable this run)
- #355: UNSCOREABLE — UNSCORED (not determinable this run)
- #369: UNSCOREABLE — UNSCORED (not determinable this run)
- #373: PARTIAL — PARTIAL
- #374: UNSCOREABLE — UNSCORED (not determinable this run)
- #396: PASS — PASS on the first clause only
- #397: PASS — PASS on the countable clause; the behavioural clause was not checked
- #400: HIT — HIT (partial read) — ceiling gate present and green
- #426: PENDING — pending — scoreable from 2026-12-03
- #493: UNSCOREABLE — UNSCORED — the measured event has not happened yet
- #508: PENDING — pending — scoreable from 2026-12-04
- #513: UNSCOREABLE — unscoreable at this traffic
- #514: UNSCOREABLE — unscoreable at this traffic
- #515: UNSCOREABLE — unscoreable at this traffic
- #518: PENDING — pending — scoreable from 2026-12-07
- #523: UNSCOREABLE — unscoreable at this traffic
- #528: PENDING — pending — scoreable from 2026-12-10
- #553: PENDING — pending — scoreable from 2026-12-01
- #570: PENDING — pending — not scoreable until the export exists (#782); earliest clean window 2026-12-04
- #607: PASS — PASS
- #685: PENDING — pending — scoreable from 2026-12-04
- #735: PENDING — pending — scoreable from 2026-12-12
- #835: PENDING — pending — scoreable from 2026-12-14

A MISS is the most useful line here: before proposing work of the same kind, say why this time differs, or do not propose it.

## Competitor patterns

- #835 [closed] SEO debilitated-sun-career: 480 impressions on 'which sign' questions, 0 clicks — answer-first FAQ +
