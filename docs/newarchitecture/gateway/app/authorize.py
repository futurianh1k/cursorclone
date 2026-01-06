from .auth import Identity, AuthError

ROLE_ORDER = {"viewer": 0, "developer": 1, "admin": 2}

def require_role(identity: Identity, min_role: str):
    if ROLE_ORDER.get(identity.role, -1) < ROLE_ORDER.get(min_role, 999):
        raise AuthError("AUTH_FORBIDDEN", 403)

def authorize_path(identity: Identity, path: str):
    if path.startswith("/v1/autocomplete"):
        require_role(identity, "viewer")
    elif path.startswith("/v1/chat"):
        require_role(identity, "viewer")
    elif path.startswith("/v1/agent"):
        require_role(identity, "developer")
    elif path.startswith("/v1/rag/index"):
        require_role(identity, "admin")
    elif path.startswith("/v1/rag/query") or path.startswith("/v1/rag"):
        require_role(identity, "viewer")
    else:
        raise AuthError("NOT_FOUND", 404)
