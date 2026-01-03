"""
Files 라우터
- GET /api/workspaces/{wsId}/files
- GET /api/workspaces/{wsId}/files/content?path=...
- PUT /api/workspaces/{wsId}/files/content
- POST /api/workspaces/{wsId}/files/upload        - 단일/다중 파일 업로드
- POST /api/workspaces/{wsId}/files/upload/zip    - ZIP 아카이브 업로드 및 압축 해제
- DELETE /api/workspaces/{wsId}/files?path=...    - 파일/폴더 삭제
"""

import os
import shutil
import zipfile
import tempfile
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
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

logger = logging.getLogger(__name__)

# 업로드 제한
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB (ZIP)
ALLOWED_EXTENSIONS = {
    # 코드 파일
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h",
    ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh", ".bash", ".zsh",
    # 설정 파일
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".xml", ".html", ".css", ".scss", ".sass", ".less",
    # 문서
    ".md", ".txt", ".rst", ".adoc", ".tex",
    # 데이터
    ".csv", ".tsv", ".sql",
    # 기타
    ".dockerfile", ".gitignore", ".editorconfig",
    # 아카이브 (ZIP 업로드용)
    ".zip",
}

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


# ============================================================
# 파일 업로드 API
# ============================================================

def _is_allowed_file(filename: str) -> bool:
    """허용된 파일 확장자인지 확인"""
    ext = Path(filename).suffix.lower()
    # 확장자가 없는 파일도 허용 (Makefile, Dockerfile 등)
    if not ext:
        return True
    return ext in ALLOWED_EXTENSIONS


def _safe_filename(filename: str) -> str:
    """안전한 파일명으로 변환"""
    # 경로 구분자 제거
    filename = filename.replace("\\", "/")
    # .. 제거
    parts = [p for p in filename.split("/") if p and p != ".."]
    return "/".join(parts)


@router.post(
    "/upload",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file or request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
    summary="파일 업로드",
    description="단일 또는 다중 파일을 워크스페이스에 업로드합니다.",
)
async def upload_files(
    ws_id: str,
    files: List[UploadFile] = File(..., description="업로드할 파일(들)"),
    target_dir: str = Form(default="", description="업로드 대상 디렉토리 (workspace 기준)"),
    overwrite: bool = Form(default=False, description="기존 파일 덮어쓰기 여부"),
):
    """
    파일 업로드
    
    - 단일 파일 또는 여러 파일 동시 업로드 가능
    - 대상 디렉토리 지정 가능 (기본: 워크스페이스 루트)
    - 기존 파일 덮어쓰기 옵션
    
    **금융권 폐쇄망 환경**:
    GitHub 접속이 불가능한 경우, 이 API를 통해 소스코드와 패키지를 업로드할 수 있습니다.
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # 대상 디렉토리 검증
    target_path = workspace_root
    if target_dir:
        try:
            target_path = validate_path(target_dir, workspace_root)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid target directory", "code": "INVALID_PATH", "detail": str(e)},
            )
    
    # 디렉토리 생성
    os.makedirs(target_path, exist_ok=True)
    
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            # 파일명 검증
            if not file.filename:
                errors.append({"file": "unknown", "error": "No filename"})
                continue
            
            safe_name = _safe_filename(file.filename)
            
            if not _is_allowed_file(safe_name):
                errors.append({"file": safe_name, "error": "File type not allowed"})
                continue
            
            # 파일 크기 확인 (스트림으로 체크)
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                errors.append({"file": safe_name, "error": f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)"})
                continue
            
            # 저장 경로
            file_path = os.path.join(target_path, safe_name)
            
            # 기존 파일 확인
            if os.path.exists(file_path) and not overwrite:
                errors.append({"file": safe_name, "error": "File already exists (use overwrite=true)"})
                continue
            
            # 디렉토리 생성 (중첩된 경로인 경우)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 파일 저장
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 상대 경로 계산
            rel_path = os.path.relpath(file_path, workspace_root)
            uploaded_files.append({
                "path": rel_path,
                "size": len(content),
            })
            
            logger.info(f"File uploaded: {ws_id}/{rel_path} ({len(content)} bytes)")
            
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})
    
    return {
        "success": len(uploaded_files) > 0,
        "uploadedFiles": uploaded_files,
        "errors": errors,
        "totalUploaded": len(uploaded_files),
        "totalErrors": len(errors),
    }


@router.post(
    "/upload/zip",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid ZIP file"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
    summary="ZIP 아카이브 업로드",
    description="ZIP 파일을 업로드하고 워크스페이스에 압축 해제합니다.",
)
async def upload_zip(
    ws_id: str,
    file: UploadFile = File(..., description="업로드할 ZIP 파일"),
    target_dir: str = Form(default="", description="압축 해제 대상 디렉토리"),
    overwrite: bool = Form(default=False, description="기존 파일 덮어쓰기 여부"),
):
    """
    ZIP 아카이브 업로드 및 압축 해제
    
    - ZIP 파일을 업로드하면 지정된 디렉토리에 압축 해제
    - 프로젝트 전체를 한 번에 업로드할 때 유용
    
    **금융권 폐쇄망 환경**:
    외부에서 다운로드한 패키지나 소스코드를 ZIP으로 묶어 업로드할 수 있습니다.
    예: node_modules.zip, vendor.zip, requirements 패키지 등
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # ZIP 파일 확인
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Only ZIP files are allowed", "code": "INVALID_FILE_TYPE"},
        )
    
    # 대상 디렉토리 검증
    target_path = workspace_root
    if target_dir:
        try:
            target_path = validate_path(target_dir, workspace_root)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid target directory", "code": "INVALID_PATH", "detail": str(e)},
            )
    
    # ZIP 파일 크기 확인
    content = await file.read()
    if len(content) > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": f"ZIP file too large (max {MAX_TOTAL_SIZE // 1024 // 1024}MB)", "code": "FILE_TOO_LARGE"},
        )
    
    extracted_files = []
    errors = []
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # ZIP 파일 열기
            with zipfile.ZipFile(tmp_path, "r") as zf:
                # ZIP bomb 체크
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > MAX_TOTAL_SIZE * 10:  # 압축 해제 후 크기 제한
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail={"error": "Extracted content too large", "code": "ZIP_TOO_LARGE"},
                    )
                
                for info in zf.infolist():
                    # 디렉토리는 스킵
                    if info.is_dir():
                        continue
                    
                    # 경로 안전성 검사
                    safe_name = _safe_filename(info.filename)
                    if not safe_name:
                        continue
                    
                    extract_path = os.path.join(target_path, safe_name)
                    
                    # 경로 탈출 방지
                    if not extract_path.startswith(str(workspace_root)):
                        errors.append({"file": info.filename, "error": "Path traversal blocked"})
                        continue
                    
                    # 기존 파일 확인
                    if os.path.exists(extract_path) and not overwrite:
                        errors.append({"file": safe_name, "error": "File exists (use overwrite=true)"})
                        continue
                    
                    # 디렉토리 생성
                    os.makedirs(os.path.dirname(extract_path), exist_ok=True)
                    
                    # 파일 추출
                    with zf.open(info.filename) as src, open(extract_path, "wb") as dst:
                        dst.write(src.read())
                    
                    rel_path = os.path.relpath(extract_path, workspace_root)
                    extracted_files.append({
                        "path": rel_path,
                        "size": info.file_size,
                    })
        finally:
            # 임시 파일 삭제
            os.unlink(tmp_path)
        
        logger.info(f"ZIP extracted: {ws_id} ({len(extracted_files)} files)")
        
        return {
            "success": True,
            "extractedFiles": extracted_files,
            "errors": errors,
            "totalExtracted": len(extracted_files),
            "totalErrors": len(errors),
        }
        
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid or corrupted ZIP file", "code": "INVALID_ZIP"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZIP extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"ZIP extraction failed: {str(e)}", "code": "ZIP_EXTRACT_ERROR"},
        )


@router.delete(
    "",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid path"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
    summary="파일/폴더 삭제",
    description="지정된 파일 또는 폴더를 삭제합니다.",
)
async def delete_file(
    ws_id: str,
    path: str = Query(..., description="삭제할 파일/폴더 경로"),
    recursive: bool = Query(default=False, description="폴더인 경우 하위 항목 포함 삭제"),
):
    """
    파일 또는 폴더 삭제
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    try:
        file_path = validate_path(path, workspace_root)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "INVALID_PATH", "detail": str(e)},
        )
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "File or folder not found", "code": "NOT_FOUND"},
        )
    
    try:
        if os.path.isdir(file_path):
            if recursive:
                shutil.rmtree(file_path)
            else:
                os.rmdir(file_path)  # 빈 폴더만 삭제 가능
        else:
            os.remove(file_path)
        
        logger.info(f"File deleted: {ws_id}/{path}")
        
        return {
            "success": True,
            "path": path,
            "message": "File or folder deleted successfully",
        }
    except OSError as e:
        if "not empty" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Folder is not empty (use recursive=true)", "code": "FOLDER_NOT_EMPTY"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Delete failed: {str(e)}", "code": "DELETE_ERROR"},
        )


@router.get(
    "/download",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid path"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
    summary="파일 다운로드",
    description="지정된 파일을 다운로드합니다.",
)
async def download_file(
    ws_id: str,
    path: str = Query(..., description="다운로드할 파일 경로"),
):
    """
    파일 다운로드
    
    SSH/SCP 대신 웹 UI에서 파일을 다운로드할 때 사용합니다.
    """
    if not _validate_workspace_access(ws_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(ws_id)
    
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    try:
        file_path = validate_path(path, workspace_root)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "INVALID_PATH", "detail": str(e)},
        )
    
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "File not found", "code": "NOT_FOUND"},
        )
    
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream",
    )
