# Panchak starts at the third quarter of Dhanishta, not at the nakshatra

- **Date:** 2026-11-09
- **PR / issue:** #713

## Why, measured

`muhurat._PANCHAK_NAKSHATRAS` flagged the whole of Dhanishta while its comment said
"latter half". Raman, *Muhurtha* (1948) ch. IV ("Influence of Constellations", p. 26, "Nakshatra Panchaka") starts the window at
the third quarter of Dhanishta and ends it with Revati. The quotation (`data/` L1227-1235;
index "Nakshatra Panchaka 26", L8459) was first the #713 filer's transcription and was
re-read against the book on 2026-11-10 (only the OCR hyphenation "Dhani-shta" differs).

The rule is now `muhurat._is_panchak(nakshatra, pada)`: Dhanishta pada 3-4, or any pada of
Shatabhisha, Purva Bhadrapada, Uttara Bhadrapada, Revati. The pada is read from
`PlanetPosition.pada`, never recomputed (the 10-degree boundary bug in `matching._moon_pada`).

Measured with the engine, noon Moon, Delhi, 2026-11-01 .. 2027-12-31: eight days change from
flagged to unflagged, all Dhanishta pada 1-2 (2026-11-17 and 2026-12-14 among them). The
finder samples the noon Moon only; on 2026-11-17 the Moon enters pada 3 at 15:31 IST, so the
learn article now says Panchak opens that afternoon. 2026-11-17 is still "avoid", now for
Chaturmas, which the Panchak check had been hiding. The 2027-01 claims (13-15 Jan, Panchak)
are unchanged.

Rejected: leaving the set and subtracting padas 1-2 in the caller (two places for one rule).
Token cost: 0, no LLM path touched.
