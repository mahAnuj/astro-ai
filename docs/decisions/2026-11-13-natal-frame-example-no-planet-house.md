# natal.txt's Manglik frame example may not name a planet in a numbered house

- **Date:** 2026-11-13
- **PR / issue:** #968 (follow-up to #966 / #327)

## Why, measured

`natal.txt:32` (FRAME DISAMBIGUATION) taught the model by example: "counted from your Moon,
Mars falls in the 4th house, which is what marks Manglik in your chart". The same prompt's
STRICT OUTPUT RULES ban naming Mars (and the other planets) and natal house numbers. A model
that obeyed the example broke both bans; one that obeyed the bans ignored the example. That
made the #966 compliance verdict ambiguous on Manglik charts.

**Decision:** the frame tag stays (it was added in #45 so a bare placement is never stated
without its frame), but the example now reads "counted from your Moon, the placement that
marks Manglik is present in your chart", and the bullet states the one carve-out in words:
naming the frame is the only place "Lagna", "Moon" or "Venus" may appear; Mars is never
named there and no house number is given. The frame words were already pinned by
`verify_natal_prompt.py`'s `manglik-frame-disambiguation` rule, so this makes the prompt
say what the gate already assumed.

**Gate:** Gate 5 of `scripts/verify_natal_prompt.py` now fails on any sentence of the form
"<planet> falls/sits/is in the Nth house". `tests/test_natal_prompt_frame_example.py` runs it
over the real prompt and over a copy with the old sentence put back; the mutation row is
`scripts/mutations/2026_11_13_968_natal_frame_example.py`.

**Cost, measured with `scripts/measure_natal_request.py`:** system prompt 3,001 → 3,000 tok,
natal worst case 6,773 → 6,772 tok against the 8,000 ceiling; file 12,640 → 12,631 B. The edit
changes the prompt fingerprint, so cached natal readings regenerate once on first request
after deploy (a one-time Groq spend, not a per-request one).

**Not done, on purpose:** the frame words "Moon" and "Venus" are still planet names that
`reading_quality.py` (#970) must not count as violations inside a frame tag. That is #970's
scope; this PR does not touch `reading_quality.py` because #969 is still open on it.
