# 2026-01-07 — New Architecture: AI Gateway(v0.3) FastAPI 구현

## 요청자 요구사항 요약
- 브랜치 `newarchitecture`에서 “중대한 변경”으로 진행
- `docs/newarchitecture/PRD.md` 및 동 폴더 md 문서 요구사항 준수
- 금융권 VDE 제약 위반 금지
- **AI Gateway를 FastAPI로 구현**
  - 인증/인가 미들웨어 포함
  - 라우팅 정책 구현
  - 감사 로그 스키마 반영
  - 문서에 정의되지 않은 기능은 추가하지 않기

## Assistant(제가) 하기로 한 것
- `docs/newarchitecture/gateway`의 v0.3 참조 구현을 기준으로, 실제 서비스 코드(`apps/gateway`)로 승격
- JWKS 캐시/리프레시, Upstream auth 분리, Streaming DLP 옵션, 감사 로그(월별 파티션/retention), OpenAPI pin 스크립트 포함
- 최소 단위 테스트 추가(Non‑negotiables, 라우팅 정책)

## 실제로 수행한 변경 내용
- **신규 서비스 코드 추가**
  - `apps/gateway/`:
    - `app/main.py`: FastAPI gateway + 인증/인가 미들웨어 + 라우팅 + DLP + 감사 로그 + SSE proxy
    - `app/auth_async.py`, `app/authorize.py`: JWT/JWKS 인증 및 Role 인가
    - `app/jwks_cache.py`: JWKS 캐시/백그라운드 refresh + fail-open/close
    - `app/audit.py`, `app/db.py`, `app/ilm.py`: 감사 로그 스키마/월별 파티셔닝/retention purge
    - `policies/dlp_rules.yaml`: DLP 정책 외부화
    - `scripts/generate_openapi.py`, `scripts/verify_openapi.py`: OpenAPI pin/검증
    - `tests/test_gateway_nonnegotiables.py`: 요구사항 기반 테스트
- **오프라인/제약 환경 대응**
  - `apps/gateway/app/config.py`: `pydantic-settings` 미설치 환경에서도 동작하도록 fallback(환경변수 기반) 추가
- **클라이언트(IDE/웹) 설정을 Gateway로 전환**
  - code-server(IDE) 내 확장(Continue/Tabby)이 직접 upstream(vLLM/Tabby)을 호출하지 않고 Gateway(`cursor-poc-gateway:8081`)만 호출하도록 설정 변경
  - `docker-compose.yml`에 `gateway` 서비스 추가(헬스체크 `/healthz`)

## 테스트 및 검증 방법
- 단위 테스트:
  - `pytest apps/gateway/tests/test_gateway_nonnegotiables.py`
- 실행(개발):
  - `apps/gateway/README.md`의 Run(dev) 절차 참고
- 로컬 라우팅 확인(예시):
  - `POST /v1/chat/completions` (Bearer dev) → 200
  - `POST /v1/completions` (Bearer dev, Tabby segments payload) → 응답 반환

## 향후 작업 제안 / 주의사항
- PRD의 “Workspace -> AI Gateway 단일 경유”를 시스템 전체에 적용하려면:
  - Web IDE/확장(Continue/Tabby) 엔드포인트를 gateway로 통합하는 작업이 필요
  - 현재 gateway 라우팅 경로(`/v1/autocomplete`, `/v1/chat`, `/v1/agent`, `/v1/rag`)를 클라이언트 설정과 정합시키는 설계 확정이 필요
- `openapi/openapi.json`은 현재 placeholder이며, gateway 런타임 환경(패키지 버전)에서 `scripts/generate_openapi.py`로 생성 후 고정/검증 단계(CI) 도입 권장

