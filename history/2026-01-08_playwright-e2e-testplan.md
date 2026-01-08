# 변경 내역: Playwright E2E 케이스 설계 및 범위 확장 (2026-01-08)

## 요청자 요구사항 요약

- “현재 playwright 테스트 자동화의 범위”를 설명하고,
- “테스트 케이스를 설계”한 뒤,
- “합시다”에 따라 실제 자동화를 확장한다.

## Assistant(제가) 응답 내용(무엇을 할지)

- 화이트라벨 SaaS 검증 관점에서 P0/P1/P2로 테스트 케이스를 설계/문서화한다.
- globalSetup에 workspace 생성 및 `/api/auth/gateway-token` 발급을 추가하여,
  Gateway/RAG 테스트가 **워크스페이스 스코프 토큰**으로 실행되도록 한다.
- UI 안정성을 위해 `data-testid`를 최소 도입한다.

## 실제로 수행한 변경 내용(파일/설계 요약)

- `apps/web/e2e/global-setup.ts`
  - 임시 계정 로그인 후 **workspace 생성** + **gateway-token 발급**
  - `.e2e/state.json`에 `workspaceId/projectId/gatewayToken` 저장(커밋 제외)
- `apps/web/e2e/helpers.ts`
  - creds/state 로딩 유틸 추가
- `apps/web/e2e/auth.spec.ts`
  - `/dashboard` 미인증 리다이렉트, 로그아웃 스모크 추가
- `apps/web/e2e/gateway.spec.ts`
  - `/healthz`, `/v1/chat/completions` 스모크 추가
- `apps/web/e2e/rag.spec.ts`
  - `/v1/rag/stats`, `/v1/rag/search` 스모크 추가
- `apps/web/e2e/whitelabel.spec.ts`
  - selector를 `data-testid` 기반으로 안정화
- UI selector 안정화
  - `apps/web/src/app/login/page.tsx` / `apps/web/src/app/dashboard/layout.tsx` / `apps/web/src/app/dashboard/page.tsx`
  - 필요한 곳에 `data-testid` 추가
- 문서
  - `docs/0017-playwright-e2e-testplan.md` 추가 (케이스 설계/우선순위)

## 테스트 및 검증 방법

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/web
E2E_WEB_URL=http://localhost:3000 \
E2E_API_URL=http://localhost:8000 \
E2E_GATEWAY_URL=http://localhost:8081 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
npm run test:e2e
```

## 향후 작업 제안 또는 주의사항

- IDE 내부 UI(자동완성/채팅 UI)는 환경/렌더링 영향으로 flakiness가 높아 P2로 분리했습니다.
- 더 안정적인 회귀 테스트를 위해서는:
  - IDE 상태/설정은 **컨테이너 exec/로그 기반 검증**을 병행하거나
  - UI에 `data-testid` 범위를 확대하는 접근을 권장합니다.

