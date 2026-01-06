from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

REQ = Counter("ai_gateway_requests_total", "Total requests", ["service", "status", "project_id"])
LAT = Histogram("ai_gateway_latency_seconds", "Latency", ["service"])
DLP = Counter("ai_gateway_dlp_actions_total", "DLP actions", ["action", "rule_id", "project_id"])
TOK = Counter("ai_gateway_tokens_total", "Token usage", ["project_id", "model", "service"])

def init_metrics(app: FastAPI):
    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

def observe_request(service: str, status_code: int, latency_ms: int, project_id: str, dlp_action: str, rule_id: str | None):
    REQ.labels(service=service, status=str(status_code), project_id=project_id).inc()
    LAT.labels(service=service).observe(latency_ms / 1000.0)
    DLP.labels(action=dlp_action, rule_id=str(rule_id or "-"), project_id=project_id).inc()

def observe_tokens(project_id: str, model: str, service: str, tokens: int):
    if tokens is None:
        return
    TOK.labels(project_id=project_id, model=model, service=service).inc(tokens)
