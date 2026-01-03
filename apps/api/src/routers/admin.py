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
    
    # 서버 타입에 따른 연결 테스트
    server_type = server.type
    host = server.host
    port = server.port
    
    resource_info = {}
    success = False
    message = ""
    
    try:
        if server_type == "ssh" or server_type == "docker":
            # SSH 연결 테스트
            success, message, resource_info = await _test_ssh_connection(
                server.id, host, port, db
            )
        elif server_type == "kubernetes":
            # Kubernetes API 연결 테스트
            success, message, resource_info = await _test_kubernetes_connection(
                server.id, host, port, db
            )
        else:
            # 기본: TCP 포트 연결 테스트
            import asyncio
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0
                )
                writer.close()
                await writer.wait_closed()
                success = True
                message = f"TCP connection to {host}:{port} successful"
            except asyncio.TimeoutError:
                message = f"Connection to {host}:{port} timed out"
            except Exception as e:
                message = f"Connection failed: {str(e)}"
        
        # 마지막 헬스체크 시간 업데이트
        if success:
            from datetime import datetime, timezone
            server.last_health_check = datetime.now(timezone.utc)
            await db.commit()
    
    except Exception as e:
        message = f"Connection test error: {str(e)}"
        logger.error(f"Connection test failed for server {server_id}: {e}")
    
    return TestConnectionResponse(
        success=success,
        message=message,
        resource_info=resource_info if resource_info else None,
    )


async def _test_ssh_connection(
    server_id: UUID, host: str, port: int, db: AsyncSession
) -> tuple[bool, str, dict]:
    """
    SSH 연결 테스트 및 리소스 정보 수집
    
    paramiko 라이브러리 사용
    """
    try:
        import paramiko
    except ImportError:
        return False, "paramiko library not installed", {}
    
    # 서버 인증 정보 조회
    from sqlalchemy import select
    from ..db.models import ServerCredentialModel
    
    cred_result = await db.execute(
        select(ServerCredentialModel).where(
            ServerCredentialModel.server_id == server_id,
            ServerCredentialModel.auth_type == "ssh_key"
        )
    )
    credential = cred_result.scalar_one_or_none()
    
    if not credential:
        return False, "No SSH credentials found for server", {}
    
    try:
        # SSH 클라이언트 설정
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 키 복호화 (암호화된 경우)
        # TODO: credential에서 암호화된 키 복호화
        private_key = credential.encrypted_private_key  # 실제로는 복호화 필요
        
        if private_key:
            import io
            key_file = io.StringIO(private_key)
            pkey = paramiko.RSAKey.from_private_key(key_file)
            
            client.connect(
                hostname=host,
                port=port,
                username="ubuntu",  # TODO: credential에서 가져오기
                pkey=pkey,
                timeout=10,
            )
        else:
            return False, "SSH private key not found", {}
        
        # 리소스 정보 수집
        resource_info = {}
        
        # CPU 정보
        stdin, stdout, stderr = client.exec_command("nproc")
        cpu_cores = stdout.read().decode().strip()
        resource_info["cpu_cores"] = int(cpu_cores) if cpu_cores.isdigit() else 0
        
        # 메모리 정보 (GB)
        stdin, stdout, stderr = client.exec_command("free -g | grep Mem | awk '{print $2}'")
        memory_gb = stdout.read().decode().strip()
        resource_info["memory_gb"] = int(memory_gb) if memory_gb.isdigit() else 0
        
        # 디스크 정보 (GB)
        stdin, stdout, stderr = client.exec_command("df -BG / | tail -1 | awk '{print $2}'")
        disk_str = stdout.read().decode().strip().replace("G", "")
        resource_info["disk_gb"] = int(disk_str) if disk_str.isdigit() else 0
        
        client.close()
        
        return True, "SSH connection successful", resource_info
        
    except paramiko.AuthenticationException:
        return False, "SSH authentication failed", {}
    except paramiko.SSHException as e:
        return False, f"SSH error: {str(e)}", {}
    except Exception as e:
        return False, f"SSH connection failed: {str(e)}", {}


async def _test_kubernetes_connection(
    server_id: UUID, host: str, port: int, db: AsyncSession
) -> tuple[bool, str, dict]:
    """
    Kubernetes API 연결 테스트
    
    kubernetes 라이브러리 사용
    """
    try:
        from kubernetes import client, config
        from kubernetes.client.rest import ApiException
    except ImportError:
        return False, "kubernetes library not installed", {}
    
    # 서버 인증 정보 조회
    from sqlalchemy import select
    from ..db.models import ServerCredentialModel
    
    cred_result = await db.execute(
        select(ServerCredentialModel).where(
            ServerCredentialModel.server_id == server_id,
            ServerCredentialModel.auth_type == "api_key"
        )
    )
    credential = cred_result.scalar_one_or_none()
    
    try:
        # API 클라이언트 설정
        configuration = client.Configuration()
        configuration.host = f"https://{host}:{port}"
        
        if credential and credential.encrypted_api_key:
            # TODO: API 키 복호화
            configuration.api_key = {"authorization": f"Bearer {credential.encrypted_api_key}"}
        
        # SSL 인증서 검증 비활성화 (PoC용)
        configuration.verify_ssl = False
        
        api_client = client.ApiClient(configuration)
        v1 = client.CoreV1Api(api_client)
        
        # 노드 정보 조회
        nodes = v1.list_node(timeout_seconds=10)
        
        total_cpu = 0
        total_memory = 0
        
        for node in nodes.items:
            capacity = node.status.capacity
            if capacity:
                cpu = capacity.get("cpu", "0")
                memory = capacity.get("memory", "0Ki")
                
                total_cpu += int(cpu) if cpu.isdigit() else 0
                # Ki를 GB로 변환
                if memory.endswith("Ki"):
                    total_memory += int(memory[:-2]) // (1024 * 1024)
        
        resource_info = {
            "node_count": len(nodes.items),
            "total_cpu_cores": total_cpu,
            "total_memory_gb": total_memory,
        }
        
        return True, f"Kubernetes connection successful ({len(nodes.items)} nodes)", resource_info
        
    except ApiException as e:
        return False, f"Kubernetes API error: {e.reason}", {}
    except Exception as e:
        return False, f"Kubernetes connection failed: {str(e)}", {}


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


# ============================================================
# 사용자 선호도 API
# ============================================================

@router.get(
    "/preferences",
    summary="사용자 선호도 조회",
    description="현재 사용자의 선호도 설정을 조회합니다.",
)
async def get_user_preferences(
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """사용자 선호도 조회"""
    from ..services.user_preference_service import user_preference_service
    
    preferences = await user_preference_service.get_all_preferences(current_user.user_id)
    return preferences


@router.get(
    "/preferences/last-server",
    summary="마지막 선택 서버 조회",
    description="사용자가 마지막으로 선택한 서버 ID를 반환합니다.",
)
async def get_last_selected_server(
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """마지막 선택 서버 조회"""
    from ..services.user_preference_service import user_preference_service
    
    server_id = await user_preference_service.get_last_selected_server(current_user.user_id)
    
    if not server_id:
        return {"server_id": None, "message": "No server selected yet"}
    
    # 서버 정보 조회
    from sqlalchemy import select
    from ..db.connection import get_db_session
    
    async with get_db_session() as db:
        result = await db.execute(
            select(InfrastructureServerModel).where(
                InfrastructureServerModel.id == server_id
            )
        )
        server = result.scalar_one_or_none()
    
    if not server:
        return {"server_id": server_id, "server_name": None, "message": "Server not found"}
    
    return {
        "server_id": str(server.id),
        "server_name": server.name,
        "server_type": server.type,
        "server_status": server.status,
    }


@router.post(
    "/preferences/last-server",
    summary="마지막 선택 서버 설정",
    description="사용자의 마지막 선택 서버를 저장합니다.",
)
async def set_last_selected_server(
    server_id: UUID,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    """마지막 선택 서버 설정"""
    from ..services.user_preference_service import user_preference_service
    from sqlalchemy import select
    
    # 서버 존재 확인
    result = await db.execute(
        select(InfrastructureServerModel).where(
            InfrastructureServerModel.id == server_id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Server not found", "code": "SERVER_NOT_FOUND"},
        )
    
    await user_preference_service.set_last_selected_server(
        current_user.user_id,
        str(server_id),
    )
    
    return {
        "message": "Last selected server updated",
        "server_id": str(server_id),
    }


@router.get(
    "/preferences/recent-workspaces",
    summary="최근 사용 워크스페이스 조회",
    description="사용자의 최근 사용 워크스페이스 목록을 반환합니다.",
)
async def get_recent_workspaces(
    limit: int = 5,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """최근 사용 워크스페이스 조회"""
    from ..services.user_preference_service import user_preference_service
    
    workspace_ids = await user_preference_service.get_recent_workspaces(
        current_user.user_id,
        limit=min(limit, 20),
    )
    
    return {
        "workspaces": workspace_ids,
        "count": len(workspace_ids),
    }


@router.post(
    "/preferences/recent-workspaces",
    summary="최근 사용 워크스페이스 추가",
    description="워크스페이스를 최근 사용 목록에 추가합니다.",
)
async def add_recent_workspace(
    workspace_id: str,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """최근 사용 워크스페이스 추가"""
    from ..services.user_preference_service import user_preference_service
    
    await user_preference_service.add_recent_workspace(
        current_user.user_id,
        workspace_id,
    )
    
    return {
        "message": "Workspace added to recent list",
        "workspace_id": workspace_id,
    }
