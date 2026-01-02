# Cursor On-Prem PoC (Web) — Starter Repo

이 레포는 사내 온프레미스 환경에서 **웹 기반 Cursor-mini PoC**를 빠르게 착수하기 위한 스캐폴딩입니다.

## 구성
- `apps/web`: Next.js + Monaco 기반 Web IDE
- `apps/api`: FastAPI 기반 API 서버 (workspace/files/ai/patch/ws)
- `packages/shared-types`: API/WS DTO 타입 (TypeScript)
- `packages/diff-utils`: unified diff 파싱/검증/적용 유틸 (TypeScript)
- `packages/prompt-templates`: 프롬프트 템플릿
- `infra/llm`: vLLM 실행 예시 (온프레미스)

## Quickstart (개발자 PC 또는 사내 Dev 서버)

### 필수 요구사항
- Node 20+, pnpm, Python 3.11+

### 설치
```bash
pnpm -r install
cd apps/api && pip install -e ".[test]"
```

### 실행 (개발 모드)
```bash
# 터미널 1: API 서버 (개발 모드: ~/cctv-fastapi 사용)
cd apps/api
export DEV_MODE=true
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 터미널 2: Web 서버
cd apps/web
pnpm dev
```

브라우저에서 `http://localhost:3000` 접속

### 테스트 실행
```bash
cd apps/api
pytest tests/ -v
```

## 주요 기능

### ✅ 완료된 기능
- 워크스페이스 관리 (생성, 목록 조회)
- 파일 시스템 연동 (읽기, 쓰기, 트리 조회)
- Patch 검증 및 적용 (unified diff)
- Context Builder (프롬프트 생성)
- vLLM Router (LLM 통신)
- Web IDE (File Tree, Code Editor, AI Chat)

### 🔄 진행 중
- 통합 테스트
- 에러 처리 개선
- 성능 최적화

## 아키텍처

```
Web IDE (Next.js + Monaco)
    ↓
API (FastAPI)
    ↓
Context Builder → vLLM Router → vLLM
    ↓
Patch Engine → File System
```

## 보안

- 경로 탈출 방지 (`../` 차단)
- 확장자 allowlist
- 파일 크기 제한
- 워크스페이스 격리
- 해시 기반 감사 로그 (원문 저장 안 함)

## 문서

- `docs/architecture.md`: 시스템 아키텍처
- `docs/api-spec.md`: API 명세
- `docs/context-builder.md`: Context Builder 설계
- `docs/runbook-onprem.md`: 온프레미스 운영 가이드
- `history/`: 변경 이력 문서

## Codex 작업
- `AGENTS.md` 규칙을 읽고 작업하도록 설정되어 있습니다.
- `codex/tasks/`에 Task 프롬프트가 준비되어 있습니다.
