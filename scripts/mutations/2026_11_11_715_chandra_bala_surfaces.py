"""#715: Chandra Bala has two grade tables, one per surface. The Muhurat Finder (personal match
and the Vivah couple verdict) weakens a house when either held source names it -- the 2A Gochara
Moon row or Raman, Muhurtha (6th, 8th, 12th) -- so house 6 is weak there; the daily Rashifal keeps
the 2A row alone, so house 6 is strong there. The finder discloses only those two held sources."""

_MUHURTA_SETS = ("_CB_MUHURTA_STRONG = {1, 3, 7, 10, 11}\n"
                 "_CB_MUHURTA_WEAK   = {2, 4, 5, 6, 8, 9, 12}\n")
_GOCHARA_SETS = ("_CB_GOCHARA_STRONG = {1, 3, 6, 7, 10, 11}\n"
                 "_CB_GOCHARA_WEAK   = {2, 4, 5, 8, 9, 12}\n")

MUTATIONS = [
    ("#715: house 6 goes back to strong on the muhurta surface (the pre-Raman-Muhurtha table)",
     "src/astro_ai/muhurat.py",
     _MUHURTA_SETS,
     "_CB_MUHURTA_STRONG = {1, 3, 6, 7, 10, 11}\n"
     "_CB_MUHURTA_WEAK   = {2, 4, 5, 8, 9, 12}\n",
     "test_house_6_is_strong_on_the_rashifal_path_and_weak_on_the_muhurta_path"),
    ("#715: house 6 becomes weak on the Rashifal surface (Gochara row no longer 2A's)",
     "src/astro_ai/muhurat.py",
     _GOCHARA_SETS,
     "_CB_GOCHARA_STRONG = {1, 3, 7, 10, 11}\n"
     "_CB_GOCHARA_WEAK   = {2, 4, 5, 6, 8, 9, 12}\n",
     "test_the_rashifal_path_keeps_the_gochara_grade_for_every_house"),
    ("#715: the muhurta surface follows Raman, Muhurtha alone (2, 4, 5, 9 stop being weak)",
     "src/astro_ai/muhurat.py",
     _MUHURTA_SETS,
     "_CB_MUHURTA_STRONG = {1, 2, 3, 4, 5, 7, 9, 10, 11}\n"
     "_CB_MUHURTA_WEAK   = {6, 8, 12}\n",
     "test_the_muhurta_surface_grades_each_house_from_the_two_held_sources"),
    ("#715: _chandra_bala gets a default surface, so a caller that forgets it is graded silently",
     "src/astro_ai/muhurat.py",
     "                  surface: str) -> tuple[int, str]:\n",
     '                  surface: str = "gochara") -> tuple[int, str]:\n',
     "test_the_surface_has_no_default_and_an_unknown_one_fails"),
    ("#715: the Rashifal path asks for the muhurta grading (house 6 turns weak on the daily card)",
     "src/astro_ai/muhurat.py",
     '_chandra_bala(r, transit_moon_rashi, surface="gochara")',
     '_chandra_bala(r, transit_moon_rashi, surface="muhurta")',
     "test_house_6_is_strong_on_the_rashifal_path_and_weak_on_the_muhurta_path"),
    ("#715: the finder's personal match asks for the Gochara grading (house 6 strong again)",
     "src/astro_ai/muhurat.py",
     '_chandra_bala(user_moon.rashi, transit_moon.rashi, surface="muhurta")',
     '_chandra_bala(user_moon.rashi, transit_moon.rashi, surface="gochara")',
     "test_the_finder_personal_match_grades_house_6_weak"),
    ("#715: the Vivah partner factors ask for the Gochara grading (house 6 strong for a couple)",
     "src/astro_ai/muhurat.py",
     '_chandra_bala(p_moon.rashi, transit_moon.rashi, surface="muhurta")',
     '_chandra_bala(p_moon.rashi, transit_moon.rashi, surface="gochara")',
     "test_the_couple_partner_factors_grade_house_6_weak"),
    ("#715: the finder's disclosure drops the Raman Muhurtha 6th/8th/12th rule it grades by",
     "src/astro_ai/templates/muhurat_finder.html",
     "(for an election chart, the Moon in the 6th, 8th or 12th from the Janma Rasi)",
     "(for an election chart)",
     "test_the_finder_states_the_source_of_the_chandra_grade"),
    ("#715: the finder footer names the unheld BPHS / Muhurtha Chintamani / Phaladeepika again",
     "src/astro_ai/templates/muhurat_finder.html",
     "<p><strong>Sources:</strong> B.V. Raman, ",
     "<p><strong>Sources:</strong> Brihat Parashara Hora Shastra, Muhurtha Chintamani, "
     "Phaladeepika; B.V. Raman, ",
     "test_the_finder_footer_names_only_held_sources"),
    ("#715: the finder's Chandra note claims what other traditions say",
     "src/astro_ai/templates/muhurat_finder.html",
     "Houses 1, 3, 7, 10 and 11 are therefore shown as strong.",
     "Houses 1, 3, 7, 10 and 11 are therefore shown as strong; other traditions differ.",
     "test_the_finder_claims_nothing_about_muhurta_traditions_in_the_chandra_note"),
]
