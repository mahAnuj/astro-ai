#!/usr/bin/env python3
"""Render both subscriber email templates and prove the Rashifal cards appear.

WHY THIS EXISTS
---------------
`welcome.html` unpacked THREE names out of `rashifal_sections` while `main.py`
has been building FOUR-tuples — `(glyph, title, teaser, body)` — since 3c8345b.
Every render where the Rashifal LLM call SUCCEEDED therefore raised
`ValueError: too many values to unpack (expected 3)`, the caller logged and
carried on, and the new subscriber got no welcome email at all. The feature
worked only in its failure mode: when generation failed, `sections` was `[]`,
the `{% if rashifal_sections %}` guard skipped the loop, and the email sent
fine. Issue #145. Nothing in the repo could have noticed — there is no test
suite, and a template arity error is invisible to a diff and to `ast.parse`.

This script is that missing check: one command, PASS/FAIL, exit 0 or 1.

  Gate 1 - digest render (all 12 rashis).  Both templates rendered in `en` and
      `hi` against the real 4-tuples `main.py` constructs, with the panchang,
      shlok, festival and trivia context keys `_email_context()` supplies. A
      raise fails. Rendering is not enough on its own, so this gate also
      asserts every rashi glyph, every rashi title and the first section's
      teaser text are present in the output — a render that silently skipped
      the loop must not pass, because a silently skipped loop is exactly how
      #145 hid for as long as it did.

  Gate 2 - single-rashi render.  Subscribers who pick one rashi get a
      one-element list (`_filter_rashi_sections`), which both templates treat
      as the non-digest mode and show the full body for. Asserts the body's
      LAST sentence — the part no teaser contains — reaches the output, so a
      template that dropped `body` and showed the teaser twice fails here.

  Gate 3 - empty-sections render.  The Rashifal-generation-failed path, which
      before #145 was the ONLY path that worked. Must still render, and must
      contain no rashi title at all: the guard has to skip the block cleanly
      rather than emit a headed-but-empty section.

  Gate 4 - wrong arity is actually detected.  Feeds both templates a list of
      3-tuples (the shape `welcome.html` used to expect) and requires BOTH to
      raise. Without this gate, a template that stopped unpacking the tuple
      would sail through gates 1-3 and this script would be decoration. This
      gate is what makes gates 1-3 mean something.

WHAT THIS DOES NOT DO
---------------------
It does not import `main.py`. That module builds the FastAPI app, reads
environment variables and touches GCS at import time, and it is edited
constantly — a gate that fails because an unrelated route was mid-edit is a
gate people learn to ignore. The fixture below instead reproduces the tuple
`main.py` builds, using the same `symbol_for_rashi_label()` and
`parse_sectioned_reading()` helpers it calls, plus a local copy of its
2-sentence teaser split. If `_send_welcome_email` ever changes the SHAPE of
those tuples, update `_sections_from_reading()` here in the same commit.

The panchang object is a stub, not a computed one: `_panchang_for_city()`
geocodes over the network, and a template gate must not need Nominatim to be
up. Only the six attributes the templates actually read are provided, so a
template that starts reading a seventh fails loudly here rather than in a
subscriber's inbox.

Usage:  uv run python scripts/verify_email_templates.py
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "src" / "astro_ai" / "templates"

sys.path.insert(0, str(REPO_ROOT / "src"))

from fastapi.templating import Jinja2Templates  # noqa: E402

from astro_ai import festivals  # noqa: E402
from astro_ai import shloks  # noqa: E402
from astro_ai import trivia  # noqa: E402
from astro_ai.chart import symbol_for_rashi_label  # noqa: E402
from astro_ai.llm import parse_sectioned_reading  # noqa: E402

WELCOME = "email/welcome.html"
DAILY = "email/daily_rashifal.html"
TEMPLATE_NAMES = (WELCOME, DAILY)

# 2026-11-08 carries Diwali AND Narak Chaturdashi, so the festival callout is
# exercised in its multi-entry form rather than its one-entry form.
FIXTURE_DATE = date(2026, 11, 8)

RASHI_LABELS: tuple[str, ...] = (
    "Aries / Mesha", "Taurus / Vrishabha", "Gemini / Mithuna",
    "Cancer / Karka", "Leo / Simha", "Virgo / Kanya",
    "Libra / Tula", "Scorpio / Vrishchika", "Sagittarius / Dhanu",
    "Capricorn / Makara", "Aquarius / Kumbha", "Pisces / Meena",
)

# Deliberately plain ASCII with no quotes or angle brackets, so the substring
# assertions below compare against text autoescaping cannot have rewritten.
TEASER_SENTENCE_1 = "The Moon lends {label} a steady morning."
TEASER_SENTENCE_2 = "Money matters settle before noon for {label}."
BODY_TAIL_SENTENCE = "By evening {label} should close the loop on one promise."


def _reading_text(labels: tuple[str, ...]) -> str:
    """A synthetic LLM reading in the `## Heading` form the prompt asks for."""
    blocks = []
    for label in labels:
        # Paragraph-SEPARATED, not space-joined. Real generated bodies carry
        # ~6 newlines (3-4 paragraphs); a fixture that is one flat line cannot
        # detect the HTML newline collapse that Gate 5 exists to catch.
        body = "\n\n".join(
            s.format(label=label)
            for s in (TEASER_SENTENCE_1, TEASER_SENTENCE_2, BODY_TAIL_SENTENCE)
        )
        blocks.append(f"## {label}\n{body}")
    return "\n\n".join(blocks)


def _teaser(body: str, sentences: int = 2) -> str:
    """Local copy of `main.py:_rashifal_teaser` — see WHAT THIS DOES NOT DO."""
    parts = re.split(r"(?<=[.!?])\s+", (body or "").strip())
    return " ".join(parts[:sentences]).strip()


def _sections_from_reading(labels: tuple[str, ...]) -> list[tuple[str, str, str, str]]:
    """The exact 4-tuple `_send_welcome_email` and the daily sender build."""
    return [
        (symbol_for_rashi_label(title) or "✦", title, _teaser(body), body)
        for title, body in parse_sectioned_reading(_reading_text(labels))
    ]


def _stub_panchang() -> SimpleNamespace:
    def at(h: int, m: int) -> datetime:
        return datetime(FIXTURE_DATE.year, FIXTURE_DATE.month, FIXTURE_DATE.day, h, m)

    return SimpleNamespace(
        sunrise=at(6, 38), sunset=at(17, 29),
        rahu_kaal_start=at(16, 6), rahu_kaal_end=at(17, 29),
        abhijit_start=at(11, 43), abhijit_end=at(12, 27),
    )


def _context(*, lang: str, sections: list, with_panchang: bool = True) -> dict:
    """The context `_email_context()` produces, plus the two keys the senders
    add afterwards (`rashifal_sections`, `unsubscribe_url`)."""
    return {
        "lang": lang,
        "today_iso": FIXTURE_DATE.isoformat(),
        "today_pretty": FIXTURE_DATE.strftime("%A, %d %B %Y"),
        "panchang": _stub_panchang() if with_panchang else None,
        "shlok": shloks.shlok_for_date(FIXTURE_DATE),
        "festivals": festivals.festivals_for_date(FIXTURE_DATE),
        "trivia": trivia.trivia_for_date(FIXTURE_DATE),
        "site_url": "https://shubhagya.com",
        "rashifal_sections": sections,
        "unsubscribe_url": "https://shubhagya.com/unsubscribe?email=qa@example.com&token=deadbeef",
    }


# Same autoescape behaviour as the app's environment, built without importing
# main.py. This one is Starlette's `directory=` default, which for .html is
# identical to the explicit pin in routes/deps.py (#409); the pin itself is
# asserted by tests/test_autoescape_pinned.py, against the REAL `templates.env`,
# so this gate renders the email templates escaped only for as long as that test
# holds. (It used to be an unasserted comment: nothing failed if either side
# turned autoescape off.)
_env = Jinja2Templates(directory=str(TEMPLATES_DIR)).env


def _render(name: str, ctx: dict) -> str:
    return _env.get_template(name).render(**ctx)


# --------------------------------------------------------------------------
# Gate 1 - digest render, all 12 rashis, both templates, both languages
# --------------------------------------------------------------------------

def gate_1_digest_render() -> list[str]:
    failures: list[str] = []
    sections = _sections_from_reading(RASHI_LABELS)

    if len(sections) != len(RASHI_LABELS):
        failures.append(
            f"fixture built {len(sections)} section(s), expected "
            f"{len(RASHI_LABELS)} — the reading fixture itself is wrong"
        )
        return failures
    bad_arity = [s for s in sections if len(s) != 4]
    if bad_arity:
        failures.append(
            f"fixture tuples have arity {len(bad_arity[0])}, expected 4 "
            "(glyph, title, teaser, body)"
        )
        return failures

    for name in TEMPLATE_NAMES:
        for lang in ("en", "hi"):
            try:
                html = _render(name, _context(lang=lang, sections=sections))
            except Exception as err:
                failures.append(
                    f"{name} [{lang}]: render raised {type(err).__name__}: {err}"
                )
                continue

            missing_titles = [t for t in RASHI_LABELS if t not in html]
            if missing_titles:
                failures.append(
                    f"{name} [{lang}]: rendered without {len(missing_titles)} rashi "
                    f"title(s) — first missing: {missing_titles[0]!r}. The section "
                    "loop did not run over every rashi."
                )
            missing_glyphs = [
                g for g in {s[0] for s in sections} if g not in html
            ]
            if missing_glyphs:
                failures.append(
                    f"{name} [{lang}]: {len(missing_glyphs)} rashi glyph(s) absent "
                    f"— first missing: {missing_glyphs[0]!r}"
                )
            teaser = sections[0][2]
            if teaser not in html:
                failures.append(
                    f"{name} [{lang}]: the first section's teaser text is absent "
                    f"({teaser!r}) — the digest card rendered no reading"
                )
            print(f"  {name} [{lang}]: {len(html):,} chars, "
                  f"{len(RASHI_LABELS) - len(missing_titles)}/{len(RASHI_LABELS)} "
                  "rashi title(s) present")
    return failures


# --------------------------------------------------------------------------
# Gate 2 - single-rashi render (the per-rashi subscriber)
# --------------------------------------------------------------------------

def gate_2_single_rashi_render() -> list[str]:
    failures: list[str] = []
    label = RASHI_LABELS[7]  # Scorpio / Vrishchika
    sections = _sections_from_reading((label,))
    body_tail = BODY_TAIL_SENTENCE.format(label=label)

    for name in TEMPLATE_NAMES:
        try:
            html = _render(name, _context(lang="en", sections=sections))
        except Exception as err:
            failures.append(
                f"{name} [single]: render raised {type(err).__name__}: {err}"
            )
            continue
        if label not in html:
            failures.append(f"{name} [single]: {label!r} absent from the output")
        if body_tail not in html:
            failures.append(
                f"{name} [single]: the body's closing sentence is absent "
                f"({body_tail!r}) — a single-rashi subscriber is being shown the "
                "teaser instead of the full reading"
            )
        print(f"  {name} [single]: {len(html):,} chars, full body present: "
              f"{body_tail in html}")
    return failures


# --------------------------------------------------------------------------
# Gate 5 - the body's paragraph breaks survive into the email
# --------------------------------------------------------------------------

def gate_5_newlines_survive() -> list[str]:
    """HTML collapses newlines. The reading's paragraphs must not collapse.

    The web card gets this free from Tailwind's `whitespace-pre-line`. Email
    has no stylesheet, so each template must declare it inline — and for three
    weeks neither did, which would have shipped every single-rashi subscriber
    one unbroken wall of text the moment the daily send started working again.

    Asserts two independent things, because either alone is fakeable: the
    newline is still THERE in the output, and the enclosing element actually
    declares a white-space rule that renders it.
    """
    failures: list[str] = []
    label = RASHI_LABELS[7]
    sections = _sections_from_reading((label,))
    body = sections[0][3]
    if "\n\n" not in body:
        return [f"fixture regression: body has no paragraph break ({body!r})"]

    for name in TEMPLATE_NAMES:
        html = _render(name, _context(lang="en", sections=sections))
        has_rule = ("white-space:pre-line" in html) or ("white-space:pre-wrap" in html)
        if not has_rule:
            failures.append(
                f"{name} [single]: no white-space:pre-line/pre-wrap anywhere in the "
                "render — the reading's paragraph breaks will collapse into one block"
            )
        first = TEASER_SENTENCE_1.format(label=label)
        tail = BODY_TAIL_SENTENCE.format(label=label)
        if first in html and tail in html:
            between = html[html.index(first) + len(first):html.index(tail)]
            if "\n" not in between:
                failures.append(
                    f"{name} [single]: the paragraph break between the body's first and "
                    "last sentence is gone from the rendered HTML"
                )
        print(f"  {name} [single]: white-space rule present: {has_rule}")
    return failures


# --------------------------------------------------------------------------
# Gate 3 - empty sections (Rashifal generation failed) still renders
# --------------------------------------------------------------------------

def gate_3_empty_sections_render() -> list[str]:
    failures: list[str] = []
    for name in TEMPLATE_NAMES:
        try:
            html = _render(name, _context(lang="en", sections=[], with_panchang=False))
        except Exception as err:
            failures.append(
                f"{name} [empty]: render raised {type(err).__name__}: {err} — the "
                "generation-failed path must still send the rest of the email"
            )
            continue
        leaked = [t for t in RASHI_LABELS if t in html]
        if leaked:
            failures.append(
                f"{name} [empty]: {leaked[0]!r} appears with no sections supplied"
            )
        print(f"  {name} [empty]: {len(html):,} chars, no rashi content: "
              f"{not leaked}")
    return failures


# --------------------------------------------------------------------------
# Gate 4 - a wrong-arity section list must actually blow up
# --------------------------------------------------------------------------

def gate_4_arity_is_enforced() -> list[str]:
    failures: list[str] = []
    three_tuples = [(s[0], s[1], s[3]) for s in _sections_from_reading(RASHI_LABELS)]

    for name in TEMPLATE_NAMES:
        try:
            _render(name, _context(lang="en", sections=three_tuples))
        except ValueError as err:
            print(f"  {name}: 3-tuples correctly rejected — {err}")
            continue
        except Exception as err:
            print(f"  {name}: 3-tuples rejected with {type(err).__name__}: {err}")
            continue
        failures.append(
            f"{name}: rendered a list of 3-tuples without error. The template is "
            "not unpacking all four fields, so gates 1-3 prove nothing about the "
            "contract main.py actually builds."
        )
    return failures


# --------------------------------------------------------------------------

def main() -> int:
    print("Email template render verification")
    print(f"  templates : {TEMPLATES_DIR.relative_to(REPO_ROOT)}")
    print(f"  checked   : {', '.join(TEMPLATE_NAMES)}")
    print(f"  fixture   : {FIXTURE_DATE.isoformat()} "
          f"({len(festivals.festivals_for_date(FIXTURE_DATE))} festival(s))")
    print()

    gates = [
        ("Gate 1 - digest render, all 12 rashis, en + hi", gate_1_digest_render),
        ("Gate 2 - single-rashi render shows the full body", gate_2_single_rashi_render),
        ("Gate 5 - body paragraph breaks survive the render", gate_5_newlines_survive),
        ("Gate 3 - empty sections (generation failed) still renders",
         gate_3_empty_sections_render),
        ("Gate 4 - wrong tuple arity is actually rejected", gate_4_arity_is_enforced),
    ]

    all_failures: list[str] = []
    results: list[tuple[str, int]] = []
    for title, run in gates:
        print(title)
        try:
            failures = run()
        except Exception as err:  # a gate that crashes is a failing gate
            failures = [f"gate raised {type(err).__name__}: {err}"]
        for line in failures:
            print(f"  FAIL: {line}")
        print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
        print()
        results.append((title, len(failures)))
        all_failures.extend(failures)

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print()
    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s). A template that cannot render "
              "the sections main.py builds means that email never reaches anyone.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
