# The `__session` cookie expires and can be revoked on the server, and `/auth/google` refuses a cross-site post

- **Date:** 2026-11-17
- **PR / issue:** #1106

## Why, measured

`session.py` signed the cookie with `URLSafeSerializer`, which carries no timestamp, so the
server could never refuse an old one; `COOKIE_MAX_AGE` was only the browser's attribute.
`/auth/logout` deleted the cookie on the device that clicked, so a copy kept working.
`/auth/google` had no origin check (`grep -rniE 'g_csrf|csrf' src/astro_ai` found 0 hits).

What shipped: a timed cookie under a new salt, `LEGACY_COOKIE_CUTOFF` for untimed ones, a fixed
90-day bound on `user.since`, a `session_revocations.json` blob read through `hot_cache`, and an
`origin_guard` on `/auth/google`. 0 LLM tokens; worst case about 1,440 Class B GCS reads a day
for the revocation refresh (one per 300 s per instance, `maxScale` 5).

## Rejected, and why

- **`g_csrf_token` double-submit (the issue's own prescription).** `base.html` runs GIS in
  callback mode (`data-callback`, no `data-login_uri`) and the fetch posts only `credential`.
  Google sets `g_csrf_token` in redirect mode only, so the check would 403 every real sign-in.
  Replaced by `Sec-Fetch-Site` / `Origin`.
- **Our own CSRF cookie.** Firebase Hosting strips every cookie but `__session`.
- **`URLSafeTimedSerializer` on the old salt.** A v2 token fed to the legacy serializer raises
  `BadPayload`, which is not a `BadSignature`; the old handler turned that into a 500. A new
  salt and `except BadData` everywhere.
- **`loads(max_age=)`.** itsdangerous treats a negative age as expired, so clock skew between
  Cloud Run instances would sign people out. Age is compared by hand with 60 s of tolerance.
- **Flipping every cookie to timed at once.** Everyone would lose their saved charts. Untimed
  cookies stay readable until a literal cutoff (merge date + 365 days, the longest a browser can
  hold one). A relative bound would honour an untimed cookie for ever, its age being unknowable.
- **Upgrade on read.** It would write the year-long cookie on a GET, which privacy.html
  promises a read-only visit does not do. A legacy cookie is re-signed by the next write.
- **A version counter in `users.json`.** The file holds up to 50 readings per user, so a
  whole-file refresh to read one integer is the wrong size, and `storage.py` is a trust-boundary
  file. A separate blob keyed `revoked_before[sub]`, compared against the `since` every
  signed-in cookie already carries (no migration of signed-in state).
- **`hot_cache.get_or_compute`.** It blocks the event loop on a miss (#144).
  `get_or_refresh` returns the stale value or `{}` and refreshes in a thread.
- **Failing closed when storage is down.** `storage.get` cannot tell "missing" from
  "unavailable", so everyone would be signed out on a GCS blip and in local dev. The 90-day
  bound still holds.

## Consequences

Sign-out revokes every cookie that user holds that was issued before it. Another instance sees a
revocation within about one TTL plus a refresh; the first request on a cold instance does not see
one until the background fill lands. The constants (`SIGNIN_MAX_AGE` 90 d, cutoff 365 d, fail open)
are defaults the owner can retune.
