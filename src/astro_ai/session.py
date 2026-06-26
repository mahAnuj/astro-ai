"""Signed-cookie persistence for a SEEKER'S COLLECTION of saved charts.

The cookie holds:
    {"charts": [SavedChart, ...], "active_id": "abc12345"}

`itsdangerous` HMAC-signs the JSON payload with `ASTRO_AI_COOKIE_SECRET`;
any tampering invalidates the signature and we treat the visitor as fresh.

Capped at MAX_CHARTS so the cookie can't grow unbounded — at ~150 bytes per
SavedChart, 10 fits comfortably inside the 4 KB browser cookie limit.

Old single-chart cookies (a flat BirthDetails dict, pre-multi-chart) are
migrated transparently on read into a 1-chart collection.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import asdict, dataclass, replace
from typing import Final

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from astro_ai.llm import BirthDetails

COOKIE_NAME: Final[str] = "astro_ai_chart"
COOKIE_MAX_AGE: Final[int] = 60 * 60 * 24 * 365  # 1 year
MAX_CHARTS: Final[int] = 10
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
# Cookie I/O
# ---------------------------------------------------------------------------


def _serializer() -> URLSafeSerializer:
    secret = os.environ.get("ASTRO_AI_COOKIE_SECRET") or _DEV_SECRET
    return URLSafeSerializer(secret, salt="birth-details")


def load_collection(request: Request) -> ChartCollection:
    """Read + decode the cookie, or return an empty collection."""
    raw = request.cookies.get(COOKIE_NAME)
    if raw is None:
        return ChartCollection(charts=(), active_id=None)
    try:
        data = _serializer().loads(raw)
    except BadSignature:
        return ChartCollection(charts=(), active_id=None)
    if not isinstance(data, dict):
        return ChartCollection(charts=(), active_id=None)

    # Migrate the old single-chart format: a flat BirthDetails dict.
    if "charts" not in data:
        try:
            legacy = BirthDetails(**data)
        except TypeError:
            return ChartCollection(charts=(), active_id=None)
        return ChartCollection(charts=(), active_id=None).add(legacy)

    try:
        charts = tuple(SavedChart(**c) for c in data["charts"])
    except (TypeError, KeyError):
        return ChartCollection(charts=(), active_id=None)
    return ChartCollection(charts=charts, active_id=data.get("active_id"))


def save_collection(response: Response, collection: ChartCollection) -> None:
    """Sign and write the collection cookie on `response`."""
    payload = _serializer().dumps(
        {
            "charts": [asdict(c) for c in collection.charts],
            "active_id": collection.active_id,
        }
    )
    response.set_cookie(
        COOKIE_NAME,
        payload,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # dev only; flip to True when behind HTTPS
    )


def clear_collection(response: Response) -> None:
    """Wipe everything — fresh start."""
    response.delete_cookie(COOKIE_NAME)
