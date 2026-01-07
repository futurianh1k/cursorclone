"""
Prometheus Metrics 미들웨어

API 메트릭 수집 및 노출

참조:
- prometheus-fastapi-instrumentator: https://github.com/trallnag/prometheus-fastapi-instrumentator
- Prometheus 문서: https://prometheus.io/docs/
"""

import os
import time
from prometheus_client import Counter, Histogram, Gauge, Info
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_fastapi_instrumentator import Instrumentator, metrics  # type: ignore
    _INSTRUMENTATOR_AVAILABLE = True
except ImportError:  # pragma: no cover
    # 테스트/제한된 환경에서는 instrumentator 미설치로도 앱이 로드되게 한다.
    # TODO: 운영 환경에서는 의존성을 강제하고, ENABLE_METRICS 사용 시 설치 여부를 검증할 것.
    _INSTRUMENTATOR_AVAILABLE = False

# ============================================================
# 커스텀 메트릭 정의
# ============================================================

# AI 요청 메트릭
AI_REQUEST_COUNTER = Counter(
    "ai_requests_total",
    "Total AI requests",
    ["mode", "status", "model"]
)

AI_REQUEST_LATENCY = Histogram(
    "ai_request_duration_seconds",
    "AI request latency",
    ["mode", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

AI_TOKEN_COUNTER = Counter(
    "ai_tokens_total",
    "Total tokens used",
    ["direction", "model"]  # direction: input/output
)

# 워크스페이스 메트릭
WORKSPACE_GAUGE = Gauge(
    "workspaces_active",
    "Number of active workspaces",
    ["status"]
)

# IDE 컨테이너 메트릭
IDE_CONTAINER_GAUGE = Gauge(
    "ide_containers_active",
    "Number of active IDE containers",
    ["status"]
)

# 인증 메트릭
AUTH_COUNTER = Counter(
    "auth_attempts_total",
    "Authentication attempts",
    ["action", "status"]  # action: login/signup/refresh, status: success/failure
)

# Rate Limit 메트릭
RATE_LIMIT_COUNTER = Counter(
    "rate_limit_hits_total",
    "Rate limit hits",
    ["endpoint"]
)

# 앱 정보
APP_INFO = Info(
    "cursor_onprem",
    "Application information"
)


def setup_metrics(app: FastAPI):
    """
    Prometheus 메트릭 설정
    
    /metrics 엔드포인트 노출
    """
    if not _INSTRUMENTATOR_AVAILABLE:
        logger.warning("prometheus_fastapi_instrumentator 미설치: metrics 설정을 스킵합니다.")
        return

    # 환경 정보 설정
    APP_INFO.info({
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Instrumentator 설정
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    
    # 기본 메트릭 추가
    instrumentator.add(
        metrics.default(
            metric_namespace="cursor_onprem",
            metric_subsystem="api",
        )
    )
    
    # 요청 크기 메트릭
    instrumentator.add(
        metrics.request_size(
            metric_namespace="cursor_onprem",
            metric_subsystem="api",
        )
    )
    
    # 응답 크기 메트릭
    instrumentator.add(
        metrics.response_size(
            metric_namespace="cursor_onprem",
            metric_subsystem="api",
        )
    )
    
    # 지연 시간 히스토그램
    instrumentator.add(
        metrics.latency(
            metric_namespace="cursor_onprem",
            metric_subsystem="api",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )
    )
    
    # 앱에 연결
    instrumentator.instrument(app)
    
    # /metrics 엔드포인트 노출
    instrumentator.expose(
        app,
        include_in_schema=True,
        tags=["monitoring"],
    )
    
    logger.info("Prometheus metrics initialized at /metrics")
    
    return instrumentator


# ============================================================
# 메트릭 기록 헬퍼 함수
# ============================================================

def record_ai_request(mode: str, model: str, status: str, duration: float, tokens_in: int = 0, tokens_out: int = 0):
    """AI 요청 메트릭 기록"""
    AI_REQUEST_COUNTER.labels(mode=mode, status=status, model=model).inc()
    AI_REQUEST_LATENCY.labels(mode=mode, model=model).observe(duration)
    
    if tokens_in > 0:
        AI_TOKEN_COUNTER.labels(direction="input", model=model).inc(tokens_in)
    if tokens_out > 0:
        AI_TOKEN_COUNTER.labels(direction="output", model=model).inc(tokens_out)


def record_auth_attempt(action: str, success: bool):
    """인증 시도 메트릭 기록"""
    status = "success" if success else "failure"
    AUTH_COUNTER.labels(action=action, status=status).inc()


def record_rate_limit_hit(endpoint: str):
    """Rate Limit 히트 기록"""
    RATE_LIMIT_COUNTER.labels(endpoint=endpoint).inc()


def update_workspace_gauge(active: int, pending: int = 0, stopped: int = 0):
    """워크스페이스 게이지 업데이트"""
    WORKSPACE_GAUGE.labels(status="active").set(active)
    WORKSPACE_GAUGE.labels(status="pending").set(pending)
    WORKSPACE_GAUGE.labels(status="stopped").set(stopped)


def update_ide_container_gauge(running: int, pending: int = 0, stopped: int = 0):
    """IDE 컨테이너 게이지 업데이트"""
    IDE_CONTAINER_GAUGE.labels(status="running").set(running)
    IDE_CONTAINER_GAUGE.labels(status="pending").set(pending)
    IDE_CONTAINER_GAUGE.labels(status="stopped").set(stopped)
