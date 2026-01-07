요청자: 사용자
일자: 2026-01-07
브랜치: feature/project-workspace-split

## 요구사항 요약
- 대시보드에서 프로젝트 단위로 워크스페이스를 그룹핑(접기/펼치기)
- 프로젝트 카드에서 “워크스페이스 추가” 버튼 제공

## Assistant(제가) 응답(무엇을 할지)
- 프론트에서 워크스페이스 목록을 projectId 기준으로 그룹핑하고, 프로젝트 카드 단위 UI로 리팩터링.
- 카드 내 접기/펼치기, 전체 펼치기/접기, 해당 프로젝트로 생성 모달 preselect를 제공.
- vitest 테스트를 추가하여 그룹핑 로직을 검증.

## 실제로 수행한 변경 내용(요약)
- Web
  - `apps/web/src/lib/projectGrouping.ts`: 그룹핑 유틸 추가
  - `apps/web/src/app/dashboard/page.tsx`: 프로젝트 카드 UI(접기/펼치기/추가 버튼/전체 토글)
  - `apps/web/src/__tests__/projectGrouping.test.ts`: 그룹핑 로직 단위 테스트 추가

## 테스트 및 검증 방법
- `cd apps/web && npm test`

