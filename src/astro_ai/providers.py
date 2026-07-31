"""Multi-provider LLM client — proactive load balancing + reactive fallback.

Why this exists: a single LLM provider's free tier is small enough that one
active Bhagya user can exhaust it. We stack the free tiers of multiple
OpenAI-compatible providers (Groq, Cerebras, Together, Mistral — all serve
Llama 3.3 70B at the same API shape) and do two things at once:

  1. PROACTIVE LOAD BALANCING (default): every request gets a freshly
     randomized provider order. Across many requests, load distributes
     evenly across all configured providers — no single tier fills up
     while the others sit idle.

  2. REACTIVE FALLBACK: if the first provider returns 429 (rate limit) or
     any APIError, we fall through to the next provider in this request's
     randomized order. The user never sees a single-provider failure.

Net result: effective free quota = sum of all your providers' quotas,
and you never hit a 429 unless the union of every provider is exhausted.

Configuration — two modes:

  Mode 1 (recommended): explicit provider chain
    BHAGYA_LLM_PROVIDERS=groq,cerebras,together,openai
    GROQ_API_KEY=...
    CEREBRAS_API_KEY=...
    TOGETHER_API_KEY=...
    OPENAI_API_KEY=...                  # paid-tier safety net
    # Optional per-provider model overrides:
    # GROQ_MODEL=llama-3.1-8b-instant   # faster, smaller free tier
    # Optional balance mode (default 'random'):
    # BHAGYA_LLM_BALANCE=order          # use configured order strictly

  Mode 2 (legacy single-provider, kept for back-compat):
    OPENAI_API_KEY=...
    ASTRO_AI_API_BASE=https://api.groq.com/openai/v1   # optional
    ASTRO_AI_MODEL=llama-3.3-70b-versatile             # optional

Both modes coexist — explicit chain takes precedence when set. If neither is
configured, chat() raises NoProvidersConfigured with a clear message.
"""

from __future__ import annotations

import logging
import os
import random
from contextvars import ContextVar
from dataclasses import dataclass

from openai import OpenAI
from openai import APIError, APIConnectionError, APITimeoutError, RateLimitError

log = logging.getLogger(__name__)

# Per-request tracking: which (provider, model) actually served the call.
# Set inside chat() on the first success; readable by any downstream code
# in the same request (e.g. notify.kundli_generated wants to include it).
# Contextvars are async-safe and don't leak across requests.
_last_provider: ContextVar[str] = ContextVar("_last_provider", default="")
_last_model: ContextVar[str] = ContextVar("_last_model", default="")


def last_used_model() -> str:
    """Return the model that served the current request's LLM call.

    Format: `"<provider>:<model>"`, e.g. `"groq120:openai/gpt-oss-120b"`.
    Empty string if no chat() call happened this request (or if it failed).
    """
    prov = _last_provider.get("")
    mod = _last_model.get("")
    if not prov and not mod:
        return ""
    return f"{prov}:{mod}"


# ─── Response quality validation ─────────────────────────────────────
#
# Some smaller/misaligned models produce syntactically-successful responses
# (200 OK from the API) that are semantically broken — no section headings,
# way too short, refusals, etc. Without validation these silently poison
# the cache and users see empty "Reading" boxes.
#
# passes_quality() below is called by chat() after each provider succeeds;
# a failure is treated identically to a 429 and the chain moves on. First
# hit was 2026-07-28 where openai/gpt-oss-20b returned a natal reading
# without the `## Heading` markers our parser needs.


# Minimum chars we'd accept for each route. Below this the response is
# certainly truncated or a refusal. Tuned to the shortest a real reading
# would ever be, minus generous slack.
_MIN_CHARS_BY_ROUTE: dict[str, int] = {
    "natal":    800,
    "outlook":  500,
    "matching": 500,
    "today":    400,
    "dasha":    300,
    "rashifal": 200,
    # Per-rashi rashifal (single Moon-sign, 120-160 words) — used by the
    # flip-card /rashifal/{slug} endpoint. Deliberately NOT in
    # _STRUCTURED_ROUTES because it emits exactly ONE `## Heading` (its
    # own rashi's name) — the multi-heading gate would reject every
    # successful generation.
    "rashifal_single": 300,
    "ask":      100,
}

# Routes whose prompts require the model to emit `## Heading` blocks. If
# the model returns fewer than 2 headings on these routes, the parser
# collapses to a single "Reading" fallback and the user sees an empty
# card — treat as failure and fall through.
#
# NOTE: `today` (daily.txt) is DELIBERATELY unsectioned — the prompt says
# "four flowing paragraphs separated by blank lines" and "DO NOT output
# bare `##` markers anywhere." Same for `ask`. Do not add either to this
# set; both use min-length as the only structural check.
_STRUCTURED_ROUTES: set[str] = {
    "natal", "outlook", "matching", "dasha", "rashifal",
}


def passes_quality(text: str, route: str) -> tuple[bool, str]:
    """Return (ok, reason). Called after each provider's chat() success."""
    stripped = (text or "").strip()
    if not stripped:
        return False, "empty response"
    min_chars = _MIN_CHARS_BY_ROUTE.get(route, 60)
    if len(stripped) < min_chars:
        return False, f"response too short ({len(stripped)} chars < {min_chars} min for {route})"
    if route in _STRUCTURED_ROUTES:
        # Count `## ` at line start — same rule the parser uses.
        heading_count = sum(1 for line in stripped.splitlines() if line.startswith("## "))
        if heading_count < 2:
            return False, f"only {heading_count} '## Heading' markers (need ≥2 for {route})"
    return True, ""


@dataclass(frozen=True)
class ProviderConfig:
    """One OpenAI-compatible provider in the fallback chain.

    api_base=None means OpenAI's default endpoint (api.openai.com).
    Per-provider model overrides come from {NAME}_MODEL env vars at lookup time.
    """
    name: str
    api_base: str | None
    default_model: str
    api_key_env: str

    def model(self) -> str:
        return os.environ.get(f"{self.name.upper()}_MODEL", self.default_model)

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


# Registry of known providers — all OpenAI-compatible. Defaults picked for the
# best quality-on-free-tier balance as of mid-2026.
#
# NOTE on the Groq default: Groq deprecated `llama-3.3-70b-versatile` on
# 2026-08-16 (announced mid-July 2026). We default Groq to `openai/gpt-oss-120b`
# — the higher-quality of the two replacements Groq recommended (the other
# being Qwen3 27B, which we passed on because our bilingual narrative use case
# rewards the larger model). Cerebras + Together still serve Llama 3.3 70B, so
# the fallback chain keeps a mixed model mix — that's fine at the API surface
# but expect slight tonal drift between providers. Override any default via
# the `{NAME}_MODEL` env var without a code change.
PROVIDERS: dict[str, ProviderConfig] = {
    # Groq: default model + per-model chain variants. Groq's free-tier quotas
    # are keyed PER MODEL (not per account), so listing multiple Groq models
    # in BHAGYA_LLM_PROVIDERS gives Nx effective daily capacity from a single
    # GROQ_API_KEY. Recommended chain:
    #   BHAGYA_LLM_PROVIDERS=groq120,groq20,groq_qwen,groq_l33,groq8
    # Random-shuffle balance (default) distributes load across all five.
    # Quality tiers (rough): 120b ≈ l33 ≥ 20b ≈ qwen > 8b for narrative depth.
    # See https://console.groq.com/docs/models for the current model list.
    "groq":       ProviderConfig("groq",       "https://api.groq.com/openai/v1",
                                  "openai/gpt-oss-120b",                       "GROQ_API_KEY"),
    "groq120":    ProviderConfig("groq120",    "https://api.groq.com/openai/v1",
                                  "openai/gpt-oss-120b",                       "GROQ_API_KEY"),
    "groq20":     ProviderConfig("groq20",     "https://api.groq.com/openai/v1",
                                  "openai/gpt-oss-20b",                        "GROQ_API_KEY"),
    "groq_qwen":  ProviderConfig("groq_qwen",  "https://api.groq.com/openai/v1",
                                  "qwen/qwen3.6-27b",                          "GROQ_API_KEY"),
    # Deprecates 2026-08-16 — remove from chain before then. Kept while
    # available because it's still high-quality free capacity.
    "groq_l33":   ProviderConfig("groq_l33",   "https://api.groq.com/openai/v1",
                                  "llama-3.3-70b-versatile",                   "GROQ_API_KEY"),
    "groq8":      ProviderConfig("groq8",      "https://api.groq.com/openai/v1",
                                  "llama-3.1-8b-instant",                      "GROQ_API_KEY"),
    "cerebras": ProviderConfig("cerebras", "https://api.cerebras.ai/v1",
                                "llama3.3-70b",                              "CEREBRAS_API_KEY"),
    "together": ProviderConfig("together", "https://api.together.xyz/v1",
                                "meta-llama/Llama-3.3-70B-Instruct-Turbo",   "TOGETHER_API_KEY"),
    "mistral":  ProviderConfig("mistral",  "https://api.mistral.ai/v1",
                                "mistral-large-latest",                      "MISTRAL_API_KEY"),
    "openai":   ProviderConfig("openai",   None,
                                "gpt-4o-mini",                               "OPENAI_API_KEY"),
}


class NoProvidersConfigured(RuntimeError):
    """Raised when no usable provider is available — bad config, not a runtime issue."""


class AllProvidersExhausted(RuntimeError):
    """Raised when every provider in the chain returned 429 or errored.

    Caller (typically a route handler) should turn this into a friendly
    "high demand right now, try again in a few minutes" page rather than a 502.
    """


def _legacy_provider() -> ProviderConfig | None:
    """Build a one-element chain from the old single-provider env vars.

    Preserves backwards-compat with deploys that set OPENAI_API_KEY +
    ASTRO_AI_API_BASE + ASTRO_AI_MODEL but haven't migrated to
    BHAGYA_LLM_PROVIDERS yet.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    return ProviderConfig(
        name="legacy",
        api_base=os.environ.get("ASTRO_AI_API_BASE"),
        default_model=os.environ.get("ASTRO_AI_MODEL", "gpt-4o-mini"),
        api_key_env="OPENAI_API_KEY",
    )


def _chain() -> list[ProviderConfig]:
    """Resolve the active provider chain. Explicit env override wins."""
    explicit = os.environ.get("BHAGYA_LLM_PROVIDERS", "").strip()
    if explicit:
        out: list[ProviderConfig] = []
        for name in explicit.split(","):
            name = name.strip().lower()
            if name not in PROVIDERS:
                log.warning("provider chain: unknown provider %r — skipping", name)
                continue
            p = PROVIDERS[name]
            if not p.api_key():
                log.warning("provider chain: %s has no %s — skipping", name, p.api_key_env)
                continue
            out.append(p)
        return out
    # Legacy single-provider fallback for unmigrated deploys.
    legacy = _legacy_provider()
    return [legacy] if legacy else []


def _call_one(provider: ProviderConfig, messages: list[dict]) -> str:
    """Issue the chat completion to one provider; raise on any failure."""
    client = OpenAI(
        api_key=provider.api_key(),
        base_url=provider.api_base,  # OpenAI() accepts None to mean default
    )
    response = client.chat.completions.create(
        model=provider.model(),
        messages=messages,
    )
    return response.choices[0].message.content or ""


def _ordered_for_request() -> list[ProviderConfig]:
    """Pick the provider order for a single request.

    'random' (default) shuffles for each request — that's the load-balancer
    behaviour. 'order' keeps the configured chain strict — useful when you've
    deliberately put a paid provider last as a safety net and don't want
    randomization to spend money when free options were available.
    """
    chain = _chain()
    if not chain:
        return chain
    balance = os.environ.get("BHAGYA_LLM_BALANCE", "random").strip().lower()
    if balance != "random":
        return chain
    shuffled = chain.copy()
    random.shuffle(shuffled)
    return shuffled


def chat(messages: list[dict], *, route: str = "") -> str:
    """Send `messages` through the configured provider chain.

    Order resolution: random shuffle per request (default), or strict
    configured order if BHAGYA_LLM_BALANCE=order. On RateLimitError (429)
    or any APIError we log and fall through to the next provider in this
    request's order. Raises AllProvidersExhausted when nothing works —
    callers should treat that as user-visible degradation, not a bug.

    `route` is a short label for the calling feature ("natal", "ask", ...)
    used for the /admin/usage per-route breakdown. Defaults to empty which
    aggregates under "unknown".

    Returns the assistant's text content.
    """
    order = _ordered_for_request()
    if not order:
        raise NoProvidersConfigured(
            "No LLM provider configured. Set BHAGYA_LLM_PROVIDERS=groq,cerebras,... "
            "with the matching {NAME}_API_KEY env vars, or set OPENAI_API_KEY for the "
            "legacy single-provider mode."
        )

    last_err: Exception | None = None
    for provider in order:
        try:
            text = _call_one(provider, messages)
            # Quality gate — some models return 200 OK but semantically
            # broken output (no headings, refusals, truncation). Fall
            # through to the next model rather than caching garbage.
            ok, reason = passes_quality(text, route)
            if not ok:
                log.warning(
                    "provider %s returned bad output for route=%s (%s) — trying next",
                    provider.name, route, reason,
                )
                last_err = RuntimeError(f"quality-fail: {provider.name} for {route}: {reason}")
                continue
            # Track which (provider, model) served this request. Downstream
            # code (notify.kundli_generated etc.) reads via last_used_model().
            _last_provider.set(provider.name)
            _last_model.set(provider.model())
            # Structured log line — Cloud Logging indexes JSON fields so you
            # can filter/graph by provider+model in Log Explorer without any
            # extra storage or dashboard code. Example query:
            #   jsonPayload.event="llm_call" AND jsonPayload.provider="groq120"
            log.info(
                "llm_call",
                extra={"json_fields": {
                    "event": "llm_call",
                    "provider": provider.name,
                    "model": provider.model(),
                    "route": route,
                    "fallback_from": last_err is not None,
                    "chars_out": len(text),
                }},
            )
            # Persistent per-day counter for /admin/usage. Best-effort;
            # never propagates errors. Circular-import-safe via lazy import.
            try:
                from astro_ai import llm_stats
                llm_stats.record(
                    provider=provider.name,
                    model=provider.model(),
                    route=route,
                    fallback=(last_err is not None),
                )
            except Exception:  # noqa: BLE001 — stats never break the reading
                log.debug("llm_stats.record failed", exc_info=True)
            if last_err is not None:
                log.info("provider %s succeeded after upstream failures", provider.name)
            return text
        except RateLimitError as err:
            log.warning("provider %s rate-limited (%s) — trying next in chain", provider.name, err)
            last_err = err
        except (APIError, APIConnectionError, APITimeoutError) as err:
            log.warning("provider %s API error (%s) — trying next in chain", provider.name, err)
            last_err = err
        except Exception as err:
            # Defensive: don't let one provider's weird error kill the whole request.
            log.warning("provider %s unexpected error (%s) — trying next in chain", provider.name, err)
            last_err = err

    raise AllProvidersExhausted(
        f"All {len(order)} provider(s) in chain failed. Last error: {last_err!r}"
    )


def active_provider_names() -> list[str]:
    """For /admin/usage — show which providers are configured + reachable."""
    return [p.name for p in _chain()]
