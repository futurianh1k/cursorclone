"""
AI 라우터
- POST /api/ai/explain   - 코드 설명
- POST /api/ai/chat      - 대화형 채팅
- POST /api/ai/rewrite   - 코드 수정
- POST /api/ai/plan      - 작업 계획 수립
- POST /api/ai/agent     - 자동 코드 작성/수정
- POST /api/ai/debug     - 버그 분석/수정
"""

from fastapi import APIRouter, HTTPException, status
from ..models import (
    AIExplainRequest,
    AIExplainResponse,
    AIChatRequest,
    AIChatResponse,
    AIRewriteRequest,
    AIRewriteResponse,
    # AI Modes
    AIMode,
    AIPlanRequest,
    AIPlanResponse,
    TaskStep,
    AIAgentRequest,
    AIAgentResponse,
    FileChange,
    AIDebugRequest,
    AIDebugResponse,
    BugFix,
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
        try:
            llm_client = get_llm_client()
            
            # 파일이 있으면 Context Builder 사용, 없으면 직접 호출
            if file_content:
                context_builder = _get_context_builder(request.workspace_id)
                
                sources = [
                    ContextSource(
                        type=ContextSourceType.SELECTION if selected_code else ContextSourceType.FILE,
                        path=request.file_path,
                        content=file_content,
                        range=request.selection,
                    )
                ]
                
                context_request = ContextBuildRequest(
                    workspace_id=request.workspace_id,
                    action=ActionType.EXPLAIN,
                    instruction=request.message,
                    sources=sources,
                )
                
                context_response = await context_builder.build(context_request)
                messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in context_response.messages
                ]
            else:
                # 파일 없이 일반 채팅
                messages = [
                    {"role": "system", "content": "You are a helpful coding assistant. Answer questions about programming, software development, and technology. Respond in the same language as the user's question."},
                    {"role": "user", "content": request.message},
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


# ============================================================
# AI Plan Mode - 작업 계획 수립
# ============================================================

@router.post(
    "/plan",
    response_model=AIPlanResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
    },
    summary="작업 계획 수립 (Plan 모드)",
    description="목표를 분석하고 단계별 실행 계획을 생성합니다.",
)
async def create_plan(request: AIPlanRequest):
    """
    사용자가 제시한 목표를 분석하고, 이를 달성하기 위한 
    단계별 실행 계획을 생성합니다.
    
    예시:
    - "로그인 기능 추가"
    - "테스트 코드 작성"
    - "코드 리팩토링"
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    try:
        import os
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # 관련 파일 내용 수집
        file_contents = {}
        if request.file_paths:
            for fp in request.file_paths[:5]:  # 최대 5개 파일
                if _validate_path(fp):
                    try:
                        content = await _read_file_content(request.workspace_id, fp)
                        file_contents[fp] = content
                    except:
                        pass
        
        if dev_mode:
            # 개발 모드: Mock 계획 생성
            steps = _generate_mock_plan_steps(request.goal, file_contents)
            return AIPlanResponse(
                summary=f"'{request.goal}'를 위한 실행 계획입니다. (개발 모드)",
                steps=steps,
                estimatedChanges=len(steps),
                tokensUsed=0,
            )
        
        # 프로덕션 모드: 실제 LLM 호출
        try:
            llm_client = get_llm_client()
            
            # Plan 프롬프트 구성
            files_context = ""
            if file_contents:
                files_context = "\n\n관련 파일:\n" + "\n".join([
                    f"### {fp}\n```\n{content[:500]}...\n```" 
                    for fp, content in file_contents.items()
                ])
            
            messages = [
                {"role": "system", "content": """You are a planning assistant. Given a goal, create a detailed step-by-step plan.

Output format (JSON):
{
  "summary": "Brief summary of the plan",
  "steps": [
    {"stepNumber": 1, "description": "Step description", "filePath": "optional/file/path.py"},
    ...
  ]
}

Keep the plan focused and actionable. Each step should be clear and specific."""},
                {"role": "user", "content": f"Goal: {request.goal}\n\nContext: {request.context or 'None'}{files_context}"}
            ]
            
            llm_response = await llm_client.chat(messages=messages)
            response_text = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            
            # JSON 파싱 시도
            try:
                import json
                # JSON 블록 추출
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                else:
                    json_str = response_text
                    
                plan_data = json.loads(json_str.strip())
                steps = [
                    TaskStep(
                        stepNumber=s.get("stepNumber", i+1),
                        description=s.get("description", ""),
                        filePath=s.get("filePath"),
                    )
                    for i, s in enumerate(plan_data.get("steps", []))
                ]
                summary = plan_data.get("summary", f"Plan for: {request.goal}")
            except:
                # 파싱 실패시 기본 응답
                steps = [TaskStep(stepNumber=1, description=response_text[:500])]
                summary = f"Plan for: {request.goal}"
            
            return AIPlanResponse(
                summary=summary,
                steps=steps,
                estimatedChanges=len(steps),
                tokensUsed=tokens_used,
            )
            
        except (LLMTimeoutError, LLMError) as e:
            # LLM 오류시 기본 계획 반환
            return AIPlanResponse(
                summary=f"⚠️ LLM 연결 실패: {str(e)}",
                steps=[TaskStep(stepNumber=1, description="LLM 서버 연결 확인 필요")],
                estimatedChanges=0,
                tokensUsed=0,
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR", "detail": str(e)},
        )


def _generate_mock_plan_steps(goal: str, file_contents: dict) -> list:
    """개발 모드용 Mock 계획 단계 생성"""
    goal_lower = goal.lower()
    
    if "로그인" in goal_lower or "auth" in goal_lower:
        return [
            TaskStep(stepNumber=1, description="사용자 모델 및 DB 스키마 정의", filePath="src/models/user.py"),
            TaskStep(stepNumber=2, description="비밀번호 해싱 유틸리티 구현", filePath="src/utils/auth.py"),
            TaskStep(stepNumber=3, description="로그인 API 엔드포인트 생성", filePath="src/routers/auth.py"),
            TaskStep(stepNumber=4, description="JWT 토큰 발급 로직 구현", filePath="src/services/jwt.py"),
            TaskStep(stepNumber=5, description="로그인 테스트 작성", filePath="tests/test_auth.py"),
        ]
    elif "테스트" in goal_lower or "test" in goal_lower:
        return [
            TaskStep(stepNumber=1, description="테스트 환경 설정 (pytest)", filePath="pytest.ini"),
            TaskStep(stepNumber=2, description="유닛 테스트 작성", filePath="tests/test_unit.py"),
            TaskStep(stepNumber=3, description="통합 테스트 작성", filePath="tests/test_integration.py"),
            TaskStep(stepNumber=4, description="테스트 커버리지 확인"),
        ]
    elif "리팩토링" in goal_lower or "refactor" in goal_lower:
        return [
            TaskStep(stepNumber=1, description="중복 코드 식별 및 분석"),
            TaskStep(stepNumber=2, description="공통 유틸리티 함수 추출", filePath="src/utils/common.py"),
            TaskStep(stepNumber=3, description="기존 코드에서 유틸리티 사용하도록 수정"),
            TaskStep(stepNumber=4, description="테스트 실행 및 확인"),
        ]
    else:
        # 일반적인 계획
        return [
            TaskStep(stepNumber=1, description=f"'{goal}' 요구사항 분석"),
            TaskStep(stepNumber=2, description="필요한 파일/모듈 식별"),
            TaskStep(stepNumber=3, description="코드 구현"),
            TaskStep(stepNumber=4, description="테스트 작성 및 실행"),
            TaskStep(stepNumber=5, description="문서화"),
        ]


# ============================================================
# AI Agent Mode - 자동 코드 작성/수정
# ============================================================

@router.post(
    "/agent",
    response_model=AIAgentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
    },
    summary="자동 코드 작성/수정 (Agent 모드)",
    description="지시사항에 따라 자동으로 코드를 분석하고 변경 사항을 제안합니다.",
)
async def run_agent(request: AIAgentRequest):
    """
    에이전트 모드: 사용자 지시에 따라 자동으로 코드를 분석하고,
    필요한 파일을 수정/생성/삭제하는 변경 사항을 제안합니다.
    
    auto_apply=True인 경우 변경 사항을 직접 적용합니다.
    (⚠️ 주의: 현재 PoC에서는 auto_apply는 무시됩니다)
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    try:
        import os
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # 관련 파일 내용 수집
        file_contents = {}
        if request.file_paths:
            for fp in request.file_paths[:10]:  # 최대 10개 파일
                if _validate_path(fp):
                    try:
                        content = await _read_file_content(request.workspace_id, fp)
                        file_contents[fp] = content
                    except:
                        pass
        
        if dev_mode:
            # 개발 모드: Mock 응답 생성
            changes = _generate_mock_agent_changes(request.instruction, file_contents)
            return AIAgentResponse(
                summary=f"'{request.instruction}' 작업 완료 (개발 모드)",
                changes=changes,
                applied=False,
                tokensUsed=0,
            )
        
        # 프로덕션 모드: 실제 LLM 호출
        try:
            llm_client = get_llm_client()
            
            # Agent 프롬프트 구성
            files_context = ""
            if file_contents:
                files_context = "\n\nFiles to modify:\n" + "\n".join([
                    f"### {fp}\n```\n{content}\n```" 
                    for fp, content in file_contents.items()
                ])
            
            messages = [
                {"role": "system", "content": """You are a coding agent. Given an instruction, analyze the code and provide specific changes.

Output format (JSON):
{
  "summary": "What was done",
  "changes": [
    {
      "filePath": "path/to/file.py",
      "action": "modify|create|delete",
      "diff": "--- a/file.py\\n+++ b/file.py\\n@@ -1,3 +1,4 @@\\n...",
      "description": "What this change does"
    }
  ]
}

Be specific and provide actual code changes in unified diff format."""},
                {"role": "user", "content": f"Instruction: {request.instruction}{files_context}"}
            ]
            
            llm_response = await llm_client.chat(messages=messages)
            response_text = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            
            # JSON 파싱 시도
            try:
                import json
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                else:
                    json_str = response_text
                    
                agent_data = json.loads(json_str.strip())
                changes = [
                    FileChange(
                        filePath=c.get("filePath", "unknown"),
                        action=c.get("action", "modify"),
                        diff=c.get("diff"),
                        description=c.get("description", ""),
                    )
                    for c in agent_data.get("changes", [])
                ]
                summary = agent_data.get("summary", "Changes generated")
            except:
                changes = [FileChange(
                    filePath="unknown",
                    action="modify",
                    description=response_text[:500],
                )]
                summary = "Agent response (parsing failed)"
            
            return AIAgentResponse(
                summary=summary,
                changes=changes,
                applied=False,  # PoC에서는 자동 적용 비활성화
                tokensUsed=tokens_used,
            )
            
        except (LLMTimeoutError, LLMError) as e:
            return AIAgentResponse(
                summary=f"⚠️ LLM 연결 실패: {str(e)}",
                changes=[],
                applied=False,
                tokensUsed=0,
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR", "detail": str(e)},
        )


def _generate_mock_agent_changes(instruction: str, file_contents: dict) -> list:
    """개발 모드용 Mock Agent 변경 사항 생성"""
    changes = []
    
    if "주석" in instruction or "comment" in instruction.lower():
        for fp, content in file_contents.items():
            lines = content.split("\n")
            diff_lines = [f"--- a/{fp}", f"+++ b/{fp}", "@@ -1,3 +1,4 @@"]
            if lines:
                diff_lines.append(f"+# {instruction}")
                diff_lines.append(f" {lines[0]}")
            
            changes.append(FileChange(
                filePath=fp,
                action="modify",
                diff="\n".join(diff_lines),
                description=f"{fp}에 주석 추가",
            ))
    elif "생성" in instruction or "create" in instruction.lower():
        changes.append(FileChange(
            filePath="new_file.py",
            action="create",
            diff="""--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,5 @@
+\"\"\"
+Auto-generated file
+\"\"\"
+
+# TODO: Implement
""",
            description="새 파일 생성",
        ))
    else:
        # 기존 파일 수정 제안
        for fp in list(file_contents.keys())[:2]:
            changes.append(FileChange(
                filePath=fp,
                action="modify",
                description=f"'{instruction}'에 따라 {fp} 수정 필요 (개발 모드)",
            ))
    
    if not changes:
        changes.append(FileChange(
            filePath="example.py",
            action="modify",
            description=f"'{instruction}' 작업을 위한 변경 사항 (개발 모드)",
        ))
    
    return changes


# ============================================================
# AI Debug Mode - 버그 분석/수정
# ============================================================

@router.post(
    "/debug",
    response_model=AIDebugResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
    },
    summary="버그 분석/수정 (Debug 모드)",
    description="에러 메시지, 스택 트레이스, 코드를 분석하여 버그 원인과 해결책을 제시합니다.",
)
async def debug_code(request: AIDebugRequest):
    """
    디버그 모드: 에러 메시지, 스택 트레이스, 관련 코드를 분석하여
    버그의 원인을 진단하고 수정 방안을 제시합니다.
    """
    if not _validate_workspace_access(request.workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Forbidden", "code": "WS_ACCESS_DENIED"},
        )
    
    if not request.error_message and not request.stack_trace and not request.description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "At least one of error_message, stack_trace, or description is required", "code": "DEBUG_NO_INPUT"},
        )
    
    try:
        import os
        dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # 파일 내용 가져오기
        file_content = None
        if request.file_path and _validate_path(request.file_path):
            try:
                if request.file_content:
                    file_content = request.file_content
                else:
                    file_content = await _read_file_content(request.workspace_id, request.file_path)
            except:
                pass
        
        if dev_mode:
            # 개발 모드: Mock 진단 생성
            diagnosis, root_cause, fixes, tips = _generate_mock_debug_response(
                error_message=request.error_message,
                stack_trace=request.stack_trace,
                file_path=request.file_path,
                file_content=file_content,
                description=request.description,
            )
            return AIDebugResponse(
                diagnosis=diagnosis,
                rootCause=root_cause,
                fixes=fixes,
                preventionTips=tips,
                tokensUsed=0,
            )
        
        # 프로덕션 모드: 실제 LLM 호출
        try:
            llm_client = get_llm_client()
            
            # Debug 프롬프트 구성
            debug_context = []
            if request.error_message:
                debug_context.append(f"Error Message:\n{request.error_message}")
            if request.stack_trace:
                debug_context.append(f"Stack Trace:\n{request.stack_trace}")
            if request.description:
                debug_context.append(f"Description:\n{request.description}")
            if file_content:
                debug_context.append(f"Code ({request.file_path}):\n```\n{file_content}\n```")
            
            messages = [
                {"role": "system", "content": """You are a debugging expert. Analyze the error and provide a diagnosis.

Output format (JSON):
{
  "diagnosis": "Detailed analysis of the problem",
  "rootCause": "The root cause of the bug",
  "fixes": [
    {
      "filePath": "path/to/file.py",
      "lineNumber": 42,
      "originalCode": "old code",
      "fixedCode": "new code",
      "explanation": "Why this fixes the issue"
    }
  ],
  "preventionTips": ["Tip 1", "Tip 2"]
}

Be thorough and specific in your analysis."""},
                {"role": "user", "content": "\n\n".join(debug_context)}
            ]
            
            llm_response = await llm_client.chat(messages=messages)
            response_text = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            
            # JSON 파싱 시도
            try:
                import json
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                else:
                    json_str = response_text
                    
                debug_data = json.loads(json_str.strip())
                fixes = [
                    BugFix(
                        filePath=f.get("filePath", request.file_path or "unknown"),
                        lineNumber=f.get("lineNumber"),
                        originalCode=f.get("originalCode", ""),
                        fixedCode=f.get("fixedCode", ""),
                        explanation=f.get("explanation", ""),
                    )
                    for f in debug_data.get("fixes", [])
                ]
                diagnosis = debug_data.get("diagnosis", "Analysis complete")
                root_cause = debug_data.get("rootCause", "Unknown")
                tips = debug_data.get("preventionTips", [])
            except:
                diagnosis = response_text[:500]
                root_cause = "LLM 응답 파싱 실패"
                fixes = []
                tips = []
            
            return AIDebugResponse(
                diagnosis=diagnosis,
                rootCause=root_cause,
                fixes=fixes,
                preventionTips=tips,
                tokensUsed=tokens_used,
            )
            
        except (LLMTimeoutError, LLMError) as e:
            return AIDebugResponse(
                diagnosis=f"⚠️ LLM 연결 실패: {str(e)}",
                rootCause="LLM 서비스 연결 필요",
                fixes=[],
                preventionTips=["vLLM 서버 상태 확인", "VLLM_BASE_URL 환경변수 확인"],
                tokensUsed=0,
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "code": "INTERNAL_ERROR", "detail": str(e)},
        )


def _generate_mock_debug_response(
    error_message: str | None,
    stack_trace: str | None,
    file_path: str | None,
    file_content: str | None,
    description: str | None,
) -> tuple:
    """개발 모드용 Mock 디버그 응답 생성"""
    
    # 에러 유형 분석
    error_lower = (error_message or "").lower() + (stack_trace or "").lower()
    
    if "typeerror" in error_lower or "type" in error_lower:
        diagnosis = "TypeError가 발생했습니다. 변수의 타입이 예상과 다릅니다."
        root_cause = "함수에 잘못된 타입의 인자가 전달되었거나, None 값에 대해 메서드를 호출했습니다."
        fixes = [BugFix(
            filePath=file_path or "unknown.py",
            lineNumber=1,
            originalCode="result = data.process()",
            fixedCode="result = data.process() if data is not None else None",
            explanation="None 체크를 추가하여 TypeError 방지",
        )]
        tips = ["타입 힌트 사용", "None 체크 추가", "isinstance()로 타입 검증"]
        
    elif "importerror" in error_lower or "modulenotfound" in error_lower:
        diagnosis = "모듈 임포트 오류입니다. 필요한 패키지가 설치되지 않았거나 경로가 잘못되었습니다."
        root_cause = "패키지가 설치되지 않았거나, 가상환경이 활성화되지 않았습니다."
        fixes = [BugFix(
            filePath="requirements.txt",
            lineNumber=None,
            originalCode="",
            fixedCode="missing_package>=1.0.0",
            explanation="필요한 패키지를 requirements.txt에 추가",
        )]
        tips = ["pip install 실행", "가상환경 확인", "PYTHONPATH 확인"]
        
    elif "syntaxerror" in error_lower:
        diagnosis = "문법 오류입니다. 코드에 구문 오류가 있습니다."
        root_cause = "괄호, 콜론, 들여쓰기 등 Python 문법 규칙 위반"
        fixes = [BugFix(
            filePath=file_path or "unknown.py",
            lineNumber=1,
            originalCode="def func(",
            fixedCode="def func():",
            explanation="함수 정의 문법 수정",
        )]
        tips = ["IDE의 린터 활성화", "코드 포맷터 사용", "괄호 짝 확인"]
        
    else:
        diagnosis = f"""## 디버그 분석 (개발 모드)

**에러**: {error_message or '없음'}

**설명**: {description or '없음'}

{'**스택 트레이스**:' + chr(10) + '```' + chr(10) + stack_trace[:500] + chr(10) + '```' if stack_trace else ''}

이 분석은 개발 모드에서 생성된 Mock 응답입니다.
실제 AI 분석을 위해 vLLM 서버를 연결해주세요."""
        root_cause = "개발 모드에서는 정확한 원인 분석이 제한됩니다."
        fixes = []
        tips = ["vLLM 서버 연결 후 재시도", "에러 로그 자세히 확인", "관련 코드 검토"]
    
    return diagnosis, root_cause, fixes, tips


# ============================================================
# AI Mode Status
# ============================================================

@router.get(
    "/modes",
    summary="사용 가능한 AI 모드 목록",
    description="현재 지원하는 AI 모드 목록과 설명을 반환합니다.",
)
async def get_available_modes():
    """사용 가능한 AI 모드 목록 반환"""
    return {
        "modes": [
            {
                "id": "ask",
                "name": "Ask",
                "description": "코드에 대해 질문하고 답변을 받습니다.",
                "icon": "💬",
            },
            {
                "id": "agent",
                "name": "Agent",
                "description": "자동으로 코드를 분석하고 변경 사항을 제안합니다.",
                "icon": "🤖",
            },
            {
                "id": "plan",
                "name": "Plan",
                "description": "목표를 분석하고 단계별 실행 계획을 생성합니다.",
                "icon": "📋",
            },
            {
                "id": "debug",
                "name": "Debug",
                "description": "에러를 분석하고 버그 수정 방안을 제시합니다.",
                "icon": "🐛",
            },
        ],
        "current": "ask",  # 기본 모드
    }
