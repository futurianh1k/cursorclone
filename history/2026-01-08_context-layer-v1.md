# 2026-01-08 — Context Layer v1 (RAG 스코프/증분 인덱싱)

## 요청자 요구사항 요약
- Cursor 수준의 “프로젝트 전체 컨텍스트”를 위해 (A)~(D) 구성요소를 갖추고,
  특히 RAG 결과가 **권한/스코프 필터**를 거친 뒤에만 사용되도록 할 것.

## Assistant 응답(무엇을 할지)
- RAG의 가장 중요한 기반인
  - **(A) 변경 감지/증분 인덱싱 메타**
  - **(D) tenant/project/workspace 스코프 강제**
  를 먼저 안정화하고, API 라우터까지 연결한다.

## 실제 수행 변경(요약)
- DB
  - `workspace_file_index`: 파일 해시/mtime/size 메타 저장(원문 저장 금지)
  - `workspace_symbols`: 심볼 인덱스 테이블(추출 로직은 후속)
- 인덱서
  - 증분 인덱싱 함수 추가 및 `/rag/index`에서 사용
  - 임베딩 payload에 `tenant_id`, `project_id` 포함
- Vector store(Qdrant)
  - payload index에 `tenant_id`, `project_id` 추가
  - 검색 시 workspace 기본 + tenant/project 조건을 추가로 필터링
- API
  - `/rag/search`, `/rag/context`가 workspace→project/org를 조회해 스코프를 전달
- 테스트 정리
  - 현행 구조에 맞게 ContextBuilder 테스트 재작성
  - DB 없는 환경에서도 IDE 테스트가 돌 수 있게 dependency overrides 적용
  - IDE 라우터 내부 함수명 불일치(NameError) 수정

## 변경 파일 목록
- `apps/api/src/db/models.py`
- `apps/api/migrations/versions/2026_01_08_0001-add_workspace_file_index_and_symbols.py`
- `apps/api/src/services/code_indexer.py`
- `apps/api/src/services/vector_store.py`
- `apps/api/src/services/context_builder.py`
- `apps/api/src/routers/rag.py`
- `apps/api/src/routers/ide.py`
- `apps/api/tests/test_context_builder.py`
- `apps/api/tests/test_audit_service.py`
- `apps/api/tests/test_filesystem.py`
- `apps/api/tests/test_ide.py`
- `apps/api/tests/test_workspace_delete.py`
- `docs/0011-context-layer-v1.md`

## 테스트 및 검증 방법
- (DB 없이) 단위 테스트 확인:
  - `cd apps/api && pytest -q tests/test_context_builder.py tests/test_ide.py`

## 향후 작업 제안/주의사항
- (B) 컨텍스트 팩킹(작업 유형 분류 + 토큰 예산 내 요약/스니펫/심볼 중심) 구현 필요
- (D) “100% Gateway 경유”를 위해 Gateway에 `/v1/rag` 라우팅 연결 필요
- 운영 환경에서는 임베딩 모델/Tabby 모델 캐시를 **외부 다운로드 없이** 공급할 경로/이미지 전략 필요

