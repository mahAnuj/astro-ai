"""Signed-cookie persistence for the seeker's session state.

The cookie holds a combined payload:
    {
      "charts": [SavedChart, ...],
      "active_id": "abc12345",
      "lang": "en"     # 'en' or 'hi'
    }

`itsdangerous` HMAC-signs the JSON payload with `ASTRO_AI_COOKIE_SECRET`;
any tampering invalidates the signature and we treat the visitor as fresh.

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
from dataclasses import asdict, dataclass, replace
from typing import Final

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from astro_ai.llm import BirthDetails

# Must be exactly "__session" — see module docstring for why.
COOKIE_NAME: Final[str] = "__session"
COOKIE_MAX_AGE: Final[int] = 60 * 60 * 24 * 365  # 1 year
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


def _serializer() -> URLSafeSerializer:
    secret = os.environ.get("ASTRO_AI_COOKIE_SECRET") or _DEV_SECRET
    return URLSafeSerializer(secret, salt="birth-details")


def _load_session(request: Request) -> dict:
    """Read + decode the cookie, or return an empty dict. All callers go through
    this so we only HMAC-verify once per request."""
    raw = request.cookies.get(COOKIE_NAME)
    if raw is None:
        return {}
    try:
        data = _serializer().loads(raw)
    except BadSignature:
        return {}
    return data if isinstance(data, dict) else {}


def _write_session(response: Response, data: dict) -> None:
    """Sign and write the combined session payload."""
    payload = _serializer().dumps(data)
    response.set_cookie(
        COOKIE_NAME,
        payload,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # dev only; flip to True when behind HTTPS-only
    )


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


def load_user(request: Request) -> SessionUser | None:
    """Return the signed-in user for this request, or None if not signed in."""
    data = _load_session(request).get("user")
    if not isinstance(data, dict):
        return None
    try:
        return SessionUser(
            email=str(data["email"]),
            name=str(data.get("name", "")),
            sub=str(data["sub"]),
            since=str(data.get("since", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


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
