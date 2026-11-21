"""Why a muhurat date rated as it did: the factor and exclusion registry (#1017 R3).

Pure functions over a `MuhuratCandidate`; no I/O, no LLM, no request field. Two lists per row:
what SCORED (tithi, star, weekday, boosters) and what was CHECKED AND NOT EXCLUDED (the hard
exclusions the event actually runs). Every factor carries one of three statuses, so none
reaches the page unlabelled:

  sourced          a rule a held book states (knowledge file + heading name it)
  contested        the held books differ, or support it only in part (knowledge file + heading)
  site_convention  this finder's own rule, said so in a sentence (a heading only if one is nearby)

The statuses, headings and sentences are the astro-auditor's ruling for #1017 R3 (2026-11-21),
transcribed, not chosen here. `heading` is a line PREFIX in `knowledge/<file>`, including the
`#` marks, so tests/test_muhurat_factor_registry.py can check it still exists. Where a status
or sentence below goes beyond the ruling's own words it says "worded here" in a comment.

The soft factors are RECOMPUTED from `EVENT_RULES` and the candidate's own tithi, star and
weekday, mirroring `muhurat.score_event`'s branches; tests/test_muhurat_factor_parity.py pins
the two together. The scorer emits no structured key for them, and editing it conflicts with
the open top-pick change, so the structured-keys refactor is a follow-up.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from astro_ai.muhurat import AUSPICIOUS_RATINGS, EVENT_RULES, _HARD_AVOID_WEEKDAYS

STATUSES = ("sourced", "contested", "site_convention")

_VR = "vedic_reference.md"
_GR = "grahas.md"

# Where each event's own rules live in knowledge/. A sourced or contested entry with no heading
# of its own points here, so the five headings are written once.
_EVENT_HEADING: dict[str, tuple[str, str]] = {
    "vivah": (_VR, "### 29.9 "),
    "griha_pravesh": (_VR, "#### Griha Pravesh"),
    "vidyarambh": (_VR, "#### Vidyarambh"),
    "namkaran": (_VR, "#### Namkaran"),
    "business": (_VR, "#### Business start"),
}

CLEARED_HEADING = "Checked and not excluded at local noon"
SCORED_HEADING = "What counted for this date"
NO_POINTS = "No tithi, star or weekday point scored for this date"
NOON_NOTE = ("Checked at local noon on this date; the Moon's star, the tithi and the yoga can "
             "change later in the day, so confirm the exact hour with your priest.")
# The auditor's wording, verbatim. The code's own "universally auspicious" is never echoed.
ABUJHA_NOTE = ("Listed as an Abujha date, a regional almanac custom this finder includes; no "
               "book it holds names it. The usual exclusion checks were not run for this date, "
               "so confirm the tithi, star and Panchak with your priest or panchang.")


def _r(status: str, sentence: str, file: str | None = None, heading: str | None = None) -> dict:
    return {"status": status, "file": file, "heading": heading, "sentence": sentence}


def _vr(status: str, sentence: str, heading: str | None = None) -> dict:
    return _r(status, sentence, _VR if heading else None, heading)


def _gr(status: str, sentence: str, heading: str) -> dict:
    return _r(status, sentence, _GR, heading)


S, C, SC = "sourced", "contested", "site_convention"
_H97, _H914, _H913, _H96 = "### 29.9 ", "### 29.14 ", "### 29.13 ", "### 29.6 "
_BIZ = "#### Business start"
_NAK = "#### Namkaran"

_BIZ_LIST = "site convention, not sourced: this finder's own {what} list for a new venture."


def _combust(planet: str, orb: str) -> str:
    return (f"{planet} within {orb} of the Sun counts as combust (orb from the Muhurtha "
            "tradition). Treating that as a veto for {event} is this finder's own convention.")


# REGISTRY[key] = {"label", "default": R, "events": {event: R}, "when": {event: {value: R}}}.
# Resolution order (resolve): when[event][value] -> events[event] -> default.
REGISTRY: dict[str, dict[str, Any]] = {
    # ─── soft (scored) factors ──────────────────────────────────────
    "good_tithi": {
        "label": "Good tithi",
        "default": _r(S, "This tithi is one the Muhurtha tradition and the Vedic tables list as "
                         "favourable for {event}."),
        "events": {
            "business": _vr(SC, _BIZ_LIST.format(what="tithi"), _BIZ),
        },
        "when": {
            # Worded here from the ruling's "rests only on Rao's paksha-less row"; status
            # contested because one table supports it and the other source names the bright half.
            "vivah": {"@Krishna": _vr(C, "In the dark half this credit rests on one table, which "
                                         "lists the tithi without naming a half; the Muhurtha "
                                         "tradition's best list is for the bright half.", _H97)},
            # Ruling: "Vd Dwadashi is contested (L2960)"; sentence worded here from that row.
            "vidyarambh": {"Dwadashi": _vr(C, "The Vedic tables list this tithi for learning the "
                                              "alphabet, but the Muhurtha tradition's general list "
                                              "rejects it, so the two differ.", "#### Vidyarambh")},
        },
    },
    "good_nakshatra": {
        "label": "Good star",
        "default": _r(S, "This star is on the favourable list in B.V. Raman's Muhurtha and the "
                         "Vedic tables for {event}."),
        "events": {
            "vivah": _vr(S, "This star is on the favourable list in B.V. Raman's Muhurtha and the "
                            "Vedic tables for {event}.", _H914),
            "business": _vr(SC, _BIZ_LIST.format(what="star"), _BIZ),
        },
        "when": {
            "vidyarambh": {n: _vr(C, "This star is on a favourable list for {event}, but listed "
                                     "by one tradition, not both.", "#### Vidyarambh")
                           for n in ("Rohini", "Revati", "Anuradha")},
        },
    },
    "good_weekday": {
        "label": "Good weekday",
        "default": _r(S, "This weekday is favoured for {event} in the Muhurtha tradition."),
        "events": {
            "vivah": _vr(S, "This weekday is favoured for {event} in the Muhurtha tradition.", _H97),
            "namkaran": _vr(C, "Traditions differ on weekdays.", _NAK),
            "business": _vr(SC, "site convention, not sourced: this finder's own weekday list for "
                                "a new venture; the books we hold give Sunday no support and call "
                                "Friday unpropitious for selling.", _BIZ),
        },
    },
    "peak_day": {
        "label": "Peak day for this event",
        "default": _vr(SC, "This finder's own bonus: Budh governs trade; no held text ranks "
                           "Wednesday for a business start.", _BIZ),
        "events": {
            "vidyarambh": _vr(SC, "This finder's own bonus for Guru's day; the Muhurtha tradition "
                                  "names Wednesday morning as best for beginning study.",
                              "#### Vidyarambh"),
        },
    },
    "avoid_weekday_soft": {
        "label": "Weekday counted against",
        "default": _vr(C, "Traditions differ on Saturday: one passage says avoid it for all "
                          "auspicious work, another calls it middling, so this finder deducts a "
                          "point instead of excluding it.", _H97),
        "events": {
            "vidyarambh": _vr(S, "The Muhurtha tradition says avoid; this finder deducts a "
                                 "point.", "#### Vidyarambh"),
            # Worded here: the ruling rules the penalty a site convention for business without
            # giving a sentence; the facts are knowledge/ Business start (Saturday "passable",
            # "middling").
            "business": _vr(SC, "This finder deducts a point for Saturday; the books we hold call "
                                "it passable for buying and middling for selling, and give no "
                                "rule for a business start.", _BIZ),
        },
    },
    # ─── boosters ───────────────────────────────────────────────────
    "amrit_siddhi": {
        "label": "Amrit Siddhi present",
        "default": _vr(C, "A weekday-and-star pairing. The Muhurtha tradition has a similar "
                          "Siddha-yoga list matching six of seven weekdays here; Monday differs. "
                          "Whether and how this finder lifts a grade for it is its own "
                          "convention.", _H97),
    },
    "sarvartha_siddhi": {
        "label": "Sarvartha Siddhi present",
        "default": _vr(SC, "This finder's own table. The Muhurtha tradition's Siddha lists are "
                           "similar, not the same, and add a tithi condition not applied here.",
                       _H97),
    },
    "ravi_yoga": {
        "label": "Ravi Yoga present",
        "default": _vr(SC, "Sunday with a listed star: an almanac convention, not stated in the "
                           "books this site holds.", _H914),
    },
    "abujha_muhurat": {
        "label": "Abujha date",
        "default": _vr(SC, ABUJHA_NOTE, _H914),
    },
    # ─── hard exclusions, in the scorer's own order ─────────────────
    "adhik_maas": {
        "label": "Not in Adhik Maas",
        "default": _vr(SC, "Adhik Maas (the extra month) is avoided for new beginnings by almanac "
                           "custom; the books this site holds describe the month but give no "
                           "muhurta rule on it.", _H96),
    },
    "eclipse": {
        "label": "No eclipse within a day",
        "default": _vr(SC, "Eclipse days and the day on each side are avoided by almanac custom; "
                           "this finder's own window.", _H914),
    },
    "nitya_yoga_block": {
        "label": "Not under a blocking yoga",
        "default": _vr(S, "Atiganda, Shula, Ganda, Vyatipata and Vaidhriti are the five yogas the "
                          "Muhurtha tradition says harm what is begun under them.", _H97),
    },
    "panchak": {
        "label": "Moon not in Panchak",
        "default": _vr(S, "Moon from the third quarter of Dhanishta to the end of Revati "
                          "(Panchak): held unsuitable for any auspicious work.", _H97),
    },
    "chaturmas": {
        "label": "Not in Chaturmas",
        "default": _vr(SC, "Chaturmas (Devshayani to Devuthani) is avoided by custom; the books we "
                           "hold give month rules per event and do not match this window — this "
                           "finder's own convention.", _H914),
        "events": {
            "vivah": _vr(C, "Chaturmas (Devshayani to Devuthani) is avoided by custom; the books "
                            "we hold give month rules per event and do not match this window — "
                            "this finder's own convention.", _H914),
        },
    },
    "kharmas": {
        "label": "Sun not in Dhanu or Meena",
        "default": _vr(SC, "Sun in Dhanu or Meena is avoided by custom; not a rule from the books "
                           "this site holds.", _H914),
    },
    "dagdha": {
        "label": "Not a Dagdha tithi-weekday pair",
        "default": _vr(SC, "Burnt tithi–weekday pairs are an almanac convention; no held text "
                           "states them.", _H914),
    },
    "jupiter_combust": {
        "label": "Guru not combust",
        "default": _gr(SC, _combust("Guru", "11°"), "### 12.5 "),
        "events": {
            "griha_pravesh": _vr(C, _combust("Guru", "11°") + " The tradition asks for strong "
                                    "Guru and Shukra at house entry.", _H913),
            "vidyarambh": _vr(SC, _combust("Guru", "11°"), _H913),
        },
    },
    "venus_combust": {
        "label": "Shukra not combust",
        "default": _gr(SC, _combust("Shukra", "10° (9° when retrograde)"), "### 12.5 "),
    },
    "mercury_combust": {
        "label": "Budh not combust",
        "default": _gr(SC, "Budh combustion blocks every weekday for a business start. This "
                           "finder's own extension; the tradition rejects only Wednesday, for the "
                           "sacred-thread ceremony.", "### 12.5 "),
    },
    "avoid_nakshatra": {
        "label": "Not an avoided star",
        "default": _r(S, "Stars outside the traditional list are rejected for {event}."),
        "events": {
            "vivah": _vr(C, "The fierce and sharp stars are avoided (an almanac tradition); "
                            "Krittika and Vishakha are this finder's reading.", "### 27.4 "),
            "namkaran": _vr(C, "Harsh stars avoided for infants: this finder's reading.", _NAK),
            "business": _vr(SC, _BIZ_LIST.format(what="avoided-star"), _BIZ),
        },
    },
    # Wording from muhurat._VIVAH_FIRST_PADA_REASON, which the ruling says is already correct.
    "avoid_nakshatra_pada": {
        "label": "Moon not in the first quarter of Makha or Moola",
        "default": _vr(S, "B.V. Raman's Muhurtha rejects the first quarter of Makha and Moola for "
                          "a wedding; the rest of those stars stays good.", _H914),
    },
    # Each event's note names the tithi the ruling marks contested or unsourced; worded here.
    "avoid_tithi": {
        "label": "Not an avoided tithi",
        "default": _r(S, "These tithis are rejected for auspicious work in the Muhurtha "
                         "tradition."),
        "events": {
            "vivah": _vr(S, "These tithis are rejected for auspicious work in the Muhurtha "
                            "tradition. Purnima is the exception: the books differ on it.", _H97),
            "griha_pravesh": _vr(S, "These tithis are rejected for auspicious work in the "
                                    "Muhurtha tradition. Navami is this finder's own addition.",
                                 "#### Griha Pravesh"),
            "namkaran": _vr(S, "These tithis are rejected for auspicious work in the Muhurtha "
                               "tradition. Navami is the exception: the books differ on it.",
                            _NAK),
            "business": _vr(S, "These tithis are rejected for auspicious work in the Muhurtha "
                               "tradition. Navami is this finder's own addition.", _H97),
        },
    },
    "avoid_krishna_tithi": {
        "label": "Not a dark-half Ekadashi to Amavasya",
        "default": _vr(S, "B.V. Raman's Muhurtha rejects the dark-half 11th through New Moon for "
                          "a wedding; the bright-half tithis are not excluded.", _H97),
    },
    # HARD Tuesday. The scorer's flag "avoid_weekday" also marks the soft Saturday and Sunday
    # penalty; registry_key_for_flag tells them apart.
    "avoid_weekday": {
        "label": "Not a Tuesday",
        "default": _vr(S, "Tuesday is rejected for auspicious work in the Muhurtha tradition.",
                       _H97),
        "events": {
            "namkaran": _vr(S, "Tuesday is rejected for auspicious work in the Muhurtha "
                               "tradition. It allows a Tuesday on the child's 10th, 12th or 16th "
                               "day after birth; this finder has no birth date, so it cannot "
                               "apply that exception.", _H97),
        },
    },
    # One note, not a per-factor weight claim (ruling, "Aggregate scoring weights").
    "soft_scoring_weights": {
        "label": "How the grade is counted",
        "default": _vr(SC, "The grade is a point count this finder chose; the books list "
                           "favourable and unfavourable factors but give no weights. Tithi and "
                           "star count 2 each, weekday and peak day 1 each, a deducted weekday "
                           "minus 1; 5 or more is excellent, 4 good, 3 acceptable.", _H97),
    },
}

# Scored keys in display order, and the hard keys in the scorer's order (ruling #10 to #24).
_SOFT_ORDER = ("good_tithi", "good_nakshatra", "good_weekday", "peak_day", "avoid_weekday_soft")
_BOOSTERS = (("Amrit Siddhi", "amrit_siddhi"), ("Sarvartha Siddhi", "sarvartha_siddhi"),
             ("Ravi Yoga", "ravi_yoga"))
_HARD_ORDER = ("adhik_maas", "eclipse", "nitya_yoga_block", "panchak", "chaturmas", "kharmas",
               "dagdha", "jupiter_combust", "venus_combust", "mercury_combust",
               "avoid_nakshatra", "avoid_nakshatra_pada", "avoid_tithi", "avoid_krishna_tithi",
               "avoid_weekday")
_QUAL_LABEL = {"@Krishna": "dark half"}


def resolve(key: str, event: str, value: str | None = None) -> tuple[str, str | None, str | None, str]:
    """(status, file, heading, sentence) for a factor under an event. Raises KeyError on an
    unknown key or event, so a typo is found by a test rather than rendered unlabelled."""
    entry = REGISTRY[key]
    label = EVENT_RULES[event]["label"]
    r = entry["when"].get(event, {}).get(value) if value and "when" in entry else None
    r = r or entry.get("events", {}).get(event) or entry["default"]
    file, heading = r["file"], r["heading"]
    if heading is None and r["status"] != "site_convention":
        file, heading = _EVENT_HEADING[event]
    return r["status"], file, heading, r["sentence"].format(event=label)


def registry_key_for_flag(flag: str, weekday: str) -> str:
    """The registry key for a flag `muhurat.score_event` emits. `avoid_weekday` is two rules:
    the hard Tuesday exclusion and the soft Saturday/Sunday penalty (they never share a row)."""
    if flag == "avoid_weekday" and weekday not in _HARD_AVOID_WEEKDAYS:
        return "avoid_weekday_soft"
    return flag


@dataclass(frozen=True)
class Item:
    key: str
    text: str          # "Good tithi: Dwitiya"
    status: str
    qual: str = ""     # the `when` qualifier that matched, "" if none
    against: bool = False


@dataclass(frozen=True)
class Explanation:
    scored: tuple[Item, ...] = ()
    cleared: tuple[Item, ...] = ()
    note: str = ""     # a row-level sentence (Abujha); "" otherwise
    scored_heading: str = SCORED_HEADING
    cleared_heading: str = CLEARED_HEADING
    no_points: str = NO_POINTS

    def __bool__(self) -> bool:
        return bool(self.scored or self.cleared or self.note)


@dataclass(frozen=True)
class LegendEntry:
    key: str
    label: str
    status: str
    sentence: str


@dataclass(frozen=True)
class Legend:
    entries: tuple[LegendEntry, ...] = ()
    noon: str = ""     # NOON_NOTE when any row shows a cleared list

    def __bool__(self) -> bool:
        return bool(self.entries or self.noon)


def _qual(key: str, event: str, *values: str) -> str:
    when = REGISTRY[key].get("when", {}).get(event, {})
    return next((v for v in values if v in when), "")


def _item(key: str, event: str, value: str = "", qual: str = "", against: bool = False) -> Item:
    label = REGISTRY[key]["label"]
    return Item(key, f"{label}: {value}" if value else label,
                resolve(key, event, qual or None)[0], qual, against)


def _soft_items(event: str, rules: dict, tithi: str, paksha: str, nakshatra: str,
                weekday: str) -> list[Item]:
    """The soft factors `score_event` counts, branch for branch."""
    out: list[Item] = []
    if tithi in rules["good_tithis"]:
        out.append(_item("good_tithi", event, tithi,
                         _qual("good_tithi", event, "@Krishna" if paksha == "Krishna" else "",
                               tithi)))
    if nakshatra in rules["good_nakshatras"]:
        out.append(_item("good_nakshatra", event, nakshatra,
                         _qual("good_nakshatra", event, nakshatra)))
    if weekday in rules["good_days"]:
        out.append(_item("good_weekday", event, weekday))
        if rules.get("peak_day") == weekday:
            out.append(_item("peak_day", event))
    elif weekday in rules["avoid_days"]:
        out.append(_item("avoid_weekday_soft", event, weekday, against=True))
    return out


def _applied_hard(rules: dict, nakshatra: str) -> list[str]:
    """The hard exclusions this event runs, derived from its `check_*` flags and `avoid_*` keys
    (never a static list), in the scorer's order. Nakshatra-based checks need a nakshatra:
    `find_candidates` degrades to "" and pada 0 together, so they are then not run."""
    have = {
        "adhik_maas": True, "eclipse": True, "nitya_yoga_block": True,
        "panchak": rules["check_panchak"] and bool(nakshatra),
        "chaturmas": rules["check_chaturmas"],
        "kharmas": rules.get("check_kharmas"),
        "dagdha": rules.get("check_dagdha"),
        "jupiter_combust": rules["check_jupiter_combust"],
        "venus_combust": rules["check_venus_combust"],
        "mercury_combust": rules["check_mercury_combust"],
        "avoid_nakshatra": bool(nakshatra),
        "avoid_nakshatra_pada": bool(rules.get("avoid_nakshatra_padas")) and bool(nakshatra),
        "avoid_tithi": True,
        "avoid_krishna_tithi": bool(rules.get("avoid_krishna_tithis")),
        "avoid_weekday": True,
    }
    return [k for k in _HARD_ORDER if have[k]]


def explain(candidate, event_type: str) -> Explanation:
    """What scored and what was checked for one finder row. Empty for any row the page does not
    call auspicious: an 'avoid' row has its own reason, and a 'caution' row is labelled "use with
    caution", where a list of cleared checks would read as an endorsement."""
    rules = EVENT_RULES.get(event_type)
    if rules is None or candidate.rating not in AUSPICIOUS_RATINGS:
        return Explanation()
    if "abujha_muhurat" in candidate.flags:
        # The Abujha branch of find_candidates skips every hard exclusion and every booster, so
        # nothing was cleared and nothing scored. Keyed on the flag: when that branch changes
        # (#1346) the cleared list follows what ran. tests pin this against today's branch.
        return Explanation(scored=(_item("abujha_muhurat", event_type),), cleared=(),
                           note=resolve("abujha_muhurat", event_type)[3])
    scored = _soft_items(event_type, rules, candidate.tithi, candidate.tithi_paksha,
                         candidate.nakshatra, candidate.weekday)
    for prefix, key in _BOOSTERS:
        if any(b.startswith(prefix) for b in candidate.boosters):
            scored.append(_item(key, event_type))
    cleared = [_item(k, event_type) for k in _applied_hard(rules, candidate.nakshatra)]
    return Explanation(scored=tuple(scored), cleared=tuple(cleared))


def legend(candidates, event_type: str) -> Legend:
    """Each distinct factor sentence the page's explained rows use, once, plus the noon note when
    a cleared list is shown. One legend per page keeps the per-row HTML small."""
    used: set[tuple[str, str]] = set()
    cleared_shown = scored_shown = False
    for c in candidates:
        ex = explain(c, event_type)
        used.update((i.key, i.qual) for i in ex.scored + ex.cleared)
        cleared_shown = cleared_shown or bool(ex.cleared)
        scored_shown = scored_shown or any(i.key != "abujha_muhurat" for i in ex.scored)
    if scored_shown:
        used.add(("soft_scoring_weights", ""))
    entries = []
    for key in REGISTRY:
        for qual in sorted(q for k, q in used if k == key):
            status, _f, _h, sentence = resolve(key, event_type, qual or None)
            label = REGISTRY[key]["label"]
            if qual:
                label = f"{label} ({_QUAL_LABEL.get(qual, qual)})"
            entries.append(LegendEntry(key, label, status, sentence))
    return Legend(tuple(entries), NOON_NOTE if cleared_shown else "")
