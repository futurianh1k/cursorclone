# 0018 - 솔루션 사용자 매뉴얼 (Cursor On-Prem PoC)

대상: 이 솔루션을 실제로 사용하는 **개발자/일반 사용자**, **운영자(관리자)**, **보안/감사 담당자**

목표: **로그인 → 워크스페이스 생성 → IDE(code-server) 접속 → Tabby 자동완성/Continue 채팅 → RAG 검색/컨텍스트**까지 “사용자 관점”에서 빠르게 따라할 수 있게 안내합니다.

> 보안 원칙(중요)
> - 토큰/비밀번호/내부 토큰(`GATEWAY_INTERNAL_TOKEN`) 등 **민감정보를 문서/티켓/채팅에 붙여넣지 마세요.**
> - 이 레포의 검증 스크립트/리포트는 원문을 저장하지 않도록 설계되어 있습니다(필요 시 해시/메타데이터만).

---

## 1) 구성요소 한 장 요약

- **Web(대시보드)**: 사용자 로그인, 프로젝트/워크스페이스 관리, IDE 열기
- **API(FastAPI)**: 워크스페이스/파일/IDE 프로비저닝, RAG 인덱싱/컨텍스트 빌드
- **AI Gateway**: 모든 AI 요청의 단일 진입점(인증/인가/DLP/감사/Upstream 분리)
- **IDE(code-server)**: 브라우저 기반 VS Code, 워크스페이스별 설정(토큰/endpoint) 자동 주입
- **Tabby**: 자동완성 서버( Gateway가 `/v1/completions`, `/v1/health`를 Tabby로 라우팅 )
- **(선택) vLLM**: Chat/Agent 모델 서빙( Gateway가 `/v1/chat/*`를 upstream으로 라우팅 )
- **(선택) RAG(Qdrant)**: 코드 임베딩 검색 + 컨텍스트 팩킹

---

## 2) 역할(Role)과 권한(요약)

권한은 운영 정책에 따라 달라질 수 있습니다. 기본적으로 다음 흐름을 권장합니다.

- **viewer**: autocomplete/채팅/RAG 조회(검색/컨텍스트) 사용
- **developer**: agent 기능(코드 변경 자동화 등) 사용
- **admin**: RAG 인덱싱(`/v1/rag/index`) 같은 운영성 기능 수행

> 운영 팁: “인덱싱”은 리소스가 크므로 관리자 역할로 제한하는 것이 안전합니다.

---

## 3) 개발자/일반 사용자 빠른 시작(5분)

### 3-1) 로그인

1. 브라우저로 Web 접속 (예: `http://<host>:3000`)
2. **로그인**(또는 최초 1회 **회원가입**)
3. 로그인 성공 시 **대시보드(`/dashboard`)**로 이동합니다.

문제 해결:
- 로그인 후 바로 튕김/401: **로그아웃 → 재로그인** 후 재시도

### 3-2) 워크스페이스 생성

1. 대시보드에서 **새 워크스페이스** 버튼 클릭
2. 프로젝트 선택(또는 새 프로젝트 생성)
3. 워크스페이스 이름 입력 후 생성

생성 후:
- 목록에 워크스페이스가 나타나고, **IDE 프로비저닝이 백그라운드로 시작**됩니다.

### 3-3) IDE(code-server) 열기

1. 워크스페이스 행에서 **IDE 열기/시작** 버튼 클릭
2. 새 창(팝업)으로 code-server가 열립니다.

IDE에서 확인할 것:
- 파일 트리/에디터가 보이는지
- 파일 생성/수정/저장 후 새로고침해도 반영되는지(워크스페이스 볼륨)

---

## 4) IDE에서 AI 기능 사용(사용자 관점)

### 4-1) Tabby 자동완성

동작 방식(요약):
- IDE 컨테이너가 시작될 때, 워크스페이스별로 **Gateway endpoint + 워크스페이스 스코프 토큰**이 IDE 설정으로 주입됩니다.
- Gateway는 `/v1/completions`, `/v1/health` 요청을 **Tabby upstream**으로 라우팅합니다.

사용 방법:
- 코드 입력 중 **자동완성(인라인 제안)**이 뜨는지 확인합니다.

문제 해결(사용자):
- 자동완성이 전혀 안 뜨면:
  - 먼저 IDE를 새로고침
  - 그래도 안 되면 운영자에게 “Gateway/Tabby 상태 확인” 요청

### 4-2) Continue(채팅/코드 도움)

동작 방식(요약):
- Continue 설정도 IDE 시작 시 자동 주입되며, Chat 요청은 Gateway의 `/v1` 경로로 나가도록 구성됩니다.

사용 방법:
- Continue 패널에서 간단히 “ping” 같은 질문을 보내 응답이 오는지 확인합니다.

문제 해결(사용자):
- 응답이 매우 느림: 모델 워밍업/자원 이슈일 수 있으니 잠시 후 재시도
- 401/403: 워크스페이스 권한/토큰 만료 가능성(로그아웃/재로그인 후 재시도)

---

## 5) RAG(코드 검색/컨텍스트) 사용 가이드

현재 PoC는 “IDE 내부 UI에서 RAG를 풀로 체감”하기보다는,
운영/API 관점에서 **검색/컨텍스트 빌드 결과를 검증**하는 방식이 안정적입니다.

- 운영자가 복붙으로 검증하는 문서: `docs/0015-whitelabel-e2e-runbook.md`
- Gateway 경유 RAG API: `/v1/rag/*` (예: `/v1/rag/search`, `/v1/rag/context`)

사용자 관점에서 기대하는 결과:
- 검색 결과에 코드 스니펫이 포함되고,
- 컨텍스트 빌드 결과(prompt)가 토큰/문자 예산 내에서 **관련 파일 일부만** 포함합니다.

---

## 6) 운영자(관리자) 운영 체크리스트(요약)

운영자는 아래를 “정상/비정상”으로 빠르게 구분할 수 있어야 합니다.

### 6-1) 서비스 헬스

- API: `/health`
- Gateway: `/healthz`
- Web: `/api/health`

### 6-2) AI Gateway 정책

- workspace 사용자 토큰(Authorization)을 upstream(API/모델)에 그대로 전달하지 않는지
- Gateway가 내부 헤더(`X-User-Id`, `X-Tenant-Id`, `X-Project-Id`, `X-Workspace-Id`)로만 upstream에 스코프를 전달하는지
- DLP가 pre/post(특히 RAG 응답)에서 적용되는지

### 6-3) IDE 설정 주입(중요)

IDE 컨테이너 생성 시 아래가 자동으로 구성되어야 합니다(운영자 확인용).

- VS Code User settings에 Tabby endpoint/token이 설정됨
- Tabby 설정 파일이 마운트됨
- Continue 설정이 마운트됨

이 동작은 API의 IDE 프로비저닝 로직에서 수행됩니다.

---

## 7) 문제 해결(FAQ)

### Q1. “IDE는 열리는데 자동완성/채팅만 안 됩니다.”

가능성이 큰 순서:
- Tabby/vLLM 서버가 내려감 또는 upstream 라우팅 불가
- Gateway 인증/인가 설정(JWKS/issuer/audience) 불일치
- 워크스페이스 스코프 토큰 만료(IDE 재시작/재로그인 필요)

운영자 권장 확인:
- `docs/0015-whitelabel-e2e-runbook.md`의 Gateway/Tabby/RAG 점검 명령

### Q2. “RAG 검색 결과가 비어있습니다.”

가능성이 큰 순서:
- 인덱싱을 수행하지 않았거나, 워크스페이스 코드가 적음
- 오프라인 임베딩 모델 경로 미배치(Strict 모드에서 실패)
- Qdrant/컬렉션 상태 문제

운영자 권장 확인:
- `/v1/rag/index` 실행 및 `/v1/rag/stats` 확인
- 오프라인 임베딩 관련 문서: `docs/0013-embedding-offline-v1.md`

### Q3. “권한 오류(403)가 납니다.”

- admin 전용 기능(RAG 인덱싱 등)을 일반 계정으로 호출했을 수 있습니다.
- 테넌트/프로젝트/워크스페이스 스코프 불일치일 수 있습니다.

---

## 8) 관련 문서(권장 읽기 순서)

- `docs/0015-whitelabel-e2e-runbook.md` (운영자 복붙 검증)
- `docs/0016-playwright-e2e.md` (UI 스모크 자동화)
- `docs/0017-playwright-e2e-testplan.md` (테스트 케이스 설계/P0~P2)
- `docs/0004-newarchitecture-ai-gateway-v03.md` (Gateway 아키텍처/원칙)

---

## 참고/출처

- Playwright Test 공식 문서: `https://playwright.dev/docs/test-intro`

