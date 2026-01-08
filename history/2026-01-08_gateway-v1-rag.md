# 2026-01-08 — Gateway v1 RAG (/v1/rag) + 내부 Upstream Auth

## 요청자 요구사항 요약
- (D) 권한/보안/감사
  - RAG도 Gateway 경유(단일 제어 지점)
  - Upstream auth 분리(사용자 토큰 전달 금지)
  - 필요 시 DLP/감사 강화

## Assistant 응답(무엇을 할지)
- Gateway에 `/v1/rag` 경로를 실제로 동작하게 만들고(UPSTREAM_RAG→API),
  Gateway→API 내부 인증 토큰을 도입해 사용자 토큰을 upstream에 전달하지 않게 한다.
- RAG 응답에도 post DLP 검사를 추가한다.
- 테스트로 내부 토큰/스코프 mismatch 차단을 고정한다.

## 실제 수행 변경(요약)
- Gateway
  - `UPSTREAM_INTERNAL_TOKEN`을 `rag/agent` upstream 호출에만 헤더로 전달(`x-internal-token`)
  - RAG 응답 post DLP 검사 추가(차단 시 400)
  - 테스트 추가
- API
  - `/v1/rag` 라우터 추가(내부 토큰 + identity 헤더 기반)
  - 스코프 강제(헤더 workspace/tenant/project와 DB 메타 mismatch 차단)
  - 테스트 추가
- docker-compose
  - `GATEWAY_INTERNAL_TOKEN` 공유 설정 추가

## 변경 파일 목록
- `apps/gateway/app/config.py`
- `apps/gateway/app/upstream_auth.py`
- `apps/gateway/app/main.py`
- `apps/gateway/tests/test_gateway_nonnegotiables.py`
- `apps/api/src/services/internal_gateway_auth.py`
- `apps/api/src/routers/rag_v1.py`
- `apps/api/src/main.py`
- `apps/api/tests/test_rag_v1_internal_auth.py`
- `docker-compose.yml`
- `docs/0014-gateway-v1-rag.md`

## 테스트 및 검증 방법
- `cd apps/gateway && pytest -q`
- `cd apps/api && pytest -q`

## 향후 작업 제안/주의사항
- 운영 환경에서는 `GATEWAY_INTERNAL_TOKEN`을 반드시 강한 값으로 설정하고 외부 노출 금지
- v2: `/api/rag/*` 직접 호출을 점진적으로 막거나, 웹/IDE가 `/v1/rag/*`로만 호출하도록 완전 전환 필요

