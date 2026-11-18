# /subscribe sends the welcome email after the response, via BackgroundTasks, not inside the request

- **Date:** 2026-11-17
- **PR / issue:** #1163 (the timing half only; the stranger-mailing half stays open)

## Why, measured

`POST /subscribe` returns an identical body, status and headers for a new and an existing
address (#1159), but a new one ran `_send_welcome_email` synchronously inside the async
handler. #1159's QA round measured ~300-2300 ms for a new address against ~2-40 ms for an
existing one, so an anonymous caller could read membership off the response time.

**Decision (chief, standing ruling 4 on #1163, Option A):** `subscribe()` takes a
`BackgroundTasks` and queues `_send_welcome_after_response`, a sync wrapper that Starlette
runs in the threadpool after the response is sent. The wrapper keeps the
`welcome email failed for %s` warning and never raises. `notify.subscribed` stays inline in
the async handler: `notify.notify()` schedules with `asyncio.get_event_loop().create_task`
and skips on `RuntimeError` with only a debug log, so from a threadpool thread the Telegram
alert would be dropped silently. It only schedules a task, so it costs nothing in-request.
Cost: 0 LLM tokens, no new dependency, no deploy-config change.

**The ordering is tested, not the clock.** `tests/test_subscribe_welcome_after_response.py`
wraps the app in an ASGI spy that notes whether a blocked welcome stub has finished when the
last response byte leaves; it is red on the inline code and green after (the TestClient runs
background tasks before returning, so a plain latency assertion could not tell the two apart).
Three mutation rows in `scripts/mutations/2026_11_17_1163_subscribe_welcome_after_response.py`
re-break it.

## The risk this accepts, NOT measured

`deploy.sh` runs Cloud Run with `--cpu 1 --min-instances 0` and the default **request-based CPU
allocation**: CPU is throttled to near zero once the response has been sent. A welcome email
sent after the response can therefore be delayed until the next request lands on that instance,
or lost if the instance is reclaimed first. **This was not measured.** It cannot be measured
from the runner, and `/subscribe` cannot be probed in production without subscribing, and
mailing, a stranger.

**This is not the background worker declined in `ARCHITECTURE.md` (the "Background task /
worker for rashifal generation" entry in the rejected list).** That one needed
`--no-cpu-throttling`, which bills for the whole instance lifetime. This change touches no
billing: it accepts the throttling risk above instead of paying to remove it.

## What would overturn it

Either of these after deploy: `welcome email failed` warnings in the Cloud Run logs, or Brevo's
transactional sends falling below the new-subscriber count for the same period. Either one
escalates to a durable design (a `welcome_pending` flag on the subscriber record, drained by
a scheduled job) rather than a retry here.

## What this does NOT close

A probe still subscribes the address and mails it, so anyone can send a stranger a welcome
email. Only double opt-in closes that. It changes what a subscriber has to do before they are
mailed, which is a product decision (owner act #4 in CLAUDE.md), so the stranger-mailing half
of #1163 stays open for the owner.
