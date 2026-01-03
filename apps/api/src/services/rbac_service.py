"""
RBAC (Role-Based Access Control) 서비스
역할 기반 접근 제어 구현

역할 계층:
- admin: 모든 권한
- manager: 팀 관리, 워크스페이스 관리
- developer: 워크스페이스 사용, AI 기능
- viewer: 읽기 전용

참조:
- OWASP RBAC: https://owasp.org/www-community/Access_Control_Cheat_Sheet
"""

from enum import Enum
from typing import List, Optional, Set, Callable
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from ..db import get_db, UserModel, UserSessionModel
from .auth_service import jwt_auth_service

logger = logging.getLogger(__name__)
security = HTTPBearer()


class Role(str, Enum):
    """사용자 역할"""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class Permission(str, Enum):
    """권한 목록"""
    # 관리자 권한
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    SERVER_MANAGE = "server:manage"
    USER_MANAGE = "user:manage"
    
    # 워크스페이스 권한
    WORKSPACE_CREATE = "workspace:create"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_SHARE = "workspace:share"
    
    # 파일 권한
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_UPLOAD = "file:upload"
    FILE_DELETE = "file:delete"
    
    # AI 권한
    AI_CHAT = "ai:chat"
    AI_EXPLAIN = "ai:explain"
    AI_REWRITE = "ai:rewrite"
    AI_AGENT = "ai:agent"
    
    # IDE 권한
    IDE_ACCESS = "ide:access"
    IDE_TERMINAL = "ide:terminal"
    IDE_DEBUG = "ide:debug"


# 역할별 권한 매핑
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # 모든 권한
    Role.MANAGER: {
        # 관리자 읽기
        Permission.ADMIN_READ,
        # 워크스페이스 전체
        Permission.WORKSPACE_CREATE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_SHARE,
        # 파일 전체
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.FILE_UPLOAD,
        Permission.FILE_DELETE,
        # AI 전체
        Permission.AI_CHAT,
        Permission.AI_EXPLAIN,
        Permission.AI_REWRITE,
        Permission.AI_AGENT,
        # IDE 전체
        Permission.IDE_ACCESS,
        Permission.IDE_TERMINAL,
        Permission.IDE_DEBUG,
    },
    Role.DEVELOPER: {
        # 워크스페이스 생성/읽기/쓰기
        Permission.WORKSPACE_CREATE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_WRITE,
        # 파일 전체
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.FILE_UPLOAD,
        Permission.FILE_DELETE,
        # AI 전체
        Permission.AI_CHAT,
        Permission.AI_EXPLAIN,
        Permission.AI_REWRITE,
        Permission.AI_AGENT,
        # IDE 전체
        Permission.IDE_ACCESS,
        Permission.IDE_TERMINAL,
        Permission.IDE_DEBUG,
    },
    Role.VIEWER: {
        # 읽기 전용
        Permission.WORKSPACE_READ,
        Permission.FILE_READ,
        Permission.AI_CHAT,
        Permission.AI_EXPLAIN,
        Permission.IDE_ACCESS,
    },
}


class RBACService:
    """RBAC 서비스 클래스"""
    
    @staticmethod
    def get_role_permissions(role: str) -> Set[Permission]:
        """역할의 권한 목록 반환"""
        try:
            role_enum = Role(role)
            return ROLE_PERMISSIONS.get(role_enum, set())
        except ValueError:
            logger.warning(f"Unknown role: {role}")
            return set()
    
    @staticmethod
    def has_permission(user_role: str, required_permission: Permission) -> bool:
        """사용자가 특정 권한을 가지고 있는지 확인"""
        permissions = RBACService.get_role_permissions(user_role)
        return required_permission in permissions
    
    @staticmethod
    def has_any_permission(user_role: str, required_permissions: List[Permission]) -> bool:
        """사용자가 권한 목록 중 하나라도 가지고 있는지 확인"""
        permissions = RBACService.get_role_permissions(user_role)
        return any(p in permissions for p in required_permissions)
    
    @staticmethod
    def has_all_permissions(user_role: str, required_permissions: List[Permission]) -> bool:
        """사용자가 모든 권한을 가지고 있는지 확인"""
        permissions = RBACService.get_role_permissions(user_role)
        return all(p in permissions for p in required_permissions)
    
    @staticmethod
    def is_admin(user_role: str) -> bool:
        """관리자 역할인지 확인"""
        return user_role == Role.ADMIN.value


rbac_service = RBACService()


# ============================================================
# FastAPI 의존성
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """
    현재 인증된 사용자 가져오기
    
    JWT 토큰 또는 세션 토큰으로 인증
    """
    token = credentials.credentials
    
    # JWT 토큰 검증
    payload = jwt_auth_service.verify_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            result = await db.execute(
                select(UserModel).where(UserModel.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                return user
    
    # 세션 토큰 검증 (대체 방법)
    from datetime import datetime
    result = await db.execute(
        select(UserSessionModel).where(
            UserSessionModel.session_token == token,
            UserSessionModel.expires_at > datetime.utcnow(),
        )
    )
    session = result.scalar_one_or_none()
    if session:
        user = await db.get(UserModel, session.user_id)
        if user:
            return user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "Invalid or expired token", "code": "UNAUTHORIZED"},
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserModel]:
    """
    현재 인증된 사용자 가져오기 (선택적)
    
    인증 토큰이 없거나 유효하지 않은 경우 None 반환
    AI Gateway 등 외부 클라이언트에서 호출할 수 있는 엔드포인트용
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # JWT 토큰 검증
    payload = jwt_auth_service.verify_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            result = await db.execute(
                select(UserModel).where(UserModel.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                return user
    
    # 세션 토큰 검증 (대체 방법)
    from datetime import datetime
    result = await db.execute(
        select(UserSessionModel).where(
            UserSessionModel.session_token == token,
            UserSessionModel.expires_at > datetime.utcnow(),
        )
    )
    session = result.scalar_one_or_none()
    if session:
        user = await db.get(UserModel, session.user_id)
        if user:
            return user
    
    return None


def require_permission(*required_permissions: Permission):
    """
    특정 권한이 필요한 엔드포인트를 위한 의존성 팩토리
    
    사용법:
        @router.get("/admin/servers")
        async def list_servers(
            current_user: UserModel = Depends(require_permission(Permission.ADMIN_READ))
        ):
            ...
    """
    async def permission_checker(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        user_role = current_user.role or "viewer"
        
        # 관리자는 모든 권한
        if rbac_service.is_admin(user_role):
            return current_user
        
        # 권한 확인
        if not rbac_service.has_all_permissions(user_role, list(required_permissions)):
            missing = [
                p.value for p in required_permissions 
                if not rbac_service.has_permission(user_role, p)
            ]
            logger.warning(
                f"Permission denied for user {current_user.user_id}: "
                f"missing {missing}, role={user_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "code": "FORBIDDEN",
                    "required": [p.value for p in required_permissions],
                    "missing": missing,
                },
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(*required_permissions: Permission):
    """
    권한 목록 중 하나라도 있으면 허용하는 의존성 팩토리
    """
    async def permission_checker(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        user_role = current_user.role or "viewer"
        
        if rbac_service.is_admin(user_role):
            return current_user
        
        if not rbac_service.has_any_permission(user_role, list(required_permissions)):
            logger.warning(
                f"Permission denied for user {current_user.user_id}: "
                f"none of {[p.value for p in required_permissions]}, role={user_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "code": "FORBIDDEN",
                    "required_any": [p.value for p in required_permissions],
                },
            )
        
        return current_user
    
    return permission_checker


def require_admin():
    """
    관리자 권한 필요
    """
    async def admin_checker(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if not rbac_service.is_admin(current_user.role or ""):
            logger.warning(
                f"Admin access denied for user {current_user.user_id}, role={current_user.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Admin access required",
                    "code": "ADMIN_REQUIRED",
                },
            )
        
        return current_user
    
    return admin_checker


def require_role(*roles: Role):
    """
    특정 역할 필요
    """
    async def role_checker(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        user_role = current_user.role or "viewer"
        
        if user_role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Role not allowed",
                    "code": "ROLE_REQUIRED",
                    "required_roles": [r.value for r in roles],
                    "current_role": user_role,
                },
            )
        
        return current_user
    
    return role_checker
