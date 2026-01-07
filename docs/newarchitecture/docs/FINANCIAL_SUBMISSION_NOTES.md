# 금융권 제출/운영 배포 강화 포인트 (v0.3)

## 1) JWKS 캐시/리프레시
- 운영 환경에서는 JWKS URL 장애/지연이 발생할 수 있으므로,
  - 메모리 캐시 + TTL
  - 백그라운드 refresh(주기)
  - refresh 실패 시 정책(FAIL_OPEN/FAIL_CLOSE) 명시가 필요

v0.3는 `JWT_JWKS_CACHE_TTL_SECONDS`, `JWT_JWKS_REFRESH_SECONDS`, `JWT_JWKS_FAIL_OPEN`을 제공한다.

## 2) Upstream Auth 분리
- Workspace에서 전달된 사용자 토큰을 업스트림(모델/탭비 등)에 전달하면
  경계가 흐려지고 토큰 노출 위험이 증가한다.
- Gateway가 내부 서비스 인증을 수행해야 한다:
  - 내부 서비스 토큰(`UPSTREAM_AUTH_MODE=static_bearer`)
  - mTLS(서비스 메시/인증서) 전제(`UPSTREAM_AUTH_MODE=mtls`)

## 3) Streaming DLP
- 기본: Request pre-DLP(프롬프트/컨텍스트)
- 옵션: Response incremental DLP(스트림 chunk 단위 검사) — 비용/지연 고려하여 선택 적용

## 4) 감사 로그/DB
- 월별 Range 파티셔닝(시간 기반)
- ILM/Retention(예: 180일/365일) 정책 및 purge job
- 인덱스는 파티션별 생성, correlation_id/project_id+ts_ms

## 5) OpenAPI 고정
- 서버 런타임 OpenAPI는 변경 위험이 있으므로
  빌드/배포 파이프라인에서 openapi.json을 생성 후 git/아티팩트로 고정하고,
  배포 시 검증(step)으로 drift를 차단한다.
