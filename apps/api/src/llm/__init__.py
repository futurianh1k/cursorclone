"""
LLM 모듈 - vLLM Router
Task D: vLLM Router 구현

에러 계층:
- LLMError (기본)
  - LLMConnectionError (연결 오류)
  - LLMTimeoutError (타임아웃)
  - LLMRateLimitError (속도 제한)
  - LLMAuthenticationError (인증 오류)
  - LLMModelNotFoundError (모델 없음)
  - LLMServerError (서버 오류)
  - LLMResponseError (응답 파싱 오류)
  - LLMValidationError (요청 유효성 오류)
"""

from .client import (
    LLMClient,
    # 에러 계층
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMServerError,
    LLMResponseError,
    LLMValidationError,
    # 유틸리티
    get_llm_client,
    close_llm_client,
)
from .sse import (
    create_sse_response,
    create_sse_chunk,
)

__all__ = [
    # 클라이언트
    "LLMClient",
    # 에러 계층
    "LLMError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMModelNotFoundError",
    "LLMServerError",
    "LLMResponseError",
    "LLMValidationError",
    # 유틸리티
    "get_llm_client",
    "close_llm_client",
    # SSE
    "create_sse_response",
    "create_sse_chunk",
]
