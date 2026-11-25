"""#1387: a `mergeable-but-open` starved behind the owner's agent-merge fix is
reclassified, not obliged. Exercised by tests/test_stall_merge_starved.py. One area
file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("merge-starved: any author's PR counts as the owner's fix (forged suppression)",
     "scripts/detect_stalls.py",
     '        if str(author.get("login", "") if isinstance(author, dict) else "").casefold() != owner:\n',
     '        if False:\n',
     "test_lookup_forged_author_is_refused"),
    ("merge-starved: the fix PR need not carry qa-pass (unjudged PR suppresses a wake)",
     "scripts/detect_stalls.py",
     '        if "qa-pass" not in {l.get("name") for l in (p.get("labels") or []) if isinstance(l, dict)}:\n',
     '        if False:\n',
     "test_lookup_needs_qa_pass_and_the_merge_workflow"),
    ("merge-starved: an unreadable lookup answers with a PR number instead of None (fails closed to silence)",
     "scripts/detect_stalls.py",
     '    except Exception:  # noqa: BLE001 - any failure is "could not tell", never a crash\n        return None\n',
     '    except Exception:  # noqa: BLE001 - any failure is "could not tell", never a crash\n        return 1\n',
     "test_lookup_cannot_determine_fails_open"),
    ("merge-starved: the new kind joins the ruling set (chief is woken again)",
     "scripts/detect_stalls.py",
     'OBLIGED_RULING_KINDS = frozenset({"boundary-hold-clearable"})',
     'OBLIGED_RULING_KINDS = frozenset({"boundary-hold-clearable", "merge-starved-owner-blocked"})',
     "test_trusted_fix_open_reclassifies_and_is_not_obliged"),
    ("merge-starved: the new kind joins the push set",
     "scripts/detect_stalls.py",
     '"draft-held-by-qa-fail", "pr-conflicting"})',
     '"draft-held-by-qa-fail", "pr-conflicting", "merge-starved-owner-blocked"})',
     "test_new_kind_is_in_neither_obliged_set"),
]
