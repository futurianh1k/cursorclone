"""
Patch 라우터
- POST /api/patch/validate
- POST /api/patch/apply
"""

import os
import hashlib
from fastapi import APIRouter, HTTPException, status
from ..models import (
    PatchValidateRequest,
    PatchValidateResponse,
    PatchApplyRequest,
    PatchApplyResponse,
    ErrorResponse,
)
from ..utils.diff_utils import (
    validate_patch,
    parse_unified_diff,
    apply_patch_to_file,
    PatchValidationResult,
)
from ..utils.filesystem import get_workspace_root, workspace_exists

router = APIRouter(prefix="/api/patch", tags=["patch"])


def _validate_workspace_access(ws_id: str) -> bool:
    """워크스페이스 접근 권한 검증"""
    # TODO: 실제 권한 검증 로직 구현
    return True


# _validate_patch_basic는 더 이상 사용하지 않음 (diff_utils.validate_patch 사용)


@router.post(
    "/validate",
    response_model=PatchValidateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
    },
    summary="패치 검증",
    description="unified diff 패치의 유효성을 검증합니다.",
)
async def validate_patch(request: PatchValidateRequest):
    """
    패치의 유효성을 검증합니다.
    
    검증 항목:
    1. diff 형식 유효성
    2. 경로 탈출 시도 (../)
    3. 파일 확장자 allowlist
    4. 패치 크기 제한
    5. 워크스페이스 내 파일인지 확인
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(request.workspace_id)
    
    # 워크스페이스 존재 여부 확인
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # diff-utils로 검증
    validation_result = validate_patch(request.patch, workspace_root)
    
    return PatchValidateResponse(
        valid=validation_result.valid,
        reason=validation_result.reason,
        files=validation_result.files if validation_result.valid else None,
    )


@router.post(
    "/apply",
    response_model=PatchApplyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid patch"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "File not found"},
        409: {"model": ErrorResponse, "description": "Conflict - patch cannot be applied"},
    },
    summary="패치 적용",
    description="검증된 패치를 실제 파일에 적용합니다.",
)
async def apply_patch(request: PatchApplyRequest):
    """
    패치를 실제 파일에 적용합니다.
    
    ⚠️ 중요 (AGENTS.md 규칙)
    코드 변경은 반드시 이 API를 통해서만 적용해야 합니다.
    /patch/validate를 먼저 호출하여 검증 후 적용을 권장합니다.
    
    흐름:
    1. 패치 검증 (validate와 동일)
    2. dry_run인 경우 여기서 종료
    3. 파일 백업 생성 (자동)
    4. 패치 적용
    5. 감사 로그 기록 (해시만)
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    workspace_root = get_workspace_root(request.workspace_id)
    
    # 워크스페이스 존재 여부 확인
    if not workspace_exists(workspace_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace not found", "code": "WS_NOT_FOUND"},
        )
    
    # 먼저 검증
    validation_result = validate_patch(request.patch, workspace_root)
    
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid patch",
                "code": f"PATCH_{validation_result.reason.upper() if validation_result.reason else 'INVALID'}",
                "detail": validation_result.reason,
            },
        )
    
    # dry_run 모드
    if request.dry_run:
        return PatchApplyResponse(
            success=True,
            appliedFiles=validation_result.files or [],
            message="Dry run - patch is valid but not applied",
        )
    
    # 패치 파싱
    parsed_files = parse_unified_diff(request.patch)
    
    if not parsed_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "No files in patch", "code": "PATCH_NO_FILES"},
        )
    
    # 각 파일에 패치 적용
    applied_files: List[str] = []
    conflicts: List[str] = []
    
    for file_info in parsed_files:
        try:
            result = apply_patch_to_file(
                Path(file_info.new_path),
                file_info,
                workspace_root,
            )
            
            if result.success:
                applied_files.append(file_info.new_path)
            else:
                if result.conflicts:
                    for conflict in result.conflicts:
                        conflicts.append(f"{file_info.new_path}: {conflict.reason}")
                else:
                    conflicts.append(f"{file_info.new_path}: unknown error")
                    
        except Exception as e:
            conflicts.append(f"{file_info.new_path}: {str(e)}")
    
    # 충돌이 있으면 409 반환
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Patch conflicts detected",
                "code": "PATCH_CONFLICT",
                "conflicts": conflicts,
                "appliedFiles": applied_files,
            },
        )
    
    # 감사 로그 기록 (해시만)
    patch_hash = hashlib.sha256(request.patch.encode()).hexdigest()
    # TODO: 실제 감사 로그 저장
    # await audit_log.record(
    #     user_id=current_user.id,
    #     workspace_id=request.workspace_id,
    #     action="patch_apply",
    #     patch_hash=patch_hash,
    #     files=applied_files,
    # )
    
    return PatchApplyResponse(
        success=True,
        appliedFiles=applied_files,
        message=f"Patch applied successfully to {len(applied_files)} file(s)",
    )
