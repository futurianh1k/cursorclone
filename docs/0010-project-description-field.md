## 요청
- 프로젝트 상세/설명(description) 필드까지 확장

## 구현 요약
- DB
  - `projects.description` (nullable, Text) 컬럼 추가
  - Alembic migration 추가
- API
  - `CreateProjectRequest.description` 추가
  - `UpdateProjectRequest.description` 추가 (PATCH에서 부분 업데이트)
  - `ProjectResponse.description` 추가
- Web
  - `Project` 타입에 `description?: string | null` 추가
  - 프로젝트 카드에서 description 표시
  - 프로젝트 “이름 변경” 편집 모드에서 description도 함께 편집(텍스트 영역) 및 저장

## 테스트
- Web: `cd apps/web && npm test`

