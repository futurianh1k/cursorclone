## 요청
- 사용자는 프로젝트/워크스페이스 분리(pid/wid) 이후, **웹 UI까지 이어서 구현**을 요청.

## 구현 요약
- Dashboard(`/dashboard`)에서:
  - 프로젝트 목록을 불러오고
  - 워크스페이스 생성 모달에서 **프로젝트 선택(기존/새 프로젝트)** 을 지원
  - 워크스페이스 카드에서 project 표시
- Web API client(`apps/web/src/lib/api.ts`)에:
  - `listProjects/createProject/getProject` 추가
  - `createWorkspace`가 `projectId/projectName` payload를 지원(하위 호환 유지)
  - `cloneGitHubRepository`가 `projectId/projectName`을 보낼 수 있게 확장
- Backend(API):
  - `CloneGitHubRequest`가 `projectId/projectName`을 수용
  - `/api/workspaces/clone`이 **기존 projectId에 붙이거나(권한 체크), 없으면 새 프로젝트 생성**하도록 확장

## 테스트
- `apps/web`: `npm test` (vitest)
  - API payload 테스트 추가 및 기존 테스트 안정화

