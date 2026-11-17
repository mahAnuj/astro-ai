# Saved /ask answers are audited weekly in CI, and no user's words leave the runner

- **Date:** 2026-11-17
- **PR / issue:** #1167 (slice 1 of 2)

## Why, measured

The owner, 2026-11-17: *"we have been saving questions answers, but I don't think we have
analysed those."* Every `/ask` answer is stored as a `form_ask` event (`routes/ask.py`,
`events.record`; question, category, lang, model, answer truncated to 4,000 chars, context,
cache_hit, and the signed-in user's email), kept 30 days. Measured on origin/main that day,
`grep -rln form_ask scripts/` returned nothing: no code read the answers, let alone graded
them. Volume is small (`llm-usage.json`, 7 days to 2026-11-16: 13 fresh `/ask` generations,
plus cache hits), so a week's answers can be audited in full.

The owner's decision on #1167, verbatim: *"Yes and a for 1st question"* — run it in CI,
not only from a session.

**What was built.** Steps inside agent-measure's existing `measure` job, after the analyst:

1. `scripts/ask_audit_due.py` — due when `measurements/ask-audit.json` is missing, broken or
   at least 6.5 days old. Fails open to "due".
2. `scripts/collect_ask_sample.py` — reads `events.recent(types=["form_ask"], days=7)` and
   writes `/tmp/ask-sample.json` with a WHITELIST of fields (id, ts, category, lang, model,
   context, cache_hit, question, answer, chart). Email and every other field are dropped. A
   counts-only `/tmp/measure/ask-sample-meta.json` is committed. Exit 2 when the bucket
   cannot be read, because `storage.get` turns every error into None and a quiet week and
   a 403 would otherwise look the same.
3. The bucket credentials are deleted and the three variables that point at them are
   blanked through `$GITHUB_ENV`. The auth step exports them to the whole job because
   "Pull the numbers" and the analyst's own `fetch_*.py` calls need them, so deleting the
   file alone would leave the path set.
4. `claude-code-action` as `qa` in its prose-audit role, `show_full_output: "false"`, no
   WebFetch/WebSearch, Bash only for named `gh issue` / guard / `jq` commands. It grades
   each distinct answer on six items (grounded in knowledge/, the `ask*.txt` contract,
   answers the question, safety, language, chart claims or "rules-only"), writes
   aggregates to `/tmp/measure/ask-audit.json`, and files or updates one issue per defect
   class (`astrology-correctness`, `bug`, `layer:prompt`) with a paraphrased example.
5. `scripts/ask_audit_guard.py` — deterministic, outside the model. Every issue body must
   pass it (no run of 6 words from a question or 12 from an answer, and an Evidence Block
   that passes `verify_issue_evidence.check()`), and every file the audit wrote is checked
   and deleted on a match before the commit job or the summary can see it.
6. The sample is deleted in an `always()` step. It is never under `/tmp/measure`, which is
   uploaded as an artifact and committed.

**Rejected.**

- *A new job.* A job is a permissions block, which `verify_workflow_permissions.py` reads
  as a widening.
- *Writing `/tmp/report.md` as the brief first said.* This job persists that file as
  `measurements/<date>.md`, the analyst's report; the audit writes `/tmp/ask-audit-report.md`.
- *Bare `Bash` for the agent.* With Bash it could `curl` the sample anywhere, so "no
  WebFetch" alone keeps nothing in. The prompt is not the control for text an outsider
  wrote (qa.md #361); the tool list and the guard are.
- *Trusting the prompt alone to keep quotes out of issues.* The agent is told to run the
  guard before every post, and that is still an instruction. What does not depend on the
  prompt is the file check after the step.

**What this does not cover, stated plainly.** An issue or comment the agent posts without
running the guard is not caught afterwards. The OIDC request token (`id-token: write`) stays
in the job for `claude-code-action` itself, so an agent with general shell could mint a new
cloud token; that is why Bash is narrowed rather than granted. Chart-specific claims are
graded "rules-only" until slice 2 adds the snapshot to `form_ask`.

**Cost.** 0 Groq tokens: it reads stored answers and makes no app LLM call. One Claude run
a week, max 80 turns, 25-minute step cap, against the shared Max weekly window
(`measurements/claude_usage.json`); not yet measured, since it has not run.
