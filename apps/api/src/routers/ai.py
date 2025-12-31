"""
AI 라우터
- POST /api/ai/explain
- POST /api/ai/rewrite
"""

from fastapi import APIRouter, HTTPException, status
from ..models import (
    AIExplainRequest,
    AIExplainResponse,
    AIRewriteRequest,
    AIRewriteResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


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


@router.post(
    "/explain",
    response_model=AIExplainResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "File not found"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
    },
    summary="코드 설명",
    description="선택된 코드에 대한 AI 설명을 반환합니다.",
)
async def explain_code(request: AIExplainRequest):
    """
    선택된 코드에 대한 AI 설명을 반환합니다.
    
    TODO: 실제 AI 설명 구현
    - Context Builder를 통해 컨텍스트 조합
    - vLLM으로 요청 전송
    - 응답 처리 및 반환
    
    흐름: API → Context Builder → vLLM → 응답
    
    ⚠️ 주의 (AGENTS.md 규칙)
    - API는 LLM을 직접 호출하지 않습니다
    - 반드시 Context Builder를 경유해야 합니다
    """
    # 경로 검증
    if not _validate_path(request.file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "AI_INVALID_PATH"},
        )
    
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # TODO: Context Builder 호출
    # context = await context_builder.build(
    #     action="explain",
    #     workspace_id=request.workspace_id,
    #     file_path=request.file_path,
    #     selection=request.selection,
    # )
    
    # TODO: vLLM 호출
    # response = await llm_client.chat(context.messages)
    
    # 더미 응답 반환
    return AIExplainResponse(
        explanation="[STUB] 이 코드는 ... (Context Builder + vLLM 연동 필요)",
        tokensUsed=0,
    )


@router.post(
    "/rewrite",
    response_model=AIRewriteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "File not found"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
    },
    summary="코드 리라이트",
    description="지시사항에 따라 코드를 수정하고 unified diff를 반환합니다.",
)
async def rewrite_code(request: AIRewriteRequest):
    """
    지시사항에 따라 코드를 수정하고 unified diff를 반환합니다.
    
    ⚠️ 중요: 이 API는 diff만 반환합니다.
    실제 적용은 /patch/validate → /patch/apply를 통해 수행해야 합니다.
    
    TODO: 실제 AI 리라이트 구현
    - Context Builder를 통해 컨텍스트 조합
    - vLLM으로 요청 전송 (rewrite 프롬프트 템플릿 사용)
    - unified diff 형식 응답 파싱
    
    흐름: API → Context Builder → vLLM → diff 반환
          → (클라이언트) → /patch/validate → /patch/apply
    
    ⚠️ 주의 (AGENTS.md 규칙)
    - API는 LLM을 직접 호출하지 않습니다
    - 코드 변경은 반드시 Patch 경로로 적용해야 합니다
    """
    target_file = request.target.get("file", "")
    
    # 경로 검증
    if not _validate_path(target_file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "AI_INVALID_PATH"},
        )
    
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # TODO: Context Builder 호출
    # context = await context_builder.build(
    #     action="rewrite",
    #     workspace_id=request.workspace_id,
    #     instruction=request.instruction,
    #     target=request.target,
    # )
    
    # TODO: vLLM 호출 (rewrite 템플릿 사용)
    # response = await llm_client.chat(context.messages)
    
    # 더미 diff 반환
    stub_diff = f"""--- a/{target_file}
+++ b/{target_file}
@@ -1,1 +1,1 @@
-# TODO: original code
+# TODO: rewritten code (Context Builder + vLLM 연동 필요)
"""
    
    return AIRewriteResponse(
        diff=stub_diff,
        tokensUsed=0,
    )
