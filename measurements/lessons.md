# Lessons — last 30 days (generated 2026-11-19T20:15:38Z)

Read this before planning, specifying or ranking. It is the loop's memory of what
failed, what moved nothing, and what rivals do. Built by `scripts/collect_lessons.py`;
deterministic, no LLM.

> **Grounding rule.** A competitor pattern may suggest what to BUILD (structure, tools,
> wording, speed). It never imports an astrological claim: a rule seen on a rival site
> ships only once it traces to `knowledge/*.md`.

## Repeated error themes: act on these

- **copy** — 20 QA FAIL(s): #536, #544, #550, #564, #649, #654, #675, #691, #815, #833, #841, #884, #960, #1000, #1077
- **grounding** — 31 QA FAIL(s): #524, #536, #635, #701, #706, #713, #747, #772, #815, #833, #841, #845, #859, #875, #1011, #1027, #1057, #1058, #1063, #1077, #1086, #1132, #1150, #1167, #1169
- **i18n** — 9 QA FAIL(s): #524, #564, #737, #815, #875, #1057, #1150
- **performance** — 8 QA FAIL(s): #524, #536, #565, #675, #747, #815
- **regression** — 32 QA FAIL(s): #536, #544, #636, #649, #654, #660, #675, #691, #704, #712, #737, #745, #747, #815, #841, #884, #1000, #1002, #1128, #1167, #1169, #1212, #1241, #1262
- **security** — 15 QA FAIL(s): #544, #564, #636, #712, #747, #841, #846, #1000, #1150, #1162, #1167, #1169
- **tests** — 29 QA FAIL(s): #536, #544, #550, #701, #713, #747, #754, #801, #804, #833, #841, #846, #913, #999, #1027, #1058, #1105, #1167, #1169, #1173, #1212
- **tokens** — 21 QA FAIL(s): #536, #564, #649, #654, #660, #675, #747, #815, #841, #846, #913, #1000, #1105, #1173, #1210

## Our errors

- QA FAIL verdicts: 119
- reverted commits on main: 0
- failed verify-production runs: 9
- ops findings now: 2
  - [amber] claude-quota: Claude weekly quota 87% used
  - [amber] loop-starved: 4 of the last 4 build cycles built nothing

## Our outcomes (analyst verdicts, latest per issue)

counts: MISS 1, OTHER 1, PARTIAL 1, PASS 5, PENDING 17, UNSCOREABLE 10
- #272: PASS — PASS on shape; the query-level half is NOT MET
- #276: OTHER — BAR MET, not attributable to the CTA
- #311: MISS — MISS
- #329: UNSCOREABLE — UNSCOREABLE at this traffic: 3 vs 10
- #338: PASS — PASS
- #373: PARTIAL — PARTIAL
- #396: PASS — PASS on the first clause only
- #397: PASS — PASS on the countable clause; the behavioural clause was not checked
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
- #843: UNSCOREABLE — not scoreable from GA4/GSC
- #1066: PENDING — pending — scoreable from 2026-12-16; the metric needs an export that does not exist
- #1073: PENDING — pending — scoreable from 2026-12-17
- #1074: PENDING — pending — scoreable from 2026-12-17; floor at risk
- #1075: PENDING — pending — scoreable from 2026-12-17
- #1080: UNSCOREABLE — not scoreable from GA4/GSC
- #1083: UNSCOREABLE — not scoreable from GA4/GSC
- #1093: PENDING — pending — scoreable from 2026-12-16; the metric needs an export that does not exist
- #1178: UNSCOREABLE — not scoreable from GA4/GSC
- #1217: PENDING — pending — scoreable from 2026-12-19
- #1226: PENDING — pending — scoreable from 2026-12-19
- #1229: PENDING — pending — scoreable from 2026-12-19

A MISS is the most useful line here: before proposing work of the same kind, say why this time differs, or do not propose it.

## Competitor patterns

- #835 [closed] SEO debilitated-sun-career: 480 impressions on 'which sign' questions, 0 clicks — answer-first FAQ +
