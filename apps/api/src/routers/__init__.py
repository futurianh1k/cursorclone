"""
API 라우터 모듈
"""

from .auth import router as auth_router
from .workspaces import router as workspaces_router
from .files import router as files_router
from .ai import router as ai_router
from .patch import router as patch_router
from .ws import router as ws_router
from .admin import router as admin_router
from .container import router as container_router
from .ssh import router as ssh_router

__all__ = [
    "auth_router",
    "workspaces_router", 
    "files_router",
    "ai_router",
    "patch_router",
    "ws_router",
    "admin_router",
    "container_router",
    "ssh_router",
]
