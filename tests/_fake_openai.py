"""One fake OpenAI client for every test that runs the REAL `providers._call_one`.

Since #475 Phase 1b `_call_one` reads the response through the SDK's
`with_raw_response` route (the only way to see the x-ratelimit headers), so a
fake that stubs `chat.completions.create` alone no longer reaches it. Five test
files used to build that stub by hand; this is the one place that knows the
shape, so the next change to the call path edits one file, not five.

Deliberately NOT a getattr fallback in production code: production reads
`with_raw_response`, and a double has to provide it.
"""
from __future__ import annotations

from types import SimpleNamespace


class WithHeaders:
    """Return this from a fake `create` to attach response headers to `response`."""

    def __init__(self, response, headers):
        self.response = response
        self.headers = headers


def fake_client(create):
    """`create(**kwargs)` returns a parsed response, or WithHeaders(response, headers)
    (or raises, as the SDK does on a non-2xx). The returned client exposes it as
    `client.chat.completions.with_raw_response.create` with `.headers` and `.parse()`.
    """
    def raw_create(**kwargs):
        out = create(**kwargs)
        if isinstance(out, WithHeaders):
            resp, headers = out.response, out.headers
        else:
            resp, headers = out, {}
        return SimpleNamespace(headers=headers, parse=lambda: resp)

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        with_raw_response=SimpleNamespace(create=raw_create))))
