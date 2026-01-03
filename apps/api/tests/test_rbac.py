"""
RBAC (Role-Based Access Control) 테스트
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.rbac_service import (
    rbac_service,
    Role,
    Permission,
    ROLE_PERMISSIONS,
)


class TestRolePermissions:
    """역할별 권한 테스트"""

    def test_admin_has_all_permissions(self):
        """관리자는 모든 권한을 가짐"""
        admin_permissions = ROLE_PERMISSIONS[Role.ADMIN]
        all_permissions = set(Permission)
        
        assert admin_permissions == all_permissions

    def test_developer_permissions(self):
        """개발자 권한 확인"""
        dev_permissions = ROLE_PERMISSIONS[Role.DEVELOPER]
        
        # 개발자가 가져야 할 권한
        assert Permission.WORKSPACE_CREATE in dev_permissions
        assert Permission.WORKSPACE_READ in dev_permissions
        assert Permission.WORKSPACE_WRITE in dev_permissions
        assert Permission.FILE_READ in dev_permissions
        assert Permission.FILE_WRITE in dev_permissions
        assert Permission.AI_CHAT in dev_permissions
        assert Permission.AI_AGENT in dev_permissions
        assert Permission.IDE_ACCESS in dev_permissions
        
        # 개발자가 가지면 안 되는 권한
        assert Permission.ADMIN_WRITE not in dev_permissions
        assert Permission.SERVER_MANAGE not in dev_permissions
        assert Permission.USER_MANAGE not in dev_permissions

    def test_viewer_permissions(self):
        """뷰어 권한 확인"""
        viewer_permissions = ROLE_PERMISSIONS[Role.VIEWER]
        
        # 뷰어가 가져야 할 권한 (읽기 전용)
        assert Permission.WORKSPACE_READ in viewer_permissions
        assert Permission.FILE_READ in viewer_permissions
        assert Permission.AI_CHAT in viewer_permissions
        assert Permission.IDE_ACCESS in viewer_permissions
        
        # 뷰어가 가지면 안 되는 권한 (쓰기)
        assert Permission.WORKSPACE_CREATE not in viewer_permissions
        assert Permission.WORKSPACE_WRITE not in viewer_permissions
        assert Permission.FILE_WRITE not in viewer_permissions
        assert Permission.AI_REWRITE not in viewer_permissions

    def test_manager_permissions(self):
        """매니저 권한 확인"""
        manager_permissions = ROLE_PERMISSIONS[Role.MANAGER]
        
        # 매니저가 가져야 할 권한
        assert Permission.ADMIN_READ in manager_permissions
        assert Permission.WORKSPACE_DELETE in manager_permissions
        assert Permission.WORKSPACE_SHARE in manager_permissions
        
        # 매니저가 가지면 안 되는 권한
        assert Permission.ADMIN_WRITE not in manager_permissions
        assert Permission.SERVER_MANAGE not in manager_permissions


class TestRBACService:
    """RBAC 서비스 테스트"""

    def test_get_role_permissions_admin(self):
        """관리자 역할의 권한 조회"""
        permissions = rbac_service.get_role_permissions("admin")
        
        assert Permission.ADMIN_WRITE in permissions
        assert Permission.SERVER_MANAGE in permissions
        assert len(permissions) == len(Permission)

    def test_get_role_permissions_unknown_role(self):
        """알 수 없는 역할은 빈 권한 반환"""
        permissions = rbac_service.get_role_permissions("unknown_role")
        
        assert permissions == set()

    def test_has_permission_admin(self):
        """관리자는 모든 권한 있음"""
        assert rbac_service.has_permission("admin", Permission.ADMIN_WRITE) is True
        assert rbac_service.has_permission("admin", Permission.SERVER_MANAGE) is True
        assert rbac_service.has_permission("admin", Permission.AI_AGENT) is True

    def test_has_permission_developer(self):
        """개발자 권한 확인"""
        assert rbac_service.has_permission("developer", Permission.AI_CHAT) is True
        assert rbac_service.has_permission("developer", Permission.FILE_WRITE) is True
        assert rbac_service.has_permission("developer", Permission.ADMIN_WRITE) is False

    def test_has_permission_viewer(self):
        """뷰어 권한 확인"""
        assert rbac_service.has_permission("viewer", Permission.FILE_READ) is True
        assert rbac_service.has_permission("viewer", Permission.FILE_WRITE) is False

    def test_has_any_permission(self):
        """권한 목록 중 하나라도 있는지 확인"""
        # 개발자: AI_CHAT 있음, ADMIN_WRITE 없음
        assert rbac_service.has_any_permission(
            "developer",
            [Permission.AI_CHAT, Permission.ADMIN_WRITE]
        ) is True
        
        # 뷰어: ADMIN_WRITE, SERVER_MANAGE 둘 다 없음
        assert rbac_service.has_any_permission(
            "viewer",
            [Permission.ADMIN_WRITE, Permission.SERVER_MANAGE]
        ) is False

    def test_has_all_permissions(self):
        """모든 권한이 있는지 확인"""
        # 개발자: AI_CHAT, FILE_READ 둘 다 있음
        assert rbac_service.has_all_permissions(
            "developer",
            [Permission.AI_CHAT, Permission.FILE_READ]
        ) is True
        
        # 개발자: AI_CHAT 있음, ADMIN_WRITE 없음
        assert rbac_service.has_all_permissions(
            "developer",
            [Permission.AI_CHAT, Permission.ADMIN_WRITE]
        ) is False

    def test_is_admin(self):
        """관리자 역할 확인"""
        assert rbac_service.is_admin("admin") is True
        assert rbac_service.is_admin("developer") is False
        assert rbac_service.is_admin("manager") is False
        assert rbac_service.is_admin("viewer") is False


class TestPermissionHierarchy:
    """권한 계층 테스트"""

    def test_role_hierarchy(self):
        """역할 계층: admin > manager > developer > viewer"""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        manager_perms = ROLE_PERMISSIONS[Role.MANAGER]
        developer_perms = ROLE_PERMISSIONS[Role.DEVELOPER]
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        
        # admin은 모든 권한
        assert len(admin_perms) == len(Permission)
        
        # manager > developer > viewer
        assert len(manager_perms) > len(developer_perms)
        assert len(developer_perms) > len(viewer_perms)
        
        # viewer 권한은 developer에 포함
        assert viewer_perms.issubset(developer_perms)
        
        # developer 권한은 manager에 포함
        assert developer_perms.issubset(manager_perms)

    def test_permission_categories(self):
        """권한 카테고리별 확인"""
        # Admin 권한은 admin/manager만
        assert Permission.ADMIN_READ in ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.ADMIN_READ in ROLE_PERMISSIONS[Role.MANAGER]
        assert Permission.ADMIN_READ not in ROLE_PERMISSIONS[Role.DEVELOPER]
        
        # Server 관리는 admin만
        assert Permission.SERVER_MANAGE in ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.SERVER_MANAGE not in ROLE_PERMISSIONS[Role.MANAGER]
        
        # AI 기능은 viewer 제외 모두
        for role in [Role.ADMIN, Role.MANAGER, Role.DEVELOPER]:
            assert Permission.AI_AGENT in ROLE_PERMISSIONS[role]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
