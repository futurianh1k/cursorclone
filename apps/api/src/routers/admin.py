"""
관리자 API 라우터
인프라 서버 관리 및 워크스페이스 배치

RBAC 권한:
- admin: 모든 관리 기능
- manager: 서버 조회만 가능
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..models import (
    RegisterServerRequest,
    ServerResponse,
    TestConnectionResponse,
    PlacementRequest,
    ErrorResponse,
    ServerType,
    ServerStatus,
    AuthType,
)
from ..db import get_db, InfrastructureServerModel, ServerCredentialModel, UserModel
from ..services.auth_service import (
    ssh_auth_service,
    mtls_auth_service,
    api_key_auth_service,
)
from ..services.placement_service import PlacementService
from ..services.rbac_service import (
    require_permission,
    require_admin,
    Permission,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/servers",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Server already exists"},
    },
    summary="인프라 서버 등록",
    description="새로운 인프라 서버를 등록합니다.",
)
async def register_server(
    request: RegisterServerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SERVER_MANAGE)),
):
    """
    인프라 서버 등록
    
    인증 정보는 암호화하여 저장됩니다.
    """
    # 중복 확인
    from sqlalchemy import select
    existing = await db.execute(
        select(InfrastructureServerModel).where(InfrastructureServerModel.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Server already exists", "code": "SERVER_EXISTS"},
        )
    
    # 서버 생성
    server = InfrastructureServerModel(
        name=request.name,
        host=request.host,
        port=request.port,
        type=request.type.value,
        region=request.region,
        zone=request.zone,
        max_workspaces=request.max_workspaces,
        status="active",
    )
    db.add(server)
    await db.flush()
    
    # 인증 정보 저장
    auth_type = request.auth.get("type")
    if auth_type == "ssh_key":
        private_key = request.auth.get("private_key")
        public_key = request.auth.get("public_key")
        
        if not private_key or not public_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "SSH key pair required", "code": "INVALID_AUTH"},
            )
        
        # 비공개키 암호화
        encrypted_private_key = ssh_auth_service.encrypt_private_key(private_key)
        
        # 공개키 지문 생성
        fingerprint = ssh_auth_service.get_key_fingerprint(public_key)
        
        credential = ServerCredentialModel(
            server_id=server.id,
            auth_type="ssh_key",
            credential_name="default",
            encrypted_private_key=encrypted_private_key,
            public_key=public_key,
            key_fingerprint=fingerprint,
        )
        db.add(credential)
    
    elif auth_type == "api_key":
        api_key = request.auth.get("api_key")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "API key required", "code": "INVALID_AUTH"},
            )
        
        encrypted_api_key = ssh_auth_service.encryption.encrypt(api_key)
        
        credential = ServerCredentialModel(
            server_id=server.id,
            auth_type="api_key",
            credential_name="default",
            encrypted_api_key=encrypted_api_key,
        )
        db.add(credential)
    
    elif auth_type == "mtls":
        certificate = request.auth.get("certificate")
        private_key = request.auth.get("private_key")
        
        if not certificate or not private_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Certificate and private key required", "code": "INVALID_AUTH"},
            )
        
        encrypted_cert, encrypted_key = mtls_auth_service.encrypt_certificate(certificate, private_key)
        
        # 인증서 유효성 검증
        cert_info = mtls_auth_service.validate_certificate(certificate)
        expires_at = None
        if cert_info.get("valid"):
            from datetime import datetime
            expires_at = datetime.fromisoformat(cert_info["expires_at"].replace("Z", "+00:00"))
        
        credential = ServerCredentialModel(
            server_id=server.id,
            auth_type="mtls",
            credential_name="default",
            encrypted_certificate=encrypted_cert,
            encrypted_private_key=encrypted_key,
            expires_at=expires_at,
        )
        db.add(credential)
    
    await db.commit()
    await db.refresh(server)
    
    return ServerResponse(
        serverId=str(server.id),
        name=server.name,
        host=server.host,
        port=server.port,
        type=ServerType(server.type),
        region=server.region,
        zone=server.zone,
        status=ServerStatus(server.status),
        max_workspaces=server.max_workspaces,
        current_workspaces=server.current_workspaces,
        cpu_capacity=float(server.cpu_capacity) if server.cpu_capacity else None,
        memory_capacity=server.memory_capacity,
        disk_capacity=server.disk_capacity,
        cpu_usage=float(server.cpu_usage) if server.cpu_usage else None,
        memory_usage=server.memory_usage,
        disk_usage=server.disk_usage,
        last_health_check=server.last_health_check.isoformat() if server.last_health_check else None,
    )


@router.get(
    "/servers",
    response_model=List[ServerResponse],
    summary="서버 목록 조회",
    description="등록된 인프라 서버 목록을 조회합니다.",
)
async def list_servers(
    status_filter: Optional[ServerStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.ADMIN_READ)),
):
    """서버 목록 조회"""
    from sqlalchemy import select
    
    query = select(InfrastructureServerModel)
    if status_filter:
        query = query.where(InfrastructureServerModel.status == status_filter.value)
    
    result = await db.execute(query)
    servers = result.scalars().all()
    
    return [
        ServerResponse(
            serverId=str(s.id),
            name=s.name,
            host=s.host,
            port=s.port,
            type=ServerType(s.type),
            region=s.region,
            zone=s.zone,
            status=ServerStatus(s.status),
            max_workspaces=s.max_workspaces,
            current_workspaces=s.current_workspaces,
            cpu_capacity=float(s.cpu_capacity) if s.cpu_capacity else None,
            memory_capacity=s.memory_capacity,
            disk_capacity=s.disk_capacity,
            cpu_usage=float(s.cpu_usage) if s.cpu_usage else None,
            memory_usage=s.memory_usage,
            disk_usage=s.disk_usage,
            last_health_check=s.last_health_check.isoformat() if s.last_health_check else None,
        )
        for s in servers
    ]


@router.post(
    "/servers/{server_id}/test",
    response_model=TestConnectionResponse,
    summary="서버 연결 테스트",
    description="서버 연결 및 리소스 정보를 테스트합니다.",
)
async def test_server_connection(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SERVER_MANAGE)),
):
    """서버 연결 테스트"""
    from sqlalchemy import select
    
    server = await db.execute(
        select(InfrastructureServerModel).where(InfrastructureServerModel.id == server_id)
    )
    server = server.scalar_one_or_none()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Server not found", "code": "SERVER_NOT_FOUND"},
        )
    
    # TODO: 실제 연결 테스트 구현
    # - SSH 연결 테스트
    # - Kubernetes API 연결 테스트
    # - 리소스 정보 수집
    
    return TestConnectionResponse(
        success=True,
        message="Connection test successful (stub)",
        resource_info={
            "cpu_cores": 8,
            "memory_gb": 32,
            "disk_gb": 500,
        },
    )


@router.post(
    "/workspaces/{workspace_id}/place",
    response_model=dict,
    summary="워크스페이스 배치",
    description="워크스페이스를 특정 서버에 배치합니다.",
)
async def place_workspace(
    workspace_id: str,
    request: PlacementRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SERVER_MANAGE)),
):
    """워크스페이스 배치"""
    placement_service = PlacementService(db)
    
    # 서버 선택 또는 지정
    if request.server_id:
        # 지정된 서버 사용
        from sqlalchemy import select
        server = await db.execute(
            select(InfrastructureServerModel).where(InfrastructureServerModel.id == UUID(request.server_id))
        )
        server = server.scalar_one_or_none()
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Server not found", "code": "SERVER_NOT_FOUND"},
            )
    else:
        # 정책 기반 자동 선택
        server = await placement_service.select_server(
            policy=request.policy.value if request.policy else "least_loaded",
            region=request.region,
        )
        if not server:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "No available server", "code": "NO_SERVER_AVAILABLE"},
            )
    
    # 워크스페이스 배치
    placement = await placement_service.place_workspace(
        workspace_id=workspace_id,
        server_id=server.id,
        policy=request.policy.value if request.policy else "auto",
    )
    
    return {
        "workspace_id": workspace_id,
        "server_id": str(server.id),
        "server_name": server.name,
        "placement_id": str(placement.id) if hasattr(placement, "id") else None,
    }
