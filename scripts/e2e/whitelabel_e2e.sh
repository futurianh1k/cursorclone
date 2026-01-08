#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/projects/cursor-onprem-poc

BASE_URL="${BASE_URL:-http://10.10.10.151}"
WEB_URL="${WEB_URL:-${BASE_URL}:3000}"
API_URL="${API_URL:-${BASE_URL}:8000}"
GATEWAY_URL="${GATEWAY_URL:-${BASE_URL}:8081}"

GATEWAY_INTERNAL_TOKEN="${GATEWAY_INTERNAL_TOKEN:-change-me-in-production}"

TEST_EMAIL="${TEST_EMAIL:-e2e.user@example.com}"
TEST_NAME="${TEST_NAME:-E2E User}"
TEST_PASSWORD="${TEST_PASSWORD:-ChangeMe1234!}"
TEST_ORG="${TEST_ORG:-org_default}"

echo "BASE_URL=${BASE_URL}"
echo "API_URL=${API_URL}"
echo "GATEWAY_URL=${GATEWAY_URL}"
echo "WEB_URL=${WEB_URL}"

echo "== docker compose up =="
docker compose up -d --build

echo "== health checks =="
curl -fsS "${API_URL}/health" >/dev/null && echo "OK api /health"
curl -fsS "${GATEWAY_URL}/healthz" >/dev/null && echo "OK gateway /healthz"
curl -fsS "${WEB_URL}/api/health" >/dev/null && echo "OK web /api/health"

echo "== signup (may fail if already exists) =="
curl -sS -X POST "${API_URL}/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d "$(python - <<PY
import os, json
print(json.dumps({
  "email": os.environ.get("TEST_EMAIL","$TEST_EMAIL"),
  "name": os.environ.get("TEST_NAME","$TEST_NAME"),
  "password": os.environ.get("TEST_PASSWORD","$TEST_PASSWORD"),
  "org_name": os.environ.get("TEST_ORG","$TEST_ORG"),
}))
PY
)" >/dev/null || true

echo "== login =="
ACCESS_TOKEN="$(
  curl -sS -X POST "${API_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "$(python - <<PY
import os, json
print(json.dumps({"email":"$TEST_EMAIL","password":"$TEST_PASSWORD"}))
PY
)" | python - <<'PY'
import sys, json
data=json.load(sys.stdin)
print(data["accessToken"])
PY
)"
echo "ACCESS_TOKEN(len)=${#ACCESS_TOKEN}"

echo "== create project =="
PROJECT_ID="$(
  curl -sS -X POST "${API_URL}/api/projects" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"name":"E2E Project","description":"white label e2e"}' \
  | python - <<'PY'
import sys, json
print(json.load(sys.stdin)["projectId"])
PY
)"
echo "PROJECT_ID=${PROJECT_ID}"

echo "== create workspace (auto provisions IDE) =="
WS_JSON="$(
  curl -sS -X POST "${API_URL}/api/workspaces" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(python - <<PY
import json
print(json.dumps({"name":"e2e_ws","language":"python","projectId":"$PROJECT_ID"}))
PY
)"
)"
WORKSPACE_ID="$(echo "${WS_JSON}" | python - <<'PY'
import sys, json
print(json.load(sys.stdin)["workspaceId"])
PY
)"
echo "WORKSPACE_ID=${WORKSPACE_ID}"

echo "== get IDE URL =="
IDE_URL="$(
  curl -sS "${API_URL}/api/ide/workspace/${WORKSPACE_ID}/url" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  | python - <<'PY'
import sys, json
print(json.load(sys.stdin)["url"])
PY
)"
echo "IDE_URL=${IDE_URL}"

echo "== gateway tabby health (best-effort) =="
curl -fsS "${GATEWAY_URL}/v1/health" >/dev/null && echo "OK gateway /v1/health" || echo "WARN gateway /v1/health failed"

echo "== rag index (best-effort) =="
curl -sS -X POST "${GATEWAY_URL}/v1/rag/index" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"${WORKSPACE_ID}\",\"force_reindex\":true}" \
  >/dev/null || true

echo "== rag search (best-effort) =="
curl -sS -X POST "${GATEWAY_URL}/v1/rag/search" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"workspace\",\"workspace_id\":\"${WORKSPACE_ID}\",\"limit\":3}" \
  >/dev/null || true

echo "== rag context (best-effort) =="
curl -sS -X POST "${GATEWAY_URL}/v1/rag/context" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"워크스페이스 생성 흐름 설명\",\"workspace_id\":\"${WORKSPACE_ID}\",\"max_results\":5,\"include_file_tree\":true,\"task_type\":\"explain\",\"max_context_tokens\":800,\"max_context_chars\":4000}" \
  >/dev/null || true

echo "DONE"
echo "- Open IDE in browser: ${IDE_URL}"
echo "- Note: IDE 내 자동완성/채팅은 UI에서 확인하세요."

