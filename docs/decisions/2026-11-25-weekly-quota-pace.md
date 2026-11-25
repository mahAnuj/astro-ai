# The build chain is paced to the week, not capped per day

- **Date:** 2026-11-25
- **PR / issue:** the PR that adds this file (owner: "do what is necessary as per you")

## Why, measured

**What happened in the week starting Fri 20 Nov 06:00 UTC:**
- The loop chained cycles back to back from the reset.
- It reached the 70% weekly ceiling on Wed 25 Nov at 12:20 UTC (`no chain: weekly Claude window at 71%, ceiling 70%`).
- It then stood down until Fri 27 Nov 06:00 UTC, about 40 hours with no build cycle.
- Earlier the same week, the fixed cap of 16 build runs a day had idled it from 13:12 to 15:04 UTC on 21 Nov, while the quota stood at 23%.
- About 16% of the weekly window was being used per day, against the 10% a day that 70% over seven days allows.

**The decision:**
- `chain_cycle.pace_reason` lets a chain or idle restart start only while weekly use is at or under `elapsed share of the week × 70% + 5%`.
- The window's start is the reading's `resets.seven_day` minus seven days.
- On the line, the loop reaches 70% as the week ends, at roughly one cycle per two hours at the measured ~0.8% a cycle. The 5% lets each week start with a burst.
- A reading with no reset time falls back to the ceiling alone.
- The daily cap stays, as a backstop against a runaway bug: 16 → 30.
- Queue rulings (QA rounds, fixes someone asked for) are started by the drain and are not paced.

**Rejected:**
- **A lower daily cap:** it idles quiet days and still allows a mid-week cliff after busy ones.
- **Raising the 70% ceiling:** the other 30% is the owner's own sessions on the same subscription.
- **Pacing the queue too:** a ruling someone made outranks the ranker; that rule predates this one.
