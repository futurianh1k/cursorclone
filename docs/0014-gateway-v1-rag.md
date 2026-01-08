# 0014 - Gateway v1 RAG (/v1/rag) + 내부 Upstream Auth

## 목표
- **RAG 요청도 100% AI Gateway를 경유**하도록 `/v1/rag` 라우팅을 완성한다.
- Gateway는 **workspace 사용자 토큰(Authorization)** 을 upstream(API)에 전달하지 않는다.
- 대신 Gateway→API 내부 호출임을 식별하기 위한 **내부 토큰 헤더(X-Internal-Token)** 를 사용한다.

## 구현 요약
### 1) Gateway
- 라우팅 정책: `/v1/rag/*` → `UPSTREAM_RAG` (이미 존재)
- 내부 upstream auth:
  - `UPSTREAM_INTERNAL_TOKEN`이 설정되면 `rag/agent` upstream 호출에만 `x-internal-token` 헤더를 추가
  - workspace 사용자 토큰은 전달하지 않음(기존 원칙 유지)
- DLP:
  - RAG 응답을 **post 단계에서도 검사**(차단 룰 매칭 시 400 반환 + audit 기록)

### 2) API
- 신규 라우터: `apps/api/src/routers/rag_v1.py`
  - prefix: `/v1/rag`
  - 인증: `X-Internal-Token` + `X-User-Id/X-Tenant-Id/X-Project-Id/X-Workspace-Id` 헤더 기반
  - 스코프 강제: request의 `workspace_id`가 header `X-Workspace-Id`와 불일치하면 403
  - tenant/project도 DB의 workspace 메타와 비교하여 불일치 시 403

### 3) docker-compose
- `GATEWAY_INTERNAL_TOKEN`을 `api`와 `gateway`에 공유
  - API: `GATEWAY_INTERNAL_TOKEN`
  - Gateway: `UPSTREAM_INTERNAL_TOKEN` (같은 값), `UPSTREAM_INTERNAL_TOKEN_HEADER`

## 테스트
- Gateway: `apps/gateway/tests/test_gateway_nonnegotiables.py`에 내부 헤더 테스트 추가
- API: `apps/api/tests/test_rag_v1_internal_auth.py`로 내부 토큰/스코프 mismatch 차단 테스트 추가

