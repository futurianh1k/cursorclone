"""
SQLAlchemy 쿼리 최적화 유틸리티

N+1 쿼리 문제 방지 및 성능 최적화

참조:
- SQLAlchemy Eager Loading: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
- N+1 Problem: https://docs.sqlalchemy.org/en/20/glossary.html#term-N-plus-one-problem
"""

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload, subqueryload, load_only
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Generic, Optional, List, Type, Any
from pydantic import BaseModel

T = TypeVar("T")


# ============================================================
# Eager Loading 헬퍼
# ============================================================

def with_relationships(query, *relationships):
    """
    관계 데이터 미리 로드 (N+1 방지)
    
    사용 예:
        query = select(User)
        query = with_relationships(query, User.workspaces, User.sessions)
    """
    for rel in relationships:
        query = query.options(selectinload(rel))
    return query


def with_joined(query, *relationships):
    """
    JOIN으로 관계 데이터 로드 (1:1 또는 N:1 관계에 적합)
    
    사용 예:
        query = select(Workspace)
        query = with_joined(query, Workspace.owner)
    """
    for rel in relationships:
        query = query.options(joinedload(rel))
    return query


def with_columns(query, model, *columns):
    """
    필요한 컬럼만 로드 (대용량 데이터 방지)
    
    사용 예:
        query = select(User)
        query = with_columns(query, User, User.user_id, User.email, User.name)
    """
    return query.options(load_only(*columns))


# ============================================================
# 페이지네이션
# ============================================================

class PaginatedResult(BaseModel, Generic[T]):
    """페이지네이션 결과"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


async def paginate(
    session: AsyncSession,
    query,
    page: int = 1,
    page_size: int = 20,
    count_query=None,
) -> PaginatedResult:
    """
    쿼리 결과 페이지네이션
    
    사용 예:
        query = select(User).where(User.org_id == org_id)
        result = await paginate(session, query, page=1, page_size=20)
    """
    # 전체 개수 조회 (별도 쿼리 또는 자동)
    if count_query is None:
        # 기본: 같은 조건으로 COUNT 쿼리
        count_stmt = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0
    else:
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
    
    # 페이지 계산
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    page = max(1, min(page, total_pages))  # 범위 제한
    offset = (page - 1) * page_size
    
    # 데이터 조회
    paginated_query = query.offset(offset).limit(page_size)
    result = await session.execute(paginated_query)
    items = result.scalars().all()
    
    return PaginatedResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


# ============================================================
# 배치 처리
# ============================================================

async def batch_load(
    session: AsyncSession,
    model: Type[T],
    ids: List[str],
    id_column: str = "id",
    batch_size: int = 100,
) -> List[T]:
    """
    ID 목록으로 배치 로드 (N+1 방지)
    
    사용 예:
        users = await batch_load(session, User, user_ids, "user_id")
    """
    if not ids:
        return []
    
    results = []
    id_attr = getattr(model, id_column)
    
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        query = select(model).where(id_attr.in_(batch_ids))
        result = await session.execute(query)
        results.extend(result.scalars().all())
    
    return results


async def batch_insert(
    session: AsyncSession,
    objects: List[Any],
    batch_size: int = 100,
):
    """
    대량 삽입 (메모리 효율적)
    
    사용 예:
        await batch_insert(session, [User(...) for _ in range(1000)])
    """
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        session.add_all(batch)
        await session.flush()


# ============================================================
# 쿼리 최적화 데코레이터
# ============================================================

def optimized_query(func):
    """
    쿼리 최적화 로깅 데코레이터
    
    개발 환경에서 느린 쿼리 감지
    """
    import functools
    import time
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD_MS", "100"))
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        if elapsed_ms > slow_query_threshold:
            logger.warning(
                f"Slow query detected: {func.__name__} took {elapsed_ms:.2f}ms"
            )
        
        return result
    
    return wrapper


# ============================================================
# 예시: 최적화된 쿼리 패턴
# ============================================================

"""
# N+1 문제 발생 예시 (피해야 함):

async def get_workspaces_bad(session, org_id):
    query = select(Workspace).where(Workspace.org_id == org_id)
    result = await session.execute(query)
    workspaces = result.scalars().all()
    
    for ws in workspaces:
        # 각 워크스페이스마다 추가 쿼리 발생! (N+1)
        print(ws.owner.name)
    
    return workspaces


# 최적화된 버전 (권장):

async def get_workspaces_good(session, org_id):
    query = (
        select(Workspace)
        .where(Workspace.org_id == org_id)
        .options(
            selectinload(Workspace.owner),  # 관계 미리 로드
            load_only(Workspace.workspace_id, Workspace.name, Workspace.status)  # 필요한 컬럼만
        )
    )
    result = await session.execute(query)
    workspaces = result.scalars().all()
    
    for ws in workspaces:
        # 추가 쿼리 없음!
        print(ws.owner.name)
    
    return workspaces
"""
