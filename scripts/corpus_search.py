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
import re
import shutil
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

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


def _corpus() -> dict[str, str]:
    """Extracted text per book. `-layout` preserves table columns."""
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

    for pdf in sorted(DATA_DIR.rglob("*.pdf")):
        if _is_excluded(pdf):
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
    if not out:
        print("FAIL: no source books found under data/.", file=sys.stderr)
        raise SystemExit(2)
    return out


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
    args = ap.parse_args()

    spellings = variants(args.term)
    # Letters only on the boundaries: a term may legitimately sit against a
    # digit, hyphen or punctuation in these books ("Vimsottari-dasa", "7 kuta").
    # Optional trailing "s" so plurals still count — the books write
    # "navamsas" and "dasamsas" freely, and excluding them lost 6 and 12 real
    # hits respectively when the boundary was first tightened.
    _patterns = {
        v: re.compile(rf"(?<![a-z]){re.escape(v)}s?(?![a-z])")
        for v in spellings
    }
    corpus = _corpus()
    total_lines = sum(t.count("\n") for t in corpus.values())

    print(f"term      : {args.term!r}")
    print(f"spellings : {len(spellings)} — {', '.join(spellings[:12])}"
          + (" …" if len(spellings) > 12 else ""))
    print(f"corpus    : {len(corpus)} books, {total_lines:,} lines (-layout)")
    for name, text in sorted(corpus.items()):
        print(f"            - {name[:58]:<58} {text.count(chr(10)):>6,} lines")
    print()

    grand = 0
    per_variant: dict[str, int] = {}
    for name, text in sorted(corpus.items()):
        lines = text.splitlines()
        hits: list[tuple[int, str, str]] = []
        for i, line in enumerate(lines):
            low = line.lower()
            for v in spellings:
                # WORD boundaries, not substrings. Substring matching found
                # "vasya" inside "amavasya" and "washy" inside "wishy-washy",
                # reporting 13 hits for a term the corpus does not contain.
                if _patterns[v].search(low):
                    hits.append((i + 1, v, line))
                    per_variant[v] = per_variant.get(v, 0) + 1
                    break
        if not hits:
            continue
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
