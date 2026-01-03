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
    UBUNTU_DEV = "cursor-workspace-ubuntu:24.04"  # Ubuntu 24.04 기반 개발 환경 (권장)
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


# ============================================================
# SSH 관련 모델
# ============================================================

class SSHConnectionInfo(BaseModel):
    """SSH 연결 정보"""
    host: str = Field(..., description="SSH 서버 호스트 (IP 또는 도메인)")
    port: int = Field(..., description="SSH 포트")
    username: str = Field(default="developer", description="SSH 사용자명")
    auth_type: str = Field(default="key", description="인증 방식: key, password")
    private_key_path: Optional[str] = Field(default=None, alias="privateKeyPath", description="개인키 경로 (로컬)")
    
    class Config:
        populate_by_name = True


class SSHConnectionResponse(BaseModel):
    """SSH 연결 정보 응답"""
    workspace_id: str = Field(..., alias="workspaceId")
    connection: SSHConnectionInfo
    status: str = Field(default="available", description="연결 상태: available, unavailable")
    ssh_command: str = Field(..., alias="sshCommand", description="SSH 접속 명령어")
    vscode_remote_uri: str = Field(..., alias="vscodeRemoteUri", description="VS Code Remote SSH URI")
    
    class Config:
        populate_by_name = True


class SetupSSHKeyRequest(BaseModel):
    """SSH 키 설정 요청"""
    public_key: str = Field(..., alias="publicKey", min_length=20, description="SSH 공개키")
    
    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, v: str) -> str:
        # SSH 키 형식 검증
        if not v.startswith(("ssh-rsa", "ssh-ed25519", "ecdsa-sha2")):
            raise ValueError("Invalid SSH public key format. Must start with ssh-rsa, ssh-ed25519, or ecdsa-sha2")
        return v.strip()
    
    class Config:
        populate_by_name = True


class SetupSSHPasswordRequest(BaseModel):
    """SSH 비밀번호 설정 요청"""
    password: str = Field(..., min_length=8, max_length=128, description="SSH 비밀번호")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # 비밀번호 복잡도 검증
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class SSHKeyResponse(BaseModel):
    """SSH 키 설정 응답"""
    success: bool
    message: str
    workspace_id: str = Field(..., alias="workspaceId")
    fingerprint: Optional[str] = None
    
    class Config:
        populate_by_name = True


class GenerateSSHKeyRequest(BaseModel):
    """SSH 키 쌍 생성 요청"""
    key_type: str = Field(default="ed25519", description="키 타입: rsa, ed25519")
    comment: Optional[str] = Field(default=None, description="키 주석 (이메일 등)")
    
    @field_validator("key_type")
    @classmethod
    def validate_key_type(cls, v: str) -> str:
        if v not in ["rsa", "ed25519"]:
            raise ValueError("Key type must be 'rsa' or 'ed25519'")
        return v


class GenerateSSHKeyResponse(BaseModel):
    """SSH 키 쌍 생성 응답"""
    success: bool
    message: str
    public_key: str = Field(..., alias="publicKey")
    private_key: str = Field(..., alias="privateKey", description="⚠️ 이 값은 다시 조회할 수 없습니다")
    fingerprint: str
    
    class Config:
        populate_by_name = True
