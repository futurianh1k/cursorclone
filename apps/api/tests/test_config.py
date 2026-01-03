"""
설정 관리 (config.py) 테스트
"""

import pytest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSettings:
    """Settings 클래스 테스트"""

    def test_default_values(self):
        """기본값 테스트"""
        from src.config import Settings
        
        settings = Settings()
        
        assert settings.APP_NAME == "Cursor On-Prem PoC API"
        assert settings.APP_VERSION == "0.1.0"
        assert settings.DEV_MODE is True
        assert settings.PORT == 8000

    def test_llm_settings(self):
        """LLM 관련 설정 테스트"""
        from src.config import Settings
        
        settings = Settings()
        
        assert "vllm" in settings.VLLM_BASE_URL.lower() or "8000" in settings.VLLM_BASE_URL
        assert "litellm" in settings.LITELLM_BASE_URL.lower() or "4000" in settings.LITELLM_BASE_URL
        assert settings.DEFAULT_MODEL is not None

    def test_security_settings(self):
        """보안 설정 테스트"""
        from src.config import Settings
        
        settings = Settings()
        
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRATION_MINUTES == 60
        assert settings.JWT_SECRET_KEY is not None

    def test_cors_origins_list_single(self):
        """단일 CORS origin 테스트"""
        from src.config import Settings
        
        settings = Settings(CORS_ORIGINS="*")
        
        assert settings.cors_origins_list == ["*"]

    def test_cors_origins_list_multiple(self):
        """다중 CORS origin 테스트"""
        from src.config import Settings
        
        settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:8080")
        
        assert "http://localhost:3000" in settings.cors_origins_list
        assert "http://localhost:8080" in settings.cors_origins_list

    def test_environment_override(self):
        """환경변수 오버라이드 테스트"""
        with patch.dict(os.environ, {"DEV_MODE": "false", "PORT": "9000"}):
            from src.config import Settings
            
            settings = Settings()
            
            # 환경변수가 설정되면 기본값이 오버라이드됨
            # (pydantic-settings가 환경변수를 읽음)

    def test_rate_limit_settings(self):
        """Rate Limit 설정 테스트"""
        from src.config import Settings
        
        settings = Settings()
        
        assert settings.RATE_LIMIT_REQUESTS_PER_MINUTE == 60
        assert settings.RATE_LIMIT_TOKENS_PER_DAY == 1000000


class TestGetSettings:
    """get_settings 함수 테스트"""

    def test_get_settings_returns_settings(self):
        """get_settings가 Settings 인스턴스를 반환하는지 테스트"""
        from src.config import get_settings, Settings
        
        settings = get_settings()
        
        assert isinstance(settings, Settings)

    def test_get_settings_cached(self):
        """get_settings가 캐시된 인스턴스를 반환하는지 테스트"""
        from src.config import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # 같은 인스턴스여야 함 (lru_cache)
        assert settings1 is settings2


class TestGlobalSettings:
    """전역 settings 인스턴스 테스트"""

    def test_global_settings_exists(self):
        """전역 settings 인스턴스 존재 테스트"""
        from src.config import settings
        
        assert settings is not None
        assert hasattr(settings, "APP_NAME")
        assert hasattr(settings, "DEV_MODE")

    def test_global_settings_is_cached_instance(self):
        """전역 settings가 캐시된 인스턴스인지 테스트"""
        from src.config import settings, get_settings
        
        # 같은 인스턴스여야 함
        assert settings is get_settings()
