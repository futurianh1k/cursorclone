"""
LLM 클라이언트 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.llm.client import (
    LLMClient,
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMServerError,
    LLMValidationError,
)


class TestLLMErrorHierarchy:
    """에러 계층 테스트"""

    def test_llm_error_base(self):
        """기본 LLMError 테스트"""
        error = LLMError("기본 오류")
        assert str(error) == "기본 오류"
        assert error.message == "기본 오류"
        assert error.cause is None

    def test_llm_error_with_cause(self):
        """원인 예외가 있는 LLMError 테스트"""
        cause = Exception("원인")
        error = LLMError("오류 발생", cause=cause)
        
        assert "원인" in str(error)
        assert error.cause is cause

    def test_llm_connection_error(self):
        """연결 오류 테스트"""
        error = LLMConnectionError("서버 연결 실패")
        
        assert isinstance(error, LLMError)
        assert "연결" in str(error) or "서버" in str(error)

    def test_llm_timeout_error(self):
        """타임아웃 오류 테스트"""
        error = LLMTimeoutError("요청 타임아웃")
        
        assert isinstance(error, LLMError)

    def test_llm_rate_limit_error(self):
        """속도 제한 오류 테스트"""
        error = LLMRateLimitError("속도 제한", retry_after=60)
        
        assert isinstance(error, LLMError)
        assert error.retry_after == 60

    def test_llm_rate_limit_error_no_retry_after(self):
        """retry_after 없는 속도 제한 오류 테스트"""
        error = LLMRateLimitError("속도 제한")
        
        assert error.retry_after is None

    def test_llm_authentication_error(self):
        """인증 오류 테스트"""
        error = LLMAuthenticationError("인증 실패")
        
        assert isinstance(error, LLMError)

    def test_llm_model_not_found_error(self):
        """모델 없음 오류 테스트"""
        error = LLMModelNotFoundError("모델 없음: gpt-5")
        
        assert isinstance(error, LLMError)
        assert "gpt-5" in str(error)

    def test_llm_server_error(self):
        """서버 오류 테스트"""
        error = LLMServerError("서버 내부 오류", status_code=503)
        
        assert isinstance(error, LLMError)
        assert error.status_code == 503

    def test_llm_validation_error(self):
        """유효성 오류 테스트"""
        error = LLMValidationError("잘못된 요청")
        
        assert isinstance(error, LLMError)


class TestLLMClient:
    """LLMClient 테스트"""

    @pytest.fixture
    def client(self):
        return LLMClient(
            base_url="http://test-llm:8000/v1",
            timeout=10.0,
            max_retries=3,
            retry_delay=0.1,
        )

    def test_client_initialization(self, client):
        """클라이언트 초기화 테스트"""
        assert client.base_url == "http://test-llm:8000/v1"
        assert client.timeout == 10.0
        assert client.max_retries == 3
        assert client.retry_delay == 0.1

    def test_client_default_values(self):
        """기본값 테스트"""
        client = LLMClient()
        
        assert client.timeout == 60.0
        assert client.max_retries == 3
        assert client.retry_delay == 1.0

    @pytest.mark.asyncio
    async def test_chat_success(self, client):
        """채팅 성공 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "응답"}}],
            "usage": {"total_tokens": 10}
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await client.chat(
                messages=[{"role": "user", "content": "안녕"}]
            )
            
            assert result["choices"][0]["message"]["content"] == "응답"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_timeout_retry(self, client):
        """타임아웃 재시도 테스트"""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            # 첫 번째: 타임아웃, 두 번째: 성공
            mock_post.side_effect = [
                httpx.TimeoutException("timeout"),
                mock_response,
            ]
            
            result = await client.chat(
                messages=[{"role": "user", "content": "test"}]
            )
            
            assert mock_post.call_count == 2
            assert result["choices"][0]["message"]["content"] == "ok"

    @pytest.mark.asyncio
    async def test_chat_connection_error(self, client):
        """연결 오류 테스트"""
        import httpx
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("연결 실패")
            
            with pytest.raises(LLMConnectionError) as exc_info:
                await client.chat(messages=[{"role": "user", "content": "test"}])
            
            assert "연결" in str(exc_info.value)
            assert mock_post.call_count == client.max_retries

    @pytest.mark.asyncio
    async def test_chat_rate_limit_error(self, client):
        """속도 제한 오류 테스트"""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.text = "Too Many Requests"
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Rate limit",
                request=MagicMock(),
                response=mock_response
            )
            
            with pytest.raises(LLMRateLimitError) as exc_info:
                await client.chat(messages=[{"role": "user", "content": "test"}])
            
            assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_chat_authentication_error(self, client):
        """인증 오류 테스트 (재시도 없음)"""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Auth error",
                request=MagicMock(),
                response=mock_response
            )
            
            with pytest.raises(LLMAuthenticationError):
                await client.chat(messages=[{"role": "user", "content": "test"}])
            
            # 재시도하지 않음
            assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_chat_model_not_found(self, client):
        """모델 없음 오류 테스트 (재시도 없음)"""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Not found",
                request=MagicMock(),
                response=mock_response
            )
            
            with pytest.raises(LLMModelNotFoundError):
                await client.chat(messages=[{"role": "user", "content": "test"}])
            
            # 재시도하지 않음
            assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_chat_server_error_retry(self, client):
        """서버 오류 재시도 테스트"""
        import httpx
        
        mock_error_response = MagicMock()
        mock_error_response.status_code = 503
        mock_error_response.text = "Service Unavailable"
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_success_response.raise_for_status = MagicMock()
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                httpx.HTTPStatusError("503", request=MagicMock(), response=mock_error_response),
                mock_success_response,
            ]
            
            result = await client.chat(messages=[{"role": "user", "content": "test"}])
            
            assert mock_post.call_count == 2
            assert result["choices"][0]["message"]["content"] == "ok"

    @pytest.mark.asyncio
    async def test_chat_validation_error(self, client):
        """유효성 오류 테스트 (재시도 없음)"""
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Bad request",
                request=MagicMock(),
                response=mock_response
            )
            
            with pytest.raises(LLMValidationError):
                await client.chat(messages=[{"role": "user", "content": "test"}])
            
            # 재시도하지 않음
            assert mock_post.call_count == 1


class TestLLMClientStream:
    """스트리밍 테스트"""

    @pytest.fixture
    def client(self):
        return LLMClient(
            base_url="http://test-llm:8000/v1",
            timeout=10.0,
            max_retries=2,
            retry_delay=0.1,
        )

    @pytest.mark.asyncio
    async def test_chat_stream_raises_for_stream_param(self, client):
        """stream=True로 chat() 호출 시 오류 테스트"""
        with pytest.raises(ValueError, match="chat_stream"):
            await client.chat(
                messages=[{"role": "user", "content": "test"}],
                stream=True
            )


class TestGetLLMClient:
    """get_llm_client 테스트"""

    def test_get_llm_client_singleton(self):
        """싱글톤 패턴 테스트"""
        from src.llm.client import get_llm_client, _global_client
        
        client1 = get_llm_client()
        client2 = get_llm_client()
        
        assert client1 is client2
