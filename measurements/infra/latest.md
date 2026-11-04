# infra-lead report — run of 2026-11-03 (HEAD d8decf7)

Focus: free-tier headroom, deploy truth, latency. Everything below was measured this run unless it says "read from" a committed file or "derived". Nothing in GCP, the repo, or CLAUDE.md was changed.

## 0. Summary

| # | Finding | Action |
|---|---|---|
| 1 | **The premise that the `exact` deploy tier has never run is wrong.** `/health` serves `build_sha` equal to HEAD, and the last runs I read show exact-tier passes. | None needed GCP-side. Comment added to #340. |
| 2 | **New, filed as #698:** `agent-work`'s cycle step has no `GH_REPO`, so the agent runs `gh repo view`, which `Bash(gh repo:*)` denies. Three cycles died in under 90 s in the last day and each produced a red `Agent queue` run. | #698 (needs `chief`: it edits `.github/workflows/`). |
| 3 | Groq is the ceiling that binds, as before. Natal worst case is 6,751 input tokens against 8,000 TPM. Input-token arithmetic puts the daily natal ceiling near 43 uncached reads/day. Real demand is about 1/day. | No new issue. See §4. |
| 4 | Latency: nothing slow. 0.55–0.64 s on the main pages, with a 0.34–0.38 s floor from this runner to a 96-byte `/health`. | None. |
| 5 | I could not read Cloud Run, GCS or Cloud Build. The credential is `agent-analytics@`. | Already tracked in #568. |

## 1. What I could not do, and why

- **No trigger export, so no GCP change.** `gcloud beta` is not installed and cannot be installed non-interactively. The GA command `gcloud builds triggers list --region asia-south1` and the global variant both returned `PERMISSION_DENIED` for `agent-analytics@bhagya-500701.iam.gserviceaccount.com`. `gcloud run services list` and `run revisions list` were denied as well. I did not try to widen the account's permissions. #568 already records that this account holds no Cloud Build, Cloud Run or Scheduler roles.
- **No before-and-after trigger diff exists, because there was nothing to change.** The brief authorises setting `BUILD_SHA`, and production already has it (§2). Editing the trigger would have been a change with no purpose, made without being able to export first.
- **No CLAUDE.md edit.** It is instructed only for a GCP change, and there was none. Its existing `BUILD_SHA` paragraph (set 2026-10-08, `--update-env-vars`) matches what I observed. The trigger's `ignoredFiles: measurements/**` was not touched, and I could not read it this run.
- **Cloud Run and GCS usage against the free tier could not be read** (no `run.*` or monitoring access). Where a Cloud Run figure appears below, it is derived from GA4 and labelled so.
- **I did not POST `/kundli` or call any LLM-backed route.** A natal call spends about 6.8k tokens of the shared Groq budget, and I cannot learn anything from it that §4 does not already give.

## 2. Deploy truth — the `exact` tier is live

| Evidence | Value |
|---|---|
| `curl https://shubhagya.com/health` (this run) | `{"ok":true,"revision":"bhagya-00572-gd7","build_sha":"d8decf71df9e5de988717922dad067e3f2956858"}` |
| `git rev-parse HEAD` | `d8decf71df9e5de988717922dad067e3f2956858`, identical |
| run 41717568381 (2026-11-03 20:59Z, workflow_dispatch) | polled `try 1..N: serving build_sha 6b7a2fa, want d8decf7`, then `DEPLOY GATE: exact — build_sha d8decf7 matches this commit (revision bhagya-00572-gd7), after 22 tries` |
| run 41685750590 (2026-11-03 17:35Z, push) | `serving build_sha e03e78c, want 6f15619`, then `DEPLOY GATE: exact — build_sha 6f15619 matches … (revision bhagya-00570-psb), after 22 tries` |
| runs 41521817998, 41454162701, 41491351147 | the same `serving build_sha <previous>, want <this>` pattern, with a different SHA each time |

The SHA moves with every deploy, so it is the commit and not a constant. The 15 most recent `verify-production` runs are all `success`.

**This premise has now been stale across at least two briefs.** The 2026-10-13 infra report said the same thing. The brief for this role should drop "has NEVER run". I cannot edit `.claude/`, and I cannot confirm where the brief text lives.

**Still wrong in the tree, so #340 stays open** (commented this run, https://github.com/mahAnuj/astro-ai/issues/340#issuecomment-6618639640). `verify-production.yml` at HEAD still says, at line 20, `REVISION-CHANGED (what runs today — build_sha is null)`. It also prints `--set-env-vars=BUILD_SHA=$COMMIT_SHA` at lines 27, 207 and 838. CLAUDE.md says `--set-env-vars` replaces the whole environment, Groq keys included. Anyone following the workflow's own advice would wipe production's env. This needs `chief` or a human push, since the App token has no `workflows` permission.

**#341 (gate waits ~12 min for a SHA a `measurements/`-only push can never deploy) was not re-tested this run.** Every run I read was a code commit or a dispatch against one.

## 3. GitHub Actions

Runs created after 2026-11-02T21:00Z, from `gh run list --limit 200`:

| workflow | runs | failed | cancelled |
|---|---|---|---|
| Agent merge | 61 | 0 | 0 |
| PR gates | 23 | 0 | 4 |
| verify-build / QA on green / Report a red main | 23 each | 0 | 0 |
| Agent queue | 11 | **4** | 0 |
| Agent work | 13 | 0 | 1 |
| Agent steward | 6 | 0 | 0 |
| verify-production | 6 | 0 | 0 |
| Close on production evidence | 6 | 0 | 0 |
| Agent measure | 3 | 0 | 0 |
| Loop outcomes | 1 | 1 | 0 |

- **`Agent queue` ×4 red (18:51Z, 18:52Z, 10:54Z and 10:55Z runs): one root cause, filed as #698.** The carrier reports `agent-work run <id> concluded 'success' within 90s of dispatch … did not run a cycle`. For run 41698210139 (issue #431) the first Bash call was `permission_denied` with `decision_reason_type: "rule"`. The command contained `gh repo view`, and `--disallowedTools` has `Bash(gh repo:*)`. The cycle step's `env:` sets only `GA4_PROPERTY_ID` and `GSC_SITE_URL`. `GH_REPO: ${{ github.repository }}` is on three other steps but not that one, so the agent improvises. Across 13 completed `agent-work` runs, 11 logged at least one `permission_denied`, and 10 of those include a denied command containing `gh repo`. Three runs ended in 90 s or less with such a denial (41698210139, 41623463054, 41623227784). The fourth fast red queue run, 41697899251 (89 s), had **no** denial, so it has a different cause that I did not find.
- **`Loop outcomes` is red by design.** It exits 1 when a loop is BROKEN and posts to #444. It has been red on 5 of its last 5 runs (the earliest is the 2026-10-11 dispatch). The 2026-11-03 report says 2 BROKEN and 2 UNKNOWN. One BROKEN item is "33 of 57 agent-work runs produced no merged PR", to which #698 is a concrete contributor. #444 is open and current, so I did not duplicate it.
- **`PR gates` cancelled ×4 and `Agent work` cancelled ×1 (run 41629198490, 1 h 13 min)** were not investigated this run. Earlier reports attribute PR-gates cancellations to the concurrency group superseding itself. That is unverified for these four.
- **Actions cost.** `measurements/cost.json` (read from file) records GitHub Actions as $0 and the repo as public. CLAUDE.md's "2,000-minute monthly allowance" is the private-repo figure and is stale, as the 2026-10-13 report already flagged. I did not re-verify billing this run.
- **The binding loop resource is Claude's weekly window, not Actions.** Read from `measurements/claude_usage.json` (generated 2026-11-03T20:28Z): `seven_day` 0.72 at the latest reading, `five_hour` 0.05, `rejected_runs` empty. The seven-day window resets at epoch 1793944800, which I did not convert to a clock time. Every dispatch that dies in under a minute still spends a session on this subscription, which is why #698 matters more than its size suggests.

## 4. Groq — the ceiling that binds first (#266, #212)

Measured this run offline, with zero LLM calls: `uv run python scripts/measure_natal_request.py` and `scripts/verify_token_budget.py`. tiktoken `o200k_base` is a proxy for gpt-oss's encoding, off by a percent or two. It counts the two messages only and excludes completion and chat-template scaffolding.

| | tokens (en) |
|---|---|
| natal system prompt | 3,083 (fixed on every request, 46% of the worst call) |
| worst natal chart (`cancer-lagna-manglik-exempt`) | **6,751** total (user 3,668), headroom +1,249 against 8,000 |
| best natal chart (`manglik-uncancelled`) | 6,432 |
| natal system prompt on 2026-10-13 / worst total | 3,111 / 6,798 (now −0.9% / −0.7%) |

`verify_token_budget.py` exits PASS: 13 paths inside their recorded budget, with growth against baseline of at most +3.1% (`ask+matching`). Its own printed reserve line is the number to read:

- **Reserved against the 7,400 TPM bucket on natal: en 7,875, hi 8,060, headroom −475 and −660.** Per-request reserve includes the scaffold and an 800-token completion reserve. `providers.py` clamps a reservation to the bucket cap, so such a request is admitted rather than waiting forever. It is therefore not a hang. The consequence is that **a natal call consumes a whole model-minute**. The gate still says PASS because it judges the ceiling on message size, not on this line.
- **A question I could not settle without spending tokens:** whether Hindi natal at an estimated 8,060 is refused by Groq as too large (413) and falls through to the paid `openai` end of the chain. #266 was closed 2026-10-21 on two probes that do not state a language. I am not filing this. It is a hypothesis resting on an estimate that includes a guessed completion reserve. One dated production sample of a Hindi chart, with the provider that answered, would settle it.

**Ceiling, usage, multiple, move, free-tier status**

- **Per-minute (TPM) ceiling.** 8,000 per model; `groq120,groq20` gives two natal reads per rolling minute. A third in the same minute has no bucket. Current demand is far below this on its own. The realistic collision is a kundli landing during the daily rashifal batch.
- **Daily (TPD) ceiling.** 200,000 per model, which CLAUDE.md records as observed. The rashifal job is 12 rashis × 2 languages = 24 calls. At the gate's `rashifal_single+payload` figures (4,186 en and 4,385 hi), that is **about 102,900 input tokens/day, or 51% of `groq120`'s TPD**, before completion tokens (not measured). Left for natal on input tokens alone: `groq120` about 97,100, which is 14 reads, plus `groq20` 200,000, which is 29 reads, assuming `groq20` also holds 200,000 and takes none of the rashifal overflow. That is **about 43 uncached natal reads/day**, an upper bound.
- **A discrepancy to note, not an issue.** CLAUDE.md quotes about 3,330 input tokens per rashifal call. The gate's measurement with one golden payload is 4,186–4,385. The two measure different things (the gate is system prompt plus a fixture payload), but the 3,330 should not be used for new capacity work.
- **Current demand, read from `measurements/ga4.json`.** 489 sessions over 2026-10-04..2026-10-31, which is 17.5/day. Only 22 of them landed on `/kundli` (12 + 10 across two rows), about 0.8/day. The 28-day daily series ending 2026-10-11 averages 10.1/day with a last-7-day mean of 13.0, so traffic is rising. Repeat charts come from the natal cache and cost 0.
- **Traffic multiple at which it breaks.** Against realistic kundli demand (0.8/day) the daily ceiling is about **55×** away. If every session were a unique kundli, which is a hard upper bound (17.5/day), it is about **2.5×**. TPD binds before TPM.
- **Proposed move.** Nothing new this run. The cheap structural moves from the 2026-10-13 comment on #266 still apply, in order: shrink the 3,083-token fixed natal system prompt, order the prompt so the shared prefix comes first, and watch the gate's reserve line. All of them stay inside the free tier. Do not add `groq` alongside `groq120`, and do not add `groq_qwen` (CLAUDE.md's measurements stand). I did not verify any new model's existence.
- **#212** (rashifal prompt growth): the gate now measures it per route, with growth against baseline at most +3.1% and the five-percent growth allowance holding. That is the instrument the issue asked for. I did not re-measure the specific 18.5% regression, and I do not close issues.

## 5. Latency (curl from the GitHub runner, 3 samples each, this run)

| route | status | total | size |
|---|---|---|---|
| / | 200 | 0.55–0.63 s | 152 KB |
| /kundli | 200 | 0.57–0.61 s | 140 KB |
| /matching | 200 | 0.55–0.60 s | 135 KB |
| /numerology | 200 | 0.57–0.64 s | 128 KB |
| /panchang | 200 | 0.55–0.61 s | 135 KB |
| /learn/ | 200 | 0.74–1.08 s | 278 KB |
| /health | 200 | 0.34–0.38 s | 96 B |

- Your probe's `/learn 307` is the missing trailing slash redirecting, not a fault. `/learn/` returns 200.
- A 96-byte `/health` costs 0.34–0.38 s, which is the network floor from this runner, so server time on the page routes is about 0.2 s. `/learn/` at 278 KB is the slowest page and still under 1.1 s.
- **Not measured:** natal generation latency (the 26 s figure) because it needs a POST that spends Groq tokens; cold-start latency under `--min-instances 0`; any browser-side timing.
- **Cloud Run free tier, derived and not read.** HTML is `no-store`, so every page view reaches Cloud Run. From GA4, 17.5 sessions/day at roughly four pages a session is on the order of 70 page requests/day. Against the published 2,000,000 requests/month free tier that is about 0.1% before bots, static files and crawlers, which I could not count. The stated multiple is therefore a floor on the real headroom question and not a measurement. I did not read CPU-seconds or GCS operations either, so I make no claim about those.
- **Service worker (#253).** I did not re-test it in a browser; #253 is closed and I have no new evidence either way.
- **#232** (twelve concurrent rashifal reads become twelve GCS calls) is closed as of 2026-10-31. I did not re-measure it.

## 6. What needs a human or `chief`

1. **#698**, a one-line workflow edit adding `GH_REPO: ${{ github.repository }}` to the `claude-code-action` step's `env:`. It is `chief`'s to rule on because it touches `.github/workflows/`. No new scope or permission is involved.
2. **#340**, the stale `verify-production.yml` header and its `--set-env-vars` advice. Same route.
3. **#568**, so a future infra run can export the trigger and read Cloud Run. Without it the 'before-and-after' requirement for a GCP change cannot be met unattended, and this role cannot do the part of its remit that GCP touches.
4. Housekeeping: `git remote -v` in this environment prints the push URL with an embedded `x-access-token`. I did not copy it anywhere. It appears in this run's tool output.
