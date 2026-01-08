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

E2E_REPORT="${E2E_REPORT:-1}"                 # 1이면 reports/e2e 에 JSON+MD 리포트 생성
E2E_REPORT_DIR="${E2E_REPORT_DIR:-reports/e2e}"
E2E_REPORT_BASENAME="${E2E_REPORT_BASENAME:-}"
E2E_TS="$(date -u +%Y%m%dT%H%M%SZ)"

CHECKS_JSON='{}'
check_set() {
  local key="$1"
  local ok="$2"
  local status_code="$3"
  local detail="${4:-}"
  CHECKS_JSON="$(python - <<PY
import json
checks=json.loads('''$CHECKS_JSON''')
checks["$key"]={"ok": ($ok=="1"), "status_code": int("$status_code"), "detail": "$detail"}
print(json.dumps(checks, ensure_ascii=False))
PY
)"
}

http_status() {
  # prints status code only; does not print body (avoid leaking)
  curl -sS -o /dev/null -w "%{http_code}" "$@"
}

echo "BASE_URL=${BASE_URL}"
echo "API_URL=${API_URL}"
echo "GATEWAY_URL=${GATEWAY_URL}"
echo "WEB_URL=${WEB_URL}"

echo "== docker compose up =="
docker compose up -d --build

echo "== health checks =="
code="$(http_status -f "${API_URL}/health" || true)"; test "$code" = "200" && echo "OK api /health" || true; check_set "api_health" "$([ "$code" = "200" ] && echo 1 || echo 0)" "$code"
code="$(http_status -f "${GATEWAY_URL}/healthz" || true)"; test "$code" = "200" && echo "OK gateway /healthz" || true; check_set "gateway_healthz" "$([ "$code" = "200" ] && echo 1 || echo 0)" "$code"
code="$(http_status -f "${WEB_URL}/api/health" || true)"; test "$code" = "200" && echo "OK web /api/health" || true; check_set "web_health" "$([ "$code" = "200" ] && echo 1 || echo 0)" "$code"

echo "== signup (may fail if already exists) =="
code="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "${API_URL}/api/auth/signup" \
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
)" || true)"
check_set "auth_signup" "$([ "$code" = "200" ] || [ "$code" = "201" ] && echo 1 || echo 0)" "${code:-0}" "signup may return 409 if already exists"

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
check_set "auth_login" "$([ "${#ACCESS_TOKEN}" -gt 20 ] && echo 1 || echo 0)" 200 "token length only; token not stored"

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
check_set "create_project" "$([ "${#PROJECT_ID}" -gt 3 ] && echo 1 || echo 0)" 201 ""

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
check_set "create_workspace" "$([ "${#WORKSPACE_ID}" -gt 3 ] && echo 1 || echo 0)" 201 ""

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
check_set "get_ide_url" "$([ "${#IDE_URL}" -gt 6 ] && echo 1 || echo 0)" 200 ""

echo "== gateway tabby health (best-effort) =="
code="$(http_status "${GATEWAY_URL}/v1/health" || true)"
if [ "$code" = "200" ]; then echo "OK gateway /v1/health"; fi
check_set "gateway_tabby_health" "$([ "$code" = "200" ] && echo 1 || echo 0)" "${code:-0}" "best-effort"

echo "== rag index (best-effort) =="
code="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "${GATEWAY_URL}/v1/rag/index" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"${WORKSPACE_ID}\",\"force_reindex\":true}" \
  || true)"
check_set "rag_index" "$([ "$code" = "202" ] || [ "$code" = "200" ] && echo 1 || echo 0)" "${code:-0}" "best-effort"

echo "== rag search (best-effort) =="
code="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "${GATEWAY_URL}/v1/rag/search" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"workspace\",\"workspace_id\":\"${WORKSPACE_ID}\",\"limit\":3}" \
  || true)"
check_set "rag_search" "$([ "$code" = "200" ] && echo 1 || echo 0)" "${code:-0}" "best-effort"

echo "== rag context (best-effort) =="
code="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "${GATEWAY_URL}/v1/rag/context" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"워크스페이스 생성 흐름 설명\",\"workspace_id\":\"${WORKSPACE_ID}\",\"max_results\":5,\"include_file_tree\":true,\"task_type\":\"explain\",\"max_context_tokens\":800,\"max_context_chars\":4000}" \
  || true)"
check_set "rag_context" "$([ "$code" = "200" ] && echo 1 || echo 0)" "${code:-0}" "best-effort"

echo "DONE"
echo "- Open IDE in browser: ${IDE_URL}"
echo "- Note: IDE 내 자동완성/채팅은 UI에서 확인하세요."

if [ "${E2E_REPORT}" = "1" ]; then
  echo "== write report (no secrets) =="
  export E2E_REPORT_DIR
  export E2E_TS
  export E2E_REPORT_BASENAME
  export E2E_CHECKS_JSON="${CHECKS_JSON}"
  export PROJECT_ID
  export WORKSPACE_ID
  export IDE_URL
  export BASE_URL API_URL GATEWAY_URL WEB_URL TEST_EMAIL TEST_ORG
  python scripts/e2e/e2e_report.py
fi
