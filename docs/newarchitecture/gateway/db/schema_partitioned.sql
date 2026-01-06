-- Partitioned audit_events parent table (ts_ms range partition)
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

-- Example: create current month partition with indexes (also auto-created by app/ilm.py)
-- CREATE TABLE audit_events_202601 PARTITION OF audit_events FOR VALUES FROM (...) TO (...);
-- CREATE INDEX idx_audit_events_202601_corr ON audit_events_202601(correlation_id);
-- CREATE INDEX idx_audit_events_202601_proj_ts ON audit_events_202601(project_id, ts_ms);
