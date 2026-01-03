"""
AI Gateway 라우터
LiteLLM Proxy를 통한 통합 AI API

역할:
- LLM 요청 라우팅 (vLLM, Tabby)
- 정책 적용 (Rate Limiting, DLP)
- 감사 로깅

참조:
- LiteLLM Proxy: https://docs.litellm.ai/docs/proxy
- OpenAI API 호환: https://platform.openai.com/docs/api-reference
"""

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, AsyncGenerator
import httpx
import os
import logging
import json
from datetime import datetime, timezone
import hashlib

from ..db import UserModel
from ..services.rbac_service import get_current_user_optional

router = APIRouter(prefix="/api/gateway", tags=["AI Gateway"])

logger = logging.getLogger(__name__)

# ============================================================
# 설정
# ============================================================

LITELLM_URL = os.getenv("LITELLM_URL", "http://cursor-poc-litellm:4000")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "sk-cursor-poc-key")
TABBY_URL = os.getenv("TABBY_URL", "http://cursor-poc-tabby:8080")

# 감사 로깅 (본문 제외)
AUDIT_LOGGING_ENABLED = os.getenv("AUDIT_LOGGING_ENABLED", "true").lower() == "true"


# ============================================================
# Pydantic Models
# ============================================================

class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI 호환 Chat Completion 요청"""
    model: str = Field(default="chat")
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.1, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=4096, ge=1)
    stream: Optional[bool] = Field(default=False)
    top_p: Optional[float] = Field(default=1.0)
    stop: Optional[List[str]] = None


class CompletionChoice(BaseModel):
    """응답 선택지"""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class CompletionUsage(BaseModel):
    """토큰 사용량"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat Completion 응답"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Optional[CompletionUsage] = None


class TabbyCompletionRequest(BaseModel):
    """Tabby 자동완성 요청"""
    prompt: str
    language: Optional[str] = None
    max_tokens: Optional[int] = Field(default=128, ge=1, le=512)
    temperature: Optional[float] = Field(default=0.1, ge=0, le=1)


class TabbyCompletionResponse(BaseModel):
    """Tabby 자동완성 응답"""
    id: str
    choices: List[dict]


class GatewayHealthResponse(BaseModel):
    """Gateway 상태 응답"""
    status: str
    litellm_available: bool
    tabby_available: bool
    timestamp: str


# ============================================================
# Helper Functions
# ============================================================

def get_user_id_from_header(request: Request) -> str:
    """요청 헤더에서 사용자 ID 추출 (폴백용)"""
    return request.headers.get("X-User-ID", "anonymous")


def get_user_id_from_model(user: Optional[UserModel]) -> str:
    """UserModel에서 사용자 ID 추출"""
    if user:
        return user.user_id
    return "anonymous"


def log_audit(
    user_id: str,
    action: str,
    model: str,
    request_id: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    latency_ms: Optional[float] = None,
    status: str = "success",
):
    """
    감사 로깅 (프롬프트/응답 본문 제외)
    
    AGENTS.md 보안 원칙:
    - 프롬프트/응답 원문 로그 저장 금지
    - 메타데이터만 기록 (user_id, action, model, 토큰 수, 지연시간)
    """
    if not AUDIT_LOGGING_ENABLED:
        return
    
    # 동기 감사 로깅 (AI Gateway용 - 빠른 응답 필요)
    from ..services.audit_service import audit_service
    audit_service.log_sync(
        user_id=user_id,
        action=action,
        model=model,
        request_id=request_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status=status,
    )


async def check_service_health(url: str, timeout: float = 5.0) -> bool:
    """서비스 상태 확인"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}/health")
            return response.status_code == 200
    except Exception:
        return False


# ============================================================
# API Endpoints
# ============================================================

@router.get("/health", response_model=GatewayHealthResponse)
async def gateway_health():
    """
    AI Gateway 상태 확인
    
    LiteLLM Proxy와 Tabby 서버의 연결 상태를 확인합니다.
    """
    litellm_ok = await check_service_health(LITELLM_URL)
    tabby_ok = await check_service_health(TABBY_URL)
    
    return GatewayHealthResponse(
        status="healthy" if litellm_ok else "degraded",
        litellm_available=litellm_ok,
        tabby_available=tabby_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """
    OpenAI 호환 Chat Completion API
    
    LiteLLM Proxy를 통해 vLLM으로 라우팅됩니다.
    Continue 확장 프로그램과 호환됩니다.
    
    인증: JWT 토큰 (Authorization: Bearer ...) 또는 X-User-ID 헤더
    JWT가 없는 경우 X-User-ID 헤더로 폴백
    """
    user_id = get_user_id_from_model(current_user) if current_user else get_user_id_from_header(req)
    request_id = hashlib.sha256(f"{user_id}-{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # LiteLLM Proxy로 요청 전달
            response = await client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json=request.model_dump(exclude_none=True),
                headers={
                    "Authorization": f"Bearer {LITELLM_API_KEY}",
                    "Content-Type": "application/json",
                    "X-Request-ID": request_id,
                },
            )
            
            if not response.is_success:
                error_detail = response.text
                logger.error(f"LiteLLM 요청 실패: {response.status_code} - {error_detail}")
                log_audit(user_id, "chat_completion", request.model, request_id, status="error")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LLM 서비스 오류: {error_detail}"
                )
            
            result = response.json()
            
            # 감사 로깅
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            usage = result.get("usage", {})
            log_audit(
                user_id=user_id,
                action="chat_completion",
                model=request.model,
                request_id=request_id,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                latency_ms=latency_ms,
                status="success",
            )
            
            return result
            
    except httpx.TimeoutException:
        log_audit(user_id, "chat_completion", request.model, request_id, status="timeout")
        raise HTTPException(status_code=504, detail="LLM 서비스 응답 시간 초과")
    except httpx.RequestError as e:
        log_audit(user_id, "chat_completion", request.model, request_id, status="connection_error")
        raise HTTPException(status_code=503, detail=f"LLM 서비스 연결 실패: {str(e)}")


@router.post("/v1/chat/completions/stream")
async def chat_completions_stream(
    request: ChatCompletionRequest,
    req: Request,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """
    스트리밍 Chat Completion API
    
    Server-Sent Events (SSE) 형식으로 응답을 스트리밍합니다.
    """
    user_id = get_user_id_from_model(current_user) if current_user else get_user_id_from_header(req)
    request_id = hashlib.sha256(f"{user_id}-{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    
    request.stream = True
    
    async def generate() -> AsyncGenerator[bytes, None]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{LITELLM_URL}/v1/chat/completions",
                    json=request.model_dump(exclude_none=True),
                    headers={
                        "Authorization": f"Bearer {LITELLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                        
        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n".encode()
    
    log_audit(user_id, "chat_completion_stream", request.model, request_id)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/v1/completions")
async def tabby_completions(
    request: TabbyCompletionRequest,
    req: Request,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """
    Tabby 자동완성 API
    
    Tabby 서버로 직접 라우팅됩니다.
    저지연 응답을 위해 LiteLLM을 거치지 않습니다.
    """
    user_id = get_user_id_from_model(current_user) if current_user else get_user_id_from_header(req)
    request_id = hashlib.sha256(f"{user_id}-{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{TABBY_URL}/v1/completions",
                json=request.model_dump(exclude_none=True),
                headers={"Content-Type": "application/json"},
            )
            
            if not response.is_success:
                logger.error(f"Tabby 요청 실패: {response.status_code}")
                log_audit(user_id, "autocomplete", "tabby", request_id, status="error")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="자동완성 서비스 오류"
                )
            
            result = response.json()
            
            # 감사 로깅
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_audit(
                user_id=user_id,
                action="autocomplete",
                model="tabby",
                request_id=request_id,
                latency_ms=latency_ms,
                status="success",
            )
            
            return result
            
    except httpx.TimeoutException:
        log_audit(user_id, "autocomplete", "tabby", request_id, status="timeout")
        raise HTTPException(status_code=504, detail="자동완성 서비스 응답 시간 초과")
    except httpx.RequestError as e:
        log_audit(user_id, "autocomplete", "tabby", request_id, status="connection_error")
        raise HTTPException(status_code=503, detail=f"자동완성 서비스 연결 실패: {str(e)}")


@router.get("/models")
async def list_models():
    """
    사용 가능한 모델 목록
    
    LiteLLM Proxy에서 설정된 모델 목록을 반환합니다.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{LITELLM_URL}/v1/models",
                headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            )
            
            if response.is_success:
                return response.json()
            else:
                # 기본 모델 목록 반환
                return {
                    "object": "list",
                    "data": [
                        {"id": "chat", "object": "model", "owned_by": "cursor-poc"},
                        {"id": "gpt-4", "object": "model", "owned_by": "cursor-poc"},
                        {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "cursor-poc"},
                    ]
                }
    except Exception:
        return {
            "object": "list",
            "data": [
                {"id": "chat", "object": "model", "owned_by": "cursor-poc"},
            ]
        }


@router.get("/usage")
async def get_usage(
    req: Request,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """
    사용량 통계 조회
    
    현재 사용자의 토큰 사용량 및 요청 횟수를 반환합니다.
    """
    user_id = get_user_id_from_model(current_user) if current_user else get_user_id_from_header(req)
    
    # TODO: Redis 또는 DB에서 실제 사용량 조회
    return {
        "user_id": user_id,
        "period": "daily",
        "requests": 0,
        "tokens": {
            "input": 0,
            "output": 0,
            "total": 0,
        },
        "limit": {
            "requests_per_minute": 60,
            "tokens_per_day": 1000000,
        }
    }
