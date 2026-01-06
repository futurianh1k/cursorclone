요청자: 사용자
일자: 2026-01-07
브랜치: feature/project-workspace-split

## 요구사항 요약
- `project_id(pid)`와 `workspace_id(wid)`를 **DB/토큰/감사 관점에서 분리**한다.
- 관계는 **1 Project : N Workspaces** 를 지원한다.
- pid 발급/검증/감사(게이트웨이 audit 포함)까지 일관되게 동작해야 한다.
- DB 구조 수정(마이그레이션) 허용.

## Assistant가 하기로 한 일(응답 요약)
- DB에 `projects` 테이블을 추가하고 `workspaces.project_id` FK를 추가한다.
- 기존 데이터는 “workspace별 1 project”로 자동 승격(backfill)하여 데이터 손실 없이 전환한다.
- Workspace 생성 시 `projectId`를 선택적으로 받아 기존 project에 붙일 수 있게 하고, 없으면 새 project를 자동 생성한다.
- Gateway 토큰 발급 시 `pid != wid` 구조를 반영하고, IDE(code-server)에도 workspace별 pid/wid 기반 토큰을 주입한다.
- 최소 단위 테스트(pytest)로 pid/wid 분리 클레임을 검증한다.

## 실제로 수행한 변경 내용
- **DB/마이그레이션**
  - `apps/api/src/db/models.py`: `ProjectModel` 추가, `WorkspaceModel.project_id` FK 추가(필수)
  - `apps/api/migrations/versions/2026_01_07_0206-97af3d80270c_add_projects_table_and_workspace_.py`
    - `projects` 테이블 생성
    - `workspaces.project_id` 컬럼 추가 + FK + 인덱스
    - 기존 workspace를 `project_id = prj_{workspace_id}`로 승격(backfill)
    - 부분 적용 상태에서도 동작하도록 idempotent DDL 적용
- **API**
  - `apps/api/src/routers/projects.py`: 프로젝트 생성/목록/조회 API 추가
  - `apps/api/src/routers/workspaces.py`
    - workspace 생성 시 `projectId`(옵션) 지원
    - `projectId` 미지정 시 새 프로젝트 자동 생성
    - `workspace_id`는 전역 유니크를 위해 suffix 부여(동일 name 다중 생성 허용)
    - list/clone 응답에 `projectId` 포함
  - `apps/api/src/routers/auth.py`: Gateway 토큰 발급에서 `project_id`를 `ws.project_id`로 사용
- **IDE/Gateway 토큰**
  - `apps/api/src/services/ide_service.py`: 컨테이너 생성 시 `project_id`를 받아 gateway 토큰 pid/wid에 반영
- **운영 편의(마이그레이션 실행)**
  - `apps/api/Dockerfile`: `alembic.ini`, `migrations/`를 이미지에 포함(컨테이너에서 alembic 실행 가능)
- **테스트**
  - `apps/api/tests/test_gateway_jwks.py`: pid/wid 분리(claim) 테스트 강화

## 테스트 및 검증 방법
- 단위 테스트:
  - `pytest apps/api/tests/test_gateway_jwks.py`
- DB 마이그레이션(컨테이너 내부):
  - `docker exec cursor-poc-api sh -lc 'cd /app && alembic -c alembic.ini upgrade head'`
- 스키마 확인:
  - `\d workspaces` 에 `project_id` NOT NULL 및 FK 존재 확인

## 주의사항 / 향후 작업
- 현재 Web UI에는 “기존 프로젝트 선택 후 workspace 추가” UI가 없다.
  - API는 `CreateWorkspaceRequest.projectId`로 지원하므로, UI는 추후 추가 가능.
- `workspace_id`가 `ws_{name}_{suffix}` 형태로 바뀌므로, “id를 name에서 역추정하는 코드”가 있다면 제거/수정 필요.

