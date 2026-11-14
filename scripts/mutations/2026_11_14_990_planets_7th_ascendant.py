"""#990: the per-Ascendant list on the planets-in-the-7th guide gets its sign arithmetic right.

Each row restores one defect (or drops a sourced qualifier) and names the test that must go red."""

_T = "src/astro_ai/templates/learn/planets-in-7th-house-marriage.html"
_VENUS = ("Aries or Scorpio Ascendant, Venus in 7th:</strong> the 7th house is Libra from an Aries Ascendant "
          "and Taurus from a Scorpio one, so Venus is in her own sign, and the 7th is a kendra.")

MUTATIONS = [
    ("#990: the false 'Taurus or Libra Ascendant, Venus in 7th' Malavya line is back",
     _T,
     _VENUS,
     "Taurus or Libra Ascendant, Venus in 7th:</strong> Venus is in her own sign in her own house.",
     "test_false_taurus_libra_venus_claim_is_gone"),
    ("#990: Venus in the 7th is 'in his own sign in his own house' again",
     _T,
     "so Venus is in her own sign, and the 7th is a kendra.",
     "so Venus is in his own sign in his own house, and the 7th is a kendra.",
     "test_venus_is_not_called_his_anywhere_in_the_block"),
    ("#990: the unsourced Malavya superlative is back on the Venus line",
     _T,
     "That meets the condition the sources we work from give for Malavya Yoga",
     "The most powerful Malavya Yoga configuration, producing exceptional marriage prosperity. That meets the "
     "condition the sources we work from give for Malavya Yoga",
     "test_venus_line_is_the_aries_or_scorpio_case_and_names_malavya"),
    ("#990: the Mars line gives the meaningless 'dispositor's mirror' reason again",
     _T,
     "the 7th house is Libra from an Aries Ascendant and Taurus from a Scorpio one, both signs of Venus. The "
     "reference we work from lists Mars in a Venus sign among the conditions that mitigate the Manglik reading, "
     "so the reading is softened, not removed.",
     "Mars is in a friendly sign of his own dispositor's mirror; Manglik-dosha reading is significantly softened.",
     "test_meaningless_dispositor_mirror_reason_is_gone"),
    ("#990: the Mars line says a Venus sign cancels the Manglik reading",
     _T,
     "mitigate the Manglik reading, so the reading is softened, not removed.",
     "cancels the Manglik reading, so the reading is removed.",
     "test_mars_line_gives_the_supported_reason_and_stays_a_mitigation"),
    ("#990: the Mars line drops the note that the cancellation rules are contested",
     _T,
     " The cancellation rules are themselves contested, and some authors reject them.",
     "",
     "test_mars_line_gives_the_supported_reason_and_stays_a_mitigation"),
    ("#990: Cancer Ascendant's 7th is stated as Aquarius (it is Capricorn)",
     _T,
     "Cancer Ascendant, Saturn in 7th (Capricorn):",
     "Cancer Ascendant, Saturn in 7th (Aquarius):",
     "test_every_stated_7th_house_sign_follows_from_its_ascendant"),
    ("#990: Gemini/Virgo's 7th signs are swapped (Pisces or Sagittarius)",
     _T,
     "Jupiter in 7th (Sagittarius or Pisces):",
     "Jupiter in 7th (Pisces or Sagittarius):",
     "test_every_stated_7th_house_sign_follows_from_its_ascendant"),
]
