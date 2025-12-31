"""
Auth 라우터
- GET /api/auth/me
"""

from fastapi import APIRouter, HTTPException, status
from ..models import UserResponse, ErrorResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
    summary="현재 사용자 정보 조회",
    description="현재 인증된 사용자의 정보를 반환합니다.",
)
async def get_current_user():
    """
    현재 인증된 사용자 정보를 반환합니다.
    
    TODO: SSO/LDAP 연동 구현
    - 온프레미스 환경에서는 사내 SSO/LDAP 연동 필요
    - 현재는 더미 데이터 반환
    """
    # TODO: 실제 인증 로직 구현
    # - Request Header에서 토큰 추출
    # - SSO/LDAP 서버에서 사용자 정보 조회
    # - 실패 시 401 Unauthorized 반환
    
    return UserResponse(
        userId="u_demo",
        name="Demo User",
        orgId="org_demo",
    )
