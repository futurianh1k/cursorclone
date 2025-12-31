"""
Patch 라우터
- POST /api/patch/validate
- POST /api/patch/apply
"""

from fastapi import APIRouter, HTTPException, status
from ..models import (
    PatchValidateRequest,
    PatchValidateResponse,
    PatchApplyRequest,
    PatchApplyResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api/patch", tags=["patch"])


def _validate_workspace_access(ws_id: str) -> bool:
    """워크스페이스 접근 권한 검증"""
    # TODO: 실제 권한 검증 로직 구현
    return True


def _validate_patch_basic(patch: str) -> tuple[bool, str | None, list[str]]:
    """
    패치 기본 검증
    
    TODO: packages/diff-utils 연동 (Task C)
    현재는 기본적인 검증만 수행
    """
    files: list[str] = []
    
    # 빈 패치 검증
    if not patch or len(patch.strip()) < 10:
        return False, "empty_or_too_small", files
    
    # 경로 탈출 검증
    if ".." in patch:
        return False, "path_traversal_suspected", files
    
    # diff 형식 기본 검증
    if "---" not in patch or "+++" not in patch:
        return False, "invalid_diff_format", files
    
    # 파일 목록 추출 (간단한 파싱)
    for line in patch.split("\n"):
        if line.startswith("+++ b/"):
            file_path = line[6:].strip()
            if file_path:
                files.append(file_path)
    
    return True, None, files


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
    
    TODO: packages/diff-utils 연동 (Task C 완료)
    - TypeScript diff-utils 구현 완료 (packages/diff-utils/src/index.ts)
    - Python에서 Node.js subprocess로 호출하거나 Python 포팅 필요
    - 실제 unified diff 파서 사용 (parseUnifiedDiff)
    - 보안 검증 강화 (validatePatch)
    - 패치 적용 (applyPatchToText)
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # 기본 검증
    valid, reason, files = _validate_patch_basic(request.patch)
    
    # TODO: 심볼릭 링크 검증
    # TODO: 파일 확장자 allowlist 검증
    # TODO: 패치 크기 제한 검증
    # TODO: 워크스페이스 내 파일인지 확인
    
    return PatchValidateResponse(
        valid=valid,
        reason=reason,
        files=files if valid else None,
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
    3. 파일 백업 생성 (옵션)
    4. 패치 적용
    5. 감사 로그 기록 (해시만)
    
    TODO: 실제 패치 적용 구현 (Task C 완료 - diff-utils 구현됨)
    - packages/diff-utils의 applyPatchToText 사용
      - TypeScript 구현 완료 (packages/diff-utils/src/index.ts)
      - Python에서 Node.js subprocess로 호출하거나 Python 포팅 필요
    - 트랜잭션 처리 (실패 시 롤백)
    - 충돌 감지 및 처리 (applyPatchToText가 ConflictInfo 반환)
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # 먼저 검증
    valid, reason, files = _validate_patch_basic(request.patch)
    
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid patch",
                "code": f"PATCH_{reason.upper()}",
                "detail": reason,
            },
        )
    
    # dry_run 모드
    if request.dry_run:
        return PatchApplyResponse(
            success=True,
            appliedFiles=files,
            message="Dry run - patch is valid but not applied",
        )
    
    # TODO: 실제 패치 적용
    # try:
    #     applied = await diff_utils.apply_patch(
    #         workspace_path=f"/workspaces/{request.workspace_id}",
    #         patch=request.patch,
    #     )
    # except ConflictError as e:
    #     raise HTTPException(status_code=409, detail=...)
    
    # TODO: 감사 로그 기록 (해시만)
    # await audit_log.record(
    #     user_id=current_user.id,
    #     workspace_id=request.workspace_id,
    #     action="patch_apply",
    #     patch_hash=hashlib.sha256(request.patch.encode()).hexdigest(),
    #     files=files,
    # )
    
    return PatchApplyResponse(
        success=True,
        appliedFiles=files,
        message="Patch applied (stub - Task C 구현 필요)",
    )
