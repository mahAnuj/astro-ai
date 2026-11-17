# /learn/gochar-2027 states only swisseph-computed dates, and `verify_learn_article_dates.py` gained a transit gate

- **Date:** 2026-11-17
- **PR / issue:** #1071

## Why, measured

`gochar-2026-planetary-transits` (1,627 impressions, position 5.7 in the 2026-10-16..11-12 window)
cannot rank for `gochar 2027` queries. The 2027 sibling is a static template and registry entry
with no `llm_summary` (so no natal-prompt growth) and no runtime LLM call: 0 Groq tokens.

Every ingress and station it states was computed through `chart._sid_calc_ut` (Lahiri, IST), never
recalled. Measured 2027 sky: Jupiter Leo to Cancer 25 Jan, to Leo 26 Jun, to Virgo 26 Nov; Saturn
Pisces to Aries 3 Jun and back to Pisces 20 Oct; Rahu and Ketu change sign **zero times** in 2027 on
either node (true node into Sagittarius 24 May 2028, mean node 24 Jun 2028), so the page says so
instead of inventing a Rahu-Ketu story. The dates gochar-2026 already stated for 2027 agree to the day.

Per-sign readings use only the section 2A Gochara table (house from the Moon, verdict by house, no
dignity adjustment) and house themes from `knowledge/houses.md`. Saturn phases are described by
position, as `vedic_reference.md` 2.7.3 requires: Sade Sati by the sign before, on and after the Moon;
Kantaka and Ashtama are labelled modern usage.

`verify_learn_article_dates.py` reported every gochar-2026 ingress date as UNCHECKED, because its
sources answer "what date is this festival", not "when does Saturn enter Aries". **Gate 5** checks
every date string in a `gochar-*` article (range endpoints included) against an ephemeris event
within one day. Rejected: widening `_attribute` (ARCHITECTURE 10, already rejected for yearless
dates) and typing the dates into a registry (the #141/#146 shape). Known limit: Gate 5 is set
membership, so a wrong date that lands on another real event passes it; `tests/test_gochar_2027_claims.py`
pins each date to its named event.
