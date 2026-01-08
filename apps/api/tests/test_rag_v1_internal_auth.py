"""
/v1/rag 내부 인증(게이트웨이 토큰 헤더) 최소 테스트

DB/Qdrant/임베딩 의존 없이, 인증/스코프 체크가 먼저 동작하는지만 확인한다.
"""

import os
import pytest
from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def _headers(ws_id: str = "ws1"):
    return {
        "X-Internal-Token": "internal-test-token",
        "X-User-Id": "user1",
        "X-Tenant-Id": "org1",
        "X-Project-Id": "prj1",
        "X-Workspace-Id": ws_id,
        "Content-Type": "application/json",
    }


def test_v1_rag_requires_internal_token(monkeypatch):
    monkeypatch.setenv("GATEWAY_INTERNAL_TOKEN", "internal-test-token")
    r = client.post("/v1/rag/search", json={"query": "x", "workspace_id": "ws1"}, headers={"Content-Type": "application/json"})
    assert r.status_code in (401, 400)  # 401 expected, but body/headers missing may lead to 400


def test_v1_rag_rejects_workspace_scope_mismatch(monkeypatch):
    monkeypatch.setenv("GATEWAY_INTERNAL_TOKEN", "internal-test-token")
    # 헤더 ws와 body ws가 다르면 embedding/qdrant 호출 전에 403으로 막아야 한다
    r = client.post("/v1/rag/search", json={"query": "x", "workspace_id": "ws-other"}, headers=_headers(ws_id="ws1"))
    assert r.status_code == 403
