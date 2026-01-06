import datetime
from sqlalchemy import text
from .db import get_engine
from .config import settings

def _month_bounds(dt: datetime.date):
    start = dt.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1)
    else:
        end = start.replace(month=start.month+1)
    return start, end

async def ensure_month_partition(ts_ms: int):
    engine = get_engine()
    if not engine:
        return
    dt = datetime.datetime.utcfromtimestamp(ts_ms/1000.0).date()
    start, end = _month_bounds(dt)
    start_ms = int(datetime.datetime(start.year, start.month, 1).timestamp()*1000)
    end_ms = int(datetime.datetime(end.year, end.month, 1).timestamp()*1000)
    part = f"audit_events_{start.year}{start.month:02d}"

    async with engine.begin() as conn:
        await conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {part}
        PARTITION OF audit_events
        FOR VALUES FROM ({start_ms}) TO ({end_ms});
        """))
        # Partition local indexes
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{part}_corr ON {part}(correlation_id);"))
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{part}_proj_ts ON {part}(project_id, ts_ms);"))

async def retention_purge(now_ms: int):
    engine = get_engine()
    if not engine:
        return
    cutoff = now_ms - (settings.audit_retention_days * 24 * 60 * 60 * 1000)
    # Drop partitions older than cutoff month (simple policy). In production, use a curated list and approvals.
    async with engine.begin() as conn:
        res = await conn.execute(text("""
        SELECT inhrelid::regclass::text AS child
        FROM pg_inherits
        WHERE inhparent = 'audit_events'::regclass;
        """))
        parts = [r[0] for r in res.fetchall()]
        for p in parts:
            # parse suffix YYYYMM
            try:
                yyyymm = p.split('_')[-1]
                year = int(yyyymm[:4]); month = int(yyyymm[4:6])
                part_start = int(datetime.datetime(year, month, 1).timestamp()*1000)
                if part_start < cutoff:
                    await conn.execute(text(f"DROP TABLE IF EXISTS {p};"))
            except Exception:
                continue
