"""
Files 라우터
- GET /api/workspaces/{wsId}/files
- GET /api/workspaces/{wsId}/files/content?path=...
- PUT /api/workspaces/{wsId}/files/content
"""

import os
from fastapi import APIRouter, HTTPException, status, Query
from ..models import (
    FileTreeResponse,
    FileTreeItem,
    FileType,
    FileContentResponse,
    UpdateFileContentRequest,
    UpdateFileContentResponse,
    ErrorResponse,
)
from ..utils.filesystem import (
    get_workspace_root,
    validate_path,
    read_file_content,
    write_file_content,
    build_file_tree,
    workspace_exists,
)

router = APIRouter(prefix="/api/workspaces/{ws_id}/files", tags=["files"])


def _validate_workspace_access(ws_id: str) -> bool:
    """워크스페이스 접근 권한 검증"""
    # TODO: 실제 권한 검증 로직 구현
    return True


def _validate_path(path: str) -> bool:
    """경로 검증 (탈출 방지)"""
    if ".." in path:
        return False
    if path.startswith("/"):
        return False
    return True


@router.get(
    "",
    response_model=FileTreeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - No access to workspace"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
    },
    summary="파일 트리 조회",
    description="워크스페이스의 파일 트리를 반환합니다.",
)
async def get_file_tree(ws_id: str):
    """
    워크스페이스의 파일 트리를 반환합니다.
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    # 워크스페이스 존재 여부 확인
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # 파일 트리 생성
    try:
        tree = build_file_tree(workspace_root)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to build file tree", "code": "FILE_TREE_ERROR"},
        )
    
    return FileTreeResponse(
        workspaceId=ws_id,
        tree=tree,
    )


@router.get(
    "/content",
    response_model=FileContentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid path"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
    summary="파일 내용 조회",
    description="지정된 파일의 내용을 반환합니다.",
)
async def get_file_content(
    ws_id: str,
    path: str = Query(..., description="파일 경로 (workspace 기준 상대 경로)"),
):
    """
    파일 내용을 반환합니다.
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    # 워크스페이스 존재 여부 확인
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # 경로 검증 및 정규화
    try:
        file_path = validate_path(path, workspace_root)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "FILE_INVALID_PATH", "detail": str(e)},
        )
    
    # 파일 읽기
    try:
        content, encoding = read_file_content(file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "File not found", "code": "FILE_NOT_FOUND"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "File read error", "code": "FILE_READ_ERROR", "detail": str(e)},
        )
    
    return FileContentResponse(
        path=path,
        content=content,
        encoding=encoding,
    )


@router.put(
    "/content",
    response_model=UpdateFileContentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
    summary="파일 내용 수정",
    description="지정된 파일의 내용을 수정합니다.",
)
async def update_file_content(
    ws_id: str,
    request: UpdateFileContentRequest,
):
    """
    파일 내용을 수정합니다.
    
    ⚠️ 주의: 이 API는 직접 파일을 수정합니다.
    AI 기반 코드 변경은 /patch/apply를 사용해야 합니다.
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    # 워크스페이스 존재 여부 확인
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # 경로 검증 및 정규화
    try:
        file_path = validate_path(request.path, workspace_root)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "FILE_INVALID_PATH", "detail": str(e)},
        )
    
    # 파일 쓰기
    try:
        write_file_content(file_path, request.content, create_backup=False)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "File write error", "code": "FILE_WRITE_ERROR", "detail": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )
    
    # TODO: 감사 로그 기록 (해시만)
    # import hashlib
    # content_hash = hashlib.sha256(request.content.encode()).hexdigest()
    # await audit_log.record(...)
    
    return UpdateFileContentResponse(
        path=request.path,
        success=True,
        message="File updated successfully",
    )
