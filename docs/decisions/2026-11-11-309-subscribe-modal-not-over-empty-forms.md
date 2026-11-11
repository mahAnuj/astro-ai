# The subscribe modal never auto-opens on a calculator page, empty or not

- **Date:** 2026-11-11
- **PR / issue:** #309 (follows #382)

## Why, measured

#382 stopped the modal opening over a tool *result*, using a `data-subscribe-defer` marker
that only result renders emit. The empty form renders no marker, so on a repeat visit
(`bhagya_visit_count` 1 -> 2, in `SHOW_AT_VISITS = [2, 5]`) the modal still opened over
the form before the visitor had typed anything. Measured on production 2026-11-11 by
`/prioritise`: `/numerology`, `/kundli`, `/muhurat` and `/panchang` each serve the gate
script and 0 defer markers.

Chosen: a `TOOL_FORM_PATHS` list in the gate (`/kundli`, `/matching`, `/numerology`,
`/muhurat`, `/panchang`), checked before the visit is counted, so the prompt reaches the
first load outside the tools instead of burning visit 2 on a calculator. The issue's own
metric allows "an equivalent exclusion in the show gate".

Rejected: a marker in each of five templates (five edits and five tests for one rule, and
`/panchang`'s date routes would each need it); keying on the form's emptiness (the gate
cannot see it, and a result is already deferred by #382).

**Cost, stated.** A visitor who only ever uses calculators is no longer auto-prompted.
The baseline is `subscribe_completed` = 1 event in the 28 days to 2026-11-07 across 101
tool-landing sessions, so there is little auto-conversion to lose. Manual CTAs
(`[data-subscribe-trigger]`, the footer link) are untouched. Not covered: `/reading` (the
kundli result) and `/rashifal`, `/ask`; the issue measured the four calculators only.
