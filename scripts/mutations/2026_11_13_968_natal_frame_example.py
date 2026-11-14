"""#968: the natal FRAME DISAMBIGUATION example no longer contradicts the output bans.

2026-11-13. The row puts the original example back ("Mars falls in the 4th house")
and requires the Gate 5 check to go red on the real prompt."""

MUTATIONS = [
    ("#968: natal.txt teaches 'Mars falls in the 4th house' again, against its own STRICT OUTPUT RULES",
     "src/astro_ai/prompts/natal.txt",
     "counted from your Moon, the placement that marks Manglik is present in your chart",
     "counted from your Moon, Mars falls in the 4th house, which is what marks Manglik in your chart",
     "test_the_shipped_natal_prompt_has_no_example_placing_a_planet_in_a_numbered_house"),
]
