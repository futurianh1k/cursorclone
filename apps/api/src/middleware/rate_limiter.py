"""
Rate Limiting 미들웨어

slowapi를 사용한 API 속도 제한

참조:
- slowapi 문서: https://github.com/laurentS/slowapi
- limits 문서: https://limits.readthedocs.io/
"""

import os
from typing import Optional, Callable, Any, TypeVar, cast

try:
    # NOTE: 운영 환경에서는 slowapi가 반드시 설치되어야 한다.
    from slowapi import Limiter, _rate_limit_exceeded_handler as rate_limit_exceeded_handler  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from slowapi.middleware import SlowAPIMiddleware  # type: ignore
    _SLOWAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    # 테스트/로컬에서 slowapi가 없을 때도 앱이 기동/수집되도록 하는 폴백.
    # TODO: 배포 파이프라인에서 slowapi 설치를 강제하고, 운영에서는 이 경로가 사용되지 않도록 검증할 것.
    _SLOWAPI_AVAILABLE = False

    class RateLimitExceeded(Exception):
        pass

    def rate_limit_exceeded_handler(*args: Any, **kwargs: Any):  # type: ignore
        # main.py에서 예외 핸들러 등록 시 호출될 수 있음. 여기서는 no-op.
        return None

    def get_remote_address(request: "Request") -> str:  # type: ignore
        client = getattr(request, "client", None)
        return getattr(client, "host", "unknown")

    _F = TypeVar("_F", bound=Callable[..., Any])

    class Limiter:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any):
            pass

        def limit(self, *args: Any, **kwargs: Any):
            def decorator(fn: _F) -> _F:
                return fn
            return decorator

        def shared_limit(self, *args: Any, **kwargs: Any):
            def decorator(fn: _F) -> _F:
                return fn
            return decorator

    class SlowAPIMiddleware:  # type: ignore
        def __init__(self, app: Any, *args: Any, **kwargs: Any):
            self.app = app
from starlette.requests import Request


def get_user_identifier(request: Request) -> str:
    """
    Rate Limiting 키 생성
    
    우선순위:
    1. 인증된 사용자 ID (JWT에서 추출)
    2. API 키
    3. 클라이언트 IP
    """
    # 1. JWT에서 사용자 ID 추출 시도
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # JWT 토큰이 있으면 사용자별 제한
        # 실제 user_id는 디코드 필요하지만, 여기서는 토큰 해시 사용
        import hashlib
        token = auth_header[7:]
        return f"user:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
    
    # 2. API 키 확인
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        import hashlib
        return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    
    # 3. 클라이언트 IP (기본)
    return get_remote_address(request)


# Redis URL (환경변수에서)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Rate Limiter 설정
# storage_uri가 있으면 Redis 사용, 없으면 메모리
try:
    limiter = Limiter(  # type: ignore
        key_func=get_user_identifier,  # type: ignore
        storage_uri=REDIS_URL,  # type: ignore
        default_limits=["1000/day", "100/hour"],  # 기본 제한
    )
except Exception:
    # Redis 연결 실패 시 메모리 사용
    limiter = Limiter(  # type: ignore
        key_func=get_user_identifier,  # type: ignore
        default_limits=["1000/day", "100/hour"],
    )


# ============================================================
# 엔드포인트별 Rate Limit 정책
# ============================================================

# 인증 관련 (엄격)
AUTH_LIMITS = {
    "login": "5/minute",          # 로그인 시도
    "signup": "3/minute",         # 회원가입
    "refresh": "10/minute",       # 토큰 갱신
    "password_reset": "3/hour",   # 비밀번호 재설정
}

# AI 관련 (리소스 집약적)
AI_LIMITS = {
    "chat": "30/minute",          # AI 채팅
    "explain": "20/minute",       # 코드 설명
    "rewrite": "15/minute",       # 코드 리라이트
    "agent": "10/minute",         # 에이전트 모드 (가장 비쌈)
    "completions": "60/minute",   # 자동완성 (Tabby)
}

# 파일 관련 (보통)
FILE_LIMITS = {
    "read": "200/minute",         # 파일 읽기
    "write": "60/minute",         # 파일 쓰기
    "upload": "30/minute",        # 파일 업로드
    "tree": "100/minute",         # 파일 트리
}

# 워크스페이스 관련
WORKSPACE_LIMITS = {
    "create": "10/hour",          # 워크스페이스 생성
    "clone": "5/hour",            # Git 클론
    "list": "100/minute",         # 목록 조회
}

# Admin 관련
ADMIN_LIMITS = {
    "default": "100/minute",
    "create_server": "10/hour",
    "delete_server": "10/hour",
}


def get_rate_limit(category: str, action: str) -> str:
    """카테고리와 액션에 따른 Rate Limit 반환"""
    limits_map = {
        "auth": AUTH_LIMITS,
        "ai": AI_LIMITS,
        "file": FILE_LIMITS,
        "workspace": WORKSPACE_LIMITS,
        "admin": ADMIN_LIMITS,
    }
    
    category_limits = limits_map.get(category, {})
    return category_limits.get(action, "100/minute")  # 기본값
