import json
import time
from typing import Optional
from sqlalchemy import text
from .auth import Identity
from .db import get_session_factory
from .ilm import ensure_month_partition

def emit_audit_stdout(event: dict):
    print(json.dumps(event, ensure_ascii=False))

async def persist_audit_db(event: dict):
    sf = get_session_factory()
    if not sf:
        return
    ts_ms = int(event.get("timestamp") or 0)
    await ensure_month_partition(ts_ms)

    async with sf() as session:
        await session.execute(text("""
            INSERT INTO audit_events(
                ts_ms, correlation_id, tenant_id, project_id, workspace_id, user_id,
                endpoint, route_target, policy_version, dlp_action, dlp_rule_id,
                status_code, latency_ms, input_tokens, output_tokens, diff_hash,
                changed_files_hash, extra
            ) VALUES (
                :ts_ms, :correlation_id, :tenant_id, :project_id, :workspace_id, :user_id,
                :endpoint, :route_target, :policy_version, :dlp_action, :dlp_rule_id,
                :status_code, :latency_ms, :input_tokens, :output_tokens, :diff_hash,
                :changed_files_hash, :extra
            )
        """), {
            "ts_ms": ts_ms,
            "correlation_id": event.get("correlation_id"),
            "tenant_id": event.get("tenant_id"),
            "project_id": event.get("project_id"),
            "workspace_id": event.get("workspace_id"),
            "user_id": event.get("user_id"),
            "endpoint": event.get("endpoint"),
            "route_target": event.get("route_target"),
            "policy_version": event.get("policy_version"),
            "dlp_action": event.get("dlp_action"),
            "dlp_rule_id": event.get("dlp_rule_id"),
            "status_code": event.get("status_code"),
            "latency_ms": event.get("latency_ms"),
            "input_tokens": event.get("input_tokens"),
            "output_tokens": event.get("output_tokens"),
            "diff_hash": event.get("diff_hash"),
            "changed_files_hash": event.get("changed_files_hash"),
            "extra": json.dumps(event.get("extra") or {}),
        })
        await session.commit()

async def emit_audit(identity: Identity, correlation_id: str, path: str, status_code: int, latency_ms: int,
                     route_target: str, policy_version: str, dlp_action: str, dlp_rule_id: Optional[str] = None,
                     input_tokens: Optional[int] = None, output_tokens: Optional[int] = None,
                     diff_hash: Optional[str] = None, changed_files_hash: Optional[str] = None, extra: Optional[dict] = None):
    event = {
        "timestamp": int(time.time()*1000),
        "correlation_id": correlation_id,
        "tenant_id": identity.tenant_id,
        "project_id": identity.project_id,
        "workspace_id": identity.workspace_id,
        "user_id": identity.user_id,
        "endpoint": path,
        "route_target": route_target,
        "policy_version": policy_version,
        "dlp_action": dlp_action,
        "dlp_rule_id": dlp_rule_id,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "diff_hash": diff_hash,
        "changed_files_hash": changed_files_hash,
        "extra": extra or {},
    }
    emit_audit_stdout(event)
    await persist_audit_db(event)
