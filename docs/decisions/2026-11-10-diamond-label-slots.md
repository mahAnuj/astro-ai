# Diamond chart labels are placed from a solved slot table, 16 units, in one shared macro

- **Date:** 2026-11-10
- **PR / issue:** #380

## Why, measured

**The defect.** The North Indian diamond is `viewBox="0 0 400 400"`; a label's rendered size is
`font-size x box/400`. Measured in headless Chromium at a 375px viewport: the /kundli Lagna box is
301px (scale 0.7525) and a /matching mini chart is 259px (scale 0.6475). The old sizes (11, and 10
in the minis) rendered at 8.3px and 6.5px. The issue's metric is >= 10px with zero overlapping
boxes in a house holding 4+ planets.

**Why not just raise the size.** Eight of twelve cells are triangles whose width shrinks to nothing
at the apex (house 2 is ~50 units wide at y=76), and the old pitch of 13 is smaller than a 16-unit
label. Stamping the new size on the old coordinates, 4 planets per house at 16 units, measured 36
overlapping box pairs and 16 labels crossing a cell line (301px box, headless Chromium).

**Decision.**
- Planet labels are 16 units (12.0px at 301, 10.4px at 259), house numbers 15, the retrograde R 13.
- Positions come from a table solved by `scripts/gen_diamond_label_slots.py` per (house, planet
  count), pitch 17.6 (1.1 x the size; was 13), pasted into `templates/_diamond_labels.html`, the one
  macro all three chart sites now call. `tests/test_diamond_label_geometry.py` re-checks every house
  at 1..8 planets from the rendered `<text>` elements.
- **A cell too small for the degree drops it.** A lone planet keeps `Su 29° R` in every cell. Past
  3 planets in a top/bottom triangle, or 2 in a side triangle, labels become `Su R`; a triangle with
  7+ becomes `Su`. The degree and retrograde flag of every planet stay in the positions table under
  the chart. Rejected: shrinking below 10px for crowded cells (the metric), and a smaller degree
  line (reads worse than dropping it).
- 8 is the ceiling: Rahu and Ketu are opposite, so a sign holds at most 7 grahas plus one node.
- **Not done:** `chart.py`'s `DIAMOND_POSITIONS` is a rule module and was left alone; no template
  reads it any more. The South Indian chart (`_south_indian_chart.html`) keeps its sizes: not
  measured, not changed. The D-9/D-10 charts print the abbreviation only, at the same slots.
- Attribute-only change; no Tailwind class was touched, so `app.css` is unchanged.
