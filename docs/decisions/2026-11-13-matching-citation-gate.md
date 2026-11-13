# matching.py joins the citation gate, with an exact ledger for Muhurta Chintamani

- **Date:** 2026-11-13
- **PR / issue:** #914 (Ask 2 only; Ask 1, the registry row, stays open)

## Why, measured

`scripts/verify_rule_citations.py` read `chart.py` (checks 1-6) and `muhurat.py` (check 7,
#716) and printed PASS while `matching.py`'s module docstring credited Brihat Parashara Hora
Shastra, a book never held in `data/` (the #216 defect), and a history note in a Nadi docstring
carried a "BPHS matching tradition" label. Check 8 scans `matching.py` whole-file, comments and
docstrings included, with the same name list as check 7. The list is filtered from
`_MUHURAT_UNHELD` rather than restated, so the two cannot drift. It fails closed if the file is
unreadable or its anchors (`compute_guna_milan`, `MATCHING_RULES_VERSION`) have moved. Both
mentions were reworded; the AST of `matching.py` with docstrings stripped is identical before
and after (`ast.dump` equal, 79,514 characters), and the suite is 4,154 passed before.

**Muhurta Chintamani is the exception, and it is deliberately narrow.** `knowledge/matching.md`
records it as held and it is the sole source of the 36-point weights, so banning the name would
ban the file's real citation. But `fetch_corpus.py` has no row for it, and a row needs a plain
line count measurable only with `data/` present. Rejected: inventing a count (an unchecked
number under a registry's authority is worse than none), and adding a row without one. Chosen: a
one-entry ledger, `_MATCHING_HELD_UNREGISTERED`, that passes the name only while (a) it is listed,
(b) the registry does not register the book, (c) `matching.py` still names it. If the registry
gains a row, or the file stops naming the book, the gate fails and says to delete the entry; a
second entry fails too. It is a temporary mechanism that closes with #914 step 1, not a
precedent for ledgering a citation to turn it green.

Tokens: 0 measured. No prompt, call or LLM path is touched.
