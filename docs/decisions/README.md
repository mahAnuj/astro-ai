# Decision log — one file per decision

**Check here, and in `ARCHITECTURE.md` §10, before proposing a change.** §10 holds every
decision up to 2026-11-09 and is frozen; everything after lives here.

## Why a folder and not a table

Until 2026-11-09 every change appended a row to the table in `ARCHITECTURE.md` §10, as
`CLAUDE.md` required ("update it in the same commit"). So any two open PRs edited the same
lines of the same file and conflicted by construction. On 2026-11-09 alone, #809, #810,
#811, #812 and #804 each went "conflicting" on that file the moment another PR merged, and
each needed `main` merged in by hand. The owner: *"I think we need to make PRs without the
requirement to update a common file at one place that could lead to conflicts."*

The mutation table had the same problem and the same fix (`scripts/mutations/`, one file
per area, since 2026-11-03). Two PRs that add two files never conflict.

`tests/test_decision_log_frozen.py` fails if a row dated after 2026-11-09 is added to the
§10 table, and checks every file here is named and shaped as below.

## How to add one

Create `docs/decisions/YYYY-MM-DD-<short-slug>.md` in the same commit as the change:

```markdown
# <The decision, in one line>

- **Date:** YYYY-MM-DD
- **PR / issue:** #NNN

## Why, measured

What was observed, with the numbers. What was rejected, and why. The source, if the
decision is about astrology.
```

One decision per file. A later decision that reverses an earlier one gets its own file and
names the one it replaces; never edit an old file to say something it did not say then.

Reading them newest first: `ls -r docs/decisions/*.md`.
