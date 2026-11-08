# Lessons — last 30 days (generated 2026-11-08T11:44:04Z)

Read this before planning, specifying or ranking. It is the loop's memory of what
failed, what moved nothing, and what rivals do. Built by `scripts/collect_lessons.py`;
deterministic, no LLM.

> **Grounding rule.** A competitor pattern may suggest what to BUILD (structure, tools,
> wording, speed). It never imports an astrological claim: a rule seen on a rival site
> ships only once it traces to `knowledge/*.md`.

## Repeated error themes: act on these

- **copy** — 13 QA FAIL(s): #328, #536, #544, #550, #564, #649, #654, #675, #691
- **grounding** — 8 QA FAIL(s): #524, #536, #635, #701, #706, #747, #772
- **i18n** — 4 QA FAIL(s): #448, #524, #564, #737
- **performance** — 6 QA FAIL(s): #524, #536, #565, #675, #747
- **regression** — 15 QA FAIL(s): #536, #544, #636, #649, #654, #660, #675, #691, #704, #712, #737, #745, #747
- **security** — 8 QA FAIL(s): #328, #544, #564, #636, #712, #747
- **tests** — 10 QA FAIL(s): #448, #536, #544, #550, #701, #747, #754
- **tokens** — 12 QA FAIL(s): #536, #564, #649, #654, #660, #675, #747

## Our errors

- QA FAIL verdicts: 54
- reverted commits on main: 0
- failed verify-production runs: 3
- ops findings now: 2
  - [red] loop-broken: agent-work.yml is broken
  - [amber] loop-idle: Build lane idle 86% of the last 7d

## Our outcomes (analyst verdicts, latest per issue)

counts: HIT 2, OTHER 2, PARTIAL 1, PASS 5, PENDING 9, UNSCOREABLE 8
- #272: PASS — PASS on shape; the query-level half is NOT MET
- #276: PENDING — pending — scoreable from 2026-11-14
- #311: PENDING — pending — scoreable from 2026-11-13
- #313: OTHER — #313 (closed 2026-10-11)
- #316: OTHER — #316 (closed 2026-10-11)
- #320: HIT — HIT on `main`'s history; residual disclosed
- #329: PENDING — pending — scoreable from 2026-11-14, and likely unscoreable at this traffic
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
- #514: UNSCOREABLE — NOT SCOREABLE YET
- #515: UNSCOREABLE — NOT SCOREABLE YET
- #518: PENDING — pending — scoreable from 2026-12-07
- #553: PENDING — pending — scoreable from 2026-12-01
- #570: PENDING — pending — not scoreable until the export exists (#782); earliest clean window 2026-12-04
- #607: PASS — PASS
- #685: PENDING — pending — scoreable from 2026-12-04

A MISS is the most useful line here: before proposing work of the same kind, say why this time differs, or do not propose it.

## Competitor patterns

- none recorded yet: discover writes one issue per pattern with `<!-- competitor-pattern -->`
