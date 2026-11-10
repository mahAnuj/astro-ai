# muhurat.py names no book the repo does not hold, and the citation gate now scans it

- **Date:** 2026-11-10
- **PR / issue:** #716

## Why, measured

At d72ace9, `grep -c "Brihat Parashara\|BPHS\|Muhurta Chintamani\|Muhurtha Chintamani\|Phaladeepika" src/astro_ai/muhurat.py`
was 10 (a module docstring, six table comments, the Dagdha, Choghadiya and Namkaran
headers, and the Chandra Bala docstring, which also named Ashvalayana). None of those texts is in
`data/` or in `scripts/fetch_corpus.py`'s registry, and `knowledge/SOURCES.md` withdrew the bare `[BPHS]`
licence. `scripts/verify_rule_citations.py` printed PASS the whole time because it read only
`chart.py`'s `source=` labels (`grep -c muhurat scripts/verify_rule_citations.py` was 0). The
muhurat attributions were comments, which no AST check reads.

**Changed.** Every site is re-labelled in comments and docstrings only; the `ast.dump` of
`muhurat.py` with docstrings stripped is identical before and after, so no rule value moved. Where
`knowledge/*.md` already records a rule, the comment says what it records and cites that section
(`vedic_reference.md` 2A for the Chandra Bala strong houses, 29.9 for Amrit and Sarvartha Siddhi,
29.10 for Dagdha and Choghadiya, `matching.md` v.24 for the 3/5/7 Tara positions). Where it records
nothing (Tara Bala names, Ravi Yoga, the Namkaran syllable table) the comment says "Source not
held". `data/` was absent on the runner (0 of 7 books), so no new citation to a book section was
asserted; nothing was read from a book.

**Gate.** `_muhurat_problems()` scans the whole text of `muhurat.py`, comments and docstrings
included, for the `_FORBIDDEN` names plus Muhurta/Muhurtha Chintamani, Phaladeepika, Jataka
Parijata/Chandrika and Ashvalayana, case-insensitive and tolerant of a name wrapped across a comment
line. It fails closed if the file is unreadable or its anchors moved. `_UNHELD_ATTRIBUTIONS` stays
empty: there is no ledger escape for these names. Nine self-test mutations, `tests/test_muhurat_attribution.py`
and four rows in `scripts/mutations/2026_11_10_716_muhurat_citations.py`.

**Rejected / left.** "Grihya Sutras" is not scanned: it is a genre named in rendered
Namkaran copy (`muhurat.py` event `seo_desc` and `intro_paragraphs`), a user-visible claim and a
behaviour change, so it needs its own issue. The Chandra Bala weak set (omits houses 2, 5, 9 that
`vedic_reference.md` 2A lists) is #715's. Amrit Siddhi's Monday stays as coded and is disclosed as
contested (29.9). Tokens: 0, no LLM path.
