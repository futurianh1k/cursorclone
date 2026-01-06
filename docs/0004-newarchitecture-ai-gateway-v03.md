# 0004 — New Architecture / AI Gateway(v0.3) 구현 기록

## 대화 요약(요구사항)
- `docs/newarchitecture/PRD.md` 및 동 폴더 문서 기준으로 구현
- 금융권 VDE 제약 준수
- FastAPI 기반 AI Gateway 구현
  - 인증/인가 미들웨어
  - 라우팅 정책
  - 감사 로그 스키마 반영
- 문서에 없는 기능 추가 금지

## 구현 결과(요약)
- `apps/gateway/`에 v0.3 AI Gateway 코드 추가
  - JWKS 캐시/리프레시(+ fail-open/close 옵션)
  - Upstream auth 분리(Workspace 토큰 업스트림 전달 금지)
  - 스트리밍 DLP 모드(기본 pre_only, 옵션 pre_and_incremental)
  - 감사 로그 DB 스키마 및 월별 파티셔닝 + retention purge 설계
  - OpenAPI pin 스크립트(생성/검증)

## 변경 파일(핵심)
- `apps/gateway/app/main.py`
- `apps/gateway/app/auth_async.py`, `apps/gateway/app/authorize.py`
- `apps/gateway/app/jwks_cache.py`
- `apps/gateway/app/audit.py`, `apps/gateway/app/db.py`, `apps/gateway/app/ilm.py`
- `apps/gateway/policies/dlp_rules.yaml`
- `apps/gateway/scripts/generate_openapi.py`, `apps/gateway/scripts/verify_openapi.py`
- `apps/gateway/tests/test_gateway_nonnegotiables.py`

## 테스트
- `pytest apps/gateway/tests/test_gateway_nonnegotiables.py`

