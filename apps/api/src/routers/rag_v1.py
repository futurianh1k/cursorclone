"""
Gateway 경유 RAG 라우터 (Financial VDE)

- Gateway가 /v1/rag 로 호출
- API는 Gateway 내부 토큰(X-Internal-Token) + Identity 헤더(X-User-Id/X-Tenant-Id/X-Project-Id/X-Workspace-Id)만 신뢰
- workspace 사용자 토큰(Authorization)은 upstream으로 전달하지 않는다
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import WorkspaceModel
from ..db.connection import get_db
from ..services.internal_gateway_auth import GatewayRequestIdentity, require_gateway_internal
from ..services.code_indexer import get_code_indexer
from ..services.context_builder import get_context_builder
from ..services.vector_store import get_vector_store
from ..services.embedding_service import get_embedding_service
from ..utils.filesystem import get_workspace_root

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["rag-v1"])


class IndexWorkspaceRequest(BaseModel):
    workspace_id: str = Field(..., description="워크스페이스 ID")
    force_reindex: bool = Field(False, description="강제 재인덱싱 여부")


class IndexingStatusResponse(BaseModel):
    workspace_id: str
    status: str
    total_files: int = 0
    indexed_files: int = 0
    total_chunks: int = 0
    indexed_chunks: int = 0
    progress_percent: float = 0.0
    error: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="검색 쿼리")
    workspace_id: str = Field(..., description="워크스페이스 ID")
    limit: int = Field(10, ge=1, le=50)
    file_filter: Optional[str] = None
    language_filter: Optional[str] = None


class SearchResultItem(BaseModel):
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_results: int


class ContextRequest(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: str
    max_results: int = Field(10, ge=1, le=20)
    include_file_tree: bool = False
    current_file: Optional[str] = None
    current_file_content: Optional[str] = None
    task_type: Optional[str] = None
    max_context_tokens: Optional[int] = Field(None, ge=256, le=12000)
    max_context_chars: Optional[int] = Field(None, ge=1024, le=200000)


class ContextItem(BaseModel):
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    relevance_score: float


class ContextResponse(BaseModel):
    query: str
    contexts: List[ContextItem]
    file_tree: Optional[str] = None
    prompt: str
    total_chars: int
    truncated: bool


class RelatedFile(BaseModel):
    file_path: str
    relevance_score: float


class StatsResponse(BaseModel):
    vectors_count: int
    points_count: int
    status: str
    config: dict


async def _load_workspace_and_check_scope(db: AsyncSession, req_ws_id: str, ident: GatewayRequestIdentity) -> WorkspaceModel:
    if req_ws_id != ident.workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace scope mismatch")

    result = await db.execute(select(WorkspaceModel).where(WorkspaceModel.workspace_id == req_ws_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # tenant/project 스코프도 강제
    if getattr(ws, "org_id", None) and ws.org_id != ident.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant scope mismatch")
    if getattr(ws, "project_id", None) and ws.project_id != ident.project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project scope mismatch")
    return ws


@router.post("/index", response_model=IndexingStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def index_workspace(
    request: IndexWorkspaceRequest,
    background_tasks: BackgroundTasks,
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
    db: AsyncSession = Depends(get_db),
):
    ws = await _load_workspace_and_check_scope(db, request.workspace_id, ident)
    workspace_path = get_workspace_root(request.workspace_id)

    async def run_indexing():
        try:
            indexer = await get_code_indexer()
            await indexer.index_workspace_incremental(
                workspace_id=request.workspace_id,
                workspace_path=str(workspace_path),
                db=db,
                tenant_id=ident.tenant_id,
                project_id=ws.project_id,
                force_reindex=request.force_reindex,
            )
        except Exception as e:
            logger.error(f"Gateway indexing failed: {e}")

    background_tasks.add_task(run_indexing)
    return IndexingStatusResponse(workspace_id=request.workspace_id, status="running")


@router.get("/index/{workspace_id}", response_model=IndexingStatusResponse)
async def get_indexing_status(
    workspace_id: str,
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
):
    if workspace_id != ident.workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace scope mismatch")
    indexer = await get_code_indexer()
    progress = indexer.get_progress(workspace_id)
    if not progress:
        return IndexingStatusResponse(workspace_id=workspace_id, status="completed", progress_percent=100.0)
    return IndexingStatusResponse(
        workspace_id=progress.workspace_id,
        status=progress.status,
        total_files=progress.total_files,
        indexed_files=progress.indexed_files,
        total_chunks=progress.total_chunks,
        indexed_chunks=progress.indexed_chunks,
        progress_percent=progress.progress_percent,
        error=progress.error,
    )


@router.delete("/index/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_index(
    workspace_id: str,
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
    db: AsyncSession = Depends(get_db),
):
    ws = await _load_workspace_and_check_scope(db, workspace_id, ident)
    indexer = await get_code_indexer()
    ok = await indexer.delete_workspace_index(workspace_id=workspace_id, db_session=db)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete index")
    return None


@router.post("/search", response_model=SearchResponse)
async def search_code(
    request: SearchRequest,
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
    db: AsyncSession = Depends(get_db),
):
    ws = await _load_workspace_and_check_scope(db, request.workspace_id, ident)
    embedding_service = await get_embedding_service()
    vector_store = await get_vector_store()
    query_embedding = await embedding_service.embed_text(request.query)
    results = await vector_store.search(
        query_embedding=query_embedding,
        workspace_id=request.workspace_id,
        tenant_id=ident.tenant_id,
        project_id=ws.project_id,
        limit=request.limit,
        file_filter=request.file_filter,
        language_filter=request.language_filter,
    )
    return SearchResponse(
        query=request.query,
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                file_path=r.file_path,
                content=r.content,
                start_line=r.start_line,
                end_line=r.end_line,
                language=r.language,
                relevance_score=r.score,
            )
            for r in results
        ],
        total_results=len(results),
    )


@router.post("/context", response_model=ContextResponse)
async def build_context(
    request: ContextRequest,
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
    db: AsyncSession = Depends(get_db),
):
    ws = await _load_workspace_and_check_scope(db, request.workspace_id, ident)
    workspace_path = str(get_workspace_root(request.workspace_id))
    context_builder = await get_context_builder()
    context_result = await context_builder.build_context(
        query=request.query,
        workspace_id=request.workspace_id,
        tenant_id=ident.tenant_id,
        project_id=ws.project_id,
        workspace_path=workspace_path,
        max_results=request.max_results,
        include_file_tree=request.include_file_tree,
        current_file=request.current_file,
        current_file_content=request.current_file_content,
        task_type=request.task_type,
        max_context_tokens=request.max_context_tokens,
        max_context_chars=request.max_context_chars,
    )
    return ContextResponse(
        query=context_result.query,
        contexts=[
            ContextItem(
                file_path=ctx.file_path,
                content=ctx.content,
                start_line=ctx.start_line,
                end_line=ctx.end_line,
                language=ctx.language,
                relevance_score=ctx.relevance_score,
            )
            for ctx in context_result.contexts
        ],
        file_tree=context_result.file_tree,
        prompt=context_result.to_prompt(),
        total_chars=context_result.total_chars,
        truncated=context_result.truncated,
    )


@router.get("/related-files", response_model=List[RelatedFile])
async def get_related_files(
    query: str,
    workspace_id: str,
    limit: int = 5,
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
    db: AsyncSession = Depends(get_db),
):
    ws = await _load_workspace_and_check_scope(db, workspace_id, ident)
    context_builder = await get_context_builder()
    files = await context_builder.get_related_files(query=query, workspace_id=workspace_id, limit=limit)
    return [RelatedFile(file_path=f["file_path"], relevance_score=f["relevance_score"]) for f in files]


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    ident: GatewayRequestIdentity = Depends(require_gateway_internal),
):
    vector_store = await get_vector_store()
    stats = await vector_store.get_collection_stats()
    return StatsResponse(
        vectors_count=stats.get("vectors_count", 0),
        points_count=stats.get("points_count", 0),
        status=stats.get("status", "unknown"),
        config=stats.get("config", {}),
    )

