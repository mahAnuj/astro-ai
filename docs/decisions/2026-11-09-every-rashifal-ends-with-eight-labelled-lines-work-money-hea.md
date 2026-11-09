# Every rashifal ends with eight labelled lines: Work, Money, Health, Family, In a relationship, Married, Students, Single and looking to marry

- **Date:** 2026-11-09
- **PR / issue:** #815

## Why, measured

Owner: lines for "students, married, in relationship, bachelors looking to marry", and AstroSage's coverage (health, wealth, family, love, occupation, married life). Each line is told the karaka verdicts it must agree with, in the gochara block. Work, Money and Health reuse `_AREA_KARAKAS`; `chart._READER_GROUPS` adds Family (Moon, Venus: the 4th house's mother/mind and home-comfort karakas, Venus also the 2nd's family comfort) and Students (Mercury, Jupiter: Rao's learning karakas, houses.md:544); the three partner lines share the 7th house set, because no source gives a separate karaka for courtship, and differ only in who they speak to. Rao gives no exam pass/fail rule, so the prompt forbids predicting an exam result or a wedding. The prose drops to 80-130 words and keeps the rotating shape; the lines always appear, in a fixed order and Hindi labels for Hindi. `publish_rashifal.py` refuses a reading missing any line (`rashifal_quality.missing_reader_lines`) and its word cap rises 220 -> 330. Cost, measured: system prompt 3,017 -> 3,160, full request hi 4,692 (budget rows raised with the reason), `rashifal_single` completion reserve 500 -> 750; the full request still reserves hi 6,707 of the 7,400 TPM bucket. Groq pays it only on the fallback path.
