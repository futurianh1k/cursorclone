요청자: 사용자
일자: 2026-01-07
브랜치: feature/project-description

## 요구사항 요약
- 프로젝트에 상세/설명(description) 필드를 추가하고 UI/API/DB까지 확장

## Assistant(제가) 응답(무엇을 할지)
- DB 스키마에 `projects.description`을 추가(Alembic migration)
- API 스키마/라우터가 description을 입력/수정/응답하도록 확장
- 대시보드에서 프로젝트 설명을 표시하고 편집 가능하도록 UX 제공
- 최소 1개 테스트(vitest)로 변경을 검증

## 실제로 수행한 변경 내용(요약)
- DB
  - `apps/api/src/db/models.py`: `ProjectModel.description` 추가
  - `apps/api/migrations/versions/2026_01_07_2201-7c8a3b1f0e3a_add_project_description.py`: migration 추가
- API
  - `apps/api/src/models/base.py`: Create/Update/Response에 description 추가
  - `apps/api/src/routers/projects.py`: POST/PATCH/GET 응답에 description 반영
- Web
  - `apps/web/src/lib/api.ts`: Project 타입/요청 형식에 description 반영
  - `apps/web/src/app/dashboard/page.tsx`: 프로젝트 카드에서 description 표시/편집/저장
  - `apps/web/src/__tests__/api.test.ts`: updateProject 시그니처 변경 반영

## 테스트 및 검증 방법
- `cd apps/web && npm test`

