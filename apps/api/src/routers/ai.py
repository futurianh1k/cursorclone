"""
AI 라우터
- POST /api/ai/explain
- POST /api/ai/rewrite
"""

from fastapi import APIRouter, HTTPException, status
from ..models import (
    AIExplainRequest,
    AIExplainResponse,
    AIChatRequest,
    AIChatResponse,
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
        
        # vLLM 호출 (개발 모드에서는 Mock 응답)
        import os
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        try:
            if dev_mode:
                # 개발 모드: Mock 응답 생성
                # 선택된 코드 추출
                if request.selection:
                    lines = file_content.split("\n")
                    start = request.selection.start_line - 1
                    end = request.selection.end_line
                    selected_code = "\n".join(lines[start:end])
                else:
                    selected_code = file_content[:500] + ("..." if len(file_content) > 500 else "")
                
                explanation = f"""## 코드 분석 (개발 모드)

**파일**: `{request.file_path}`

### 코드 내용
```
{selected_code}
```

### 설명
이 코드는 `{request.file_path}` 파일의 내용입니다.

> ⚠️ **개발 모드**: 실제 LLM 서비스가 연결되지 않았습니다.
> vLLM 서버를 시작하면 실제 AI 분석 결과를 받을 수 있습니다.

**vLLM 설정 방법**:
```bash
# docker-compose.yml에 vLLM 서비스 추가 또는
# VLLM_BASE_URL 환경변수 설정
export VLLM_BASE_URL=http://your-vllm-server:8000/v1
```
"""
                return AIExplainResponse(
                    explanation=explanation,
                    tokensUsed=0,
                )
            
            # 프로덕션 모드: 실제 LLM 호출
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
            # LLM 에러 시 개발 모드 응답 제공
            explanation = f"""## LLM 서비스 연결 실패

**에러**: {str(e)}

vLLM 서버가 실행되고 있지 않거나 연결할 수 없습니다.

**해결 방법**:
1. vLLM 서버 상태 확인
2. `VLLM_BASE_URL` 환경변수 확인
3. 네트워크 연결 확인
"""
            return AIExplainResponse(
                explanation=explanation,
                tokensUsed=0,
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
    "/chat",
    response_model=AIChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
    },
    summary="AI 채팅",
    description="코드에 대한 질문, 수정 요청, 주석 추가 등 자유로운 대화형 AI 인터페이스.",
)
async def chat_with_ai(request: AIChatRequest):
    """
    대화형 AI 인터페이스.
    
    - 사용자 질문 + 파일 컨텍스트를 함께 LLM에 전달
    - "주석 달아줘", "이 코드 뭐야?", "버그 찾아줘" 등 자유로운 요청 처리
    - 파일이 없어도 일반 질문 가능
    
    흐름: API → Context Builder → vLLM → 응답
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    # 파일 경로 검증
    if request.file_path and not _validate_path(request.file_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid path", "code": "AI_INVALID_PATH"},
        )
    
    try:
        import os
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # 파일 내용 가져오기
        file_content = None
        if request.file_path:
            try:
                if request.file_content:
                    file_content = request.file_content
                else:
                    file_content = await _read_file_content(request.workspace_id, request.file_path)
            except Exception as e:
                # 파일 읽기 실패해도 채팅은 계속
                file_content = f"[파일 읽기 실패: {e}]"
        
        # 선택된 코드 추출
        selected_code = None
        if file_content and request.selection:
            lines = file_content.split("\n")
            start = request.selection.start_line - 1
            end = request.selection.end_line
            selected_code = "\n".join(lines[start:end])
        
        if dev_mode:
            # 개발 모드: Mock 응답 생성
            response_text = _generate_mock_chat_response(
                message=request.message,
                file_path=request.file_path,
                file_content=file_content,
                selected_code=selected_code,
            )
            
            return AIChatResponse(
                response=response_text,
                tokensUsed=0,
                suggestedAction=_detect_action(request.message),
            )
        
        # 프로덕션 모드: 실제 LLM 호출
        context_builder = _get_context_builder(request.workspace_id)
        
        sources = []
        if file_content:
            sources.append(
                ContextSource(
                    type=ContextSourceType.SELECTION if selected_code else ContextSourceType.FILE,
                    path=request.file_path,
                    content=file_content,
                    range=request.selection,
                )
            )
        
        context_request = ContextBuildRequest(
            workspace_id=request.workspace_id,
            action=ActionType.EXPLAIN,  # 일반 채팅도 EXPLAIN 타입 사용
            instruction=request.message,
            sources=sources,
        )
        
        context_response = await context_builder.build(context_request)
        
        try:
            llm_client = get_llm_client()
            
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in context_response.messages
            ]
            
            llm_response = await llm_client.chat(messages=messages)
            
            response_text = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            
            return AIChatResponse(
                response=response_text or "[응답이 비어있습니다]",
                tokensUsed=tokens_used,
                suggestedAction=_detect_action(request.message),
            )
            
        except (LLMTimeoutError, LLMError) as e:
            # LLM 에러 시 친화적인 응답
            return AIChatResponse(
                response=f"⚠️ LLM 서비스에 연결할 수 없습니다.\n\n**에러**: {str(e)}\n\n`VLLM_BASE_URL` 환경변수를 확인해주세요.",
                tokensUsed=0,
            )
            
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Security validation failed", "code": "SECURITY_ERROR", "detail": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR", "detail": str(e)},
        )


def _detect_action(message: str) -> str | None:
    """사용자 메시지에서 제안 액션 감지"""
    message_lower = message.lower()
    
    rewrite_keywords = ["수정", "변경", "바꿔", "추가", "삭제", "주석", "리팩터", "fix", "change", "add", "remove", "comment"]
    explain_keywords = ["설명", "뭐야", "뭔가요", "알려줘", "어떻게", "explain", "what", "how", "why"]
    
    if any(kw in message_lower for kw in rewrite_keywords):
        return "rewrite"
    if any(kw in message_lower for kw in explain_keywords):
        return "explain"
    
    return None


def _generate_mock_chat_response(
    message: str,
    file_path: str | None,
    file_content: str | None,
    selected_code: str | None,
) -> str:
    """개발 모드용 Mock 응답 생성"""
    # 사용자 요청 분석
    action = _detect_action(message)
    
    if not file_path:
        return f"""안녕하세요! 저는 코드 어시스턴트입니다.

**질문**: {message}

현재 파일이 선택되지 않았습니다. 파일을 열고 코드에 대해 질문하시면 더 정확한 도움을 드릴 수 있습니다.

---
> ⚠️ **개발 모드**: vLLM 서버가 연결되지 않았습니다.
"""
    
    code_preview = selected_code or (file_content[:300] + "..." if file_content and len(file_content) > 300 else file_content)
    
    if action == "rewrite" and "주석" in message:
        # 주석 추가 요청에 대한 Mock 응답
        return f"""## 주석 추가 제안

**파일**: `{file_path}`

**요청**: {message}

### 원본 코드
```
{code_preview}
```

### 제안된 변경사항

코드에 주석을 추가하려면 **Rewrite 모드**를 사용하세요:
1. 주석을 달 코드 영역을 선택
2. "Rewrite" 모드로 전환
3. "주석 달아줘"라고 입력

---
> ⚠️ **개발 모드**: 실제 코드 수정은 vLLM 연결 후 가능합니다.
> `VLLM_BASE_URL` 환경변수를 설정하세요.
"""
    
    return f"""## AI 응답

**파일**: `{file_path}`

**질문**: {message}

### 코드 내용
```
{code_preview}
```

### 분석

이 코드는 `{file_path}` 파일의 내용입니다.

{f"선택된 영역 ({len(selected_code.split(chr(10)))}줄)을 분석했습니다." if selected_code else "전체 파일을 분석했습니다."}

---
> ⚠️ **개발 모드**: 실제 AI 분석은 vLLM 서버 연결 후 가능합니다.
"""


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
