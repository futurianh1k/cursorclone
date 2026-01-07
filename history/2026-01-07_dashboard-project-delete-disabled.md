요청자: 사용자
일자: 2026-01-07
브랜치: feature/project-workspace-split

## 요구사항 요약
- 프로젝트 카드에서 프로젝트 삭제를 “워크스페이스 0개일 때만” 가능하도록 UI로 명확히 표현

## 실제 수행한 변경
- Web
  - 프로젝트 카드 헤더의 🗑️ 삭제 버튼을 `workspaceCount==0`일 때만 활성화
  - 비활성화 시 시각적 피드백(회색/opacity/cursor) 및 안내 툴팁 추가
  - 조건 로직을 `canDeleteProject()` 유틸로 분리하고 단위 테스트 추가

## 테스트
- `cd apps/web && npm test`

