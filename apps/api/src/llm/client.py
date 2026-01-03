"""
vLLM 클라이언트 - OpenAI 호환 API 클라이언트
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
"""

import os
import httpx
import asyncio
import logging
from typing import AsyncIterator, Optional, Dict, Any, List
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


# ============================================================
# 에러 클래스 계층
# ============================================================

class LLMError(Exception):
    """LLM 관련 기본 오류"""
    
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.message = message
        self.cause = cause
    
    def __str__(self):
        if self.cause:
            return f"{self.message} (원인: {self.cause})"
        return self.message


class LLMConnectionError(LLMError):
    """LLM 서버 연결 오류"""
    pass


class LLMTimeoutError(LLMError):
    """LLM 요청 타임아웃 오류"""
    pass


class LLMRateLimitError(LLMError):
    """LLM 속도 제한 오류 (429)"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, cause: Exception = None):
        super().__init__(message, cause)
        self.retry_after = retry_after  # 재시도까지 대기 시간 (초)


class LLMAuthenticationError(LLMError):
    """LLM 인증 오류 (401, 403)"""
    pass


class LLMModelNotFoundError(LLMError):
    """요청한 모델을 찾을 수 없음 (404)"""
    pass


class LLMServerError(LLMError):
    """LLM 서버 내부 오류 (5xx)"""
    
    def __init__(self, message: str, status_code: int = 500, cause: Exception = None):
        super().__init__(message, cause)
        self.status_code = status_code


class LLMResponseError(LLMError):
    """LLM 응답 파싱 오류"""
    pass


class LLMValidationError(LLMError):
    """요청 유효성 검사 오류 (400)"""
    pass


class LLMClient:
    """vLLM OpenAI 호환 클라이언트"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        LLM 클라이언트 초기화
        
        Args:
            base_url: vLLM 서버 URL (기본값: 환경변수 또는 http://localhost:8001/v1)
            api_key: API 키 (vLLM은 기본적으로 키 불필요, 호환성을 위해)
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간 지연 시간 (초)
        """
        self.base_url = base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
        self.api_key = api_key or os.getenv("VLLM_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # httpx 클라이언트 설정
        headers = {"Content-Type": "application/json"}
        
        # API 키가 있는 경우에만 Authorization 헤더 추가
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers,
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        채팅 완료 요청 (non-streaming)
        
        Args:
            messages: 메시지 목록 [{"role": "system", "content": "..."}, ...]
            model: 모델 이름
            temperature: 온도 파라미터
            max_tokens: 최대 토큰 수
            stream: 스트리밍 여부 (False)
            
        Returns:
            응답 딕셔너리
            
        Raises:
            LLMError: LLM 오류
            LLMTimeoutError: 타임아웃 오류
        """
        if stream:
            raise ValueError("Use chat_stream() for streaming requests")
        
        # 모델 이름: 파라미터 > 환경변수 > 기본값
        model_name = model or os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # 재시도 로직
        last_error = None
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            attempt_start = time.time()
            
            try:
                logger.debug(
                    f"LLM 요청 시도 {attempt + 1}/{self.max_retries}: "
                    f"model={model_name}, messages={len(messages)}"
                )
                
                response = await self.client.post(
                    "/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                
                elapsed = time.time() - start_time
                logger.info(
                    f"LLM 요청 성공: model={model_name}, "
                    f"attempts={attempt + 1}, elapsed={elapsed:.2f}s"
                )
                
                return response.json()
                
            except httpx.ConnectError as e:
                last_error = LLMConnectionError(
                    f"LLM 서버 연결 실패: {self.base_url}",
                    cause=e
                )
                logger.warning(
                    f"LLM 연결 실패 (시도 {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"재시도 대기: {delay:.1f}초")
                    await asyncio.sleep(delay)
                    continue
                raise last_error
                
            except httpx.TimeoutException as e:
                last_error = LLMTimeoutError(
                    f"LLM 요청 타임아웃 ({self.timeout}초 초과)",
                    cause=e
                )
                logger.warning(
                    f"LLM 타임아웃 (시도 {attempt + 1}/{self.max_retries}): "
                    f"timeout={self.timeout}s"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"재시도 대기: {delay:.1f}초")
                    await asyncio.sleep(delay)
                    continue
                raise last_error
                
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                response_text = e.response.text[:200]  # 처음 200자만
                
                # 상태 코드별 에러 분류
                if status_code == 429:
                    # Rate Limit
                    retry_after = e.response.headers.get("Retry-After")
                    retry_seconds = int(retry_after) if retry_after else None
                    last_error = LLMRateLimitError(
                        f"LLM 속도 제한 초과",
                        retry_after=retry_seconds,
                        cause=e
                    )
                    logger.warning(
                        f"LLM 속도 제한 (시도 {attempt + 1}/{self.max_retries}): "
                        f"retry_after={retry_seconds}s"
                    )
                    if attempt < self.max_retries - 1:
                        delay = retry_seconds or (self.retry_delay * (attempt + 1) * 2)
                        logger.info(f"재시도 대기: {delay:.1f}초")
                        await asyncio.sleep(delay)
                        continue
                        
                elif status_code == 401:
                    last_error = LLMAuthenticationError(
                        "LLM API 인증 실패: API 키를 확인하세요",
                        cause=e
                    )
                    logger.error(f"LLM 인증 실패: status={status_code}")
                    raise last_error  # 재시도하지 않음
                    
                elif status_code == 403:
                    last_error = LLMAuthenticationError(
                        "LLM API 접근 권한 없음",
                        cause=e
                    )
                    logger.error(f"LLM 권한 없음: status={status_code}")
                    raise last_error  # 재시도하지 않음
                    
                elif status_code == 404:
                    last_error = LLMModelNotFoundError(
                        f"모델을 찾을 수 없음: {model_name}",
                        cause=e
                    )
                    logger.error(f"LLM 모델 없음: model={model_name}")
                    raise last_error  # 재시도하지 않음
                    
                elif status_code == 400:
                    last_error = LLMValidationError(
                        f"LLM 요청 유효성 오류: {response_text}",
                        cause=e
                    )
                    logger.error(f"LLM 유효성 오류: {response_text}")
                    raise last_error  # 재시도하지 않음
                    
                elif status_code >= 500:
                    # 서버 오류는 재시도
                    last_error = LLMServerError(
                        f"LLM 서버 오류: {status_code}",
                        status_code=status_code,
                        cause=e
                    )
                    logger.warning(
                        f"LLM 서버 오류 (시도 {attempt + 1}/{self.max_retries}): "
                        f"status={status_code}, response={response_text}"
                    )
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (attempt + 1)
                        logger.info(f"재시도 대기: {delay:.1f}초")
                        await asyncio.sleep(delay)
                        continue
                else:
                    # 기타 클라이언트 오류는 재시도하지 않음
                    last_error = LLMError(
                        f"LLM 클라이언트 오류: {status_code} - {response_text}",
                        cause=e
                    )
                    logger.error(f"LLM 클라이언트 오류: status={status_code}")
                    raise last_error
                    
            except Exception as e:
                last_error = LLMError(f"예기치 않은 오류: {e}", cause=e)
                logger.error(
                    f"LLM 예기치 않은 오류 (시도 {attempt + 1}/{self.max_retries}): "
                    f"error={type(e).__name__}: {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"재시도 대기: {delay:.1f}초")
                    await asyncio.sleep(delay)
                    continue
        
        total_elapsed = time.time() - start_time
        logger.error(
            f"LLM 요청 최종 실패: model={model_name}, "
            f"attempts={self.max_retries}, elapsed={total_elapsed:.2f}s, "
            f"error={last_error}"
        )
        raise last_error or LLMError("알 수 없는 오류")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        채팅 스트리밍 요청
        
        Args:
            messages: 메시지 목록
            model: 모델 이름
            temperature: 온도 파라미터
            max_tokens: 최대 토큰 수
            
        Yields:
            스트리밍 청크 (텍스트)
            
        Raises:
            LLMError: LLM 오류
            LLMTimeoutError: 타임아웃 오류
        """
        # 모델 이름: 파라미터 > 환경변수 > 기본값
        model_name = model or os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # 재시도 로직
        last_error = None
        start_time = time.time()
        chunk_count = 0
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"LLM 스트림 요청 시도 {attempt + 1}/{self.max_retries}: "
                    f"model={model_name}, messages={len(messages)}"
                )
                
                async with self.client.stream(
                    "POST",
                    "/chat/completions",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # SSE 형식 파싱: "data: {...}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # "data: " 제거
                            
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                import json
                                data = json.loads(data_str)
                                
                                # Delta에서 content 추출
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        chunk_count += 1
                                        yield content
                                        
                            except json.JSONDecodeError as e:
                                # JSON 파싱 실패 시 로그 기록
                                logger.debug(f"SSE 파싱 실패: {data_str[:100]}")
                                continue
                    
                    elapsed = time.time() - start_time
                    logger.info(
                        f"LLM 스트림 완료: model={model_name}, "
                        f"chunks={chunk_count}, elapsed={elapsed:.2f}s"
                    )
                    return
                    
            except httpx.ConnectError as e:
                last_error = LLMConnectionError(
                    f"LLM 서버 연결 실패: {self.base_url}",
                    cause=e
                )
                logger.warning(
                    f"LLM 스트림 연결 실패 (시도 {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"재시도 대기: {delay:.1f}초")
                    await asyncio.sleep(delay)
                    continue
                raise last_error
                    
            except httpx.TimeoutException as e:
                last_error = LLMTimeoutError(
                    f"LLM 스트림 타임아웃 ({self.timeout}초 초과)",
                    cause=e
                )
                logger.warning(
                    f"LLM 스트림 타임아웃 (시도 {attempt + 1}/{self.max_retries})"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"재시도 대기: {delay:.1f}초")
                    await asyncio.sleep(delay)
                    continue
                raise last_error
                
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                
                if status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    retry_seconds = int(retry_after) if retry_after else None
                    last_error = LLMRateLimitError(
                        "LLM 속도 제한 초과",
                        retry_after=retry_seconds,
                        cause=e
                    )
                    logger.warning(
                        f"LLM 스트림 속도 제한 (시도 {attempt + 1}/{self.max_retries})"
                    )
                    if attempt < self.max_retries - 1:
                        delay = retry_seconds or (self.retry_delay * (attempt + 1) * 2)
                        logger.info(f"재시도 대기: {delay:.1f}초")
                        await asyncio.sleep(delay)
                        continue
                        
                elif status_code in (401, 403):
                    last_error = LLMAuthenticationError(
                        "LLM API 인증/권한 오류",
                        cause=e
                    )
                    logger.error(f"LLM 스트림 인증 오류: status={status_code}")
                    raise last_error
                    
                elif status_code == 404:
                    last_error = LLMModelNotFoundError(
                        f"모델을 찾을 수 없음: {model_name}",
                        cause=e
                    )
                    logger.error(f"LLM 스트림 모델 없음: model={model_name}")
                    raise last_error
                    
                elif status_code >= 500:
                    last_error = LLMServerError(
                        f"LLM 서버 오류: {status_code}",
                        status_code=status_code,
                        cause=e
                    )
                    logger.warning(
                        f"LLM 스트림 서버 오류 (시도 {attempt + 1}/{self.max_retries}): "
                        f"status={status_code}"
                    )
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (attempt + 1)
                        logger.info(f"재시도 대기: {delay:.1f}초")
                        await asyncio.sleep(delay)
                        continue
                else:
                    last_error = LLMError(
                        f"LLM 클라이언트 오류: {status_code}",
                        cause=e
                    )
                    logger.error(f"LLM 스트림 클라이언트 오류: status={status_code}")
                    raise last_error
                    
            except Exception as e:
                last_error = LLMError(f"예기치 않은 스트림 오류: {e}", cause=e)
                logger.error(
                    f"LLM 스트림 예기치 않은 오류 (시도 {attempt + 1}/{self.max_retries}): "
                    f"error={type(e).__name__}: {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)
                    logger.info(f"재시도 대기: {delay:.1f}초")
                    await asyncio.sleep(delay)
                    continue
        
        total_elapsed = time.time() - start_time
        logger.error(
            f"LLM 스트림 최종 실패: model={model_name}, "
            f"attempts={self.max_retries}, elapsed={total_elapsed:.2f}s"
        )
        raise last_error or LLMError("알 수 없는 오류")
    
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 전역 클라이언트 인스턴스 (싱글톤)
_global_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    전역 LLM 클라이언트 가져오기
    
    Returns:
        LLM 클라이언트 인스턴스
    """
    global _global_client
    if _global_client is None:
        _global_client = LLMClient()
    return _global_client


async def close_llm_client():
    """전역 LLM 클라이언트 종료"""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None
