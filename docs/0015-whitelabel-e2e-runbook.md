# 0015 - 화이트라벨 SaaS E2E 검증 Runbook (복붙용)

목표: **워크스페이스 생성 → code-server 접속 → Tabby 자동완성/채팅 → RAG 검색/컨텍스트**까지 “운영자가 복붙”으로 검증.

> 주의(보안/운영):
> - `GATEWAY_INTERNAL_TOKEN`, `JWT_SECRET_KEY`, `MASTER_ENCRYPTION_KEY`는 **반드시 운영 값으로 교체**하세요.
> - 로그/스크립트에 사용자 비밀번호/토큰을 장기 저장하지 마세요(테스트 후 삭제 권장).

---

## 0) 환경 변수(운영 기본값)

아래 값은 예시입니다. 고객사 환경에 맞게 수정하세요.

```bash
export BASE_URL="http://10.10.10.151"
export WEB_URL="${BASE_URL}:3000"
export API_URL="${BASE_URL}:8000"
export GATEWAY_URL="${BASE_URL}:8081"

# 내부 토큰 (Gateway -> API)
export GATEWAY_INTERNAL_TOKEN="change-me-in-production"
export UPSTREAM_INTERNAL_TOKEN_HEADER="x-internal-token"

# 테스트 계정
export TEST_EMAIL="e2e.user@example.com"
export TEST_NAME="E2E User"
export TEST_PASSWORD="ChangeMe1234!"
export TEST_ORG="org_default"

# 오프라인 임베딩(금융권 VDE 권장) — 모델을 ./models/embedding 에 사전 배치해야 함
# export EMBEDDING_LOCAL_FILES_ONLY="true"
# export EMBEDDING_STRICT="true"
# export EMBEDDING_MODEL_PATH="/models/embedding"
# export EMBEDDING_CACHE_DIR="/root/.cache/huggingface"
```

---

## 1) 서비스 기동/헬스

```bash
cd /home/ubuntu/projects/cursor-onprem-poc

# (권장) .env에 운영 시크릿을 넣고, compose env로 주입
docker compose up -d --build

curl -fsS "${API_URL}/health" | python -m json.tool
curl -fsS "${GATEWAY_URL}/healthz" | python -m json.tool
curl -fsS "${WEB_URL}/api/health" | python -m json.tool
```

---

## 2) 가입/로그인 (API)

> API 스키마:
> - signup: `email`, `name`, `password`, `org_name`
> - login: `email`, `password`

```bash
# signup (이미 존재하면 409 등으로 실패할 수 있음)
curl -sS -X POST "${API_URL}/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d "$(python - <<'PY'
import os, json
print(json.dumps({
  "email": os.environ["TEST_EMAIL"],
  "name": os.environ["TEST_NAME"],
  "password": os.environ["TEST_PASSWORD"],
  "org_name": os.environ.get("TEST_ORG","org_default"),
}))
PY
)" | python -m json.tool

# login -> accessToken 추출
ACCESS_TOKEN="$(
  curl -sS -X POST "${API_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "$(python - <<'PY'
import os, json
print(json.dumps({"email": os.environ["TEST_EMAIL"], "password": os.environ["TEST_PASSWORD"]}))
PY
)" | python - <<'PY'
import sys, json
data=json.load(sys.stdin)
print(data["accessToken"])
PY
)"

echo "ACCESS_TOKEN(len)=${#ACCESS_TOKEN}"

# me
curl -fsS "${API_URL}/api/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | python -m json.tool
```

---

## 3) 프로젝트 생성 → 워크스페이스 생성

### 3-1) 프로젝트 생성

```bash
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
```

### 3-2) 워크스페이스 생성(프로젝트에 추가)

> 워크스페이스 생성은 백그라운드로 IDE(code-server) 컨테이너 프로비저닝이 시작됩니다.

```bash
WS_JSON="$(
  curl -sS -X POST "${API_URL}/api/workspaces" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(python - <<'PY'
import json
print(json.dumps({
  "name": "e2e_ws",
  "language": "python",
  "projectId": "__PROJECT_ID__",
}).replace("__PROJECT_ID__", __import__("os").environ["PROJECT_ID"]))
PY
)"
)"
echo "${WS_JSON}" | python -m json.tool

WORKSPACE_ID="$(echo "${WS_JSON}" | python - <<'PY'
import sys, json
print(json.load(sys.stdin)["workspaceId"])
PY
)"
echo "WORKSPACE_ID=${WORKSPACE_ID}"
```

---

## 4) IDE(code-server) URL 확인/접속

```bash
# 워크스페이스 IDE URL 조회 (필요 시 컨테이너 생성/재사용)
IDE_URL="$(
  curl -sS "${API_URL}/api/ide/workspace/${WORKSPACE_ID}/url" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  | python - <<'PY'
import sys, json
print(json.load(sys.stdin)["url"])
PY
)"
echo "IDE_URL=${IDE_URL}"

# 브라우저로 접속 (운영자 확인):
echo "Open: ${IDE_URL}"
```

**검증 포인트**
- 접속 시 **암호를 묻지 않아야** 합니다(code-server `--auth none`).
- IDE에서 파일 생성/수정 후, 컨테이너 stop → start 해도 상태가 유지되어야 합니다(워크스페이스 볼륨).

---

## 5) Tabby 자동완성 / Chat (Gateway 경유)

> IDE 내부 확장(Continue/Tabby)은 “설정 주입”으로 Gateway를 보게 구성되어 있어야 합니다.  
> 여기서는 운영자가 **Gateway 엔드포인트가 살아있는지** 먼저 확인합니다.

```bash
# Tabby health (Gateway가 Tabby upstream으로 라우팅)
curl -fsS "${GATEWAY_URL}/v1/health" | python -m json.tool || true
```

> 실제 자동완성은 IDE UI에서 확인하세요(입력 시 추천이 뜨는지).

---

## 6) RAG (Gateway 경유 /v1/rag)

### 6-1) 인덱싱 시작

> Gateway는 workspace 사용자 토큰을 upstream(API)에 전달하지 않습니다.  
> 대신 workspace-scoped JWT(Authorization)로 Gateway에 요청하고, Gateway가 내부 토큰으로 API를 호출합니다.

```bash
# (선택) 인덱싱 시작: 워크스페이스 코드가 충분히 있어야 의미가 있음
curl -sS -X POST "${GATEWAY_URL}/v1/rag/index" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"${WORKSPACE_ID}\",\"force_reindex\":true}" \
  | python -m json.tool
```

### 6-2) 검색

```bash
curl -sS -X POST "${GATEWAY_URL}/v1/rag/search" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"workspace\",\"workspace_id\":\"${WORKSPACE_ID}\",\"limit\":5}" \
  | python -m json.tool
```

### 6-3) 컨텍스트 빌드(팩킹/예산 포함)

```bash
curl -sS -X POST "${GATEWAY_URL}/v1/rag/context" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$(python - <<'PY'
import os, json
print(json.dumps({
  "query": "이 프로젝트에서 워크스페이스 생성 흐름을 설명해줘",
  "workspace_id": os.environ["WORKSPACE_ID"],
  "max_results": 8,
  "include_file_tree": True,
  "task_type": "explain",
  "max_context_tokens": 1200,
  "max_context_chars": 6000,
}))
PY
)" | python -m json.tool
```

---

## 7) DLP 차단 시나리오(필수)

### 7-1) pre DLP: 요청 본문 차단 예시(Private Key)

```bash
curl -sS -X POST "${GATEWAY_URL}/v1/rag/search" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query":"-----BEGIN PRIVATE KEY-----","workspace_id":"'"${WORKSPACE_ID}"'","limit":1}' \
  | python -m json.tool
```

### 7-2) post DLP: RAG 응답 차단

> 실제로 post DLP가 트리거되려면 “검색/컨텍스트 결과”에 차단 패턴이 포함되어야 합니다.  
> (예: 레포에 `AKIA...` 형태 문자열이 들어있는 파일이 존재)

---

## 8) 한 번에 실행(스크립트)

아래 스크립트는 위 내용을 자동으로 실행합니다:

```bash
cd /home/ubuntu/projects/cursor-onprem-poc
chmod +x scripts/e2e/whitelabel_e2e.sh
scripts/e2e/whitelabel_e2e.sh
```

### 8-1) 실행 결과 리포트(JSON/Markdown) 생성(권장)

스크립트는 기본적으로 **민감정보(비밀번호/토큰) 없이** 실행 결과를 `reports/e2e/`에 저장합니다.

- **출력 파일**
  - `reports/e2e/whitelabel_e2e_<UTC timestamp>.json`
  - `reports/e2e/whitelabel_e2e_<UTC timestamp>.md`
- **추가 포함(수동 체크리스트)**
  - 리포트(`*.md`)에 IDE UI에서 직접 확인해야 하는 항목(자동완성/채팅/상태보존 등) 체크박스가 포함됩니다.
- **포함 정보**
  - base/api/gateway/web URL
  - 생성된 `projectId/workspaceId/ideUrl`
  - 헬스/RAG 호출의 성공 여부 및 상태코드
- **미포함(저장 금지)**
  - 사용자 비밀번호
  - access token / refresh token

사용 예시:

```bash
export E2E_REPORT=1
export E2E_REPORT_DIR="reports/e2e"
export E2E_REPORT_BASENAME="customerA_smoke_001"
scripts/e2e/whitelabel_e2e.sh
ls -al reports/e2e | tail
```

리포트 생성을 끄려면:

```bash
export E2E_REPORT=0
scripts/e2e/whitelabel_e2e.sh
```
