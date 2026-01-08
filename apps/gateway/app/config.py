import os
from typing import Optional

# 금융권 VDE 환경에서는 외부 의존성 추가가 민감하므로,
# pydantic-settings 미설치 환경에서도 동작하도록 fallback을 제공한다.
try:
    from pydantic_settings import BaseSettings  # type: ignore
    from pydantic import Field  # type: ignore
except Exception:  # pragma: no cover
    BaseSettings = object  # type: ignore

    def Field(default=None, alias=None, description=None):  # type: ignore
        return default


class Settings(BaseSettings):
    # Upstreams
    upstream_tabby: str = Field(default="http://tabby:8080", alias="UPSTREAM_TABBY")
    upstream_agent: str = Field(default="http://opencode-model:8080", alias="UPSTREAM_AGENT")
    upstream_chat: str = Field(default="http://chat-llm:8080", alias="UPSTREAM_CHAT")
    upstream_rag: str = Field(default="http://code-rag:8080", alias="UPSTREAM_RAG")

    # JWT / Auth
    jwt_dev_mode: bool = Field(default=False, alias="JWT_DEV_MODE")
    jwt_jwks_url: Optional[str] = Field(default=None, alias="JWT_JWKS_URL")
    jwt_jwks_file: Optional[str] = Field(default=None, alias="JWT_JWKS_FILE")
    jwt_audience: Optional[str] = Field(default=None, alias="JWT_AUDIENCE")
    jwt_issuer: Optional[str] = Field(default=None, alias="JWT_ISSUER")

    # JWKS cache/refresh
    jwt_jwks_cache_ttl_seconds: int = Field(default=300, alias="JWT_JWKS_CACHE_TTL_SECONDS")
    jwt_jwks_refresh_seconds: int = Field(default=60, alias="JWT_JWKS_REFRESH_SECONDS")
    jwt_jwks_fail_open: bool = Field(default=False, alias="JWT_JWKS_FAIL_OPEN")  # false => fail close

    # DLP
    dlp_rules_path: str = Field(default="policies/dlp_rules.yaml", alias="DLP_RULES_PATH")
    dlp_reload_seconds: int = Field(default=30, alias="DLP_RELOAD_SECONDS")
    dlp_stream_mode: str = Field(default="pre_only", alias="DLP_STREAM_MODE")  # pre_only | pre_and_incremental
    dlp_stream_max_buffer_bytes: int = Field(default=1048576, alias="DLP_STREAM_MAX_BUFFER_BYTES")

    # Audit DB
    audit_db_dsn: Optional[str] = Field(default=None, alias="AUDIT_DB_DSN")
    audit_retention_days: int = Field(default=365, alias="AUDIT_RETENTION_DAYS")

    # Upstream auth separation
    upstream_auth_mode: str = Field(default="none", alias="UPSTREAM_AUTH_MODE")  # none|static_bearer|mtls
    upstream_bearer_token: Optional[str] = Field(default=None, alias="UPSTREAM_BEARER_TOKEN")
    upstream_ca_file: Optional[str] = Field(default=None, alias="UPSTREAM_CA_FILE")
    upstream_client_cert_file: Optional[str] = Field(default=None, alias="UPSTREAM_CLIENT_CERT_FILE")
    upstream_client_key_file: Optional[str] = Field(default=None, alias="UPSTREAM_CLIENT_KEY_FILE")

    # Internal upstream token (service-to-service) — do not forward workspace Authorization token
    upstream_internal_token: Optional[str] = Field(default=None, alias="UPSTREAM_INTERNAL_TOKEN")
    upstream_internal_token_header: str = Field(default="x-internal-token", alias="UPSTREAM_INTERNAL_TOKEN_HEADER")

    # HTTP
    upstream_timeout_seconds: float = Field(default=30.0, alias="UPSTREAM_TIMEOUT_SECONDS")
    stream_read_timeout_seconds: float = Field(default=60.0, alias="STREAM_READ_TIMEOUT_SECONDS")


def _fallback_settings_from_env() -> Settings:
    """
    pydantic-settings 미설치 시에도 Settings가 존재하도록 강제 초기화.
    BaseSettings가 object인 경우, Field는 단순 default를 반환하므로
    아래에서 환경변수를 반영해 속성을 덮어쓴다.
    """
    s = Settings()  # type: ignore
    s.upstream_tabby = os.getenv("UPSTREAM_TABBY", s.upstream_tabby)
    s.upstream_agent = os.getenv("UPSTREAM_AGENT", s.upstream_agent)
    s.upstream_chat = os.getenv("UPSTREAM_CHAT", s.upstream_chat)
    s.upstream_rag = os.getenv("UPSTREAM_RAG", s.upstream_rag)

    s.jwt_dev_mode = os.getenv("JWT_DEV_MODE", "false").lower() == "true"
    s.jwt_jwks_url = os.getenv("JWT_JWKS_URL") or None
    s.jwt_jwks_file = os.getenv("JWT_JWKS_FILE") or None
    s.jwt_audience = os.getenv("JWT_AUDIENCE") or None
    s.jwt_issuer = os.getenv("JWT_ISSUER") or None

    s.jwt_jwks_cache_ttl_seconds = int(os.getenv("JWT_JWKS_CACHE_TTL_SECONDS", str(s.jwt_jwks_cache_ttl_seconds)))
    s.jwt_jwks_refresh_seconds = int(os.getenv("JWT_JWKS_REFRESH_SECONDS", str(s.jwt_jwks_refresh_seconds)))
    s.jwt_jwks_fail_open = os.getenv("JWT_JWKS_FAIL_OPEN", "false").lower() == "true"

    s.dlp_rules_path = os.getenv("DLP_RULES_PATH", s.dlp_rules_path)
    s.dlp_reload_seconds = int(os.getenv("DLP_RELOAD_SECONDS", str(s.dlp_reload_seconds)))
    s.dlp_stream_mode = os.getenv("DLP_STREAM_MODE", s.dlp_stream_mode)
    s.dlp_stream_max_buffer_bytes = int(os.getenv("DLP_STREAM_MAX_BUFFER_BYTES", str(s.dlp_stream_max_buffer_bytes)))

    s.audit_db_dsn = os.getenv("AUDIT_DB_DSN") or None
    s.audit_retention_days = int(os.getenv("AUDIT_RETENTION_DAYS", str(s.audit_retention_days)))

    s.upstream_auth_mode = os.getenv("UPSTREAM_AUTH_MODE", s.upstream_auth_mode)
    s.upstream_bearer_token = os.getenv("UPSTREAM_BEARER_TOKEN") or None
    s.upstream_ca_file = os.getenv("UPSTREAM_CA_FILE") or None
    s.upstream_client_cert_file = os.getenv("UPSTREAM_CLIENT_CERT_FILE") or None
    s.upstream_client_key_file = os.getenv("UPSTREAM_CLIENT_KEY_FILE") or None

    s.upstream_internal_token = os.getenv("UPSTREAM_INTERNAL_TOKEN") or None
    s.upstream_internal_token_header = os.getenv("UPSTREAM_INTERNAL_TOKEN_HEADER", s.upstream_internal_token_header)

    s.upstream_timeout_seconds = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", str(s.upstream_timeout_seconds)))
    s.stream_read_timeout_seconds = float(os.getenv("STREAM_READ_TIMEOUT_SECONDS", str(s.stream_read_timeout_seconds)))
    return s


settings = _fallback_settings_from_env()

