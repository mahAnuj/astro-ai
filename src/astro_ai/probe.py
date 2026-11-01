"""Let the production verifier identify itself, so its probes do not page the owner.

WHY THIS EXISTS

`verify-production.yml` exercises two real user paths against the live site --
`POST /numerology` and `POST /reading` -> `/kundli` -- and both fired the
owner's Telegram alert as if a visitor had submitted them. Measured over the
eight days to 2026-10-31: 4-6 identical alerts a day, byte-identical because
the probe's input is hardcoded, so the 8-hex key never changes:

    🔢  Numerology reading
    🛤 life path 9 · system=chaldean
    🔖 061e3306

THE PROBES ARE CORRECT AND MUST STAY. Neither can be a GET: #172 records that
the Lo Shu grid renders only in a submitted result (grid markers on
`GET /numerology` = 0, on the POST = 3), and #216/#218 that the rule-source
labels appear only behind `POST /reading` -> 303 -> `GET /kundli` with a cookie
jar. A static gate cannot replace them either -- it guards the SOURCE, while
the probe proves the DEPLOYED BYTES carry the disclosure, which matters while
#253 is open (a service worker has served a stale stylesheet since
2026-08-16). So the probe is right; firing a visitor alert for it is the bug.

WHY IT MATTERS BEYOND ANNOYANCE. The owner alert channel is the thing that has
to work on the day something actually breaks. Training it to be ignored is the
defect, and it is the same class `ARCHITECTURE.md` names elsewhere: a channel
nobody reads is a channel that reported nothing.

THE SCOPE IS THE LOAD-BEARING PART, NOT A FOOTNOTE

`X-Bhagya-Probe` is an UNAUTHENTICATED header. Anyone can send it. That is
acceptable for an alert carrying a diagnostic and an 8-hex key, and
unacceptable for one carrying a question, an email or a name -- so the rule is
an ALLOW-LIST of the four alerts `notify.py` documents as PII-free
(`kundli_generated`, `matching_done`, `dosha_checked`, `numerology_computed`),
and anything not on it is never suppressed however the request is shaped.

A deny-list would have been the obvious shape and is the wrong one: a formatter
added later would be suppressible by default, and the one that matters would be
the one nobody remembered to list. `verify_no_relaxation.py` makes the same
argument about `disallowedTools`, and `ops_today.py` about its conclusion set --
"an allow-list of failures was the wrong way round".

EVERY FAILURE MODE FALLS TOWARD SENDING THE ALERT. An unknown event name, a
request with no headers, a header-lookup that raises, a wrong value: all
return False, which means the alert fires. A false alert is noise; a swallowed
one is a visitor whose activity the owner never saw, and this module is not
worth that trade.

`notify.py` IS NOT TOUCHED. It is a trust-boundary path (#354), and the
decision belongs at the call site anyway -- a formatter cannot see the request.
"""
from __future__ import annotations

#: The header the verifier sends. Named for the product rather than for CI
#: because any probe may use it, and the value says which one is calling.
PROBE_HEADER = "X-Bhagya-Probe"

#: The only value that suppresses. An exact match, not a prefix or a
#: truthiness test: `X-Bhagya-Probe: 0` must not suppress, and a header with
#: some other provenance must not either.
PROBE_VALUE = "verify-production"

#: The four alerts `notify.py` documents as carrying NO PII -- a diagnostic
#: plus an 8-hex `identity.short_key`. This list and that docstring have to
#: stay in step; `tests/test_probe_alert_suppression.py` asserts they do, by
#: reading `notify.py` rather than by restating its contents here.
SUPPRESSIBLE = frozenset({
    "kundli_generated",
    "matching_done",
    "dosha_checked",
    "numerology_computed",
})


def suppresses_owner_alert(request, event: str) -> bool:
    """True only when `event` is PII-free AND the request is a declared probe.

    `request` is a Starlette request, whose `.headers` is case-insensitive, so
    `x-bhagya-probe` and `X-Bhagya-Probe` both match -- which is required, not
    convenient: HTTP header names are case-insensitive and a proxy may
    normalise them.

    Anything unexpected returns False. See the module docstring: every failure
    mode here has to fall toward sending the alert.
    """
    if event not in SUPPRESSIBLE:
        return False
    try:
        return request.headers.get(PROBE_HEADER) == PROBE_VALUE
    except Exception:
        # No `.headers`, a mapping that raises, `request` is None. A module
        # that decides whether to notify must never be the reason a request
        # 500s, and `notify` itself already log-and-swallows for the same
        # reason.
        return False
