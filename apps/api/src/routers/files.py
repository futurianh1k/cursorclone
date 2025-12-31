"""
Files 라우터
- GET /api/workspaces/{wsId}/files
- GET /api/workspaces/{wsId}/files/content?path=...
- PUT /api/workspaces/{wsId}/files/content
"""

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
    
    TODO: 실제 파일 트리 조회 구현
    - 파일시스템에서 디렉토리 구조 읽기
    - 허용된 확장자 필터링
    - 숨김 파일 제외 옵션
    """
    # TODO: 워크스페이스 존재 여부 확인
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # TODO: 파일시스템에서 실제 트리 구조 읽기
    # TODO: .gitignore 등 제외 패턴 적용
    
    # 더미 데이터 반환
    return FileTreeResponse(
        workspaceId=ws_id,
        tree=[
            FileTreeItem(
                name="src",
                path="src",
                type=FileType.DIRECTORY,
                children=[
                    FileTreeItem(
                        name="main.py",
                        path="src/main.py",
                        type=FileType.FILE,
                    ),
                ],
            ),
            FileTreeItem(
                name="README.md",
                path="README.md",
                type=FileType.FILE,
            ),
        ],
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
    
    TODO: 실제 파일 읽기 구현
    - 경로 검증 (탈출 방지)
    - 파일 존재 여부 확인
    - 인코딩 감지
    - 바이너리 파일 처리
    """
    # 경로 검증
    if not _validate_path(path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "FILE_INVALID_PATH"},
        )
    
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # TODO: 파일시스템에서 실제 파일 읽기
    # TODO: 파일 크기 제한 확인
    # TODO: 허용된 확장자인지 확인
    
    # 더미 데이터 반환
    return FileContentResponse(
        path=path,
        content='print("hello on-prem poc")\n',
        encoding="utf-8",
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
    
    TODO: 실제 파일 쓰기 구현
    - 경로 검증 (탈출 방지)
    - 파일 존재 여부 확인
    - 백업 생성 (옵션)
    - 권한 확인
    """
    # 경로 검증
    if not _validate_path(request.path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "FILE_INVALID_PATH"},
        )
    
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # TODO: 파일시스템에 실제 쓰기
    # TODO: 감사 로그 기록 (해시만)
    
    return UpdateFileContentResponse(
        path=request.path,
        success=True,
        message="File updated (stub)",
    )
