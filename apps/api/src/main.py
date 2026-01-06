"""
On-Prem Cursor PoC API
FastAPI 메인 애플리케이션

Task B: API 명세 반영
- docs/api-spec.md 기준으로 라우터/스키마 구성
- 실제 기능 구현은 하지 않고, 입력검증/에러코드/TODO 포함
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 환경 설정
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# .env 파일 로드 (apps/api/.env)
# __file__ = apps/api/src/main.py
# parent = apps/api/src
# parent.parent = apps/api
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from .routers import (
    auth_router,
    workspaces_router,
    files_router,
    ai_router,
    patch_router,
    ws_router,
    admin_router,
    container_router,
    ssh_router,
    ide_router,
    ai_gateway_router,
)
from .routers.rag import router as rag_router

# ============================================================
# App 설정
# ============================================================

app = FastAPI(
    title="On-Prem Cursor PoC API",
    version="0.1.0",
    description="""
    사내 온프레미스 환경을 위한 Cursor-style AI 코딩 서비스 API
    
    ## 주요 기능
    - **Auth**: 사용자 인증 (SSO/LDAP 연동 예정)
    - **Workspaces**: 워크스페이스 관리
    - **Files**: 파일 트리 및 내용 관리
    - **AI**: 코드 설명/리라이트 (vLLM 연동)
    - **Patch**: diff 기반 코드 변경 적용
    - **WebSocket**: 실시간 협업
    
    ## 보안 원칙 (AGENTS.md)
    - 외부 네트워크 호출 금지
    - 프롬프트/응답 원문 로그 저장 금지
    - 코드 변경은 반드시 Patch 경로로 적용
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# 미들웨어 설정
# ============================================================

# Rate Limiter 설정
from .middleware.rate_limiter import limiter
from .middleware.security_headers import SecurityHeadersMiddleware

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================
# CORS 설정 (보안 헤더 미들웨어보다 먼저 실행되어야 함)
# ============================================================

# 환경변수에서 허용 origin 목록 가져오기
# ⚠️ 온프레미스 환경에서는 내부 도메인만 허용 (절대 * 사용 금지)
ALLOWED_ORIGINS_STR = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    ""
)

# 개발 환경에서는 모든 origin 허용 (프로덕션에서는 명시적 origin만)
if os.getenv("ENVIRONMENT", "development") == "development" or DEBUG:
    # 개발 환경: 일반적인 origin들 허용
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        # Docker 네트워크 origins (일반적인 Docker 네트워크 IP 범위)
        "http://172.18.0.1:3000",
        "http://172.18.0.1:3001",
        "http://172.17.0.1:3000",
        "http://172.17.0.1:3001",
        "http://172.16.0.1:3000",
        "http://172.16.0.1:3001",
        # SSH 원격 접속용 (로컬 네트워크)
        "http://10.10.10.151:3000",
        "http://10.10.10.151:3001",
    ]
    # 환경변수에서 추가 origin이 있으면 추가
    if ALLOWED_ORIGINS_STR:
        ALLOWED_ORIGINS.extend([origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()])
    # 중복 제거
    ALLOWED_ORIGINS = list(set(ALLOWED_ORIGINS))
    # 개발 환경: Docker 네트워크, localhost, 로컬 네트워크 정규식 패턴
    import re
    # localhost, 127.0.0.1, Docker 네트워크 (172.16-31.x.x), 사설 IP (10.x.x.x, 192.168.x.x)
    ALLOWED_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+):\d+"
    logger.info(f"CORS: Development mode - allowing origins: {ALLOWED_ORIGINS} and regex: {ALLOWED_ORIGIN_REGEX}")
else:
    # 프로덕션: 명시적 origin만 허용
    if ALLOWED_ORIGINS_STR:
        ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]
    else:
        ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # "*" 가 포함되어 있으면 경고 로그
    if "*" in ALLOWED_ORIGINS:
        logger.warning(
            "⚠️ CORS_ALLOWED_ORIGINS에 '*'가 포함되어 있습니다. "
            "프로덕션 환경에서는 명시적 도메인만 허용해야 합니다."
        )
    
    # 프로덕션에서는 정규식 사용 안 함
    ALLOWED_ORIGIN_REGEX = None

# CORS 미들웨어는 다른 미들웨어보다 먼저 추가해야 OPTIONS 요청이 제대로 처리됨
# allow_headers는 리스트로 명시해야 함 (["*"]는 지원하지 않음)
cors_kwargs = {
    "allow_origins": ALLOWED_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    "allow_headers": [
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "Accept",
        "Accept-Language",
        "Content-Language",
    ],
    "expose_headers": ["*"],
}

# 개발 환경에서는 정규식으로 origin 허용
if os.getenv("ENVIRONMENT", "development") == "development" or DEBUG:
    cors_kwargs["allow_origin_regex"] = ALLOWED_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **cors_kwargs)

# 보안 헤더 미들웨어 (CORS 이후에 실행)
# OPTIONS 요청은 CORS preflight이므로 SecurityHeadersMiddleware에서 건너뜀
app.add_middleware(SecurityHeadersMiddleware)

# ============================================================
# 전역 에러 핸들러
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    전역 예외 처리
    
    ⚠️ 보안 주의 (AGENTS.md)
    - 상세 에러 메시지는 로그에만 기록
    - 사용자에게는 일반적인 메시지만 반환
    """
    # 로깅 (스택트레이스는 내부 로그에만)
    logger.error(
        f"Unhandled exception: {request.method} {request.url.path}",
        exc_info=True,  # 스택트레이스 포함
    )
    
    # 응답 내용 구성
    content = {
        "error": "Internal server error",
        "code": "INTERNAL_ERROR",
    }
    
    # 개발 환경에서만 상세 메시지 포함
    if DEBUG:
        content["detail"] = str(exc)
    
    return JSONResponse(
        status_code=500,
        content=content,
    )

# ============================================================
# 라우터 등록
# ============================================================

# Health check (라우터 외부)
@app.get("/health", tags=["health"])
async def health():
    """
    기본 서버 상태 확인 (간단)
    
    Kubernetes liveness probe용
    """
    return {"ok": True, "version": "0.1.0"}


@app.get("/health/ready", tags=["health"])
async def health_ready():
    """
    준비 상태 확인 (상세)
    
    Kubernetes readiness probe용
    DB, Redis, vLLM 연결 상태 확인
    """
    import httpx
    from datetime import datetime
    
    checks = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "checks": {}
    }
    all_healthy = True
    
    # 1. 데이터베이스 확인
    try:
        from .db import get_db, async_session
        async with async_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        checks["checks"]["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    # 2. Redis 확인
    try:
        from .services.cache_service import cache_service
        if cache_service._client:
            await cache_service._client.ping()
            checks["checks"]["redis"] = {"status": "healthy"}
        else:
            checks["checks"]["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    # 3. vLLM/LiteLLM 확인
    try:
        vllm_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        litellm_url = os.getenv("LITELLM_BASE_URL", "")
        
        target_url = litellm_url if litellm_url else vllm_url
        if target_url:
            # /health 또는 /models 엔드포인트 확인
            health_url = target_url.replace("/v1", "/health")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(health_url)
                if resp.status_code == 200:
                    checks["checks"]["llm"] = {"status": "healthy", "url": target_url}
                else:
                    # /models 시도
                    resp = await client.get(f"{target_url}/models")
                    if resp.status_code == 200:
                        checks["checks"]["llm"] = {"status": "healthy", "url": target_url}
                    else:
                        checks["checks"]["llm"] = {"status": "degraded", "status_code": resp.status_code}
        else:
            checks["checks"]["llm"] = {"status": "not_configured"}
    except Exception as e:
        checks["checks"]["llm"] = {"status": "unhealthy", "error": str(e)}
        # LLM 실패는 전체 실패로 처리하지 않음 (선택적 서비스)
    
    # 4. 워크스페이스 디렉토리 확인
    workspaces_dir = Path("/workspaces")
    if workspaces_dir.exists() and workspaces_dir.is_dir():
        checks["checks"]["workspaces"] = {
            "status": "healthy",
            "path": str(workspaces_dir),
            "writable": os.access(workspaces_dir, os.W_OK)
        }
    else:
        checks["checks"]["workspaces"] = {"status": "unhealthy", "error": "Directory not found"}
        all_healthy = False
    
    checks["healthy"] = all_healthy
    
    if all_healthy:
        return checks
    else:
        return JSONResponse(status_code=503, content=checks)


@app.get("/health/live", tags=["health"])
async def health_live():
    """
    생존 상태 확인 (최소)
    
    Kubernetes liveness probe용 - 앱이 응답하는지만 확인
    """
    return {"alive": True}


# 개발용 디버그 엔드포인트
@app.get("/debug/env", tags=["debug"])
def debug_env():
    """환경변수 디버깅 (개발용)"""
    import os
    from pathlib import Path
    
    env_path = Path(__file__).parent.parent / ".env"
    workspaces_dir = Path("/workspaces")
    return {
        "env_file_path": str(env_path),
        "env_file_exists": env_path.exists(),
        "workspaces_dir": str(workspaces_dir),
        "workspaces_dir_exists": workspaces_dir.exists(),
        "workspaces": [str(p) for p in workspaces_dir.iterdir()] if workspaces_dir.exists() else [],
    }


# API 라우터 등록
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(files_router)
app.include_router(ai_router)
app.include_router(patch_router)
app.include_router(admin_router)
app.include_router(container_router)  # 컨테이너 관리 라우터
app.include_router(ssh_router)        # SSH 접속 관리 라우터
app.include_router(ide_router)        # IDE (code-server) 프로비저닝 라우터
app.include_router(ai_gateway_router) # AI Gateway (LiteLLM/Tabby 통합) 라우터
app.include_router(rag_router)        # RAG (코드 검색/컨텍스트 빌더) 라우터

# WebSocket 라우터 등록
app.include_router(ws_router)

# ============================================================
# Startup / Shutdown 이벤트
# ============================================================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    logger.info("애플리케이션 시작 중...")
    
    # Prometheus 메트릭 설정
    from .middleware.metrics import setup_metrics
    setup_metrics(app)
    
    # 데이터베이스 초기화 (재시도 로직 포함)
    try:
        from .db import init_db
        await init_db()
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        # 데이터베이스 연결 실패해도 앱은 계속 실행 (나중에 재시도 가능)
        # 프로덕션에서는 여기서 종료할 수도 있음
        if os.getenv("REQUIRE_DB", "true").lower() == "true":
            raise
    
    # Redis 캐시 연결
    try:
        from .services.cache_service import cache_service
        await cache_service.connect()
    except Exception as e:
        logger.warning(f"Redis 연결 실패 (계속 진행): {e}")
        # Redis는 선택적이므로 실패해도 계속 진행
    
    logger.info("애플리케이션 시작 완료")
    # vLLM 클라이언트는 필요 시 자동 생성됨 (get_llm_client)


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    # Redis 캐시 연결 종료
    from .services.cache_service import cache_service
    await cache_service.disconnect()
    
    # LLM 클라이언트 종료
    from .llm import close_llm_client
    await close_llm_client()
