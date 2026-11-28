"""The request-indexing list asks for a not-indexed next-year /learn page first (#1571)."""

_F = "scripts/fetch_index_status.py"
_T = "test_request_indexing_asks_for_a_not_indexed_next_year_learn_page_before_stale_pages"

MUTATIONS = [
    ("index status: the year-successor rule is off",
     _F,
     '.year + 1\n',
     '.year - 1\n',
     _T),
    ("index status: ask-first pages are not lifted above stale ones",
     _F,
     'for r, why, _ in first + rest]',
     'for r, why, _ in rest + first]',
     _T),
    ("index status: ask-first pages are not capped to half the list",
     _F,
     '[:limit // 2]',
     '[:limit]',
     _T),
    ("index status: a /panchang date page counts as a successor",
     _F,
     'parts[0] == "learn" and re.search(rf',
     're.search(rf',
     _T),
    ("index status: the year match has no digit boundary",
     _F,
     '(?<!\\d){year}(?!\\d)',
     '{year}',
     _T),
    ("index status: a stale-only page is asked for first",
     _F,
     '            reasons.append(f"not indexed: {r.get(\'coverageState\') or r.get(\'verdict\')}")\n'
     '            if _names_year(r["url"], year):\n'
     '                reasons.append(f"names {year}: ask before it has impressions")\n'
     '                ask_first = True\n',
     '            reasons.append(f"not indexed: {r.get(\'coverageState\') or r.get(\'verdict\')}")\n'
     '        if _names_year(r["url"], year):\n'
     '            reasons.append(f"names {year}: ask before it has impressions")\n'
     '            ask_first = True\n',
     _T),
]
