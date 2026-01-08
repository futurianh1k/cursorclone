# 0012 - Context Packing v1 (작업 유형 분류 + 토큰 예산 기반)

## 목표
RAG 검색 결과를 “그냥 많이” 붙이는 방식에서 벗어나, **작업 유형에 맞는 컨텍스트를**  
**토큰 예산 안에서** 안정적으로 구성한다.

## 구현 요약
### 1) 작업 유형 분류 (v1: 휴리스틱)
- 입력 `query` 및 `current_file/current_file_content` 존재 여부를 기반으로
  - `autocomplete`, `refactor`, `bugfix`, `explain`, `search`, `chat` 중 하나로 분류
- 외부 모델 호출 없이 온프레미스에서 안정적으로 동작하도록 단순 규칙 기반으로 시작

### 2) 예산 기반 컨텍스트 팩킹
- `max_context_tokens` / `max_context_chars` 예산을 도입 (미지정 시 서버 기본값)
- current file을 최우선 포함하되, 예산이 작으면 **잘라서라도 포함**
- 검색 결과는 score 우선 정렬 후, 작업 유형별 정책으로 파일당 청크 수 제한
  - `bugfix/refactor`: 파일당 최대 2청크
  - `autocomplete`: 파일당 최대 1청크 (과잉 컨텍스트 방지)
- 예산 초과 시 줄 단위로 잘라 `... (truncated)` 마커로 표시

### 3) API(선택 필드 추가)
- `POST /rag/context` 요청에 아래 필드를 선택적으로 추가
  - `taskType` (미지정 시 서버 분류)
  - `maxContextTokens`
  - `maxContextChars`

## 변경 파일
- `apps/api/src/services/context_builder.py`
  - 작업 유형 분류/팩킹/토큰 추정/절단 로직 추가
- `apps/api/src/routers/rag.py`
  - `ContextRequest`에 선택 필드 추가 및 서비스로 전달
- `apps/api/tests/test_context_builder.py`
  - 분류/예산 절단 동작 테스트 추가

## 제한/후속 작업
- v1은 휴리스틱 분류이므로, v2에서 아래를 고도화 예정
  - 작업 유형 분류 정확도 향상(IDE 이벤트/명시 태그/경량 모델 등)
  - 심볼 기반(정의/참조) 우선순위 반영
  - “현재 파일의 커서 주변”을 중심으로 하는 autocomplete 전용 컨텍스트

