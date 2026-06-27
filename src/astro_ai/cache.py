"""LLM-call cache + observability.

Two jobs in one module so we don't end up with two SQLite files:

1. CACHE expensive reading generations to avoid recomputing them. Many of our
   reads are deterministic given (chart, date) — natal reads are identical
   forever, daily reads identical for 24h, etc. Cache hits massively reduce
   token usage and let the free tier serve real traffic.

2. LOG every LLM-bound call (cache hit or miss) with route, language,
   estimated tokens, and latency. Feeds the `/admin/usage` dashboard so we
   can see WHICH features are eating tokens and tune accordingly.

Storage: a single SQLite database file (default `bhagya.db` in the working
directory; override with the `BHAGYA_CACHE_DB` env var). Two tables:

    llm_cache  (cache_key PK, text, created_at, expires_at, route, tokens)
    llm_calls  (id PK, timestamp, route, lang, cache_hit, tokens, latency_ms)

Why SQLite over Redis/etc.: zero setup, file-based persistence across server
restarts, fine up to ~10K writes/second. When traffic actually warrants
Redis, swap the storage layer behind the same `get`/`put`/`log_call` API.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

DB_PATH: Path = Path(os.environ.get("BHAGYA_CACHE_DB", "bhagya.db"))
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS llm_cache (
            cache_key      TEXT PRIMARY KEY,
            text           TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            expires_at     TEXT,
            route          TEXT NOT NULL,
            input_tokens   INTEGER DEFAULT 0,
            output_tokens  INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS llm_calls (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      TEXT NOT NULL,
            route          TEXT NOT NULL,
            lang           TEXT NOT NULL,
            cache_hit      INTEGER NOT NULL,
            input_tokens   INTEGER DEFAULT 0,
            output_tokens  INTEGER DEFAULT 0,
            latency_ms     INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_calls_timestamp ON llm_calls(timestamp);
        CREATE INDEX IF NOT EXISTS idx_cache_expires   ON llm_cache(expires_at);
        """
    )


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    """Thread-safe sqlite session — coarse lock is fine at our scale."""
    with _LOCK:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        try:
            _init_db(conn)
            yield conn
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Fingerprints — stable hashes used as parts of cache keys
# ---------------------------------------------------------------------------


def fingerprint_chart(birth_date: str, birth_time: str, birth_place: str) -> str:
    """Stable 16-char hash of birth details. Same inputs → same hash.

    Used as the per-chart cache namespace so two seekers with identical birth
    details share cached readings (e.g. twins) and so a single seeker's
    repeated visits hit the same cache key.
    """
    raw = f"{birth_date}|{birth_time}|{birth_place.lower().strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def fingerprint_prompt(prompt_path: Path) -> str:
    """8-char hash of prompt file content. Edit the prompt → cache invalidates.

    Without this, a prompt rewrite would silently keep serving the OLD reading
    for cached entries forever. Including the hash in every cache key forces a
    regeneration the moment the prompt file changes.
    """
    return hashlib.sha256(prompt_path.read_bytes()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Cache API
# ---------------------------------------------------------------------------


def get(cache_key: str) -> str | None:
    """Return cached text if present and unexpired; None otherwise."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        row = c.execute(
            "SELECT text, expires_at FROM llm_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if row is None:
        return None
    text, expires_at = row
    if expires_at and expires_at < now:
        return None
    return text


def put(
    cache_key: str,
    text: str,
    *,
    route: str,
    ttl_days: int | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Store `text` under `cache_key` with optional TTL (None = never expires)."""
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=ttl_days)).isoformat() if ttl_days else None
    with _conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO llm_cache
                (cache_key, text, created_at, expires_at, route, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (cache_key, text, now.isoformat(), expires_at, route, input_tokens, output_tokens),
        )


def log_call(
    route: str,
    lang: str,
    *,
    cache_hit: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
) -> None:
    """Append a row to llm_calls for the /admin/usage dashboard."""
    with _conn() as c:
        c.execute(
            """
            INSERT INTO llm_calls
                (timestamp, route, lang, cache_hit, input_tokens, output_tokens, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                route,
                lang,
                int(cache_hit),
                input_tokens,
                output_tokens,
                latency_ms,
            ),
        )


def estimate_tokens(text: str) -> int:
    """Rough token estimate from text length.

    Latin script ~4 chars/token; Devanagari (Hindi) ~2.5 chars/token because
    it's denser. Good enough for /admin/usage trend lines — the source of
    truth for exact billing is the LLM provider's dashboard.
    """
    has_devanagari = any("ऀ" <= c <= "ॿ" for c in text)
    chars_per_token = 2.5 if has_devanagari else 4.0
    return max(1, int(len(text) / chars_per_token))


# ---------------------------------------------------------------------------
# Usage summary for the /admin/usage page
# ---------------------------------------------------------------------------


def usage_summary(days: int = 1) -> dict[str, object]:
    """Aggregated stats over the last `days` days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _conn() as c:
        totals_row = c.execute(
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN cache_hit=1 THEN 1 ELSE 0 END),
                SUM(input_tokens),
                SUM(output_tokens),
                AVG(CASE WHEN cache_hit=0 THEN latency_ms ELSE NULL END)
            FROM llm_calls WHERE timestamp > ?
            """,
            (cutoff,),
        ).fetchone()
        by_route_rows = c.execute(
            """
            SELECT
                route,
                COUNT(*),
                SUM(CASE WHEN cache_hit=1 THEN 1 ELSE 0 END),
                SUM(input_tokens),
                SUM(output_tokens)
            FROM llm_calls WHERE timestamp > ?
            GROUP BY route ORDER BY COUNT(*) DESC
            """,
            (cutoff,),
        ).fetchall()
        cache_count = c.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]

    total_calls = totals_row[0] or 0
    cache_hits = totals_row[1] or 0
    return {
        "days": days,
        "total_calls": total_calls,
        "cache_hits": cache_hits,
        "cache_misses": total_calls - cache_hits,
        "hit_rate_pct": int(cache_hits / total_calls * 100) if total_calls else 0,
        "total_input_tokens": totals_row[2] or 0,
        "total_output_tokens": totals_row[3] or 0,
        "avg_miss_latency_ms": int(totals_row[4]) if totals_row[4] else 0,
        "by_route": [
            {
                "route": r[0],
                "calls": r[1],
                "hits": r[2],
                "hit_rate_pct": int(r[2] / r[1] * 100) if r[1] else 0,
                "input_tokens": r[3] or 0,
                "output_tokens": r[4] or 0,
            }
            for r in by_route_rows
        ],
        "cache_entries": cache_count,
    }
