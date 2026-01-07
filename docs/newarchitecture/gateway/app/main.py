from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import time
import json
import asyncio
import orjson

from .config import settings
from .auth import AuthError, Identity
from .auth_async import verify_bearer_token_async
from .authorize import authorize_path
from .policy import resolve_route
from .dlp import dlp_engine
from .audit import emit_audit
from .metrics import init_metrics, observe_request, observe_tokens
from .diffhash import extract_unified_diff_from_json, sha256_text
from .db import ensure_schema
from .jwks_cache import jwks_cache
from .upstream_auth import upstream_headers, httpx_verify_and_cert
from .ilm import retention_purge

app = FastAPI(title="AI Gateway", version="0.3.0")
init_metrics(app)

@app.on_event("startup")
async def on_startup():
    await ensure_schema()
    # JWKS background refresh (only when URL is set)
    if settings.jwt_jwks_url:
        asyncio.create_task(jwks_cache.start_background_refresh())

@app.on_event("shutdown")
async def on_shutdown():
    await jwks_cache.stop()

def _json_error(code: str, corr: str):
    return {"error": {"code": code, "message": code}, "correlation_id": corr}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/ops/retention/purge")
async def ops_retention_purge(request: Request):
    # In production, protect this endpoint (mTLS/admin scope). Here: require header key for demo.
    key = request.headers.get("x-ops-key")
    if not key or key != "change-me":
        return Response(content=orjson.dumps(_json_error("AUTH_FORBIDDEN", "ops")), status_code=403, media_type="application/json")
    now_ms = int(time.time()*1000)
    await retention_purge(now_ms)
    return {"status": "ok"}

@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    start = time.time()

    # Correlation ID early
    corr = request.headers.get("x-correlation-id") or Identity.new_correlation_id()
    policy_version = "policy-0.3"

    # AuthN (async)
    try:
        identity = await verify_bearer_token_async(request.headers.get("authorization"))
    except AuthError as e:
        return Response(content=orjson.dumps(_json_error(e.code, corr)), status_code=e.status,
                        media_type="application/json", headers={"X-Correlation-Id": corr})

    # AuthZ
    try:
        authorize_path(identity, request.url.path)
    except AuthError as e:
        return Response(content=orjson.dumps(_json_error(e.code, corr)), status_code=e.status,
                        media_type="application/json", headers={"X-Correlation-Id": corr, "X-Policy-Version": policy_version})

    body = await request.body()

    # DLP pre-check
    dlp_action, dlp_rule_id = dlp_engine.inspect_bytes(body)
    if dlp_action == "block":
        latency_ms = int((time.time()-start)*1000)
        await emit_audit(identity, corr, request.url.path, 400, latency_ms, route_target="-",
                         policy_version=policy_version, dlp_action="block", dlp_rule_id=dlp_rule_id,
                         extra={"dlp_stage": "pre"})
        return Response(content=orjson.dumps(_json_error("DLP_BLOCKED", corr)), status_code=400,
                        media_type="application/json", headers={"X-Correlation-Id": corr, "X-Policy-Version": policy_version})

    route = resolve_route(request.url.path)
    if not route:
        return Response(content=orjson.dumps(_json_error("NOT_FOUND", corr)), status_code=404,
                        media_type="application/json", headers={"X-Correlation-Id": corr, "X-Policy-Version": policy_version})

    service_name = route.get("name", "unknown")
    upstream = route["upstream"]
    url = upstream + request.url.path

    # Upstream auth separation:
    # - Do NOT forward workspace Authorization token to upstream
    headers = {
        "X-Correlation-Id": corr,
        "X-User-Id": identity.user_id,
        "X-Tenant-Id": identity.tenant_id,
        "X-Project-Id": identity.project_id,
        "X-Workspace-Id": identity.workspace_id,
        "X-Policy-Version": policy_version,
        "Content-Type": request.headers.get("content-type", "application/json"),
        "Accept": request.headers.get("accept", "application/json"),
        **upstream_headers(),
    }

    verify, cert = httpx_verify_and_cert()
    timeout = httpx.Timeout(settings.upstream_timeout_seconds, read=settings.stream_read_timeout_seconds)

    # Streaming SSE proxy + incremental DLP (optional)
    if "text/event-stream" in request.headers.get("accept", ""):
        async def event_stream():
            buffered = b""
            async with httpx.AsyncClient(timeout=timeout, verify=verify, cert=cert) as client:
                try:
                    async with client.stream(request.method, url, headers=headers, content=body) as r:
                        if r.status_code >= 400:
                            yield b"event: error\ndata: {\"code\":\"UPSTREAM_ERROR\"}\n\n"
                            return
                        async for chunk in r.aiter_bytes():
                            if settings.dlp_stream_mode == "pre_and_incremental":
                                buffered += chunk
                                if len(buffered) > settings.dlp_stream_max_buffer_bytes:
                                    # avoid unbounded memory; if overflow, stop streaming
                                    yield b"event: error\ndata: {\"code\":\"DLP_STREAM_BUFFER_OVERFLOW\"}\n\n"
                                    return
                                action, rid = dlp_engine.inspect_bytes(buffered)
                                if action == "block":
                                    # block immediately
                                    yield b"event: error\ndata: {\"code\":\"DLP_BLOCKED\"}\n\n"
                                    return
                            yield chunk
                except (httpx.TimeoutException, httpx.HTTPError):
                    yield b"event: error\ndata: {\"code\":\"UPSTREAM_UNAVAILABLE\"}\n\n"

        resp = StreamingResponse(event_stream(), media_type="text/event-stream")
        status_code = 200
        latency_ms = int((time.time()-start)*1000)
        await emit_audit(identity, corr, request.url.path, status_code, latency_ms, route_target=service_name,
                         policy_version=policy_version, dlp_action=dlp_action, dlp_rule_id=dlp_rule_id,
                         extra={"mode": "sse", "dlp_stage": settings.dlp_stream_mode})
        observe_request(service_name, status_code, latency_ms, identity.project_id, dlp_action, dlp_rule_id)
        resp.headers["X-Correlation-Id"] = corr
        resp.headers["X-Policy-Version"] = policy_version
        return resp

    # Non-stream proxy
    async with httpx.AsyncClient(timeout=timeout, verify=verify, cert=cert) as client:
        try:
            r = await client.request(request.method, url, headers=headers, content=body)
            status_code = r.status_code
            content_type = r.headers.get("content-type","application/json")
            content = r.content
        except httpx.TimeoutException:
            status_code = 504
            content_type = "application/json"
            content = orjson.dumps(_json_error("UPSTREAM_TIMEOUT", corr))
        except httpx.HTTPError:
            status_code = 503
            content_type = "application/json"
            content = orjson.dumps(_json_error("UPSTREAM_UNAVAILABLE", corr))

    # Post-processing: agent diff hash capture
    diff_hash = None
    extra = {}
    model_name = request.headers.get("x-model", "unknown")
    input_tokens = None
    output_tokens = None

    if service_name == "agent" and status_code < 400 and content_type.startswith("application/json"):
        try:
            payload = json.loads(content.decode("utf-8"))
            diff = extract_unified_diff_from_json(payload) if isinstance(payload, dict) else None
            if diff:
                diff_hash = sha256_text(diff)
            usage = payload.get("usage") if isinstance(payload, dict) else None
            if isinstance(usage, dict):
                input_tokens = usage.get("prompt_tokens")
                output_tokens = usage.get("completion_tokens")
        except Exception:
            extra["agent_parse_error"] = True

    latency_ms = int((time.time() - start) * 1000)
    await emit_audit(identity, corr, request.url.path, status_code, latency_ms, route_target=service_name,
                     policy_version=policy_version, dlp_action=dlp_action, dlp_rule_id=dlp_rule_id,
                     input_tokens=input_tokens, output_tokens=output_tokens, diff_hash=diff_hash, extra=extra)

    observe_request(service_name, status_code, latency_ms, identity.project_id, dlp_action, dlp_rule_id)
    if input_tokens:
        observe_tokens(identity.project_id, model_name, service_name, int(input_tokens))
    if output_tokens:
        observe_tokens(identity.project_id, model_name, service_name, int(output_tokens))

    resp = Response(content=content, status_code=status_code, media_type=content_type)
    resp.headers["X-Correlation-Id"] = corr
    resp.headers["X-Policy-Version"] = policy_version
    return resp
