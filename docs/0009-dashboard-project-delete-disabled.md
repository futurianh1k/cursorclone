## 요청
- 프로젝트 카드에서 “프로젝트 삭제” 버튼을 워크스페이스 0개일 때만 활성화되게 해서 더 명확하게

## 구현 요약
- 프로젝트 카드 헤더의 **🗑️ 삭제** 버튼을 다음 규칙으로 변경
  - 워크스페이스가 **0개면 활성화**
  - 워크스페이스가 **1개 이상이면 비활성화(disabled)** + 회색 처리 + `not-allowed` 커서
  - 툴팁(`title`)로 “워크스페이스가 있으면 삭제할 수 없습니다” 안내

## 코드
- `apps/web/src/app/dashboard/page.tsx`
- `apps/web/src/lib/projectManagement.ts`
- `apps/web/src/__tests__/projectManagement.test.ts`

## 테스트
- `cd apps/web && npm test`

