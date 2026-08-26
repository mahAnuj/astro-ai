#!/usr/bin/env python3
"""Search the source books with transliteration-aware spelling expansion.

WHY THIS EXISTS

Sanskrit terms have no single English spelling, and our books disagree with
our code. Searching the corpus for the spelling *we* use silently returns
nothing, which reads exactly like "this rule is unsourced" — the most
dangerous wrong answer an audit can produce, because it invites someone to
invent a replacement rule.

Measured on the real corpus (77,119 `-layout` lines, 2026-08-16):

    vimshottari      2      vimsottari    134
    navamsha         0      navamsa       275
    dashamsa         0      dasamsa        62
    dasha            5      dasa         2179

Every one of those left-hand numbers would have been read as a gap. During
the Kundli audit the `vimshottari` search nearly produced a false "thinly
sourced" verdict on the dasha engine — the material is there, spelled the
other way.

WHAT IT DOES NOT DO

It does not rank, embed or summarise. It answers two questions exactly:

    "where does the corpus discuss X, under any spelling?"   (search)
    "is X genuinely absent, under EVERY spelling?"           (--absent)

The second is the one that matters. A vector search cannot answer it — it
returns nearest neighbours and never "nothing", so it cannot distinguish an
absent rule from a badly-worded query. Absence has to be proven by exhaustive
matching, which is what `--absent` does: it exits non-zero if ANY variant
matches, so a claim of "not in the corpus" is checkable rather than asserted.

TABLES ARE STILL NOT SAFE TO READ FROM HERE. Scanned PDFs lose table rows in
the text layer without any marker — Cheiro's alphabet page drops A-M entirely
and renders `Y = 1` as `Y = I`. Confirm any table against the rendered page
image (`pdftoppm -f <page> -l <page> -r 200 -png`) before believing it.

LINE NUMBERS ARE FOR CITING. A hit reported at N is the line `grep -n` and
`sed -n 'Np'` give back on `pdftotext -layout <book> -`, because numbering
counts newlines only. It did not always: `splitlines()` also breaks on the form
feed pdftotext writes at every page boundary, so numbers drifted by ~1 per page
(#226). See `_lines()`.

USAGE

    python3 scripts/corpus_search.py "vimshottari"       # find it, any spelling
    python3 scripts/corpus_search.py "vashya" --absent   # prove it is missing
    python3 scripts/corpus_search.py "koota" -c 3        # 3 lines of context

EXIT CODES
    0  search: matches found        | --absent: genuinely absent
    1  search: nothing found        | --absent: FOUND (absence claim is false)
    2  corpus could not be read
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Extraction cache. Deliberately NOT under data/: `_corpus()` ingests every
# *.txt it finds beneath DATA_DIR, so a cache written there would be read back
# as a source book on the next run — double-counting every book and inflating
# the line total that ABSENT verdicts are reported against. That is not
# hypothetical: this tool has already counted `data/emails/sarbani.pdf`, our
# own outreach message, as a source book, which made `Ashtakoot` briefly
# appear present because we had written the word ourselves.
CACHE_DIR = Path(__file__).resolve().parent.parent / ".corpus-cache"

# ─── Transliteration rules, derived from what the corpus actually does ──
#
# Each entry rewrites one spelling convention into its alternatives. They are
# applied combinatorially, so "vimshottari" reaches "vimsottari" via sh->s and
# "navamsha" reaches "navamsa" the same way. Rules are bidirectional because
# the code and the books each use both directions somewhere.
#
# Every rule below was added because a real term in this project needed it —
# none are speculative.
_RULES: tuple[tuple[str, str], ...] = (
    ("sh", "s"),      # vimshottari/vimsottari, navamsha/navamsa, rashi/rasi
    ("oo", "u"),      # koota/kuta, moolatrikona/mulatrikona
    ("aa", "a"),      # Sunaphaa/Sunapha, Anaphaa/Anapha
    ("ee", "i"),      # Kendra spellings, Peedha/Pida
    ("ksh", "x"),     # Lakshmi/Laxmi, Moksha/Moxa
    ("v", "w"),       # Vishti/Wishti, Varna/Warna
    ("ph", "f"),      # Sunapha/Sunafa
    ("th", "t"),      # Chatushpada/Chatuspada, tithi/titi
)

# Irregulars that no rule generates. Kept small and explicit on purpose: a
# long hand-list rots, so anything expressible as a rule belongs above.
# Devanagari equivalents. Without these the tool reports a FALSE ABSENT the
# moment a Sanskrit source enters the corpus — which is exactly what happened
# when Muhurta Chintamani was added: `bhakoot --absent` still printed "no
# spelling matched" while भकूट sat in the file, because every variant it
# generated was Latin. A false absent is the dangerous direction: it retires a
# gap that is still open, or licenses inventing a rule that the corpus has.
#
# Stems, not inflected forms. Sanskrit compounds and case endings mean भकूट
# appears as भकूटं, भकूटगुणाः, दुष्टभकूटपरिहारः — matching the stem catches all
# of them, and the word-boundary rule below is deliberately NOT applied to
# Devanagari, where compounding is the norm rather than the exception.
_DEVANAGARI: dict[str, tuple[str, ...]] = {
    "ashtakoota":   ("अष्टकूट",),
    "koota":        ("कूट",),
    "varna":        ("वर्ण",),
    "vashya":       ("वश्य",),
    "tara":         ("तारा",),
    "yoni":         ("योनि",),
    "graha maitri": ("ग्रहमैत्र", "मैत्री"),
    "gana":         ("गण",),
    "bhakoot":      ("भकूट",),
    "nadi":         ("नाडी",),
    "guna milan":   ("गुणमिलन", "गुण"),
    "tithi":        ("तिथि",),
    "nakshatra":    ("नक्षत्र",),
    "muhurta":      ("मुहूर्त",),
    "dasha":        ("दशा",),
    "lagna":        ("लग्न",),
}

_EXPLICIT: dict[str, tuple[str, ...]] = {
    "dasha":        ("dasa", "dasa"),
    "antardasha":   ("antardasa", "antar dasa", "bhukti"),
    "mahadasha":    ("mahadasa", "maha dasa"),
    "guna milan":   ("gun milan", "melapak", "kuta matching", "36 gunas"),
    "ashtakoota":   ("ashtakuta", "asta kuta", "eight kutas"),
    "graha maitri": ("planetary friendship", "graha maitram"),
    "moolatrikona": ("mulatrikona", "moola trikona"),
    "rahu kaal":    ("rahu kala", "rahukalam", "rahu kalam"),
    "combustion":   ("combust", "astangata", "asta"),
    "nitya yoga":   ("yoga of the day", "daily yoga"),
}


def variants(term: str) -> list[str]:
    """Every spelling of `term` worth searching for, longest first."""
    base = term.lower().strip()
    out = {base}

    # Each rule is applied ONCE, to the original term only — deliberately not
    # to closure. Full combinatorial expansion of these eight rules turns
    # "vimshottari" into 48 spellings, most of them noise like
    # "veemshhoththaaree": slow to match, and short garbage variants risk
    # false positives that would be worse than the miss they are meant to
    # prevent. Every real divergence in this corpus is a single substitution
    # (vimshottari->vimsottari, navamsha->navamsa, koota->kuta,
    # dashamsa->dasamsa), so one pass is sufficient and stays honest.
    for src, dst in _RULES:
        if src in base:
            out.add(base.replace(src, dst))
        if dst in base:
            out.add(base.replace(dst, src))

    # Explicit expansions match on WHOLE WORDS, not substrings. Substring
    # matching made `dashamsa` (the D-10 divisional chart) pull in the
    # "dasha"->"dasa" entry and report 2,105 hits about dasha PERIODS — a
    # false positive far worse than the miss it was meant to prevent, since
    # it would look like abundant sourcing for a rule that has none.
    def _is_word(needle: str, haystack: str) -> bool:
        return re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", haystack) is not None

    lowered = base
    for key, extras in _EXPLICIT.items():
        if _is_word(key, lowered):
            out.update(extras)
        for extra in extras:
            if _is_word(extra, lowered):
                out.add(key)

    for key, deva in _DEVANAGARI.items():
        if _is_word(key, base):
            out.update(deva)

    # A trailing 'a' is dropped freely in these books (Chatushpada/Chatushpad).
    # Floor of 6 characters BEFORE dropping: shorter truncations are
    # degenerate. "vashya" -> "vashy" -> "vasy" matched inside "amavasya" and
    # reported Vashya as sourced when it is not — a false SOURCED verdict,
    # which is strictly worse than a miss because it retires a real gap.
    # Applied to the ORIGINAL term only, never to rule-derived variants.
    # Stacking it on a derivation turned "vashya" into "washya" (v->w) into
    # "washy", which then matched "wishy-washy" in Cheiro and reported Vashya
    # as present. Each transformation is defensible alone; composing them
    # manufactures words that are in no tradition.
    if base.endswith("a") and len(base) >= 6:
        out.add(base[:-1])

    return sorted(out, key=len, reverse=True)


# ─── Case endings, and why relaxing the trailing boundary cannot find them ──
#
# Sanskrit a-stems inflect by REPLACING the stem's final -a, not by appending
# to it: `maudhya` becomes `maudhyena`, `maudhyasya`. The search term is
# therefore not a substring of its own inflected form, so NO relaxation of the
# trailing boundary can ever reach those — `maudhyena` does not contain
# `maudhya`. That is #217: `maudhya --absent` printed a clean absence while
# `Maudhyam` sits in Rao Vol. I.
#
# Measured 2026-08-25 against the five forms the gate fixtures carry — the
# three endings #217 names (-am, -ena, -asya) plus the locative -e — through
# the pipeline the tool actually uses, variants() then _pat(). The path is the
# whole point: variants() already emits the truncated stem `maudhy`, so a
# candidate can reach -ena and -e through that stem even though it cannot
# reach them through `maudhya`. Scored on the base spelling alone, the middle
# row reads 3/5 and looks refuted; scored the way the tool searches, it is not.
#
#                          base only   via variants()
#     s?(?![a-z])             0/5           0/5    the pattern that shipped
#     suffix set, #217 (a)    2/5           4/5    -ena and -e are appended to
#                                                  nothing, so they stay unseen
#     (?![a-z]{4,}), #217 (b) 3/5           5/5    finds all five, via `maudhy`
#     stem + ending set       5/5           5/5    and rejects maudhyamika
#
# So (b) is NOT refuted on form count. It is rejected on what ELSE it finds.
# Over 92 terms on the one book then in data/ (vedic_astro_textbook.pdf,
# 16,724 lines) it changes 16 terms' counts where this pattern changes none:
#
#     nadi        0 ->    1   "the northern direction (nadir – 4th house)"
#     hora       45 ->   47   "prasna or horary astrology"
#     bala       55 ->   60   "loss of status and balance"; "Balava", a karana
#     dasha    1300 -> 1314   "Dasamsa Chart (D-10)"; "Dasami", a tithi
#
# `nadi` matching the English word "nadir" is a false SOURCED verdict on one
# of the eight kootas — the direction this module's docstring calls the worse
# error, and worse than the false negative #217 was filed about. Some of (b)'s
# extra hits are genuine compounds (kendradi, nakshatramsa, vargottamamsa), so
# the trade is not one-sided; the counts are corpus-dependent on the books
# actually present (`scripts/fetch_corpus.py` is the registry and reports the
# live count) and would move with the rest. The asymmetry of the two errors does not move.
#
# (An earlier version of this comment recorded 3/5 for (b) with the reasoning
# "still blind to -ena and -e", and the #217 commit message recorded 0/5 and
# 3/5 as "both fixes the issue proposed". Neither reproduces: 0/5 is the
# SHIPPED pattern, not a proposal, and 3/5 is a base-spelling measurement of a
# tool that does not search that way. The 1/5 and 4/5 that triage handed down
# do not reproduce either. Superseded by the table above.)
#
# The ending set is explicit and short on purpose. "Any one-to-four letters
# may follow" re-opens the false-SOURCED direction the boundary was tightened
# to close, and a false SOURCED verdict retires a gap that is still open.
_ENDINGS: tuple[str, ...] = (
    "asya", "ani", "ena", "aya", "am", "as", "ah", "at", "ay", "e",
)


def _pat(v: str) -> "re.Pattern[str]":
    """The match pattern for one spelling.

    Letters only on the boundaries: a term may legitimately sit against a
    digit, hyphen or punctuation in these books ("Vimsottari-dasa", "7 kuta").
    Optional trailing "s" so plurals still count — the books write "navamsas"
    and "dasamsas" freely, and excluding them lost 6 and 12 real hits
    respectively when the boundary was first tightened.
    """
    # Devanagari terms match as substrings: भकूट legitimately appears
    # inside भकूटगुणाः and दुष्टभकूटपरिहारः, and requiring a boundary
    # would miss every compound — which in Sanskrit is most of them.
    if any(ord(ch) > 0x0900 for ch in v):
        return re.compile(re.escape(v))

    body = rf"{re.escape(v)}s?"
    # Same 6-character floor as the trailing-'a' drop in variants(). Note what
    # is NOT claimed: lowering it to 3 was measured against the present corpus
    # and changed no count, so this floor guards a risk rather than a hit we
    # have seen. Keep it anyway — a 3-letter stem plus a 2-letter ending is
    # short enough to land inside English prose, and the wrong direction here
    # is a false SOURCED verdict, which retires a gap that is still open.
    if v.endswith("a") and len(v) >= 6:
        body += "|" + re.escape(v[:-1]) + "(?:" + "|".join(_ENDINGS) + ")"
    # The LEADING (?<![a-z]) governs the whole alternation, and it is the only
    # thing keeping "vasya" out of "amavasya" and "washy" out of "wishy-washy".
    # #217 is a trailing-side change; do not weaken this half.
    return re.compile(rf"(?<![a-z])(?:{body})(?![a-z])")


# Directories under data/ that are NOT source books (#159 QA, BUG-1).
#
# `data/emails/sarbani.pdf` is our own outreach message to an astrologer. It
# discusses "Ashtakoot cancellations" and "Manglik detection" because WE wrote
# those words, and an unfiltered rglob over data/ made the tool cite our own
# prose back to us as classical sourcing: `--absent "ashtakoota"` exited 1 on
# two hits that are both ours, contradicting a measured absence CLAUDE.md
# records as settled.
#
# That is the exact failure this module's docstring warns about — a false
# SOURCED verdict, worse than a miss because it retires a real gap. A search
# tool that quotes the project back to itself is not a source of truth.
_EXCLUDED_DIRS = {"emails", "daily_cache"}


def _is_excluded(pdf: Path) -> bool:
    return any(part in _EXCLUDED_DIRS for part in pdf.relative_to(DATA_DIR).parts[:-1])


_CACHE_HITS: list[str] = []
_CACHE_MISSES: list[str] = []


def _pdftotext_version() -> str:
    """Identify the extractor, so a poppler upgrade invalidates the cache.

    Different poppler versions reflow columns differently, and this corpus is
    full of tables. A cache keyed only on the file would survive an upgrade and
    silently serve text the current binary would not produce.
    """
    try:
        res = subprocess.run(["pdftotext", "-v"], capture_output=True,
                             text=True, timeout=10)
        return (res.stdout + res.stderr).strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return "unknown"


def _cache_key(pdf: Path, tool: str) -> str:
    """Content identity for one extraction, without reading the PDF.

    Keyed on (path, size, mtime, extractor, flags). Hashing 12 MB of PDF on
    every run would give back much of what the cache saves; size+mtime is the
    standard build-system trade and is enough here, where the books are
    write-once.

    The FLAGS are part of the key on purpose. `-layout` yields ~30% fewer lines
    than plain `pdftotext` because it reflows columns, and this repo has already
    had two line-count tables disagree purely because they mixed the two. A
    cache that ignored the flag would make that confusion permanent.
    """
    st = pdf.stat()
    raw = f"{pdf.resolve()}|{st.st_size}|{st.st_mtime_ns}|{tool}|-layout"
    return hashlib.sha256(raw.encode()).hexdigest()


def _corpus(use_cache: bool = True) -> dict[str, str]:
    """Extracted text per book. `-layout` preserves table columns.

    Extraction is cached per book under `.corpus-cache/`, because `pdftotext`
    re-ran on every invocation and this tool is meant to be called repeatedly —
    a QA sourcing pass checks many terms, and each one paid the full extraction
    of every book again.

    Only a SUCCESSFUL, non-empty extraction is ever cached. The refusal below
    is what every ABSENT verdict rests on; caching a failure would convert a
    loud "refusing to search a partial corpus" into a permanent silent one.
    """
    if not DATA_DIR.is_dir():
        print(f"FAIL: {DATA_DIR} not found.", file=sys.stderr)
        raise SystemExit(2)
    if not shutil.which("pdftotext"):
        print("FAIL: pdftotext not installed (brew install poppler).", file=sys.stderr)
        raise SystemExit(2)

    out: dict[str, str] = {}

    # Plain-text sources are read as-is. archive.org publishes its OCR as a
    # `_djvu.txt` beside each scan, and for image-only PDFs that text is the
    # ONLY usable form — Raman's Muhurtha extracts to 0 lines as a PDF but
    # 9,158 lines as djvu text. Taking the .txt is not a shortcut; it is the
    # same OCR the PDF's text layer would have carried if it had one.
    for txt in sorted(DATA_DIR.rglob("*.txt")):
        if _is_excluded(txt):
            continue
        try:
            out[txt.name] = txt.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: could not read {txt.name}: {exc}", file=sys.stderr)
            raise SystemExit(2) from None

    tool = _pdftotext_version() if use_cache else ""
    for pdf in sorted(DATA_DIR.rglob("*.pdf")):
        if _is_excluded(pdf):
            continue

        cached = CACHE_DIR / f"{_cache_key(pdf, tool)}.txt" if use_cache else None
        if cached is not None and cached.is_file():
            try:
                text = cached.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                text = ""
            # An empty cache entry must never satisfy a lookup — see the
            # refusal below. Treat it as a miss and re-extract.
            if text.strip():
                out[pdf.name] = text
                _CACHE_HITS.append(pdf.name)
                continue

        try:
            res = subprocess.run(
                ["pdftotext", "-layout", str(pdf), "-"],
                capture_output=True, text=True, timeout=180,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL: could not extract {pdf.name}: {exc}", file=sys.stderr)
            raise SystemExit(2) from None
        # A book that fails to parse must NOT silently contribute "" — every
        # ABSENT verdict rests on having actually read every book, and an
        # empty string looks identical to a book that genuinely lacks the
        # term. One real PDF in this corpus already emits "Syntax Error:
        # Failed to parse XRef entry / try to reconstruct" during extraction,
        # so this is one bad reconstruct away from producing a confident,
        # wrong "unsourced" verdict.
        if res.returncode != 0 or not res.stdout.strip():
            print(f"FAIL: {pdf.name} extracted to {len(res.stdout)} bytes "
                  f"(rc={res.returncode}). Refusing to search a partial corpus.",
                  file=sys.stderr)
            raise SystemExit(2)
        out[pdf.name] = res.stdout
        _CACHE_MISSES.append(pdf.name)
        if cached is not None:
            # Write via a temp file in the same directory, then rename. A
            # half-written cache entry that still passed the .strip() check
            # above would be served as a complete book, and a truncated book is
            # exactly how a false ABSENT verdict gets manufactured.
            try:
                CACHE_DIR.mkdir(exist_ok=True)
                tmp = cached.with_suffix(f".{os.getpid()}.tmp")
                tmp.write_text(res.stdout, encoding="utf-8")
                tmp.replace(cached)
            except Exception:  # noqa: BLE001
                pass  # a cache that cannot be written must not break a search
    if not out:
        print("FAIL: no source books found under data/.", file=sys.stderr)
        raise SystemExit(2)
    return out


def _lines(text: str) -> list[str]:
    """Split a book into lines FOR REPORTING — on "\n" only, never splitlines().

    `str.splitlines()` also breaks on form feeds, and `pdftotext` emits one per
    page: 515 of them in vedic_astro_textbook.pdf alone. Numbering that way
    drifts by roughly one per page against `grep -n` and `sed -n 'Np'`, which is
    what anyone re-checking a citation actually uses — this tool reported
    "Six upagrahas called" at 1741 where `grep -n` says 1688, and
    "Gulika rises at the middle" at 1813 against 1758 (#226). A pinpoint
    citation that cannot be resolved again is the failure mode this whole tool
    exists to prevent, arriving through the tool built to prevent it.

    A form feed left sitting inside its line is harmless: matching never looks
    at line numbers, so hit counts and --absent verdicts were never affected by
    this and no absence verdict needs revisiting.
    """
    lines = text.split("\n")
    # `split` yields a trailing "" where `splitlines` yields nothing, for text
    # that ends in a newline. It cannot shift any line number — it is last —
    # but it would print a phantom blank line in the -c context window, so drop
    # it. Only the one: interior blank lines are real lines and are numbered.
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _scan(text: str, spellings: list[str],
          patterns: dict[str, "re.Pattern[str]"],
          ) -> tuple[list[str], list[tuple[int, str, str]]]:
    """One book's hits as (line number, spelling, line), plus its lines.

    Line numbers are 1-based over `_lines()`, so they agree with `grep -n` and
    are resolvable with `sed -n 'Np'`. Kept out of `main()` so the gate can
    assert on the numbering the tool actually reports rather than on a copy of
    this loop — the #226 defect lived in exactly these three lines and no
    fixture could reach them while they sat inside `main()`.
    """
    lines = _lines(text)
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        low = line.lower()
        for v in spellings:
            # WORD boundaries, not substrings. Substring matching found
            # "vasya" inside "amavasya" and "washy" inside "wishy-washy",
            # reporting 13 hits for a term the corpus does not contain.
            if patterns[v].search(low):
                hits.append((i + 1, v, line))
                break
    return lines, hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("term")
    ap.add_argument("--absent", action="store_true",
                    help="assert the term is absent under every spelling; "
                         "exit 1 if any variant matches")
    ap.add_argument("-c", "--context", type=int, default=0,
                    help="lines of context to print around each hit")
    ap.add_argument("--max-hits", type=int, default=8,
                    help="hits to print per book (default 8)")
    ap.add_argument("--no-cache", action="store_true",
                    help="re-extract every book instead of using .corpus-cache/")
    args = ap.parse_args()

    spellings = variants(args.term)
    _patterns = {v: _pat(v) for v in spellings}
    corpus = _corpus(use_cache=not args.no_cache)
    total_lines = sum(t.count("\n") for t in corpus.values())

    print(f"term      : {args.term!r}")
    print(f"spellings : {len(spellings)} — {', '.join(spellings[:12])}"
          + (" …" if len(spellings) > 12 else ""))
    print(f"corpus    : {len(corpus)} books, {total_lines:,} lines (-layout)")
    if _CACHE_HITS or _CACHE_MISSES:
        # Say which books came from cache. An ABSENT verdict is only as good as
        # the text behind it, and "cached" is a fact the reader needs in order
        # to know what to re-check if they suspect the extraction.
        print(f"pdf cache : {len(_CACHE_HITS)} cached, "
              f"{len(_CACHE_MISSES)} extracted"
              + (f" ({', '.join(n[:28] for n in _CACHE_MISSES)})"
                 if _CACHE_MISSES else ""))
    for name, text in sorted(corpus.items()):
        print(f"            - {name[:58]:<58} {text.count(chr(10)):>6,} lines")
    print()

    grand = 0
    per_variant: dict[str, int] = {}
    for name, text in sorted(corpus.items()):
        lines, hits = _scan(text, spellings, _patterns)
        if not hits:
            continue
        for _, v, _line in hits:
            per_variant[v] = per_variant.get(v, 0) + 1
        grand += len(hits)
        print(f"  {name}  —  {len(hits)} hit(s)")
        for ln, v, line in hits[:args.max_hits]:
            print(f"    {ln:>6}  [{v}]  {line.strip()[:110]}")
            if args.context:
                lo = max(0, ln - 1 - args.context)
                hi = min(len(lines), ln + args.context)
                for c in range(lo, hi):
                    if c != ln - 1:
                        print(f"            | {lines[c].strip()[:104]}")
        if len(hits) > args.max_hits:
            print(f"    … and {len(hits) - args.max_hits} more")
        print()

    if per_variant:
        print("  spelling that actually matched:")
        for v, n in sorted(per_variant.items(), key=lambda kv: -kv[1]):
            print(f"    {v:<28} {n}")
        print()

    if args.absent:
        if grand:
            print(f"ABSENCE CLAIM IS FALSE — {grand} hit(s) across "
                  f"{len(per_variant)} spelling(s).")
            return 1
        print(f"NO SPELLING MATCHED — 0 hits for any of {len(spellings)} "
              f"spellings across {total_lines:,} lines.")
        print()
        print("  This proves the TERM is absent, not the CONCEPT. Before")
        print("  reporting a rule as unsourced, check its constituent names:")
        print("  'nitya yoga' matches nothing while vyatipata and vaidhriti —")
        print("  the two yogas muhurat.py actually blocks on — are in the books;")
        print("  'graha maitri' matches nothing while planetary friendship is")
        print("  covered 170 times under 'naisargika' and 'friendship'.")
        return 0

    if not grand:
        print(f"No hits for any of {len(spellings)} spellings. "
              f"Re-run with --absent to record that as a verified absence.")
        return 1
    print(f"{grand} hit(s) total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
