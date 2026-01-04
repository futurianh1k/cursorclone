"""
데이터베이스 연결 관리
대규모 스케일링을 위한 연결 풀 및 비동기 쿼리 지원
"""

import os
import asyncio
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# 데이터베이스 URL (환경변수에서 가져오기)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc"
)

# 비동기 엔진 생성 (연결 풀 설정)
# asyncpg의 경우 connect_args에 timeout 설정
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # SQL 로깅 (개발 시 True)
    pool_size=20,  # 연결 풀 크기 (동시 연결 수)
    max_overflow=40,  # 추가 연결 허용
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_recycle=3600,  # 1시간마다 연결 재생성
    connect_args={
        "server_settings": {
            "application_name": "cursor_poc_api",
        },
        "command_timeout": 10,  # asyncpg 명령 타임아웃 (초)
    },
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
    """데이터베이스 초기화 (테이블 생성) - 재시도 로직 포함"""
    max_retries = 10  # 재시도 횟수 증가
    base_delay = 2  # 초
    retry_delay = base_delay
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"데이터베이스 연결 시도 {attempt}/{max_retries}...")
            # 연결 테스트 및 테이블 생성
            async with engine.begin() as conn:
                # 테이블 생성
                await conn.run_sync(Base.metadata.create_all)
            logger.info("데이터베이스 초기화 완료")
            return
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # DNS 해석 실패 또는 연결 거부 오류인 경우
            is_network_error = (
                "name resolution" in error_msg.lower() or 
                "temporary failure" in error_msg.lower() or 
                "connection refused" in error_msg.lower() or
                "gaierror" in error_type.lower()
            )
            
            if attempt < max_retries:
                logger.warning(
                    f"데이터베이스 연결 실패 (시도 {attempt}/{max_retries}): {error_type}: {error_msg}. "
                    f"{retry_delay}초 후 재시도..."
                )
                await asyncio.sleep(retry_delay)
                # 지수 백오프 (최대 30초)
                retry_delay = min(base_delay * (2 ** (attempt - 1)), 30)
            else:
                logger.error(f"데이터베이스 연결 최종 실패 ({max_retries}회 시도): {error_type}: {error_msg}")
                raise
