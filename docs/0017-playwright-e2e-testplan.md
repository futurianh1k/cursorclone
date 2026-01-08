# 0017 - Playwright E2E 테스트 케이스 설계 (화이트라벨 SaaS 검증)

이 문서는 “화이트라벨 SaaS 검증” 관점에서 **Playwright E2E 테스트 케이스**를 체계적으로 설계한 문서입니다.

## 범위(현재 구현/자동화 기준)

- **Web UI**: 로그인, 대시보드, 워크스페이스 생성/조회/삭제, IDE 시작/중지/열기(부분)
- **AI Gateway**: 헬스, Chat(최소 요청/응답), RAG stats/search(응답 스키마)
- **IDE 내부 UI(Tabby 자동완성/Continue 채팅 UI)**: *현재는 자동화 난이도가 높아 P2로 분류(대체 검증 권장)*

## 전제/환경 변수

- Web: `E2E_WEB_URL` (기본 `http://localhost:3000`)
- API: `E2E_API_URL` (기본 `http://localhost:8000`)
- Gateway: `E2E_GATEWAY_URL` (기본 `http://localhost:8081`)
- Chromium: `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` (기본 `/usr/bin/chromium`)
- Chat 모델: `E2E_CHAT_MODEL` (기본 `Qwen/Qwen2.5-Coder-7B-Instruct`)

> 온프레미스/VDE 제약 상 Playwright 브라우저 자동 다운로드는 금지/회피합니다(`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`).

## 테스트 데이터/상태 관리 전략

- `globalSetup`에서:
  - 임시 계정 signup/login → Web용 `access_token`을 localStorage에 주입한 `storageState` 생성
  - 테스트용 workspace 생성
  - `/api/auth/gateway-token`으로 **워크스페이스 스코프 토큰(gatewayToken)** 발급
- 산출물(커밋 제외):
  - `apps/web/.e2e/storage-state.json`
  - `apps/web/.e2e/creds.json`
  - `apps/web/.e2e/state.json` (workspaceId/projectId/gatewayToken 포함)

## Flakiness(불안정성) 대응 원칙

- **P0는 “기능 살아있음”을 빠르게 보장**하는 스모크만 포함
- IDE 프로비저닝/모델 로딩은 환경 영향을 크게 받으므로:
  - popup open/IDE 내부 UI는 **best-effort 또는 별도 레벨(P2)**로 격리
  - 상태 변화는 폴링/타임아웃을 길게 두되, 실패 시 원인(상태/응답)만 남기고 민감정보는 출력하지 않음

---

## 테스트 케이스 목록(우선순위)

### P0 (Smoke) — 매 배포/운영 점검 시

- **AUTH-01 로그인 성공(UI)**: `/login` → `/dashboard` 이동
- **AUTH-02 미인증 차단**: 토큰 없이 `/dashboard` 접근 시 `/login` 리다이렉트
- **AUTH-03 로그아웃**: 로그아웃 클릭 시 `/login` 이동 + 토큰 제거

- **WS-01 대시보드 렌더**: Workspaces 화면 로딩
- **WS-02 워크스페이스 생성(UI, 빈 워크스페이스)**: 모달 → 생성 → 성공 메시지/리스트 반영

- **GW-01 Gateway 헬스**: `GET /healthz` 200
- **GW-02 Chat 스모크**: `POST /v1/chat/completions` 200~399(환경에 따라 응답 지연 가능)

- **RAG-01 Stats 스모크**: `GET /v1/rag/stats` 200 + 응답 스키마 확인
- **RAG-02 Search 스모크**: `POST /v1/rag/search` 200 + 응답 스키마 확인(결과가 비어도 OK)

### P1 (Regression) — 주 1회/릴리즈 전

- **WS-03 삭제 확인 UX**: “삭제”→“확인/취소” 플로우
- **IDE-01 시작/중지 상태 변화**: `stopped → starting → running` / `running → stopped`
- **IDE-02 새로고침 후 상태 유지**: 대시보드 reload 이후에도 상태 일치
- **PRJ-01 프로젝트 수정**: 이름/설명 변경 후 반영
- **PRJ-02 프로젝트 삭제 정책**: 워크스페이스 존재 시 삭제 비활성/차단

### P2 (Deep/Hard) — 선택(불안정/환경 의존)

- **IDE-UI-01 code-server 접속(암호 없음)**: IDE URL 접속 성공
- **TAB-UI-01 Tabby 자동완성 UI 검증**: editor suggestion 발생 확인 (*flaky*)
- **CHAT-UI-01 Continue/Chat UI가 Gateway 경유로 응답하는지** (*추적/로그 기반 검증이 더 안정적*)

---

## 참고/출처

- Playwright Test 공식 문서: `https://playwright.dev/docs/test-intro`

