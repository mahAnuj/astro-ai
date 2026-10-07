"""Shared auth + POST for the Google read-only data APIs.

No new dependencies. `google.auth` is already present (google-cloud-storage
pulls it in) and the rest is urllib, because `pyproject.toml` deliberately keeps
anything dev-only out of `[project.dependencies]` so the Cloud Run image stays
as small as it is.

Credentials come from ADC, so the same code authenticates three ways without
knowing which:

  * GitHub Actions  — Workload Identity Federation, keyless. The org blocks
    service-account key creation (`constraints/iam.disableServiceAccountKeyCreation`),
    which is why there is no JSON key anywhere in this repo.
  * Local, as the service account — the identity CI actually uses:
        gcloud auth application-default login \
          --impersonate-service-account=agent-analytics@bhagya-500701.iam.gserviceaccount.com
  * Local, as you — only useful for a smoke test; your own GA4/GSC access is
    wider than the service account's, so a script that works this way may still
    403 in CI. Prefer impersonation.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]
TIMEOUT = 60


SA = "agent-analytics@bhagya-500701.iam.gserviceaccount.com"


def token() -> str:
    import google.auth
    import google.auth.transport.requests as _tr
    from google.auth.exceptions import DefaultCredentialsError, RefreshError

    try:
        creds, _ = google.auth.default(scopes=SCOPES)
        creds.refresh(_tr.Request())
    except DefaultCredentialsError:
        # A stack trace here tells an unattended agent nothing it can act on.
        raise SystemExit(
            "No Application Default Credentials.\n"
            "  Locally, authenticate as the identity CI uses:\n"
            f"    gcloud auth application-default login --impersonate-service-account={SA}\n"
            "  In GitHub Actions this is google-github-actions/auth with the\n"
            "  workload_identity_provider input — no key, by design."
        ) from None
    except RefreshError as e:
        raise SystemExit(
            f"Credentials found but could not be refreshed: {e}\n"
            f"  If impersonating, you need roles/iam.serviceAccountTokenCreator on {SA}."
        ) from None
    return creds.token


def post(url: str, body: dict, bearer: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        # 403 here is nearly always the grant, not the code: the service account
        # must be added inside GA4 (Property access management) and Search
        # Console (Users and permissions) separately. Project IAM does not cover
        # either of them.
        raise SystemExit(f"HTTP {e.code} from {url.split('/')[2]}\n{detail}") from None


def window(days: int) -> tuple[str, str]:
    """A trailing window that EXCLUDES today and yesterday.

    GA4's standard reports lag 24-48h and GSC lags 2-3 days. A window ending
    today reads partial days as a decline, which is how a healthy ship gets
    scored as a regression.
    """
    import datetime as _dt

    end = _dt.date.today() - _dt.timedelta(days=3)
    return (end - _dt.timedelta(days=days - 1)).isoformat(), end.isoformat()
