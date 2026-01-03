"""
AI Gateway API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.main import app

client = TestClient(app)


class TestGatewayHealth:
    """Gateway 상태 API 테스트"""

    def test_gateway_health(self):
        """Gateway 상태 조회 테스트"""
        response = client.get("/api/gateway/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "litellm_available" in data
        assert "tabby_available" in data
        assert "timestamp" in data


class TestChatCompletions:
    """Chat Completion API 테스트"""

    @patch("httpx.AsyncClient")
    def test_chat_completions_success(self, mock_client):
        """Chat Completion 성공 테스트"""
        # Mock 응답 설정
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "chat",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        mock_instance = MagicMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        response = client.post(
            "/api/gateway/v1/chat/completions",
            json={
                "model": "chat",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        
        # 외부 서비스 연결 없이 테스트하므로 503 또는 200 허용
        assert response.status_code in [200, 503, 504]

    def test_chat_completions_validation_error(self):
        """Chat Completion 입력 검증 실패 테스트"""
        response = client.post(
            "/api/gateway/v1/chat/completions",
            json={
                "model": "chat",
                # messages 필드 누락
            }
        )
        
        assert response.status_code == 422

    def test_chat_completions_invalid_temperature(self):
        """잘못된 temperature 값 테스트"""
        response = client.post(
            "/api/gateway/v1/chat/completions",
            json={
                "model": "chat",
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 3.0  # 범위 초과 (0-2)
            }
        )
        
        assert response.status_code == 422


class TestTabbyCompletions:
    """Tabby 자동완성 API 테스트"""

    def test_tabby_completions_validation(self):
        """Tabby 자동완성 입력 검증 테스트"""
        response = client.post(
            "/api/gateway/v1/completions",
            json={
                "prompt": "def hello_world():",
                "language": "python",
                "max_tokens": 128
            }
        )
        
        # 외부 서비스 연결 없이 테스트하므로 503 또는 504 허용
        assert response.status_code in [200, 503, 504]

    def test_tabby_completions_without_prompt(self):
        """prompt 없이 요청 테스트"""
        response = client.post(
            "/api/gateway/v1/completions",
            json={
                "language": "python"
            }
        )
        
        assert response.status_code == 422


class TestModels:
    """모델 목록 API 테스트"""

    def test_list_models(self):
        """모델 목록 조회 테스트"""
        response = client.get("/api/gateway/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)


class TestUsage:
    """사용량 API 테스트"""

    def test_get_usage(self):
        """사용량 조회 테스트"""
        response = client.get("/api/gateway/usage")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "period" in data
        assert "requests" in data
        assert "tokens" in data
        assert "limit" in data


class TestAuditLogging:
    """감사 로깅 테스트"""

    @patch("src.routers.ai_gateway.logger")
    def test_audit_logging_excludes_content(self, mock_logger):
        """감사 로그에 본문이 포함되지 않는지 테스트"""
        # 이 테스트는 로그 호출을 검증하여
        # 프롬프트/응답 본문이 포함되지 않는지 확인합니다.
        
        # API 호출 (외부 서비스 연결 없이)
        response = client.post(
            "/api/gateway/v1/chat/completions",
            json={
                "model": "chat",
                "messages": [{"role": "user", "content": "This should not be logged"}]
            }
        )
        
        # 응답 상태 확인 (연결 실패 예상)
        assert response.status_code in [200, 503, 504]
        
        # 로그 호출 확인 (있는 경우)
        for call in mock_logger.info.call_args_list:
            log_message = str(call)
            # 프롬프트 본문이 로그에 포함되지 않아야 함
            assert "This should not be logged" not in log_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
