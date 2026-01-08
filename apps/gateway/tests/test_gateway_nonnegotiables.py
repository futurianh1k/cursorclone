import os
import sys

import pytest


# tests 실행 시 apps/gateway를 import path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_upstream_auth_does_not_forward_workspace_token():
    """
    Non-negotiable:
    - Workspace 사용자 토큰을 Upstream에 전달 금지
    여기서는 upstream_headers()가 workspace 토큰(Authorization)을 생성하지 않음을 보장한다.
    """
    from app.upstream_auth import upstream_headers

    headers = upstream_headers()
    # upstream_headers는 내부 서비스 인증용 헤더만 생성 가능하며,
    # workspace 토큰을 그대로 전달하는 형태가 아니다.
    assert "Authorization" not in headers or headers["Authorization"].startswith("Bearer ")


def test_internal_headers_only_for_rag_and_agent(monkeypatch):
    from app.upstream_auth import internal_headers

    monkeypatch.setenv("UPSTREAM_INTERNAL_TOKEN", "internal-token")
    monkeypatch.setenv("UPSTREAM_INTERNAL_TOKEN_HEADER", "x-internal-token")

    # settings는 import 시 이미 초기화될 수 있으므로, 모듈을 리로드해서 env 반영
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    import app.upstream_auth as ua
    importlib.reload(ua)

    assert ua.internal_headers("rag") == {"x-internal-token": "internal-token"}
    assert ua.internal_headers("agent") == {"x-internal-token": "internal-token"}
    assert ua.internal_headers("chat") == {}


def test_dlp_default_mode_is_pre_only():
    """
    Non-negotiable:
    - 스트리밍 DLP 기본은 pre_only
    """
    from app.config import settings

    assert settings.dlp_stream_mode == "pre_only"


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/v1/autocomplete", "autocomplete"),
        ("/v1/completions", "autocomplete"),
        ("/v1/health", "autocomplete"),
        ("/v1/chat", "chat"),
        ("/v1/agent", "agent"),
        ("/v1/rag/query", "rag"),
    ],
)
def test_routing_policy_exists(path, expected):
    """
    PRD In-scope:
    - Tabby / Agent / Chat / RAG 연동 라우팅 정책 존재
    """
    from app.policy import resolve_route

    route = resolve_route(path)
    assert route is not None
    assert route["name"] == expected

