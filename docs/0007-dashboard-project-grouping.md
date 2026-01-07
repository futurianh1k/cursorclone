## 요청
- 프로젝트 단위로 워크스페이스 목록을 그룹핑(접기/펼치기)
- 프로젝트 카드에서 바로 “워크스페이스 추가” 버튼 제공

## 구현 요약
- `/dashboard`에서 워크스페이스 리스트를 `projectId` 기준으로 그룹핑
  - 프로젝트 카드: 접기/펼치기 토글, 워크스페이스 수/IDE 상태(실행/중지) 표시
  - 카드 내: 해당 프로젝트의 워크스페이스 목록 렌더
  - 카드 상단: “+ 워크스페이스 추가” 버튼(해당 프로젝트로 모달 preselect)
  - 상단: “모두 펼치기/모두 접기” 제공

## 코드
- `apps/web/src/lib/projectGrouping.ts`: 그룹핑 유틸
- `apps/web/src/app/dashboard/page.tsx`: 프로젝트 카드 UI
- `apps/web/src/__tests__/projectGrouping.test.ts`: 그룹핑 테스트

## 테스트
- `cd apps/web && npm test`

