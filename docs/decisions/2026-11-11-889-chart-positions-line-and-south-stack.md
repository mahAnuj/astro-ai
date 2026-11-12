# /matching prints a positions line under each chart, and the South Indian stack fits its cell

- **Date:** 2026-11-11
- **PR / issue:** #889

## Why, measured

`_diamond_labels.html` and `scripts/gen_diamond_label_slots.py` said the degree and retrograde
flag a crowded diamond cell drops "remain in the positions table under the chart"
(`docs/decisions/2026-11-10-diamond-label-slots.md` says the same and is left as written; this file corrects it). That is true on `/kundli`
(`result.html`, the collapsed "Planetary positions" table) and false on `/matching`, which has no
planet table: a degree or R the slot modes dropped from a `/matching` chart was lost from the page.
Both sentences now say where each page keeps it.

- **`/matching` gets a compact positions line under each chart** (`_chart_positions.html`, called
  from `matching_result.html`'s `mini_chart` macro): every planet from `ch.diamond_chart()`, house
  by house, `Su 29° R · Mo 12° ...`, `text-xs` in `text-bhagya-muted`, labelled by the new
  `matching_positions_label` key (en "Positions", hi "ग्रह स्थिति"). Abbreviations stay the chart's
  own English two letters. Rejected: a full table per chart (two more tables on a page that is
  already long), and Hindi abbreviations (invented, and not what the chart prints).
- **South Indian cell, measured at 375px in headless Chromium** (301px box): with 6 planets in the
  lagna cell the 6th left the cell and `LAGNA` (cy+92) collided with a label from the 5th; with 8,
  three labels left the cell. Now `LAGNA` sits in the header row (cx+46), 1..6 planets stay one
  column (start rises from cy+42 to cy+29 so six end inside), 7..8 use two columns of `Su R` (the
  degree is dropped, as the diamond does; `/kundli`'s table carries it, because "Su 29° R" is ~50
  units wide and a cell has 94). Font sizes are unchanged (8.28px rendered at 375px, as before).
- **Not done:** `chart.py` is a rule module and was not edited; the D-9/D-10 diamonds still print
  abbreviations only and have no table of their own.
- Template change only; every Tailwind class used was already in `app.css` (`verify_css_build` PASS
  with no rebuild). No LLM path: 0 tokens.
