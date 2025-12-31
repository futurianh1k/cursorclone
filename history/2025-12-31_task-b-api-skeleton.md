# 2025-12-31 - Task B: API 명세 반영 (스켈레톤 구현)

## 사용자 요구사항

- Task B 수행: `docs/api-spec.md` 기준으로 FastAPI 라우터/스키마(Pydantic) 구성
- 아직 실제 기능 구현은 하지 말고, 입력검증/에러코드/TODO 포함

## 구현 답변

`docs/api-spec.md`에 정의된 모든 엔드포인트에 대한 FastAPI 라우터와 Pydantic 스키마를 구현했습니다.

### 구현 내용

1. **Pydantic 스키마 정의** (`apps/api/src/models.py`)
   - Auth, Workspaces, Files, AI, Patch, WebSocket 관련 모든 Request/Response 모델
   - 입력 검증 (경로 탈출 방지, 범위 검증 등)
   - 에러 응답 모델

2. **라우터 구현** (`apps/api/src/routers/`)
   - `auth.py`: GET /api/auth/me
   - `workspaces.py`: POST/GET /api/workspaces
   - `files.py`: GET /api/workspaces/{wsId}/files, GET/PUT /content
   - `ai.py`: POST /api/ai/explain, POST /api/ai/rewrite
   - `patch.py`: POST /api/patch/validate, POST /api/patch/apply
   - `ws.py`: WS /ws/workspaces/{wsId}

3. **main.py 수정**
   - 모든 라우터 등록
   - CORS 설정 (환경변수 지원)
   - 전역 에러 핸들러
   - OpenAPI 문서 자동 생성

4. **API 명세 상세화** (`docs/api-spec.md`)
   - 각 엔드포인트의 Request/Response 스키마
   - 에러 코드 정의
   - 흐름 설명 (특히 AI → Patch 경로)

## 수정 내역 요약

### 추가된 파일
- `apps/api/src/models.py`: Pydantic 스키마 정의 (신규)
- `apps/api/src/routers/__init__.py`: 라우터 모듈 초기화 (신규)
- `apps/api/src/routers/auth.py`: Auth 라우터 (신규)
- `apps/api/src/routers/workspaces.py`: Workspaces 라우터 (신규)
- `apps/api/src/routers/files.py`: Files 라우터 (신규)
- `apps/api/src/routers/ai.py`: AI 라우터 (신규)
- `apps/api/src/routers/patch.py`: Patch 라우터 (신규)
- `apps/api/src/routers/ws.py`: WebSocket 라우터 (신규)
- `history/2025-12-31_task-b-api-skeleton.md`: 변경 이력 (본 문서)

### 수정된 파일
- `apps/api/src/main.py`: 라우터 등록 및 설정 추가
- `docs/api-spec.md`: 상세 명세 추가 (Request/Response, 에러 코드, 흐름)

### 주요 설계 결정

1. **보안 우선**
   - 모든 경로 입력에 대해 `../` 탈출 검증
   - 절대 경로 금지
   - 워크스페이스 격리 검증 함수 포함

2. **AGENTS.md 규칙 준수**
   - API는 LLM을 직접 호출하지 않음 (Context Builder 경유)
   - 코드 변경은 반드시 Patch 경로로 적용
   - 에러 메시지는 일반적인 메시지만 반환

3. **확장 가능한 구조**
   - 라우터별 모듈 분리
   - 공통 검증 함수 분리 가능
   - TODO 주석으로 구현 가이드 제공

## 테스트

### Import 테스트
```bash
cd apps/api && python -c "from src.main import app; print('Import successful')"
```
✅ 성공

### OpenAPI 문서
- `/docs`: Swagger UI
- `/redoc`: ReDoc

### TODO 항목
모든 라우터에 TODO 주석 포함:
- 실제 기능 구현
- DB 연동
- Context Builder 연동 (AI 라우터)
- diff-utils 연동 (Patch 라우터)
- SSO/LDAP 연동 (Auth 라우터)

## 향후 작업

1. **Task C (Diff 유틸)**: `packages/diff-utils` 구현 후 Patch 라우터 연동
2. **Context Builder**: `docs/context-builder.md` 설계 기반 구현 후 AI 라우터 연동
3. **Task D (vLLM Router)**: LLM 클라이언트 구현 후 Context Builder 연동
4. **실제 기능 구현**: 각 라우터의 TODO 항목 구현

## 참고

- **원본 태스크**: `codex/tasks/task-b-api-skeleton.md`
- **API 명세**: `docs/api-spec.md`
- **아키텍처**: `docs/architecture.md`
- **AGENTS 규칙**: `AGENTS.md`
