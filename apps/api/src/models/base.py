"""
Pydantic 스키마 정의 (API 요청/응답)
Task B: API 명세 반영
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
import re


# ============================================================
# Common
# ============================================================

class ErrorResponse(BaseModel):
    """공통 에러 응답"""
    error: str
    code: str
    detail: Optional[str] = None


# ============================================================
# Auth
# ============================================================

class SignUpRequest(BaseModel):
    """회원가입 요청"""
    email: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    org_name: Optional[str] = Field(default=None, max_length=255)
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()


class LoginRequest(BaseModel):
    """로그인 요청"""
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """로그인 응답"""
    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    user: "UserResponse"
    
    class Config:
        populate_by_name = True


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: str = Field(..., alias="userId")
    email: str
    name: str
    org_id: str = Field(..., alias="orgId")
    role: str = "developer"
    avatar_url: Optional[str] = Field(default=None, alias="avatarUrl")
    
    class Config:
        populate_by_name = True


# ============================================================
# Workspaces
# ============================================================

class CreateWorkspaceRequest(BaseModel):
    """워크스페이스 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100)
    language: Optional[str] = Field(default="python", max_length=50)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # 알파벳, 숫자, 하이픈, 언더스코어만 허용
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class WorkspaceResponse(BaseModel):
    """워크스페이스 응답"""
    workspace_id: str = Field(..., alias="workspaceId")
    name: str
    root_path: str = Field(..., alias="rootPath")
    
    class Config:
        populate_by_name = True


class WorkspaceListResponse(BaseModel):
    """워크스페이스 목록 응답"""
    workspaces: List[WorkspaceResponse]


class CloneGitHubRequest(BaseModel):
    """GitHub 저장소 클론 요청"""
    repository_url: str = Field(..., alias="repositoryUrl", min_length=1)
    name: Optional[str] = Field(default=None, max_length=100)
    branch: Optional[str] = Field(default=None, max_length=100)
    
    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        # GitHub URL 형식 검증 (https://github.com/owner/repo 또는 git@github.com:owner/repo.git)
        github_patterns = [
            r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:\.git)?$",
            r"^git@github\.com:[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+\.git$",
        ]
        if not any(re.match(pattern, v) for pattern in github_patterns):
            raise ValueError("Invalid GitHub repository URL")
        return v
    
    class Config:
        populate_by_name = True


# ============================================================
# Files
# ============================================================

class FileType(str, Enum):
    """파일 타입"""
    FILE = "file"
    DIRECTORY = "directory"


class FileTreeItem(BaseModel):
    """파일 트리 아이템"""
    name: str
    path: str
    type: FileType
    children: Optional[List["FileTreeItem"]] = None


class FileTreeResponse(BaseModel):
    """파일 트리 응답"""
    workspace_id: str = Field(..., alias="workspaceId")
    tree: List[FileTreeItem]
    
    class Config:
        populate_by_name = True


class FileContentResponse(BaseModel):
    """파일 내용 응답"""
    path: str
    content: str
    encoding: str = "utf-8"


class UpdateFileContentRequest(BaseModel):
    """파일 내용 수정 요청"""
    path: str = Field(..., min_length=1)
    content: str
    
    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        # 경로 탈출 방지
        if ".." in v:
            raise ValueError("Path traversal is not allowed")
        if v.startswith("/"):
            raise ValueError("Absolute paths are not allowed")
        return v


class UpdateFileContentResponse(BaseModel):
    """파일 내용 수정 응답"""
    path: str
    success: bool
    message: Optional[str] = None


# ============================================================
# AI
# ============================================================

class SelectionRange(BaseModel):
    """선택 범위"""
    start_line: int = Field(..., alias="startLine", ge=1)
    end_line: int = Field(..., alias="endLine", ge=1)
    
    @field_validator("end_line")
    @classmethod
    def validate_range(cls, v: int, info) -> int:
        start = info.data.get("start_line")
        if start and v < start:
            raise ValueError("end_line must be >= start_line")
        return v
    
    class Config:
        populate_by_name = True


class AIExplainRequest(BaseModel):
    """AI 코드 설명 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    file_path: str = Field(..., alias="filePath", min_length=1)
    selection: Optional[SelectionRange] = None
    
    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if ".." in v:
            raise ValueError("Path traversal is not allowed")
        return v
    
    class Config:
        populate_by_name = True


class AIExplainResponse(BaseModel):
    """AI 코드 설명 응답"""
    explanation: str
    tokens_used: Optional[int] = Field(default=None, alias="tokensUsed")
    
    class Config:
        populate_by_name = True


# ============================================================
# AI Chat (대화형 API)
# ============================================================

class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class AIChatRequest(BaseModel):
    """AI 채팅 요청 - 대화형 코드 질문/수정"""
    workspace_id: str = Field(..., alias="workspaceId")
    message: str = Field(..., min_length=1, description="사용자 질문 또는 지시")
    file_path: Optional[str] = Field(default=None, alias="filePath", description="현재 열린 파일 경로")
    file_content: Optional[str] = Field(default=None, alias="fileContent", description="파일 내용 (선택)")
    selection: Optional[SelectionRange] = Field(default=None, description="선택된 코드 범위")
    history: Optional[List[ChatMessage]] = Field(default=None, description="이전 대화 히스토리")
    
    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v and ".." in v:
            raise ValueError("Path traversal is not allowed")
        return v
    
    class Config:
        populate_by_name = True


class AIChatResponse(BaseModel):
    """AI 채팅 응답"""
    response: str = Field(..., description="AI 응답")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    suggested_action: Optional[str] = Field(default=None, alias="suggestedAction", description="제안 액션 (rewrite, explain 등)")
    
    class Config:
        populate_by_name = True


class AIRewriteRequest(BaseModel):
    """AI 코드 리라이트 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    instruction: str = Field(..., min_length=1, max_length=2000)
    target: dict = Field(...)  # {file: str, selection: SelectionRange}
    
    @field_validator("target")
    @classmethod
    def validate_target(cls, v: dict) -> dict:
        if "file" not in v:
            raise ValueError("target must contain 'file'")
        if ".." in v.get("file", ""):
            raise ValueError("Path traversal is not allowed")
        return v
    
    class Config:
        populate_by_name = True


class AIRewriteResponse(BaseModel):
    """AI 코드 리라이트 응답 (diff 반환)"""
    diff: str
    tokens_used: Optional[int] = Field(default=None, alias="tokensUsed")
    
    class Config:
        populate_by_name = True


# ============================================================
# Patch
# ============================================================

class PatchValidateRequest(BaseModel):
    """패치 검증 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    patch: str = Field(..., min_length=1)
    
    class Config:
        populate_by_name = True


class PatchValidateResponse(BaseModel):
    """패치 검증 응답"""
    valid: bool
    reason: Optional[str] = None
    files: Optional[List[str]] = None


class PatchApplyRequest(BaseModel):
    """패치 적용 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    patch: str = Field(..., min_length=1)
    dry_run: bool = Field(default=False, alias="dryRun")
    
    class Config:
        populate_by_name = True


class PatchApplyResponse(BaseModel):
    """패치 적용 응답"""
    success: bool
    applied_files: List[str] = Field(default_factory=list, alias="appliedFiles")
    message: Optional[str] = None
    
    class Config:
        populate_by_name = True


# ============================================================
# WebSocket
# ============================================================

class WSMessageType(str, Enum):
    """WebSocket 메시지 타입"""
    FILE_CHANGE = "file_change"
    CURSOR_MOVE = "cursor_move"
    AI_STREAM = "ai_stream"
    ERROR = "error"


class WSMessage(BaseModel):
    """WebSocket 메시지"""
    type: WSMessageType
    payload: dict


# ============================================================
# Admin / Infrastructure
# ============================================================

class ServerType(str, Enum):
    """서버 타입"""
    KUBERNETES = "kubernetes"
    DOCKER = "docker"
    SSH = "ssh"


class ServerStatus(str, Enum):
    """서버 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class AuthType(str, Enum):
    """인증 타입"""
    SSH_KEY = "ssh_key"
    MTLS = "mtls"
    API_KEY = "api_key"


class RegisterServerRequest(BaseModel):
    """서버 등록 요청"""
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1)
    port: int = Field(default=22, ge=1, le=65535)
    type: ServerType
    region: Optional[str] = Field(default=None, max_length=100)
    zone: Optional[str] = Field(default=None, max_length=100)
    max_workspaces: Optional[int] = Field(default=100, ge=1)
    auth: dict = Field(..., description="인증 정보 (타입별로 다름)")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class ServerResponse(BaseModel):
    """서버 응답"""
    id: str = Field(..., alias="serverId")
    name: str
    host: str
    port: int
    type: ServerType
    region: Optional[str] = None
    zone: Optional[str] = None
    status: ServerStatus
    max_workspaces: int
    current_workspaces: int
    cpu_capacity: Optional[float] = None
    memory_capacity: Optional[int] = None
    disk_capacity: Optional[int] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[int] = None
    disk_usage: Optional[int] = None
    last_health_check: Optional[str] = None
    
    class Config:
        populate_by_name = True


class TestConnectionResponse(BaseModel):
    """연결 테스트 응답"""
    success: bool
    message: str
    resource_info: Optional[dict] = None


class PlacementPolicyType(str, Enum):
    """배치 정책 타입"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    REGION_BASED = "region_based"


class PlacementRequest(BaseModel):
    """워크스페이스 배치 요청"""
    server_id: Optional[str] = Field(default=None, alias="serverId")
    policy: Optional[PlacementPolicyType] = Field(default=PlacementPolicyType.LEAST_LOADED)
    region: Optional[str] = None
    
    class Config:
        populate_by_name = True
