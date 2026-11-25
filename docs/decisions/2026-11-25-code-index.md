# Agents look a symbol up in a generated line-range index before reading a long file

- **Date:** 2026-11-25
- **PR / issue:** #1466 (part of #1256). Siblings: #1467 (the read-log hook, which measures whether
  the rule is followed) and #1468 (the workflow half, which builds the index in `agent-work`).

## Why, measured

#1256: 93.9% of agent-work tokens are cache reads (`measurements/loop.json`,
`tokens.per_merged_pr` = 10,062,674 at filing, 91 merged PRs). Every turn re-reads the whole
context, so a `Read` of a 5,248-line `chart.py` is paid again on every later turn. An agent that
looks a function up and reads its 80 lines keeps the rest out of the cache.

So `scripts/build_code_index.py` prints a file or directory outline with line ranges
(`uv run python scripts/build_code_index.py <path>`), and with no argument writes a gitignored
`.code-index/`. The rule "Look up before you read (#1256)" is pinned in backend-engineer,
frontend-engineer, qa and architect (`tests/test_code_index.py`).

Choices and what they cost:

- **Files under 400 lines get one line.** An outline of a short file costs about as much as
  reading it. **Every index file is at most 8,000 chars** (about 2k tokens): shrink docstring text
  70 -> 40 -> 0 chars, then split into parts. Nothing is dropped, so a symbol is never missing from
  the index, only on a later page.
- **qa still reads every changed hunk and every file the claim is about.** The index finds context;
  it does not replace reading what the diff touches. **The architect keeps `ARCHITECTURE.md` a
  whole read**: a rejected proposal missed there costs a full review cycle.
- **Ranges go stale on edit**, so the rule says to re-run after editing and calls a range a pointer,
  not evidence. Every index file says so in its header.
- **"Named in" for a template is not proof of rendering.** It is a literal-string match over the
  AST; a template name built any other way shows as `no literal reference found`.
- The index starts a decorated def at its first decorator, so a range read includes the route line.

## Rejected

- **Committing the index.** It would conflict on every PR, the same reason the decision log became
  a folder (`docs/decisions/README.md`), and would be stale by the next commit.
- **`git ls-files` for the file list.** It would miss a new file the agent has just created and not yet
  added, and needs git; `os.walk` with an exclude set sees the working tree as it is.
- **Tags/ctags or a language server.** Not stdlib, no markdown or Jinja support, and nothing that
  maps a template to its route.
- **Dropping `Class.method` entries to fit the budget.** The issue says nothing is dropped; the
  split into parts costs a second page and loses nothing.
- **Indexing `tests/`.** Tests are read for the one case they pin, not browsed.
