# Index status is collected by URL Inspection over the sitemap, and staleness is never computed on a shallow clone

- **Date:** 2026-11-18
- **PR / issue:** #1065, subtask 1 of 2 (`partial/`, refs and does not close). The collector,
  its tests and its mutation rows. Not built here: the `agent-measure.yml` step that runs it
  (closed-list item 1, a session authors it) and the `/admin/ops` panel (subtask 2).

## Why, measured

Owner, 2026-11-15: *"are we tracking which pages of the websites are indexed or not in GSC,
which are indexed before we did some serious updates and accordingly suggest indexing"*. Nothing
read index status. On 2026-11-15 `/sitemap.xml` listed 213 URLs and `measurements/gsc-all.json`
showed impressions for 140 pages, so 76 URLs had zero impressions and nothing said whether each was
not indexed, indexed and not ranking, or pointed at a different canonical.

`scripts/fetch_index_status.py` calls `urlInspection/index:inspect` once per sitemap URL, in order,
and prints one JSON document (`measurements/index-status.json` once the workflow step exists).
213 sequential calls fit in the 600 per minute and 2,000 per day per-property quota. Zero LLM
tokens: HTTP reads and one `git log` per page.

Decisions in it, each of which has a test and a mutation row
(`scripts/mutations/2026_11_18_1065_index_status.py`):

- **Staleness only on full history.** `git rev-parse --is-shallow-repository` must print exactly
  `false`. A depth-1 clone (what `actions/checkout` does by default) gives every file the tip
  commit's date, so every page would read as changed after its crawl. Otherwise `stale_in_index`
  is null with `stale_reason: "shallow-checkout"`. Null, not false: false asserts a measurement.
- **A quota stop is partial, never a guess.** A 429, or a 403 whose body says "quota", ends the
  run with `partial: true`; the unreached rows are `not_inspected` with every verdict field null
  and are not counted as indexed. They are not filled in from an earlier file, which would be a
  guess under a fresh timestamp. `ApiError` subclasses `SystemExit`, so the loop catches it by
  name; `except Exception` would let a 429 kill the process.
- **A file that says nothing is not written.** A 400/401/403 on the first call, an unreadable
  sitemap, zero URLs, or a run that inspected nothing: exit 1 and print nothing.
- **Requesting indexing is offered only where it can help.** `request_indexing` (top 10, by
  impressions, then sitemap priority, then URL) excludes canonical mismatches and
  robots/noindex-blocked pages: "Request indexing" fixes neither. Google has no API to request
  indexing for ordinary pages, so the click stays the owner's.
- **The route-to-file table is data, so it has a gate.** One test drives the real `/sitemap.xml`
  and fails if any URL maps to no file or to a file that does not exist. `base.html`, `i18n.py`
  and `learn_registry.py` are deliberately not mapped to any page: one edit would flag all 213.
  `/muhurat/<slug>` maps to `muhurat_landing.html` plus `muhurat.py`, because the landing copy
  lives in `EVENT_LANDING`. `/rashifal*` and `/panchang*` change by data, not by commit, so
  commit staleness understates them; the document's `note` says so.
- **Impressions join is checked.** `impressions_matched` reports how many of the pages that had
  impressions were found in the sitemap, so a URL-form mismatch shows as a low number rather than
  as silent zeros.

Rejected (from the architect's design on #1065): copying `measurements/` into the image;
writing the list to GCS (a `storage.py` write path, a trust-boundary file); importing
`routes/seo.py` to build the sitemap (it would describe the checkout, not what Google was told);
threaded inspection; merging old verdicts into a partial run; GA4 for ranking.

**Not verified, stated plainly:** no live call was made. The response field names and enum values
come from Google's documentation, and the tests' fixtures are doc-derived. The first run in CI must
confirm that `index:inspect` accepts the `webmasters.readonly` scope and the service account's
Search Console role, and capture one real response.
