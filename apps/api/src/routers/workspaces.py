"""
Workspaces 라우터
- POST /api/workspaces
- GET /api/workspaces
- POST /api/workspaces/clone (GitHub 클론)
"""

import os
import subprocess
import re
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    CreateWorkspaceRequest,
    CloneGitHubRequest,
    WorkspaceResponse,
    ErrorResponse,
)
from ..utils.filesystem import (
    get_workspace_root,
    create_workspace_directory,
    delete_workspace_directory,
    workspace_exists,
)
from ..db.connection import get_db
from ..services.workspace_service import WorkspaceService
from ..services.workspace_manager import WorkspaceManager

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Workspace already exists"},
    },
    summary="워크스페이스 생성",
    description="새로운 워크스페이스를 생성합니다.",
)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    새 워크스페이스를 생성합니다.
    
    빈 워크스페이스를 생성합니다.
    
    인증 필수: JWT 토큰, 권한: workspace:create
    """
    workspace_id = f"ws_{request.name}"
    workspace_root = get_workspace_root(workspace_id)
    
    # 워크스페이스 존재 여부 확인 (디렉토리)
    if workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Workspace already exists", "code": "WS_ALREADY_EXISTS"},
        )
    
    # DB에서도 중복 확인
    existing = await db.execute(
        select(WorkspaceModel).where(WorkspaceModel.workspace_id == workspace_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Workspace already exists in database", "code": "WS_ALREADY_EXISTS"},
        )
    
    # 워크스페이스 디렉토리 생성
    try:
        create_workspace_directory(workspace_id, workspace_root)
    except OSError as e:
        logger.error(f"Failed to create workspace directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to create workspace", "code": "WS_CREATE_FAILED"},
        )
    
    # DB에 메타데이터 저장
    try:
        workspace_model = WorkspaceModel(
            workspace_id=workspace_id,
            name=request.name,
            owner_id=current_user.user_id,
            org_id=current_user.org_id,
            root_path=str(workspace_root),
            status="stopped",
        )
        db.add(workspace_model)
        await db.commit()
        await db.refresh(workspace_model)
        logger.info(f"Workspace created: {workspace_id} by {current_user.user_id}")
    except Exception as e:
        logger.error(f"Failed to save workspace to DB: {e}")
        # DB 저장 실패해도 디렉토리는 생성됨 - 로그만 남기고 계속 진행
        await db.rollback()
    
    return WorkspaceResponse(
        workspaceId=workspace_id,
        name=request.name,
        rootPath=str(workspace_root),
    )


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
    summary="워크스페이스 목록 조회",
    description="현재 사용자가 접근 가능한 워크스페이스 목록을 반환합니다.",
)
async def list_workspaces(
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    limit: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    status_filter: Optional[str] = Query(default=None, description="상태 필터 (running, stopped)"),
):
    """
    사용자가 접근 가능한 워크스페이스 목록을 반환합니다.
    
    - 관리자: 모든 워크스페이스 조회 가능
    - 일반 사용자: 자신이 소유한 워크스페이스만 조회
    
    인증 필수: JWT 토큰, 권한: workspace:read
    페이지네이션 지원: page, limit 파라미터
    """
    from ..services.rbac_service import rbac_service
    
    workspaces: List[WorkspaceResponse] = []
    offset = (page - 1) * limit
    
    # 기본 쿼리
    query = select(WorkspaceModel)
    
    # 관리자가 아니면 자신의 워크스페이스만
    if not rbac_service.is_admin(current_user.role or "viewer"):
        query = query.where(WorkspaceModel.owner_id == current_user.user_id)
    
    # 상태 필터
    if status_filter:
        query = query.where(WorkspaceModel.status == status_filter)
    
    # 페이지네이션 및 정렬
    query = query.order_by(WorkspaceModel.created_at.desc()).offset(offset).limit(limit)
    
    # DB에서 조회
    result = await db.execute(query)
    db_workspaces = result.scalars().all()
    
    for ws in db_workspaces:
        workspaces.append(
            WorkspaceResponse(
                workspaceId=ws.workspace_id,
                name=ws.name,
                rootPath=ws.root_path,
            )
        )
    
    # DB에 없는 경우 파일시스템에서 조회 (하위 호환성)
    if not workspaces:
        workspaces_dir = Path("/workspaces")
        if workspaces_dir.exists():
            for entry in list(workspaces_dir.iterdir())[offset:offset+limit]:
                if entry.is_dir() and entry.name.startswith("ws_"):
                    workspace_id = entry.name
                    workspace_name = workspace_id.replace("ws_", "")
                    workspaces.append(
                        WorkspaceResponse(
                            workspaceId=workspace_id,
                            name=workspace_name,
                            rootPath=str(entry),
                        )
                    )
    
    return workspaces


@router.post(
    "/clone",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "Workspace already exists"},
        500: {"model": ErrorResponse, "description": "Failed to clone repository"},
    },
    summary="GitHub 저장소 클론",
    description="GitHub 저장소를 클론하여 새 워크스페이스를 생성합니다.",
)
async def clone_github_repository(
    request: CloneGitHubRequest,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    """
    GitHub 저장소를 클론하여 새 워크스페이스를 생성합니다.
    
    저장소 URL에서 자동으로 이름을 추출하거나, name을 지정할 수 있습니다.
    
    인증 필수: JWT 토큰, 권한: workspace:create
    """
    # 저장소 이름 추출
    if request.name:
        workspace_name = request.name
    else:
        # URL에서 저장소 이름 추출
        # https://github.com/owner/repo -> repo
        # git@github.com:owner/repo.git -> repo
        match = re.search(r"/([^/]+?)(?:\.git)?$", request.repository_url)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid repository URL", "code": "INVALID_REPO_URL"},
            )
        workspace_name = match.group(1)
    
    workspace_id = f"ws_{workspace_name}"
    workspace_root = get_workspace_root(workspace_id)
    
    # 워크스페이스 존재 여부 확인
    if workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Workspace already exists", "code": "WS_ALREADY_EXISTS"},
        )
    
    # 워크스페이스 디렉토리 생성
    try:
        workspace_root.mkdir(parents=True, exist_ok=False)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to create workspace directory", "code": "WS_CREATE_FAILED"},
        )
    
    # Git 클론 실행
    try:
        clone_cmd = ["git", "clone"]
        if request.branch:
            clone_cmd.extend(["-b", request.branch])
        clone_cmd.append(request.repository_url)
        clone_cmd.append(str(workspace_root))
        
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5분 타임아웃
        )
        
        if result.returncode != 0:
            # 실패 시 디렉토리 정리
            if workspace_root.exists():
                import shutil
                shutil.rmtree(workspace_root)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Failed to clone repository",
                    "code": "GIT_CLONE_FAILED",
                    "detail": result.stderr[:500] if result.stderr else "Unknown error",
                },
            )
    except subprocess.TimeoutExpired:
        # 타임아웃 시 디렉토리 정리
        if workspace_root.exists():
            import shutil
            shutil.rmtree(workspace_root)
        
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": "Clone operation timed out", "code": "GIT_CLONE_TIMEOUT"},
        )
    except Exception as e:
        # 기타 오류 시 디렉토리 정리
        if workspace_root.exists():
            import shutil
            shutil.rmtree(workspace_root)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to clone repository", "code": "GIT_CLONE_FAILED", "detail": str(e)},
        )
    
    # DB에 메타데이터 저장
    try:
        workspace_model = WorkspaceModel(
            workspace_id=workspace_id,
            name=workspace_name,
            owner_id=current_user.user_id,
            org_id=current_user.org_id,
            root_path=str(workspace_root),
            status="stopped",
        )
        db.add(workspace_model)
        await db.commit()
        await db.refresh(workspace_model)
        logger.info(f"Workspace cloned: {workspace_id} from {request.repository_url} by {current_user.user_id}")
    except Exception as e:
        logger.error(f"Failed to save workspace to DB: {e}")
        await db.rollback()
    
    return WorkspaceResponse(
        workspaceId=workspace_id,
        name=workspace_name,
        rootPath=str(workspace_root),
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
        500: {"model": ErrorResponse, "description": "Failed to delete workspace"},
    },
    summary="워크스페이스 삭제",
    description="워크스페이스와 모든 관련 데이터를 완전히 삭제합니다.",
)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    워크스페이스를 완전히 삭제합니다.

    다음을 수행합니다:
    1. 워크스페이스 존재 확인
    2. 실행 중인 컨테이너 정리 (있는 경우)
    3. 파일시스템에서 워크스페이스 디렉토리 삭제
    4. 데이터베이스에서 메타데이터 삭제

    WARNING: 이 작업은 되돌릴 수 없습니다.
    """
    workspace_root = get_workspace_root(workspace_id)

    # 워크스페이스 존재 확인
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Workspace not found",
                "code": "WS_NOT_FOUND",
            },
        )

    # TODO: 권한 확인 (사용자가 이 워크스페이스의 소유자인지)
    # if not has_permission(current_user, workspace_id):
    #     raise HTTPException(status_code=403, detail="Forbidden")

    # 1. 실행 중인 컨테이너 정리
    manager = WorkspaceManager.get_instance()
    try:
        success, message = await manager.remove_container(
            workspace_id,
            force=True,
            remove_volumes=True
        )
        if success:
            logger.info(f"Container removed for workspace {workspace_id}: {message}")
        else:
            logger.warning(f"Failed to remove container for workspace {workspace_id}: {message}")
    except Exception as e:
        # 컨테이너가 없거나 이미 삭제된 경우 무시
        logger.info(f"No container to remove for workspace {workspace_id}: {e}")

    # 2. 워크스페이스 디렉토리 삭제
    try:
        delete_workspace_directory(workspace_root)
        logger.info(f"Workspace directory deleted: {workspace_id}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid workspace path",
                "code": "INVALID_PATH",
                "detail": str(e),
            },
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to delete workspace",
                "code": "WS_DELETE_FAILED",
                "detail": str(e),
            },
        )

    # 3. 데이터베이스에서 메타데이터 삭제
    try:
        service = WorkspaceService(db)
        deleted = await service.hard_delete_workspace(workspace_id)
        if deleted:
            logger.info(f"Workspace metadata deleted from database: {workspace_id}")
        else:
            logger.warning(f"Workspace metadata not found in database: {workspace_id}")

        # 커밋
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to delete workspace metadata: {e}")
        await db.rollback()
        # DB 삭제 실패는 치명적이지 않으므로 경고만 로깅
        # 파일은 이미 삭제되었으므로 계속 진행

    # 204 No Content 응답
    return None
