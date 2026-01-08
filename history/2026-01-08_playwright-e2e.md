# 변경 내역: Playwright E2E 테스트 자동화 추가 (2026-01-08)

## 요청자 요구사항 요약

- Web UI 테스트 자동화를 적용해달라.
- 도구는 **Playwright**를 사용한다.

## Assistant(제가) 응답 내용(무엇을 할지)

- `apps/web`에 Playwright 기반 E2E 스모크 테스트를 추가한다.
- 온프레미스/VDE 환경을 고려해 **브라우저 자동 다운로드를 강제하지 않고**, 시스템 Chromium 또는 지정된 실행 파일을 사용하도록 구성한다.

## 실제로 수행한 변경 내용(파일/설계 요약)

- `apps/web/package.json`
  - `@playwright/test` devDependency 추가
  - `test:e2e`, `test:e2e:ui`, `test:e2e:headed` 스크립트 추가
  - `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`을 스크립트에 포함(다운로드 억제)
- `apps/web/playwright.config.ts`
  - `E2E_WEB_URL` 기반 baseURL 구성
  - `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 기반 실행 파일 경로 지정
  - globalSetup/리포터/타임아웃 설정
- `apps/web/e2e/global-setup.ts`
  - API를 통해 임시 계정 생성/로그인 후 localStorage `access_token` 주입
  - `apps/web/.e2e/` 아래 storageState 및 creds 생성(커밋 제외)
- `apps/web/e2e/whitelabel.spec.ts`
  - 대시보드 로딩(인증) 스모크
  - 워크스페이스 생성(UI) 스모크
  - (best-effort) IDE 시작 버튼 클릭 시 popup 오픈 시도
  - UI 로그인 스모크(별도)
- `.gitignore`
  - Playwright 결과물 및 `.e2e/` 디렉토리 커밋 제외
- `docs/0016-playwright-e2e.md`
  - 운영자 관점 실행 방법/환경변수/제약 문서화

## 테스트 및 검증 방법

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/web
E2E_WEB_URL=http://localhost:3000 \
E2E_API_URL=http://localhost:8000 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
npm run test:e2e
```

> 주의: 패키지 설치는 내부 레지스트리/허용된 네트워크에서 수행해야 합니다.

## 향후 작업 제안 또는 주의사항

- IDE 컨테이너 프로비저닝/모델 로딩은 환경에 따라 오래 걸릴 수 있어 popup 검증은 best-effort로 두었습니다.
- 안정적인 UI selector를 위해 필요 시 `data-testid` 도입을 확대할 수 있습니다.

