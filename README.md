# Cursor On-Prem PoC (Web) — Starter Repo

이 레포는 사내 온프레미스 환경에서 **웹 기반 Cursor-mini PoC**를 빠르게 착수하기 위한 스캐폴딩입니다.

## 구성
- `apps/web`: Next.js + Monaco 기반 Web IDE 스켈레톤
- `apps/api`: FastAPI 기반 API 스켈레톤 (workspace/files/ai/patch/ws)
- `packages/shared-types`: API/WS DTO 타입 (TypeScript)
- `packages/diff-utils`: unified diff 파싱/검증/적용 유틸 (TypeScript)
- `packages/prompt-templates`: 프롬프트 템플릿
- `infra/llm`: vLLM 실행 예시 (온프레미스)

## Quickstart (개발자 PC 또는 사내 Dev 서버)
1) Node 20+, pnpm, Python 3.11+
2) `pnpm -r install`
3) API: `pnpm --filter @poc/api dev`
4) WEB: `pnpm --filter @poc/web dev`

## Codex 작업
- `AGENTS.md` 규칙을 읽고 작업하도록 설정되어 있습니다.
- `codex/tasks/`에 Task 프롬프트가 준비되어 있습니다.
