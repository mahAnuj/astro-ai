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
4. `claude-code-action` as `qa` in its prose-audit role, `show_full_output: "false"`,
   `display_report: "false"`, `--permission-mode default`, no WebFetch/WebSearch, Bash only
   for `gh issue list|view`, `gh label list`, the guard, the post script and one exact
   `date` command. It grades
   each distinct answer on six items (grounded in knowledge/, the `ask*.txt` contract,
   answers the question, safety, language, chart claims or "rules-only"), writes
   aggregates to `/tmp/measure/ask-audit.json`, and files or updates one issue per defect
   class (`astrology-correctness`, `bug`, `layer:prompt`) with a paraphrased example.
5. `scripts/ask_audit_guard.py` — deterministic, outside the model. No run of 6 words from
   a question or 12 from an answer. Every regular file under `/tmp/measure` newer than the
   sample, plus the report, is checked after the agent step and deleted on a match before
   the commit job or the summary can see it; guard exit 2 ("could not verify") deletes them
   unchecked. On a match it prints only "a user quote was found in <file>".
6. `scripts/ask_audit_post.py` — the agent's only way to post. It takes a body file under
   `/tmp/ask-work`, a title, labels from a closed list and an optional issue number; it
   runs the guard on body and title and `verify_issue_evidence.check()` on the body, and
   calls `gh` only if both pass. It always applies `provenance:outsider`. **Scoped by `gh`,
   not by the prompt (#1291):** `--issue N` is accepted only for an issue that `gh issue
   view` shows carrying the `provenance:outsider` label, the hidden
   `<!-- ask-audit-class: <class> -->` line AND an author that is this repository's own App
   (`resolve_provenance.is_self_app`, `is_bot` a real bool); a new issue must carry the line
   and is capped at 5 per rolling 24h, counted from `gh issue list --state all` on every call
   (no search index, which is eventually consistent; no process memory). Anything
   unreadable or malformed, and a full 100-row listing that never leaves the window, exits 2
   with nothing posted; every `gh` read happens before the label is created.
7. The sample is deleted in an `always()` step. It is never under `/tmp/measure`, which is
   uploaded as an artifact and committed.

**Rejected.**

- *A new job.* A job is a permissions block, which `verify_workflow_permissions.py` reads
  as a widening.
- *Writing `/tmp/report.md` as the brief first said.* This job persists that file as
  `measurements/<date>.md`, the analyst's report; the audit writes `/tmp/ask-audit-report.md`.
- *Bare `Bash` for the agent.* With Bash it could `curl` the sample anywhere, so "no
  WebFetch" alone keeps nothing in. The prompt is not the control for text an outsider
  wrote (qa.md #361); the tool list and the guard are.
- *Trusting the prompt alone to keep quotes out of issues.* The first cut of this PR still
  did: raw `gh issue create|comment` took `--body-file <any path>`, so the guard ran only
  if the agent chose to run it (QA FAIL on #1169). Those patterns are gone; the post script
  is the only route, and it runs the guard itself.
- *Letting the post script read any path.* It would then post any file the runner can
  read, `/proc/<pid>/environ` or `.git/config` included; it accepts only `/tmp/ask-work`.

**The prompt-injection path, and why the label (QA on #1169).** An outsider types an `/ask`
question; the LLM answers it; the audit agent reads both and files an issue as `claude[bot]`;
`resolve_provenance.py`'s self-app exception (owner's rulings 2026-11-01/02) answered TRUSTED
for that author, and `--apply` then *removed* any `provenance:outsider` label; so the next
cycle handed a stranger's words, one paraphrase removed, to an engineer. That is the
laundering hop the resolver's docstring already names. Two changes close it for this writer:
`ask_audit_post.py` puts `provenance:outsider` on every issue it files or comments on, and
`resolve_provenance.py` now answers OUTSIDER for a self-app issue carrying that label (Step 0a
exit 1: no engineer). The label is honoured by *presence*, unlike `provenance:trusted`,
because it can only narrow. A human with write access lifts it with a `provenance:trusted`
override, as for any outsider issue; the supported route is still to re-file the defect in
their own words. Checked live on 2026-11-17: the only issue carrying the label is #392,
closed, so no open self-filed issue becomes unworkable. *Rejected:* making the taint apply to
every author. A human-filed issue the audit comments on gets the label as a record, but the
human's own wording is what an engineer would build from, and the resolver still trusts it.

**Secrets reachable from the agent's shell (QA on #1169).** Closed, as far as the action's
documented inputs allow:
- `--permission-mode default`. v1 runs in **auto mode** unless told otherwise, where a safety
  review may approve a call no allow rule covers; its `docs/usage.md` says to opt out when a
  workflow "relies on `--allowedTools` as a strict list". This one does.
- No allowed command prints the environment: no `env`/`printenv`; `jq` (`jq -n env`) and
  `wc` (`--files0-from` echoes file contents in its errors) removed; `date` only as the exact
  `date -u +%Y-%m-%dT%H:%M:%SZ` (`date -f FILE` echoes lines too).
- Read denied on `/proc`, `/dev`, `.git`, the runner temp dir, `~/.config`, `~/.claude`.
  Writes confined to `/tmp/ask-work/**` and the two output files (no bare Write, so no edit to
  `.claude/` settings).
- The checkout's persisted `GITHUB_TOKEN` (`http.extraheader` in `.git/config`) is unset
  before the agent runs; nothing after it in the job uses git.
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB: "1"` on the step: the action's documented best-effort
  scrub of Anthropic, cloud and Actions secrets from tool subprocesses (`docs/security.md`),
  otherwise switched on only by `allowed_non_write_users`.
- `display_report: "false"` explicitly, since `@v1` floats.

**Residual risks, stated plainly.**
- `claude-code-action` has **no input to unset** `CLAUDE_CODE_OAUTH_TOKEN`,
  `ACTIONS_ID_TOKEN_REQUEST_*` or `GITHUB_TOKEN` for tool processes (checked against its v1
  `action.yml` inputs, 2026-11-17). The scrub is the documented mechanism and it says
  "best-effort"; which variables it removes was not verified. If it removes `GH_TOKEN`, the
  agent's `gh` calls fail and the audit files nothing (fails closed, visible as no issues).
  Bubblewrap PID isolation, which the action installs only with `allowed_non_write_users`,
  is not on, so the parent process's `/proc/<pid>/environ` is still on disk; only the Read
  deny rule stands between it and the agent, and Claude Code applies Read rules to Grep and
  Glob on a best-effort basis.
- The OIDC request token (`id-token: write`) stays in the job for `claude-code-action`. No
  allowed command can make an HTTP request with it.
- None of this has run in Actions: the permission rules' path syntax (`//tmp/...`,
  `Edit(...)` covering Write) is from Claude Code's documentation, not observed. If a rule
  does not match, the agent cannot write its outputs and the step reports "no report written".
- The guard misses by design: quotes under 6 words, re-ordered, encoded or homoglyph text.
- An agent that restates outside text in an issue WITHOUT the label is still trusted by the
  resolver; the label covers only writers that apply it.
- **Before #1291** `--issue N` took any number, so an injected audit agent could comment on
  and label `provenance:outsider` any issue, the loop's own included (the label alone makes
  it unworkable at Step 0a), and "at most five new issues" was a sentence in the prompt only.
  Both are now enforced in the script. What stays open: the author test trusts every identity
  in `SELF_APPS` (`claude`, `github-actions`), so a different loop writer's issue that also
  carries the label and the class line would pass, and the cap does not cover comments.
- Chart-specific claims are graded "rules-only" until slice 2 adds the snapshot to `form_ask`.

**Cost.** 0 Groq tokens: it reads stored answers and makes no app LLM call. One Claude run
a week, max 80 turns, 25-minute step cap, against the shared Max weekly window
(`measurements/claude_usage.json`); not yet measured, since it has not run.
