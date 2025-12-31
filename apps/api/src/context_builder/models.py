"""
Context Builder Pydantic 모델 정의
Task: Context Builder 구현
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class ContextSourceType(str, Enum):
    """컨텍스트 소스 타입"""
    SELECTION = "selection"
    FILE = "file"
    RELATED = "related"
    SEARCH = "search"


class ActionType(str, Enum):
    """액션 타입"""
    REWRITE = "rewrite"
    EXPLAIN = "explain"
    GENERATE = "generate"
    CHAT = "chat"


class SelectionRange(BaseModel):
    """선택 범위"""
    start_line: int = Field(..., ge=1, description="시작 라인 (1-based)")
    end_line: int = Field(..., ge=1, description="종료 라인 (1-based)")
    start_col: Optional[int] = Field(default=None, ge=1, description="시작 컬럼 (1-based)")
    end_col: Optional[int] = Field(default=None, ge=1, description="종료 컬럼 (1-based)")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")


class ContextSource(BaseModel):
    """컨텍스트 소스 정의"""
    type: ContextSourceType = Field(..., description="소스 타입")
    path: str = Field(..., min_length=1, description="파일 경로")
    content: Optional[str] = Field(default=None, description="파일 내용")
    range: Optional[SelectionRange] = Field(default=None, description="선택 범위 (type=selection일 때)")
    
    class Config:
        use_enum_values = True


class ContextBuildRequest(BaseModel):
    """Context Builder 요청"""
    workspace_id: str = Field(..., min_length=1, description="워크스페이스 ID")
    action: ActionType = Field(..., description="액션 타입")
    instruction: str = Field(..., min_length=1, max_length=2000, description="사용자 지시사항")
    sources: List[ContextSource] = Field(..., min_length=1, description="컨텍스트 소스 목록")
    
    # 선택적 옵션
    max_tokens: Optional[int] = Field(default=4096, ge=1, le=8192, description="최대 토큰 수")
    include_related: Optional[bool] = Field(default=False, description="관련 파일 포함 여부")
    
    class Config:
        use_enum_values = True


class PromptMessage(BaseModel):
    """LLM 메시지 형식"""
    role: str = Field(..., description="역할 (system/user/assistant)")
    content: str = Field(..., min_length=1, description="메시지 내용")


class ContextBuildResponse(BaseModel):
    """Context Builder 응답"""
    messages: List[PromptMessage] = Field(..., min_length=1, description="프롬프트 메시지 목록")
    
    # 메타데이터 (로깅용, 원문 저장 금지)
    metadata: Dict[str, Any] = Field(
        ...,
        description="메타데이터 (action, source_count, total_tokens_estimate, context_hash 등)"
    )
