# A Cloud Run revision refuses to start on an unset, blank or placeholder secret

- **Date:** 2026-11-17
- **PR / issue:** #1104

## Why, measured

Three secrets each fell back silently to a constant committed in this public repo:
`ADMIN_PASSWORD` (`routes/deps.py`, `_ADMIN_DEV_FALLBACK`), `ASTRO_AI_COOKIE_SECRET`
(`session.py`, `_DEV_SECRET`; `identity.py` derives its HMAC subkey from it) and the
unsubscribe key (`subscribers.py`, a third copy of the string, identical to the admin
fallback). `deploy.sh` checks the variables are set, but production deploys through the
GCP-side Cloud Build trigger, which never runs `deploy.sh`, so nothing checked at start-up.

**Decision.** `main._lifespan` calls `deps.insecure_secrets()` when `K_REVISION` is set
(Cloud Run only) and raises `RuntimeError` before the warm-up if either secret is unset,
blank, or equal to either committed placeholder. The log line and the message name the
variables, never the values. With `K_REVISION` unset (local dev, `TestClient`) nothing
changes. The unsubscribe key now comes from `session.cookie_secret()`: with the env var set
it is byte-identical to before, so links already in sent emails still verify (pinned by a
test against the old formula); unset, its dev fallback is no longer the admin string.

**Why refuse to start, not 503 per route.** A Cloud Run revision whose container fails to
start never receives traffic, so if production ever lost a secret the previous revision
keeps serving and the cost is a failed deploy. A per-route 503 would break live pages on a
revision that already took traffic.

**Not verified: production's environment.** This was built without `gcloud`, so whether
`ADMIN_PASSWORD` and `ASTRO_AI_COOKIE_SECRET` hold real values on the service today is
unknown. The worst case if either does not is a failed deploy of the next revision, not an
outage. The owner can confirm with `gcloud run services describe bhagya --region
asia-south1 --format='value(spec.template.spec.containers[0].env)'` before the next deploy.

**Not done.** `deploy.sh` still only checks "non-empty" (its logic is unchanged; the app now
catches a placeholder). Admin Basic auth still has no rate limit or lockout, which the issue
mentions but its acceptance criteria do not ask for.
