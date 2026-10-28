# infra-lead report — 2026-10-27

Focus: free-tier headroom, deploy truth, latency. Read-only on code. **No GCP change was made** (see §1: I could not read the trigger, and the change I was asked to make was already in place).

Labels used below: **MEASURED** = produced by a command this run. **RECORDED** = a figure from a repo file or an issue that I did not re-measure. **UNVERIFIED** = could not be checked.

## Headlines

1. **The `exact` deploy tier is not "never run". It is the only tier running.** `BUILD_SHA` is on the service and every `verify-production` run I read since 2026-10-21 passed on `exact`. The brief's premise is stale; the tree's text is stale in the same way (#340).
2. **I could not read the Cloud Build trigger, Cloud Run or Cloud Scheduler.** The service account `agent-infra` authenticates as (`agent-analytics`) is denied all three. Export-before-edit cannot be satisfied, so I changed nothing. Filed as **#568** (needs a human).
3. **New finding, filed as #567.** `rashifal-generate`'s cron has a 3 h margin to the Groq fallback and GitHub's cron lag exceeded it on 1 of 3 runs. On 2026-10-27 both languages published after their `warm-rashifal` slots.
4. Of the four "standing" issues, two are already closed (#266, #253), one is functionally resolved (#232), and one has its named gap closed by an instrument (#212). Details in §3.
5. Production is healthy and fast right now: every route 200, ~0.5 s warm.

---

## 1. Deploy truth — BUILD_SHA

**MEASURED**
- `GET https://shubhagya.com/health` -> `{"ok":true,"revision":"bhagya-00518-8zz","build_sha":"fcd2e092194426d240e3023756f193e8a59eefec"}`, taken twice this run (probe file, then my own curl). `build_sha` is non-null.
- `fcd2e09` is "#475 Phase 3 … (#565)", dated 2026-10-28 02:22 +0530 (= 2026-10-27 20:52Z). `git log -- src pyproject.toml uv.lock README.md Dockerfile` lists it as the newest commit touching anything the Dockerfile copies. HEAD `19b8f2e` is measurements-only and produced no build — consistent with `ignoredFiles: measurements/**` still being in force (inferred from behaviour; I could not read the trigger).
- `verify-production` runs, final gate line:
  - `40581840674` (fcd2e09): `DEPLOY GATE: exact — build_sha fcd2e09 matches this commit (revision bhagya-00518-8zz), after 20 tries`
  - `40555319572` (233440f): `exact … after 22 tries`
  - `39637008475` (d12494d, 2026-10-21): `exact … after 38 tries`; also `39645143028`, `39650183990` exact.
- Every earlier run I opened shows `serving build_sha <old sha>, want <new sha>` during the poll — i.e. the field is populated and compared per commit.

**What this means.** A green `verify-production` now proves *this commit* is what is serving, as the file's header always said it could. Nothing needs setting on the trigger.

**Stale text in the tree** (all in #340; I added this evidence there and on #282, closed neither):
- `verify-production.yml` lines 20-28, ~207 and ~826 say the tier "runs today" as revision-changed and tell the reader to add **`--set-env-vars=BUILD_SHA=$COMMIT_SHA`**. `--set-env-vars` replaces the service's whole environment (the Groq keys with it). `deploy.sh:20` and CLAUDE.md both say `--update-env-vars`. Anyone following the in-tree text during a regression would wipe production's environment.
- `README.md:252` says `deploy.sh` passes secrets via `--set-env-vars`; `deploy.sh:81` uses `--update-env-vars`.
- CLAUDE.md still says revision-changed is "the tier every run has used so far".

**Not done / could not do.** I did not export the trigger (denied; `gcloud beta` is also not installed on the runner, so the command in the prompt would stall on a component install even with permission). Nothing was edited, so there is no before/after to report and CLAUDE.md was not touched for a GCP change. The trigger's `ignoredFiles: measurements/**` is unread this run — **do not treat it as re-verified**.

## 2. GCP access — #568

`gcloud builds triggers list` (regional and global), `gcloud builds list`, `gcloud run services list`, `gcloud scheduler jobs list`, `gcloud projects get-iam-policy` — all `PERMISSION_DENIED` as `agent-analytics@bhagya-500701`. #280 ("gcloud is granted and unusable") was closed when the auth step was added; the step works but the identity has no roles. Ask in #568: viewer-level roles first; a separate service account if trigger-editing is ever wanted. **IAM is the owner's call and I did not try to work around it.**

Consequence for this report: Cloud Run `maxScale`/`minScale`, request counts, CPU-seconds, GCS operation counts and the Cloud Scheduler times are all **UNVERIFIED** — I have only the RECORDED `maxScale 5` (`ARCHITECTURE.md:94`) and the scheduler times in `ARCHITECTURE.md:117-118`.

## 3. Headroom — ceiling, usage, break multiple, move, free tier?

Traffic baseline, **RECORDED** (`measurements/latest.md`, GA4, window 2026-09-27..10-24, written today): **397 sessions / 28 days = 14.2/day**; `/kundli` landings **22** (0.8/day). The analyst notes the exports exclude the last 3 days and that some Direct traffic may be the owner/agents.

### 3a. Groq natal request (#266, closed 2026-10-21)

- Ceiling: 8,000 TPM per model; the gate budgets a 7,400 bucket (RECORDED in `verify_token_budget.py` output); 200,000 TPD per model (RECORDED, CLAUDE.md).
- **MEASURED** (`scripts/measure_natal_request.py`, `verify_token_budget.py`, tiktoken `o200k_base`, a proxy): natal worst fixture **6,757 tokens** (system 3,083 + user 3,674), best 6,438. Gate-reserved incl. scaffold + completion reserve, *unshed*: **en 7,872 / hi 8,057 against 7,400 — headroom −657.** So an unshed natal does not fit one model-minute. It works in production because the shed ladder drops optional blocks (the #266 history); I did not verify the shed outcome this run.
- Break multiple, arithmetic on the numbers above (completion not counted, so optimistic):
  - **TPM:** burst-driven, not volume-driven — about one natal per model per minute, two across `groq120,groq20`. A third inside a minute has no bucket.
  - **TPD:** 200,000 / 6,757 ≈ 29 natals per model, ≈ **59/day across both**, *if* the nightly rashifal path costs the Groq budget nothing. Against 14.2 sessions/day as an upper bound (every session a distinct uncached chart) that is **≈ 4.2×**; against actual `/kundli` landings (0.8/day) ≈ 70×. The natal cache (SQLite + GCS) makes repeats free, so reality is nearer the second figure. On a day the rashifal fallback fires, ~40k tokens/language of TPD go first (RECORDED 12 × ~3,330 each, not re-measured), cutting the 59.
- Move: none needed now. The structural options remain the cheap ones already listed on #266 (shrink the 3,083-token system prompt, which is 46% of every call; find out whether Groq's cached tokens count toward TPM/TPD — **#475 Phase 1b's verdict is still pending**, `ARCHITECTURE.md` 2026-10-25). All inside the free tier. A third model is a human decision.
- **Not measured:** I did not POST `/kundli` — it spends ~6.7k of the shared bucket for no new information; the 503 rate in production is therefore not re-measured. #266's 10-21 closing probe (two distinct charts, no 503) is the latest evidence.

### 3b. Prompt growth (#212)

- **MEASURED** `verify_token_budget.py`: PASS, 13 paths inside their recorded budget. `rashifal_single` system **2,874** (baseline 2,874, +0.0%), headroom 344; with payload 4,133 (headroom 268); `natal` 3,083 (−0.9% vs baseline 3,111); `natal+payload` 6,757 (headroom 111 under its 7,000 ceiling — the tightest row).
- #212's complaint was that nothing measured per-request tokens. At the system-prompt level something now does (#400, in the `verify_*` sweep). Runtime per-route/per-model tokens exist on `/admin/ops` (#473/#475) but I cannot read it from here. The issue's own last comment says to keep it open; whether to close it is `/prioritise`'s call. **The tightest row, `natal+payload`, has 111 tokens of headroom — one more optional block in the payload and the gate goes red, which is the gate working.**
- Shape change worth knowing: the daily rashifal now comes from the nightly Claude job (#515), with Groq as the fallback, so the 24-calls/day TPD pressure that caused the 2026-08 outage only returns on fallback days (see §4).

### 3c. Twelve concurrent rashifal reads (#232)

- **Code read, concurrency NOT exercised.** `rashifal_derive.derive_single_reading` checks `daily_cache` tier-0, then `_durable_get` (GCS) only on a miss, negative misses held 30 s, then writes the blob back to tier-0 and derives the section. That is the memoisation #232 asks for. Residual: N simultaneous first requests on one cold instance each do their own GCS read — bounded by (cold instances ≤ 5, RECORDED maxScale) × (lang) per day.
- At 14.2 sessions/day that residual is immaterial; I have no GCS operation counts (access denied) so no break multiple can be stated. **Move:** none. Candidate for closure by `/prioritise` with the residual stated; I did not close it.

### 3d. Service worker (#253, closed 2026-10-20 by `close-on-evidence`)

- **MEASURED live:** `https://shubhagya.com/static/sw.js` has `CACHE_VERSION = 'bhagya-v4'`, a `res.ok`/opaque check before `cache.put` (line 59), and a `no-cache` background revalidate under `waitUntil` (lines 89-97). The home page links `app.css?v=ad4efc16`. `sw.js` is served `cache-control: public, max-age=300`, ETag set, `x-cache: HIT` — the worker file itself is not pinned for weeks. Fix confirmed in production. Gap stated in the issue still stands: no gate executes `sw.js` and no real-browser test was run.

## 4. The nightly rashifal job vs. GitHub cron lag — #567 (new)

- Design (`rashifal-generate.yml` header): cron 22:00Z, `warm-rashifal` 01:00Z, `send-daily` 01:30Z. Margin 3 h.
- **MEASURED** scheduled-run lag: 2 h 08 m (10-25 00:08Z), 1 h 58 m (10-25 23:58Z), **3 h 19 m (10-27 01:19Z; last job finished 01:22:47Z)**. The same week, scheduled `Agent work` ran a median 199 / max 369 min late (n=15) and `Agent measure` a median 111 / max 192 min late (n=41).
- 1 of 3 runs published after the documented warm slots (en 01:00Z, hi 01:15Z). **UNVERIFIED:** whether Groq actually generated that morning — Cloud Scheduler is unreadable and `/admin/ops` is not reachable from here.
- Proposed (in #567): cron earlier and off the hour, e.g. `7 20 * * *`; free-tier-neutral (no Groq tokens; Claude Max is flat). Open question left to Engineering: the shared Claude 5 h cap window. Workflow files are on the `needs-human-review` boundary.

## 5. Latency (MEASURED, curl from the runner, 3 tries each)

| route | status | total (s) |
|---|---|---|
| `/` | 200 | 0.50-0.51 |
| `/kundli` (form page, no saved chart: 139,784 B = the landing view) | 200 | 0.55-0.57 |
| `/matching` | 200 | 0.49-0.51 |
| `/numerology` | 200 | 0.56 |
| `/panchang` | 200 | 0.50-0.58 |
| `/muhurat` | 200 | 0.48-0.50 |
| `/festivals` | 200 | **1.15** first, then 0.63-0.64 |
| `/learn/` | 200 | 0.65-0.71 (`/learn` -> 307 -> `/learn/`, 0.31 s) |
| `/rashifal/aries` | 200 | **0.98** first, then 0.50-0.56 |
| `/health` | 200 | 0.28-0.34 |
| `/static/sw.js`, `app.css` | 200 | 0.35 or 0.015 (edge hit alternating) |

- Nothing is slow on the pages I probed. The only outliers are first hits on `/festivals` (1.15 s, 314 KB) and `/rashifal/aries` (0.98 s) — consistent with a cold in-process cache, 3 samples each, no more than that.
- **Not measured:** LLM-backed misses. #355 recorded an average ~40 s cache-miss in production (RECORDED); the "26 s kundli" in the role brief is from earlier testing. I did not generate a reading (spends the shared Groq bucket). That remains the real latency exposure and the reason for the cache-first design.
- `/learn` redirecting with a **307** (temporary) rather than 301 is Engineering's/SEO's to judge; noted, not filed.

## 6. GitHub Actions

- **MEASURED** (`gh run list --limit 1000`, 7 days from 2026-10-20 23:00Z): 810 runs, ~4,300 wall-clock minutes (an upper bound, not billed minutes). `PR gates` 156 runs / ~1,485 min; `Agent work` 32 / ~1,418; `verify-build` 198 / ~924; `verify-production` 31 / ~178.
- **CLAUDE.md's "2,000-minute monthly allowance" is stale.** `measurements/cost.json` records Actions at $0 on a public repository, "unlimited since 2026-10-12 (#338)". I could not query repo visibility directly (`gh repo view` was denied in this run), so this rests on that RECORDED row and CLAUDE.md's own "the repo is public" (#354). On that basis minutes are not a ceiling that binds. Noted in the #340 comment.
- Failures in the last 48 h read from logs: `Agent measure` 40420746687 and `Agent discover` 40420451019 (10-26 ~23:35Z) — GitHub returned `remote: Internal Server Error` on the push and then `could not enable auto-merge … needs a hand`. Transient; **no `measurements/*` branches or open PRs remain** (checked). `Agent work` 40274940597 died at exit 143 after ~3 min (runner/SIGTERM). Open PRs now: 564, 556, 552, 550, 549, 544 — all the code loop's; four are `qa-fail` drafts, 549 is `needs-human-review` + `qa-pass`.
- Observation, not mine to fix: `loop-outcomes` (run 40479276729) reports 29 of 32 `agent-work` runs produced no merged PR while that workflow used ~1,418 wall-clock minutes this week. On a public repo this costs no money; it is a yield question for `/prioritise`.

## 7. Actions taken this run

- Filed **#567** (cron lag vs. fallback) and **#568** (IAM roles for `agent-infra`).
- Commented evidence on **#340** and **#282**; closed nothing.
- No GCP configuration changed; no file in the repo edited; no push.

## 8. Next run should

1. Read `/admin/ops` (or ask for a probe of it) to answer §4's open question: did the Groq fallback fire on 2026-10-27, and what do the per-model TPD numbers actually say?
2. If #568 lands, export the trigger first and confirm `ignoredFiles: measurements/**` and the `BUILD_SHA` step are still present.
3. Re-check #567's lag table with more samples after any cron change.
