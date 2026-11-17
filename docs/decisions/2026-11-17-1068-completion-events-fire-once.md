# kundli_generated and ask_answered count completions (a POST and its GET), not renders

- **Date:** 2026-11-17
- **PR / issue:** #1068

## Why, measured

Both events are declared by the template that shows the result, and that template renders on every
revisit: `result.html` on every `GET /kundli` with a saved chart (nav tap, `/switch`) and on
`/r/{short_id}` snapshots, `ask.html` on every `GET /ask?q=` with an answer (reload, language switch,
back navigation). `measurements/ga4-events.json`, 2026-10-16..2026-11-12: `kundli_generated` 55,
`ask_answered` 130, neither readable as a count of generations or questions.

**Semantic change, from the deploy of this commit:** the two events count a completed POST
(`POST /reading`, `POST /ask`) followed by the GET it redirects to, once. **History before that date
counts renders and is not comparable.** Event names are unchanged so the series stays one series.

Decision: the 303 sets a one-shot flag, the GET that follows reads it, renders the declaration and
clears it. The flag lives INSIDE the signed `__session` cookie as `ev = {name: expiry_epoch}`
(120s, stale stamps ignored; only the two fixed names). Not a cookie of its own: Firebase Hosting
forwards only `__session` (`session.py` docstring), so a separate `bhagya_ev_*` cookie would be
stored by the browser and stripped before Cloud Run, and the events would never fire on the live site
while every TestClient test stayed green. `tests/test_analytics_completion_events.py` replays the
flow carrying ONLY `__session` for that reason.

Three consequences kept deliberate:

- **One `Set-Cookie: __session` per response.** Every `save_*` re-reads the request cookie, so two
  writers on a response leave two headers and the browser keeps the last, dropping the first one's
  data. `set_event_flag` / `clear_event_flag` start from the cookie already pending on the response
  and replace that header; call them after the route's other session write.
- **A GET that carries no flag writes no cookie.** The clear happens only when the flag was present,
  so the year-long cookie is not re-extended by reads (`privacy.html`: "Visits that only read it do
  not extend it").
- **A flag survives a visit that does not consume it** (a bare `/ask`, a `/r/` view) and is gone
  after 120s. An abandoned flag can therefore fire on the next result page opened within two minutes.

Rejected: `source: new|saved` on the event (no way to tell them apart without a second flag); a
separate cookie (above); firing from the POST's JSON response (neither route has one; both are
post-redirect-get); a `GET /kundli?new=1` query parameter (bookmarkable, so it would re-fire on every
visit to a saved URL).

Not covered: a browser that blocks cookies never shows the event, which is also true of the chart
itself. `privacy.html` lists the cookie by what is saved to it; it needs no new entry because no new
cookie exists. Tokens: 0, no prompt or `_cached` key touched.
