# matching, numerology, muhurat and the dosha checks declare completions straight from the POST body

- **Date:** 2026-11-18
- **PR / issue:** #1217 (slice of #1070, rows 3-6)

## Why, measured

`measurements/ga4-events.json`, 2026-10-16..2026-11-12: 16 event names, none for these tools, while
`measurements/ga4.json` shows 23 (`/muhurat/griha-pravesh`), 19 (`/matching`) and 24 (`/numerology`)
organic landing sessions. Completions were unmeasurable. Declared with the #1067 marker:
`matching_completed`, `numerology_completed`, `muhurat_searched`, `dosha_check_completed`.

**No one-shot session flag, unlike #1068.** `kundli_generated` and `ask_answered` needed a flag
because their template also renders on a GET (a saved chart, a reload, `/r/<id>`). Here every
template that shows a result is rendered by the POST that computed it (`grep TemplateResponse` in
`routes/{matching,numerology,muhurat,dosha}.py`: the GET handlers pass `reading`/`compat`/
`candidates` as `None`, and no GET reads a stored result). So the success render IS the
completion, and an error, validation or empty render must carry no marker, which
`tests/test_analytics_tool_completion_events.py` asserts for each route. The R7 shareable
`GET /muhurat?...` of #1017 does not exist yet; whoever builds it must fire from that GET too, or
`muhurat_searched` undercounts it (#1017 F1 says "POST or R7 GET").

Consequence kept deliberate: a user who re-submits the same form (a reload re-POSTs after the
browser's confirm) counts twice, because that is a second computation. It is a completion count,
not a unique-user count.

Choices a reader should be able to check:

- **`score_band`** cuts the 36-point total at 18 and 25 (the issue's bands). 18 is the verdict's
  own floor (`_overall_verdict`), 25 is not a verdict boundary (those are 18/24/30). Half points
  (17.5, 24.5) fall in the lower band.
- **`muhurat_searched.mode`** is which optional input drove the result: `couple` (both partner
  charts computed), else `namkaran` (the CHILD's chart was computed; `event_type=namkaran` alone is
  `basic`, since `event_type` is its own param), else `personal` (a saved chart was computed), else
  `basic`. The inputs can overlap (vivah + personal + couple), so the order is fixed and the lossy
  case is the personal overlay on couple/namkaran. `days` is the number of days searched as the
  page's own "N-day search" line counts it; `valid_count` is the non-`avoid` dates.
- **Muhurat builds its params in the route**, but the template spells each value out
  (`muhurat_searched.mode`, ...) rather than passing the dict, because
  `tests/test_pii_egress_analytics.py` reads the argument expressions and a bare name is invisible
  to it. Each is on `ALLOWED_CALL_EXPRESSIONS` with the reason.
- **Tokens:** 0. Template markers only.
