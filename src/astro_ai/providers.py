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
from urllib.parse import urlparse

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
# Total tokens the most recent call reported. Set in _call_one on EVERY call
# (None when the response carries no usage) so a fallback provider that omits
# usage cannot inherit the figure from the one that failed before it.
_last_usage: ContextVar[int | None] = ContextVar("_last_usage", default=None)

# completion_tokens for the most recent call, or None when the provider did not
# report one (#473). The INPUT half has been available since #396 as
# `_last_prefix[0]` and was used only for the prefix-cache ratios; the output
# half was never read at all.
#
# Until #473 the /admin/ops token columns came from
# `cache.estimate_tokens(text) * 2` -- input DEFINED as twice an estimate of the
# output, which is why every route on that page reported a perfect 2:1 ratio. It
# was a constant wearing the costume of a measurement, and it understated the
# rashifal job by ~5x because a cache-layer "call" there is twelve provider
# calls. Both halves are in the response and were being discarded.
_last_completion: ContextVar[int | None] = ContextVar("_last_completion", default=None)
# (prompt_tokens, cached_tokens_or_None) for the most recent call, or None when
# even the prompt size could not be read (#396). Kept apart from _last_usage on
# purpose: that one is a total other modules already read. chat() resets this to
# None before EVERY _call_one, so one provider's figures cannot be recorded
# against the next provider that served the request.
#
# The SECOND element is independently optional, and that is the whole point.
# Measured against live Groq 2026-10-17 on openai/gpt-oss-120b with a 2,363-token
# prompt: a cache MISS returns `prompt_tokens_details: null` -- the entire object,
# not `cached_tokens: 0` -- and a HIT returns `{"cached_tokens": 2304}`. So a
# silence is ambiguous at THIS layer (unsupported model? or supported and simply
# missed?) and must not be collapsed here. We therefore keep the prompt size even
# when the cache figure is absent, and llm_stats.record() -- which knows the model
# -- is what resolves the ambiguity. Returning None for the whole tuple on a miss
# (the original shape) threw away the one number needed to resolve it.
_last_prefix: ContextVar[tuple[int, int | None, bool] | None] = ContextVar(
    "_last_prefix", default=None)


def _prefix_usage(usage) -> tuple[int, int | None, bool] | None:
    """(prompt_tokens, cached_tokens, rejected) from a usage block.

    FOUR outcomes, because the provider has four things to say, and the
    fourth used to be indistinguishable from the second:

    * `None`            -- no readable prompt size, so nothing is known at all.
    * `(prompt, None)`  -- the prompt size is known, the cache figure is NOT.
                           A cached count of `None` is never turned into 0 here:
                           recording a silence as a measured zero would put a
                           confident "0% cached" against a call that may simply
                           have been ineligible. Resolving which is
                           llm_stats.record()'s job -- it knows the model.
    * `(prompt, n, False)`     -- the provider reported, and `n` may legitimately
                                  be 0.
    * `(prompt, None, True)`   -- the provider reported something IMPOSSIBLE and
                                  it was thrown away. Distinct from a silence,
                                  and QA round 4 found that collapsing the two
                                  was its own defect: `record()` books a silence
                                  on an eligible call as a measured zero, so a
                                  misreporting provider became indistinguishable
                                  from one that genuinely missed, dragged the
                                  published saving down, and left
                                  `reported_unmeasurable` -- the counter that
                                  exists to make this rule falsifiable -- at 0.
                                  The flag is what lets `record()` keep the call
                                  out of both denominators and still count the
                                  rejection.

    bool is excluded because it is an int subclass. A negative count, and a
    cached count LARGER than the prompt it came from, are both rejected: neither
    is a measurement, and letting either through would publish a percentage that
    is negative or over 100. Rejecting them here is what makes llm_stats's
    "neither rate can exceed 100% by construction" an actual property of the
    code rather than an assumption about the provider. Never raises -- this runs on the happy
    path of every LLM call.
    """
    try:
        prompt = getattr(usage, "prompt_tokens", None)
        details = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", None)
    except Exception:  # noqa: BLE001 — observability never breaks a reading
        return None
    if not isinstance(prompt, int) or isinstance(prompt, bool) or prompt < 0:
        return None
    if cached is None:
        # A SILENCE. Not a rejection: Groq omits the field entirely on a miss,
        # so this is the ambiguous case `record()` resolves from the model.
        return prompt, None, False
    if not isinstance(cached, int) or isinstance(cached, bool) or cached < 0:
        # Present but not a count (a string, a float, a bool) or negative. The
        # provider DID say something and it is unusable, so this is a rejection
        # and must not read as a measured zero either.
        return prompt, None, True
    if cached > prompt:
        # Cached tokens are a SUBSET of prompt tokens (Groq: "cached_tokens:
        # Number of input tokens that were served from cache"), so this is not a
        # measurement -- it is a provider reporting something impossible. Rejected
        # here rather than stored, because llm_stats documents "neither rate can
        # exceed 100% by construction" and that is only true if this holds. QA
        # round 3 found the claim was resting on vendor sanity with nothing
        # enforcing it: _prefix_usage(prompt=100, cached=5000) returned
        # (100, 5000) and the published 5000% was saved only by the clamp.
        return prompt, None, True
    return prompt, cached, False


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


def last_used_tokens() -> int | None:
    """Total tokens the current request's most recent LLM call reported.

    None when no call happened or the provider returned no usage block.
    """
    return _last_usage.get(None)


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


class RequestTooLarge(AllProvidersExhausted):
    """The request itself is bigger than a provider's per-request ceiling.

    Kept distinct from a plain exhaustion because the two need OPPOSITE
    responses and were being conflated. A 429 is transient: wait, retry, try
    another model, and the same request eventually goes through. A 413 is
    structural — the request cannot fit, so waiting changes nothing and the
    next model on the same host with the same cap returns the same error.

    This is not hypothetical. `/kundli` failed in production with

        Error code: 413 - Request too large for model 'openai/gpt-oss-120b'
        ... tokens per minute (TPM): Limit 8000, Requested 8562

    and Groq sends it with `"code": "rate_limit_exceeded"`, which is what made
    it look transient. The openai SDK has no 413 subclass, so it arrived as a
    generic `APIStatusError`, landed in the `except APIError` branch, and the
    chain burned a second identical call on `groq20` — which shares the same
    8,000 TPM cap and returned the same 413.

    Subclasses AllProvidersExhausted so existing `except` clauses in the routes
    keep working and keep rendering the degraded page.
    """


def _is_request_too_large(err: Exception) -> bool:
    """Is this the structural 413, as opposed to a transient rate limit?

    Matches on the HTTP status first, because that is the one part of the
    response that is not free text. The string check is a fallback for
    providers that signal an oversized request some other way; it is
    deliberately narrow ("request too large" / "too large for model") so that
    an ordinary 429 mentioning "rate limit" does not match.
    """
    if getattr(err, "status_code", None) == 413:
        return True
    text = str(err).lower()
    return "request too large" in text or "too large for model" in text


def _failure_reason(err: Exception) -> str:
    """Short class for WHY a provider failed, for the fallback breakdown (#355).

    One of: 429_tpm, 429_tpd, 429 (a rate limit that names neither window),
    413, timeout, empty, quality, error. A closed vocabulary on purpose: these
    are stored as dict keys in every day-file, so free text would grow the blob
    without bound and never aggregate.

    The 413 test runs FIRST. Groq's oversized-request body spells out "tokens
    per minute (TPM)", so classifying on the words alone would file a
    structural failure under 429_tpm — the exact conflation RequestTooLarge
    exists to prevent. Deliberately does not parse the Limit/Used/Requested
    figures; that is #350.

    `quality` is not derived here: a bad-output response is not an exception,
    so chat() sets it explicitly instead of parsing its own message back.
    """
    if _is_request_too_large(err):
        return "413"
    if isinstance(err, RateLimitError):
        text = str(err).lower()
        if "per day" in text or "tpd" in text:
            return "429_tpd"
        if "per minute" in text or "tpm" in text:
            return "429_tpm"
        return "429"
    if isinstance(err, APITimeoutError):
        return "timeout"
    if isinstance(err, EmptyCompletion):
        return "empty"
    return "error"


# Groq's free tier is 8,000 TPM PER MODEL, and it counts the request against
# that same bucket — so a single request above the cap can never succeed, at
# any traffic level, on any free-tier model in the chain.
#
# The pre-flight budget is the ceiling minus a margin for what we cannot
# measure from here: the chat-template scaffolding Groq wraps the messages in,
# and whatever completion it reserves. Measured 2026-09-05, the largest fixture
# request assembled to 8,019 tok by our count while production reported 8,562
# for a real chart — so that unmeasured remainder is worth ~500 tok and the
# margin is set generously above it.
REQUEST_TOKEN_CEILING = int(os.environ.get("BHAGYA_REQUEST_TOKEN_CEILING", "8000"))
REQUEST_TOKEN_MARGIN = int(os.environ.get("BHAGYA_REQUEST_TOKEN_MARGIN", "1000"))

# Bytes per token, for pre-flight estimates ONLY. Measured with tiktoken
# o200k_base over the eight golden charts (scripts/measure_natal_request.py),
# 2026-09-05.
#
# TWO constants, because the halves of a request have genuinely different
# densities and one number cannot serve both:
#
#   instruction prose   4.227 B/tok (en system prompt), 4.295 (hi)
#   chart-data blocks   3.697 to 3.778 across the eight fixtures
#
# Each is set just below the measured FLOOR for its own kind — not below the
# average — so each rounds slightly high without the error compounding. The
# floor matters: 3.7 looks like a safe data constant against a 3.70-3.78 range
# and is not, because `strong-gajakesari` sits at 3.6970 and gets under-counted
# by two tokens. `tests/test_natal_request_size.py` asserts the no-under-count
# property against tiktoken over all eight charts, which is how that was found.
# A single 3.9 constant — the
# whole-request average — was tried and rejected: it priced the Hindi system
# prompt at 3,540 against a real 3,214, and the 326 tok of phantom cost made
# the guard shed the entire topic-summaries block (4.6 kB) on four of eight
# charts to save ~50 tokens they did not need. A guard should be conservative
# in its MARGIN, where the conservatism is visible and tunable, not in an
# estimate that silently degrades output.
#
# `cache.estimate_tokens` is not reused here: at 4.0 B/tok it under-counted
# these same requests by ~3%, and a guard that under-counts waves through
# exactly the request it exists to stop. It stays as it is for the
# /admin/usage counters, which are stats rather than a safety check.
_BYTES_PER_TOKEN_PROSE = 4.2
_BYTES_PER_TOKEN_DATA = 3.65


def estimate_prose_tokens(text: str) -> int:
    """Token estimate for instruction prose — prompt templates, overlays."""
    return -(-len(text.encode("utf-8")) * 100 // int(_BYTES_PER_TOKEN_PROSE * 100))


def estimate_data_tokens_for_bytes(n_bytes: int) -> int:
    """Token estimate for assembled chart data, from a UTF-8 byte count."""
    return -(-n_bytes * 100 // int(_BYTES_PER_TOKEN_DATA * 100))


def estimate_data_tokens(text: str) -> int:
    """Token estimate for assembled chart data — the user message."""
    return estimate_data_tokens_for_bytes(len(text.encode("utf-8")))


# --- Per-model token bucket (#475 Phase 1) ----------------------------------
#
# Groq's 8,000 TPM is keyed PER MODEL. Until now the only reaction to it was
# reactive: send, take the 429, sleep the hint, retry once. This is the
# proactive half -- chat() asks a per-model bucket for room BEFORE it sends, and
# waits a bounded time, or moves to the next provider, instead of spending a
# call on a guaranteed 429.
#
# A CONTINUOUS-REFILL BUCKET, deliberately not a strict sliding 60 s window. A
# sliding window over 8,000 admits at most two 3,210-token calls per 60 s, so
# twelve calls would need start times spread over >= 300 s -- the issue's own
# acceptance (12 x 3,210 within 300 s) would be unreachable by construction.
# The one Groq 429 body on record (llm.py, "Limit 8000, Used 5009, Requested
# 3587 ... try again in 4.47s") satisfies (5009 + 3587 - 8000) / (8000 / 60)
# = 4.47 EXACTLY, i.e. Groq behaves like a bucket refilling at LIMIT/60 per
# second. That is an inference from one 429 body, not a measurement of Groq's
# limiter (the x-ratelimit headers that would settle it are #396, out of scope).
# If Groq turns out to be stricter, the 429 handling below stays the backstop.
#
# PER PROCESS, NOT PER ACCOUNT. Each Cloud Run instance builds its own buckets,
# so two instances can still jointly overspend a model, and anything else using
# the key is invisible. This narrows the 429 rate; it cannot remove it.
#
# Capacity is LIMIT - margin. The 600 is judgment, not a measurement: the one
# measured unknown is the chat-template remainder (~543 tok, 8,562 reported vs
# 8,019 counted, 2026-09-05), rounded up. The estimator below already adds its
# own scaffold, so the two overlap on purpose -- an over-reserve costs a short
# wait; an under-reserve costs a 429 and a wasted call.
_TPM_MARGIN = 600

# Pre-flight cost of one request = estimated prompt + scaffold + a completion
# reserve. Reserved at FULL weight: Groq's prefix cache may discount the cached
# part of the prompt, but how a cache hit counts against TPM is #396 and still
# open, so over-reserving is the safe direction. No max_completion_tokens is
# sent (qwen's truncation history is in PROVIDERS above), so the completion
# half is a reserve, not a cap. Calibrated against tiktoken by
# tests/test_token_bucket.py::test_the_request_estimate_*.
_SCAFFOLD_TOKENS = 250
_COMPLETION_RESERVE: dict[str, int] = {"rashifal_single": 500}
_COMPLETION_RESERVE_DEFAULT = 800


def _completion_reserve(route: str) -> int:
    return _COMPLETION_RESERVE.get(route, _COMPLETION_RESERVE_DEFAULT)


def estimate_request_tokens(messages: list[dict], route: str = "") -> int:
    """What one chat() call will cost the TPM bucket, before it is sent.

    System messages are instruction prose and everything else is chart data --
    the same split, and the same two byte-density constants, as the natal
    pre-flight guard, because the two halves of a request have genuinely
    different densities (see _BYTES_PER_TOKEN_PROSE).
    """
    total = _SCAFFOLD_TOKENS + _completion_reserve(route)
    for m in messages:
        content = m.get("content")
        text = content if isinstance(content, str) else str(content or "")
        total += (estimate_prose_tokens(text) if m.get("role") == "system"
                  else estimate_data_tokens(text))
    return total


@dataclass
class _Reservation:
    """A claim on a bucket. `tokens` is what was charged (clamped to capacity)."""
    bucket: "_TokenBucket"
    tokens: int
    wait_s: float
    forced: bool = False
    settled: bool = False


class _TokenBucket:
    """Continuous-refill token bucket with FIFO slots; O(1) under its own lock.

    State is (level, t): the level as of time `t`, and `t` MAY BE IN THE FUTURE
    -- a reservation that has to wait is assigned the slot at which the bucket
    will have drained enough, and `t` moves to that slot. The next caller is
    therefore queued behind it without any polling or re-check, and slots can
    never go backwards. The caller sleeps OUTSIDE the lock, so one waiting
    thread never blocks another from reserving its own, later slot.
    """

    def __init__(self, limit: int, margin: int, *, clock=time.monotonic):
        self.cap = max(limit - margin, 1)
        self.rate = limit / 60.0          # tokens per second
        self._clock = clock
        self._lock = threading.Lock()
        self._level = 0.0
        self._t = 0.0

    def _level_at(self, t0: float) -> float:
        # t0 >= self._t always holds at the call sites; the max() is belt and braces.
        return max(0.0, self._level - max(0.0, t0 - self._t) * self.rate)

    def reserve(self, tokens: int, max_wait_s: float, *, force: bool = False
                ) -> tuple["_Reservation | None", float]:
        """(reservation, predicted_wait_s). None means DENIED, with state untouched.

        Denied when the wait would exceed `max_wait_s` -- the caller skips to
        another provider instead. `force=True` is the last resort: it charges
        the bucket at once, never waits, and may overdraft it (the next caller
        then queues behind the debt).
        """
        # Clamped: a request bigger than the whole bucket could otherwise never
        # be admitted, and would wait forever. The ~7k-token natal chart is
        # within a few hundred tokens of the cap.
        n = min(max(int(tokens), 0), self.cap)
        with self._lock:
            now = self._clock()
            if force:
                if self._t <= now:
                    self._level = self._level_at(now)
                    self._t = now
                self._level += n
                return _Reservation(self, n, 0.0, forced=True), 0.0
            t0 = max(now, self._t)
            level = self._level_at(t0)
            deficit = level + n - self.cap
            slot = t0 + (deficit / self.rate if deficit > 0 else 0.0)
            wait = max(0.0, slot - now)
            if wait > max_wait_s:
                return None, wait
            self._level = max(0.0, level - (slot - t0) * self.rate) + n
            self._t = slot
            return _Reservation(self, n, wait), wait

    def settle(self, res: "_Reservation", actual: int) -> None:
        """Replace the estimate with what the call really used. Once per reservation."""
        with self._lock:
            if res.settled:
                return
            res.settled = True
            self._level = max(0.0, self._level + max(int(actual), 0) - res.tokens)

    def refund(self, res: "_Reservation") -> None:
        self.settle(res, 0)


# Injectable so tests never sleep for real. Looked up at call time, so a test
# that monkeypatches either name takes effect for buckets already built.
def _pace_clock() -> float:
    return time.monotonic()


def _pace_sleep(seconds: float) -> None:
    time.sleep(seconds)


_BUCKETS: dict[str, _TokenBucket] = {}
_BUCKETS_LOCK = threading.Lock()


def _bucket_key(provider: ProviderConfig) -> str:
    # The SAME key chat() hands llm_stats.record, so /admin/ops can line the
    # bucket's figures up with measured_by_model. Provider name AND model: the
    # model alone is what Groq limits, but listing `groq` beside `groq120` in the
    # chain is already documented as a mistake, and keying on the pair is what
    # the recorded stats do, so the two views cannot disagree about a row.
    return f"{provider.name}|{provider.model()}"


def _tpm_limit(provider: ProviderConfig) -> int | None:
    """The TPM ceiling we know for this provider, or None = do not pace it.

    Only Groq's is known (REQUEST_TOKEN_CEILING, one definition). A limit we
    have not measured is not guessed at: an unknown provider is sent to
    unpaced, exactly as before.
    """
    host = urlparse(provider.api_base).hostname if provider.api_base else None
    return REQUEST_TOKEN_CEILING if host == "api.groq.com" else None


def _bucket_for(provider: ProviderConfig) -> _TokenBucket | None:
    limit = _tpm_limit(provider)
    if limit is None:
        return None
    key = _bucket_key(provider)
    # The registry lock is released before any bucket lock is taken, and no
    # thread ever holds two while sleeping.
    with _BUCKETS_LOCK:
        bucket = _BUCKETS.get(key)
        if bucket is None:
            bucket = _BUCKETS[key] = _TokenBucket(
                limit, _TPM_MARGIN, clock=lambda: _pace_clock())
    return bucket


def _pacing_enabled() -> bool:
    """Kill switch, read per call: BHAGYA_TPM_PACING=0 restores the pre-#475 path.

    Roll back with `gcloud run services update bhagya
    --update-env-vars=BHAGYA_TPM_PACING=0` -- --update-env-vars, never
    --set-env-vars, which would replace the whole environment.
    """
    return os.environ.get("BHAGYA_TPM_PACING", "1").strip().lower() not in (
        "0", "false", "off", "no")


def _pace_done(res: "_Reservation | None", err: Exception | None) -> None:
    """Settle `res` once its call has finished, successfully or not.

    If the response carried usage, charge what Groq will have counted -- the
    same (prompt, completion) pair llm_stats books -- which also covers an
    empty or quality-failed completion, since usage is read before that check.
    Without usage: a 429 or any other 4xx was REFUSED, so nothing was consumed
    and the estimate is returned; a timeout, a dropped connection, a 5xx or an
    unexpected error may well have been counted upstream, so the estimate stays.
    """
    if res is None:
        return
    prefix, completion = _last_prefix.get(), _last_completion.get(None)
    if prefix and completion is not None:
        res.bucket.settle(res, prefix[0] + completion)
        return
    status = getattr(err, "status_code", None)
    if isinstance(err, RateLimitError) or (
            isinstance(status, int) and not isinstance(status, bool) and 400 <= status < 500):
        res.bucket.refund(res)


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

    _last_usage.set(getattr(getattr(response, "usage", None), "total_tokens", None))
    _last_prefix.set(_prefix_usage(getattr(response, "usage", None)))
    # `int(...)` guarded: a provider may answer a string or a bool here and a
    # bool is an int, so `isinstance(n, int)` alone would store `True` as 1.
    _comp = getattr(getattr(response, "usage", None), "completion_tokens", None)
    _last_completion.set(
        int(_comp) if isinstance(_comp, (int, float)) and not isinstance(_comp, bool) else None)

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

# Token-bucket wait budget for BATCH callers (#475 Phase 1). chat(max_wait_s=None)
# is the interactive default (RETRY_AFTER_MAX_S, 6 s): a user is waiting, so a
# provider whose bucket is more than 6 s from having room is skipped. The warm and
# send-daily rashifal jobs have nobody waiting and are the traffic that overspends
# a bucket, so they pass this instead -- see llm.generate_rashifal(pace_deadline=).
#
# A per-call bound ONLY -- on its own it does not make a job fit. QA simulated the
# inline two-language send (24 calls, 2 workers): 319-395 s in 8 of 8 seeds, past
# the 300 s Cloud Run timeout, because every call could still wait its full 150 s.
# Hence PACE_JOB_DEADLINE_S below, which bounds the TOTAL. A wait beyond the budget
# does not fail the call -- the provider is skipped to the next, and if every one
# is over budget the call is FORCED through un-waited -- so exceeding it costs a
# possible 429, never a reading. Simulated, not measured in production; the
# /admin/ops "blocked on bucket" column is where it shows up.
# Env-overridable like REQUEST_TOKEN_CEILING above.
PACE_JOB_BUDGET_S = float(os.environ.get("BHAGYA_PACE_JOB_BUDGET_S", "150"))

# Job-level deadline for pacing waits (#475 Phase 1, QA round 2). The job entry
# point (see pace_deadline) turns this into ONE absolute time shared by every call
# of the job -- both languages of /admin/send-daily-rashifal -- and each chat call
# is handed min(PACE_JOB_BUDGET_S, time left): the allowance decays as the job
# runs, and a call that arrives after the deadline has 0 s to wait, so it skips to
# the next provider and then takes the forced, un-waited pass (today's pre-pacing
# behaviour: it may 429 and falls to the existing 429 handling).
#
# Why 230: the Cloud Run request timeout is 300 s and the deadline stops WAITING,
# not the job. Calls after it still cost their own latency (~10 s, two workers)
# and the forced pass's 429 handling (one hint sleep <= RETRY_AFTER_MAX_S, then
# the next provider), and the email loop runs after generation. Simulated (scaled
# clock, Groq-shaped limiter, real chat(), 2 workers, 24 calls, 8 seeds): the job
# ended 245-258 s at 230 (15-28 s past it), 239-249 at 220 and 245-272 at 240, so
# 230 + ~28 s = ~258 s leaves ~40 s of the 300 for the emails. Higher buys fewer
# forced calls but spends that headroom (260 -> up to 282 s); lower fails more.
# Simulated, NOT production-measured. It bounds the wait, not the failures: at 230
# the forced tail 429s and exhausted the chain for one language in 7 of 8 seeds
# (a language that completed is cached; one that failed is not). One language per request -- the
# /admin/warm-rashifal path -- never reached the deadline (119-191 s, 0 429s).
# Env-overridable like PACE_JOB_BUDGET_S.
PACE_JOB_DEADLINE_S = float(os.environ.get("BHAGYA_PACE_JOB_DEADLINE_S", "230"))


def pace_deadline(allowance_s: float | None = None) -> float:
    """The absolute pacing deadline for a job that starts now.

    Call ONCE at the job's entry point and pass the result down as a plain
    argument -- never a ContextVar: the rashifal fan-out runs in pool threads and
    context does not propagate into them. Uses the same injectable clock as the
    buckets, so a test's fake clock moves the deadline and the buckets together.
    """
    return _pace_clock() + (PACE_JOB_DEADLINE_S if allowance_s is None else allowance_s)


def pace_wait_budget(deadline: float | None) -> float | None:
    """The `max_wait_s` for a chat() call made now under `deadline`.

    None (no deadline) stays None = the interactive default. Otherwise
    min(PACE_JOB_BUDGET_S, time left), floored at 0: never more than the
    per-call budget, and exactly 0 once the deadline has passed.
    """
    if deadline is None:
        return None
    return max(0.0, min(PACE_JOB_BUDGET_S, deadline - _pace_clock()))

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


def chat(messages: list[dict], *, route: str = "",
         max_wait_s: float | None = None) -> str:
    """Send `messages` through the configured provider chain.

    Order resolution: random shuffle per request (default), or strict
    configured order if BHAGYA_LLM_BALANCE=order. On RateLimitError (429)
    or any APIError we log and fall through to the next provider in this
    request's order. Raises AllProvidersExhausted when nothing works —
    callers should treat that as user-visible degradation, not a bug.

    `route` is a short label for the calling feature ("natal", "ask", ...)
    used for the /admin/usage per-route breakdown. Defaults to empty which
    aggregates under "unknown".

    `max_wait_s` (#475) is the TOTAL time this call may spend waiting on the
    per-model token bucket, across the whole chain. None means the interactive
    default (RETRY_AFTER_MAX_S); 0 means never wait, only fail over. A provider
    whose wait would not fit is skipped, and if the chain then fails, the skipped
    ones are tried in ascending predicted wait WITHOUT waiting -- pacing alone
    never turns a reading into AllProvidersExhausted. See _TokenBucket.

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
    # Who produced `last_err` and why, for llm_stats' fallback breakdown. Set
    # ONLY through _fail() below so they cannot drift from `last_err` — a
    # fallback recorded with last_err set and no reason would break
    # sum(fallback_reasons) == fallbacks.
    last_failed_provider = ""
    last_reason = ""
    sleep_budget = RETRY_AFTER_BUDGET_S
    # Token-bucket pacing (#475). `pace_left` is separate from `sleep_budget`:
    # that one belongs to the provider's own "try again in Ns" hints.
    pacing_on = _pacing_enabled()
    pace_left = RETRY_AFTER_MAX_S if max_wait_s is None else max(0.0, float(max_wait_s))
    est: int | None = None
    paced: dict[str, dict[str, int]] = {}
    deferred: list[tuple[float, ProviderConfig]] = []
    # Hosts that have already rejected this request as too large. Same-host
    # providers share the per-request ceiling, so once one says 413 the rest
    # will too — see RequestTooLarge.
    too_large_hosts: set[str | None] = set()
    too_large = False

    def _fail(err: Exception, reason: str | None = None) -> None:
        """Record `err` as this request's latest failure, with its provider and reason."""
        nonlocal last_err, last_failed_provider, last_reason
        last_err = err
        last_failed_provider = provider.name
        last_reason = reason or _failure_reason(err)

    def _note_too_large(err: Exception) -> bool:
        """Record a 413 and mark its host unusable for this request.

        Structural, not transient — see RequestTooLarge. Every other provider
        on the same host shares the ceiling, so re-sending the same bytes to
        them is a guaranteed second 413: a wasted round-trip that delays the
        fallback to a provider that could actually serve it. Providers on OTHER
        hosts are still tried, which is the whole point of keeping the chain
        going — that is what lets the paid `openai` net catch an oversized
        request.

        Returns True when the error was a size failure and has been handled.
        """
        nonlocal too_large
        if not _is_request_too_large(err):
            return False
        skipped = [p.name for p in order
                   if p.api_base == provider.api_base and p is not provider]
        too_large_hosts.add(provider.api_base)
        too_large = True
        log.error(
            "provider %s rejected the request as TOO LARGE (route=%s): %s. This "
            "is a size failure, not a rate limit — waiting cannot fix it.%s",
            provider.name, route, err,
            f" Skipping same-host provider(s): {', '.join(skipped)}." if skipped else "",
        )
        return True

    def _worklist():
        """The chain, then (only if it all failed) the providers pacing skipped.

        Evaluated lazily: the second pass reads `deferred` and `too_large` as
        they stand when the first pass has ended. A 413 is structural, and
        sending forced calls after it would only repeat it.
        """
        for p in order:
            yield p, False
        if too_large:
            return
        for _wait, p in sorted(deferred, key=lambda d: d[0]):
            yield p, True

    for provider, force in _worklist():
        if provider.api_base in too_large_hosts:
            continue
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
            # Ask the bucket for room BEFORE spending a call (#475). Outside the
            # try: a denial is a `break`, and nothing here is a provider failure.
            res = None
            pc = None
            bucket = _bucket_for(provider) if pacing_on else None
            if bucket is not None:
                key = _bucket_key(provider)
                pc = paced.setdefault(key, {"reserved": 0, "waits": 0, "wait_ms": 0,
                                            "skips": 0, "forced": 0})
                if est is None:
                    est = estimate_request_tokens(messages, route)
                res, predicted = bucket.reserve(est, pace_left, force=force)
                if res is None:
                    pc["skips"] += 1
                    log.info("provider %s skipped by the token bucket (route=%s): "
                             "would wait %.1fs, %.1fs allowed", provider.name, route,
                             predicted, pace_left)
                    # A retry after a real 429 is an optimisation, not a request
                    # that pacing owes a second pass.
                    if not retried:
                        deferred.append((predicted, provider))
                    break
                if res.forced:
                    pc["forced"] += 1
                    log.warning("provider %s forced past the token bucket (route=%s): "
                                "every provider's wait exceeded the budget",
                                provider.name, route)
                else:
                    pc["reserved"] += 1
                if res.wait_s > 0:
                    pc["waits"] += 1
                    pc["wait_ms"] += int(round(res.wait_s * 1000))
                    pace_left -= res.wait_s
                    (log.info if res.wait_s > 1.0 else log.debug)(
                        "provider %s: waiting %.2fs for token-bucket room (route=%s)",
                        provider.name, res.wait_s, route)
                    _pace_sleep(res.wait_s)
            try:
                # Reset first: a fake or failing _call_one never sets these, and
                # the previous provider's figures must not be read as this one's.
                # _last_usage and _last_completion join _last_prefix here (#475):
                # _pace_done reads the pair, and a ThreadPool worker keeps its
                # context across tasks. The real _call_one sets all three
                # together, so the leak needs an attempt that raises before it
                # gets there or a response with a partial usage block -- but then
                # the bucket would be settled against the PREVIOUS task's figures,
                # and last_used_tokens() would report them.
                _last_prefix.set(None)
                _last_usage.set(None)
                _last_completion.set(None)
                try:
                    raw_text = _call_one(provider, messages)
                except BaseException as call_err:
                    _pace_done(res, call_err)
                    raise
                _pace_done(res, None)
                prefix = _last_prefix.get()
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
                    _fail(RuntimeError(f"quality-fail: {provider.name} for {route}: {reason}"),
                          "quality")
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
                        # Groq prefix cache (#396); null = not reported, not 0.
                        "prompt_tokens": prefix[0] if prefix else None,
                        "cached_tokens": prefix[1] if prefix else None,
                        # Seconds this request waited on the token bucket for
                        # this model; null = not paced (#475).
                        "paced_wait_s": round(pc["wait_ms"] / 1000, 2) if pc else None,
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
                        fallback_reason=last_reason,
                        failed_provider=last_failed_provider,
                        prompt_tokens=prefix[0] if prefix else None,
                        cached_tokens=prefix[1] if prefix else None,
                        reported_impossible=bool(prefix[2]) if prefix else False,
                        # #473: the MEASURED pair, recorded here because this is
                        # the only layer that knows it. The cache layer above
                        # counts documents, not provider calls -- one rashifal
                        # "call" is twelve of these -- so tokens summed there can
                        # never be right however good the arithmetic.
                        completion_tokens=_last_completion.get(None),
                        # EVERY provider's counters, under its own key (#475): the
                        # one that waited and then 429'd, or was skipped, is not
                        # the one serving, and `pc` alone would drop it.
                        pacing={k: dict(v) for k, v in paced.items()} or None,
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
                _fail(err)
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
                _fail(err)
                if _note_too_large(err):
                    break
                log.warning("provider %s API error (%s) — trying next in chain", provider.name, err)
                break
            except Exception as err:
                # Defensive: don't let one provider's weird error kill the whole
                # request. The size check runs here too: a 413 is structural
                # however it reaches us, and pinning the handling to one except
                # clause makes it depend on which SDK class the provider's
                # library happens to raise.
                _fail(err)
                if _note_too_large(err):
                    break
                log.warning("provider %s unexpected error (%s) — trying next in chain", provider.name, err)
                break
    # Known gap (#475): pacing counters (`paced`) are booked by llm_stats.record()
    # on SUCCESS only. A request that ends here has no record call to ride, and a
    # new one would be an added storage op on the failure path, so the waits and
    # skips of a chain that exhausts are not on the panel; they are still in the
    # log (skips at INFO, forced passes at WARNING).
    if too_large:
        raise RequestTooLarge(
            f"The request is larger than the per-request ceiling of every provider "
            f"in the chain that accepted it for inspection. Retrying will not help; "
            f"the request has to get smaller, or a provider without that ceiling has "
            f"to be in the chain. Last error: {last_err!r}"
        )
    raise AllProvidersExhausted(
        f"All {len(order)} provider(s) in chain failed. Last error: {last_err!r}"
    )


def active_provider_names() -> list[str]:
    """For /admin/usage — show which providers are configured + reachable."""
    return [p.name for p in _chain()]
