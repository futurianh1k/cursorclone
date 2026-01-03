"""
IDE 컨테이너 관리 Pydantic 모델
브라우저 기반 VS Code (code-server) 프로비저닝을 위한 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class IDEContainerStatus(str, Enum):
    """IDE 컨테이너 상태"""
    PENDING = "pending"           # 생성 대기 중
    STARTING = "starting"         # 시작 중
    RUNNING = "running"           # 실행 중
    STOPPING = "stopping"         # 종료 중
    STOPPED = "stopped"           # 종료됨
    ERROR = "error"               # 오류


class IDEType(str, Enum):
    """IDE 타입"""
    CODE_SERVER = "code-server"   # 브라우저 기반 VS Code
    JUPYTER = "jupyter"           # Jupyter Notebook
    THEIA = "theia"               # Eclipse Theia


class IDEContainerConfig(BaseModel):
    """IDE 컨테이너 설정"""
    cpu_limit: str = Field(default="2", alias="cpuLimit", description="CPU 제한 (cores)")
    memory_limit: str = Field(default="4Gi", alias="memoryLimit", description="메모리 제한")
    storage_size: str = Field(default="10Gi", alias="storageSize", description="스토리지 크기")
    gpu_enabled: bool = Field(default=False, alias="gpuEnabled", description="GPU 사용 여부")
    extensions: Optional[List[str]] = Field(default=None, description="사전 설치할 VS Code 확장")
    environment: Optional[dict] = Field(default=None, description="환경 변수")
    
    class Config:
        populate_by_name = True


class CreateIDEContainerRequest(BaseModel):
    """IDE 컨테이너 생성 요청"""
    workspace_id: str = Field(..., alias="workspaceId", description="워크스페이스 ID")
    ide_type: IDEType = Field(default=IDEType.CODE_SERVER, alias="ideType")
    config: Optional[IDEContainerConfig] = Field(default=None, description="컨테이너 설정")
    
    class Config:
        populate_by_name = True


class IDEContainerResponse(BaseModel):
    """IDE 컨테이너 응답"""
    container_id: str = Field(..., alias="containerId")
    workspace_id: str = Field(..., alias="workspaceId")
    user_id: str = Field(..., alias="userId")
    ide_type: IDEType = Field(..., alias="ideType")
    status: IDEContainerStatus
    url: Optional[str] = Field(default=None, description="IDE 접속 URL")
    internal_url: Optional[str] = Field(default=None, alias="internalUrl", description="내부 URL")
    port: Optional[int] = Field(default=None, description="할당된 포트")
    created_at: str = Field(..., alias="createdAt")
    last_accessed: Optional[str] = Field(default=None, alias="lastAccessed")
    config: Optional[IDEContainerConfig] = None
    
    class Config:
        populate_by_name = True


class IDEContainerListResponse(BaseModel):
    """IDE 컨테이너 목록 응답"""
    containers: List[IDEContainerResponse]
    total: int


class StartIDEContainerResponse(BaseModel):
    """IDE 컨테이너 시작 응답"""
    container_id: str = Field(..., alias="containerId")
    status: IDEContainerStatus
    url: str = Field(..., description="IDE 접속 URL")
    token: Optional[str] = Field(default=None, description="접속 토큰 (필요한 경우)")
    expires_at: Optional[str] = Field(default=None, alias="expiresAt", description="세션 만료 시간")
    
    class Config:
        populate_by_name = True


class StopIDEContainerResponse(BaseModel):
    """IDE 컨테이너 종료 응답"""
    container_id: str = Field(..., alias="containerId")
    status: IDEContainerStatus
    message: str
    
    class Config:
        populate_by_name = True


class IDESessionInfo(BaseModel):
    """IDE 세션 정보"""
    session_id: str = Field(..., alias="sessionId")
    container_id: str = Field(..., alias="containerId")
    user_id: str = Field(..., alias="userId")
    started_at: str = Field(..., alias="startedAt")
    last_activity: str = Field(..., alias="lastActivity")
    is_active: bool = Field(default=True, alias="isActive")
    
    class Config:
        populate_by_name = True


class IDEHealthResponse(BaseModel):
    """IDE 서비스 상태 응답"""
    total_containers: int = Field(..., alias="totalContainers")
    running_containers: int = Field(..., alias="runningContainers")
    available_capacity: int = Field(..., alias="availableCapacity")
    avg_cpu_usage: float = Field(default=0.0, alias="avgCpuUsage")
    avg_memory_usage: float = Field(default=0.0, alias="avgMemoryUsage")
    
    class Config:
        populate_by_name = True
