# 0016 - Playwright E2E 테스트 자동화 (On-Prem / VDE 친화)

이 문서는 **Cursor On-Prem PoC의 Web(UI) 흐름**을 Playwright로 자동 검증하기 위한 최소 구성입니다.

## 목표

- Web UI 기준으로 아래 플로우를 **스모크 수준으로 자동 검증**
  - 로그인 페이지 동작
  - 대시보드 접근(인증 상태)
  - 워크스페이스 생성 모달 → 워크스페이스 생성(최소)
  - (Best-effort) IDE 시작 버튼 클릭 시 popup(open) 시도

## 보안/온프레미스 제약

- **외부 인터넷 다운로드를 전제로 하지 않음**
  - Playwright의 브라우저 자동 다운로드는 차단/회피합니다.
  - 시스템에 설치된 Chromium을 사용하거나, 환경변수로 실행 파일 경로를 지정합니다.

## 설치/실행 방법

### 1) (권장) 시스템 Chromium 준비

- Ubuntu 예시:

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium
```

> 환경에 따라 패키지 이름이 다를 수 있습니다.

### 2) apps/web 의존성 설치 (내부 레지스트리 사용 권장)

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/web
npm install --legacy-peer-deps
```

### 3) E2E 실행

기본값(로컬):

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/web
E2E_WEB_URL=http://localhost:3000 \
E2E_API_URL=http://localhost:8000 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
npm run test:e2e
```

Docker Compose로 띄운 상태(기본 포트):

- Web: `http://localhost:3000`
- API: `http://localhost:8000`

### 환경 변수

- **`E2E_WEB_URL`**: Web base URL (기본 `http://localhost:3000`)
- **`E2E_API_URL`**: API base URL (기본 `http://localhost:8000`)
- **`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`**: 시스템 chromium 경로(기본 `/usr/bin/chromium`)
- **`E2E_EMAIL`**, **`E2E_PASSWORD`**: 고정 계정으로 실행하고 싶을 때 선택 지정
  - 지정하지 않으면 매 실행마다 임시 계정을 생성합니다(충돌 회피 목적).

## 생성되는 산출물(민감정보 제외)

- `apps/web/.e2e/`
  - `storage-state.json`: 테스트 런용 localStorage(access_token) 저장
  - `creds.json`: UI 로그인 스모크 테스트용 임시 계정(이메일/테스트 비밀번호)
- `apps/web/playwright-report/`, `apps/web/test-results/`

위 경로들은 `.gitignore`에 포함되어 커밋되지 않습니다.

## 참고/출처

- Playwright Test 공식 문서: `https://playwright.dev/docs/test-intro`

