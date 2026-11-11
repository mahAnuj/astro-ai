# The muhurat finder states how it judges combustion; no verdict changed

- **Date:** 2026-11-11
- **PR / issue:** #219 (`closes #219`: its ask was that the page state its convention)

## Why, measured

At b3850d3 the finder said only "Guru + Shukra + Budh combustion per event karaka" (and "combustion
checks" in two descriptions). It never said how combustion is judged, which planet blocks which event,
or that Budh's Business veto is our own widening. What the code does: `_combustion_flags` tests the
planet's separation from the Sun at noon on each date against `chart.COMBUSTION_ORBS` (Guru 11, Shukra
10/9 retrograde, Budh 14/13 retrograde; Raman, *Muhurtha*, Appendix, verified in `knowledge/grahas.md`
12.1); `score_event` turns a hit into a terminal "avoid" for the planets an event checks. `EVENT_RULES`:
Vivah Guru + Shukra, Griha Pravesh Guru, Vidyarambh Guru, Business Budh, Namkaran none. Business vetoes
every weekday; Raman's only Mercury-combustion line (Upanayana, p. 64) rejects Wednesday alone
(`knowledge/grahas.md` 12.5), so the veto is ours.

**Changed.** One English paragraph in `muhurat_finder.html`, always shown (it does not depend on a
personal or couple search): the degree test and the orbs, the per-event list, "does not count days
around a planet's rising or setting", "knows only combust or not combust", and that the Business Budh
veto is the finder's own extension. Two code comments in `muhurat.py`: Namkaran's waiver is labelled
unsourced for Namkaran, by analogy with Raman's Seemantha (p. 58) and Annaprasana (p. 60) waivers
(`knowledge/grahas.md` 12.5, no Namkaran line; QA round 1 caught the first wording, "Sourced"), and the
Business Mercury flag says it is not sourced. No flag, orb, grade or verdict changed. Tokens: 0; `src/astro_ai/prompts`
untouched.

**Not claimed.** Nothing about what *Muhurta Chintamani* or any other text's method is: `knowledge/` does
not hold it (12.5 measured the heliacal model absent) and `data/` held 0 books on the runner, so the
issue's own quotation was not re-verified. The paragraph names Raman only for the orbs. Same bound as the
#714 disclosure: state what the code does and what is held.

**Rejected.** Modelling days-from-heliacal rising/setting or the infant/aged states: it needs a source
`knowledge/` does not hold (closed-list item 2) and would move verdicts. Narrowing Business to Wednesday:
a verdict change on a product call, so it is not made here. Both stay open as a value question, not as
this issue's acceptance.

**Would overturn this:** a held text giving a different method, or a ruling to drop the Business
extension. Either is a sourced change that edits `tests/test_combustion_disclosure.py` on purpose.

**Gate.** `tests/test_combustion_disclosure.py` (orbs read back from `COMBUSTION_ORBS`, the event list
pinned to `EVENT_RULES`, no wording about any other text, Business vetoes every weekday, Namkaran still
waives all three) and six rows in `scripts/mutations/2026_11_11_219_combustion_note.py`.
