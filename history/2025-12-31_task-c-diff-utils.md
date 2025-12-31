# 2025-12-31 - Task C: Diff 유틸 구현

## 사용자 요구사항

- Task C 수행: unified diff 파서/검증/적용 최소 구현
- `../` 탈출 금지, 파일 확장자 allowlist, patch 크기 제한
- `/patch/validate`, `/patch/apply`에 연결

## 구현 답변

`packages/diff-utils`에 unified diff 파서, 보안 검증, 패치 적용 기능을 구현했습니다.

### 구현 내용

1. **Unified Diff 파서** (`parseUnifiedDiff`)
   - `--- a/path`, `+++ b/path` 형식 파싱
   - `@@ -start,count +start,count @@` hunk 헤더 파싱
   - 다중 파일 diff 지원

2. **보안 검증** (`validatePatch`)
   - 경로 탈출 방지 (`../`, `..\\` 검증)
   - 파일 확장자 allowlist (`.py`, `.js`, `.ts` 등 허용)
   - 패치 크기 제한 (1MB)
   - 파일 수 제한 (100개)
   - 워크스페이스 내 경로 검증

3. **패치 적용** (`applyPatchToText`)
   - unified diff를 원본 텍스트에 적용
   - 컨텍스트 매칭 검증
   - 충돌 감지 및 보고

4. **테스트 코드** (`index.test.ts`)
   - 기본 파싱/검증/적용 테스트
   - vitest 설정 필요 (TODO)

5. **API 라우터 연동 준비**
   - Python API 라우터에 TODO 업데이트
   - 향후 Node.js subprocess 호출 또는 Python 포팅 필요

## 수정 내역 요약

### 추가된 파일
- `packages/diff-utils/src/index.ts`: Diff 유틸 구현 (대폭 확장)
- `packages/diff-utils/src/index.test.ts`: 테스트 코드 (신규)
- `history/2025-12-31_task-c-diff-utils.md`: 변경 이력 (본 문서)

### 수정된 파일
- `packages/diff-utils/tsconfig.json`: Node.js 타입 지원 추가
- `packages/diff-utils/package.json`: @types/node 추가
- `apps/api/src/routers/patch.py`: TODO 주석 업데이트 (diff-utils 구현 완료 명시)

### 주요 설계 결정

1. **보안 우선**
   - 경로 탈출 방지 (정규화 및 검증)
   - 확장자 allowlist (명시적 허용만)
   - 크기 제한 (패치 1MB, 파일 10MB)
   - 워크스페이스 격리 검증

2. **타입 안정성**
   - TypeScript로 타입 정의
   - 인터페이스 명확화 (PatchFile, PatchHunk, HunkLine)

3. **확장 가능한 구조**
   - 단일 파일 패치 우선 지원
   - 다중 파일 패치 파싱 지원 (적용은 향후)

## 테스트

### 빌드 테스트
```bash
cd packages/diff-utils && pnpm build
```
✅ 성공

### 테스트 코드
- `index.test.ts` 작성 완료
- vitest 설정 필요 (TODO)

### 수동 테스트
```typescript
// 간단한 실행 테스트
node dist/index.js  // (테스트 코드의 if require.main === module 부분)
```

## 향후 작업

1. **Python API 연동**
   - Node.js subprocess로 호출하거나
   - Python 포팅 (unifiediff 패키지 활용 가능)

2. **테스트 프레임워크 설정**
   - vitest 설정
   - CI/CD 통합

3. **다중 파일 패치 적용**
   - 현재는 단일 파일만 지원
   - 다중 파일 적용 기능 추가

4. **성능 최적화**
   - 대용량 파일 처리
   - 병렬 처리

## 참고

- **원본 태스크**: `codex/tasks/task-c-diff-utils.md`
- **API 명세**: `docs/api-spec.md`
- **AGENTS 규칙**: `AGENTS.md`
- **구현 위치**: `packages/diff-utils/src/index.ts`
