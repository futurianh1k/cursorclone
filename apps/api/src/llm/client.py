"""
vLLM 클라이언트 - OpenAI 호환 API 클라이언트
Task D: vLLM Router 구현
"""

import os
import httpx
import asyncio
from typing import AsyncIterator, Optional, Dict, Any, List
from contextlib import asynccontextmanager
import time


class LLMError(Exception):
    """LLM 관련 오류"""
    pass


class LLMTimeoutError(LLMError):
    """LLM 타임아웃 오류"""
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
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException as e:
                last_error = LLMTimeoutError(f"Request timeout: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise last_error
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    # 서버 오류는 재시도
                    last_error = LLMError(f"Server error: {e.response.status_code}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                else:
                    # 클라이언트 오류는 재시도하지 않음
                    raise LLMError(f"Client error: {e.response.status_code} - {e.response.text}")
                    
            except Exception as e:
                last_error = LLMError(f"Unexpected error: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
        
        raise last_error or LLMError("Unknown error")
    
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
        for attempt in range(self.max_retries):
            try:
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
                                        yield content
                                        
                            except json.JSONDecodeError:
                                # JSON 파싱 실패 시 무시
                                continue
                    
                    return
                    
            except httpx.TimeoutException as e:
                last_error = LLMTimeoutError(f"Stream timeout: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise last_error
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    last_error = LLMError(f"Server error: {e.response.status_code}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                else:
                    raise LLMError(f"Client error: {e.response.status_code} - {e.response.text}")
                    
            except Exception as e:
                last_error = LLMError(f"Unexpected error: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
        
        raise last_error or LLMError("Unknown error")
    
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
