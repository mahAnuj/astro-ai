"""PR merge time (2026-11-19, owner: "track the max time a PR took to merge"):
scripts/issue_flow.py pr_flow and the /admin/ops "PR merge time" panel. Exercised by
tests/test_issue_flow.py. One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("pr merge time: the max reports the fastest PR instead of the slowest",
     "scripts/issue_flow.py",
     '                               "max_h": hs[-1] if hs else None,',
     '                               "max_h": hs[0] if hs else None,',
     "test_pr_flow_reports_median_p90_and_the_max_and_names_the_slowest"),
    ("pr merge time: automated measurement PRs drag the numbers toward zero",
     "scripts/issue_flow.py",
     "        if c is None or m is None or _automated(pr):\n            continue\n        rows.append(",
     "        if c is None or m is None:\n            continue\n        rows.append(",
     "test_pr_flow_excludes_the_automated_measurement_prs"),
    ("pr merge time: open PRs are listed newest first",
     "scripts/issue_flow.py",
     '    open_rows.sort(key=lambda r: -r["age_h"])',
     '    open_rows.sort(key=lambda r: r["age_h"])',
     "test_open_prs_are_listed_oldest_first_with_what_they_wait_on"),
    ("pr merge time: a held PR reads as waiting on gates",
     "scripts/issue_flow.py",
     '    if "needs-human-review" in labels:\n        return "chief (trust boundary)"\n',
     "",
     "test_open_prs_are_listed_oldest_first_with_what_they_wait_on"),
    ("pr merge time: a malformed block 500s the ops page",
     "src/astro_ai/ops_data.py",
     '    except (TypeError, ValueError, KeyError, AttributeError) as exc:\n        log.warning("pr_flow unreadable for the ops panel: %s", exc)\n        return None\n',
     '    finally:\n        pass\n',
     "test_the_ops_page_survives_a_malformed_pr_flow"),
]
