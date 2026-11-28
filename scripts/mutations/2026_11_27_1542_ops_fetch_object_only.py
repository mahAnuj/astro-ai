"""#1542 (2026-11-27): a non-object top-level JSON (`[1]`, `"x"`, `5`) in any measurements file
500ed /admin/ops on every tab. `_fetch` now returns a JSON object or None, rejecting at both the
disk and the HTTPS site. Exercised by tests/test_ops_nonobject_json.py.
One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("ops-fetch-object: the disk read no longer checks the top-level type",
     "src/astro_ai/ops_data.py",
     "data = _as_object(name, json.loads((local / name).read_text()), \"disk\")",
     "data = json.loads((local / name).read_text())",
     "test_a_bad_disk_file_falls_through_to_https"),
    ("ops-fetch-object: the HTTPS read no longer checks the top-level type",
     "src/astro_ai/ops_data.py",
     "data = _as_object(name, json.loads(resp.read().decode(\"utf-8\")), \"HTTPS\")",
     "data = json.loads(resp.read().decode(\"utf-8\"))",
     "test_a_non_object_https_body_is_none"),
    ("ops-fetch-object: any non-null JSON counts as an object",
     "src/astro_ai/ops_data.py",
     "    if isinstance(data, dict):\n        return data\n    log.warning(\"ops_data: %s from %s is a %s",
     "    if data is not None:\n        return data\n    log.warning(\"ops_data: %s from %s is a %s",
     "test_one_file_a_list_does_not_500_any_tab"),
]
