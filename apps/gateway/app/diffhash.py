import hashlib
import json
from typing import Optional


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def extract_unified_diff_from_json(payload: dict) -> Optional[str]:
    """
    Agent 응답 payload에서 unified diff 텍스트를 추출한다.
    본문 전체를 저장하지 않고 diff 해시만 남기기 위한 보조 함수.
    """
    # common shapes:
    # - {"diff": "..."}
    # - {"changes":[{"diff":"..."}]}
    if "diff" in payload and isinstance(payload.get("diff"), str):
        return payload.get("diff")
    changes = payload.get("changes")
    if isinstance(changes, list):
        for c in changes:
            if isinstance(c, dict) and isinstance(c.get("diff"), str):
                return c.get("diff")
    # try nested: {"result":{"diff":"..."}}
    res = payload.get("result")
    if isinstance(res, dict) and isinstance(res.get("diff"), str):
        return res.get("diff")
    return None


def sha256_json_canonical(obj: object) -> str:
    """
    JSON 객체를 canonical 형태(키 정렬, 최소 구분)로 직렬화 후 sha256.
    changed_files_hash 등 메타데이터 해싱에 사용.
    """
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(raw)

