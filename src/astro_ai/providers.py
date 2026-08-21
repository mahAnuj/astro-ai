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
import re
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass

from openai import BadRequestError, OpenAI
from openai import APIError, APIConnectionError, APITimeoutError, RateLimitError

log = logging.getLogger(__name__)


# Reasoning-model envelopes we strip before rendering. Groq's
# openai/gpt-oss-*, DeepSeek-R1, Qwen QWQ and other reasoning-tuned models
# emit their internal chain-of-thought as visible text (usually inside
# <think>...</think>). Shipping that raw dumps the whole planning process
# to the user — a real Bhagya user emailed to show /ask returning
# "<think> Here's a thinking process: ... Constraints: Answer FIRST
# directly, NO planet/sign/house names... ✅ Ready." verbatim. Every LLM
# response through the provider chain must be cleaned before it reaches
# quality gates, cache, or the template.
_REASONING_BLOCK_PATTERNS = [
    re.compile(r"<\s*think(?:ing)?\s*>.*?<\s*/\s*think(?:ing)?\s*>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<\s*reason(?:ing)?\s*>.*?<\s*/\s*reason(?:ing)?\s*>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<\s*analysis\s*>.*?<\s*/\s*analysis\s*>", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[\s*REASONING\s*\].*?\[\s*/\s*REASONING\s*\]", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[\s*THINK(?:ING)?\s*\].*?\[\s*/\s*THINK(?:ING)?\s*\]", re.DOTALL | re.IGNORECASE),
]

# Orphan reasoning-opener anywhere in the text (paired block removal has
# already run). If any survivor is found, everything from that opener to
# end-of-string is treated as reasoning-in-progress that got truncated,
# and dropped. This catches shapes like:
#   "Your reading is X <think>need to double-check..." (truncated mid-answer)
# where the answer prefix is preserved and the leaking scratchpad is cut.
# When the opener is at position 0 the whole text is dropped (empty →
# quality gate fails → chain falls through).
_ORPHAN_REASONING_OPENER = re.compile(
    r"<\s*(?:think(?:ing)?|reason(?:ing)?|analysis)\s*>|\[\s*(?:THINK(?:ING)?|REASONING)\s*\]",
    re.IGNORECASE,
)

# Orphan reasoning-closer (rare: model emitted `</think>` with no opener,
# usually a mangled shape). Just delete the tag; keep surrounding text.
_ORPHAN_REASONING_CLOSER = re.compile(
    r"<\s*/\s*(?:think(?:ing)?|reason(?:ing)?|analysis)\s*>|\[\s*/\s*(?:THINK(?:ING)?|REASONING)\s*\]",
    re.IGNORECASE,
)

# Leading meta-preambles some non-reasoning models slip in. Only stripped
# at the very start of the text; conservative on purpose.
_META_PREAMBLE_PATTERNS = [
    re.compile(r"^\s*(?:Here'?s|Here is)\s+(?:my|the|a)\s+(?:thinking|reasoning|analysis|thought)\s+process[:\-]?\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:Let me|I'll|I will)\s+(?:think|analyze|reason)\s+(?:through|about|step[- ]by[- ]step)[^\n.]*[.\n:]\s*", re.IGNORECASE),
    re.compile(r"^\s*\*\*Analyze User Input:\*\*.*?(?=\n\s*\n|\Z)", re.DOTALL | re.IGNORECASE),
]


def strip_reasoning_envelope(text: str) -> str:
    """Strip LLM reasoning-chain leakage from raw model output.

    Applied inside chat() so every provider response is cleaned before
    it reaches quality gates, cache, or the template. Defensive against:
      - <think>...</think> and <thinking>...</thinking> (Groq gpt-oss,
        DeepSeek-R1, Qwen)
      - <reason>...</reason>, <analysis>...</analysis>
      - [REASONING]...[/REASONING], [THINK]...[/THINK]
      - Unclosed opener (truncated response) — returned as "" so quality
        gate fails cleanly and the chain falls through
      - Leading meta preambles ("Here's my thinking process:", etc.)

    Whitespace is collapsed around removed blocks. Returns "" if nothing
    salvageable remains.
    """
    if not text:
        return text
    cleaned = text
    # 1. Remove paired reasoning blocks anywhere in the text.
    for pattern in _REASONING_BLOCK_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    # 2. Any surviving orphan opener (truncated response, mid-text leak)
    #    → drop everything from the opener onward. Preserves any answer
    #    prefix; when opener is at position 0 the result is empty.
    m = _ORPHAN_REASONING_OPENER.search(cleaned)
    if m:
        cleaned = cleaned[:m.start()]
    # 3. Any surviving orphan closer (rare mangled shape) → delete the
    #    tag itself, keep surrounding text.
    cleaned = _ORPHAN_REASONING_CLOSER.sub("", cleaned)
    cleaned = cleaned.strip()
    if not cleaned:
        return ""
    # 4. Strip a small set of common leading meta-preambles.
    for pattern in _META_PREAMBLE_PATTERNS:
        cleaned = pattern.sub("", cleaned, count=1)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned

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
    # are keyed PER MODEL, so listing several Groq MODELS in
    # BHAGYA_LLM_PROVIDERS multiplies effective TPM from a single GROQ_API_KEY.
    #
    # VERIFIED against GET /openai/v1/models on 2026-08-20, because this table
    # had gone stale and the staleness was invisible: production was running
    # `groq120,groq_qwen,groq_l33,groq8` and TWO of those four models no longer
    # exist. `_chain()` only skips a provider when its API KEY is missing, so a
    # decommissioned model stays in the chain, is counted as a provider, fails
    # at call time, and contributes nothing. The effect was a nominally
    # four-provider chain delivering two models' worth of quota — which is what
    # exhausted the daily rashifal job.
    #
    # Groq's whole catalogue is 13 models and most are not usable here: two
    # Whisper (speech-to-text), two Orpheus (TTS), three safety classifiers
    # (prompt-guard at 512-token context, and gpt-oss-safeguard), and
    # allam-2-7b (Arabic, 4k context). What remains for narrative generation is
    # the three below plus `groq/compound` and `groq/compound-mini`, which are
    # AGENTIC models that can invoke tool use and web search — deliberately not
    # added, because a model that browses can import outside claims into a
    # chart-grounded reading. Try them behind a review before trusting them.
    #
    # Current recommended chain — the two BOUNDABLE live models:
    #   BHAGYA_LLM_PROVIDERS=groq120,groq20
    # Do NOT also list "groq": it resolves to the same model as groq120 and
    # would share one TPM bucket while looking like extra capacity.
    #
    # groq_qwen IS DELIBERATELY NOT IN THAT CHAIN, and the reason is measured,
    # not aesthetic. qwen3.6-27b rejects `reasoning_effort` with a 400, so it
    # is the one model here we cannot bound. Left unbounded it reasons until it
    # hits its own completion limit, gets truncated mid-`<think>`, and the
    # envelope stripper then cleans it to zero visible characters — a ~40s call
    # that returns nothing and falls through to the next provider. Twelve of
    # those per language is the whole of the overage:
    #
    #   full 2-language rashifal job, groq120,groq_qwen : 399s  (timeout 300s)
    #   same job, groq120,groq20                        : 213s  (83s en + 130s hi)
    #
    # Measured 2026-08-22 against the live API, on the code in this file.
    # Adding qwen back for its extra TPM bucket is a trade that LOSES: the
    # bucket is worth less than the wall-clock its empty calls burn.
    # Quality tiers (rough): 120b > qwen > 20b for narrative depth — which is
    # why qwen looks attractive on paper. It is not usable here until either
    # Groq accepts reasoning_effort for it or we set an explicit
    # max_completion_tokens high enough for it to CLOSE the envelope (we set
    # no completion cap at all today; the truncation is the model's own).
    "groq":       ProviderConfig("groq",       "https://api.groq.com/openai/v1",
                                  "openai/gpt-oss-120b",                       "GROQ_API_KEY"),
    "groq120":    ProviderConfig("groq120",    "https://api.groq.com/openai/v1",
                                  "openai/gpt-oss-120b",                       "GROQ_API_KEY"),
    "groq20":     ProviderConfig("groq20",     "https://api.groq.com/openai/v1",
                                  "openai/gpt-oss-20b",                        "GROQ_API_KEY"),
    "groq_qwen":  ProviderConfig("groq_qwen",  "https://api.groq.com/openai/v1",
                                  "qwen/qwen3.6-27b",                          "GROQ_API_KEY"),
    # REMOVED 2026-08-20, both confirmed 404 model_not_found:
    #   groq_l33  llama-3.3-70b-versatile  (its own comment said "remove before
    #             2026-08-16"; the date passed and it stayed in the chain)
    #   groq8     llama-3.1-8b-instant
    # Left as a note rather than deleted silently, so the next person adding a
    # Groq entry checks the live model list first instead of trusting this file.
    "cerebras": ProviderConfig("cerebras", "https://api.cerebras.ai/v1",
                                "llama3.3-70b",                              "CEREBRAS_API_KEY"),
    "together": ProviderConfig("together", "https://api.together.xyz/v1",
                                "meta-llama/Llama-3.3-70B-Instruct-Turbo",   "TOGETHER_API_KEY"),
    "mistral":  ProviderConfig("mistral",  "https://api.mistral.ai/v1",
                                "mistral-large-latest",                      "MISTRAL_API_KEY"),
    "openai":   ProviderConfig("openai",   None,
                                "gpt-4o-mini",                               "OPENAI_API_KEY"),
}


class EmptyCompletion(RuntimeError):
    """A provider returned 200 with no visible text.

    Its own error class so the chain can treat it as a provider failure and
    move on, rather than the caller receiving "" and caching it as a reading.
    """


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


# Models that rejected `reasoning_effort` with a 400. Learned at runtime rather
# than hardcoded, because a hardcoded model list is exactly what went stale and
# broke production: two entries in PROVIDERS pointed at decommissioned models
# for days, and a third was added after checking only that Groq LISTED it —
# never that it could complete a reading. A capability probed from the API
# cannot drift the way a list maintained by hand does.
_NO_REASONING_EFFORT: set[str] = set()
_NO_REASONING_LOCK = threading.Lock()


def _call_one(provider: ProviderConfig, messages: list[dict]) -> str:
    """Issue the chat completion to one provider; raise on any failure.

    Two behaviours here exist because of a production outage on 2026-08-21,
    where the daily rashifal blast returned 503 and subscribers got no email.

    REASONING BUDGET. Groq's gpt-oss models are reasoning models. Left
    unbounded they can spend their entire completion budget on hidden
    reasoning and return an EMPTY message — `finish_reason="length"`,
    thousands of completion tokens, zero visible characters. Measured on the
    live rashifal prompt, that is a coin flip per call, not a property of a
    particular model: in one run gpt-oss-20b succeeded and gpt-oss-120b came
    back empty, in another the reverse. That is why the failure looked
    intermittent and survived several rounds of review.

    `reasoning_effort="low"` fixes it decisively and is also the single
    biggest token saving available: gpt-oss-20b went 1,978 -> 262 completion
    tokens, gpt-oss-120b from an empty 3,072 to a clean 302, with MORE visible
    text in both cases. Not every model accepts the parameter — qwen3.6-27b
    returns a 400 — so support is probed once per model and remembered.

    EMPTY IS AN ERROR, NOT AN ANSWER. This used to `return content or ""`, so
    a truncated or reasoning-only response was indistinguishable from success.
    A blank reading was cached for the day on /rashifal, and the 12-call email
    job silently dropped signs while still reporting ok. Raising here is what
    lets the fallback chain do its job.
    """
    client = OpenAI(
        api_key=provider.api_key(),
        base_url=provider.api_base,  # OpenAI() accepts None to mean default
    )
    model = provider.model()
    kwargs: dict = {}
    if model not in _NO_REASONING_EFFORT:
        kwargs["reasoning_effort"] = "low"

    try:
        response = client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
    except BadRequestError as err:
        # Only retry for THIS parameter. Any other 400 is a real error and must
        # propagate, or a malformed request would silently look like a
        # capability gap and burn a second call every time.
        if "reasoning_effort" not in str(err) or not kwargs:
            raise
        with _NO_REASONING_LOCK:
            _NO_REASONING_EFFORT.add(model)
        log.info("provider %s (%s) does not accept reasoning_effort — "
                 "retrying without it and remembering", provider.name, model)
        response = client.chat.completions.create(model=model, messages=messages)

    choice = response.choices[0]
    content = choice.message.content or ""
    finish = getattr(choice, "finish_reason", None)

    if not content.strip():
        usage = getattr(response, "usage", None)
        raise EmptyCompletion(
            f"{provider.name} ({model}) returned no visible text "
            f"(finish_reason={finish}, completion_tokens="
            f"{getattr(usage, 'completion_tokens', '?')})"
        )
    if finish == "length":
        # Content exists but was cut off mid-thought. Not raised: on some
        # models this is the normal shape of a long-but-usable answer, and
        # rejecting it outright would empty the chain. Logged so it is
        # visible rather than silent — qwen3.6-27b does this routinely on the
        # rashifal route, producing ~7x the requested length.
        log.warning("provider %s (%s) truncated at the completion limit "
                    "(%d chars kept)", provider.name, model, len(content))
    return content


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


# --- 429 back-off -----------------------------------------------------------
#
# Providers tell us how long to wait and we ignored it. Groq's 429 body carries
# the wait in prose — "Please try again in 4.47s" — and standard HTTP carries it
# in `Retry-After`. On a tokens-per-minute limit that wait is usually a few
# seconds, because TPM refills continuously.
#
# The rashifal job is what exposed this: 12 per-rashi calls at ~3,587 tokens
# each is ~43,000 tokens against an 8,000 TPM ceiling, so the chain exhausted
# and the caller saw AllProvidersExhausted for a limit that cleared 4.5 seconds
# later.
#
# Deliberately conservative — chat() runs on web request threads as well as in
# the nightly job, so an unbounded sleep turns a rate limit into a timeout:
#
#   RETRY_AFTER_MAX_S     ignore a hint longer than this and fall through
#                         immediately; the next provider beats waiting.
#   RETRY_AFTER_BUDGET_S  total seconds any ONE chat() may sleep across the
#                         whole chain, so slow providers cannot compound.
RETRY_AFTER_MAX_S = 6.0
RETRY_AFTER_BUDGET_S = 10.0

_RETRY_PROSE = re.compile(r"try again in\s+([0-9]*\.?[0-9]+)\s*(ms|s\b|seconds?)", re.I)


def _retry_after_seconds(err: Exception) -> float | None:
    """Seconds the provider asked us to wait, or None if it did not say.

    Standard `Retry-After` header first, then the prose in the error body —
    Groq puts the number only in the message. Returns None rather than 0.0 when
    absent, so a caller cannot read "no hint" as "retry immediately".
    """
    resp = getattr(err, "response", None)
    hdrs = getattr(resp, "headers", None)
    if hdrs:
        raw = hdrs.get("retry-after") or hdrs.get("Retry-After")
        if raw:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass  # HTTP-date form; the prose fallback usually carries it too
    m = _RETRY_PROSE.search(str(err))
    if not m:
        return None
    value = float(m.group(1))
    return value / 1000.0 if m.group(2).lower() == "ms" else value


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
    sleep_budget = RETRY_AFTER_BUDGET_S
    for provider in order:
        # ONE retry of THIS provider when it tells us how long to wait, before
        # falling through. See _retry_after_seconds: a TPM limit clears in
        # seconds, so advancing to the next provider throws away a request
        # that a short sleep would have completed — and when the chain runs
        # out the caller sees AllProvidersExhausted for a limit that had
        # already cleared. Bounded by RETRY_AFTER_MAX_S per hint and
        # RETRY_AFTER_BUDGET_S across the whole chain, because chat() runs on
        # web request threads as well as in the nightly rashifal job.
        retried = False
        while True:
            try:
                raw_text = _call_one(provider, messages)
                # Sanitize reasoning-model leakage BEFORE the quality gate so
                # the heading-count check operates on the visible answer, not
                # on the model's `<think>` scratchpad. Also prevents any
                # downstream cache from storing the leaked chain-of-thought.
                text = strip_reasoning_envelope(raw_text)
                leaked_reasoning = (raw_text.strip() != text)
                if leaked_reasoning:
                    log.warning(
                        "provider %s (%s) leaked reasoning envelope for route=%s (raw=%d, cleaned=%d) — stripped",
                        provider.name, provider.model(), route, len(raw_text), len(text),
                    )
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
                    break
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
                        "leaked_reasoning": leaked_reasoning,
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
                # Editorial review log (opt-in via BHAGYA_LLM_REVIEW=1). Off in
                # prod; on locally when eyeballing outputs. Best-effort — the
                # module swallows all errors internally.
                try:
                    from astro_ai import llm_review
                    llm_review.record(
                        route=route,
                        provider=provider.name,
                        model=provider.model(),
                        text=text,
                        chars_raw=len(raw_text),
                        leaked_reasoning=leaked_reasoning,
                    )
                except Exception:  # noqa: BLE001 — review log never breaks the call
                    log.debug("llm_review.record failed", exc_info=True)
                if last_err is not None:
                    log.info("provider %s succeeded after upstream failures", provider.name)
                return text
            except RateLimitError as err:
                last_err = err
                # Parsing is defensive: this runs inside an exception handler,
                # so anything it raises converts a recoverable 429 into a dead
                # chain. Headers come from the provider, not from us.
                try:
                    wait = _retry_after_seconds(err)
                except Exception:  # noqa: BLE001 — a bad header is not fatal
                    log.debug("could not parse retry hint from %s", provider.name,
                              exc_info=True)
                    wait = None
                # Retry THIS provider once, and only when it named a short wait
                # we can still afford. `retried` makes it once per provider —
                # without it a provider that keeps returning the same hint would
                # spin until the budget drained, turning one slow call into ten.
                # `0 < wait` is load-bearing, not decoration. A negative
                # Retry-After — which a proxy or a clock-skewed server can
                # send — made time.sleep() raise ValueError straight out of
                # chat(), so the remaining providers were never tried, and
                # `sleep_budget -= wait` ADDED to the budget, quietly breaking
                # the ceiling documented above. NaN fails every comparison and
                # falls through, which is also correct.
                if (not retried and wait is not None
                        and 0 < wait <= RETRY_AFTER_MAX_S and wait <= sleep_budget):
                    retried = True
                    sleep_budget -= wait
                    log.warning(
                        "provider %s rate-limited (route=%s) — it asked for %.2fs; "
                        "waiting and retrying it once (%.1fs of budget left)",
                        provider.name, route, wait, sleep_budget,
                    )
                    time.sleep(wait)
                    continue
                log.warning(
                    "provider %s rate-limited (%s) — trying next in chain%s",
                    provider.name, err,
                    "" if wait is None else f" (asked for {wait:.2f}s, not waiting)",
                )
                break
            except (APIError, APIConnectionError, APITimeoutError) as err:
                log.warning("provider %s API error (%s) — trying next in chain", provider.name, err)
                last_err = err
                break
            except Exception as err:
                # Defensive: don't let one provider's weird error kill the whole request.
                log.warning("provider %s unexpected error (%s) — trying next in chain", provider.name, err)
                last_err = err
                break
    raise AllProvidersExhausted(
        f"All {len(order)} provider(s) in chain failed. Last error: {last_err!r}"
    )


def active_provider_names() -> list[str]:
    """For /admin/usage — show which providers are configured + reachable."""
    return [p.name for p in _chain()]
