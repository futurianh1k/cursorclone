"""
Pydantic 스키마 정의 (API 요청/응답)
"""

# 기존 모델 (base.py에서 가져옴)
from .base import (
    ErrorResponse,
    SignUpRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    CreateWorkspaceRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
    CloneGitHubRequest,
    FileType,
    FileTreeItem,
    FileTreeResponse,
    FileContentResponse,
    UpdateFileContentRequest,
    UpdateFileContentResponse,
    SelectionRange,
    AIExplainRequest,
    AIExplainResponse,
    AIRewriteRequest,
    AIRewriteResponse,
    PatchValidateRequest,
    PatchValidateResponse,
    PatchApplyRequest,
    PatchApplyResponse,
    WSMessageType,
    WSMessage,
    ServerType,
    ServerStatus,
    AuthType,
    RegisterServerRequest,
    ServerResponse,
    TestConnectionResponse,
    PlacementPolicyType,
    PlacementRequest,
)

# 컨테이너 모델
from .container import (
    ContainerStatus,
    ContainerImage,
    ResourceLimits,
    ContainerConfig,
    StartContainerRequest,
    StopContainerRequest,
    RestartContainerRequest,
    ExecuteCommandRequest,
    ContainerStatusResponse,
    ContainerLogsResponse,
    ExecuteCommandResponse,
    ContainerActionResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    # Auth
    "SignUpRequest",
    "LoginRequest",
    "LoginResponse",
    "UserResponse",
    # Workspaces
    "CreateWorkspaceRequest",
    "WorkspaceResponse",
    "WorkspaceListResponse",
    "CloneGitHubRequest",
    # Files
    "FileType",
    "FileTreeItem",
    "FileTreeResponse",
    "FileContentResponse",
    "UpdateFileContentRequest",
    "UpdateFileContentResponse",
    # AI
    "SelectionRange",
    "AIExplainRequest",
    "AIExplainResponse",
    "AIRewriteRequest",
    "AIRewriteResponse",
    # Patch
    "PatchValidateRequest",
    "PatchValidateResponse",
    "PatchApplyRequest",
    "PatchApplyResponse",
    # WebSocket
    "WSMessageType",
    "WSMessage",
    # Admin / Infrastructure
    "ServerType",
    "ServerStatus",
    "AuthType",
    "RegisterServerRequest",
    "ServerResponse",
    "TestConnectionResponse",
    "PlacementPolicyType",
    "PlacementRequest",
    # Container
    "ContainerStatus",
    "ContainerImage",
    "ResourceLimits",
    "ContainerConfig",
    "StartContainerRequest",
    "StopContainerRequest",
    "RestartContainerRequest",
    "ExecuteCommandRequest",
    "ContainerStatusResponse",
    "ContainerLogsResponse",
    "ExecuteCommandResponse",
    "ContainerActionResponse",
]
