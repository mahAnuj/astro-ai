#!/usr/bin/env python3
"""Get the source books in `data/` onto this machine, and prove they are the right ones.

`data/` is gitignored, so a fresh clone or container holds a subset — often one
book of seven. CLAUDE.md is blunt about why that matters: "An absence measured
against a partial corpus is worthless." Every `--absent` result, every "not in
the corpus" verdict, and issues #163/#191/#201/#217 all rest on which books are
actually present. This script makes that state explicit and repeatable instead
of a manual drop nobody records.

    uv run python scripts/fetch_corpus.py                 # report only
    uv run python scripts/fetch_corpus.py --fetch         # download the free ones
    uv run python scripts/fetch_corpus.py --from-dir ~/books
    uv run python scripts/fetch_corpus.py --from-bucket   # $BHAGYA_STORAGE_BUCKET

VERIFICATION IS THE POINT, not the download. Each entry carries the plain
`pdftotext` line count recorded in knowledge/SOURCES.md. Measured 2026-08-26 on
poppler 24.02.0, `data/vedic_astro_textbook.pdf` extracts to **exactly** 20,669
lines against SOURCES.md's recorded 20,669 — so the count is a real fingerprint,
not a rough guide. A different edition, a sample copy, or a truncated download
lands on a different number and is REJECTED. Silently accepting one of those is
how a false absence reaches a published astrological claim.

WHY SOME BOOKS ARE NOT DOWNLOADABLE HERE. Two are distributed free by their
author or publisher and carry a URL below. The other four are commercial,
in-copyright titles that this project already owns as purchased copies; they are
marked `owned` and carry their publisher and ISBN rather than a link. Do NOT add
mirror URLs for those — an unauthorised mirror is also, in practice, how you end
up with a silently different edition and a corpus whose line counts no longer
mean anything. Bring your own copy via --from-dir or --from-bucket.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Tolerance on the recorded line count. Exact is what we expect and what we get
# on poppler 24.02.0; the band exists only so a poppler upgrade reports OK-with-
# a-delta rather than failing the whole corpus. It is deliberately tight: a
# sample copy or a wrong edition misses by far more than this.
TOLERANCE = 0.02


@dataclass(frozen=True)
class Book:
    filename: str
    author: str
    title: str
    lines: int          # plain `pdftotext` (NO -layout), per knowledge/SOURCES.md
    source: str         # a URL, or "owned"
    note: str = ""


# Row numbers match knowledge/SOURCES.md, which keeps them stable so older issue
# comments referencing "source 9" still resolve. 5 and 8 are retired scans.
BOOKS: tuple[Book, ...] = (
    Book("Astrology For Beginners BVRaman_text.pdf", "B.V. Raman",
         "Astrology for Beginners", 15_409, "owned",
         "In print. Commercial title — supply your own copy."),
    Book("vedic_astro_textbook.pdf", "P.V.R. Narasimha Rao",
         "Vedic Astrology: An Integrated Approach", 20_669,
         "https://www.vedicastrologer.org/articles/vedic_astro_textbook.pdf",
         "Author-distributed on his own site."),
    Book("book1-for-CD.pdf", "P.V.R. Narasimha Rao",
         "Lessons on Vedic Astrology, Vol. I (Lessons 1-45)", 12_244,
         "https://www.vedicastrologer.org/classes/book1-for-CD.pdf",
         "Author-distributed; companion to his free mp3 class series."),
    Book("Astrology-e-book-compressed.pdf", "Chennareddy Vasudev",
         "Astrology (e-book)", 5_220,
         "https://shanthavasanthatrust.org/wp-content/uploads/2023/08/"
         "Astrology-e-book-compressed.pdf",
         "Published free by Shantha Vasantha Trust."),
    Book("Numerology-With Tantra, Ayurveda, and Astrology.pdf", "Harish Johari",
         "Numerology: With Tantra, Ayurveda, and Astrology", 5_952, "owned",
         "Destiny Books / Inner Traditions, 1990. ISBN 9780892812585. In print. "
         "Blocks #163, #201, #173 — the highest-value item to supply."),
    Book("Numerology-You.pdf", "Jayant Kumar",
         "Numerology & You", 1_110, "owned",
         "Educreation, 2016. ISBN 978-1-61813-620-6. Our copy is a 43-page "
         "publisher sample, so its 1,110 lines are the SAMPLE, not the book."),
    Book("Numerology the Complete Guide, Volume 1-The Personality Reading.pdf",
         "Matthew Oliver Goodwin",
         "Numerology: The Complete Guide, Vol. 1", 28_171, "owned",
         "Newcastle Publishing, 1981. Western/Pythagorean, NOT Vedic — see "
         "SOURCES.md before citing. Largest single item in #191."),
)


def count_lines(pdf: Path) -> int | None:
    """Plain `pdftotext` line count, or None if it cannot be read.

    No -layout, deliberately: SOURCES.md's counts are plain, and -layout reflows
    columns for ~30% fewer lines. Mixing the two made an earlier revision of that
    table meaningless, which is why the flag is stated wherever a count is.
    """
    try:
        out = subprocess.run(["pdftotext", str(pdf), "-"],
                             capture_output=True, timeout=300)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace").count("\n")


def verdict(book: Book, path: Path) -> tuple[str, str]:
    """(status, detail) for a file that exists on disk."""
    n = count_lines(path)
    if n is None:
        return "UNREADABLE", "pdftotext could not extract it"
    if n == book.lines:
        return "VERIFIED", f"{n:,} lines, exact match"
    drift = abs(n - book.lines) / book.lines
    if drift <= TOLERANCE:
        return "OK", f"{n:,} lines vs {book.lines:,} recorded ({drift:.1%} — poppler drift?)"
    return "MISMATCH", (f"{n:,} lines vs {book.lines:,} recorded ({drift:.0%} off) — "
                        f"wrong edition, sample, or truncated download")


def download(url: str, dest: Path) -> tuple[bool, str]:
    """Fetch to a temp file and move into place only once it looks like a PDF.

    Atomic on purpose: a half-finished download left at `dest` reads as "the book
    is present" to corpus_search.py and to every absence check downstream.
    """
    tmp = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "astro-ai-fetch-corpus/1"})
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 — https URLs above
            data = r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        return False, f"{type(e).__name__}: {e}"
    if not data.startswith(b"%PDF"):
        return False, f"not a PDF (got {len(data):,} bytes starting {data[:16]!r})"
    try:
        fd, tmp = tempfile.mkstemp(dir=str(dest.parent), suffix=".part")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        shutil.move(tmp, dest)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return True, f"{len(data):,} bytes"


def supply_from(src_dir: Path, book: Book, dest: Path) -> tuple[bool, str]:
    cand = src_dir / book.filename
    if not cand.is_file():
        return False, f"not found in {src_dir}"
    shutil.copy2(cand, dest)
    return True, f"copied from {cand}"


def supply_from_bucket(bucket: str, book: Book, dest: Path) -> tuple[bool, str]:
    try:
        from google.cloud import storage  # imported lazily: only this path needs it
    except ImportError:
        return False, "google-cloud-storage is not installed"
    try:
        blob = storage.Client().bucket(bucket).blob(f"corpus/{book.filename}")
        if not blob.exists():
            return False, f"gs://{bucket}/corpus/{book.filename} not found"
        blob.download_to_filename(str(dest))
    except Exception as e:  # noqa: BLE001 — report any GCS failure, never half-write
        if dest.exists():
            dest.unlink()
        return False, f"{type(e).__name__}: {e}"
    return True, f"from gs://{bucket}/corpus/{book.filename}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true",
                    help="download the entries that carry a free, author- or "
                         "publisher-distributed URL")
    ap.add_argument("--from-dir", metavar="DIR",
                    help="copy any missing book found in DIR (for your own copies)")
    ap.add_argument("--from-bucket", nargs="?", const="", metavar="BUCKET",
                    help="pull from gs://BUCKET/corpus/ (default $BHAGYA_STORAGE_BUCKET)")
    ap.add_argument("--force", action="store_true",
                    help="re-obtain even books already present and verified")
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    bucket = None
    if args.from_bucket is not None:
        bucket = args.from_bucket or os.environ.get("BHAGYA_STORAGE_BUCKET", "")
        if not bucket:
            print("--from-bucket needs a name or $BHAGYA_STORAGE_BUCKET", file=sys.stderr)
            return 2

    if shutil.which("pdftotext") is None:
        print("WARNING: pdftotext not found — files cannot be verified, only placed.\n",
              file=sys.stderr)

    present = bad = 0
    print(f"corpus target: {DATA_DIR}\n")
    for b in BOOKS:
        dest = DATA_DIR / b.filename
        acted = ""

        if not dest.exists() or args.force:
            if bucket:
                ok, why = supply_from_bucket(bucket, b, dest)
                acted = f"    bucket: {why}"
            if not dest.exists() and args.from_dir:
                ok, why = supply_from(Path(args.from_dir).expanduser(), b, dest)
                acted = f"    from-dir: {why}"
            if not dest.exists() and args.fetch and b.source != "owned":
                ok, why = download(b.source, dest)
                acted = f"    download: {why}"

        if dest.exists():
            status, detail = verdict(b, dest)
            if status in ("VERIFIED", "OK"):
                present += 1
            else:
                bad += 1
        else:
            status = "MISSING"
            detail = ("commercial title — supply your own copy"
                      if b.source == "owned" else "run with --fetch")

        print(f"  [{status:<10}] {b.filename}")
        print(f"               {b.author} — {b.title}")
        print(f"               {detail}")
        if b.note:
            print(f"               {b.note}")
        if acted:
            print(acted)
        if status == "MISSING" and b.source != "owned":
            print(f"               free: {b.source}")
        print()

    total = len(BOOKS)
    print(f"corpus completeness: {present}/{total} usable"
          + (f", {bad} present but WRONG" if bad else ""))
    if present < total:
        print("\nAn absence measured against a partial corpus is worthless.")
        print("Say which books were present whenever you report one (CLAUDE.md).")
    # Non-zero only for a file that is present and wrong — that is a defect.
    # Merely missing is the normal state of a fresh clone, not a failure.
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
