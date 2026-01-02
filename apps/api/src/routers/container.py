"""
워크스페이스 컨테이너 관리 라우터

API 엔드포인트:
- POST /api/workspaces/{workspace_id}/container/start - 컨테이너 시작
- POST /api/workspaces/{workspace_id}/container/stop - 컨테이너 중지
- POST /api/workspaces/{workspace_id}/container/restart - 컨테이너 재시작
- DELETE /api/workspaces/{workspace_id}/container - 컨테이너 삭제
- GET /api/workspaces/{workspace_id}/container/status - 컨테이너 상태 조회
- GET /api/workspaces/{workspace_id}/container/logs - 컨테이너 로그 조회
- POST /api/workspaces/{workspace_id}/execute - 명령 실행
"""

import logging
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from datetime import datetime

from ..models import ErrorResponse
from ..models.container import (
    StartContainerRequest,
    StopContainerRequest,
    RestartContainerRequest,
    ExecuteCommandRequest,
    ContainerStatusResponse,
    ContainerLogsResponse,
    ExecuteCommandResponse,
    ContainerActionResponse,
    ContainerConfig,
)
from ..services.workspace_manager import (
    get_workspace_manager,
    WorkspaceManagerError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}",
    tags=["container"],
)


# ============================================================
# 컨테이너 라이프사이클 API
# ============================================================

@router.post(
    "/container/start",
    response_model=ContainerActionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
        500: {"model": ErrorResponse, "description": "Failed to start container"},
    },
    summary="컨테이너 시작",
    description="워크스페이스 컨테이너를 시작합니다. 컨테이너가 없으면 새로 생성합니다.",
)
async def start_container(
    workspace_id: str,
    request: Optional[StartContainerRequest] = None,
):
    """
    워크스페이스 컨테이너를 시작합니다.
    
    - 컨테이너가 없으면 새로 생성합니다.
    - config를 지정하면 새 설정으로 컨테이너를 생성합니다.
    """
    manager = get_workspace_manager()
    
    config = request.config if request else None
    
    success, message, container_id = await manager.start_container(
        workspace_id=workspace_id,
        config=config,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": message, "code": "CONTAINER_START_FAILED"},
        )
    
    logger.info(f"Container started for workspace {workspace_id}")
    
    return ContainerActionResponse(
        success=True,
        message=message,
        workspace_id=workspace_id,
        container_id=container_id,
    )


@router.post(
    "/container/stop",
    response_model=ContainerActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Workspace not found"},
        500: {"model": ErrorResponse, "description": "Failed to stop container"},
    },
    summary="컨테이너 중지",
    description="워크스페이스 컨테이너를 중지합니다.",
)
async def stop_container(
    workspace_id: str,
    request: Optional[StopContainerRequest] = None,
):
    """
    워크스페이스 컨테이너를 중지합니다.
    
    - timeout: 정상 종료 대기 시간 (초)
    - force: True이면 강제 종료 (SIGKILL)
    """
    manager = get_workspace_manager()
    
    timeout = request.timeout if request else 10
    force = request.force if request else False
    
    success, message = await manager.stop_container(
        workspace_id=workspace_id,
        timeout=timeout,
        force=force,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": message, "code": "CONTAINER_STOP_FAILED"},
        )
    
    logger.info(f"Container stopped for workspace {workspace_id}")
    
    return ContainerActionResponse(
        success=True,
        message=message,
        workspace_id=workspace_id,
    )


@router.post(
    "/container/restart",
    response_model=ContainerActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Container not found"},
        500: {"model": ErrorResponse, "description": "Failed to restart container"},
    },
    summary="컨테이너 재시작",
    description="워크스페이스 컨테이너를 재시작합니다.",
)
async def restart_container(
    workspace_id: str,
    request: Optional[RestartContainerRequest] = None,
):
    """
    워크스페이스 컨테이너를 재시작합니다.
    """
    manager = get_workspace_manager()
    
    timeout = request.timeout if request else 10
    
    success, message, container_id = await manager.restart_container(
        workspace_id=workspace_id,
        timeout=timeout,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": message, "code": "CONTAINER_RESTART_FAILED"},
        )
    
    logger.info(f"Container restarted for workspace {workspace_id}")
    
    return ContainerActionResponse(
        success=True,
        message=message,
        workspace_id=workspace_id,
        container_id=container_id,
    )


@router.delete(
    "/container",
    response_model=ContainerActionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Container not found"},
        500: {"model": ErrorResponse, "description": "Failed to remove container"},
    },
    summary="컨테이너 삭제",
    description="워크스페이스 컨테이너를 삭제합니다. 볼륨은 유지됩니다.",
)
async def remove_container(
    workspace_id: str,
    force: bool = Query(default=False, description="강제 삭제 여부"),
):
    """
    워크스페이스 컨테이너를 삭제합니다.
    
    - 워크스페이스 파일은 유지됩니다.
    - force=True이면 실행 중인 컨테이너도 강제 삭제합니다.
    """
    manager = get_workspace_manager()
    
    success, message = await manager.remove_container(
        workspace_id=workspace_id,
        force=force,
        remove_volumes=False,  # 볼륨은 유지
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": message, "code": "CONTAINER_REMOVE_FAILED"},
        )
    
    logger.info(f"Container removed for workspace {workspace_id}")
    
    return ContainerActionResponse(
        success=True,
        message=message,
        workspace_id=workspace_id,
    )


# ============================================================
# 컨테이너 상태 조회 API
# ============================================================

@router.get(
    "/container/status",
    response_model=ContainerStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Workspace not found"},
    },
    summary="컨테이너 상태 조회",
    description="워크스페이스 컨테이너의 상태 및 리소스 사용량을 조회합니다.",
)
async def get_container_status(workspace_id: str):
    """
    워크스페이스 컨테이너의 상태를 조회합니다.
    
    - 컨테이너 상태 (running, stopped, etc.)
    - CPU/메모리 사용량
    - 시작 시간 등
    """
    manager = get_workspace_manager()
    
    status_response = await manager.get_status(workspace_id)
    
    return status_response


@router.get(
    "/container/logs",
    response_model=ContainerLogsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Container not found"},
    },
    summary="컨테이너 로그 조회",
    description="워크스페이스 컨테이너의 로그를 조회합니다.",
)
async def get_container_logs(
    workspace_id: str,
    tail: int = Query(default=100, ge=1, le=10000, description="마지막 N줄"),
    since: Optional[str] = Query(default=None, description="이 시간 이후 로그 (ISO 8601)"),
    until: Optional[str] = Query(default=None, description="이 시간 이전 로그 (ISO 8601)"),
):
    """
    워크스페이스 컨테이너의 로그를 조회합니다.
    
    - tail: 마지막 N줄만 조회
    - since/until: 시간 범위 지정 (ISO 8601 형식)
    """
    manager = get_workspace_manager()
    
    since_dt = None
    until_dt = None
    
    try:
        if since:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if until:
            until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid datetime format: {e}", "code": "INVALID_DATETIME"},
        )
    
    logs_response = await manager.get_logs(
        workspace_id=workspace_id,
        tail=tail,
        since=since_dt,
        until=until_dt,
    )
    
    return logs_response


# ============================================================
# 명령 실행 API
# ============================================================

@router.post(
    "/execute",
    response_model=ExecuteCommandResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Container not found"},
        408: {"model": ErrorResponse, "description": "Command timeout"},
        500: {"model": ErrorResponse, "description": "Command execution failed"},
    },
    summary="명령 실행",
    description="워크스페이스 컨테이너 내에서 명령을 실행합니다.",
)
async def execute_command(
    workspace_id: str,
    request: ExecuteCommandRequest,
):
    """
    워크스페이스 컨테이너 내에서 명령을 실행합니다.
    
    - 셸 명령을 실행하고 결과를 반환합니다.
    - 위험한 명령은 차단됩니다.
    - timeout 내에 완료되어야 합니다.
    
    보안 주의사항:
    - 명령은 컨테이너 내에서 격리되어 실행됩니다.
    - 일부 위험한 명령 패턴은 차단됩니다.
    """
    manager = get_workspace_manager()
    
    try:
        result = await manager.execute_command(
            workspace_id=workspace_id,
            command=request.command,
            working_dir=request.working_dir,
            env=request.env,
            timeout=request.timeout,
        )
        
        logger.info(
            f"Command executed in {workspace_id}: exit_code={result.exit_code}, "
            f"duration={result.duration_ms}ms"
        )
        
        return result
        
    except WorkspaceManagerError as e:
        if e.code == "CONTAINER_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.message, "code": e.code},
            )
        elif e.code == "CONTAINER_NOT_RUNNING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": e.message, "code": e.code},
            )
        elif e.code == "COMMAND_TIMEOUT":
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail={"error": e.message, "code": e.code},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": e.message, "code": e.code},
            )
