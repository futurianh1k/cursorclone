import pytest


def test_gateway_jwks_shape():
    """
    newarchitecture v0.3:
    - AI Gateway는 JWKS로 JWT를 검증한다.
    - API는 /api/auth/jwks로 JWKS를 제공한다.

    여기서는 서비스 레벨(jwks dict)을 검증한다. (DB/네트워크 의존성 없음)
    """
    from src.services.auth_service import jwt_auth_service

    jwks = jwt_auth_service.get_gateway_jwks()
    assert isinstance(jwks, dict)
    assert "keys" in jwks
    assert isinstance(jwks["keys"], list)
    assert len(jwks["keys"]) >= 1

    key = jwks["keys"][0]
    assert key.get("kty") == "RSA"
    assert key.get("use") == "sig"
    assert key.get("kid")
    assert key.get("n")
    assert key.get("e")


def test_gateway_token_has_required_claims():
    """
    Gateway 토큰은 tid/pid/wid/role 클레임을 포함해야 한다.
    """
    from jose import jwt as jose_jwt
    from src.services.auth_service import jwt_auth_service

    token = jwt_auth_service.create_gateway_workspace_token(
        user_id="u_test",
        tenant_id="org_default",
        project_id="prj_test",
        workspace_id="ws_test",
        role="developer",
    )
    claims = jose_jwt.get_unverified_claims(token)
    assert claims["sub"] == "u_test"
    assert claims["tid"] == "org_default"
    assert claims["pid"] == "prj_test"
    assert claims["wid"] == "ws_test"
    assert claims["role"] == "developer"

