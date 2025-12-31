# 2025-12-31 - Task D: vLLM Router 구현 완료

## 사용자 요구사항

- Task D 수행: vLLM Router 스켈레톤 구현
- vLLM OpenAI 호환 endpoint 클라이언트
- streaming 응답을 SSE로 프록시
- timeout/retry/예외 처리 포함

## 구현 답변

vLLM OpenAI 호환 API 클라이언트를 구현하고, Context Builder와 연동하여 전체 AI 흐름을 완성했습니다.

### 구현 내용

1. **vLLM 클라이언트** (`llm/client.py`)
   - OpenAI 호환 API 클라이언트 (`LLMClient`)
   - `chat()`: non-streaming 채팅 완료 요청
   - `chat_stream()`: streaming 채팅 요청
   - 재시도 로직 (최대 3회, 지수 백오프)
   - 타임아웃 처리 (기본 60초)
   - 에러 처리 (`LLMError`, `LLMTimeoutError`)

2. **SSE 유틸리티** (`llm/sse.py`)
   - `create_sse_response()`: 스트리밍 응답을 SSE 형식으로 변환
   - `create_sse_chunk()`: SSE 청크 생성
   - FastAPI StreamingResponse 활용

3. **AI 라우터 연동** (`routers/ai.py`)
   - `/api/ai/explain`: Context Builder → vLLM → 응답
   - `/api/ai/rewrite`: Context Builder → vLLM → diff 반환
   - 에러 처리 (타임아웃, 서비스 오류)
   - 토큰 사용량 추적

4. **애플리케이션 생명주기** (`main.py`)
   - shutdown 이벤트에서 LLM 클라이언트 종료

## 수정 내역 요약

### 추가된 파일
- `apps/api/src/llm/__init__.py`: LLM 모듈 초기화
- `apps/api/src/llm/client.py`: vLLM 클라이언트 구현
- `apps/api/src/llm/sse.py`: SSE 유틸리티 구현
- `history/2025-12-31_task-d-vllm-router.md`: 변경 이력 (본 문서)

### 수정된 파일
- `apps/api/src/routers/ai.py`: vLLM 클라이언트 연동
- `apps/api/src/main.py`: LLM 클라이언트 종료 로직 추가
- `apps/api/pyproject.toml`: httpx 의존성 추가

### 주요 설계 결정

1. **OpenAI 호환 API**
   - vLLM이 OpenAI 호환 API를 제공하므로 표준 형식 사용
   - `/v1/chat/completions` 엔드포인트 사용

2. **재시도 전략**
   - 서버 오류(5xx)만 재시도
   - 클라이언트 오류(4xx)는 즉시 실패
   - 지수 백오프 (1초, 2초, 3초)

3. **에러 처리**
   - 타임아웃: 504 Gateway Timeout
   - 서비스 오류: 503 Service Unavailable
   - 상세 에러는 내부 로그에만 기록 (AGENTS.md 규칙)

4. **스트리밍 지원**
   - SSE 형식으로 프록시
   - 청크 단위로 전송
   - `[DONE]` 신호로 종료

## 테스트

### Import 테스트
```bash
cd apps/api && python -c "from src.llm import get_llm_client; print('LLM client import successful')"
```
✅ 성공

### 기능 테스트
- LLM 클라이언트 인스턴스 생성
- 메시지 형식 변환
- 에러 처리

### TODO
- 실제 vLLM 서버와 통합 테스트
- 스트리밍 응답 테스트
- 재시도 로직 테스트

## 설정

### 환경 변수
- `VLLM_BASE_URL`: vLLM 서버 URL (기본값: `http://localhost:8001/v1`)
- `VLLM_API_KEY`: API 키 (기본값: `dummy-key`, vLLM은 키 불필요)

### vLLM 서버 실행
```bash
# Docker Compose 사용
cd infra/llm && docker-compose -f vllm-compose.yml up -d

# 또는 직접 실행
docker run --gpus all -p 8001:8000 vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --dtype half
```

## 전체 흐름

```
┌─────────────┐
│   Web IDE   │
└──────┬──────┘
       │ POST /api/ai/explain
       ▼
┌──────────────────┐
│   API Gateway    │
│   (FastAPI)      │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Context Builder  │
│ - 컨텍스트 조합   │
│ - 프롬프트 생성   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  vLLM Client     │
│  - OpenAI 호환   │
│  - 재시도/타임아웃│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│   vLLM Server    │
│   (On-Prem)      │
└──────────────────┘
```

## 향후 작업

1. **스트리밍 엔드포인트 추가**
   - `/api/ai/explain/stream` (SSE)
   - `/api/ai/rewrite/stream` (SSE)

2. **성능 최적화**
   - 연결 풀링
   - 요청 큐잉
   - 배치 처리

3. **모니터링**
   - 응답 시간 추적
   - 토큰 사용량 집계
   - 에러율 모니터링

4. **테스트 코드 작성**
   - 단위 테스트 (LLM 클라이언트)
   - 통합 테스트 (전체 흐름)
   - Mock vLLM 서버

## 참고

- **원본 태스크**: `codex/tasks/task-d-llm-router.md`
- **vLLM 문서**: https://docs.vllm.ai/
- **OpenAI API 참조**: https://platform.openai.com/docs/api-reference
- **Context Builder**: `docs/context-builder.md`
- **구현 위치**: `apps/api/src/llm/`
