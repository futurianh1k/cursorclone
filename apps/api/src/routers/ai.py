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
from ..context_builder import (
    DefaultContextBuilder,
    ContextBuildRequest,
    ContextSource,
    ContextSourceType,
    ActionType,
    SecurityError,
)
from ..llm import (
    get_llm_client,
    LLMError,
    LLMTimeoutError,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Context Builder 인스턴스 (전역 또는 의존성 주입)
# TODO: 실제로는 의존성 주입 또는 설정에서 가져오기
_context_builder_cache = {}


def _get_context_builder(workspace_id: str) -> DefaultContextBuilder:
    """
    워크스페이스별 Context Builder 가져오기
    
    TODO: 실제 워크스페이스 루트 경로 가져오기
    """
    if workspace_id not in _context_builder_cache:
        # TODO: 실제 워크스페이스 루트 경로
        workspace_root = f"/workspaces/{workspace_id}"
        _context_builder_cache[workspace_id] = DefaultContextBuilder(
            workspace_root=workspace_root,
        )
    return _context_builder_cache[workspace_id]


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


async def _read_file_content(workspace_id: str, file_path: str) -> str:
    """
    파일 내용 읽기 (files 라우터와 동일한 로직 사용)
    """
    import os
    from ..utils.filesystem import get_workspace_root, validate_path, read_file_content, workspace_exists
    
    workspace_root = get_workspace_root(workspace_id)
    
    # 워크스페이스 존재 여부 확인
    if not workspace_exists(workspace_root):
        raise ValueError(f"Workspace not found: {workspace_id}")
    
    # 경로 검증 및 파일 읽기
    try:
        full_path = validate_path(file_path, workspace_root)
        content, _ = read_file_content(full_path)
        return content
    except (ValueError, FileNotFoundError) as e:
        raise ValueError(f"Failed to read file: {e}")


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
    
    try:
        # 파일 내용 읽기
        file_content = await _read_file_content(request.workspace_id, request.file_path)
        
        # Context Builder 준비
        context_builder = _get_context_builder(request.workspace_id)
        
        # 컨텍스트 소스 구성
        sources = [
            ContextSource(
                type=ContextSourceType.FILE if not request.selection else ContextSourceType.SELECTION,
                path=request.file_path,
                content=file_content,
                range=request.selection,
            )
        ]
        
        # Context Builder 호출
        context_request = ContextBuildRequest(
            workspace_id=request.workspace_id,
            action=ActionType.EXPLAIN,
            instruction=f"다음 코드를 설명해주세요: {request.file_path}",
            sources=sources,
        )
        
        context_response = await context_builder.build(context_request)
        
        # vLLM 호출
        try:
            llm_client = get_llm_client()
            
            # 메시지 형식 변환
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in context_response.messages
            ]
            
            llm_response = await llm_client.chat(
                messages=messages,
                max_tokens=request.max_tokens if hasattr(request, "max_tokens") else None,
            )
            
            # 응답 추출
            explanation = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            
            if not explanation:
                explanation = "[LLM 응답이 비어있습니다]"
            
            return AIExplainResponse(
                explanation=explanation,
                tokensUsed=tokens_used,
            )
            
        except LLMTimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={"error": "LLM timeout", "code": "LLM_TIMEOUT", "detail": str(e)},
            )
        except LLMError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "LLM service error", "code": "LLM_ERROR", "detail": str(e)},
            )
        
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Security validation failed", "code": "SECURITY_ERROR", "detail": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
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
    
    try:
        # 파일 내용 읽기
        file_content = await _read_file_content(request.workspace_id, target_file)
        
        # 선택 범위 추출
        selection_range = None
        if "selection" in request.target:
            from ..context_builder import SelectionRange
            sel = request.target["selection"]
            selection_range = SelectionRange(
                start_line=sel.get("startLine", sel.get("start_line", 1)),
                end_line=sel.get("endLine", sel.get("end_line", 1)),
            )
        
        # Context Builder 준비
        context_builder = _get_context_builder(request.workspace_id)
        
        # 컨텍스트 소스 구성
        sources = [
            ContextSource(
                type=ContextSourceType.SELECTION if selection_range else ContextSourceType.FILE,
                path=target_file,
                content=file_content,
                range=selection_range,
            )
        ]
        
        # Context Builder 호출
        context_request = ContextBuildRequest(
            workspace_id=request.workspace_id,
            action=ActionType.REWRITE,
            instruction=request.instruction,
            sources=sources,
        )
        
        context_response = await context_builder.build(context_request)
        
        # vLLM 호출 (rewrite 템플릿 사용)
        try:
            llm_client = get_llm_client()
            
            # 메시지 형식 변환
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in context_response.messages
            ]
            
            llm_response = await llm_client.chat(
                messages=messages,
                max_tokens=request.max_tokens if hasattr(request, "max_tokens") else None,
            )
            
            # 응답 추출 (unified diff 형식)
            diff = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            
            if not diff:
                # 빈 diff인 경우 기본 형식 반환
                diff = f"""--- a/{target_file}
+++ b/{target_file}
@@ -1,0 +1,0 @@
"""
            
            return AIRewriteResponse(
                diff=diff,
                tokensUsed=tokens_used,
            )
            
        except LLMTimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={"error": "LLM timeout", "code": "LLM_TIMEOUT", "detail": str(e)},
            )
        except LLMError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "LLM service error", "code": "LLM_ERROR", "detail": str(e)},
            )
        
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Security validation failed", "code": "SECURITY_ERROR", "detail": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR"},
        )
