"""
Workspaces 라우터
- POST /api/workspaces
- GET /api/workspaces
- POST /api/workspaces/clone (GitHub 클론)
"""

import os
import subprocess
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from ..models import (
    CreateWorkspaceRequest,
    CloneGitHubRequest,
    WorkspaceResponse,
    ErrorResponse,
)
from ..utils.filesystem import (
    get_workspace_root,
    create_workspace_directory,
    workspace_exists,
)
from ..db import UserModel
from ..services.rbac_service import get_current_user, require_permission, Permission

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


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
):
    """
    새 워크스페이스를 생성합니다.
    
    빈 워크스페이스를 생성합니다.
    
    인증 필수: JWT 토큰, 권한: workspace:create
    """
    workspace_id = f"ws_{request.name}"
    workspace_root = get_workspace_root(workspace_id)
    
    # 워크스페이스 존재 여부 확인
    if workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Workspace already exists", "code": "WS_ALREADY_EXISTS"},
        )
    
    # 워크스페이스 디렉토리 생성
    try:
        create_workspace_directory(workspace_id, workspace_root)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to create workspace", "code": "WS_CREATE_FAILED"},
        )
    
    # TODO: DB에 메타데이터 저장
    
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
async def list_workspaces():
    """
    사용자가 접근 가능한 워크스페이스 목록을 반환합니다.
    
    /workspaces 디렉토리에서 조회합니다.
    """
    workspaces: List[WorkspaceResponse] = []
    
    # /workspaces 디렉토리에서 조회
    workspaces_dir = Path("/workspaces")
    if workspaces_dir.exists():
        for entry in workspaces_dir.iterdir():
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
    
    # TODO: DB에서 사용자 권한에 따른 목록 필터링
    # TODO: 페이지네이션 지원
    
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
    
    # TODO: DB에 메타데이터 저장
    
    return WorkspaceResponse(
        workspaceId=workspace_id,
        name=workspace_name,
        rootPath=str(workspace_root),
    )
