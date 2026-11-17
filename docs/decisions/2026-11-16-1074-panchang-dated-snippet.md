# A dated /panchang/{date} snippet is built once, from the page's own values

- **Date:** 2026-11-16
- **PR / issue:** #1074

## Why, measured

`panchang.html` hardcoded "Today's Panchang" in the `<title>` and a values-free description
for every date, so `/panchang/2026-12-02` (probed 2026-11-15) was titled "Today's Panchang"
17 days ahead and its description carried no date, tithi, nakshatra or Rahu Kaal.

Chosen: `routes/panchang._answer_snippet` builds one sentence ("On Wednesday, 2 December 2026
in Mumbai, India: Krishna Navami at sunrise, Moon in Uttara Phalguni, Rahu Kaal 12:27–13:50.")
from `p`, `moon_info` and the rendered date. The page shows it under the H1 on every date, and
a non-today description is that sentence plus a fixed tail when it fits 160 characters, so the
snippet and the page cannot drift. Non-today title: "Panchang <date> — Tithi, Nakshatra, Rahu
Kaal (<city>)". `/panchang` keeps its title and description byte for byte. Rahu Kaal is
omitted when `daylight_ordinary` is False (#227), the Moon when `moon_info` is absent, and a
`p` of None yields a values-free dated description. The tithi is the sunrise one, the page's
stated convention (#593); the Moon is the page's own "Moon Today" value. No interpretive
word and no new rule. 0 LLM tokens.

Known and left: the dated title names Rahu Kaal even on a polar date whose page omits it; the
title is a static phrase, the sentence and description are the part the omission rule governs.
