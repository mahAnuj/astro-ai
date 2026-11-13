"""#968: natal.txt must not teach by an example its own output rules ban.

The FRAME DISAMBIGUATION bullet once told the model to write "counted from your
Moon, Mars falls in the 4th house", while STRICT OUTPUT RULES forbid naming Mars
and natal house numbers. A model that followed the example broke both bans, and
#966's compliance rate on Manglik charts measured a contradiction, not the model.

Gate 5 of scripts/verify_natal_prompt.py carries the check. The test below runs
that gate over the real prompt (the target of the mutation row in
scripts/mutations/2026_11_13_968_natal_frame_example.py) and over a copy with the
defect put back, so a gate that cannot go red fails here.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "verify_natal_prompt", ROOT / "scripts" / "verify_natal_prompt.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_natal_prompt"] = gate
_spec.loader.exec_module(gate)

PROMPT = ROOT / "src" / "astro_ai" / "prompts" / "natal.txt"
DEFECT = 'counted from your Moon, Mars falls in the 4th house, which is what marks Manglik in your chart'


def test_the_shipped_natal_prompt_has_no_example_placing_a_planet_in_a_numbered_house(capsys):
    text = PROMPT.read_text(encoding="utf-8")
    assert gate.gate_5_no_retired_claims(text) is True, capsys.readouterr().out


def test_gate_5_goes_red_when_the_frame_example_returns(capsys):
    text = PROMPT.read_text(encoding="utf-8") + "\n" + DEFECT + "\n"
    assert gate.gate_5_no_retired_claims(text) is False
    assert "#968" in capsys.readouterr().out


def test_frame_bullet_keeps_the_three_frame_words_and_names_no_mars_example():
    line = next(l for l in PROMPT.read_text(encoding="utf-8").splitlines()
                if "FRAME DISAMBIGUATION" in l)
    for word in ("Lagna", "Moon", "Venus"):
        assert word in line
    assert not re.search(r"\b\d+(?:st|nd|rd|th)\s+house\b", line)
    # Mars may be named only to forbid it.
    assert all("never name Mars" in line for _ in re.findall(r"\bMars\b", line))
