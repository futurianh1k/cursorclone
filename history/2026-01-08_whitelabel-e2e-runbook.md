# 2026-01-08 — 화이트라벨 SaaS E2E 검증 Runbook/스크립트 추가

## 요청자 요구사항 요약
- 고객사 연동 전, 화이트라벨 SaaS 형태로
  - 워크스페이스 생성
  - code-server 실행
  - Tabby 자동완성/채팅
  - RAG 검색/컨텍스트
  를 E2E로 검증할 수 있는 “복붙 가능한 명령 모음” 문서를 만들 것.

## Assistant 응답(무엇을 할지)
- 실제 API 스키마(회원가입/로그인/프로젝트/워크스페이스/IDE/RAG)를 기준으로
  운영자가 그대로 복붙해 실행 가능한 Runbook을 docs에 작성하고,
  동일 절차를 자동화한 bash 스크립트도 추가한다.

## 실제 수행 변경(요약)
- Runbook 문서 추가: `docs/0015-whitelabel-e2e-runbook.md`
- 자동화 스크립트 추가: `scripts/e2e/whitelabel_e2e.sh`

## 테스트 및 검증 방법
- 문서 절차대로 `curl`/`docker compose` 실행
- 또는:
  - `chmod +x scripts/e2e/whitelabel_e2e.sh`
  - `scripts/e2e/whitelabel_e2e.sh`

## 주의사항
- 운영에서는 `GATEWAY_INTERNAL_TOKEN` 등 시크릿을 반드시 교체
- 오프라인 임베딩 사용 시 모델을 `./models/embedding`에 사전 배치 필요

