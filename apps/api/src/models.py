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

class UserResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: str = Field(..., alias="userId")
    name: str
    org_id: str = Field(..., alias="orgId")
    
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
