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
import os
from pathlib import Path
from dotenv import load_dotenv

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
)

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
# CORS 설정
# ============================================================

# 환경변수에서 허용 origin 목록 가져오기
# 온프레미스 환경에서는 내부 도메인만 허용
ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

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
    # TODO: 로깅 (스택트레이스는 내부 로그에만)
    # logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            # 상세 메시지는 개발 환경에서만
            # "detail": str(exc) if DEBUG else None,
        },
    )

# ============================================================
# 라우터 등록
# ============================================================

# Health check (라우터 외부)
@app.get("/health", tags=["health"])
def health():
    """서버 상태 확인"""
    return {"ok": True, "version": "0.1.0"}


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

# WebSocket 라우터 등록
app.include_router(ws_router)

# ============================================================
# Startup / Shutdown 이벤트
# ============================================================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    # 데이터베이스 초기화
    from .db import init_db
    await init_db()
    
    # Redis 캐시 연결
    from .services.cache_service import cache_service
    await cache_service.connect()
    
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
