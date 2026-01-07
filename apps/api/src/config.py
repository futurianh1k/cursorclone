"""
애플리케이션 설정 관리

모든 환경변수와 설정을 중앙에서 관리합니다.
Pydantic Settings를 사용하여 타입 안전성 보장.

사용법:
    from ..config import settings
    print(settings.VLLM_BASE_URL)
"""

import os
from typing import Optional
from pydantic import Field
from functools import lru_cache

try:
    # NOTE: pydantic-settings는 운영/개발 의존성이다.
    from pydantic_settings import BaseSettings  # type: ignore
except ImportError:  # pragma: no cover
    # 테스트/제한된 환경에서 pydantic-settings가 없을 때의 폴백.
    # TODO: 배포 파이프라인에서 pydantic-settings 설치를 강제할 것.
    from pydantic import BaseModel, ConfigDict

    class BaseSettings(BaseModel):  # type: ignore
        model_config = ConfigDict(extra="ignore")

        def __init__(self, **data):
            # 가능한 경우 환경변수로 기본값을 오버라이드(문자열 기준)
            for field_name in getattr(self.__class__, "model_fields", {}).keys():
                if field_name in data:
                    continue
                env_val = os.getenv(field_name)
                if env_val is not None:
                    data[field_name] = env_val
            super().__init__(**data)


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # ============================================================
    # 기본 설정
    # ============================================================
    
    APP_NAME: str = Field(default="Cursor On-Prem PoC API")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)
    DEV_MODE: bool = Field(default=True, description="개발 모드 여부")
    
    # ============================================================
    # 서버 설정
    # ============================================================
    
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    # ============================================================
    # 데이터베이스 설정
    # ============================================================
    
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://cursor:cursor@cursor-poc-db:5432/cursor_poc",
        description="PostgreSQL 연결 URL"
    )
    
    # ============================================================
    # Redis 설정
    # ============================================================
    
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis 연결 URL"
    )
    
    # ============================================================
    # LLM 설정
    # ============================================================
    
    VLLM_BASE_URL: str = Field(
        default="http://cursor-poc-vllm:8000/v1",
        description="vLLM 서버 URL"
    )
    
    LITELLM_BASE_URL: str = Field(
        default="http://cursor-poc-litellm:4000",
        description="LiteLLM Proxy URL"
    )
    
    LITELLM_API_KEY: str = Field(
        default="sk-cursor-poc-key",
        description="LiteLLM API 키"
    )
    
    DEFAULT_MODEL: str = Field(
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
        description="기본 LLM 모델"
    )
    
    VISION_MODEL: str = Field(
        default="gpt-4-vision-preview",
        description="Vision LLM 모델"
    )
    
    # ============================================================
    # Tabby 설정
    # ============================================================
    
    TABBY_URL: str = Field(
        default="http://cursor-poc-tabby:8080",
        description="Tabby 서버 URL"
    )
    
    # ============================================================
    # 워크스페이스 설정
    # ============================================================
    
    WORKSPACE_BASE_PATH: str = Field(
        default="/workspaces",
        description="워크스페이스 기본 경로"
    )
    
    MAX_FILE_SIZE_MB: int = Field(
        default=10,
        description="최대 파일 크기 (MB)"
    )
    
    # ============================================================
    # 보안 설정
    # ============================================================
    
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT 시크릿 키"
    )
    
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT 알고리즘"
    )
    
    JWT_EXPIRATION_MINUTES: int = Field(
        default=60,
        description="JWT 만료 시간 (분)"
    )
    
    # ============================================================
    # 로깅 설정
    # ============================================================
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="로그 레벨"
    )
    
    LOGGING_BACKEND: str = Field(
        default="none",
        description="중앙 로깅 백엔드 (elasticsearch, loki, splunk, none)"
    )
    
    ELASTICSEARCH_URL: str = Field(
        default="http://localhost:9200",
        description="Elasticsearch URL"
    )
    
    ELASTICSEARCH_INDEX: str = Field(
        default="cursor-poc-logs",
        description="Elasticsearch 인덱스"
    )
    
    LOKI_URL: str = Field(
        default="http://localhost:3100/loki/api/v1/push",
        description="Loki Push API URL"
    )
    
    SPLUNK_HEC_URL: str = Field(
        default="",
        description="Splunk HEC URL"
    )
    
    SPLUNK_HEC_TOKEN: str = Field(
        default="",
        description="Splunk HEC 토큰"
    )
    
    # ============================================================
    # Rate Limiting 설정
    # ============================================================
    
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60,
        description="분당 최대 요청 수"
    )
    
    RATE_LIMIT_TOKENS_PER_DAY: int = Field(
        default=1000000,
        description="일당 최대 토큰 수"
    )
    
    # ============================================================
    # CORS 설정
    # ============================================================
    
    CORS_ORIGINS: str = Field(
        default="*",
        description="허용된 CORS origins (쉼표 구분)"
    )
    
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins를 리스트로 반환"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # ============================================================
    # 기타 설정
    # ============================================================
    
    KEYCLOAK_URL: str = Field(
        default="http://cursor-poc-keycloak:8080",
        description="Keycloak 서버 URL"
    )
    
    KEYCLOAK_REALM: str = Field(
        default="cursor-poc",
        description="Keycloak Realm"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스 가져오기 (캐시됨)"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
