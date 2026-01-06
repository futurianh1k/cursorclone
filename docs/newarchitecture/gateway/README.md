# AI Gateway (FastAPI) — v0.3 (Ops-ready)

## New (v0.3)
- JWKS cache/refresh strategy + fail-open/close
- Upstream auth separation (do NOT forward workspace token)
- Streaming DLP policy clarified (pre + incremental optional)
- Audit DB partitioning schema + retention job design
- OpenAPI spec pinned: scripts generate/verify `openapi.json`

## Run (dev)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export JWT_DEV_MODE=true
export UPSTREAM_AUTH_MODE=none
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

## Ops env (core)
### JWT / JWKS
- `JWT_JWKS_URL` or `JWT_JWKS_FILE`
- `JWT_JWKS_CACHE_TTL_SECONDS` (default: 300)
- `JWT_JWKS_REFRESH_SECONDS` (default: 60)
- `JWT_JWKS_FAIL_OPEN` (default: false)

### Upstream Auth Separation
- `UPSTREAM_AUTH_MODE` = `none` | `static_bearer` | `mtls`
- `UPSTREAM_BEARER_TOKEN` (when static_bearer)
- `UPSTREAM_CA_FILE`, `UPSTREAM_CLIENT_CERT_FILE`, `UPSTREAM_CLIENT_KEY_FILE` (when mtls)

### Streaming DLP
- `DLP_STREAM_MODE` = `pre_only` | `pre_and_incremental`
- `DLP_STREAM_MAX_BUFFER_BYTES` (default: 1048576)

### Audit/ILM
- `AUDIT_DB_DSN`
- `AUDIT_RETENTION_DAYS` (default: 365)

## OpenAPI pin
- `scripts/generate_openapi.py` generates `openapi/openapi.json`
- `scripts/verify_openapi.py` verifies current runtime schema matches pinned
