"""
Alembic 마이그레이션 환경 설정

환경변수:
- DATABASE_URL: PostgreSQL 연결 URL

사용법:
- alembic revision --autogenerate -m "설명"
- alembic upgrade head
- alembic downgrade -1
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 모델 import (autogenerate를 위해)
from src.db.connection import Base
from src.db.models import (
    OrganizationModel,
    UserModel,
    WorkspaceModel,
    WorkspaceResourceModel,
    AuditLogModel,
    InfrastructureServerModel,
    ServerCredentialModel,
    WorkspacePlacementModel,
    PlacementPolicyModel,
    UserSessionModel,
)

# Alembic Config 객체
config = context.config

# 환경변수에서 DATABASE_URL 가져오기
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://cursor:cursor@localhost:5432/cursor_poc"
)

# asyncpg를 psycopg2로 변경 (Alembic은 동기 드라이버 사용)
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

config.set_main_option("sqlalchemy.url", database_url)

# Python 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 모델 메타데이터 (autogenerate 지원)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    오프라인 모드로 마이그레이션 실행
    
    데이터베이스 연결 없이 SQL 스크립트만 생성합니다.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 컬럼 타입 변경 감지
        compare_server_default=True,  # 기본값 변경 감지
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    온라인 모드로 마이그레이션 실행
    
    실제 데이터베이스에 연결하여 마이그레이션을 실행합니다.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 컬럼 타입 변경 감지
            compare_server_default=True,  # 기본값 변경 감지
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
