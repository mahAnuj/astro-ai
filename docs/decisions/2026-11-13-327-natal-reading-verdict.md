# Every fresh natal reading gets a log-only verdict against natal.txt's own bans

- **Date:** 2026-11-13
- **PR / issue:** #966 (slice 1 of #327); follow-ups #967 and #968

## Why, measured

`prompts/natal.txt` states hard bans (nine planet names, sign names, house numbers,
decimals, classical-text names, 17 banned words) and seven sections. Nothing checked
the natal output; the only `check_reading(` caller was rashifal's. A prompt rule is a
request: `rashifal_quality` measured its planet ban broken in 31.0% of 252 published
readings. A provider silently swapping models would move the natal rate unseen.

**Chosen:** `src/astro_ai/reading_quality.py` (stdlib, zero LLM, zero GCS ops) and one
call in `routes/kundli.py::_render_natal_for`, inside `if not was_cached:`, wrapped in
try/except. It adds `q_ok`, `q_sections`, `q_banned` (kind -> count), `q_words` and
`q_manglik` to the existing `form_kundli` event, and logs kind:term pairs, never prose.
It never blocks, regenerates or changes what is served. `events.py` needed no edit
(`record(data=dict)` takes any keys). `natal.txt` is untouched, so 0 tokens.

**Rejected:** blocking or regenerating (a second ~7,800-token call against an 8,000 TPM
per-model bucket); checking inside `llm.generate_reading` (no channel to the event, grows
`llm.py`); a thread-local "last verdict" (shared mutable state for one extra caller); a
private `## ` counter (the route already holds `parse_sectioned_reading`'s result, so a
second definition of "section" could only drift); Mars/Saravali aliases (natal.txt bans
nine English words and a fixed list of texts; banning more would invent a rule).

## What the number does not mean

- **natal.txt contradicts itself (#968).** Line 32 tells the model to write "Mars falls in
  the 4th house" on Manglik charts, which breaks the planet ban (:51) and the house-number
  ban (:53) together. Manglik charts can fail for a reason the model cannot fix, so the
  event carries `q_manglik` and the rate must be sliced by it. Fixing the prompt is #968
  (`prompts/` is the #354 trust boundary).
- **Hindi: the pass rate must not be published.** Section count is checked, but every banned
  term is a Latin-script word, so `q_banned` undercounts. `q_words` is None for `lang != en`
  (the 920-1380 band is an English count). Devanagari tables need a `knowledge/` or `i18n.py`
  source first.
- **Coverage is "fresh generations through `/kundli`", not all natal readings (#967).** The
  snapshot route (`_cached(... call_fn=generate_reading)`) also generates; that reading is then
  cached so the next `/kundli` view is `was_cached=True`, and nothing restored from GCS is
  checked either. The metric "0 -> 100% of natal readings" in #966 is unreachable by this slice.
- **Not checked: five of natal.txt:54's DO NOT phrases** ("transit", "gochar", "natal Lagna",
  "Bhava", "lord of the"; "natal Moon" only via the Moon planet rule), so `ok` is True for a
  reading using them. Follow-up: #970. QA round 1 found this and the docs had not said it.
- **Broader than the prompt:** the decimal and chapter rules also flag "10.30", "1.0" and
  "chapter 4" prose, and the stems over-match ("manifesto", "navigator"). Read a rate as a trend.
- **Undercounts by construction:** planets and signs are case-sensitive ("the moon" is missed),
  and the seeker's name is stripped before matching (Meena, Tula, Kanya, Leo are real first
  names), which hides a genuine hit on a name equal to a banned term. "second house" may flag a
  literal second house. Log-only is what makes shipping before calibrating safe; the first
  week of events is the calibration. The false-positive rate on real output is undetermined.

Guards: `tests/test_reading_quality.py` parses natal.txt's planet line, BANNED WORDS paragraph
and classical-text list, so a ban added to the prompt without the linter fails the build.
