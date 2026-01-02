"""
데이터베이스 연결 관리
대규모 스케일링을 위한 연결 풀 및 비동기 쿼리 지원
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

# 데이터베이스 URL (환경변수에서 가져오기)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc"
)

# 비동기 엔진 생성 (연결 풀 설정)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # SQL 로깅 (개발 시 True)
    pool_size=20,  # 연결 풀 크기 (동시 연결 수)
    max_overflow=40,  # 추가 연결 허용
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_recycle=3600,  # 1시간마다 연결 재생성
)

# 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base 클래스
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션 의존성
    
    사용 예:
        @router.get("/api/workspaces")
        async def list_workspaces(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
