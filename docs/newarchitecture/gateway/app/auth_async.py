import json
from typing import Optional, Dict, Any
import jwt

from .config import settings
from .auth import Identity, AuthError, _load_jwks_from_file, _select_key_from_jwks
from .jwks_cache import jwks_cache

async def verify_bearer_token_async(authorization: Optional[str]) -> Identity:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("AUTH_INVALID_TOKEN", 401)
    token = authorization.split(" ", 1)[1].strip()

    if settings.jwt_dev_mode:
        if token != "dev":
            raise AuthError("AUTH_INVALID_TOKEN", 401)
        return Identity(user_id="dev-user", tenant_id="dev-tenant", project_id="dev-project", workspace_id="dev-workspace", role="developer")

    if not settings.jwt_jwks_url and not settings.jwt_jwks_file:
        raise AuthError("AUTH_MISCONFIGURED_JWKS", 500)

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "RS256")

        if settings.jwt_jwks_url:
            jwks = await jwks_cache.refresh(force=False)
        else:
            jwks = _load_jwks_from_file(settings.jwt_jwks_file)

        key = _select_key_from_jwks(jwks, kid)
        if not key:
            raise AuthError("AUTH_UNKNOWN_KID", 401)

        signing_key = jwt.algorithms.get_default_algorithms()[key["kty"]].from_jwk(json.dumps(key))

        options = {"verify_aud": bool(settings.jwt_audience)}
        kwargs = {}
        if settings.jwt_audience:
            kwargs["audience"] = settings.jwt_audience
        if settings.jwt_issuer:
            kwargs["issuer"] = settings.jwt_issuer

        claims = jwt.decode(token, signing_key, algorithms=[alg], options=options, **kwargs)

    except AuthError:
        raise
    except Exception:
        raise AuthError("AUTH_INVALID_TOKEN", 401)

    user_id = str(claims.get("sub") or claims.get("user_id") or "")
    tenant_id = str(claims.get("tid") or claims.get("tenant_id") or "")
    project_id = str(claims.get("pid") or claims.get("project_id") or "")
    workspace_id = str(claims.get("wid") or claims.get("workspace_id") or "")
    role = str(claims.get("role") or "developer")

    if not (user_id and tenant_id and project_id and workspace_id):
        raise AuthError("AUTH_MISSING_CLAIMS", 403)

    return Identity(user_id=user_id, tenant_id=tenant_id, project_id=project_id, workspace_id=workspace_id, role=role)
