"""#1436: scripts/fetch_gsc.py --by query-page is a query x page map that states its own
partial coverage and refuses to combine with --trend/--band."""

MUTATIONS = [
    ("#1436: --by query-page asks GSC for the query dimension only (no page per row)",
     "scripts/fetch_gsc.py",
     '"dimensions": ["query", "page"],',
     '"dimensions": ["query"],',
     "test_main_posts_one_query_page_body_and_one_total"),
    ("#1436: the query-page export stops saying it is a PARTIAL view",
     "scripts/fetch_gsc.py",
     '    cov_note += (" — PARTIAL VIEW: Google withholds anonymised (low-volume) queries, so "\n'
     '                 "these rows describe only the visible share; a page\'s impressions here are "\n'
     '                 "NOT its page total — use --by page for that")\n',
     '    pass\n',
     "test_main_document_states_its_mode_and_partial_coverage"),
    ("#1436: --by query-page may be combined with --trend or --band",
     "scripts/fetch_gsc.py",
     '    if args.by == "query-page" and (args.trend or args.band):',
     '    if False:',
     "test_flag_combinations_that_make_no_sense_exit_before_any_request"),
    ("#1436: a query-page row drops its page",
     "scripts/fetch_gsc.py",
     '    rows = [{"query": r["keys"][0], "page": r["keys"][1],',
     '    rows = [{"query": r["keys"][0],',
     "test_row_shape_keeps_the_page_and_sorts_by_impressions"),
]
