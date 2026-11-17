"""Signed-cookie persistence for the seeker's session state.

The cookie holds a combined payload:
    {
      "charts": [SavedChart, ...],
      "active_id": "abc12345",
      "lang": "en"     # 'en' or 'hi'
    }

`itsdangerous` HMAC-signs the JSON payload with `ASTRO_AI_COOKIE_SECRET`;
any tampering invalidates the signature and we treat the visitor as fresh.
The signature is timed (#1106): every write stamps it, and the server refuses a
cookie older than COOKIE_MAX_AGE, so a copied cookie does not outlive the
browser's own Max-Age. See `_decode`.

Capped at MAX_CHARTS so the cookie can't grow unbounded — at ~150 bytes per
SavedChart, 10 fits comfortably inside the 4 KB browser cookie limit.

WHY THE COOKIE IS NAMED `__session`:

Firebase Hosting strips ALL cookies from inbound requests before forwarding
to Cloud Run, EXCEPT cookies named exactly `__session` (this is hardcoded
behaviour to keep the Fastly CDN cache efficient). If we used our own cookie
name, browsers would store the cookie but Firebase would never forward it,
and every subsequent request would look stateless. Hence: one combined
`__session` cookie holds everything we need to persist.
"""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Final

from fastapi import Request, Response
from itsdangerous import BadData, BadSignature, URLSafeSerializer, URLSafeTimedSerializer

from astro_ai.llm import BirthDetails

# Must be exactly "__session" — see module docstring for why.
COOKIE_NAME: Final[str] = "__session"
COOKIE_MAX_AGE: Final[int] = 60 * 60 * 24 * 365  # 1 year
# One constant drives both the browser's Max-Age and the server-side bound in
# `_decode`, so the two cannot drift apart.
CLOCK_SKEW_S: Final[int] = 60  # Cloud Run instances' clocks are not identical
SIGNIN_MAX_AGE: Final[int] = 60 * 60 * 24 * 90  # 90 days, FIXED from `user.since`
# Cookies written before #1106 carry no timestamp, so their age is unknowable and
# a relative bound would honour them forever. They are accepted until this
# instant: 2027-11-17 00:00:00 UTC = the merge date + 365 days, the longest a
# browser can still hold a cookie written the day this shipped (Max-Age is 1 year
# and every write re-stamps it). After it, a legacy cookie is `{}`.
LEGACY_COOKIE_CUTOFF: Final[int] = 1826409600
MAX_CHARTS: Final[int] = 10
DEFAULT_LANG: Final[str] = "en"
SUPPORTED_LANGS: Final[frozenset[str]] = frozenset({"en", "hi"})
_DEV_SECRET: Final[str] = "astro-ai-dev-secret-CHANGE-FOR-PROD"


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SavedChart:
    """One persisted seeker. ID is generated when the chart is first saved."""

    id: str
    name: str            # may be empty if seeker didn't supply
    birth_date: str
    birth_time: str
    birth_place: str

    @classmethod
    def from_birth_details(cls, details: BirthDetails) -> SavedChart:
        return cls(
            id=secrets.token_hex(4),  # 8-char hex, ~4B possibilities — fine for collision among ≤10
            name=details.name or "",
            birth_date=details.birth_date,
            birth_time=details.birth_time,
            birth_place=details.birth_place,
        )

    def to_birth_details(self) -> BirthDetails:
        return BirthDetails(
            name=self.name,
            birth_date=self.birth_date,
            birth_time=self.birth_time,
            birth_place=self.birth_place,
        )

    def display_name(self) -> str:
        """Fall back to a useful label when the seeker didn't supply a name."""
        return self.name.strip() or f"{self.birth_place} {self.birth_date}"


@dataclass(frozen=True)
class ChartCollection:
    """The seeker's saved-charts list plus which one is currently active."""

    charts: tuple[SavedChart, ...]
    active_id: str | None

    @property
    def active(self) -> SavedChart | None:
        if not self.charts:
            return None
        if self.active_id:
            for c in self.charts:
                if c.id == self.active_id:
                    return c
        return self.charts[0]

    def get(self, chart_id: str) -> SavedChart | None:
        return next((c for c in self.charts if c.id == chart_id), None)

    def add(self, details: BirthDetails) -> ChartCollection:
        """Add a new chart (or reactivate an existing one with identical details)."""
        for existing in self.charts:
            if (
                existing.birth_date == details.birth_date
                and existing.birth_time == details.birth_time
                and existing.birth_place == details.birth_place
            ):
                # Dedup — same chart already saved. Reactivate, refresh name.
                refreshed = replace(existing, name=details.name or existing.name)
                charts = tuple(refreshed if c.id == existing.id else c for c in self.charts)
                return ChartCollection(charts=charts, active_id=existing.id)
        if len(self.charts) >= MAX_CHARTS:
            raise ValueError(
                f"You've reached the {MAX_CHARTS}-chart limit. "
                "Delete one from the homepage before saving another."
            )
        new = SavedChart.from_birth_details(details)
        return ChartCollection(charts=self.charts + (new,), active_id=new.id)

    def set_active(self, chart_id: str) -> ChartCollection:
        if not any(c.id == chart_id for c in self.charts):
            return self  # unknown id — silently no-op
        return ChartCollection(charts=self.charts, active_id=chart_id)

    def remove(self, chart_id: str) -> ChartCollection:
        remaining = tuple(c for c in self.charts if c.id != chart_id)
        if not remaining:
            return ChartCollection(charts=(), active_id=None)
        new_active = self.active_id
        if new_active == chart_id or new_active is None:
            new_active = remaining[0].id
        return ChartCollection(charts=remaining, active_id=new_active)


# ---------------------------------------------------------------------------
# Cookie I/O — the cookie is read once per request and written as a whole
# blob; helpers below operate on the parsed dict so chart and lang updates
# coexist without clobbering each other.
# ---------------------------------------------------------------------------


def cookie_secret() -> str:
    """The signing secret: the one place the env var and dev fallback are read.

    Public because `identity.py` derives its HMAC subkey from it rather than
    asking for a second secret — see that module for why.
    """
    return os.environ.get("ASTRO_AI_COOKIE_SECRET") or _DEV_SECRET


def _serializer() -> URLSafeTimedSerializer:
    """The serializer every WRITE uses. A new salt, not the old one on a timed
    class: a v2 token fed to the legacy untimed serializer raises `BadPayload`,
    which is not a `BadSignature`, and the old `except BadSignature` turned that
    into a 500 (#1106)."""
    return URLSafeTimedSerializer(cookie_secret(), salt="birth-details-v2")


def _legacy_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(cookie_secret(), salt="birth-details")


def _decode(raw: str) -> dict:
    """Verify and decode a `__session` value, or `{}`. The only place a cookie
    is parsed: `_load_session` and `_pending_session` both come here, and a
    second parse site would silently disagree with the first about what a valid
    cookie is.

    Age is compared by hand, NOT with `loads(max_age=)`: itsdangerous treats a
    negative age (stamp ahead of this instance's clock) as expired, so clock skew
    between two Cloud Run instances would sign people out. A stamp up to
    CLOCK_SKEW_S in the future is accepted.

    READS NEVER WRITE. A legacy cookie is not upgraded here, because privacy.html
    promises a visit that only reads does not extend the cookie; it is re-signed
    by the next ordinary write.
    """
    try:
        data, stamp = _serializer().loads(raw, return_timestamp=True)
    except BadSignature:
        data = None
    except BadData:
        return {}
    else:
        age = time.time() - stamp.timestamp()
        if age > COOKIE_MAX_AGE + CLOCK_SKEW_S or age < -CLOCK_SKEW_S:
            return {}
        return data if isinstance(data, dict) else {}
    if time.time() >= LEGACY_COOKIE_CUTOFF:
        return {}
    try:
        data = _legacy_serializer().loads(raw)
    except BadData:  # BadPayload is not a BadSignature
        return {}
    return data if isinstance(data, dict) else {}


def _load_session(request: Request) -> dict:
    """Read + decode the cookie, or return an empty dict. All callers go through
    this so we only HMAC-verify once per request."""
    raw = request.cookies.get(COOKIE_NAME)
    if raw is None:
        return {}
    return _decode(raw)


def _write_session(response: Response, data: dict) -> None:
    """Sign and write the combined session payload."""
    payload = _serializer().dumps(data)
    response.set_cookie(
        COOKIE_NAME,
        payload,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        # Keyed on K_REVISION, which Cloud Run sets and local dev / TestClient
        # leave unset: the browser sees HTTPS at Firebase Hosting and applies
        # Secure there, but this function has no request to read the scheme
        # from (Cloud Run itself sees plain http behind the proxy). Always-True
        # would stop the cookie round-tripping over http://127.0.0.1.
        secure=bool(os.environ.get("K_REVISION")),
    )


# ---------------------------------------------------------------------------
# One-shot "this GET follows a completed POST" flags (#1068)
# ---------------------------------------------------------------------------
# `kundli_generated` and `ask_answered` are declared by the template that renders
# the RESULT, and that template also renders on every revisit (/kundli with a
# saved chart, /r/<id>, a reload of /ask?q=), so a render cannot tell a
# completion from a re-view. The POST's 303 sets the flag, the GET that follows
# reads it and clears it.
#
# THE FLAG LIVES INSIDE `__session`, not in a cookie of its own. Firebase Hosting
# forwards only `__session` (module docstring), so a `bhagya_ev_*` cookie would be
# stored by the browser and stripped before Cloud Run saw it: the event would
# never fire on shubhagya.com while every TestClient test stayed green.
#
# Shape: `ev = {name: expiry_epoch}`. `__session` lasts a year, so the 120s
# lifetime is carried by the stamp, and a stale one is ignored. Names are a fixed
# set so nothing a request carries can shape a key.
#
# Both writers below return the response with exactly ONE `__session`
# Set-Cookie. Every other `save_*` here re-reads the REQUEST cookie, so two
# writers on one response leave two headers and the browser keeps the last,
# silently dropping the first writer's data (the bug `save_session_atomic`
# documents). So a flag write starts from the cookie already pending on the
# response, when there is one, and replaces that header. Call these AFTER the
# route's other session write: a `save_*` made later would re-read the request
# and drop the flag.
EVENT_FLAG_NAMES: Final[frozenset[str]] = frozenset({"kundli_generated", "ask_answered"})
EVENT_FLAG_TTL: Final[int] = 120  # seconds


def _check_flag_name(name: str) -> None:
    if name not in EVENT_FLAG_NAMES:
        raise ValueError(f"unknown event flag {name!r}")


def _pending_session(request: Request, response: Response) -> dict:
    """The session as this response will leave it: the `__session` cookie an
    earlier writer already put on `response`, else the one the request carried."""
    prefix = (COOKIE_NAME + "=").encode("latin-1")
    for key, value in response.raw_headers:
        if key == b"set-cookie" and value.startswith(prefix):
            raw = value[len(prefix):].split(b";", 1)[0].decode("latin-1")
            return _decode(raw)
    return _load_session(request)


def _replace_session(response: Response, data: dict) -> None:
    """`_write_session`, but any `__session` header already on the response goes."""
    prefix = (COOKIE_NAME + "=").encode("latin-1")
    response.raw_headers[:] = [
        (k, v) for k, v in response.raw_headers
        if not (k == b"set-cookie" and v.startswith(prefix))
    ]
    _write_session(response, data)


def _live_flags(data: dict) -> dict:
    ev = data.get("ev")
    if not isinstance(ev, dict):
        return {}
    now = time.time()
    return {k: v for k, v in ev.items()
            if k in EVENT_FLAG_NAMES and isinstance(v, (int, float)) and v > now}


def set_event_flag(request: Request, response: Response, name: str) -> None:
    """Mark that the next GET is the one that follows a completed `name`."""
    _check_flag_name(name)
    data = _pending_session(request, response)
    flags = _live_flags(data)
    flags[name] = int(time.time()) + EVENT_FLAG_TTL
    data["ev"] = flags
    _replace_session(response, data)


def event_flag_present(request: Request, name: str) -> bool:
    _check_flag_name(name)
    return name in _live_flags(_load_session(request))


def clear_event_flag(request: Request, response: Response, name: str) -> None:
    """Consume the flag. Call only when `event_flag_present` was True: this
    writes the year-long cookie, and a read-only GET must not (privacy.html
    promises visits that only read it do not extend it)."""
    _check_flag_name(name)
    data = _pending_session(request, response)
    flags = _live_flags(data)
    flags.pop(name, None)
    if flags:
        data["ev"] = flags
    else:
        data.pop("ev", None)
    _replace_session(response, data)


def load_collection(request: Request) -> ChartCollection:
    """Pull the ChartCollection out of the session cookie."""
    data = _load_session(request)
    raw_charts = data.get("charts", [])
    try:
        charts = tuple(SavedChart(**c) for c in raw_charts)
    except (TypeError, KeyError):
        return ChartCollection(charts=(), active_id=None)
    return ChartCollection(charts=charts, active_id=data.get("active_id"))


def save_collection(response: Response, collection: ChartCollection,
                    request: Request | None = None) -> None:
    """Write the chart collection without clobbering the lang preference.

    `request` lets us preserve the existing `lang` from the current session
    cookie. If omitted (rare — only legacy callers), lang gets reset to the
    default; pass `request` from any route handler that has it.
    """
    data = _load_session(request) if request is not None else {}
    data["charts"] = [asdict(c) for c in collection.charts]
    data["active_id"] = collection.active_id
    _write_session(response, data)


@dataclass(frozen=True)
class SavedMatching:
    """The user's most recent /matching submission.

    Persisted in the session cookie so /ask?ctx=matching can recover both
    charts on the follow-up without asking the user to re-enter. Both
    parties' full birth details are stored; the seeker can be either
    party (whoever they identify with) or a curious third-party (rare).
    """
    groom_name: str
    groom_birth_date: str
    groom_birth_time: str
    groom_birth_place: str
    bride_name: str
    bride_birth_date: str
    bride_birth_time: str
    bride_birth_place: str


def load_last_matching(request: Request) -> SavedMatching | None:
    """Read the most-recent matching submission from the session cookie.

    Returns None if the user hasn't done /matching in this session, or
    if the stored payload is malformed (e.g. schema change).
    """
    data = _load_session(request)
    raw = data.get("last_matching")
    if not isinstance(raw, dict):
        return None
    try:
        return SavedMatching(**raw)
    except (TypeError, KeyError):
        return None


def save_last_matching(response: Response, request: Request | None,
                        matching: SavedMatching) -> None:
    """Write the most-recent matching submission, preserving other session keys."""
    data = _load_session(request) if request is not None else {}
    data["last_matching"] = asdict(matching)
    _write_session(response, data)


def load_lang(request: Request) -> str:
    """Read the seeker's language preference. Defaults to English."""
    candidate = _load_session(request).get("lang", DEFAULT_LANG)
    return candidate if candidate in SUPPORTED_LANGS else DEFAULT_LANG


def save_lang(response: Response, lang: str, request: Request) -> None:
    """Write the lang preference without clobbering chart data."""
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    data = _load_session(request)
    data["lang"] = lang
    _write_session(response, data)


def clear_collection(response: Response) -> None:
    """Wipe the whole session — fresh start (clears chart + lang)."""
    response.delete_cookie(COOKIE_NAME)


# ─── Ask Bhagya rate-limit helpers ──────────────────────────────────────────
# Per-cookie daily counter keeps one user from draining the LLM provider's
# free tier. Kept in the same __session payload so we don't need a second
# cookie (Firebase only forwards one anyway — see module docstring).


def load_ask_usage(request: Request) -> tuple[str, int]:
    """Return (date_iso, count_used) of today's Ask Bhagya usage."""
    data = _load_session(request)
    return data.get("ask_date", ""), int(data.get("ask_count", 0))


def save_ask_usage(response: Response, request: Request,
                   date_iso: str, count: int) -> None:
    """Persist today's ask quota state into the session cookie."""
    data = _load_session(request)
    data["ask_date"] = date_iso
    data["ask_count"] = count
    _write_session(response, data)


# ─── Signed-in user helpers ─────────────────────────────────────────────────
# Google Sign-In stores a compact user record inside the same __session cookie
# (Firebase only forwards __session — hence one cookie for everything). Payload
# is small: email + display name + Google sub (unique ID) + signed-in-at ISO.
# Total ~150 bytes, well within the ~4KB per-cookie limit.


@dataclass(frozen=True)
class SessionUser:
    """The signed-in user, as persisted in the session cookie."""

    email: str
    name: str      # display name from Google; may be empty
    sub: str       # Google's stable unique user ID (safer than email as key)
    since: str     # ISO timestamp of when this session was authenticated


def _since_epoch(since: str) -> int | None:
    """`user.since` as epoch seconds, or None when empty/unparsable. A naive
    stamp (a date only) is read as UTC."""
    try:
        parsed = datetime.fromisoformat(since)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def load_user(request: Request) -> SessionUser | None:
    """Return the signed-in user for this request, or None if not signed in.

    Two server-side bounds beyond the cookie signature (#1106), both read off
    `since`, which every signed-in cookie already carries (legacy included):
    SIGNIN_MAX_AGE, fixed and not sliding, and a per-user `revoked_before`
    written by sign-out. Both treat an unusable `since` as signed out.
    """
    data = _load_session(request).get("user")
    if not isinstance(data, dict):
        return None
    try:
        user = SessionUser(
            email=str(data["email"]),
            name=str(data.get("name", "")),
            sub=str(data["sub"]),
            since=str(data.get("since", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None
    issued = _since_epoch(user.since)
    if issued is None or time.time() - issued > SIGNIN_MAX_AGE:
        return None
    # Imported here: revocation -> storage/hot_cache, and `users` imports this
    # module, so a module-level import would be a cycle waiting for a refactor.
    from astro_ai import revocation

    if issued <= revocation.revoked_before(user.sub):
        return None
    return user


def save_user(response: Response, request: Request, user: SessionUser) -> None:
    """Persist the signed-in user into the session cookie.

    Preserves other session state (charts, lang, ask usage) — this only
    writes the `user` key of the combined payload.
    """
    data = _load_session(request)
    data["user"] = asdict(user)
    _write_session(response, data)


def clear_user(response: Response, request: Request) -> None:
    """Sign out — remove the user record but keep other session state."""
    data = _load_session(request)
    data.pop("user", None)
    _write_session(response, data)


def save_session_atomic(
    response: Response,
    request: Request,
    *,
    user: "SessionUser | None" = None,
    collection: "ChartCollection | None" = None,
    lang: str | None = None,
) -> None:
    """Update multiple session fields in a SINGLE atomic cookie write.

    Fixes the multi-write clobber bug where two consecutive save_xxx()
    calls each read `_load_session(request)` (missing each other's
    writes, since the request cookie is snapshot at request start) and
    both call `response.set_cookie(COOKIE_NAME, ...)`, appending two
    Set-Cookie headers. Browsers keep only the LAST one, so the earlier
    write is silently thrown away.

    Concrete case this fixed (2026-07-28): sign-in on device 2 merged
    the user's cross-device charts into the cookie, but then save_user
    re-read the empty pre-sign-in request cookie and overwrote with a
    user-only cookie. Charts disappeared on the reload.
    """
    data = _load_session(request)
    if user is not None:
        data["user"] = asdict(user)
    if collection is not None:
        data["charts"] = [asdict(c) for c in collection.charts]
        data["active_id"] = collection.active_id
    if lang is not None:
        if lang not in SUPPORTED_LANGS:
            lang = DEFAULT_LANG
        data["lang"] = lang
    _write_session(response, data)
