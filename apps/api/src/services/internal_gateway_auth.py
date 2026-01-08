"""
Gateway -> API 내부 호출 인증

원칙:
- Gateway는 workspace 사용자 토큰(Authorization)을 upstream(API)에 전달하지 않는다.
- 대신 내부 서비스 토큰(X-Internal-Token)을 사용해 Gateway 발 호출임을 식별한다.
"""

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, status


@dataclass
class GatewayRequestIdentity:
    user_id: str
    tenant_id: str
    project_id: str
    workspace_id: str


def require_gateway_internal(
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
    x_workspace_id: Optional[str] = Header(default=None, alias="X-Workspace-Id"),
) -> GatewayRequestIdentity:
    expected = os.getenv("GATEWAY_INTERNAL_TOKEN", "").strip()
    if not expected:
        # PoC 편의: 토큰 미설정이면 실패(운영에서는 반드시 설정 권장)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal token not configured")

    if not x_internal_token or x_internal_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized (internal)")

    if not (x_user_id and x_tenant_id and x_project_id and x_workspace_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing identity headers")

    return GatewayRequestIdentity(
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        project_id=x_project_id,
        workspace_id=x_workspace_id,
    )

