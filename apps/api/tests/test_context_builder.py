"""
Context Builder (apps/api/src/services/context_builder.py) 테스트

기존 테스트는 과거 구조(src/context_builder/...) 기준이라 현재 코드와 불일치하여
현행 ContextBuilderService에 맞게 재작성한다.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.context_builder import ContextBuilderService
from src.services.vector_store import SearchResult


@pytest.mark.asyncio
async def test_build_context_passes_scope_to_vector_store(monkeypatch):
    svc = ContextBuilderService()
    svc._embedding_service = AsyncMock()
    svc._embedding_service.embed_text.return_value = [0.0] * 8
    svc._vector_store = AsyncMock()
    svc._vector_store.search.return_value = [
        SearchResult(
            chunk_id="c1",
            score=0.9,
            content="def hello():\n    return 1",
            file_path="a.py",
            start_line=1,
            end_line=2,
            language="python",
            workspace_id="ws1",
            metadata={},
        )
    ]

    res = await svc.build_context(
        query="hello",
        workspace_id="ws1",
        tenant_id="org_default",
        project_id="prj1",
        max_results=3,
        include_file_tree=False,
    )

    assert res.workspace_id == "ws1"
    assert len(res.contexts) == 1
    svc._vector_store.search.assert_awaited()
    kwargs = svc._vector_store.search.await_args.kwargs
    assert kwargs["workspace_id"] == "ws1"
    assert kwargs["tenant_id"] == "org_default"
    assert kwargs["project_id"] == "prj1"


def test_detect_language_basic():
    svc = ContextBuilderService()
    assert svc._detect_language(".py") == "python"
    assert svc._detect_language(".ts") == "typescript"
    assert svc._detect_language(".unknown") == ""


def test_current_file_context_truncates():
    svc = ContextBuilderService()
    content = "\n".join([f"line{i}" for i in range(1, 301)])
    ctx = svc._create_current_file_context("main.py", content, max_lines=100)
    assert ctx is not None
    assert ctx.start_line == 1
    assert ctx.end_line == 100
    assert "truncated" in ctx.content
