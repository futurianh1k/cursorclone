"""
IDE 컨테이너 관리 라우터
브라우저 기반 VS Code (code-server) 프로비저닝 API

참조:
- code-server: https://github.com/coder/code-server
- Docker SDK for Python: https://docker-py.readthedocs.io/
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import Optional
import os
import uuid
import logging
from datetime import datetime, timezone
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Docker SDK (설치 필요: pip install docker)
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

from ..models.ide import (
    CreateIDEContainerRequest,
    IDEContainerResponse,
    IDEContainerListResponse,
    IDEContainerStatus,
    IDEType,
    IDEContainerConfig,
    StartIDEContainerResponse,
    StopIDEContainerResponse,
    IDEHealthResponse,
)
from ..db import UserModel
from ..db.connection import get_db
from ..db.models import WorkspaceModel
from ..services.rbac_service import get_current_user_optional, get_current_user

router = APIRouter(prefix="/api/ide", tags=["IDE"])

logger = logging.getLogger(__name__)

# ============================================================
# 설정
# ============================================================

# IDE 컨테이너 기본 설정
IDE_CONTAINER_IMAGE = os.getenv("IDE_CONTAINER_IMAGE", "cursor-poc-code-server:latest")
IDE_NETWORK = os.getenv("IDE_NETWORK", "cursor-network")
IDE_PORT_RANGE_START = int(os.getenv("IDE_PORT_RANGE_START", "9000"))
IDE_PORT_RANGE_END = int(os.getenv("IDE_PORT_RANGE_END", "9100"))
IDE_BASE_URL = os.getenv("IDE_BASE_URL", "http://localhost")
WORKSPACE_BASE_PATH = os.getenv("WORKSPACE_BASE_PATH", "/home/ubuntu/workspaces")

# In-memory 저장소 (PoC용, 실제 환경에서는 DB 사용)
_ide_containers: dict[str, dict] = {}
_used_ports: set[int] = set()


# ============================================================
# Helper Functions
# ============================================================

def get_docker_client():
    """Docker 클라이언트 반환"""
    if not DOCKER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Docker SDK가 설치되지 않았습니다. pip install docker"
        )
    try:
        return docker.from_env()
    except Exception as e:
        logger.error(f"Docker 연결 실패: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Docker 데몬에 연결할 수 없습니다: {str(e)}"
        )


def allocate_port() -> int:
    """사용 가능한 포트 할당"""
    for port in range(IDE_PORT_RANGE_START, IDE_PORT_RANGE_END):
        if port not in _used_ports:
            _used_ports.add(port)
            return port
    raise HTTPException(
        status_code=503,
        detail="사용 가능한 포트가 없습니다. 일부 IDE를 종료해주세요."
    )


def release_port(port: int):
    """포트 해제"""
    _used_ports.discard(port)


def get_user_id_from_model(user: Optional[UserModel]) -> str:
    """UserModel에서 사용자 ID 추출"""
    if user:
        return user.user_id
    return "user-default"


def get_user_id_from_header(request: Request) -> str:
    """요청 헤더에서 사용자 ID 추출 (폴백용)"""
    return request.headers.get("X-User-ID", "user-default")


# ============================================================
# Docker 컨테이너 스캔 (기존 컨테이너 복구)
# ============================================================

_last_scan_time = 0

def scan_existing_containers():
    """
    기존에 실행 중인 IDE 컨테이너를 스캔하여 in-memory 저장소에 추가
    목록 조회 시 호출 (최소 5초 간격)
    """
    global _last_scan_time
    import time
    
    # 5초 내에 스캔했으면 스킵
    current_time = time.time()
    if current_time - _last_scan_time < 5:
        return
    _last_scan_time = current_time
    
    if not DOCKER_AVAILABLE:
        logger.debug("Docker SDK not available, skipping container scan")
        return
    
    try:
        client = docker.from_env()
        # cursor.type=ide 레이블이 있는 컨테이너만 조회
        containers = client.containers.list(
            all=True,  # 중지된 컨테이너도 포함
            filters={"label": "cursor.type=ide"}
        )
        
        logger.info(f"Docker 컨테이너 스캔: {len(containers)}개 발견")
        
        for container in containers:
            container_id = container.name
            
            # 레이블에서 정보 추출
            labels = container.labels
            workspace_id = labels.get("cursor.workspace_id", "unknown")
            
            # 포트 정보 추출
            port = None
            if container.status == "running":
                ports = container.ports
                if "8080/tcp" in ports and ports["8080/tcp"]:
                    port = int(ports["8080/tcp"][0]["HostPort"])
                    _used_ports.add(port)
            
            # 상태 결정
            status = IDEContainerStatus.STOPPED.value
            if container.status == "running":
                status = IDEContainerStatus.RUNNING.value
            elif container.status == "exited":
                status = IDEContainerStatus.STOPPED.value
            
            # 이미 저장소에 있으면 상태만 업데이트
            if container_id in _ide_containers:
                _ide_containers[container_id]["status"] = status
                if port:
                    _ide_containers[container_id]["port"] = port
                    _ide_containers[container_id]["url"] = f"{IDE_BASE_URL}:{port}"
                continue
            
            # 컨테이너 정보 저장
            container_info = {
                "container_id": container_id,
                "workspace_id": workspace_id,
                "user_id": "user-default",  # 기존 컨테이너는 사용자 정보 없음
                "ide_type": IDEType.CODE_SERVER.value,
                "status": status,
                "url": f"{IDE_BASE_URL}:{port}" if port else None,
                "internal_url": f"http://{container_id}:8080",
                "port": port,
                "created_at": container.attrs.get("Created", datetime.now(timezone.utc).isoformat()),
                "last_accessed": None,
                "config": IDEContainerConfig().model_dump(),
            }
            _ide_containers[container_id] = container_info
            logger.info(f"기존 IDE 컨테이너 발견: {container_id}, workspace: {workspace_id}, status: {status}, port: {port}")
    
    except Exception as e:
        logger.warning(f"기존 컨테이너 스캔 실패: {e}")


# ============================================================
# API Endpoints
# ============================================================

@router.post("/containers", response_model=IDEContainerResponse)
async def create_ide_container(
    request: CreateIDEContainerRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user),
):
    """
    새 IDE 컨테이너 생성
    
    워크스페이스에 대한 브라우저 기반 VS Code (code-server) 컨테이너를 생성합니다.
    
    인증 필수: JWT 토큰 (Authorization: Bearer ...)
    """
    user_id = current_user.user_id
    # 컨테이너 이름: ide-{workspace_id} 형식으로 직관적으로 생성
    container_id = f"ide-{request.workspace_id}"
    
    # 기존 컨테이너 확인
    existing = next(
        (c for c in _ide_containers.values() 
         if c["workspace_id"] == request.workspace_id 
         and c["user_id"] == user_id
         and c["status"] not in [IDEContainerStatus.STOPPED, IDEContainerStatus.ERROR]),
        None
    )
    if existing:
        logger.info(f"기존 IDE 컨테이너 반환: {existing['container_id']}")
        return IDEContainerResponse(**existing)
    
    # 포트 할당
    port = allocate_port()
    
    # 설정 기본값
    config = request.config or IDEContainerConfig()
    
    # 컨테이너 정보 저장
    now = datetime.now(timezone.utc).isoformat()
    container_info = {
        "container_id": container_id,
        "workspace_id": request.workspace_id,
        "user_id": user_id,
        "ide_type": request.ide_type.value,
        "status": IDEContainerStatus.PENDING.value,
        "url": None,
        "internal_url": None,
        "port": port,
        "created_at": now,
        "last_accessed": None,
        "config": config.model_dump(),
    }
    _ide_containers[container_id] = container_info
    
    # 백그라운드에서 컨테이너 실제 생성
    background_tasks.add_task(
        _create_container_async,
        container_id,
        request.workspace_id,
        port,
        config,
    )
    
    logger.info(f"IDE 컨테이너 생성 시작: {container_id}, workspace: {request.workspace_id}")
    
    return IDEContainerResponse(**container_info)


async def _create_container_async(
    container_id: str,
    workspace_id: str,
    port: int,
    config: IDEContainerConfig,
):
    """비동기 컨테이너 생성"""
    try:
        _ide_containers[container_id]["status"] = IDEContainerStatus.STARTING.value
        
        # Docker 클라이언트
        if DOCKER_AVAILABLE:
            client = docker.from_env()
            
            # 워크스페이스 경로
            workspace_path = os.path.join(WORKSPACE_BASE_PATH, workspace_id)
            
            # code-server 컨테이너 생성
            container = client.containers.run(
                IDE_CONTAINER_IMAGE,
                detach=True,
                name=container_id,
                ports={"8080/tcp": port},
                volumes={
                    workspace_path: {"bind": "/home/coder/project", "mode": "rw"}
                },
                environment={
                    "PASSWORD": "",  # 비밀번호 비활성화 (Keycloak 인증 사용)
                    "WORKSPACE_ID": workspace_id,
                },
                network=IDE_NETWORK,
                mem_limit=config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(float(config.cpu_limit) * 100000),
                labels={
                    "cursor.workspace_id": workspace_id,
                    "cursor.container_id": container_id,
                    "cursor.type": "ide",
                },
            )
            
            # 시작 대기 (최대 30초)
            for _ in range(30):
                container.reload()
                if container.status == "running":
                    break
                await asyncio.sleep(1)
            
            ide_url = f"{IDE_BASE_URL}:{port}"
            _ide_containers[container_id]["status"] = IDEContainerStatus.RUNNING.value
            _ide_containers[container_id]["url"] = ide_url
            _ide_containers[container_id]["internal_url"] = f"http://{container_id}:8080"
            
            logger.info(f"IDE 컨테이너 시작 완료: {container_id}, URL: {ide_url}")
        else:
            # Docker 없는 경우 (개발/테스트용)
            # 기존 docker-compose의 code-server 사용
            await asyncio.sleep(2)  # 시뮬레이션
            ide_url = f"{IDE_BASE_URL}:{port}"
            _ide_containers[container_id]["status"] = IDEContainerStatus.RUNNING.value
            _ide_containers[container_id]["url"] = ide_url
            _ide_containers[container_id]["internal_url"] = f"http://code-server:8080"
            
            logger.info(f"IDE 컨테이너 (시뮬레이션) 시작: {container_id}")
            
    except Exception as e:
        logger.error(f"IDE 컨테이너 생성 실패: {container_id}, error: {e}")
        _ide_containers[container_id]["status"] = IDEContainerStatus.ERROR.value
        release_port(port)


@router.get("/containers", response_model=IDEContainerListResponse)
async def list_ide_containers(
    workspace_id: Optional[str] = None,
    status: Optional[IDEContainerStatus] = None,
    current_user: UserModel = Depends(get_current_user),
):
    """
    IDE 컨테이너 목록 조회
    
    인증 필수: JWT 토큰 (Authorization: Bearer ...)
    """
    # 기존 Docker 컨테이너 스캔 (새로 추가된 컨테이너 감지)
    scan_existing_containers()
    
    user_id = current_user.user_id
    
    containers = []
    for container_info in _ide_containers.values():
        # 사용자 필터 (user-default는 모든 사용자에게 표시)
        if container_info["user_id"] != user_id and container_info["user_id"] != "user-default":
            continue
        # 워크스페이스 필터
        if workspace_id and container_info["workspace_id"] != workspace_id:
            continue
        # 상태 필터
        if status and container_info["status"] != status.value:
            continue
        
        containers.append(IDEContainerResponse(**container_info))
    
    return IDEContainerListResponse(containers=containers, total=len(containers))


@router.get("/containers/{container_id}", response_model=IDEContainerResponse)
async def get_ide_container(container_id: str):
    """
    IDE 컨테이너 상세 조회
    """
    if container_id not in _ide_containers:
        raise HTTPException(status_code=404, detail="IDE 컨테이너를 찾을 수 없습니다")
    
    container_info = _ide_containers[container_id]
    
    # 실제 Docker 상태 동기화
    if DOCKER_AVAILABLE:
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
            if container.status == "running":
                container_info["status"] = IDEContainerStatus.RUNNING.value
            elif container.status == "exited":
                container_info["status"] = IDEContainerStatus.STOPPED.value
        except docker.errors.NotFound:
            container_info["status"] = IDEContainerStatus.STOPPED.value
        except Exception as e:
            logger.warning(f"Docker 상태 조회 실패: {e}")
    
    return IDEContainerResponse(**container_info)


@router.post("/containers/{container_id}/start", response_model=StartIDEContainerResponse)
async def start_ide_container(container_id: str):
    """
    IDE 컨테이너 시작
    
    중지된 컨테이너를 다시 시작합니다.
    """
    if container_id not in _ide_containers:
        raise HTTPException(status_code=404, detail="IDE 컨테이너를 찾을 수 없습니다")
    
    container_info = _ide_containers[container_id]
    
    if container_info["status"] == IDEContainerStatus.RUNNING.value:
        # 이미 실행 중
        return StartIDEContainerResponse(
            container_id=container_id,
            status=IDEContainerStatus.RUNNING,
            url=container_info["url"],
        )
    
    # Docker 컨테이너 시작
    if DOCKER_AVAILABLE:
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
            container.start()
            
            # 시작 대기
            for _ in range(15):
                container.reload()
                if container.status == "running":
                    break
                await asyncio.sleep(1)
            
            container_info["status"] = IDEContainerStatus.RUNNING.value
            container_info["last_accessed"] = datetime.now(timezone.utc).isoformat()
            
        except docker.errors.NotFound:
            raise HTTPException(status_code=404, detail="Docker 컨테이너를 찾을 수 없습니다")
        except Exception as e:
            logger.error(f"컨테이너 시작 실패: {e}")
            raise HTTPException(status_code=500, detail=f"컨테이너 시작 실패: {str(e)}")
    else:
        # Docker 없는 경우 상태만 변경
        container_info["status"] = IDEContainerStatus.RUNNING.value
    
    return StartIDEContainerResponse(
        container_id=container_id,
        status=IDEContainerStatus(container_info["status"]),
        url=container_info["url"],
    )


@router.post("/containers/{container_id}/stop", response_model=StopIDEContainerResponse)
async def stop_ide_container(container_id: str):
    """
    IDE 컨테이너 중지
    """
    if container_id not in _ide_containers:
        raise HTTPException(status_code=404, detail="IDE 컨테이너를 찾을 수 없습니다")
    
    container_info = _ide_containers[container_id]
    
    if container_info["status"] == IDEContainerStatus.STOPPED.value:
        return StopIDEContainerResponse(
            container_id=container_id,
            status=IDEContainerStatus.STOPPED,
            message="컨테이너가 이미 중지되어 있습니다"
        )
    
    # Docker 컨테이너 중지
    if DOCKER_AVAILABLE:
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
            container.stop(timeout=10)
            container_info["status"] = IDEContainerStatus.STOPPED.value
        except docker.errors.NotFound:
            container_info["status"] = IDEContainerStatus.STOPPED.value
        except Exception as e:
            logger.error(f"컨테이너 중지 실패: {e}")
            raise HTTPException(status_code=500, detail=f"컨테이너 중지 실패: {str(e)}")
    else:
        container_info["status"] = IDEContainerStatus.STOPPED.value
    
    return StopIDEContainerResponse(
        container_id=container_id,
        status=IDEContainerStatus.STOPPED,
        message="컨테이너가 중지되었습니다"
    )


@router.delete("/containers/{container_id}")
async def delete_ide_container(container_id: str):
    """
    IDE 컨테이너 삭제
    """
    if container_id not in _ide_containers:
        raise HTTPException(status_code=404, detail="IDE 컨테이너를 찾을 수 없습니다")
    
    container_info = _ide_containers[container_id]
    
    # Docker 컨테이너 삭제
    if DOCKER_AVAILABLE:
        try:
            client = docker.from_env()
            container = client.containers.get(container_id)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass  # 이미 없음
        except Exception as e:
            logger.warning(f"Docker 컨테이너 삭제 실패: {e}")
    
    # 포트 해제
    if container_info.get("port"):
        release_port(container_info["port"])
    
    # 메모리에서 삭제
    del _ide_containers[container_id]
    
    logger.info(f"IDE 컨테이너 삭제: {container_id}")
    
    return {"success": True, "message": "IDE 컨테이너가 삭제되었습니다"}


async def _collect_container_metrics() -> tuple[float, float]:
    """
    Docker 컨테이너 메트릭 수집
    
    Returns:
        (avg_cpu_usage, avg_memory_usage) 퍼센트
    """
    if not DOCKER_AVAILABLE or not _ide_containers:
        return 0.0, 0.0
    
    try:
        client = docker.from_env()
        cpu_usages = []
        memory_usages = []
        
        for container_info in _ide_containers.values():
            container_id = container_info.get("docker_container_id")
            if not container_id:
                continue
            
            try:
                container = client.containers.get(container_id)
                stats = container.stats(stream=False)
                
                # CPU 사용률 계산
                cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                           stats["precpu_stats"]["cpu_usage"]["total_usage"]
                system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                              stats["precpu_stats"]["system_cpu_usage"]
                
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0
                    cpu_usages.append(cpu_percent)
                
                # 메모리 사용률 계산
                mem_usage = stats["memory_stats"].get("usage", 0)
                mem_limit = stats["memory_stats"].get("limit", 1)
                mem_percent = (mem_usage / mem_limit) * 100.0
                memory_usages.append(mem_percent)
                
            except docker.errors.NotFound:
                continue
            except Exception as e:
                logger.warning(f"Failed to get metrics for container {container_id}: {e}")
                continue
        
        avg_cpu = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0.0
        avg_mem = sum(memory_usages) / len(memory_usages) if memory_usages else 0.0
        
        return avg_cpu, avg_mem
        
    except Exception as e:
        logger.error(f"Failed to collect container metrics: {e}")
        return 0.0, 0.0


@router.get("/health", response_model=IDEHealthResponse)
async def get_ide_health():
    """
    IDE 서비스 상태 조회
    
    Docker가 사용 가능한 경우 실제 컨테이너 메트릭 수집
    """
    total = len(_ide_containers)
    running = sum(1 for c in _ide_containers.values() 
                  if c["status"] == IDEContainerStatus.RUNNING.value)
    available = IDE_PORT_RANGE_END - IDE_PORT_RANGE_START - len(_used_ports)
    
    # 실제 메트릭 수집
    avg_cpu, avg_mem = await _collect_container_metrics()
    
    return IDEHealthResponse(
        total_containers=total,
        running_containers=running,
        available_capacity=available,
        avg_cpu_usage=round(avg_cpu, 2),
        avg_memory_usage=round(avg_mem, 2),
    )


@router.get("/workspace/{workspace_id}/url")
async def get_workspace_ide_url(
    workspace_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    워크스페이스의 IDE URL 조회 (또는 생성)
    
    워크스페이스에 대한 IDE URL을 반환합니다.
    실행 중인 컨테이너가 없으면 새로 생성합니다.
    
    인증 필수: JWT 토큰 (Authorization: Bearer ...)
    """
    user_id = current_user.user_id
    
    # 1. 로컬 in-memory 저장소에서 찾기 (router의 _ide_containers)
    existing = next(
        (c for c in _ide_containers.values() 
         if c["workspace_id"] == workspace_id 
         and c["user_id"] == user_id
         and c["status"] == IDEContainerStatus.RUNNING.value),
        None
    )
    
    if existing:
        # 마지막 접근 시간 업데이트
        existing["last_accessed"] = datetime.now(timezone.utc).isoformat()
        return {
            "url": existing["url"],
            "container_id": existing["container_id"],
            "status": "existing",
        }
    
    # 2. ide_service에서 찾기 (워크스페이스 생성 시 자동 생성된 컨테이너)
    from ..services.ide_service import get_ide_service
    ide_service = get_ide_service()
    service_container = ide_service.get_container_for_workspace(workspace_id, user_id)
    
    if service_container and service_container.get("status") == "running":
        return {
            "url": service_container["url"],
            "container_id": service_container["container_id"],
            "status": "existing",
        }
    
    # 3. 컨테이너가 없으면 새로 생성
    # DB에서 workspace를 조회하여 project_id(pid)를 함께 전달
    workspace = await db.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == workspace_id,
            WorkspaceModel.owner_id == current_user.user_id,
        )
    )
    workspace = workspace.scalar_one_or_none()
    success, message, ide_url, port = await ide_service.create_ide_container(
        workspace_id=workspace_id,
        user_id=user_id,
        project_id=workspace.project_id if workspace else None,
        tenant_id=current_user.org_id,
        role=current_user.role,
    )
    
    if success and ide_url:
        return {
            "url": ide_url,
            "container_id": None,  # 비동기로 생성되므로 아직 ID 없음
            "status": "created",
        }
    
    # 4. 실패 시 공유 인스턴스 URL 반환 (fallback)
    code_server_url = os.getenv("CODE_SERVER_URL", "http://localhost:8443")
    
    return {
        "url": f"{code_server_url}/?folder=/home/coder/project/{workspace_id}",
        "container_id": None,
        "status": "shared",  # 공유 인스턴스
    }
