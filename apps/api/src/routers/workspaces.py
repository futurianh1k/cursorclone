"""
Workspaces 라우터
- POST /api/workspaces
- GET /api/workspaces
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models import (
    CreateWorkspaceRequest,
    WorkspaceResponse,
    ErrorResponse,
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
    
    TODO: 실제 워크스페이스 생성 구현
    - 파일시스템에 격리된 디렉토리 생성
    - 권한 설정 (사용자별 접근 제어)
    - 메타데이터 DB 저장
    """
    # TODO: 워크스페이스 이름 중복 체크
    # TODO: 사용자 권한 확인
    # TODO: 파일시스템 디렉토리 생성
    # TODO: DB에 메타데이터 저장
    
    workspace_id = f"ws_{request.name}"
    root_path = f"/workspaces/{workspace_id}"
    
    return WorkspaceResponse(
        workspaceId=workspace_id,
        name=request.name,
        rootPath=root_path,
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
    
    TODO: 실제 워크스페이스 목록 조회 구현
    - DB에서 사용자 권한에 따른 목록 조회
    - 페이지네이션 지원 (추후)
    """
    # TODO: 현재 사용자 ID 추출
    # TODO: DB에서 접근 가능한 워크스페이스 조회
    
    return [
        WorkspaceResponse(
            workspaceId="ws_demo",
            name="demo-project",
            rootPath="/workspaces/ws_demo",
        )
    ]
