# infra-lead report — 2026-10-13

Focus: free-tier headroom, deploy truth, latency. Everything below was measured this run unless marked otherwise. Nothing in GCP or the repo was changed.

## 0. What I did not do, and why

- **No GCP change, no trigger export.** The credential in this environment is `agent-analytics@bhagya-500701.iam.gserviceaccount.com`. It gets `PERMISSION_DENIED` on `builds triggers list` (global and asia-south1), `run services list` and `projects get-iam-policy`. The `beta` component is also not installed here. So I could not export the trigger, and per the rules I did not edit it. The brief's "you may fix this yourself" turned out not to need a fix (§1), but if it had, this run could not have made it.
- **No edit to CLAUDE.md.** The brief says to record GCP changes there; there was no GCP change. CLAUDE.md's existing BUILD_SHA paragraph (set 2026-10-08, `--update-env-vars`) is accurate and I verified it (§1).
- Cloud Run / GCS usage against the free tier **could not be read** (no `run.*` or monitoring access). Where I give a Cloud Run figure it is derived from GA4 sessions and labelled as such.

## 1. Deploy truth — the premise was stale: the `exact` tier is live and has run

The brief says the exact tier "has NEVER run". It has.

| Evidence | Value |
|---|---|
| `curl https://shubhagya.com/health` (this run) | `{"ok":true,"revision":"bhagya-00440-bvw","build_sha":"ee1949a80deb699628e6f428a6ca83bce0047b93"}` |
| `git rev-parse HEAD` | `ee1949a80deb699628e6f428a6ca83bce0047b93` — identical |
| run 38439139160 (2026-10-13 17:29Z) | `DEPLOY GATE: exact — build_sha 686fe3a matches this commit (revision bhagya-00438-8p2), after 20 tries` (~5 min) |
| run 38136019114 (2026-10-11) | `DEPLOY GATE: exact … after 1 tries` |
| #282 comment | records it set 2026-10-08, run 37740508193 |

`build_sha` has been non-null in every log I read (39dedb4, babc857, 04bc524, 5fa5ebe). Revisions seen serving: 00429 → 00440 over 2026-10-11..13.

**Two real problems with deploy truth, both filed:**

- **#341** — the gate waits for `$GITHUB_SHA`, which only works if that commit is one Cloud Build builds. Run 38333011428 (dispatch 2026-10-13 01:37Z, HEAD `be4046b`, a `measurements/`-only commit that the trigger's `ignoredFiles` can never build) polled 48× for a SHA that cannot exist and failed red after 12 min, while production was healthy and serving `39dedb4`. `agent-merge.yml:352` dispatches `--ref main`, so a nightly measurements commit landing in the gap reproduces it. Run 38160697735 (push `39dedb4`) timed out the other way: it did deploy, but after the 12-min window (served 00433 by 10-13 01:37Z). I cannot see Cloud Build, so I cannot say whether that was a slow or a queued build. Proposed: wait for the newest commit ≤ `$GITHUB_SHA` that touches a path outside `measurements/`. No cost change.
- **#340** — the tree still says the opposite and prints a dangerous command. `verify-production.yml` lines 27/206/825 and `health.py:61` tell the reader to add `--set-env-vars=BUILD_SHA=…`; CLAUDE.md says never `--set-env-vars` (it replaces the whole env, including the Groq keys). `infra-lead.md` and `agent-infra.yml` still say "has NEVER run"; `infra-lead.md` says verify-production is daily (it is `17 6 * * 1`, weekly) and names `scripts/verify_token_budget.py`, **which does not exist**.

#282 item 1 is done and item 2 was withdrawn in its own comment; the issue is stale-open. I may not close it — for `/prioritise`.

## 2. GitHub Actions

- **#339 (needs a human): billing block.** On 2026-10-12, six jobs on four workflows never started: *"The job was not started because recent account payments have failed or your spending limit needs to be increased."* PR gates + verify-build (03:07Z), Agent merge ×2 (03:08Z), verify-production scheduled drift run (15:29Z), Agent steward (18:21Z). Window ≥ 15 h 14 m. The Monday drift check never ran. I have no billing scope, so I could not tell a failed payment from a zero spending limit.
- The repo is **public** (`gh api repos/mahAnuj/astro-ai --jq .visibility`), where standard runner minutes are not metered. CLAUDE.md's "2,000-minute monthly allowance" is the private-repo figure. Either that line is wrong, or something here is billed that I could not identify. Flagged in #339 for the human; I make no claim which.
- Volume, last 100 runs (2026-10-11T16:04Z → 2026-10-13T23:13Z, ~55 h), summed job wall-clock (overstates billed minutes): total **546 min** — Agent work 252 (6 runs), PR gates 185 (21), verify-build 48 (28), verify-production 42 (6), everything else < 7 each. Sustained, that is ~7,000 min/month, 3.6× the 2,000 figure, which is why §2's billing question matters.
- Other failures in that window, none infra: PR gates "cancelled" ×6 are the concurrency group superseding itself (`Canceling since a higher priority waiting request`); PR gates `failure` ×3 and Loop outcomes `failure` ×2 exit 1 with real gate output (not investigated further); verify-build and PR gates on run 38342901013/…051 failed with a 404 from the annotations API (no log retrievable).
- `verify-production` weekly: the paths-ignore change worked — 6 runs in 55 h, 3 of them dispatches from agent-merge, vs 12 runs/day on 10-08.

## 3. Latency (curl from the GitHub runner, US; this run)

| route | status | TTFB | total | size |
|---|---|---|---|---|
| / | 200 | 0.67 s | 0.70 s | 152 KB |
| /kundli | 200 | 0.98 s | 1.01 s | 140 KB |
| /matching | 200 | 0.57 s | 0.60 s | 135 KB |
| /numerology | 200 | 0.59 s | 0.61 s | 128 KB |
| /panchang | 200 | 0.55 s | 0.58 s | 134 KB |
| /rashifal/aries | 200 | 0.99 s | 1.02 s | 126 KB |
| /health | 200 | 0.60 s | 0.60 s | 96 B |
| /static/css/app.css (CDN HIT) | 200 | 0.41 s | 0.42 s | 85.6 KB |

Your `/tmp/probe.txt` agrees (0.65–0.92 s). Reading: the network floor from this runner is ~0.4–0.6 s (a 96-byte `/health` costs 0.60 s; a CDN-hit CSS 0.41 s), so server time on the static-ish pages is ~0.1–0.5 s. Nothing here is slow. `/kundli` GET 0.98 s and `/rashifal/aries` 0.99 s are the highest; both were warm.

- **Not measured:** the natal *generation* latency (the 26 s figure) — it needs a POST /kundli, which spends ~6.8k tokens of the shared Groq budget (§4). I did not spend them. Cold-start latency (min-instances 0) not measured.
- HTML is `cache-control: private, no-cache, no-store, must-revalidate` with `x-cache: MISS`, so every page view reaches Cloud Run. At present traffic that is irrelevant (§5); it becomes the lever at much higher traffic.
- `sw.js` is `no-cache`; `app.css` is `public, max-age=300` with a `?v=` hash. #253's stylesheet half holds; the remaining `/static/` cache-first assets are as the issue's last comment describes. Not re-tested in a browser.

## 4. Groq — the ceiling that binds first (#266, #212)

Measured: `uv run python scripts/measure_natal_request.py` (tiktoken `o200k_base`, a proxy for gpt-oss's encoding, ±1–2 %; excludes completion and chat-template overhead).

| | tokens |
|---|---|
| system prompt (en) | 3,111 (fixed, every request — 46 % of the worst call) |
| worst chart (cancer-lagna-manglik-exempt) | 6,798 total = **85 % of 8,000 TPM** |
| best chart (manglik-uncancelled) | 6,477 |

Ceiling table (current numbers from the above, ARCHITECTURE.md, and `measurements/latest.md`):

| Ceiling | Value | Current use | Breaks at | Move | Free tier? |
|---|---|---|---|---|---|
| Groq TPM, per model | 8,000 | one uncached natal = 6.5–6.8k input | **3 uncached natals in one minute** (chain `groq120,groq20` has 2 buckets) | not the binding constraint — see TPD | n/a |
| Groq TPD, per model | 200,000 (CLAUDE.md; 198,298 reached 2026-10-08 per ARCHITECTURE.md) | ~80k/day rashifal combined job (24 × ~3,330, ARCHITECTURE.md, not re-measured) | ≈ **47 uncached natal reads/day** on input tokens alone (≈120k left on groq120 + 200k on groq20, ÷ ~6.8k); real number is lower because completion tokens are unmeasured | shrink the 3,111-token system prompt; verify whether Groq prompt caching applies to these two models and counts toward TPM/TPD (**not verified**) | yes |
| Model beyond the two | — | — | — | **human decision** per CLAUDE.md; the obvious candidates are already ruled out there | unknown |

Modelled (Poisson, uniform arrivals — arithmetic, not observation) TPM collisions on a 2-request/min ceiling: 100 uncached kundlis/day → 0.08 % lost; 1,000/day → 5.7 %; 5,000/day → 47 %. TPD bites at ~47/day, long before TPM does, so TPD is the number to design to.

Today's load: GA4 278 sessions / 28 days ≈ 9.9/day. If every session were a unique kundli that is ~21 % of 47/day; the real kundli rate is lower and the natal cache (SQLite + GCS) makes repeat charts free. So **the 503s in #266 at today's traffic are more probably the daily rashifal job and a kundli sharing the day's TPD or a minute, than organic kundli volume.** That is a hypothesis; a timestamped production 503 would confirm or kill it. Posted as a comment on #266.

#212: still nothing measures per-request tokens in production or CI for rashifal. `measure_natal_request.py` is offline and natal-only; `verify_token_budget.py`, which `infra-lead.md` calls "the gate that makes it real", does not exist (#340). I did not file a separate issue: #212 already carries it and building the gate is Engineering's.

## 5. Cloud Run / GCS headroom

I could not read Cloud Run or GCS usage (permissions, §0). Derived only:

- Cloud Run free tier: 2M requests/month (public figure, not re-checked this run). Traffic: GA4 278 sessions / 28 d. Even at a deliberately generous 100 requests per session (HTML + assets + bots) that is ~28k requests / 28 d ≈ **1.4 % of 2M; the breach multiple is ≈ 70× at that assumption**, higher at any realistic one. `deploy.sh` sets `--max-instances 5 --concurrency 80 --cpu 1 --memory 512Mi --min-instances 0`; I did not verify that the live service matches `deploy.sh`.
- Cloud Run is not the first thing to break; Groq TPD is, ~15× sooner in sessions terms.

## 6. #232 and #253 (standing)

- **#232 is largely closed by the tree already.** `rashifal_derive.derive_single_reading` reads `daily_cache` tier 0 first and writes the GCS blob back into it (`rashifal_derive.py:112–131`), and the route is `async def rashifal_single` calling it synchronously (`routes/rashifal.py:171`, call at 268), so the first cold read blocks the loop and the other eleven then find tier 0 populated. Net: **one GCS read per instance per language per day**, not twelve. Residual: that one read blocks the event loop for the US↔asia-south1 round-trip; I did not measure GCS latency from `asia-south1`. With `maxScale=5` this is ≤ 5 reads/lang/day. I recommend someone re-verify against the 12-concurrent scenario in the issue and close it. I did not.
- **#253** unchanged since its last comment: stylesheet half fixed (`?v=` hash seen live), `/static/` cache-first remainder open.

## 7. Issues filed / commented

| # | What | Needs |
|---|---|---|
| #339 | Actions jobs refused to start for billing, 2026-10-12 | **human** (Billing & plans) |
| #341 | Exact deploy gate waits for a SHA that may never deploy | engineer (workflow edit) |
| #340 | Stale "never ran" text + `--set-env-vars` advice + nonexistent `verify_token_budget.py` | engineer / doc edit |
| #266 (comment) | Capacity numbers above | — |

Suggest `/prioritise` close #282 (item 1 done, item 2 withdrawn) and look at #232.

## 8. Unverified / for the next run

- Cloud Build deploy duration and queue time (case 2 in #341); needs Cloud Build read access for this service account (`roles/cloudbuild.builds.viewer`) or a human to read the build history for 39dedb4 — **adding IAM bindings is a human decision**.
- Cloud Run / GCS actual usage vs free tier (needs `roles/monitoring.viewer` or `run.viewer`).
- Natal completion tokens and whether Groq's prompt caching helps (needs one live, budgeted call).
- Whether the Actions billing block recurred between 10-12 18:21Z and 10-13 01:37Z.
