# 2026-01-08 — Context Packing v1 (작업 유형 분류 + 토큰 예산)

## 요청자 요구사항 요약
- (B) 컨텍스트 빌더(컨텍스트 팩킹)
  - 질의/작업 유형 분류(autocomplete vs refactor vs bugfix 등)
  - 토큰 예산 내에서 관련 파일/스니펫을 선별하여 LLM 컨텍스트에 담기

## Assistant 응답(무엇을 할지)
- 서버 측 ContextBuilder에 “작업 유형 분류 + 토큰/문자 예산 기반 컨텍스트 선택/절단”을 추가한다.
- 외부 모델 호출 없이 온프레미스에서도 동작하도록 v1은 휴리스틱으로 시작한다.
- 테스트로 예산 준수(truncated)와 분류 동작을 검증한다.

## 실제 수행 변경(요약)
- `ContextBuilderService`
  - 작업 유형 분류(휴리스틱) 추가
  - `max_context_tokens/max_context_chars` 예산 도입
  - 예산 초과 시 줄 단위 절단 + `... (truncated)` 마커 추가
- `POST /rag/context`
  - 요청에 선택 필드 `taskType/maxContextTokens/maxContextChars` 추가
- 안정화
  - IDE 컨테이너 목록 응답에서 docker raw status(`created`)가 enum 검증을 깨는 문제를 상태 정규화로 해결
- 테스트
  - 컨텍스트 예산 준수/절단(truncated) 테스트 추가
  - 전체 `pytest` 통과 확인

## 변경 파일 목록
- `apps/api/src/services/context_builder.py`
- `apps/api/src/routers/rag.py`
- `apps/api/src/routers/ide.py`
- `apps/api/tests/test_context_builder.py`
- `docs/0012-context-packing-v1.md`

## 테스트 및 검증 방법
- `cd apps/api && pytest -q`

## 향후 작업 제안/주의사항
- v2: cursor 주변 컨텍스트(autocomplete)에 대한 전용 입력(파일/라인/커서 위치) 전달 및 우선순위 반영
- v2: 심볼 인덱스(정의/참조)와 결합해 “파일 단위”보다 더 정확한 컨텍스트 선택

