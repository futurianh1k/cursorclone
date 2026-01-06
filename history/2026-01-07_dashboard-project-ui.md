요청자: 사용자
일자: 2026-01-07
브랜치: feature/project-workspace-split

## 요구사항 요약
- 프로젝트/워크스페이스 분리(pid/wid) 이후, **UI까지 이어서 구현**.
- 대시보드에서 프로젝트를 선택해 워크스페이스를 생성할 수 있어야 함.

## Assistant(제가) 응답(무엇을 할지)
- Web Dashboard에서 프로젝트 목록을 불러오고, “새 워크스페이스 생성” 모달에 프로젝트 선택(기존/새 프로젝트)을 추가.
- API client에 projects API 및 createWorkspace payload 확장(projectId/projectName).
- GitHub 클론도 기존 프로젝트에 붙일 수 있도록 API가 projectId를 수용하도록 보완.
- vitest로 최소 1개 테스트 추가/갱신.

## 실제로 수행한 변경 내용(요약)
- Web
  - `apps/web/src/lib/api.ts`: projects API 추가 + createWorkspace payload 확장 + cloneGitHubRepository projectId 전달 지원
  - `apps/web/src/app/dashboard/page.tsx`: 프로젝트 목록 로드 + 워크스페이스 생성 모달에 프로젝트 선택 UI + 카드에 project 표시
  - `apps/web/src/__tests__/api.test.ts`: projectId/projectName payload 테스트 추가
  - `apps/web/src/__tests__/components/FileTree.test.tsx`: 테스트 안정화(폴더 toggle 케이스 대응)
- API
  - `apps/api/src/models/base.py`: `CloneGitHubRequest`에 projectId/projectName 추가
  - `apps/api/src/routers/workspaces.py`: `/clone`에서 projectId 지정 시 해당 프로젝트에 workspace 추가(권한 검사), 미지정 시 새 프로젝트 생성

## 테스트 및 검증 방법
- Web:
  - `cd apps/web && npm install --legacy-peer-deps`
  - `cd apps/web && npm test`
- API:
  - `docker compose build api && docker compose up -d api`
  - `/health` 확인

## 향후 작업 / 주의사항
- 프로젝트를 “대시보드 상단에서 관리(삭제/이름 변경 등)”하는 UI는 아직 미구현(필요 시 추가).
- `npm install`은 eslint peer-deps 충돌로 `--legacy-peer-deps`가 필요할 수 있음(개발환경 정리 과제).

