"""
컨테이너 관련 Pydantic 스키마 정의
워크스페이스 컨테이너 관리를 위한 요청/응답 모델
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from enum import Enum
import re


class ContainerStatus(str, Enum):
    """컨테이너 상태"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


class ContainerImage(str, Enum):
    """지원하는 컨테이너 이미지"""
    PYTHON = "cursor-workspace-python:latest"
    NODEJS = "cursor-workspace-nodejs:latest"
    GOLANG = "cursor-workspace-golang:latest"
    RUST = "cursor-workspace-rust:latest"
    JAVA = "cursor-workspace-java:latest"
    CUSTOM = "custom"


class ResourceLimits(BaseModel):
    """리소스 제한 설정"""
    cpu_count: float = Field(default=2.0, ge=0.5, le=16, description="CPU 코어 수")
    memory_mb: int = Field(default=2048, ge=256, le=32768, description="메모리 (MB)")
    disk_mb: int = Field(default=10240, ge=1024, le=102400, description="디스크 (MB)")


class ContainerConfig(BaseModel):
    """컨테이너 설정"""
    image: ContainerImage = Field(default=ContainerImage.PYTHON)
    custom_image: Optional[str] = Field(default=None, description="커스텀 이미지 이름")
    resources: ResourceLimits = Field(default_factory=ResourceLimits)
    env_vars: Optional[dict] = Field(default=None, description="환경 변수")
    ports: Optional[List[str]] = Field(default=None, description="포트 매핑 (예: ['8080:80'])")
    
    @model_validator(mode="after")
    def validate_custom_image(self) -> "ContainerConfig":
        """커스텀 이미지 검증"""
        if self.image == ContainerImage.CUSTOM and not self.custom_image:
            raise ValueError("custom_image is required when image is 'custom'")
        if self.custom_image and not re.match(r"^[\w.-]+(?::[\w.-]+)?$", self.custom_image):
            raise ValueError("Invalid custom image format")
        return self


class StartContainerRequest(BaseModel):
    """컨테이너 시작 요청"""
    config: Optional[ContainerConfig] = Field(default=None, description="새 설정 적용 (선택)")
    

class StopContainerRequest(BaseModel):
    """컨테이너 중지 요청"""
    timeout: int = Field(default=10, ge=1, le=300, description="타임아웃 (초)")
    force: bool = Field(default=False, description="강제 종료 여부")


class RestartContainerRequest(BaseModel):
    """컨테이너 재시작 요청"""
    timeout: int = Field(default=10, ge=1, le=300, description="타임아웃 (초)")


class ExecuteCommandRequest(BaseModel):
    """명령 실행 요청"""
    command: str = Field(..., min_length=1, max_length=10000, description="실행할 명령")
    working_dir: Optional[str] = Field(default=None, description="작업 디렉토리")
    env: Optional[dict] = Field(default=None, description="환경 변수")
    timeout: int = Field(default=60, ge=1, le=3600, description="타임아웃 (초)")
    
    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        # 기본적인 위험한 명령 차단
        dangerous_patterns = [
            r"rm\s+-rf\s+/\s*$",  # rm -rf /
            r"mkfs",
            r"dd\s+if=",
            r":(){:\|:&};:",  # fork bomb
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Potentially dangerous command blocked")
        return v
    
    @field_validator("working_dir")
    @classmethod
    def validate_working_dir(cls, v: Optional[str]) -> Optional[str]:
        if v and ".." in v:
            raise ValueError("Path traversal is not allowed")
        return v


class ContainerStatusResponse(BaseModel):
    """컨테이너 상태 응답"""
    workspace_id: str = Field(..., alias="workspaceId")
    container_id: Optional[str] = Field(default=None, alias="containerId")
    status: ContainerStatus
    image: Optional[str] = None
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    resources: Optional[ResourceLimits] = None
    cpu_usage_percent: Optional[float] = Field(default=None, alias="cpuUsagePercent")
    memory_usage_mb: Optional[int] = Field(default=None, alias="memoryUsageMb")
    
    class Config:
        populate_by_name = True


class ContainerLogsResponse(BaseModel):
    """컨테이너 로그 응답"""
    workspace_id: str = Field(..., alias="workspaceId")
    logs: str
    since: Optional[str] = None
    until: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ExecuteCommandResponse(BaseModel):
    """명령 실행 응답"""
    exit_code: int = Field(..., alias="exitCode")
    stdout: str
    stderr: str
    duration_ms: int = Field(..., alias="durationMs")
    
    class Config:
        populate_by_name = True


class ContainerActionResponse(BaseModel):
    """컨테이너 액션 응답"""
    success: bool
    message: str
    workspace_id: str = Field(..., alias="workspaceId")
    container_id: Optional[str] = Field(default=None, alias="containerId")
    
    class Config:
        populate_by_name = True
