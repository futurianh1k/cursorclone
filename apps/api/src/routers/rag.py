"""
RAG (Retrieval-Augmented Generation) API 라우터
코드베이스 인덱싱 및 컨텍스트 검색 엔드포인트

- POST /api/rag/index - 워크스페이스 인덱싱
- GET /api/rag/index/{workspace_id} - 인덱싱 상태 조회
- POST /api/rag/search - 코드 검색
- POST /api/rag/context - 컨텍스트 빌드
- DELETE /api/rag/index/{workspace_id} - 인덱스 삭제
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import WorkspaceModel, UserModel
from ..db.connection import get_db
from ..services.rbac_service import get_current_user
from ..services.code_indexer import get_code_indexer, IndexingProgress
from ..services.context_builder import get_context_builder
from ..services.vector_store import get_vector_store
from ..services.embedding_service import get_embedding_service
from ..utils.filesystem import get_workspace_root

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


# ============================================================
# Request/Response Models
# ============================================================

class IndexWorkspaceRequest(BaseModel):
    """워크스페이스 인덱싱 요청"""
    workspace_id: str = Field(..., description="워크스페이스 ID")
    force_reindex: bool = Field(False, description="강제 재인덱싱 여부")


class IndexingStatusResponse(BaseModel):
    """인덱싱 상태 응답"""
    workspace_id: str
    status: str
    total_files: int
    indexed_files: int
    total_chunks: int
    indexed_chunks: int
    progress_percent: float
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """코드 검색 요청"""
    query: str = Field(..., min_length=1, description="검색 쿼리")
    workspace_id: str = Field(..., description="워크스페이스 ID")
    limit: int = Field(10, ge=1, le=50, description="최대 결과 수")
    file_filter: Optional[str] = Field(None, description="파일 경로 필터")
    language_filter: Optional[str] = Field(None, description="언어 필터")


class SearchResultItem(BaseModel):
    """검색 결과 항목"""
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    relevance_score: float


class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    results: List[SearchResultItem]
    total_results: int


class ContextRequest(BaseModel):
    """컨텍스트 빌드 요청"""
    query: str = Field(..., min_length=1, description="사용자 질문/요청")
    workspace_id: str = Field(..., description="워크스페이스 ID")
    max_results: int = Field(10, ge=1, le=20, description="최대 검색 결과 수")
    include_file_tree: bool = Field(False, description="파일 트리 포함 여부")
    current_file: Optional[str] = Field(None, description="현재 편집 중인 파일 경로")
    current_file_content: Optional[str] = Field(None, description="현재 파일 내용")
    task_type: Optional[str] = Field(
        None,
        description="작업 유형(선택). 미지정 시 서버에서 휴리스틱 분류. 예: autocomplete/refactor/bugfix/explain/search/chat",
    )
    max_context_tokens: Optional[int] = Field(
        None,
        ge=256,
        le=12000,
        description="컨텍스트 토큰 예산(선택). 미지정 시 서버 기본값 사용",
    )
    max_context_chars: Optional[int] = Field(
        None,
        ge=1024,
        le=200000,
        description="컨텍스트 문자 예산(선택). 미지정 시 서버 기본값 사용",
    )


class ContextItem(BaseModel):
    """컨텍스트 항목"""
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    relevance_score: float


class ContextResponse(BaseModel):
    """컨텍스트 응답"""
    query: str
    contexts: List[ContextItem]
    file_tree: Optional[str] = None
    prompt: str
    total_chars: int
    truncated: bool


class RelatedFile(BaseModel):
    """관련 파일"""
    file_path: str
    relevance_score: float


class StatsResponse(BaseModel):
    """통계 응답"""
    vectors_count: int
    points_count: int
    status: str
    config: dict


# ============================================================
# 엔드포인트
# ============================================================

@router.post(
    "/index",
    response_model=IndexingStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="워크스페이스 인덱싱 시작",
    description="워크스페이스의 코드 파일을 벡터 DB에 인덱싱합니다. 백그라운드에서 실행됩니다.",
)
async def index_workspace(
    request: IndexWorkspaceRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """워크스페이스 인덱싱 시작"""
    # 워크스페이스 존재 확인
    result = await db.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == request.workspace_id,
            WorkspaceModel.owner_id == current_user.user_id,
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    # 워크스페이스 경로
    workspace_path = get_workspace_root(request.workspace_id)
    
    # 백그라운드에서 인덱싱 실행
    async def run_indexing():
        try:
            indexer = await get_code_indexer()
            # 증분 인덱싱(기본) + 강제 재인덱싱 옵션 지원
            await indexer.index_workspace_incremental(
                workspace_id=request.workspace_id,
                workspace_path=str(workspace_path),
                db=db,
                tenant_id=current_user.org_id,
                project_id=workspace.project_id,
                force_reindex=request.force_reindex,
            )
        except Exception as e:
            logger.error(f"Background indexing failed: {e}")
    
    background_tasks.add_task(run_indexing)
    
    logger.info(f"Indexing started for workspace: {request.workspace_id}")
    
    return IndexingStatusResponse(
        workspace_id=request.workspace_id,
        status="running",
        total_files=0,
        indexed_files=0,
        total_chunks=0,
        indexed_chunks=0,
        progress_percent=0.0,
    )


@router.get(
    "/index/{workspace_id}",
    response_model=IndexingStatusResponse,
    summary="인덱싱 상태 조회",
    description="워크스페이스 인덱싱 진행 상태를 조회합니다.",
)
async def get_indexing_status(
    workspace_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """인덱싱 상태 조회"""
    indexer = await get_code_indexer()
    progress = indexer.get_progress(workspace_id)
    
    if not progress:
        # 진행 중인 인덱싱 없음 - 완료된 것으로 간주
        return IndexingStatusResponse(
            workspace_id=workspace_id,
            status="completed",
            total_files=0,
            indexed_files=0,
            total_chunks=0,
            indexed_chunks=0,
            progress_percent=100.0,
        )
    
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


@router.delete(
    "/index/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="인덱스 삭제",
    description="워크스페이스의 벡터 인덱스를 삭제합니다.",
)
async def delete_index(
    workspace_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """인덱스 삭제"""
    # 워크스페이스 소유권 확인
    result = await db.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == workspace_id,
            WorkspaceModel.owner_id == current_user.user_id,
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    indexer = await get_code_indexer()
    await indexer.delete_workspace_index(workspace_id)
    
    logger.info(f"Index deleted for workspace: {workspace_id}")


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="코드 검색",
    description="쿼리와 관련된 코드 청크를 검색합니다.",
)
async def search_code(
    request: SearchRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """코드 검색"""
    embedding_service = await get_embedding_service()
    vector_store = await get_vector_store()

    # 스코프 확보 (workspace -> project/tenant)
    result = await db.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == request.workspace_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    
    # 쿼리 임베딩
    query_embedding = await embedding_service.embed_text(request.query)
    
    # 검색
    results = await vector_store.search(
        query_embedding=query_embedding,
        workspace_id=request.workspace_id,
        tenant_id=current_user.org_id,
        project_id=workspace.project_id,
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


@router.post(
    "/context",
    response_model=ContextResponse,
    summary="컨텍스트 빌드",
    description="LLM 프롬프트를 위한 관련 코드 컨텍스트를 구성합니다.",
)
async def build_context(
    request: ContextRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """컨텍스트 빌드"""
    # 워크스페이스 경로 조회
    result = await db.execute(
        select(WorkspaceModel).where(
            WorkspaceModel.workspace_id == request.workspace_id,
        )
    )
    workspace = result.scalar_one_or_none()
    
    workspace_path = None
    if workspace:
        workspace_path = str(get_workspace_root(request.workspace_id))
    
    context_builder = await get_context_builder()
    
    context_result = await context_builder.build_context(
        query=request.query,
        workspace_id=request.workspace_id,
        tenant_id=current_user.org_id,
        project_id=workspace.project_id if workspace else None,
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


@router.get(
    "/related-files",
    response_model=List[RelatedFile],
    summary="관련 파일 조회",
    description="쿼리와 관련된 파일 목록을 조회합니다.",
)
async def get_related_files(
    query: str,
    workspace_id: str,
    limit: int = 5,
    current_user: UserModel = Depends(get_current_user),
):
    """관련 파일 조회"""
    context_builder = await get_context_builder()
    
    files = await context_builder.get_related_files(
        query=query,
        workspace_id=workspace_id,
        limit=limit,
    )
    
    return [
        RelatedFile(
            file_path=f["file_path"],
            relevance_score=f["relevance_score"],
        )
        for f in files
    ]


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="벡터 DB 통계",
    description="벡터 데이터베이스의 통계 정보를 조회합니다.",
)
async def get_stats(
    current_user: UserModel = Depends(get_current_user),
):
    """벡터 DB 통계"""
    vector_store = await get_vector_store()
    stats = await vector_store.get_collection_stats()
    
    return StatsResponse(
        vectors_count=stats.get("vectors_count", 0),
        points_count=stats.get("points_count", 0),
        status=stats.get("status", "unknown"),
        config=stats.get("config", {}),
    )
