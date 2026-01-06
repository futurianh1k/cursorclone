"""
Pydantic 스키마 정의 (API 요청/응답)
Task B: API 명세 반영
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
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
    refresh_token: Optional[str] = Field(None, alias="refreshToken", description="리프레시 토큰 (토큰 갱신용)")
    token_type: str = Field(default="bearer", alias="tokenType")
    expires_in: Optional[int] = Field(None, alias="expiresIn", description="액세스 토큰 만료 시간 (초)")
    user: "UserResponse"
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: str = Field(..., alias="userId")
    email: str
    name: str
    org_id: str = Field(..., alias="orgId")
    role: str = "developer"
    avatar_url: Optional[str] = Field(default=None, alias="avatarUrl")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


# ============================================================
# Workspaces
# ============================================================

class CreateWorkspaceRequest(BaseModel):
    """워크스페이스 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100)
    language: Optional[str] = Field(default="python", max_length=50)
    project_id: Optional[str] = Field(default=None, alias="projectId", max_length=100, description="기존 프로젝트에 워크스페이스를 추가할 때 사용")
    project_name: Optional[str] = Field(default=None, alias="projectName", max_length=255, description="projectId가 없을 때 새 프로젝트 생성용 이름(선택)")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # 알파벳, 숫자, 하이픈, 언더스코어만 허용
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("projectId must contain only alphanumeric characters, hyphens, and underscores")
        return v


class WorkspaceResponse(BaseModel):
    """워크스페이스 응답"""
    workspace_id: str = Field(..., alias="workspaceId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    name: str
    root_path: str = Field(..., alias="rootPath")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class CreateProjectRequest(BaseModel):
    """프로젝트 생성 요청"""
    name: str = Field(..., min_length=1, max_length=255)
    
    @field_validator("name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        return v.strip()


class ProjectResponse(BaseModel):
    """프로젝트 응답"""
    project_id: str = Field(..., alias="projectId")
    name: str
    owner_id: str = Field(..., alias="ownerId")
    org_id: Optional[str] = Field(default=None, alias="orgId")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIExplainResponse(BaseModel):
    """AI 코드 설명 응답"""
    explanation: str
    tokens_used: Optional[int] = Field(default=None, alias="tokensUsed")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIChatResponse(BaseModel):
    """AI 채팅 응답"""
    response: str = Field(..., description="AI 응답")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    suggested_action: Optional[str] = Field(default=None, alias="suggestedAction", description="제안 액션 (rewrite, explain 등)")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


# ============================================================
# AI Modes (Agent, Plan, Ask, Debug)
# ============================================================

class AIMode(str, Enum):
    """AI 작동 모드"""
    ASK = "ask"          # 질문/답변 모드
    AGENT = "agent"      # 자동 코드 작성/수정 모드
    PLAN = "plan"        # 작업 계획 수립 모드
    DEBUG = "debug"      # 버그 분석/수정 모드


class TaskStep(BaseModel):
    """작업 단계"""
    step_number: int = Field(..., alias="stepNumber")
    description: str
    status: str = Field(default="pending", pattern="^(pending|in_progress|completed|failed)$")
    file_path: Optional[str] = Field(default=None, alias="filePath")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIPlanRequest(BaseModel):
    """AI Plan 모드 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    goal: str = Field(..., min_length=1, description="달성할 목표")
    context: Optional[str] = Field(default=None, description="추가 컨텍스트")
    file_paths: Optional[List[str]] = Field(default=None, alias="filePaths", description="관련 파일 경로들")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIPlanResponse(BaseModel):
    """AI Plan 모드 응답"""
    summary: str = Field(..., description="계획 요약")
    steps: List[TaskStep] = Field(..., description="실행 단계들")
    estimated_changes: int = Field(default=0, alias="estimatedChanges", description="예상 변경 파일 수")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIAgentRequest(BaseModel):
    """AI Agent 모드 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    instruction: str = Field(..., min_length=1, description="수행할 작업 지시")
    file_paths: Optional[List[str]] = Field(default=None, alias="filePaths", description="작업 대상 파일들")
    auto_apply: bool = Field(default=False, alias="autoApply", description="자동 적용 여부")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class FileChange(BaseModel):
    """파일 변경 내역"""
    file_path: str = Field(..., alias="filePath")
    action: str = Field(..., pattern="^(create|modify|delete)$")
    diff: Optional[str] = None
    description: str


class AIAgentResponse(BaseModel):
    """AI Agent 모드 응답"""
    summary: str = Field(..., description="작업 요약")
    changes: List[FileChange] = Field(..., description="파일 변경 내역")
    applied: bool = Field(default=False, description="적용 여부")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIDebugRequest(BaseModel):
    """AI Debug 모드 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    error_message: Optional[str] = Field(default=None, alias="errorMessage", description="에러 메시지")
    stack_trace: Optional[str] = Field(default=None, alias="stackTrace", description="스택 트레이스")
    file_path: Optional[str] = Field(default=None, alias="filePath", description="에러 발생 파일")
    file_content: Optional[str] = Field(default=None, alias="fileContent", description="파일 내용")
    description: Optional[str] = Field(default=None, description="문제 설명")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class BugFix(BaseModel):
    """버그 수정 제안"""
    file_path: str = Field(..., alias="filePath")
    line_number: Optional[int] = Field(default=None, alias="lineNumber")
    original_code: str = Field(..., alias="originalCode")
    fixed_code: str = Field(..., alias="fixedCode")
    explanation: str
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIDebugResponse(BaseModel):
    """AI Debug 모드 응답"""
    diagnosis: str = Field(..., description="문제 진단")
    root_cause: str = Field(..., alias="rootCause", description="근본 원인")
    fixes: List[BugFix] = Field(..., description="수정 제안들")
    prevention_tips: Optional[List[str]] = Field(default=None, alias="preventionTips", description="예방 팁")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIRewriteResponse(BaseModel):
    """AI 코드 리라이트 응답 (diff 반환)"""
    diff: str
    tokens_used: Optional[int] = Field(default=None, alias="tokensUsed")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


# ============================================================
# Patch
# ============================================================

class PatchValidateRequest(BaseModel):
    """패치 검증 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    patch: str = Field(..., min_length=1)
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class PatchApplyResponse(BaseModel):
    """패치 적용 응답"""
    success: bool
    applied_files: List[str] = Field(default_factory=list, alias="appliedFiles")
    message: Optional[str] = None
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


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
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


# ============================================================
# AI Context & Image (Cursor-like features)
# ============================================================

class ContextType(str, Enum):
    """컨텍스트 타입"""
    FILE = "file"           # 전체 파일
    SELECTION = "selection" # 코드 선택 영역
    FOLDER = "folder"       # 폴더 전체
    IMAGE = "image"         # 이미지
    URL = "url"             # 웹 페이지 URL
    CLIPBOARD = "clipboard" # 클립보드 내용


class ContextItem(BaseModel):
    """추가된 컨텍스트 아이템"""
    type: ContextType
    path: Optional[str] = Field(default=None, description="파일/폴더 경로")
    content: Optional[str] = Field(default=None, description="텍스트 내용")
    selection: Optional[SelectionRange] = Field(default=None, description="선택 영역")
    image_url: Optional[str] = Field(default=None, alias="imageUrl", description="업로드된 이미지 URL")
    image_base64: Optional[str] = Field(default=None, alias="imageBase64", description="Base64 인코딩된 이미지")
    mime_type: Optional[str] = Field(default=None, alias="mimeType", description="이미지 MIME 타입")
    name: Optional[str] = Field(default=None, description="표시용 이름")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIAdvancedChatRequest(BaseModel):
    """고급 AI 채팅 요청 (Cursor 스타일)"""
    workspace_id: str = Field(..., alias="workspaceId")
    message: str = Field(..., min_length=1, description="사용자 질문 또는 지시")
    mode: AIMode = Field(default=AIMode.ASK, description="AI 모드")
    contexts: Optional[List[ContextItem]] = Field(default=None, description="추가 컨텍스트 목록")
    history: Optional[List[ChatMessage]] = Field(default=None, description="이전 대화 히스토리")
    # 현재 열린 파일 (기본 컨텍스트)
    current_file: Optional[str] = Field(default=None, alias="currentFile")
    current_content: Optional[str] = Field(default=None, alias="currentContent")
    current_selection: Optional[SelectionRange] = Field(default=None, alias="currentSelection")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class AIAdvancedChatResponse(BaseModel):
    """고급 AI 채팅 응답"""
    response: str = Field(..., description="AI 응답")
    mode: AIMode = Field(..., description="사용된 AI 모드")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    # 모드별 추가 데이터
    plan_steps: Optional[List[TaskStep]] = Field(default=None, alias="planSteps", description="Plan 모드: 작업 단계")
    file_changes: Optional[List[FileChange]] = Field(default=None, alias="fileChanges", description="Agent 모드: 파일 변경")
    bug_fixes: Optional[List[BugFix]] = Field(default=None, alias="bugFixes", description="Debug 모드: 버그 수정")
    suggested_action: Optional[str] = Field(default=None, alias="suggestedAction")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ImageUploadResponse(BaseModel):
    """이미지 업로드 응답"""
    image_id: str = Field(..., alias="imageId")
    image_url: str = Field(..., alias="imageUrl")
    thumbnail_url: Optional[str] = Field(default=None, alias="thumbnailUrl")
    mime_type: str = Field(..., alias="mimeType")
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ImageAnalysisRequest(BaseModel):
    """이미지 분석 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    image_base64: Optional[str] = Field(default=None, alias="imageBase64")
    question: Optional[str] = Field(default=None, description="이미지에 대한 질문")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ImageAnalysisResponse(BaseModel):
    """이미지 분석 응답"""
    description: str = Field(..., description="이미지 설명")
    extracted_text: Optional[str] = Field(default=None, alias="extractedText", description="OCR 추출 텍스트")
    code_blocks: Optional[List[str]] = Field(default=None, alias="codeBlocks", description="추출된 코드 블록")
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ContextSuggestRequest(BaseModel):
    """컨텍스트 제안 요청"""
    workspace_id: str = Field(..., alias="workspaceId")
    query: str = Field(..., min_length=1, description="검색 쿼리")
    types: Optional[List[ContextType]] = Field(default=None, description="필터링할 타입")
    limit: int = Field(default=10, ge=1, le=50)
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ContextSuggestion(BaseModel):
    """컨텍스트 제안 아이템"""
    type: ContextType
    path: Optional[str] = None
    name: str
    preview: Optional[str] = None
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class ContextSuggestResponse(BaseModel):
    """컨텍스트 제안 응답"""
    suggestions: List[ContextSuggestion]
    total: int
    
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
