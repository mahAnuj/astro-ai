# BACKLOG.md — standing triage overview

**Last full scan: 2026-08-25, against `origin/main` = `c14093c`.**
**Execution round 1 in progress — see *Execution log* below. Branch head `4a918a2`.**
Produced by `/prioritise` (the `project-manager` agent), then QA-verified in the parent
session — which overturned two of its six closure proposals. 36 open issues at scan time.

**QA state at `c14093c`:** `uv run pytest` → **24 passed**; `scripts/mutate_behaviour_suite.py`
→ **8/8 caught, CONTROL correctly MISSED**. See *QA baseline* below — a bare clone reports
14 failures that are not defects.

## How to use and update this file

This file exists so the *next* `/prioritise` run starts warm instead of re-deriving 36
issues from scratch. It is a cache, and like every cache in this repo it is only as good
as the evidence behind each entry — so:

- **Every verdict carries the SHA it was checked at.** A verdict without one is a claim,
  not a finding. `verified@c14093c` means someone read the code at that commit;
  `carried` means the verdict was inherited from an earlier scan and *not* re-checked.
- **Re-verify what changed.** On the next run, diff `origin/main` against the SHA in the
  header. Issues whose touched files appear in that diff get re-checked from source;
  the rest may carry their verdict forward, with the `checked@` column left at the older
  SHA so the staleness is visible rather than laundered into looking fresh.
- **Update in place, do not rewrite.** Move rows between sections, bump SHAs and dates,
  add new issues. Keep closed issues in the *Recently resolved* section for one scan
  cycle so a reopened issue does not read as new.
- **This is the same failure class CLAUDE.md warns about twice** — the "do not re-search"
  note that outlived its evidence by two days, and the `[BPHS]` blanket licence. A note
  in this file is never sufficient grounds to skip a check before shipping; it only tells
  you where to look first.

Scans are read-only. The agent proposes closures; **the human closes**.

---

## Environment gaps that limited the 2026-08-25 scan

These are properties of the scanning checkout, not of the backlog. Any verdict marked
`corpus-unverified` or `prod-unverified` below is limited by one of them.

1. **Production is unreachable** from the agent sandbox (`shubhagya.com:443` is
   policy-denied by the proxy). Every verdict is against `origin/main`, never the live
   site. Closing an issue still requires production evidence (CLAUDE.md).
2. **`data/` holds 1 of the 8 books** (only `vedic_astro_textbook.pdf`). Corpus hit-count
   claims in #216–#219 and #191 were verified as *code* claims by reading, not as
   *corpus* claims by measurement.
3. **No venv, no `swisseph`** → the scanning agent could not run `pytest` or the
   `verify_*.py` gates. **The parent session has since run them — see below.**

---

## QA baseline — measured 2026-08-25 at `c14093c`

| Command | Result |
|---|---|
| `uv run pytest` (env fixed) | **24 passed** |
| `scripts/mutate_behaviour_suite.py` (env fixed) | **8/8 caught; CONTROL correctly MISSED** |
| `uv run pytest` (bare clone) | **14 failed, 10 passed** — all environmental |

**A bare clone in this sandbox reports 14 failures and none of them is a defect.** Two
independent environmental causes, isolated by changing one variable at a time:

1. **`nominatim.openstreetmap.org:443` is denied by the environment's network policy**
   (403 on CONNECT, confirmed in the agent proxy's `recentRelayFailures`). Nine tests
   reach it transitively — all eight in `test_blast_outcomes.py` plus
   `test_panchang_strip_cache.py::test_fallback_keeps_the_strip_visible`. They fail with
   `KeyError: 'sent'`, because the route correctly 500s with
   `{"ok":false,"error":"Couldn't compute reference chart: Geocoding failed…"}`.
2. **No `.env`, so `OPENAI_API_KEY` is unset.** The five `test_rashifal_degraded.py`
   failures are all "Rashifal is temporarily unavailable — API key not configured".

With the geocoder stubbed and a dummy key set, all 24 pass.

**The mutation harness fails its own CONTROL under cause 1**, reporting `BLIND (CAUGHT)`
and correctly declaring its own 8/8 worthless — because a suite that is already red reports
every mutation as caught, including the no-op. Give it a working environment
(`PYTEST_ADDOPTS` reaching the stub) and CONTROL returns to `OK (correctly missed)`. Worth
knowing before anyone reads a `BLIND` verdict as a harness defect.

---

## Repo state at scan

| | |
|---|---|
| `origin/main` | `c14093c`; local `main` identical, tree clean, 0 ahead → everything committed is live |
| Open PRs | 0 |
| Stale remote branches | `feat/design-189-190`, `feat/homepage-187-188`, `feat/mobile-app-feel`, `fix/manglik-coherence` — all tips 2026-08-09, all against **closed** issues #187–#190. Abandoned; candidates for deletion. |
| `AGENT_STATUS.md` | absent → no loop in flight in this checkout |

---

## Proposed closures — **QA-verified, and two were overturned**

Each row below was re-checked in the parent session against `origin/main` rather than
relayed from the agent. Two of the six did not survive that check, which is the argument
for doing it: a triage pass that only relays is a triage pass that launders.

Closure evidence is posted on all six issues. **Nothing has been closed** — the human closes.

| # | Verdict | Evidence | checked@ |
|---|---|---|---|
| **#171** Yoni koota article vs tool | **Fixed — close** | `learn/kundali-matching-ashtakoot-guna-milan.html:36` now states we do *not* use the 14×14 five-level grid and retracts the Raman attribution; `:38` discloses North/South divergence; contradicting worked examples gone; `matching.py::_yoni` still 4/2/0, which is now what the page says. #177 separately records Yoni verified 27/27 + 7/7 (`d387d9d`, `820a80f`). | c14093c |
| **#159** RAG index | ❌ **OVERTURNED — do NOT close; re-scope in place** | The agent read the 2026-08-16 comment as a decision to drop RAG. It is not: it ends *"Keep this issue open, re-scoped: revisit RAG once the corpus grows."* Closing would discard a live condition and the two constraints attached to any future build (absence must come from exhaustive matching, never similarity; any table confirmed against the page image). The corpus-growth trigger has **partly** fired — CLAUDE.md records one of the two named sources acquired, ~5k lines rather than the doubling that comment anticipated. Retitle to the deferred form so the next pass stops re-litigating it from the title. | c14093c |
| **#178** `[BLOCKER]` acquire Muhurtha + Lo Shu | ⚠️ **Scope reads empty — but the last item is UNVERIFIABLE from a clone** | Items 1–3 struck (owner confirmed in-thread that both scans were deleted); 4b explicitly dropped as a bad trade; 5 absorbed by #191. Item **4a** rests entirely on CLAUDE.md:262 naming `data/matching/raman-muhurtha-1948-…txt`. `data/` is gitignored and a fresh clone holds only `vedic_astro_textbook.pdf`, so `data/matching/` cannot be checked here — **and `knowledge/SOURCES.md` has no row for the book at all**, so the two registries that should agree disagree. Sole evidence is a sentence in CLAUDE.md, which is the pattern CLAUDE.md itself warns about. Confirm on the machine that has `data/`, add the SOURCES.md row, then close. **Drop `[BLOCKER]` from the title now either way** — it gates nothing. | c14093c `corpus-unverified` |
| **#214** panchang strip cache hygiene | **Close, fold remnant into #184** | Items 1–2 fixed and deployed (`9e8acb1`, `9054f36`, `b7e1fc4`, rev `bhagya-00358-z6b`), gated by `tests/test_panchang_strip_cache.py`. Item 3 called "tidiness rather than a defect" by the filer. Remaining stale pointer (`hot_cache.py:17,44` → `main.py::_HOMEPAGE_PANCHANG_CACHE`; real symbol `routes/deps.py:542::_PANCHANG_STRIP_CACHE`) is already **#184 §1** verbatim. **Correction for #184:** it proposes repointing to `routes/home.py`, but a tree-wide grep finds the symbol `_HOMEPAGE_PANCHANG_CACHE` **only** in those two `hot_cache.py` comments — it exists nowhere else, so #184's target is dangling too. Repoint to `routes/deps.py:542::_PANCHANG_STRIP_CACHE`. | c14093c |
| **#185** route-table guard as a gate | **Answer "no" and close** — see *Not recommended* | `scripts/route_inventory.py` exists; no `routes.expected.txt` anywhere. Issue itself says "Closing this as 'no' is a perfectly good outcome." | c14093c |
| **#163** numerology pair disagreements | **Duplicate — merge into #201** | Determinate parts shipped in `cd0689e`; remaining scope *is* #201's title. Its stated premise ("a comment claims they are the same") is now **false** — `numerology.py:461-473` says the opposite. **Re-measured independently** at `c14093c`: 23/45 disagreements, 5 friend↔enemy flips at (1,8) (6,8) (7,7) (8,8) (9,9), `8-8` enemy vs friend — the agent's numbers reproduce exactly. | c14093c |

---

## Queue — 2026-08-25

| Pos | Issue | Size | Loop | Gate |
|---|---|---|---|---|
| 1 | **#220 + #222** daily blast aborts silently, and leaks subscriber addresses *(bundle)* — **assigned, labelled `bug`/`priority:high`** | S | `/bug` | **Yes — does not exist today** |
| 2 | **#172** code still asserts the Cheiro attribution it disproved 40 lines earlier | XS | `/bug` | No (comment fix) |
| 3 | **#193** date gate reports four claims and checks zero | S–M | `/bug` | **Yes — it *is* the gate** |
| 4 | **#163 + #201** 23 of 45 pair verdicts contradict *(ship the disclosure now)* | S / M–L | `/bug` then `/feature` | Yes, for the model |
| 5 | **#217** `corpus_search.py` word-boundary hides Sanskrit inflections | S | `/bug` | **Yes** — `maudhya` → `Maudhyam` |
| 6 | **#212** rashifal prompt input grew 18.5%/call | S | `/bug` | **Yes — a measurement** |
| 7 | **#150** `/panchang` omits Yamaganda, Gulikai, Brahma Muhurta, moonrise/moonset | S–M | `/feature` | **Yes** — extend `verify_panchang_angas.py` |

### 1. #220 + #222 — daily blast *(bundle — separate PRs to this function will collide)*

Both live in ~45 lines of `routes/subscribe.py::send_daily_rashifal` (from :460).
**#220:** the per-subscriber loop has no `try/except`; a raise means every later subscriber
gets nothing, **and both alerts (`zero_delivered`, `partial`) sit below the loop so neither
fires**, and the outcome JSON never returns. Cloud Scheduler is `--max-retry-attempts=0`.
**#222:** `RuntimeError(f"…: {failures[:5]}")` puts up to five raw subscriber addresses into
Telegram *and* into `events.record`'s `error_message`, which `/admin/activity` renders and
GCS retains 30 days.

**Position 1** because this is the endpoint that failed silently for 21 days unnoticed;
#220 re-opens exactly that hole (silent, reaches beyond the site, unretryable) and #222 is
new PII egress introduced as a side effect.

**Correction to #220 before anyone acts on it:** its title blames a raising
`email_sender.send`, but `email_sender.py:62-76` already wraps the HTTP call in
`except Exception` → `False`. The realistic raise sources are the loop body *around* the
send — `sub['email']` is subscripted directly **twice** (unsubscribe URL, and the send), so
a row missing `email` raises `KeyError`; plus `template.render`. The geocode path is safe
(`_panchang_for_city` swallows). **The item #220 files as "Related, LOW" is the most likely
trigger and belongs in the main fix.**

**Gate:** `tests/test_blast_outcomes.py` has six tests and its `fake_send` fixture only ever
returns `True`/`False` — **there is no raising case**. Add one asserting the loop continues,
`sent + failed == total`, and the partial alert fires; then run
`scripts/mutate_behaviour_suite.py`.

### 2. #172 — Cheiro attribution survives its own refutation

User-facing half is fixed (`templates/numerology.html:298-309` now says "NO SOURCE IN data/
COVERS THIS GRID", with 0 hits for `lo shu`/`loshu`/`lo-shu` across 13 PDFs / 77,119 lines).
But `numerology.py:263` and `:278-281` still carry the original Cheiro source block —
**forty lines below** `numerology.py:224-230`, which reads "NOT sourced to Cheiro … nothing
may present it as Cheiro's". Also `:273` "zeros excluded per Cheiro".

No user is being lied to any more, which keeps it off position 1. But it is the exact defect
class CLAUDE.md is built around — the justification outliving its refutation — and it is
nearly free. Natural first user of #216's `[UNSOURCED — widely cited, not in corpus]` marker.

### 3. #193 — a gate that prints coverage and checks nothing

`scripts/verify_learn_article_dates.py` gained year inheritance in `fe3dfe0`. All four
inherited claims decline attribution, and an unattributed inherited claim **does not fail
Gate 3** — so the inheritance path adds zero checked claims.

**FIXED 2026-08-25 — Gate 4 landed (`129c1df`), QA-verified.** The issue's repro, with its
line number corrected from `:90` to `:98`: corrupt `vivah-muhurat-2027.html:98`
`Jul 14` → `Jul 16`. That exited **0** before Gate 4 and exits **1** after it. The paragraph
above is kept as the historical statement of the defect, not a live claim — flagged by QA,
because a present-tense description of a closed defect is the exact rot this file warns about.

Wrong dates are this repo's most expensive recurring defect (`_FESTIVALS_2026` shipped 9 of
17 wrong by up to 21 days; #143 closed while a fourth wrong date was live; the
`_ABUJHA_MUHURATS` signature has recurred four times), and festival/muhurat dates reach
users **through email and the rashifal LLM prompt** — harder to retract than a page.

**Qualifications:** (a) script not run here (no `swisseph`) — exit-0 not independently
reproduced; logic confirmed present, file last touched by a merge on 2026-08-16.
(b) The behaviour is a **documented design choice** (header :139-146: "a decline is a fact
about the gate's reach"), so the fix is widening attribution, which needs a ruling on the
ambiguity rule, not just a patch.
**Accept only on:** md5 before → corrupt → assert **exit 1** → restore → assert md5 identical.

### 4. #163 + #201 — 23 of 45 numerology pair verdicts contradict

Measured on `origin/main` during the scan, not taken from the issue:

```
disagreements: 23 of 45
sign flips friend<->enemy: 5 — (1,8) (6,8) (7,7) (8,8) (9,9)
```

`_pair_verdict()` (frozenset-keyed, drives `/numerology/compatibility`) and the
`_LP_DESTINY_*` maps (ordered-tuple, drive the Bhagya Score) disagree. `8-8` is **enemy** on
the compatibility page and **friend (+5)** in the Bhagya Score.

Position 4 rather than higher because #163's headline overstates it: the tables answer
*different questions* (Life Path × Life Path between two people vs Life Path × Destiny within
one person), and a user only sees the contradiction by reading both surfaces.

**This is the blocked-value / unblocked-disclosure case.** The value is genuinely blocked:
#201 establishes Johari is directional (L2967: "Number 3s are neutral toward 4s, though
**4s are enemies of 3s**") and `frozenset({1,8}) == frozenset({8,1})`, so the structure
**cannot represent** its cited source; picking a winner per pair would invent a source
position. **The disclosure ships today** — the contradiction is already in a code comment
(`numerology.py:461-473`) and *not* on the page. Say on-page which relationship each verdict
describes.

### 5. #217 — third false-negative mechanism in `corpus_search.py`

Unchanged at `scripts/corpus_search.py:284-285`:

```python
return re.compile(rf"(?<![a-z]){re.escape(v)}s?(?![a-z])")
```

The boundary admits a trailing plural `s` and nothing else, so `-am`, `-ena`, `-asya`, `-aṃ`
are invisible. Reported: `maudhya` → 0 hits while `book1-for-CD.pdf:324` reads
*"called \"Maudhyam\""*.

Ranked on unblocking power. This tool's `--absent` mode is what makes "unsourced" a
*checkable* claim here, and this is the **third** distinct false-negative mechanism in it —
CLAUDE.md records two, one of which cost two days of a wrong "do not re-search" note. A false
"not in the corpus" is dangerous in the direction that deletes a correct rule or lets a wrong
one survive an audit.

**Blocks:** #216, #218, #219, #191, and the #163/#201 sourcing work.
**Careful:** the tool has a false-*positive* history too (it once counted our own outreach
PDF as a source book) — do not loosen the boundary far enough to reintroduce that class.
*(Regex verified by reading; hit-count not reproducible — `book1-for-CD.pdf` not in checkout.)*

### 6. #212 — prompt input grew 18.5%/call on the outage path

9,466 → 11,215 ch ≈ 2,366 → 2,803 tok, × 24 calls/day ≈ **+10.5k input tokens/day** against
groq120's 200k TPD. QA observed `groq120 rate-limited … TPD: Limit 200000` repeatedly; the
chain fell through to groq20 and no user saw a failure.

**CORRECTED 2026-08-26 — this paragraph previously said `prompts/` was last modified at
`e06c4e7`, "the exact 'after' tree #212 measured, so its numbers describe HEAD". Wrong on
both halves, and it cost an engineer a wrong conclusion.** #212 measured `3c02c71` vs
**`0f6501c`** (the issue's own prose names `e06c4e7`, one commit later — that is where the
error entered), and its "combined per call" is **system prompt + day-signals block only**,
excluding the transit block and the per-rashi anchor. Rebuilt under the issue's own date:

```
3c02c71 2026-08-22:  sys=8710  day_signals= 756  sum= 9466   issue:  9,466  ✓
0f6501c 2026-08-22:  sys=9634  day_signals=1581  sum=11215   issue: 11,215  ✓
```

**#212's figures reproduce to the character.** An engineer working from the line above
measured a different pair (`348ab01` → HEAD), got 11,258 → 13,482, and reported the issue's
absolutes as unreproducible. They are not. Do not close #212 saying they were.

Position 6 because it is **silent** (silence is what let the previous failure run 21 days),
but nothing is currently wrong for any user. Headroom, not breakage.

**Do:** drop the redundant banned-phrase list from the system prompt; reorder the user message
so the shared prefix precedes the unique per-rashi anchor. **Do not** drop the
Rahu Kaal/Abhijit block — #212 concedes it earns its place.
**Gate:** record tokens/call before and after **as numbers**. Not an estimate — the issue
exists because a growth of this size went unnoticed.

### 7. #150 — `/panchang` Phase 1 gap

Across `templates/panchang.html` the only hit for any of the five terms is `:211`, still
reading *"(not shown above, deferred to a next release)"*. `chart.py` has no
Yamaganda/Gulikai/Brahma Muhurta/moonrise code.

The page is **honest** about the gap, so nothing is wrong in front of a user — incomplete,
not lying. It earns its slot on the tiebreak: last #132 Phase 1 gap on the page targeted at
~500K monthly queries; the eighth-of-daylight segmentation is already implemented for Rahu
Kaal; `swe.rise_trans` is already called for the Sun at `chart.py:3520-3521`, so
moonrise/moonset is a body-constant change.

**Trap:** `panchang.html:211` must be removed **in the same commit**, or the page starts
lying in the opposite direction.

---

## Blocked — and what still ships today

| Issue | Waits on | Unblocked half |
|---|---|---|
| **#201** (+ #163 remainder) | A directional 9×9 model. `frozenset` cannot express an asymmetric source. | **Yes — the on-page disclosure.** Queue item 4. |
| **#218** Budha-Aditya 6°, Manglik combust-Mars 6° | A human ruling. Both move user-facing verdicts; Manglik reaches **email and LLM prompts**. `book1-for-CD.pdf:3337`: "There are different opinions on this." | **Two.** (a) Label both `UNSOURCED` in place — truthful today, costs nothing. (b) **Add the missing gate now**: `0a1b6ee` added Gate 6 to `verify_muhurat_tables.py` for the main table; these two constants have the same unguarded shape. `verify_manglik_coherence.py` checks cross-module *agreement*, not sourcing. |
| **#219** muhurat combustion convention | A tradition ruling: degree-orb (current) vs Muhūrta Cintāmaṇi's days-from-heliacal, plus two unmodelled blocking states (*bālatva*, *vṛddhatva*). CLAUDE.md: regional variation is legitimate — so the requirement is to **state the convention**, not switch. | **Two disclosures.** State the convention on the finder; and **cite the `namkaran` waiver** at `muhurat.py:634-636` — found correct and uncited, with two sources. An uncited correct rule is one refactor from being "simplified" out. |
| **#216** the `[BPHS]` blanket licence | Partly on **#217** (re-sourcing sweeps run through `corpus_search`). | **Yes — the marker.** Replacing `[BPHS]` with `[UNSOURCED — widely cited, not in corpus]` at `knowledge/SOURCES.md:178-180` is unblocked; only the per-use sweep waits. |
| **#191** extract ~22,000 readable lines | Nothing technically — but **not from this checkout** (`data/` holds 1 of 8 books). | On the machine that has `data/`. |
| **#209** kundli landing claims | A human decision on wording. | **Rescope.** 2 of 3 claims resolved: padas now computed (`9d5f3a1`); "Swiss Ephemeris" **measured** to be a naming question, not correctness — Moshier worst case ~0.1″ against a 12,000″ pada, 120,000× margin. Only **moolatrikona** (advertised `about.html:162`, never computed) is a live false claim. Retitle to that alone or close and refile — the title is now wrong on two of three counts. |

---

## Explicitly not recommended (2026-08-25)

- **#124 Hindi at `/hi/…` with hreflang.** `priority:high`, quotes ~2M monthly searches, and
  is the most re-raisable item here. Not now: a **1–2 day project** whose own deferral comment
  names the risk ("rushing it risks breaking existing English URLs during the split"), landing
  on `main` — which *is* the deploy — with no staging and request-path-only coverage. Growth,
  not harm. Needs a dedicated cycle, and must not share a window with anything touching routes.
- **#185 route-table guard as a permanent gate → answer "no".** #154 proved its value as a
  *one-off diff tool* (67 entries across 27 commits). As a standing gate, every legitimate new
  route forces a baseline regeneration, and reflexive regeneration is how a gate stops meaning
  anything — this repo has already paid for gates that could not fail (`c14093c`: "the mutation
  harness could not report a miss"). Thirteen `verify_*` gates plus a behaviour suite exist;
  the marginal one is not free. Keep `route_inventory.py` as the refactor tool it is good at.
- **#128 / #129 / #131 / #114 / #115 / #198 / #203 — feature and design work.** Ashtakvarga,
  Shodashvarga, Kundli PDF, WebGL mandala, 3D dasha helix, mobile hero motion, name-numerology.
  All plausible; none is a defect. With a silent email failure (#220), PII in a chat channel
  (#222), a gate that checks nothing (#193) and 23 contradictory verdicts (#163) live, adding
  surface area is the wrong move. **#114/#115 especially** would add a WebGL bundle to a site
  whose defining performance incident (#144) was a ~13-second homepage.
- **#200 numerology copy names books and authors — do not run as filed.** Not stale, but
  contestable and needs a ruling first. It cites CLAUDE.md's cite-the-tradition rule, but that
  rule is written for *astrological* claims and `/numerology` is explicitly **not** Vedic — the
  page's own `tool_desc` says "19th-20th century Western and ancient Chinese systems, not
  classical Vedic Jyotish". Naming Cheiro at `numerology.html:11, 22, 42, 54, 115` is **how the
  page stays honest**. The narrow defensible version is the three sites where a tradition name
  works as well: `:484` "per Johari", `:497` "Per Johari's Vedic-integrated system", `:566`
  "Kumar's formula". Get a human ruling on Cheiro before touching it.
- **#151 Panchang-anga material missing from `knowledge/*.md`.** Real — the corpus gap behind
  `/panchang` and the Muhurat Finder. Not queued: content-authoring blocked on the same `data/`
  access as #191, and #150 ships user-visible value on the same page first. **Pair with #191.**

---

## Full open-issue index (36 at `c14093c`)

`Q` = queue position. `checked@` = SHA the verdict was verified at; **`—` means not
individually re-verified in this pass** — treat its state as unknown, not as fine.

| # | Title (short) | State | checked@ |
|---|---|---|---|
| 222 | blast leaks subscriber emails to Telegram + /admin/activity | **Q1 — assigned** | c14093c |
| 220 | blast aborts mid-run, silently and unretryably | **Q1 — assigned** | c14093c |
| 219 | muhurat combustion: degree-orb vs days-from-heliacal | blocked (2 disclosures ship) | c14093c |
| 218 | Budha-Aditya 6° and Manglik combust-Mars 6° unsourced | blocked (label + gate ship) | c14093c |
| 217 | corpus_search word-boundary hides Sanskrit inflections | **Q5** | c14093c |
| 216 | SOURCES.md blanket `[BPHS]` licence | blocked on #217 (marker ships) | c14093c |
| 214 | panchang strip cache hygiene | **close** → fold into #184 | c14093c |
| 212 | rashifal prompt input +18.5%/call | **Q6** | c14093c |
| 211 | rashifal: 12 readings differ because the prompt says to; Gochara unused | live | — |
| 209 | /kundli + /about advertise padas, moolatrikona, Swiss Ephemeris | **rescope** to moolatrikona only | c14093c |
| 203 | [DESIGN] name numerology section | not recommended now | c14093c |
| 201 | directional 9×9 model for numerology pairs | **Q4** (value blocked) | c14093c |
| 200 | numerology copy names books/authors | **needs ruling** — do not run as filed | c14093c |
| 198 | [DESIGN] mobile hero motion | not recommended now | c14093c |
| 194 | nothing verifies a cited quotation is within its cited line range | live | — |
| 193 | date gate: inherited-year claims never attribute | **Q3** | c14093c |
| 191 | extract ~22,000 readable lines from data/ | blocked — needs the `data/` machine | c14093c |
| 185 | should the route-table guard become a gate? | **close as "no"** | c14093c |
| 184 | post-#154 cleanup: stale doc pointers + dead code | live; absorbs #214's remnant | c14093c |
| 178 | [BLOCKER] acquire Muhurtha + Lo Shu source | **hold** — 4a unverifiable from a clone | c14093c |
| 177 | no Ashtakoot Guna Milan material in corpus | live | — |
| 175 | Vashya koota collapses the 5×5 matrix | live | — |
| 173 | Rudraksha bead for Life Path 1 and 8 diverges from §11 | live | — |
| 172 | Lo Shu cited as Cheiro in code, disproved 40 lines above | **Q2** | c14093c |
| 171 | Yoni koota article vs tool | **close — fixed** | c14093c |
| 163 | two compatibility tables disagree on 23 of 45 pairs | **close as dup** → #201 | c14093c |
| 159 | [FEATURE] local RAG index | **keep open, re-scope** — closure overturned | c14093c |
| 151 | knowledge/*.md has no Panchang-anga material | deferred — pair with #191 | c14093c |
| 150 | /panchang omits Yamaganda, Gulikai, Brahma Muhurta, moon rise/set | **Q7** | c14093c |
| 140 | [FEATURE] user profiling insights | live | — |
| 131 | [FEATURE] Kundli PDF download | not recommended now | c14093c |
| 129 | [FEATURE] Shodashvarga D-1…D-60 | not recommended now | c14093c |
| 128 | [FEATURE] Ashtakvarga calculator | not recommended now | c14093c |
| 124 | [SEO] Hindi at /hi/… with hreflang | **not now** — needs a dedicated cycle | c14093c |
| 115 | [FEATURE] 3D dasha helix | not recommended now | c14093c |
| 114 | [FEATURE] WebGL birth-chart mandala | not recommended now | c14093c |

---

## Execution log — round 1, 2026-08-25

Ten commits on `claude/github-issues-prioritize-n12fv3`, none pushed. `main` stayed at
`4014f1e` (docs and tooling only, no app code) throughout.

**All four items are QA-verified. Every one failed its first submission.** That is the
headline number and the argument for the loop: none of the defects QA caught was visible in
a diff, and two of them were introduced *by the fix* for the issue being worked.

| Item | Commits | QA |
|---|---|---|
| **#220 + #222** blast aborts silently, leaks addresses | `d394179` → `7743471` | **PASS** (2nd) |
| **#172** Cheiro attribution in code | `6960103` → `ee73ce1` → `e75ac70` | **PASS** (2nd); gate hardening also **PASS** |
| **#217** corpus_search inflections | `77edd70` → `28a5443` | **PASS** (2nd) |
| **#193** date gate checks nothing | `9901948` `62cd675` `129c1df` → `4a918a2` | **PASS** (2nd) |

### What QA caught that review would not have

- **The blast fix reproduced #220's own harm one frame out.** `_mask_email` raised on a
  truthy non-string email at the alert *below* the loop — no alert, no outcome JSON, exactly
  the defect being fixed, relocated by the fix. Found by driving the real route, not reading.
- **#172's fix attached a provenance label nobody measured** (`plain pdftotext` on a count
  recorded for a different search), and left a docstring asserting `[UNSOURCED]` and
  "repeatable across sources" in one paragraph.
- **#172's new gate let the historical defect walk past.** Restoring the pre-#172 header and
  trimming one denial held the mention count at 7; the gate printed "all denials" and exited
  0. `!=` alone would not have caught it — it needed a denial-presence check.
- **#217's justification was measured by a different code path than the tool uses.** The
  rejected candidate scores 5/5 through `variants()` → `_pat()`, not the 3/5 recorded. The
  real reason to reject it is that it flips `nadi` 0→1 on the English word "nadir" — a false
  SOURCED verdict on the highest-weighted koota.
- **#193's harness told a future reader to stand down.** Its "red by design" hint was
  conditional on failure, so it only printed on the run where someone needed the truth: drop
  Gate 4 and it says "That is #193's defect, not a regression."

### The recurring defect class, three times in one session

A justification that outlives its evidence — #172's Cheiro block, #217's measurement,
#193's harness hint, plus `_mask_email`'s "no input can make it raise" docstring. This is
the class `CLAUDE.md` is built around, and it is still the most common thing found here.

### Filed, not fixed

| Issue | What |
|---|---|
| [#223](https://github.com/mahAnuj/astro-ai/issues/223) | a non-dict subscribers row still aborts the blast, no alert — row-level version of #220 |
| [#224](https://github.com/mahAnuj/astro-ai/issues/224) | `mutate_behaviour_suite.py` unusable on a fresh clone; fix is hermetic tests, not the harness |
| [#225](https://github.com/mahAnuj/astro-ai/issues/225) | the short-sections alert guard is correct but ungated |

Also posted: a correction on #217 (the 3/5 figure does not reproduce), evidence comments on
the six proposed closures, and a QA note on #222 flagging that nobody has checked whether
Cloud Scheduler logs a failed attempt's response body — if it does, `failed_emails` is a
live third egress point.

### Environment findings worth carrying forward

- **A fresh clone reports 14 test failures that are not defects** — blocked outbound
  geocoding (9) and no `.env` (5). Two separate agents each spent time rediscovering this
  before doing any work. That is what #224 is for.
- **`data/vedic_astro_textbook.pdf` is tracked**, contradicting CLAUDE.md's "`data/` is
  gitignored". Pre-existing, already noted in #178's thread.
- **Commit signing is configured but impossible**: `commit.gpgsign=true` points at a 0-byte
  public key with no private key present, so every commit lands unsigned — including the two
  already on `main`.
- **Subagents cannot spawn subagents.** `dev-lead` returns a dispatch plan instead; the
  parent session runs the engineer and QA legs. Subagents also cannot reach GitHub, so issue
  text must be inlined into their briefs.

## Scan history

| Date | SHA | Open | Closures proposed | Queue head |
|---|---|---|---|---|
| 2026-08-25 | `c14093c` | 36 | proposed 6; **QA overturned 2** → #171, #214, #185, #163(dup) stand; #159 keep-open; #178 hold | #220 + #222 (assigned) |

### 2026-08-25 — what QA changed

The scan proposed six closures. Re-checking each against the repo and the issue threads
before posting the evidence overturned two:

- **#159** — the thread's own recommendation is *keep open, re-scoped*. The agent read a
  deferral as a decision to drop. Closing would have destroyed a live condition.
- **#178** — scope really does read as empty, but its one surviving item is evidenced only
  by a line in CLAUDE.md that cannot be checked from a clone, and `SOURCES.md` contradicts
  it by omission.

Both failures share a shape: **a verdict derived from a summary rather than from the
source it summarises.** That is the same defect this file is built to resist, arriving
through the process meant to prevent it. Relaying a triage agent is not triage — check the
thread and the tree before acting on its conclusion.
