"""#1457: the Vivah lagna legend keys on a block produced, not on row eligibility.
tests/test_muhurat_lagna_page.py."""

_M = "src/astro_ai/muhurat_lagna.py"

MUTATIONS = [
    ("#1457: the legend keys on row eligibility again (a page whose every row failed still shows it)",
     _M, "if any(lagna_view(c, event_type, city) is not None for c in candidates):",
     "if any(_eligible(c, event_type) for c in candidates):",
     "test_the_legend_is_keyed_on_a_block_produced_not_on_row_eligibility"),
    ("#1457: the legend needs EVERY row to produce a block (one failing date hides it)",
     _M, "if any(lagna_view(c, event_type, city) is not None for c in candidates):",
     "if all(lagna_view(c, event_type, city) is not None for c in candidates):",
     "test_the_legend_is_keyed_on_a_block_produced_not_on_row_eligibility"),
]
