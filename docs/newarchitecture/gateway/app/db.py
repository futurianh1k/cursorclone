from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from .config import settings

_engine: Optional[AsyncEngine] = None
_session_factory = None

def get_engine() -> Optional[AsyncEngine]:
    global _engine, _session_factory
    if not settings.audit_db_dsn:
        return None
    if _engine is None:
        _engine = create_async_engine(settings.audit_db_dsn, pool_pre_ping=True)
        _session_factory = sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine

def get_session_factory():
    get_engine()
    return _session_factory

async def ensure_schema():
    if not settings.audit_db_dsn:
        return
    engine = get_engine()
    async with engine.begin() as conn:
        # Parent partitioned table
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id BIGSERIAL NOT NULL,
            ts_ms BIGINT NOT NULL,
            correlation_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            route_target TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            dlp_action TEXT NOT NULL,
            dlp_rule_id TEXT,
            status_code INT NOT NULL,
            latency_ms INT NOT NULL,
            input_tokens INT,
            output_tokens INT,
            diff_hash TEXT,
            changed_files_hash TEXT,
            extra JSONB,
            PRIMARY KEY (id, ts_ms)
        ) PARTITION BY RANGE (ts_ms);
        """))
        # indexes on parent are not automatically created on partitions; we create per-partition in job/script.
