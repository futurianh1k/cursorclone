"""
Workspaces 라우터
- POST /api/workspaces
- GET /api/workspaces
"""

import os
from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models import (
    CreateWorkspaceRequest,
    WorkspaceResponse,
    ErrorResponse,
)
from ..utils.filesystem import (
    get_workspace_root,
    create_workspace_directory,
    workspace_exists,
)

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
async def create_workspace(request: CreateWorkspaceRequest):
    """
    새 워크스페이스를 생성합니다.
    
    개발 모드: 환경변수 DEV_MODE=true일 때 ~/cctv-fastapi 사용
    운영 모드: /workspaces/{workspace_id} 사용
    """
    # 개발 모드 확인
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
    workspace_id = f"ws_{request.name}"
    workspace_root = get_workspace_root(workspace_id, dev_mode=dev_mode)
    
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
    
    개발 모드: ~/cctv-fastapi를 ws_demo로 반환
    운영 모드: /workspaces 디렉토리에서 조회
    """
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
    workspaces: List[WorkspaceResponse] = []
    
    if dev_mode:
        # 개발 모드: 샘플 저장소를 demo 워크스페이스로 반환
        sample_root = get_workspace_root("demo", dev_mode=True)
        if workspace_exists(sample_root):
            workspaces.append(
                WorkspaceResponse(
                    workspaceId="ws_demo",
                    name="cctv-fastapi",
                    rootPath=str(sample_root),
                )
            )
    else:
        # 운영 모드: /workspaces 디렉토리에서 조회
        workspaces_dir = get_workspace_root("", dev_mode=False).parent
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
