"""#1338: `compute_panchang` is memoised on exact coordinates, never a grid cell."""

MUTATIONS = [
    ("#1338: the panchang cache goes back to the 0.5deg cell (the finder depends on whether the landing page ran first)",
     "src/astro_ai/chart.py",
     "        round(natal.birth_lat, 4),\n        round(natal.birth_lon, 4),\n        natal.birth_tz,",
     "        round(natal.birth_lat * 2) / 2,\n        round(natal.birth_lon * 2) / 2,\n        natal.birth_tz,",
     "test_the_finder_does_not_depend_on_the_landing_page_having_run_first"),

    ("#1338: the panchang cache key is rounded to 0.1deg (~11 km), still merging two points of one city",
     "src/astro_ai/chart.py",
     "        round(natal.birth_lat, 4),\n        round(natal.birth_lon, 4),\n        natal.birth_tz,",
     "        round(natal.birth_lat, 1),\n        round(natal.birth_lon, 1),\n        natal.birth_tz,",
     "test_two_cities_in_one_half_degree_cell_each_keep_their_own_times_in_either_order"),

    ("#1338: the panchang cache stops returning its entries (every call recomputes)",
     "src/astro_ai/chart.py",
     "    if cached is not None:\n        return cached\n\n    weekday = today.weekday()",
     "    if False:\n        return cached\n\n    weekday = today.weekday()",
     "test_the_cache_still_hits_for_the_same_place_and_day"),

    ("#1338: the panchang cache loses its size bound (free-text cities grow it without limit)",
     "src/astro_ai/chart.py",
     "    if len(_PANCHANG_CACHE) >= _PANCHANG_CACHE_MAX:\n        _PANCHANG_CACHE.clear()\n",
     "    if False:\n        _PANCHANG_CACHE.clear()\n",
     "test_the_cache_is_bounded_because_free_text_cities_mint_keys"),
]
