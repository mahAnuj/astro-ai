"""#871: /matching's two mini charts keep their labels and the retrograde R >= 10px.

Each row re-breaks one property the two new tests in tests/test_diamond_label_geometry.py hold."""

MUTATIONS = [
    ("#871: the retrograde R goes back to the 13-unit tspan (8.4px in a 259px /matching box)",
     "src/astro_ai/templates/_diamond_labels.html",
     '<tspan font-size="16" fill="{{ r_fill }}">',
     '<tspan font-size="13" fill="{{ r_fill }}">',
     "test_retrograde_mark_clears_ten_px_at_375_on_matching"),
    ("#871: the two /matching charts sit side by side from 640px again (219px box, 8.76px labels)",
     "src/astro_ai/templates/matching_result.html",
     '<div class="grid md:grid-cols-2 gap-5">',
     '<div class="grid sm:grid-cols-2 gap-5">',
     "test_matching_charts_stack_until_md_so_each_box_stays_above_the_two_up_floor"),
]
