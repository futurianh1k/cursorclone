# 0011 - Context Layer v1 (RAG 안정화: 스코프/증분 인덱싱)

## 사용자 요구사항 요약
- Cursor처럼 “프로젝트 전체 컨텍스트”가 안정적으로 동작하도록 다음 4요소가 함께 필요
  - (A) 인덱싱/리트리벌(검색) 레이어(텍스트/벡터, 변경 감지)
  - (B) 컨텍스트 빌더(컨텍스트 팩킹)
  - (C) 로컬/서버 모델 서빙(vLLM/임베딩/Tabby)
  - (D) 권한/보안/감사(스코프 권한, Gateway DLP/감사, Upstream auth 분리)

## 이번 단계(v1)에서 반영한 것
### (A) 변경 감지 + 증분 인덱싱 기반 마련
- `workspace_file_index` 테이블을 추가하여 파일 단위로 **sha256/mtime/size** 메타를 저장
- Code indexer가 전체 재인덱싱이 아닌 **변경된 파일만 재인덱싱**할 수 있도록 증분 경로를 추가

### (A)(D) 스코프 강제(tenant/project/workspace)
- Qdrant payload에 `tenant_id`, `project_id`를 포함하도록 확장
- Vector search에서 `workspace_id`는 필수, 가능한 경우 `tenant_id`, `project_id`로 추가 필터링
  - 목적: “프로젝트 전체 컨텍스트”를 다룰수록 데이터 혼입/유출 리스크가 커지므로, 검색 단계에서 격리를 강제

### API 연결
- `POST /rag/index`가 내부적으로 증분 인덱싱 경로를 사용하도록 변경
- `/rag/search`, `/rag/context`도 workspace→project/org를 조회하여 검색/컨텍스트 빌드에 스코프를 전달

## 변경된/추가된 파일
- DB 모델
  - `apps/api/src/db/models.py`
    - `WorkspaceFileIndexModel`
    - `WorkspaceSymbolModel` (심볼 인덱스는 v2에서 실제 추출 로직 연결 예정)
- 마이그레이션
  - `apps/api/migrations/versions/2026_01_08_0001-add_workspace_file_index_and_symbols.py`
- 인덱서
  - `apps/api/src/services/code_indexer.py`
    - `index_workspace_incremental()`
    - `index_file_with_scope()`
    - payload에 tenant/project 포함
- 벡터 스토어
  - `apps/api/src/services/vector_store.py`
    - tenant/project payload index 추가
    - `search()`에 tenant_id/project_id 필터 옵션 추가
- RAG 라우터
  - `apps/api/src/routers/rag.py`
    - 증분 인덱싱 호출
    - search/context에서 스코프 전달

## 테스트/검증
- (DB 없이) 단위 테스트 기준으로 아래는 통과하도록 정리
  - `apps/api/tests/test_context_builder.py` (현행 ContextBuilderService 기준으로 재작성)
  - `apps/api/tests/test_ide.py` (DB 의존 없이 dependency overrides로 동작)

## 다음 단계(v2) 제안
- (B) 컨텍스트 팩킹 고도화
  - 작업 유형 분류(autocomplete/refactor/bugfix 등)
  - 토큰 예산 기반 요약/스니펫/심볼 중심 추출
- (A) 심볼 인덱스 실제 추출 연결
  - Python(ast), TS/JS(tsserver), Go(gopls) 등 언어별 최소 파서/프로토콜 연동
- (D) Gateway `/v1/rag` 경유(100% gateway) 및 감사/DLP 일관화

