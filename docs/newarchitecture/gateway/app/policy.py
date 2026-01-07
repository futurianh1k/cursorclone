from .config import settings

def resolve_route(path: str) -> dict | None:
    if path.startswith("/v1/autocomplete"):
        return {"name": "autocomplete", "upstream": settings.upstream_tabby}
    if path.startswith("/v1/agent"):
        return {"name": "agent", "upstream": settings.upstream_agent}
    if path.startswith("/v1/chat"):
        return {"name": "chat", "upstream": settings.upstream_chat}
    if path.startswith("/v1/rag"):
        return {"name": "rag", "upstream": settings.upstream_rag}
    return None
