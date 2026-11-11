# Tomorrow's rashifal is written the day before, so Groq never generates it

- **Date:** 2026-11-10
- **PR / issue:** #852

## Why, measured

**The symptom.** In the week to 2026-11-10, /admin/ops showed rashifal at 28 requests, **177 Groq
calls** and **778,261 input tokens**. That is about 24 calls a day: the 01:00 UTC
`/admin/warm-rashifal` generating 12 rashis in 2 languages.

**Claude's job was not broken.** Run 42752986016 published 12 English and 12 Hindi sections and
wrote its run record. Both artifacts pass the site's own gates: `passes_quality(..., "rashifal")`
on each language, and `"rashifal_single"` on all 24 sections. Its blob arrived too late to matter.

**The timing.** The job's cron was `0 22 * * *` and it wrote TODAY. GitHub started it 2h50m–6h
late: the last 12 runs began between 00:50 and 03:59 UTC, after the warm. The warm then found no
blob and paid Groq, and Claude's later blob changed nothing already cached per instance.

**Decision.**
- A scheduled run writes the NEXT IST day, from `17 6 * * *` (11:47 IST).
- Even the worst measured delay plus the 45-minute job lands before IST midnight (18:30 UTC). A
  test pins that arithmetic.
- The day is "the IST date 18h from now" (`scripts/rashifal_target_date.py`), so a run delayed
  past IST midnight writes the day that just started rather than the one after.
- Both scripts already took `--date` and pin the transit and panchang to it. Verified: 11-11 builds
  Wednesday, Shukla Dwitiya, Moon in Jyeshtha; 11-10 builds Tuesday, Pratipada, Anuradha.
- Manual runs still write today, which is how a bad day is regenerated or one rashi spliced in.
- Groq stays the fallback for a missed day.

**Also fixed.** /admin/ops said "no run recorded" on an instance's first render, because
`_rashifal_runs()` used `hot_cache(initial={})` and could not tell "not read yet" from "no
record". It now returns None until the read lands, and the panel says "record not loaded yet".

**Rejected:**
- **Moving the Groq warm later.** The 07:00 IST email blast reads the warm's output at 01:30 UTC.
- **Several cron slots with a skip check.** More runs and more Claude quota to buy what one
  afternoon slot with 12h of slack already gives.

**The switch-over leaves a gap, by construction** (QA on #853). The old 22:00 UTC cron no longer
writes TODAY, and the new 06:17 UTC cron writes TOMORROW. So the day the change merges, and the
next day if it merges after 06:17 UTC, have no early Claude write. The 01:00 UTC warm generates
those days on Groq, as before: about 24 calls and about 110k input tokens each. To close the gap
by hand, dispatch `rashifal-generate` once with `date=<that day>` (the input this PR adds).

**Residual risk.** A prompt-file change deployed between generation and the day itself changes
the storage key's fingerprint. The day then falls back to Groq, the same as a missed run.
