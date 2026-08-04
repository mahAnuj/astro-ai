"""Optional per-call LLM output logger for editorial spot-check review.

Enabled via BHAGYA_LLM_REVIEW=1 (default off). When on, every successful
LLM response — after reasoning-envelope stripping and quality-gate
approval — is appended to data/llm_review/YYYY-MM-DD.jsonl. Purpose:
eyeball outputs for a week or two after shipping a fix (like the
reasoning-leak strip) to confirm nothing regresses before turning the
logger off again.

Records are JSONL, one per call:
  {"ts": "...Z", "route": "ask", "provider": "groq120",
   "model": "openai/gpt-oss-120b",
   "chars_raw": 2431, "chars_cleaned": 987, "leaked_reasoning": true,
   "text": "..."}

Only the cleaned text is stored; raw is intentionally NOT persisted (it
can contain the exact prompt-injection payload that caused a leak, and
keeping it invites replay bugs). Files auto-rotate per date; a small
purge trims files older than BHAGYA_LLM_REVIEW_KEEP_DAYS (default 14).

Best-effort — a write failure never breaks the reading.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

log = logging.getLogger(__name__)


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


_MAX_TEXT_CHARS = 8000
_LOCK = Lock()
_last_purge_epoch = 0.0


def _dir() -> Path:
    return Path(os.environ.get("BHAGYA_LLM_REVIEW_DIR", "data/llm_review"))


def _keep_days() -> int:
    try:
        return max(1, int(os.environ.get("BHAGYA_LLM_REVIEW_KEEP_DAYS", "14")))
    except ValueError:
        return 14


def is_enabled() -> bool:
    return _flag("BHAGYA_LLM_REVIEW")


def record(
    *,
    route: str,
    provider: str,
    model: str,
    text: str,
    chars_raw: int,
    leaked_reasoning: bool,
) -> None:
    """Append one review record. Never raises.

    Called from providers.chat() after quality-gate approval. Silently
    returns if BHAGYA_LLM_REVIEW is not set — zero cost when off.
    """
    if not is_enabled():
        return
    try:
        target_dir = _dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{date.today().isoformat()}.jsonl"
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "route": route or "unknown",
            "provider": provider,
            "model": model,
            "chars_raw": chars_raw,
            "chars_cleaned": len(text),
            "leaked_reasoning": leaked_reasoning,
            "text": text[:_MAX_TEXT_CHARS],
        }
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
        _maybe_purge(target_dir)
    except Exception:  # noqa: BLE001 — review log never breaks the call
        log.debug("llm_review.record failed", exc_info=True)


def _maybe_purge(target_dir: Path) -> None:
    """Trim files older than the keep window. Runs at most once per hour."""
    global _last_purge_epoch
    now = time.time()
    if now - _last_purge_epoch < 3600:
        return
    _last_purge_epoch = now
    try:
        cutoff = date.today() - timedelta(days=_keep_days())
        for f in target_dir.glob("*.jsonl"):
            try:
                file_date = date.fromisoformat(f.stem)
            except ValueError:
                continue
            if file_date < cutoff:
                f.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
