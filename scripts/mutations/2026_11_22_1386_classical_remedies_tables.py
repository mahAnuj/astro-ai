"""#1386: /learn/debilitated-sun-career stops calling one modern textbook's remedy tables "classical".

Each row restores the pre-fix wording verbatim and names the scan test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_T = "src/astro_ai/templates/learn/debilitated-sun-career.html"
_R = "src/astro_ai/learn_registry.py"
_SCAN = "test_no_source_file_calls_a_remedy_table_classical"

MUTATIONS = [
    ("#1386: debilitated-sun remedy legend calls the textbook tables 'the classical remedies tables we hold' again",
     _T,
     "follow the remedies reference we hold, which rests on one modern textbook's planet-by-planet remedy tables rather than a classical ranking;",
     "appear in the classical remedies tables we hold;",
     _SCAN),
    ("#1386: debilitated-sun 'How to strengthen' FAQ calls the textbook tables 'the classical remedies tables we hold' again",
     _R,
     "Sourced in one modern textbook's planet-by-planet remedy tables, as our remedies reference records them:",
     "Sourced in the classical remedies tables we hold:",
     _SCAN),
]
