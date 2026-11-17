"""Server-side sign-out for the `__session` cookie (#1106).

A signed cookie is valid wherever it is copied until something server-side says
otherwise. Sign-out only deleted the cookie on the device that clicked, so a copy
kept working. This module keeps one fact per user: `revoked_before[sub]`, an epoch
second. `session.load_user` signs a cookie out when its `user.since` is at or
before that instant, so sign-out ends every cookie issued up to that moment
("sign out everywhere") and a later sign-in is unaffected.

WHY A BLOB OF ITS OWN, not a counter on `users.json`: that file holds up to 50
readings per user, so refreshing it as a whole to read one integer is the wrong
size, and `storage.py` is a trust-boundary file this change has no business in.
The blob is `{"revoked_before": {sub: epoch}}` and entries older than
`SIGNIN_MAX_AGE` are pruned on write, because a cookie that old is signed out by
its age alone.

COST ON THE REQUEST PATH: `load_user` calls `revoked_before` only when the cookie
carries a `user`, and the read goes through `hot_cache.get_or_refresh`
(stale-while-revalidate, #144), so it never blocks the event loop and costs 0 GCS
reads while warm. Worst case is one read per 300 s per instance.

CONSEQUENCES, STATED:
  * Another instance sees a revocation within the TTL plus one refresh, not at
    once. The instance that handled the sign-out sees it immediately, from the
    process-local dict below.
  * The first request on a cold instance reads `initial={}` and so does not see
    revocations made elsewhere until the background fill lands.
  * FAIL OPEN. `storage.get` cannot tell "missing" from "unavailable", so failing
    closed would sign every user out on a GCS blip and in local dev with no
    bucket. A revocation that cannot be read is a revocation that is not applied;
    the 90-day age bound still holds.
"""

from __future__ import annotations

import logging
import threading
import time

from astro_ai import hot_cache, storage
from astro_ai.session import SIGNIN_MAX_AGE

log = logging.getLogger(__name__)

KEY = "session_revocations.json"
CACHE_KEY = "session:revoked"
TTL_S = 300

# Mirrors the written blob for revocations THIS process made, so sign-out is
# immediate here instead of waiting out the cache.
_LOCAL: dict[str, int] = {}
_LOCK = threading.Lock()


def _read() -> dict[str, int]:
    data = storage.get_json(KEY)
    raw = data.get("revoked_before") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for sub, stamp in raw.items():
        if isinstance(stamp, (int, float)) and not isinstance(stamp, bool):
            out[str(sub)] = int(stamp)
    return out


def revoked_before(sub: str) -> int:
    """Epoch second before which `sub`'s cookies are void; 0 if none known."""
    cached = hot_cache.get_or_refresh(CACHE_KEY, TTL_S, _read, initial={})
    with _LOCK:
        local = _LOCAL.get(sub, 0)
    return max(local, cached.get(sub, 0))


def revoke(sub: str) -> None:
    """Void every cookie `sub` holds that was issued up to now. Never raises:
    the caller is sign-out, which must still clear the device's own cookie."""
    now = int(time.time())
    horizon = now - SIGNIN_MAX_AGE
    with _LOCK:
        _LOCAL[sub] = now
        for old in [k for k, v in _LOCAL.items() if v < horizon]:
            _LOCAL.pop(old, None)

    def mutate(current):
        state = current if isinstance(current, dict) else {}
        table = state.get("revoked_before")
        table = table if isinstance(table, dict) else {}
        table = {k: v for k, v in table.items()
                 if isinstance(v, (int, float)) and v >= horizon}
        table[sub] = now
        return {"revoked_before": table}

    try:
        written = storage.update_json(KEY, mutate, default={"revoked_before": {}})
    except Exception as err:  # noqa: BLE001 - sign-out must not fail on storage
        log.warning("revocation.revoke(%s) failed: %s", sub, err)
        return
    if written is None:
        log.warning("revocation.revoke: storage unavailable; revocation is "
                    "process-local only")
