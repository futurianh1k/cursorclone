"""
데이터베이스 모델 정의
멀티 테넌트 및 대규모 스케일링을 위한 스키마
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .connection import Base


class OrganizationModel(Base):
    """조직 테이블"""
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    max_workspaces = Column(Integer, default=100)
    max_users = Column(Integer, default=500)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    users = relationship("UserModel", back_populates="organization")
    workspaces = relationship("WorkspaceModel", back_populates="organization")


class UserModel(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    org_id = Column(String(100), ForeignKey("organizations.org_id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255))  # bcrypt 해시 (온프레미스에서는 SSO 사용 시 NULL 가능)
    role = Column(String(50), nullable=False, default="developer")  # admin, developer, viewer
    avatar_url = Column(String(500))  # 프로필 이미지 URL
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # 2FA 관련 필드
    totp_enabled = Column(Boolean, default=False)  # 2FA 활성화 여부
    totp_secret = Column(Text)  # TOTP 시크릿 (암호화됨)
    totp_secret_pending = Column(Text)  # 설정 중인 시크릿 (확인 전)
    backup_code_hashes = Column(JSONB)  # 백업 코드 해시 목록
    backup_code_hashes_pending = Column(JSONB)  # 설정 중인 백업 코드 해시
    
    # 관계
    organization = relationship("OrganizationModel", back_populates="users")
    workspaces = relationship("WorkspaceModel", back_populates="owner")
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")


class ProjectModel(Base):
    """프로젝트 테이블 (1 Project : N Workspaces)"""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    owner_id = Column(String(100), ForeignKey("users.user_id"), nullable=False, index=True)
    org_id = Column(String(100), ForeignKey("organizations.org_id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    owner = relationship("UserModel")
    organization = relationship("OrganizationModel")
    workspaces = relationship("WorkspaceModel", back_populates="project")

    __table_args__ = (
        Index("idx_project_owner_created", "owner_id", "created_at"),
        Index("idx_project_org_created", "org_id", "created_at"),
    )


class WorkspaceModel(Base):
    """워크스페이스 테이블"""
    __tablename__ = "workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(100), unique=True, nullable=False, index=True)
    project_id = Column(String(100), ForeignKey("projects.project_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(100), ForeignKey("users.user_id"), nullable=False, index=True)
    org_id = Column(String(100), ForeignKey("organizations.org_id"), nullable=True, index=True)
    container_id = Column(String(255))  # Kubernetes Pod 이름 또는 Docker 컨테이너 ID
    status = Column(String(50), nullable=False, default="stopped", index=True)  # running, stopped, deleted
    root_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True))  # 마지막 접근 시간 (자동 정지용)
    
    # 관계
    owner = relationship("UserModel", back_populates="workspaces")
    organization = relationship("OrganizationModel", back_populates="workspaces")
    project = relationship("ProjectModel", back_populates="workspaces")
    
    # 인덱스 (최적화됨)
    __table_args__ = (
        # 소유자별 워크스페이스 조회 (상태 필터링)
        Index("idx_workspace_owner_status", "owner_id", "status"),
        # 조직별 워크스페이스 조회 (상태 필터링)
        Index("idx_workspace_org_status", "org_id", "status"),
        # 프로젝트별 워크스페이스 조회 (상태 포함)
        Index("idx_workspace_project_status", "project_id", "status"),
        # 마지막 접근 시간 기반 조회 (상태 포함 - 자동 정지용)
        Index("idx_workspace_last_accessed_status", "status", "last_accessed_at"),
        # 생성일 기반 정렬 (소유자별)
        Index("idx_workspace_owner_created", "owner_id", "created_at"),
    )


class WorkspaceResourceModel(Base):
    """워크스페이스 리소스 사용량"""
    __tablename__ = "workspace_resources"
    
    workspace_id = Column(String(100), ForeignKey("workspaces.workspace_id"), primary_key=True)
    cpu_usage = Column(String(20))  # "1.5" (cores)
    memory_usage = Column(BigInteger)  # bytes
    disk_usage = Column(BigInteger)  # bytes
    network_io = Column(BigInteger)  # bytes
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLogModel(Base):
    """감사 로그 테이블 (해시만 저장)"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # explain, rewrite, patch_apply 등
    instruction_hash = Column(String(64))  # SHA-256 해시
    response_hash = Column(String(64))  # SHA-256 해시
    patch_hash = Column(String(64))  # SHA-256 해시 (patch 적용 시)
    tokens_used = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 인덱스 (최적화됨)
    __table_args__ = (
        # 사용자별 시간순 조회
        Index("idx_audit_user_time", "user_id", "timestamp"),
        # 워크스페이스별 시간순 조회
        Index("idx_audit_workspace_time", "workspace_id", "timestamp"),
        # 액션별 조회 (통계, 필터링용)
        Index("idx_audit_action", "action"),
        # 액션 + 시간 복합 인덱스 (액션별 시간순 조회)
        Index("idx_audit_action_time", "action", "timestamp"),
        # 사용자 + 액션 복합 인덱스 (사용자별 액션 통계)
        Index("idx_audit_user_action", "user_id", "action"),
    )


class InfrastructureServerModel(Base):
    """인프라 서버 테이블"""
    __tablename__ = "infrastructure_servers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=22)
    type = Column(String(50), nullable=False)  # kubernetes, docker, ssh
    region = Column(String(100), index=True)
    zone = Column(String(100))
    status = Column(String(50), nullable=False, default="active", index=True)  # active, inactive, maintenance
    max_workspaces = Column(Integer, default=100)
    current_workspaces = Column(Integer, default=0)
    cpu_capacity = Column(Numeric(10, 2))  # 총 CPU cores
    memory_capacity = Column(BigInteger)  # 총 메모리 (bytes)
    disk_capacity = Column(BigInteger)  # 총 디스크 (bytes)
    cpu_usage = Column(Numeric(10, 2), default=0)
    memory_usage = Column(BigInteger, default=0)
    disk_usage = Column(BigInteger, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_health_check = Column(DateTime(timezone=True))
    
    # 관계
    credentials = relationship("ServerCredentialModel", back_populates="server", cascade="all, delete-orphan")
    placements = relationship("WorkspacePlacementModel", back_populates="server")
    
    # 인덱스
    __table_args__ = (
        Index("idx_server_status", "status"),
        Index("idx_server_region", "region"),
    )


class ServerCredentialModel(Base):
    """서버 인증 정보 테이블 (암호화 저장)"""
    __tablename__ = "server_credentials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(UUID(as_uuid=True), ForeignKey("infrastructure_servers.id", ondelete="CASCADE"), nullable=False)
    auth_type = Column(String(50), nullable=False)  # ssh_key, mtls, api_key
    credential_name = Column(String(255), nullable=False)
    # 암호화된 필드들
    encrypted_private_key = Column(Text)  # SSH private key 또는 mTLS key (암호화)
    encrypted_certificate = Column(Text)  # mTLS certificate (암호화)
    encrypted_api_key = Column(Text)  # API key (암호화)
    public_key = Column(Text)  # SSH public key (평문 가능)
    # 메타데이터
    key_fingerprint = Column(String(64))  # SSH 키 지문
    expires_at = Column(DateTime(timezone=True))  # 인증서 만료일
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    server = relationship("InfrastructureServerModel", back_populates="credentials")
    
    # 제약조건
    __table_args__ = (
        Index("idx_credential_server_type", "server_id", "auth_type"),
    )


class WorkspacePlacementModel(Base):
    """워크스페이스 배치 정보"""
    __tablename__ = "workspace_placements"
    
    workspace_id = Column(String(100), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), primary_key=True)
    server_id = Column(UUID(as_uuid=True), ForeignKey("infrastructure_servers.id"), nullable=False, index=True)
    container_id = Column(String(255))  # Pod 이름 또는 컨테이너 ID
    placement_policy = Column(String(50))  # auto, manual, region_based
    placed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    server = relationship("InfrastructureServerModel", back_populates="placements")


class PlacementPolicyModel(Base):
    """배치 정책 설정"""
    __tablename__ = "placement_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    policy_type = Column(String(50), nullable=False)  # round_robin, least_loaded, region_based
    enabled = Column(Boolean, default=True)
    config = Column(JSONB)  # 정책별 설정 (예: 지역 우선순위, 리소스 가중치)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserSessionModel(Base):
    """사용자 세션 테이블"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_address = Column(String(45))  # IPv4 또는 IPv6
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    user = relationship("UserModel", back_populates="sessions")
    
    __table_args__ = (
        Index("idx_session_token", "session_token"),
        Index("idx_session_expires", "expires_at"),
    )
