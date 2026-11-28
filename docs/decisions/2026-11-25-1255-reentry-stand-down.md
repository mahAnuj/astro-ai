# A queued `issue` entry is stood down when a cycle already ran on it and nothing is new; pre-QA reads the top three failure themes

- **Date:** 2026-11-25
- **PR / issue:** #1255

## Why, measured

`measurements/loop.json`, 2026-11-12..19: 124 build cycles on 98 issues, **26 repeats**
(`python3 -c` in the issue, 124 98 26 at 084a5ce). 23 of the 26 are `kind=issue` rows started
by `agent-queue` (`cycle_queue.drain`), 3 are `ranked`. Nine of the 26 lasted under ten minutes
(about 12.0M tokens): a cycle that re-read the issue and its PR, found nothing new and stood
down. Seventeen were long (about 62.2M tokens); the one sampled (#1226 / PR #1227, a fix commit
at 20:00 and `QA: PASS` at 20:51) was a legitimate QA-FAIL fix round.

**The ceiling is 16%, not 100%.** A code stand-down can reach at most the nine short repeats,
about 12M of the 74M tokens. The issue's target of "0 extra cycles" is not reachable by it, and
the after-week measure should expect a fall of up to 9, not to 0. The 3 `ranked` repeats happen
inside the agent (project-manager ranking), which is only reachable by editing `.claude/`; that
is out of scope here (edits to it were refused in #1207, #1364 and #1469).

**Tokens:** 0 Groq tokens. No request-path LLM call.

### 1. `scripts/reentry.py`, called from `cycle_queue.stale_reason`

An `issue` entry is stood down only when ALL of these are read successfully: a `claude[bot]`
comment whose first line opens as an agent-cycle trace (`CYCLE_OPENER`; the cycle's trace,
T_last, amended 2026-11-27, #1477) on the issue or its owned PR is newer than the entry; exactly one open PR is owned by the issue; its head commit is no newer than
T_last; no `QA: PASS|FAIL` comment is newer than T_last; and the PR is not `behind`, `dirty` or
`unknown`. Anything else, or any read error, re-enters. It runs after the existing
waiting-to-merge check, so it contradicts nothing; it is #1207's unimplemented repair 2, made
precise.

- **Deviation from the issue's wording, stated.** The issue says "no new QA verdict, commit or
  main merge". "Main merge" is read as "the PR needs main merged into it" (`behind`/`dirty`), not
  "main moved". Main moves most hours, so the literal reading would make the rule vacuous.
- **The entry's own queue time is the "something new" test.** A red-gates or QA-FAIL entry is
  written after the last cycle, is newer than T_last, and always runs. Only an entry queued
  BEFORE a cycle that has since run is dropped.
- **Fail open.** A wasted stand-down costs about 35s; a wrongly dropped entry is permanent.
- **Trust.** Comment bodies and branch names are untrusted: the `jq` returns two booleans per
  comment, never a body, and the only text taken from a branch name is the issue number
  `_OWNED_BRANCH` matched. Only `claude[bot]` can be T_last; a verdict from any author blocks the
  stand-down (the safe direction).
- **Known limits.** `committer.date` is the author's clock, not the push time, so a commit made
  before T_last and pushed after it reads as old. That errs toward a wasted stand-down, never
  toward dropping a QA FAIL. (The first version also counted every non-`QA:` `claude[bot]`
  comment as a trace; see the amendment below.)
- **Cost:** about four extra `gh api` reads per drained `issue` entry, against a 1,000/hour
  `GITHUB_TOKEN` budget. The reason is written to the run summary and, by `drain`, into the
  dropped entry ("nothing new since the last cycle"), so the count of stand-downs is searchable.
- Kinds `pr`, `fix_pr` and `measure` are untouched: a QA round already drops on a ruled head, and
  a fix entry is an explicit request.

### 2. `scripts/pre_qa_check.py` THEME_CHECKS

`measurements/lessons.json` (2026-11-25), QA FAILs by theme: regression 31, grounding 30, tests
26 (copy and tokens 17). The issue's own numbers (31, 30, 29) were older. After the gates and
before pytest the script now runs, per theme, the checks that can see that class in a diff and
prints `themes: regression PASS grounding PASS tests PASS` (also to the run summary); a check that
cannot compute exits 2, never PASS.

- **tests:** code under `src/astro_ai/` or `scripts/` gained a `def` or `class` and the diff
  touches no `tests/` file; a changed mutation row whose anchor is not in its file exactly once,
  or whose test is defined nowhere (a dead row is the static form of "survived").
- **regression:** every changed `.py` parses; every changed template parses under Jinja; a
  top-level def, class or CONSTANT the diff removed (and did not re-add) that code still uses.
- **grounding, a proxy:** a claim-bearing path (`knowledge/`, `prompts/`, `templates/learn/`,
  `chart.py`, `muhurat*.py`, `matching.py`) changed with no `corpus:` line in any commit since the
  merge base and no `knowledge/*.md` change. It cannot judge whether a claim is TRUE; `qa`,
  `astro-auditor` and `verify_rule_citations` do that.

## Amendment 2026-11-27 (#1477)

**Defect:** T_last was the newest non-`QA:` comment by `claude[bot]`, but the steward, chief,
analyst and architect all post as `claude[bot]`. A fix entry queued at 10:01 right after a
`QA: FAIL` at 10:00 was stood down as "nothing new" when an unrelated `claude[bot]` comment
landed at 10:30 and the head was older, so the QA-FAIL fix never ran.

**Fix:** T_last is the newest `claude[bot]` comment whose FIRST LINE opens as an agent-cycle
trace, a regex boolean computed in `jq` (bodies still never enter Python):
`CYCLE_OPENER = '^[*# ]*(/?agent-cycle|Cycle [0-9-]+ [(]agent-cycle)'`. Openers measured on
cycle comments: `**/agent-cycle (build) picked`, `**agent-cycle (run on`,
`**/agent-cycle (2026-11-23)`, `Cycle 2026-11-23 (agent-cycle`. Steward, chief, analyst and
architect first lines (`**steward**`, `**chief**`, `## Analyst score`, `Architect plan`) do not
match, and a later line cannot match (no multiline flag).

- **Fail open.** The opener is a model-written convention, not a contract. A new phrasing
  misses, no trace is found, and the entry re-enters at the cost of one wasted cycle, never a
  dropped fix.
- **Residual, stated.** A cycle that started before a FAIL and commented after the entry was
  queued still counts as having consumed that entry: when a cycle started is not observable from
  comments. This is the same direction as before but now the only way a fix entry is dropped.

## Rejected

Editing `.claude/commands/*.md`; any workflow edit (the App token has no `workflows`
permission); standing down `pr` and `fix_pr` entries; "main moved" as the main-merge test; a
waiver flag for the pre-QA themes (YAGNI, the checks are kept narrow); a GCS or file store for
last-cycle state (the comments are the store, as the queue already does); pinning the theme list
to `lessons.json` in a test (regenerated daily, so the test would follow data drift).
