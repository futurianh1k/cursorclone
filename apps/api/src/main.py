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

from .routers import (
    auth_router,
    workspaces_router,
    files_router,
    ai_router,
    patch_router,
    ws_router,
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


# API 라우터 등록
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(files_router)
app.include_router(ai_router)
app.include_router(patch_router)

# WebSocket 라우터 등록
app.include_router(ws_router)

# ============================================================
# Startup / Shutdown 이벤트
# ============================================================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    # TODO: 초기화 작업
    # - DB 연결
    # - vLLM 클라이언트 초기화
    # - 설정 로드
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    # TODO: 정리 작업
    # - DB 연결 종료
    # - 리소스 정리
    pass
