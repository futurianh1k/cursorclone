import hashlib

def sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()

def extract_unified_diff_from_json(payload: dict) -> str | None:
    for key in ("diff", "unified_diff", "patch", "unifiedDiff"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None
