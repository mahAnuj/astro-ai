# The loop keeps itself awake, reads its freshest quota, and QA files what it lets through

- **Date:** 2026-11-20
- **PR / issue:** #1280

## Why, measured

**What happened on 2026-11-20 (UTC):**
- **03:53:** an `agent-work` run logged 88% of the weekly Claude window, `allowed_warning`. The reading carried `resets.seven_day` = 06:00.
- **06:00:** the window reset.
- **11:05:** the next cycle logged 4%, `allowed`.
- **11:43:** `chain_cycle.py` judged quota from `claude_usage.json`, still the 03:53 reading (refreshed only at 11:45). It refused: "latest Claude reading says 'allowed_warning'".
- **11:52 onward:** nothing woke the loop again. In the 27 hours to 15:17, GitHub fired the hourly `agent-queue` cron 3 times (18:16, 00:41, 08:32). An hourly run never started a cycle anyway; only `agent-work`'s own cron did, and its 15:00 slot never fired.

**Why QA let it through.** The first QA round on #749, which shipped the chain on 2026-11-06, wrote: *"NON-BLOCKING FINDINGS: … (2) quota staleness measured from generated_at with 36h tolerance, not latest.at"*. It was rated non-blocking because it fails safe: the loop waits rather than overspends. `qa.md` had no rule that a non-blocking finding becomes an issue, so it stayed in a comment on a merged PR.

**The decisions:**
1. **`chain_cycle.py` judges the freshest reading.**
   - It takes the newest finished cycle's own reading when that is newer than the file (`fresh_reading`).
   - It sets aside a reading whose five-hour and seven-day windows have both reset (`windows_reset`).
   - The 70% ceiling, `allowed`-only and 36h age guards are unchanged.
2. **An idle lane restarts.** A run with no finished cycle behind it (the hourly cron, or the heartbeat) asks `idle_reason`.
   - It starts one ranked cycle when the build lane has been free for 60 min, or 4 h after a cycle that produced nothing.
   - The quota, busy-lane and 16-a-day cap guards are the same as for a chain.
3. **A heartbeat** (`scripts/heartbeat.py`). Every `agent-queue` run ends by dispatching a `heartbeat=true` run, unless another run is already waiting.
   - A heartbeat run dozes up to 20 min, yielding within 30 s if another run starts waiting, then does a normal run's work.
   - `workflow_dispatch` from `github.token` is not suppressed and has no three-level limit.
   - It adds no permission and no job. The drain timeout goes 15 → 30 min and `CLAIM_TTL` 20 → 31 min, to keep `CLAIM_TTL` above the timeout.
4. **`qa.md`: a non-blocking finding is filed**, labelled `qa` and `bug`, titled `QA follow-up:`, with an Evidence Block. Its number is cited in the verdict.

**Rejected:**
- **More cron lines:** each is dropped independently, and the measured drop rate makes them a lottery.
- **Cloud Scheduler calling the GitHub API:** reliable, but it needs a GitHub token stored in GCP, which is the owner's act #3.
- **A separate heartbeat job or workflow:** `verify_workflow_permissions.py` fails any new job that inherits a scope, by design.
- **Dozing in a second concurrency group:** two drains at once would race on the queue's comment-marker claims, which are not atomic.
- **Re-arming unconditionally:** a dispatch while a run is pending cancels that run, and with it a `workflow_run` chain payload.

**Cost:** the repo is public, so Actions minutes are unlimited (#338). That is about 3 heartbeat runs an hour while idle, mostly asleep. No model runs.
