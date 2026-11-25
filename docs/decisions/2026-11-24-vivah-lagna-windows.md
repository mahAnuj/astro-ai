# Vivah rows show lagna windows computed from the sky, as a note that never touches the day rating

- **Date:** 2026-11-24
- **PR / issue:** #1026

## Why, measured

Rao's wedding guideline names a lagna "Benefic planet owned" and says "The 7th house should be
clean" (`knowledge/grahas.md` section 12.5). The finder rated the day and said nothing of the
hour. The astro-auditor ruled how to read that, and this change transcribes the ruling:

- Benefic-owned lagna: Taurus, Libra, Sagittarius, Pisces always; Cancer only while the Moon is
  waxing at that instant (elongation 0 to 180); Gemini and Virgo only while Mercury shares its
  sign with no malefic. The malefic set for that test is Sun, Mars, Saturn, Rahu, Ketu and the
  waning Moon, per `knowledge/vedic_reference.md` section 4.7. `grahas.md` section 2 omits Saturn
  from its extraction of the same Rao passage; section 4.7 is the conservative reading (fewer
  Gemini and Virgo windows), so it is the one used.
- A 7th house is clean when none of the nine bodies, Rahu and Ketu included, is in the sign
  opposite the lagna. That is this finder's own minimal reading, and the page says so. Aspects to
  the 7th are not considered because the sources held do not say whether they count. Rahu is the
  true node (`chart.PLANETS`), Ketu is Rahu plus 180 degrees. "Joined" is read as the same sign.
- Shown only on Vivah rows rated excellent, good or acceptable, with an ordinary sunrise. It is a
  note: the day rating is unchanged (`muhurat.py` is not edited and does not import the new
  module; a test pins both), a window is never removed or ranked by Rahu Kaal, and the copy never
  calls a window auspicious, safe or recommended. The ruled caveat, the none-met sentence and the
  benefic disclosure are constants in `muhurat_lagna.py` and pinned verbatim by tests.
- Windows are found, not tabulated: lagna sign on a 10-minute grid and the slow state (each
  body's sign, waxing or waning) on a 3-hour grid, every change bisected to one second, the
  predicate read once per piece. Rounded INWARD to the whole minute, the opposite of the Bhadra
  window, because this states a qualifying span and must never claim a minute that does not
  qualify. A lagna change splits a window, since the page names the lagna.
- Computed per rendered row through a Jinja global (`muhurat_lagna`, `muhurat_lagna_legend`, the
  `_muhurat_why` pattern) behind an `lru_cache` keyed on date and place, so only the rows shown pay.
  A failure renders nothing; it never renders the none-met sentence, which is a claim about the sky.

Cost, measured 2026-11-24 at New Delhi: `find_candidates` for 365 days takes 1.83 s and has 34
auspicious-rated rows with a sunrise. The windows cost about 4 ms a day cold (a 5-minute scan of
the whole predicate cost 26.4 ms a day, 0.90 s for the 34 rows, +49% on the search, and was
rejected), 0.011 ms a day warm. LLM tokens: 0 per call and per day. GCS operations: 0. No paid
service.

Rejected: a `lagna_windows` field on `MuhuratCandidate` or a registry entry in
`muhurat_factors.py` (computes all 365 days, and the registry explains what moved the rating,
which this must not); a fixed lagna-start table per city (wrong at other latitudes, silently);
`chart._NATURAL_BENEFICS` (counts Mercury and the Moon unconditionally, weaker than Rao); an LLM
to word or compute it; a new `/muhurat/vivah/lagna` page (CLAUDE.md forbids a parallel page type).

Not done here: the templates (step 2, the frontend dispatch), windows on the landing page, and
Abujha rows (they follow the rating, as ruled; #1346 changes what rating they get).
