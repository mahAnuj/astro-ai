# infra-lead report — 2026-10-08

Focus: validate the four blockers in `measurements/discover/latest.md`. Each one was reproduced here, not taken from the report. Three issues filed (#278, #279, #280). One blocker could not be reproduced, and one turned out not to be a problem.

## Blocker verdicts

| # | Claim | Verdict | Filed |
|---|---|---|---|
| 1 | `pdftotext` missing in agent sandboxes | **Confirmed**, and wider than reported | #278 |
| 2 | CI holds 1 of 7 books; is it fixable? | **Confirmed.** Registry is 8, not 7. Partly fixable | #279 |
| 3 | WebSearch rejects reddit.com (400); Quora returns nothing | **COULD NOT REPRODUCE.** Nothing filed | none |
| 4 | shubhagya.com has no title/meta | **Not real.** A WebFetch artefact | none |

### 1. pdftotext (#278)
- `which pdftotext` returns nothing. `corpus_search.py vimshottari` prints `FAIL: pdftotext not installed`.
- Only `pr-gates.yml` and `agent-research.yml` install poppler. Six workflows do not: `agent-discover`, `agent-work`, `agent-design`, `agent-sync`, `agent-infra` and `agent-measure`.
- `agent-discover` passes `--disallowedTools Bash(sudo:*)`, so the agent cannot install it. Only the workflow step can.
- The gap is wider than discover. `agent-work`, which hosts QA, has the same hole.
- `fetch_corpus.py` also reports the one good book as "WRONG" without pdftotext, because it cannot count lines.
- Side find: `agent-research.yml:58` calls `fetch_corpus.py --list`. That flag does not exist (`unrecognized arguments`), and `2>/dev/null || true` hides the failure. Included in #278.

### 2. Partial corpus (#279)
- `git ls-files data` shows one tracked book. `fetch_corpus.py` registers **8** (the discover report says 7), and reports `0/8 usable, 1 present but WRONG`.
- No workflow ever runs `--fetch` or `--from-bucket`.
- Fixable in CI:
  - **4 of 8** are public: Rao textbook, Rao Lessons, Vasudev, and the Raman Muhurtha `.txt`.
  - `curl -I` on the 3 download URLs returned HTTP 200 from this sandbox.
  - I did not download them, so **file sizes are unmeasured**.
- The other **4** are owned, in-copyright books (including Goodwin, 28,171 lines). They need the owner to upload them to a private `corpus/` path in the bucket and grant the CI service account read access.
  - **Not verified:** whether the bucket already holds them, or whether the SA can read them. This job has no GCP credentials (see below).
  - This is a copyright and ownership decision for the human. I uploaded nothing.
- Free tier: the public route, yes. The bucket route is probably yes, but the book sizes need measuring first.

### 3. Social listening: could not establish
- `WebSearch` was **permission-denied in this run** (`Claude requested permissions to use WebSearch, but you haven't granted it yet`). I made two attempts: a reddit.com-filtered query and a Quora-targeted query. Neither executed.
- The discover run saw a 400 from the tool. This run saw a permission block, which is a different failure, and I produced no evidence on either.
- So I **cannot say** whether the cause is a tool limit or the query. I proposed nothing and filed nothing.
- To settle it, re-run from a context where WebSearch is allowed. Try a bare `reddit rahu mahadasha ketu antardasha`, then `allowed_domains: ["reddit.com"]`, then the `site:quora.com` form. Compare the three.

### 4. shubhagya.com "no title or meta": not a site defect
- `curl https://shubhagya.com/` returned HTTP 200, 152,472 bytes.
- The raw HTML has `<title>Shubh Bhagya — Free Kundli, Rashifal, Panchang, Numerology, Muhurat, Ask 3 Free Questions</title>`.
- It also has `meta description`, `robots: index, follow`, `og:title`, `og:description` and `twitter:description`. There are 24 `<meta` tags in total.
- `WebFetch` converts the page to markdown and drops `<head>`. Its own answer: "content looks like converted text, not raw HTML".
- **What it means:** the discover run's observation was a tool artefact, not a rendering or SEO fault. Nothing is wrong on the site.
- **Rule for future agents:** use `curl` for head tags, not WebFetch. Do not file SEO findings from WebFetch output about `<title>` or meta.
- I did not check the ~38 articles that #267 says have empty `seo_title`. That is separate and is already filed.

## Deploy truth: BUILD_SHA could not be set (#280)
- I tried to export the trigger and edit it. **Blocked:** `agent-infra.yml` grants `id-token: write` but has **no `google-github-actions/auth` step**. `GOOGLE_APPLICATION_CREDENTIALS` is empty and `gcloud auth list` shows no credentialed account.
- `gcloud beta builds triggers export` failed. `gcloud auth login` falls to an interactive flow and crashed.
- **Nothing was changed GCP-side.** Before and after are both unchanged and there is no export file, so CLAUDE.md was not edited. `ignoredFiles: measurements/**` is untouched.
- Live `/health` right now: `{"ok":true,"revision":"bhagya-00391-bmt","build_sha":null}`. This is the revision-changed tier, and the `exact` tier still has never run.
- The fix needs two things (#280):
  - An auth step copied from `agent-discover.yml`.
  - A decision on whether `agent-analytics@bhagya-500701` may be given Cloud Build trigger edit rights. I suspect it does not have them today, but I did not test it.

## Production probe (from `/tmp/probe.txt`, taken before this run, not re-measured by me)
- `/` 200 in 0.69s. `/kundli` 200 in 0.60s. `/matching` 200 in 0.98s. `/numerology` 200 in 0.57s. `/learn` 307 in 0.36s.
- The 307 on `/learn` is presumably a trailing-slash redirect. I did not follow it. If it is not one, it is worth a look.
- This is a single sample. It does not exercise #266, which is intermittent and needs repeated natal requests. I made no capacity measurements this run.
- I did not measure the numbers asked for by the standing items (#266, #212, #232, #253), so I make no claims on them.

## Not done / limits
- **No workflow files were edited.** They need a branch and PR, and the job token has `contents: read`.
- I did not download any corpus book.
- WebSearch could not be exercised (see 3).
- No issues were closed.
