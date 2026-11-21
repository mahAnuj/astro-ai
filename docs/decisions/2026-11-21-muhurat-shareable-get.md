# The muhurat finder has a shareable GET result URL (basic mode only) and names the next auspicious date on a zero result

- **Date:** 2026-11-21
- **PR / issue:** #1336 (slice 5 of #1017; R7 and R8)

## Why, measured

`GET /muhurat?event=griha_pravesh&city=Delhi&start=2026-11-22&days=30` returned 200 and the empty
form: the GET read none of its parameters, so a result had no URL. A search with no
excellent/good/acceptable date ended in a sentence that named no date, which is the page Kharmas
(mid-December to mid-January) makes common: a griha pravesh window starting 2026-12-20 is empty and
the first auspicious date is 2027-01-20 (business: 2027-01-24).

No rule changed: no line of `muhurat.py` moved. Every date shown is `find_candidates` output.

## What was built

- **One shared path.** `_finder_response` in `routes/muhurat.py` holds the POST body; the POST route
  is a thin forwarder with its signature unchanged. GET declares only `event`, `city`, `start`,
  `days` and passes only those, so personal, couple and Namkaran input is impossible on a GET by
  construction (extra query parameters are ignored, and the saved chart is never read for compute).
  The POST HTML is byte-identical before and after apart from the added share and next-date lines
  (diffed on 10 searches).
- **Basic mode only.** The "Share these dates" link and the linked next date are built only when
  the search used none of the personal, couple or Namkaran inputs. The URL carries the four basic
  fields and nothing else; `days` is the clamped value (`len(candidates)`), so the link reproduces
  the page. In the other modes the next date is plain text. Personal results depend on birth data
  that must never be put in a URL, and a signed or stored snapshot was rejected as a storage and
  privacy commitment this slice does not need.
- **Indexing.** A GET result is `noindex, follow` with a canonical to `/muhurat/<event-slug>` (the
  indexable page for the topic; `/muhurat` for an unknown event). Bare `GET /muhurat` and every POST
  keep `index, follow` and the old canonical. `base.html` gained a `{% block canonical %}` whose
  default is byte-identical. No `robots.txt` Disallow: a crawler that may not fetch the page never
  sees its noindex.
- **No search event from a GET.** A GET calls neither `notify.muhurat_computed` nor declares
  `muhurat_searched`. A link is crawlable and forwardable, so counting renders would turn the
  owner's Telegram into a bot meter and move the #1217 and #1218 baselines, which count form
  submissions. **Cost: a person who opens a shared link emits no search event.** Share-link landings
  are read from GA4 landing pages with a query string instead. A city that cannot be geocoded on a
  GET (a typo in a link anyone can write) logs a warning and does not call `_fire_error_alert`;
  any other failure still alerts. The status stays 500, as on POST.
- **City length cap.** A city over 100 characters is a 400 ("City is too long.") before any geocode,
  on GET and POST: a GET is an unauthenticated way to spend a Nominatim lookup on any string.
  `days` handling is unchanged: the route does not clamp, `find_candidates` clamps to 1..365.
- **R8 scan.** Only when the rows hold no `muhurat.AUSPICIOUS_RATINGS` date (the template's own
  definition, so caution is not "found"). `_next_auspicious_date` calls `find_candidates` in 60-day
  chunks starting the day after the window and stops at the first chunk with an auspicious row, or
  once 365 days past the window have been read. It names the earliest auspicious row of that chunk,
  not `rows[0]`: rows come back best-tier-first, and for business from 2026-12-20 the best-rated row
  (2027-01-27) is three days after the earliest (2027-01-24). Finder and scan run in ONE
  `run_in_threadpool` hop. Not cached: the key space (any city) is unbounded and the path is rare.
  A failed scan logs and leaves the already-computed result standing.

## Assumption flagged

The issue says "scanning up to the existing 365-day cap". This reads it as 365 days PAST the
searched window, not 365 days from its start; otherwise a 180-day search that found nothing would
claim "none in 365 days" having looked at 185. Changing it is one constant,
`NEXT_DATE_HORIZON_DAYS`.

## Rejected

- Calling the POST route function from GET: its `Form(...)` defaults are truthy objects and leak into
  every optional field.
- Duplicating the handler for GET: the two would drift, the failure this repo keeps recording.
- One 365-day `find_candidates` call always: about 0.6 s on every zero result against about 0.1 s
  when the answer is in the first chunk.
- `hot_cache` for the scan; a copy button and client JS for sharing; a `robots.txt` Disallow.

Tokens: none per call and per day; no GCS operation; no new service. Tests:
`tests/test_muhurat_share_get.py`, rows in `scripts/mutations/2026_11_21_1336_muhurat_share_get.py`.
