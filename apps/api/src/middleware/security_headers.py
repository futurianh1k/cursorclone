"""
보안 헤더 미들웨어

OWASP 권장 보안 헤더 추가

참조:
- OWASP Secure Headers: https://owasp.org/www-project-secure-headers/
- MDN HTTP Headers: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers
"""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    보안 헤더 추가 미들웨어
    
    추가되는 헤더:
    - X-Content-Type-Options: MIME 타입 스니핑 방지
    - X-Frame-Options: 클릭재킹 방지
    - X-XSS-Protection: XSS 필터 활성화 (레거시 브라우저용)
    - Referrer-Policy: Referrer 정보 제한
    - Content-Security-Policy: 리소스 로드 정책
    - Strict-Transport-Security: HTTPS 강제 (프로덕션)
    - Permissions-Policy: 브라우저 기능 제한
    """
    
    def __init__(
        self,
        app,
        csp_policy: str = None,
        enable_hsts: bool = None,
        hsts_max_age: int = 31536000,  # 1년
    ):
        super().__init__(app)
        
        # 환경 감지
        self.is_production = os.getenv("ENVIRONMENT", "development") == "production"
        self.enable_hsts = enable_hsts if enable_hsts is not None else self.is_production
        self.hsts_max_age = hsts_max_age
        
        # CSP 정책 (기본값)
        self.csp_policy = csp_policy or self._default_csp_policy()
    
    def _default_csp_policy(self) -> str:
        """기본 CSP 정책"""
        # 개발 환경에서는 느슨하게
        if not self.is_production:
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*; "
                "frame-ancestors 'self';"
            )
        
        # 프로덕션에서는 엄격하게
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # Monaco Editor 등
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self' wss:; "
            "frame-ancestors 'self'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # OPTIONS 요청은 CORS preflight이므로 보안 헤더만 추가하고 건너뜀
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response
        
        response = await call_next(request)
        
        # ============================================================
        # 보안 헤더 추가
        # ============================================================
        
        # MIME 타입 스니핑 방지
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 클릭재킹 방지
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # XSS 필터 (레거시 브라우저)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer 정책
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP
        response.headers["Content-Security-Policy"] = self.csp_policy
        
        # HSTS (프로덕션에서만)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )
        
        # 브라우저 기능 제한
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=()"
        )
        
        # 추가 보안 헤더
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Server 헤더 제거/변경 (정보 노출 방지)
        response.headers["Server"] = "Cursor-OnPrem"
        
        return response


class RateLimitExceededHandler:
    """Rate Limit 초과 시 응답 핸들러"""
    
    @staticmethod
    def get_response(request: Request, exc) -> Response:
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too many requests",
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "요청 횟수가 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
                "retry_after": getattr(exc, "retry_after", 60),
            },
            headers={
                "Retry-After": str(getattr(exc, "retry_after", 60)),
                "X-RateLimit-Limit": str(getattr(exc, "limit", "unknown")),
            }
        )
