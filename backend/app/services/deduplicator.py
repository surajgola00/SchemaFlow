# Deduplicator logic mock
def deduplicate_records(records: list) -> list:
    seen = set()
    for rec in records:
        h = str(rec.get("data", ""))
        if h in seen:
            rec["is_duplicate"] = True
        else:
            rec["is_duplicate"] = False
            seen.add(h)
    return records
