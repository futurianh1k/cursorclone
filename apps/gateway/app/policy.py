from .config import settings


def resolve_route(path: str) -> dict | None:
    # Tabby (autocomplete)
    # - Tabby 서버/클라이언트는 /v1/completions, /v1/health 등을 사용한다.
    # - PRD의 "Tabby 연동"을 충족하기 위해 gateway에서 해당 경로를 upstream_tabby로 라우팅한다.
    if path.startswith("/v1/autocomplete") or path.startswith("/v1/completions") or path.startswith("/v1/health"):
        return {"name": "autocomplete", "upstream": settings.upstream_tabby}
    if path.startswith("/v1/agent"):
        return {"name": "agent", "upstream": settings.upstream_agent}
    if path.startswith("/v1/chat"):
        return {"name": "chat", "upstream": settings.upstream_chat}
    if path.startswith("/v1/rag"):
        return {"name": "rag", "upstream": settings.upstream_rag}
    return None

